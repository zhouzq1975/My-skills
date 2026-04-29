#!/usr/bin/env python3
"""Fetch structured restaurant data from Google Maps Places API.

This module handles a single restaurant. It can:
  1. Search for a place by name + address -> get place_id
  2. Fetch Place Details -> return structured data
  3. Optionally merge results into an existing source-packet JSON

Requires GOOGLE_PLACES_API_NEW_KEY in environment or scripts/.env file.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import sys
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("ERROR: 'requests' is not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

DOTENV_PATH = Path(__file__).resolve().parent / ".env"
TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PLACE_DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"
TEXT_SEARCH_FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.location",
])
DETAIL_FIELD_MASK = ",".join([
    "id",
    "displayName",
    "formattedAddress",
    "location",
    "rating",
    "userRatingCount",
    "regularOpeningHours",
    "nationalPhoneNumber",
    "internationalPhoneNumber",
    "websiteUri",
    "priceLevel",
    "priceRange",
    "businessStatus",
    "types",
    "googleMapsUri",
    "reviews",
])
SCHEMA_VERSION = 2
HTTP_TIMEOUT = 15


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("\"'")
            if key and key not in os.environ:
                os.environ[key] = value


def get_api_key() -> str:
    load_dotenv(DOTENV_PATH)
    key = os.environ.get("GOOGLE_PLACES_API_NEW_KEY", "")
    if not key:
        raise RuntimeError(
            "GOOGLE_PLACES_API_NEW_KEY not set. Set it in environment or in scripts/.env"
        )
    return key


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_packet(path: Path, packet: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(packet, f, ensure_ascii=False, indent=2)
        f.write("\n")


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "restaurant"


def price_level_to_symbol(level: int | str | None) -> str | None:
    mapping = {0: "Free", 1: "€", 2: "€€", 3: "€€€", 4: "€€€€"}
    enum_mapping = {
        "PRICE_LEVEL_FREE": "Free",
        "PRICE_LEVEL_INEXPENSIVE": "€",
        "PRICE_LEVEL_MODERATE": "€€",
        "PRICE_LEVEL_EXPENSIVE": "€€€",
        "PRICE_LEVEL_VERY_EXPENSIVE": "€€€€",
    }
    if isinstance(level, str):
        return enum_mapping.get(level)
    return mapping.get(level)


def first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value:
            continue
        return value
    return None


def money_to_decimal(money: dict[str, Any] | None) -> float | None:
    if not isinstance(money, dict):
        return None
    units = money.get("units")
    nanos = money.get("nanos", 0)
    if units is None and nanos in (None, 0):
        return None
    try:
        units_val = float(units or 0)
        nanos_val = float(nanos or 0) / 1_000_000_000
    except (TypeError, ValueError):
        return None
    return round(units_val + nanos_val, 2)


def format_eur_range(min_price: float | None, max_price: float | None) -> str | None:
    def fmt(value: float) -> str:
        if value.is_integer():
            return str(int(value))
        return f"{value:.2f}".rstrip("0").rstrip(".")

    if min_price is None and max_price is None:
        return None
    if min_price is not None and max_price is not None:
        return f"€{fmt(min_price)}–{fmt(max_price)}"
    if min_price is not None:
        return f"€{fmt(min_price)}+"
    return f"up to €{fmt(max_price)}"


def format_price_range_code(min_price: float | None, max_price: float | None) -> str | None:
    def fmt(value: float) -> str:
        if value.is_integer():
            return str(int(value))
        return f"{value:.2f}".rstrip("0").rstrip(".")

    if min_price is None and max_price is None:
        return None
    if min_price is not None and max_price is not None:
        return f"eur_{fmt(min_price)}_{fmt(max_price)}"
    if min_price is not None:
        return f"eur_{fmt(min_price)}_plus"
    return f"eur_up_to_{fmt(max_price)}"


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "codex-restaurant-data-capture/1.0"})
    return session


def google_headers(api_key: str, field_mask: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": field_mask,
    }


def review_text(review: dict[str, Any]) -> str | None:
    text = review.get("text")
    if isinstance(text, dict):
        return text.get("text")
    if isinstance(text, str):
        return text
    original = review.get("originalText")
    if isinstance(original, dict):
        return original.get("text")
    if isinstance(original, str):
        return original
    return None


def adapt_place_new(place: dict[str, Any]) -> dict[str, Any]:
    location = place.get("location") or {}
    display_name = place.get("displayName") or {}
    regular_hours = place.get("regularOpeningHours") or {}
    adapted_reviews = []
    for review in place.get("reviews") or []:
        adapted_reviews.append({
            "rating": review.get("rating"),
            "text": review_text(review),
            "relative_time_description": review.get("relativePublishTimeDescription"),
        })
    return {
        "place_id": place.get("id"),
        "name": display_name.get("text") if isinstance(display_name, dict) else None,
        "formatted_address": place.get("formattedAddress"),
        "geometry": {
            "location": {
                "lat": location.get("latitude"),
                "lng": location.get("longitude"),
            }
        },
        "rating": place.get("rating"),
        "user_ratings_total": place.get("userRatingCount"),
        "opening_hours": {
            "weekday_text": regular_hours.get("weekdayDescriptions") or [],
        },
        "formatted_phone_number": place.get("nationalPhoneNumber"),
        "international_phone_number": place.get("internationalPhoneNumber"),
        "website": place.get("websiteUri"),
        "price_level": place.get("priceLevel"),
        "price_range": place.get("priceRange"),
        "business_status": place.get("businessStatus"),
        "types": place.get("types") or [],
        "url": place.get("googleMapsUri"),
        "reviews": adapted_reviews,
    }


def find_place(
    name: str,
    address: str,
    api_key: str,
    session: requests.Session | None = None,
) -> dict[str, Any] | None:
    query = f"{name} {address}"
    client = session or requests
    resp = client.post(
        TEXT_SEARCH_URL,
        headers=google_headers(api_key, TEXT_SEARCH_FIELD_MASK),
        json={"textQuery": query, "languageCode": "en"},
        timeout=HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    places = data.get("places", [])
    if not places:
        return None
    place = places[0]
    return {
        "place_id": place.get("id"),
        "name": (place.get("displayName") or {}).get("text"),
        "formatted_address": place.get("formattedAddress"),
        "geometry": {"location": place.get("location") or {}},
    }


def get_place_details(
    place_id: str,
    api_key: str,
    language: str = "en",
    session: requests.Session | None = None,
) -> dict[str, Any] | None:
    params = {
        "languageCode": language,
    }
    client = session or requests
    resp = client.get(
        PLACE_DETAILS_URL.format(place_id=place_id),
        headers=google_headers(api_key, DETAIL_FIELD_MASK),
        params=params,
        timeout=HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    return adapt_place_new(resp.json())


def fetch_place_details_with_fallback(
    place_id: str,
    api_key: str,
    session: requests.Session,
) -> dict[str, Any]:
    languages = ("en", "zh-CN", "de")
    results: dict[str, Any] = {}
    concurrent_failed = False

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(languages)) as executor:
        future_map = {
            lang: executor.submit(get_place_details, place_id, api_key, lang, session)
            for lang in languages
        }
        for lang, future in future_map.items():
            try:
                results[lang] = future.result()
            except requests.RequestException as exc:
                concurrent_failed = True
                print(
                    f"  ⚠ Concurrent Place Details failed for language={lang}: {exc}",
                    file=sys.stderr,
                )
                results[lang] = None

    if concurrent_failed:
        print(
            "  ↻ Falling back to sequential Place Details requests for failed languages.",
            file=sys.stderr,
        )
        for lang in languages:
            if results.get(lang):
                continue
            try:
                results[lang] = get_place_details(place_id, api_key, lang, session)
            except requests.RequestException as exc:
                print(
                    f"  ⚠ Sequential Place Details failed for language={lang}: {exc}",
                    file=sys.stderr,
                )
                results[lang] = None

    return results


def fetch_restaurant(name: str, address: str, api_key: str) -> dict[str, Any] | None:
    with build_session() as session:
        candidate = find_place(name, address, api_key, session=session)
        if not candidate:
            print(f"  ⚠ No place found for: {name} ({address})", file=sys.stderr)
            return None

        place_id = candidate["place_id"]
        print(f"  ✓ Found place_id: {place_id}", file=sys.stderr)

        details = fetch_place_details_with_fallback(place_id, api_key, session)
        details_en = details.get("en")
        details_zh = details.get("zh-CN")
        details_de = details.get("de")

        if not details_en:
            print(f"  ⚠ Place Details failed for: {place_id}", file=sys.stderr)
            return None
        return {
            "place_id": place_id,
            "details_en": details_en,
            "details_zh": details_zh,
            "details_de": details_de,
        }


def extract_weekly_hours(details: dict[str, Any]) -> dict[str, str] | None:
    oh = details.get("opening_hours")
    if not oh:
        return None
    weekday_text = oh.get("weekday_text", [])
    if not weekday_text:
        return None
    hours = {}
    for entry in weekday_text:
        parts = entry.split(": ", 1)
        if len(parts) == 2:
            hours[parts[0]] = parts[1]
    return hours or None


def extract_reviews_raw(details: dict[str, Any], lang: str) -> list[dict[str, Any]]:
    reviews = details.get("reviews", [])
    if not reviews:
        return []
    rows = []
    for r in reviews[:5]:
        rows.append({
            "platform": "google_maps_places_api",
            "rating": r.get("rating"),
            "language": lang,
            "text": r.get("text"),
            "publishedAtRaw": r.get("relative_time_description"),
            "dishTermsRaw": [],
            "selectionReason": "food_search_evidence_unclassified",
        })
    return rows


def canonicalize_seed(seed: dict[str, Any]) -> dict[str, Any]:
    extra_fields = deepcopy(seed.get("extra_fields") or {})
    category = first_non_empty(extra_fields.get("category"), seed.get("category"))
    chain = first_non_empty(extra_fields.get("chain"), seed.get("chain"))
    neighborhood = first_non_empty(extra_fields.get("neighborhood"), extra_fields.get("district"), seed.get("neighborhood"), seed.get("district"))
    category_code = first_non_empty(extra_fields.get("categoryCode"), seed.get("categoryCode"))
    if not category_code:
        if category in {"小吃", "Snack", "snack"}:
            category_code = "snack"
        elif category in {"饭店", "Restaurant", "restaurant"}:
            category_code = "restaurant"
        elif category in {"面馆", "Noodle house", "noodle house", "noodle_house"}:
            category_code = "noodle_house"
        elif category:
            category_code = str(category).strip().lower().replace(" ", "-")
    chain_bool = first_non_empty(extra_fields.get("chainBool"), seed.get("chainBool"))
    if chain_bool is None and chain is not None:
        chain_text = str(chain).strip()
        if chain_text in {"是", "yes", "true", "1"}:
            chain_bool = True
        elif chain_text in {"否", "no", "false", "0"}:
            chain_bool = False
    neighborhood_code = first_non_empty(extra_fields.get("neighborhoodCode"), extra_fields.get("districtCode"), seed.get("neighborhoodCode"), seed.get("districtCode"))
    if not neighborhood_code and neighborhood:
        neighborhood_code = str(neighborhood).strip().lower().replace(" ", "-").replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return {
        "inputNameRaw": first_non_empty(
            seed.get("inputNameRaw"),
            seed.get("nameZh"),
            seed.get("name_zh"),
            seed.get("nameEn"),
            seed.get("name_en"),
            seed.get("nameDe"),
            seed.get("name_de"),
            seed.get("name"),
        ),
        "nameZh": first_non_empty(seed.get("nameZh"), seed.get("name_zh")),
        "nameEn": first_non_empty(seed.get("nameEn"), seed.get("name_en"), seed.get("name")),
        "nameDe": first_non_empty(seed.get("nameDe"), seed.get("name_de"), seed.get("nameEn"), seed.get("name_en"), seed.get("name")),
        "addressRaw": first_non_empty(seed.get("addressRaw"), seed.get("address"), ""),
        "city": seed.get("city") or "",
        "country": seed.get("country") or "",
        "googleMapsUrl": first_non_empty(seed.get("googleMapsUrl"), seed.get("google_maps_url")),
        "extra_fields": {
            "category": category,
            "categoryCode": category_code,
            "chain": chain,
            "chainBool": chain_bool,
            "neighborhood": neighborhood,
            "neighborhoodCode": neighborhood_code,
        },
    }


def canonicalize_identity(identity: dict[str, Any]) -> dict[str, Any]:
    website = first_non_empty(identity.get("website"), identity.get("websiteUrl"))
    geo = identity.get("geo")
    if not isinstance(geo, dict):
        geo = {"lat": None, "lng": None}
    return {
        "canonicalName": first_non_empty(identity.get("canonicalName"), identity.get("canonical_name")),
        "aliases": deepcopy(identity.get("aliases") or []),
        "branchName": first_non_empty(identity.get("branchName"), identity.get("branch_name")),
        "branchCode": identity.get("branchCode"),
        "addressNormalized": first_non_empty(identity.get("addressNormalized"), identity.get("address_normalized")),
        "geo": {"lat": geo.get("lat"), "lng": geo.get("lng")},
        "neighborhood": identity.get("neighborhood"),
        "neighborhoodCode": identity.get("neighborhoodCode"),
        "phone": identity.get("phone"),
        "website": website,
        "officialSocialAccounts": deepcopy(identity.get("officialSocialAccounts") or identity.get("official_social_accounts") or []),
        "placeId": first_non_empty(identity.get("placeId"), identity.get("place_id")),
        "tripadvisorId": identity.get("tripadvisorId"),
        "deliveryPlatformIds": deepcopy(identity.get("deliveryPlatformIds") or {"wolt": None, "lieferando": None, "uberEats": None}),
        "identityMatchConfidence": first_non_empty(identity.get("identityMatchConfidence"), identity.get("identity_match_confidence")),
    }


def canonicalize_opening_hours(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows or []:
        if row.get("source") != "google_maps_api":
            continue
        out.append({
            "source": "google_maps_api",
            "weeklyHours": first_non_empty(row.get("weeklyHours"), row.get("weekly_hours")),
        })
    return out


def old_review_signal_to_raw(rows: list[dict[str, Any]], lang: str) -> list[dict[str, Any]]:
    out = []
    for row in rows or []:
        out.append({
            "platform": first_non_empty(row.get("platform"), "google_maps_places_api"),
            "rating": row.get("rating"),
            "language": first_non_empty(row.get("language"), lang),
            "text": row.get("text"),
            "publishedAtRaw": first_non_empty(row.get("publishedAtRaw"), row.get("time")),
            "dishTermsRaw": deepcopy(row.get("dishTermsRaw") or []),
            "selectionReason": first_non_empty(row.get("selectionReason"), "food_search_evidence_unclassified"),
        })
    return out


def canonicalize_observed(observed: dict[str, Any]) -> dict[str, Any]:
    review_signals = deepcopy(observed.get("review_signals") or {"google": None, "tripadvisor": None})
    if review_signals.get("google") is None:
        western = (observed.get("western_review_signals") or [])
        if western:
            first = western[0]
            review_signals["google"] = {
                "rating": first.get("rating"),
                "reviewCount": first.get("reviewCount") if "reviewCount" in first else first.get("review_count"),
            }
    if isinstance(review_signals.get("google"), dict):
        review_signals["google"].pop("priceBand", None)
        review_signals["google"].pop("price_band", None)
        review_signals["google"].pop("category", None)
    review_signals.setdefault("tripadvisor", None)

    reviews_raw = deepcopy(observed.get("reviews_raw") or {"google": [], "tripadvisor": []})
    if not reviews_raw.get("google"):
        reviews_raw["google"] = old_review_signal_to_raw(observed.get("western_review_signals_detail") or [], "en") + old_review_signal_to_raw(observed.get("chinese_review_signals") or [], "zh")
    reviews_raw.setdefault("tripadvisor", [])

    price = deepcopy(observed.get("price") or {})
    if not price:
        price = {
            "priceRangeDisplay": first_non_empty(observed.get("price_range")),
            "priceRangeCode": first_non_empty(observed.get("price_range")),
            "minPriceEur": None,
            "maxPriceEur": None,
        }
    else:
        price = {
            "priceRangeDisplay": first_non_empty(price.get("priceRangeDisplay"), observed.get("price_range")),
            "priceRangeCode": first_non_empty(price.get("priceRangeCode"), observed.get("price_range")),
            "minPriceEur": price.get("minPriceEur"),
            "maxPriceEur": price.get("maxPriceEur"),
        }

    return {
        "opening_hours": canonicalize_opening_hours(observed.get("opening_hours") or []),
        "price": price,
        "service_modes": deepcopy(observed.get("service_modes") or []),
        "menus": deepcopy(observed.get("menus") or []),
        "review_signals": review_signals,
        "reviews_raw": reviews_raw,
        "photos": deepcopy(observed.get("photos") or []),
    }


def canonicalize_normalized(normalized: dict[str, Any]) -> dict[str, Any]:
    dish_entities = deepcopy(normalized.get("dishEntities") or [])
    if not dish_entities:
        for item in normalized.get("menu_items") or []:
            dish_entities.append({
                "canonicalName": first_non_empty(item.get("canonicalName"), item.get("name")),
                "nameZh": item.get("nameZh"),
                "nameEn": item.get("nameEn"),
                "nameDe": item.get("nameDe"),
                "aliases": deepcopy(item.get("aliases") or []),
                "section": item.get("section"),
                "dishCode": item.get("dishCode"),
                "isPrimary": False,
                "dietaryTags": deepcopy(item.get("dietaryTags") or []),
                "spiceLevel": item.get("spiceLevel"),
                "availabilityStatus": item.get("availabilityStatus"),
                "sourceRefs": [
                    {
                        "source": item.get("source"),
                        "sourceUrl": item.get("sourceUrl"),
                    }
                ] if item.get("source") or item.get("sourceUrl") else [],
            })
    return {
        "cuisineLabels": deepcopy(normalized.get("cuisineLabels") or normalized.get("categories") or []),
        "cuisineCodes": deepcopy(normalized.get("cuisineCodes") or []),
        "dietaryTags": deepcopy(normalized.get("dietaryTags") or normalized.get("dietary_tags") or []),
        "dishEntities": dish_entities,
    }


def canonicalize_inferred(inferred: dict[str, Any]) -> dict[str, Any]:
    return {
        "positioning_summary": inferred.get("positioning_summary"),
        "short_description_zh": inferred.get("short_description_zh"),
        "short_description_en": inferred.get("short_description_en"),
        "short_description_de": inferred.get("short_description_de"),
        "is_new_opening": inferred.get("is_new_opening"),
    }


def canonicalize_extracted(extracted: dict[str, Any]) -> dict[str, Any]:
    review_insights = deepcopy(extracted.get("reviewInsights") or {})
    search_terms = deepcopy(extracted.get("searchTerms") or extracted.get("searchCandidates") or {})
    return {
        "reviewInsights": {
            "recommendedDishes": deepcopy(review_insights.get("recommendedDishes") or []),
            "dishMentions": deepcopy(review_insights.get("dishMentions") or []),
        },
        "searchTerms": {
            "restaurantAliases": deepcopy(search_terms.get("restaurantAliases") or []),
            "cuisineAliases": deepcopy(search_terms.get("cuisineAliases") or []),
            "dishAliases": deepcopy(search_terms.get("dishAliases") or []),
            "exactTerms": deepcopy(search_terms.get("exactTerms") or []),
            "autocompleteTerms": deepcopy(search_terms.get("autocompleteTerms") or []),
            "styleTerms": deepcopy(search_terms.get("styleTerms") or []),
            "occasionTerms": deepcopy(search_terms.get("occasionTerms") or []),
            "nonSpicyTerms": deepcopy(search_terms.get("nonSpicyTerms") or search_terms.get("nonSpicySignals") or []),
            "spicyTerms": deepcopy(search_terms.get("spicyTerms") or search_terms.get("spicySignals") or []),
            "languageHints": deepcopy(search_terms.get("languageHints") or []),
        },
    }


def convert_legacy_field_status(field_status: dict[str, Any]) -> dict[str, Any]:
    def pick(*keys: str) -> dict[str, Any]:
        for key in keys:
            if key in field_status:
                row = field_status.get(key) or {}
                return {
                    "status": row.get("status", "not_obtained"),
                    "failureReason": first_non_empty(row.get("failureReason"), row.get("failure_reason"), "source_not_found"),
                }
        return {"status": "not_obtained", "failureReason": "source_not_found"}

    return {
        "identity_name": pick("identity_name", "identity"),
        "identity_contact": pick("identity_contact"),
        "identity_location": pick("identity_location", "geo"),
        "opening_hours": pick("opening_hours"),
        "rating": pick("rating"),
        "full_menu": pick("full_menu"),
        "search_menu_coverage": pick("search_menu_coverage"),
        "search_review_coverage": pick("search_review_coverage"),
        "google_places_api_new": pick("google_places_api_new", "google_maps_api"),
        "tripadvisor": pick("tripadvisor"),
    }


def canonicalize_source_packet(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows or []:
        out.append({
            "type": row.get("type"),
            "platform": row.get("platform"),
            "url": row.get("url"),
            "sourceId": row.get("sourceId"),
            "accessStatus": first_non_empty(row.get("accessStatus"), row.get("access_status")),
            "relevance": row.get("relevance"),
            "accessMethod": row.get("accessMethod"),
            "httpStatus": row.get("httpStatus"),
            "contentType": row.get("contentType"),
            "capturedAt": row.get("capturedAt"),
            "snapshotPath": row.get("snapshotPath"),
            "notes": row.get("notes"),
        })
    return out


def canonicalize_quality(quality: dict[str, Any]) -> dict[str, Any]:
    return {
        "overallConfidence": first_non_empty(quality.get("overallConfidence"), quality.get("overall_confidence")),
        "servingReadiness": quality.get("servingReadiness") or "partial",
        "blockingReasons": deepcopy(quality.get("blockingReasons") or []),
        "needsReview": deepcopy(first_non_empty(quality.get("needsReview"), quality.get("needs_review"), [])),
        "conflicts": deepcopy(quality.get("conflicts") or []),
        "lastCompiledAt": first_non_empty(quality.get("lastCompiledAt"), quality.get("last_compiled_at"), date.today().isoformat()),
    }


def canonicalize_packet(packet: dict[str, Any]) -> dict[str, Any]:
    seed = canonicalize_seed(packet.get("seed") or {})
    name_for_slug = first_non_empty(seed.get("nameEn"), seed.get("nameDe"), seed.get("nameZh"), "restaurant")
    city_slug = slugify(seed.get("city") or "city")
    restaurant_slug = slugify(name_for_slug)
    packet_meta = deepcopy(packet.get("packet_meta") or {})
    packet_meta = {
        "packetId": first_non_empty(packet_meta.get("packetId"), f"{city_slug}__{restaurant_slug}"),
        "city": first_non_empty(packet_meta.get("city"), seed.get("city"), ""),
        "country": first_non_empty(packet_meta.get("country"), seed.get("country"), ""),
        "slug": first_non_empty(packet_meta.get("slug"), restaurant_slug),
        "createdAt": first_non_empty(packet_meta.get("createdAt"), date.today().isoformat()),
        "updatedAt": date.today().isoformat(),
        "schemaVersion": SCHEMA_VERSION,
    }

    canonical = {
        "packet_meta": packet_meta,
        "seed": seed,
        "identity": canonicalize_identity(packet.get("identity") or {}),
        "observed": canonicalize_observed(packet.get("observed") or {}),
        "normalized": canonicalize_normalized(packet.get("normalized") or {}),
        "inferred": canonicalize_inferred(packet.get("inferred") or {}),
        "extracted": canonicalize_extracted(packet.get("extracted") or {}),
        "field_status": convert_legacy_field_status(packet.get("field_status") or {}),
        "source_packet": canonicalize_source_packet(packet.get("source_packet") or []),
        "quality": canonicalize_quality(packet.get("quality") or {}),
    }
    if not canonical["identity"].get("officialSocialAccounts"):
        canonical["identity"]["officialSocialAccounts"] = deepcopy((packet.get("observed") or {}).get("official_social_accounts") or [])
    return canonical


def ensure_v2_seed(packet: dict[str, Any]) -> dict[str, Any]:
    canonical = canonicalize_packet(packet)
    packet.clear()
    packet.update(canonical)
    return packet["seed"]


def ensure_v2_structure(packet: dict[str, Any]) -> None:
    canonical = canonicalize_packet(packet)
    packet.clear()
    packet.update(canonical)


def mark_api_failure(packet: dict[str, Any], reason: str, note: str, url: str = "") -> dict[str, Any]:
    ensure_v2_structure(packet)
    fs = packet["field_status"]
    fs["google_places_api_new"] = {"status": "not_obtained", "failureReason": reason}

    sources = packet["source_packet"]
    existing = next((s for s in sources if s.get("type") == "api" and s.get("platform") == "google_places_api_new"), None)
    payload = {
        "type": "api",
        "platform": "google_places_api_new",
        "url": url,
        "sourceId": None,
        "accessStatus": "failed",
        "relevance": "high",
        "accessMethod": "places_api_new",
        "httpStatus": None,
        "contentType": "application/json",
        "capturedAt": date.today().isoformat(),
        "snapshotPath": None,
        "notes": note,
    }
    if existing is None:
        sources.append(payload)
    else:
        existing.update(payload)

    packet["quality"]["lastCompiledAt"] = date.today().isoformat()
    return packet


def maybe_set_serving_readiness(packet: dict[str, Any]) -> None:
    quality = packet.setdefault("quality", {})
    field_status = packet.setdefault("field_status", {})
    extracted = packet.setdefault("extracted", {}).setdefault("searchTerms", {})
    normalized = packet.setdefault("normalized", {})
    observed = packet.setdefault("observed", {})

    name_ok = field_status.get("identity_name", {}).get("status") in {"confirmed", "partial"}
    loc_ok = field_status.get("identity_location", {}).get("status") in {"confirmed", "partial"}
    dish_ok = bool(
        normalized.get("dishEntities")
        or any((menu.get("items") or []) for menu in observed.get("menus") or [] if isinstance(menu, dict))
    )
    search_ok = bool(extracted.get("dishAliases") or extracted.get("cuisineAliases") or extracted.get("styleTerms"))
    conflicts = quality.get("conflicts") or []
    has_blocking_conflict = any("identity" in c.lower() or "location" in c.lower() or "branch" in c.lower() for c in conflicts if isinstance(c, str))

    if has_blocking_conflict:
        quality["servingReadiness"] = "blocked"
    elif name_ok and loc_ok and dish_ok and search_ok:
        quality["servingReadiness"] = "ready"
    else:
        quality["servingReadiness"] = "partial"


def merge_into_packet(packet: dict[str, Any], api_data: dict[str, Any]) -> dict[str, Any]:
    ensure_v2_structure(packet)
    details = api_data["details_en"]
    details_zh = api_data.get("details_zh") or {}
    details_de = api_data.get("details_de") or {}
    place_id = api_data["place_id"]
    geo = details.get("geometry", {}).get("location", {})

    identity = packet["identity"]
    observed = packet["observed"]
    field_status = packet["field_status"]

    if not identity.get("placeId"):
        identity["placeId"] = place_id

    if geo and (not identity.get("geo") or not identity["geo"].get("lat")):
        identity["geo"] = {"lat": geo.get("lat"), "lng": geo.get("lng")}

    phone = details.get("international_phone_number") or details.get("formatted_phone_number")
    if phone and not identity.get("phone"):
        identity["phone"] = phone

    website = details.get("website")
    if website and not identity.get("website"):
        identity["website"] = website

    address = details.get("formatted_address")
    if address and not identity.get("addressNormalized"):
        identity["addressNormalized"] = address

    if details_zh.get("name") and not identity.get("canonicalName"):
        identity["canonicalName"] = details_zh.get("name")
    elif details.get("name") and not identity.get("canonicalName"):
        identity["canonicalName"] = details.get("name")

    weekly_hours = extract_weekly_hours(details)
    if weekly_hours:
        existing_sources = {h.get("source") for h in observed.get("opening_hours", [])}
        if "google_maps_api" not in existing_sources:
            observed["opening_hours"].append({
                "source": "google_maps_api",
                "weeklyHours": weekly_hours,
            })

    rating = details.get("rating")
    review_count = details.get("user_ratings_total")
    observed["review_signals"]["google"] = {
        "rating": rating,
        "reviewCount": review_count,
    }

    price_sym = price_level_to_symbol(details.get("price_level"))
    price_range = details.get("price_range") or {}
    start_price = price_range.get("startPrice") if isinstance(price_range, dict) else None
    end_price = price_range.get("endPrice") if isinstance(price_range, dict) else None
    min_price = money_to_decimal(start_price)
    max_price = money_to_decimal(end_price)
    currency = first_non_empty(
        (start_price or {}).get("currencyCode") if isinstance(start_price, dict) else None,
        (end_price or {}).get("currencyCode") if isinstance(end_price, dict) else None,
    )

    if min_price is not None:
        observed["price"]["minPriceEur"] = min_price if currency in {None, "EUR"} else observed["price"].get("minPriceEur")
    if max_price is not None:
        observed["price"]["maxPriceEur"] = max_price if currency in {None, "EUR"} else observed["price"].get("maxPriceEur")
    range_display = format_eur_range(observed["price"].get("minPriceEur"), observed["price"].get("maxPriceEur"))
    range_code = format_price_range_code(observed["price"].get("minPriceEur"), observed["price"].get("maxPriceEur"))
    if range_display and range_code:
        observed["price"]["priceRangeDisplay"] = range_display
        observed["price"]["priceRangeCode"] = range_code
    elif price_sym:
        if not observed["price"].get("priceRangeDisplay"):
            observed["price"]["priceRangeDisplay"] = price_sym
        if not observed["price"].get("priceRangeCode"):
            observed["price"]["priceRangeCode"] = price_sym

    types = details.get("types", [])
    if types and not observed.get("service_modes"):
        modes = []
        if "restaurant" in types or "food" in types:
            modes.append("dine_in")
        if "meal_delivery" in types:
            modes.append("delivery")
        if "meal_takeaway" in types:
            modes.append("takeaway")
        if modes:
            observed["service_modes"] = modes

    en_reviews = extract_reviews_raw(details, "en")
    zh_reviews = extract_reviews_raw(details_zh, "zh")
    de_reviews = extract_reviews_raw(details_de, "de")
    if en_reviews or zh_reviews or de_reviews:
        observed["reviews_raw"]["google"] = (en_reviews + zh_reviews + de_reviews)[:20]

    if place_id or identity.get("canonicalName"):
        field_status["identity_name"] = {"status": "confirmed", "failureReason": "not_applicable"}
    if geo or address:
        field_status["identity_location"] = {"status": "confirmed", "failureReason": "not_applicable"}
    if phone or website:
        field_status["identity_contact"] = {"status": "confirmed", "failureReason": "not_applicable"}
    if rating is not None:
        field_status["rating"] = {"status": "confirmed", "failureReason": "not_applicable"}
        if observed["reviews_raw"].get("google"):
            field_status["search_review_coverage"] = {"status": "partial", "failureReason": "not_applicable"}
    if weekly_hours:
        field_status["opening_hours"] = {"status": "confirmed", "failureReason": "not_applicable"}
    field_status["google_places_api_new"] = {"status": "confirmed", "failureReason": "not_applicable"}

    sources = packet["source_packet"]
    existing = next((s for s in sources if s.get("type") == "api" and s.get("platform") == "google_places_api_new"), None)
    payload = {
        "type": "api",
        "platform": "google_places_api_new",
        "url": details.get("url", ""),
        "sourceId": place_id,
        "accessStatus": "accessed",
        "relevance": "high",
        "accessMethod": "places_api_new",
        "httpStatus": 200,
        "contentType": "application/json",
        "capturedAt": date.today().isoformat(),
        "snapshotPath": None,
        "notes": (
            f"Places API returned place_id={place_id}, rating={rating}, reviews={review_count}, "
            f"business_status={details.get('business_status', 'unknown')}."
        ),
    }
    if existing is None:
        sources.append(payload)
    else:
        existing.update(payload)

    packet["quality"]["lastCompiledAt"] = date.today().isoformat()
    maybe_set_serving_readiness(packet)
    return packet


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch Google Maps data for a single restaurant.")
    parser.add_argument("--name", help="Restaurant name for search query.")
    parser.add_argument("--address", help="Restaurant address for search query.")
    parser.add_argument("--packet", help="Path to an existing source-packet.json.")
    parser.add_argument("--output", help="Write merged packet to this path instead of updating --packet in place.")
    parser.add_argument("--raw", action="store_true", help="Output raw API response to stdout (no packet merge).")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be fetched without calling the API.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    name = args.name
    address = args.address
    packet = None
    packet_path = None

    if args.packet:
        packet_path = Path(args.packet).resolve()
        packet = load_json(packet_path)
        seed = ensure_v2_seed(packet)
        if not name:
            name = seed.get("nameEn") or seed.get("nameZh") or seed.get("nameDe")
        if not address:
            address = seed.get("addressRaw", "")

    if not name:
        parser.error("--name is required (or provide --packet with a seed)")

    address = address or ""
    print(f"🔍 Searching: {name} | {address}", file=sys.stderr)

    if args.dry_run:
        print(f"  [DRY RUN] Would search Places API for: {name} {address}")
        return

    output_path = Path(args.output).resolve() if args.output else packet_path

    try:
        api_key = get_api_key()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        if packet is not None and output_path is not None:
            url = packet["seed"].get("googleMapsUrl", "") or ""
            write_packet(output_path, mark_api_failure(packet, "api_key_not_configured", str(exc), url=url))
        sys.exit(1)

    try:
        api_data = fetch_restaurant(name, address, api_key)
    except requests.RequestException as exc:
        print(f"  ✗ Places API request failed: {exc}", file=sys.stderr)
        if packet is not None and output_path is not None:
            url = packet["seed"].get("googleMapsUrl", "") or ""
            write_packet(output_path, mark_api_failure(packet, "api_call_failed", str(exc), url=url))
        sys.exit(1)

    if not api_data:
        print("  ✗ No results from Places API.", file=sys.stderr)
        if packet is not None and output_path is not None:
            url = packet["seed"].get("googleMapsUrl", "") or ""
            packet = mark_api_failure(packet, "api_no_results", f"No Google Maps Places API result for query: {name} | {address}", url=url)
            write_packet(output_path, packet)
        sys.exit(1)

    if args.raw:
        json.dump(api_data, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return

    if packet is None:
        template_path = Path(__file__).resolve().parent.parent / "assets" / "restaurant-source-packet.template.json"
        packet = load_json(template_path)
        packet["seed"] = {
            "inputNameRaw": name,
            "nameZh": None,
            "nameEn": name,
            "nameDe": name,
            "addressRaw": address,
            "city": "",
            "country": "",
            "googleMapsUrl": api_data["details_en"].get("url"),
            "extra_fields": {
                "category": None,
                "categoryCode": None,
                "chain": None,
                "chainBool": None,
                "neighborhood": None,
                "neighborhoodCode": None,
            },
        }
        ensure_v2_structure(packet)

    packet = merge_into_packet(packet, api_data)

    if output_path:
        write_packet(output_path, packet)
        print(f"  ✓ Written to: {output_path}", file=sys.stderr)
    else:
        json.dump(packet, sys.stdout, ensure_ascii=False, indent=2)
        print()


if __name__ == "__main__":
    main()
