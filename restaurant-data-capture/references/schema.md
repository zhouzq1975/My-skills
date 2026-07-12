# Schema Reference

## Top-level objects

`Source Packet V3` preserves the current packet's main structure while explicitly adding `packet_meta` and `extracted`.

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

The canonical design baseline is `/Volumes/媒体/chopmap/docs/specs/2026-06-07-restaurant-source-packet-v3-design.md`. Use `berlin__7-dumpling__source-packet.json` as the structural sample when changing the template or packet-writing scripts.

New packets should use `packet_meta.schemaVersion: 3`. Existing active packets may still carry older numeric values until a separate migration updates them.

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

### seed

Use `seed.extra_fields.category` and `seed.extra_fields.categoryCode` only as controlled intake hints.

Use:

- `seed.extra_fields.categoryCode`
  - controlled venue-category code
  - must come from `/Users/zhouziqiang/.codex/skills/restaurant-data-capture/assets/category-taxonomy.json`
- `seed.extra_fields.category`
  - matching standard Chinese label for that code
  - should use the taxonomy entry's `zh` value instead of packet-local wording

### normalized

Use for canonicalized restaurant and food facts.

Examples:

- canonical restaurant identity
- cuisine normalization
- canonical dish entities
- restaurant-level dietary tags

For cuisine normalization, use `normalized.cuisineCodes` as the canonical machine-oriented cuisine taxonomy field.
Use:

- `normalized.cuisineCodes`
  - stable, language-agnostic cuisine/type codes used for filtering, aggregation, and downstream compilation
  - must come from `/Users/zhouziqiang/.codex/skills/restaurant-data-capture/assets/cuisine-code-taxonomy.json`
  - should preserve the ordering defined in that taxonomy file

For display/search-oriented cuisine tags, use `extracted.cuisineTags` with aligned `zh`, `en`, and `de` arrays sourced from `/Users/zhouziqiang/.codex/skills/restaurant-data-capture/assets/cuisine-tag-taxonomy.json`. Taxonomy entries may include optional `codeHints` back to likely `normalized.cuisineCodes`; those hints may remain empty for pure scene/display tags.

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
- manually maintained operating-status flag

For this skill, `inferred` is a required frontend display layer rather than an optional scratch field. Populate it from the evidence already collected in the packet before finalizing the file. The expected keys are:

- `positioning_summary`
- `short_description_zh`
- `short_description_en`
- `short_description_de`
- `operating_status`
- `is_new_opening`

Keep the wording concise, factual, and grounded in the packet evidence.

`operating_status` values:

- `operating`
- `temporarily_closed`
- `closed_permanently`

`is_new_opening` values:

- `true`
- `false`
- `null`

For an open new restaurant, use `operating_status: "operating"` and `is_new_opening: true`. The current serving pipeline uses `is_new_opening` for the new-restaurant badge and maps `operating_status` separately for open/closed display.

`positioning_summary` has a distinct role from the localized short-description fields.

- `positioning_summary`
  - one compact English normalization sentence
  - meant to capture the restaurant's positioning in a retrieval/editorial sense
  - should summarize branch or neighborhood context, restaurant format, cuisine/style focus, core menu anchors, and the strongest menu-evidence mode
- `short_description_zh` / `short_description_en` / `short_description_de`
  - user-facing localized display copy
  - may read a little more naturally and descriptively
  - should still stay factual and evidence-grounded, but do not need to follow the same compressed normalization pattern as `positioning_summary`

`positioning_summary` generation rules:

- write it in English only
- keep it to one sentence
- target roughly 18-35 words
- start with branch, neighborhood, or local context when available
- identify the venue format clearly, such as `restaurant`, `noodle house`, `snack spot`, `hotpot restaurant`, or `buffet restaurant`
- name 2-3 core menu anchors using category-level phrases such as `dim sum`, `roast meats`, `hand-pulled noodles`, `Sichuan mains`, `hotpot`, `dumplings`, or `buffet dining`
- end with a short evidence clause such as `with official menu evidence`, `with official and delivery menu evidence`, or `with menu-photo evidence`
- keep it neutral and structural; do not write marketing copy, subjective praise, or long review-style narration
- do not repeat full review claims, atmosphere commentary, or operational detail unless they materially affect positioning

Preferred template:

- `[Neighborhood/branch] [descriptor] focused on [anchor 1], [anchor 2], and [anchor 3], with [evidence phrase].`

Examples:

- `Charlottenburg Cantonese restaurant focused on dim sum, roast meats, and noodle dishes, with official and delivery menu evidence.`
- `Friedrichshain Chinese noodle house focused on noodle soups, dry noodles, and dumplings, with delivery and menu-photo evidence.`
- `Lichtenberg Chinese buffet restaurant focused on buffet dining, wok dishes, and duck plates, with official menu evidence.`

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

`observed.reviews_raw` is an evidence set for dish-search extraction, not a full review archive. Include only reviews with concrete food-search evidence: explicit dish/food/preparation mentions, positive or negative dish-specific evaluation, platform-marked relevant snippets with food evidence, or food-evidence reviews from within the last 1 year. Do not impose an artificial item cap at the schema level; keep the actual in-scope count returned by the source. Exclude generic service, ambience, staff, queue, price, or broad "good food" reviews without concrete food-search evidence.
Raw review items should contain `platform`, `rating`, `language`, `text`, `publishedAtRaw`, `dishTermsRaw`, and `selectionReason`. Retained rows should have non-empty `dishTermsRaw`; if the source text has no concrete food terms, do not store it in `reviews_raw`. Do not store `reviewId`, `author`, `publishedAtIso`, `sourceUrl`, or AI-derived sentiment in `observed.reviews_raw`.

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
- When source menu evidence shows item-level prices, store each visible item price in `observed.menus[].items[].priceRaw` using the source's displayed formatting, such as `"8,50 €"`. Add `priceRaw` to refreshed packet items even if the older packet shape did not have a price field.
- use `dishEntities.isPrimary` for menu/positioning centrality
- when a packet has five or more `dishEntities`, set at least one primary dish; keep primary dish selections compact, usually 3-12 items
- do not store signature state in the source packet; derive it later in `restaurantCatalog`
- `normalized.dishEntities[].dishCode` is a cross-packet global dish concept code. It is not a local menu-item slug and not a menu number.
- Valid known global dish codes live in `/Volumes/媒体/chopmap/data/taxonomies/dish-code-taxonomy.json`.
- The dish-code taxonomy is an auxiliary input/lookup table for packet generation, not a source-packet output document. Source packets must not copy taxonomy-only fields such as taxonomy `canonicalName`, `labels`, `facets`, `mergeFrom`, `avoid`, or `pinyin`.
- The only direct packet field derived from the dish-code taxonomy is `normalized.dishEntities[].dishCode`. Any later use of taxonomy labels or facets should happen by looking up that `dishCode` outside the source packet.
- Use a non-null `dishCode` only when the normalized dish entity clearly maps to a taxonomy entry. Otherwise set `dishCode` to `null` and preserve the dish's real names/aliases for later taxonomy review.
- `canonicalName`, `nameZh`, `nameEn`, and `nameDe` stay restaurant/menu-specific. Do not overwrite them with the taxonomy label just because `dishCode` was assigned.
- `aliases` may include menu-origin names, official translations, pinyin/transliterations, and high-confidence review-derived dish names. Do not use `aliases` as an unbounded AI synonym dump.
- If an existing packet has a local slug, menu number, or platform-derived ID in `dishCode`, treat it as a migration candidate rather than a valid global code.
- Google Maps menu photos may be represented as `observed.menus` with `source: "google_maps_menu_photo"` when they contain first-hand menu text. Preserve multilingual labels in `nameRaw`; mark OCR uncertainty in `descriptionRaw` or `notes`; include visible dish-level prices in `priceRaw`.
- Standalone sauce/dip category items are excluded from menu evidence. Keep sauce words inside dish names, but do not store standalone sauces, dips, soy sauce, vinegar, chili oil, garlic oil, or `Sauces`/`Saucen` section items.

Canonical `observed.menus` item shape:

```json
{
  "source": "lieferando_menu_in_app_browser",
  "sourceUrl": "https://www.lieferando.de/en/menu/example",
  "capturedAt": "2026-04-21",
  "language": "en",
  "freshnessRank": "primary_current_menu",
  "notes": "Prices were visible and captured in priceRaw.",
  "items": [
    {
      "sectionRaw": "Dumplings",
      "nameRaw": "Wonton in Chili - Oil",
      "descriptionRaw": "with ginger and sesame",
      "priceRaw": "8,50 €"
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
- `not_ready`

Use this compact checklist:

### ready

Requires:

- `field_status.identity_name.status` is `confirmed` or `partial`
- `field_status.identity_location.status` is `confirmed` or `partial`
- `extracted.cuisineTags.zh`, `extracted.cuisineTags.en`, and `extracted.cuisineTags.de` are all non-empty and aligned by position
- at least one dish/menu evidence field is non-empty:
  - `normalized.dishEntities`, or
  - `observed.menus[*].items`
- at least one search-candidate field is non-empty:
  - `extracted.searchTerms.dishAliases`, or
  - `extracted.searchTerms.cuisineAliases`, or
  - `extracted.searchTerms.styleTerms`
- `quality.conflicts` contains no unresolved identity/location conflict

### not_ready

Use when the restaurant has not opened yet, is permanently closed, identity/location are missing or materially conflicted, dish/menu/search coverage is still too weak, or serving compilation would be too unreliable.

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
- `extracted.cuisineTags`
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
- `normalized.dishEntities[].dishCode` when the dish maps to a known global code in `/Volumes/媒体/chopmap/data/taxonomies/dish-code-taxonomy.json`

Optional and deferrable:

- `normalized.dishEntities[].dishCode` for dishes not yet covered by the global dish-code taxonomy; leave it `null` instead of inventing a local code
- taxonomy metadata such as dish `labels`, `facets`, `mergeFrom`, `avoid`, and taxonomy-level `canonicalName`; these remain outside the source packet and are retrieved later by `dishCode`
- `sceneTagCodes`
- `dietaryTagCodes`
- `bestForCodes`

## Filename convention

Use:

`city__restaurant-slug__source-packet.json`

Default directory for this workspace:

`/Volumes/媒体/chopmap/data/restaurants/`
