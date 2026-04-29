#!/usr/bin/env python3
"""Create a starter restaurant source packet from a seed JSON file."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path


SCHEMA_VERSION = 2


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "restaurant"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Initialize a single-restaurant source packet JSON file."
    )
    parser.add_argument("--seed", required=True, help="Path to a seed JSON file.")
    parser.add_argument(
        "--template",
        default=str(
            Path(__file__).resolve().parent.parent
            / "assets"
            / "restaurant-source-packet.template.json"
        ),
        help="Path to the packet template JSON file.",
    )
    parser.add_argument(
        "--output",
        default="/Volumes/媒体/chopmap/data/restaurants",
        help="Output directory for the generated packet.",
    )
    return parser


def choose_name(seed: dict) -> str:
    return (
        seed.get("nameEn")
        or seed.get("nameDe")
        or seed.get("nameZh")
        or seed.get("name_en")
        or seed.get("name_de")
        or seed.get("name_zh")
        or "restaurant"
    )


def normalize_seed(seed: dict) -> dict:
    extra_fields = seed.get("extra_fields") or {}
    category = extra_fields.get("category") or seed.get("category")
    chain = extra_fields.get("chain") or seed.get("chain")
    neighborhood = (
        extra_fields.get("neighborhood")
        or extra_fields.get("district")
        or seed.get("neighborhood")
        or seed.get("district")
    )
    category_code = extra_fields.get("categoryCode")
    if not category_code:
        if category in {"小吃", "Snack", "snack"}:
            category_code = "snack"
        elif category in {"饭店", "Restaurant", "restaurant"}:
            category_code = "restaurant"
        elif category in {"面馆", "Noodle house", "noodle house", "noodle_house"}:
            category_code = "noodle_house"
        elif category:
            category_code = str(category).strip().lower().replace(" ", "-")
    chain_bool = extra_fields.get("chainBool")
    if chain_bool is None and chain is not None:
        chain_text = str(chain).strip()
        if chain_text in {"是", "yes", "true", "1"}:
            chain_bool = True
        elif chain_text in {"否", "no", "false", "0"}:
            chain_bool = False
    neighborhood_code = extra_fields.get("neighborhoodCode") or extra_fields.get("districtCode")
    if not neighborhood_code and neighborhood:
        neighborhood_code = (
            str(neighborhood)
            .strip()
            .lower()
            .replace(" ", "-")
            .replace("ä", "ae")
            .replace("ö", "oe")
            .replace("ü", "ue")
            .replace("ß", "ss")
        )
    return {
        "inputNameRaw": seed.get("inputNameRaw") or seed.get("nameZh") or seed.get("name_zh") or seed.get("nameEn") or seed.get("name_en"),
        "nameZh": seed.get("nameZh") or seed.get("name_zh"),
        "nameEn": seed.get("nameEn") or seed.get("name_en") or seed.get("name"),
        "nameDe": seed.get("nameDe") or seed.get("name_de") or seed.get("nameEn") or seed.get("name_en") or seed.get("name"),
        "addressRaw": seed.get("addressRaw") or seed.get("address") or "",
        "city": seed.get("city") or "",
        "country": seed.get("country") or "",
        "googleMapsUrl": seed.get("googleMapsUrl") or seed.get("google_maps_url"),
        "extra_fields": {
            "category": category,
            "categoryCode": category_code,
            "chain": chain,
            "chainBool": chain_bool,
            "neighborhood": neighborhood,
            "neighborhoodCode": neighborhood_code,
        },
    }


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    seed_path = Path(args.seed).resolve()
    template_path = Path(args.template).resolve()
    output_dir = Path(args.output).resolve()

    raw_seed = load_json(seed_path)
    packet = load_json(template_path)
    seed = normalize_seed(raw_seed)
    packet["seed"] = seed

    city_slug = slugify(seed.get("city", "city"))
    restaurant_slug = slugify(choose_name(seed))
    packet_id = f"{city_slug}__{restaurant_slug}"
    today = date.today().isoformat()

    packet["packet_meta"] = {
        "packetId": packet_id,
        "city": seed.get("city", ""),
        "country": seed.get("country", ""),
        "slug": restaurant_slug,
        "createdAt": today,
        "updatedAt": today,
        "schemaVersion": SCHEMA_VERSION,
    }
    packet["quality"]["lastCompiledAt"] = today

    filename = f"{city_slug}__{restaurant_slug}__source-packet.json"

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(packet, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(output_path)


if __name__ == "__main__":
    main()
