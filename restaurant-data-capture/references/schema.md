# Schema Reference

## Top-level objects

`Source Packet V2` preserves the current packet's main structure while explicitly adding `packet_meta` and `extracted`.

Required top-level objects:

- `packet_meta`
- `seed`
- `identity`
- `observed`
- `normalized`
- `inferred`
- `extracted`
- `field_status`
- `source_packet`
- `quality`

The canonical packet shape for this skill is the one used by `berlin__7-dumpling__source-packet.json`. Treat that file as the reference when changing the template or the packet-writing scripts.

## Layer rules

### observed

Use for direct facts and close-to-source evidence.

Examples:

- Google Maps API phone number
- menu item shown on Wolt
- opening hours shown on Google Maps API
- raw review text returned by Google Maps API
- source-specific price display or category text

### identity

Use for stable restaurant identity and contact surfaces.

Examples:

- canonical name and aliases
- address and geo
- phone
- website
- official social account links/handles

Store official social account links under `identity.officialSocialAccounts`. Do not store them under `observed`, and do not collect or analyze account content.

### normalized

Use for canonicalized restaurant and food facts.

Examples:

- canonical restaurant identity
- cuisine normalization
- canonical dish entities
- restaurant-level dietary tags

### extracted

Use for search-oriented derivations generated from evidence.

Examples:

- review-derived recommended dishes
- dish mention counts
- restaurant alias buckets
- dish alias buckets
- style or occasion terms

### inferred

Use for cautious interpretation that is useful but not established as a canonical fact.

Examples:

- positioning summary
- localized short descriptions
- manually maintained new-opening flag

For this skill, `inferred` is a required frontend display layer rather than an optional scratch field. Populate it from the evidence already collected in the packet before finalizing the file. The expected keys are:

- `positioning_summary`
- `short_description_zh`
- `short_description_en`
- `short_description_de`
- `is_new_opening`

Keep the wording concise, factual, and grounded in the packet evidence.

Never move inferred data into observed.
Never store free-form search expansions in normalized.

## Review model

Review data is three-layered:

- `observed.review_signals`
  - platform summaries such as rating and review count
- `observed.reviews_raw`
  - raw review evidence grouped by platform
- `extracted.reviewInsights`
  - search-oriented outputs such as `recommendedDishes` and `dishMentions`

`observed.reviews_raw` is an evidence set for dish-search extraction, not a full review archive. Include only reviews with concrete food-search evidence: explicit dish/food/preparation mentions, positive or negative dish-specific evaluation, platform-marked relevant snippets with food evidence, or food-evidence reviews from within the last 6 months. If more than 20 in-scope reviews are available per platform, keep the most recent 20; if fewer are available, keep the actual count. Exclude generic service, ambience, staff, queue, price, or broad "good food" reviews without concrete food-search evidence.
Raw review items should contain `platform`, `rating`, `language`, `text`, `publishedAtRaw`, `dishTermsRaw`, and `selectionReason`. Do not store `reviewId`, `author`, `publishedAtIso`, `sourceUrl`, or AI-derived sentiment in `observed.reviews_raw`.

## Menu model

Menu data is three-layered:

- `observed.menus`
  - source-scoped menu evidence arrays
  - each menu object carries compact source metadata and source-facing item blocks
- `normalized.dishEntities`
  - canonical dish facts for downstream compilation

Current rule:

- `observed.menus` is the primary source-evidence anchor for menu capture and reprocessing
- `normalized.dishEntities` is the primary dish-compilation anchor
- use `dishEntities.isPrimary` for menu/positioning centrality
- do not store signature state in the source packet; derive it later in `restaurantCatalog`
- Google Maps menu photos may be represented as `observed.menus` with `source: "google_maps_menu_photo"` when they contain first-hand menu text. Preserve multilingual labels in `nameRaw`; mark OCR uncertainty in `descriptionRaw` or `notes`; do not store dish-level prices.
- Standalone sauce/dip category items are excluded from menu evidence. Keep sauce words inside dish names, but do not store standalone sauces, dips, soy sauce, vinegar, chili oil, garlic oil, or `Sauces`/`Saucen` section items.

Canonical `observed.menus` item shape:

```json
{
  "source": "lieferando_menu_playwright",
  "sourceUrl": "https://www.lieferando.de/en/menu/example",
  "capturedAt": "2026-04-21",
  "language": "en",
  "freshnessRank": "primary_current_menu",
  "notes": "Prices were visible but intentionally excluded.",
  "items": [
    {
      "sectionRaw": "Dumplings",
      "nameRaw": "Wonton in Chili - Oil",
      "descriptionRaw": "with ginger and sesame"
    }
  ]
}
```

## Field status values

Allowed `status` values:

- `confirmed`
- `partial`
- `not_obtained`

New packets should emit only the current fixed `field_status` key set used by the sample packet: `identity_name`, `identity_contact`, `identity_location`, `opening_hours`, `rating`, `full_menu`, `search_menu_coverage`, `search_review_coverage`, `google_places_api_new`, and `tripadvisor`. Legacy status keys such as `official_menu`, `delivery_menu`, `official`, and `google_maps_api` are compatibility inputs only and should not appear in refreshed packets.

Allowed `failureReason` values:

- `source_not_found`
- `source_exists_but_not_accessed`
- `source_requires_logged_in_review`
- `evidence_conflict`
- `only_delivery_menu_found`
- `high_frequency_mentions_without_official_confirmation`
- `mentioned_in_reviews_but_not_confirmed_by_current_menu`
- `not_applicable`
- `api_key_not_configured`
- `api_call_failed`
- `api_no_results`

## Source packet values

Allowed `type` values:

- `official`
- `delivery`
- `map`
- `review_platform`
- `api`
- `photo`

Allowed `platform` values for `api` type:

- `google_places_api_new`

Allowed `accessStatus` values:

- `accessed`
- `found_not_accessed`
- `login_required`
- `failed`
- `branch_mismatch`

Allowed `relevance` values:

- `high`
- `medium`
- `low`

## Publishability contract

`quality.servingReadiness` values:

- `ready`
- `partial`
- `blocked`

Use this compact checklist:

### ready

Requires:

- `field_status.identity_name.status` is `confirmed` or `partial`
- `field_status.identity_location.status` is `confirmed` or `partial`
- at least one dish/menu evidence field is non-empty:
  - `normalized.dishEntities`, or
  - `observed.menus[*].items`
- at least one search-candidate field is non-empty:
  - `extracted.searchTerms.dishAliases`, or
  - `extracted.searchTerms.cuisineAliases`, or
  - `extracted.searchTerms.styleTerms`
- `quality.conflicts` contains no unresolved identity/location conflict

### partial

Use when identity/location are mostly usable but dish/menu/search coverage is still too weak.

### blocked

Use when identity/location are missing or materially conflicted, or serving compilation would be too unreliable.

Review coverage is helpful but is not a hard prerequisite for `ready`.

## Minimum required search-critical fields

Every packet intended for search publication must include:

- `packet_meta.packetId`
- seed restaurant name or address
- at least one `source_packet` entry
- stable `identity`
- `observed.menus`
- `observed.review_signals`
- `observed.reviews_raw`
- `normalized.dishEntities`
- `normalized.cuisineCodes`
- `extracted.reviewInsights`
- `extracted.searchTerms`
- `field_status.identity_name`
- `field_status.identity_location`
- `field_status.search_menu_coverage`
- `field_status.search_review_coverage`
- `quality.servingReadiness`

## Code strategy

Keep code-bearing fields only when they materially improve multilingual search normalization or stable serving-layer compilation.

Required now:

- `normalized.cuisineCodes`

Optional and deferrable:

- `sceneTagCodes`
- `dietaryTagCodes`
- `bestForCodes`

## Filename convention

Use:

`city__restaurant-slug__source-packet.json`

Default directory for this workspace:

`/Volumes/媒体/chopmap/data/restaurants/`
