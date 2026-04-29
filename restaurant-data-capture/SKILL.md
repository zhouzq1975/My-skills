---
name: restaurant-data-capture
description: Use for creating or updating source-grounded restaurant data packets under data/restaurants.
---

# Restaurant Data Capture

Use this skill to build or refresh one restaurant source packet under `data/restaurants/*.json`.

The packet is the evidence-rich local source-of-truth layer.
It is not the serving document.

Keep the unit of work to one restaurant unless the user explicitly asks for a batch.
Emit one JSON file per restaurant.

## Skill Root

This skill's scripts, references, and assets live under:

`/Users/zhouziqiang/.codex/skills/restaurant-data-capture`

Do not assume the current working directory is the project repo or the skill directory.
When running commands from this skill, use absolute paths rooted at the skill directory, or set:

```bash
SKILL_DIR="/Users/zhouziqiang/.codex/skills/restaurant-data-capture"
```

## Core Model

The packet must preserve the boundary between the source layer and the serving layer.

- `source packet`
  - stores evidence, raw menu capture, raw reviews, provenance, low-confidence candidates, and AI-assisted intermediate analysis
- `restaurantCatalog`
  - is derived later for retrieval, filtering, ranking, and frontend rendering

Do not optimize the packet for frontend shape.
Do not copy full evidence blobs into the serving layer.

## Packet Shape Baseline

Treat /Volumes/媒体/chopmap/data/restaurants/berlin__7-dumpling__source-packet.json as the structural sample for this skill.

Keep the starter template and the packet-writing scripts aligned to that sample. New packets should preserve the sample's top-level objects and the exact current `field_status` key set:

- `identity_name`
- `identity_contact`
- `identity_location`
- `opening_hours`
- `rating`
- `full_menu`
- `search_menu_coverage`
- `search_review_coverage`
- `google_places_api_new`
- `tripadvisor`

Do not emit legacy packet fields such as `official_menu`, `delivery_menu`, `official`, `google_maps_api`, `menu_items_raw`, `menu_items_raw_structured`, `breakfast_brunch_signals`, or `newness_signals`.

## Quick Start

1. Read the user seed: restaurant name, address, city, optional Google Maps URL.
2. Create or refresh the packet skeleton with `/Users/zhouziqiang/.codex/skills/restaurant-data-capture/scripts/init_restaurant_packet.py`.
3. Run `/Users/zhouziqiang/.codex/skills/restaurant-data-capture/scripts/fetch_google_place.py` early to populate Google-sourced identity, geo, review signals, and raw reviews.
4. Gather remaining sources in the order defined in `/Users/zhouziqiang/.codex/skills/restaurant-data-capture/references/workflow.md`.
5. Fill the packet using the rules in `/Users/zhouziqiang/.codex/skills/restaurant-data-capture/references/schema.md`.
6. Preserve the distinction between `observed`, `normalized`, `extracted`, and `inferred`.
7. Finish by setting `field_status` and `quality.servingReadiness`.

## Workflow

### 1. Confirm identity first

Confirm that all gathered sources refer to the same branch.
Resolve branch ambiguity before collecting deeper fields.

Identity is good enough to proceed only when you can confidently assign:

- canonical restaurant name
- branch identity when relevant
- normalized address
- geo or branch location confirmation
- source URLs that clearly point to the same branch

### 2. Run Google Maps API enrichment early

Before any browser-based map search, check whether Google API data is already present.

1. If `field_status.google_places_api_new` is missing or `not_obtained`, run `/Users/zhouziqiang/.codex/skills/restaurant-data-capture/scripts/fetch_google_place.py --packet <packet_path>`.
2. The script should fetch Place Details and merge:
   - `identity.placeId`
   - `identity.geo`
   - `identity.phone`
   - `identity.website`
   - `identity.officialSocialAccounts`
   - `identity.addressNormalized`
   - `observed.opening_hours`
   - `observed.review_signals.google`
   - `observed.reviews_raw.google`
   - `observed.price`
3. If the API succeeds, skip Google Maps browser automation for fields already covered by the API.
4. If the API hits an access block or operational block, stop normal collection flow and handle the API problem first.

Google Places blocking rule:

- Treat `503`, `429`, timeouts, transport failures, key-loading issues, and other API access/availability blockers as a blocking incident for this run.
- First try to resolve the problem before proceeding. Examples: retry, inspect the script behavior, check env/key loading, reduce transient request concurrency, or fix an obvious request bug.
- If the block cannot be resolved in the current session, stop and report to the user. Do not continue to official, delivery, Tripadvisor, or Google Maps menu/photo collection after an unresolved Google Places blocker.
- Only continue to later sources when Google Places either succeeds or fails for a non-blocking reason such as `api_no_results` for the branch you are researching.

Decision rules:

- Prefer API data over browser-scraped map data for geo, rating, review count, hours, phone, website, and Google review capture.
- Collect official social account links for `identity.officialSocialAccounts`; do not collect or analyze social account content.
- Browser automation is still useful for menu inspection, photo inspection, or non-Google platforms.

### 3. Gather high-value sources in order

Start with Google Places, official sources, delivery menu platforms, Tripadvisor, and Google Maps menu/photo surfaces.

Delivery menu capture is mandatory for every packet when a delivery platform exists for the branch. Use MCP Playwright for Wolt, Uber Eats, Lieferando, and similar dynamic delivery sites. Do not skip delivery menus because Google Maps or official menus already exist. Those sources are complementary, not substitutes.

Read `/Users/zhouziqiang/.codex/skills/restaurant-data-capture/references/workflow.md` for the required order.

Other places do not need to be collected.

### 4. Extract by layer, not by convenience

Use the packet layers strictly.

- `observed`
  - direct facts and close-to-source evidence
- `normalized`
  - canonicalized restaurant and dish facts
- `extracted`
  - search-oriented derivations generated from evidence
- `inferred`
  - cautious hypotheses or soft interpretation

`inferred` is required and must be generated from the evidence already collected in the packet. It is the AI-synthesized frontend summary layer, not a scratchpad. Keep it populated with concise positioning and short descriptions derived from menu, review, identity, and operating evidence.

Rules:

- Never upgrade a review mention into a confirmed menu fact.
- Never present a common dish as a signature dish without evidence.
- Never use `extracted` to store canonical restaurant facts.
- Never use `normalized` to store free-form search expansions.

### 5. Build review data with the three-layer model

Review data must be split into:

- `observed.review_signals`
  - platform-level summaries such as rating and review count
- `observed.reviews_raw`
  - raw review evidence grouped by platform
- `extracted.reviewInsights`
  - dish-oriented search outputs such as `recommendedDishes` and `dishMentions`

Do not store raw reviews by language bucket.
Store them by platform first.
`observed.reviews_raw` is not a full review archive. Keep only reviews that provide concrete food-search evidence: explicit dish/food/preparation mentions, positive or negative dish-specific evaluation, platform-marked relevant snippets with food evidence, or food-evidence reviews from within the last 6 months. If more than 20 in-scope reviews are available for a platform, keep the most recent 20; otherwise keep the actual count. Do not keep generic service, ambience, staff, queue, price, or broad "good food" reviews without concrete food-search evidence.
Raw review items should keep only platform-original review evidence plus minimal selection metadata: `platform`, `rating`, `language`, `text`, `publishedAtRaw`, `dishTermsRaw`, and `selectionReason`. Do not store `reviewId`, `author`, `publishedAtIso`, `sourceUrl`, or AI-derived sentiment in `reviews_raw`; dish sentiment is aggregated into `extracted.reviewInsights`.

### 6. Build menu data with the three-layer model

Menu data must be split into:

- `observed.menus`
  - source-scoped menu evidence arrays with provenance, capture metadata, raw text, and item blocks
- `normalized.dishEntities`
  - canonicalized dish facts for downstream compilation

Current dish-compilation anchor rule:

- `observed.menus` is the primary source-evidence structure for menu capture and reprocessing
- `normalized.dishEntities` is the primary downstream menu/dish structure
- use `dishEntities.isPrimary` for menu/positioning centrality
- do not store signature state in the source packet; signature is derived later in `restaurantCatalog` from primary and recommended overlap
- `dishEntities` should use `canonicalName`, `nameZh`, `nameEn`, `nameDe`, `aliases`, `section`, `dishCode`, `isPrimary`, `dietaryTags`, `spiceLevel`, `availabilityStatus`, and `sourceRefs`
- Capture Google Maps menu photos as `observed.menus` when they contain first-hand menu text, especially Chinese labels missing from delivery or official web menus. Use `source: "google_maps_menu_photo"` and mark OCR/manual transcription uncertainty in item descriptions or menu notes.
- Do not capture standalone sauce/dip category items as menu evidence. Keep sauce words when they are part of a dish name, but exclude standalone sauces, dips, soy sauce, vinegar, chili oil, garlic oil, and `Sauces`/`Saucen` section items.

### 7. Generate search candidates conservatively

`extracted.searchTerms` may remain string-array buckets.
Do not turn it into a free-form synonym dump.

Allowed buckets:

- `restaurantAliases`
- `cuisineAliases`
- `dishAliases`
- `styleTerms`
- `occasionTerms`
- `exactTerms`
- `autocompleteTerms`
- `nonSpicyTerms`
- `spicyTerms`
- `languageHints`

Bucket rule:

- every bucket must be generated from explicit allowed-source rules
- do not include low-confidence free-form AI synonyms in v1

For `dishAliases`, allowed sources are:

- menu original names
- official translations
- deterministic pinyin or transliteration
- high-confidence review-derived dish names

### 8. Record source coverage in machine-readable form

For every material source, add a `source_packet` entry with:

- `type`
- `platform`
- `url`
- `sourceId`
- `accessStatus`
- `relevance`
- `accessMethod`
- `httpStatus`
- `contentType`
- `capturedAt`
- `snapshotPath`
- `notes`

If a source is found but not read, mark it as `found_not_accessed`.
If a source requires login, mark it as `login_required`.

### 9. Finish with publishability, not just completeness

Every important field group should end with:

- `status`: `confirmed`, `partial`, or `not_obtained`
- `failureReason`: controlled values from `/Users/zhouziqiang/.codex/skills/restaurant-data-capture/references/schema.md`

Then set `quality.servingReadiness`.

Use this publish contract:

- `ready`
  - identity and location are usable
  - at least one dish/menu evidence field is non-empty
  - at least one search-candidate bucket is non-empty
  - no unresolved identity/location conflict blocks serving compilation
- `partial`
  - packet is useful as source material but not yet ready to publish
- `blocked`
  - packet is too conflicted or too sparse to publish

Review coverage is helpful but is not a hard prerequisite for `ready`.

## Output Rules

- Produce one JSON file per restaurant.
- Use the template at `/Users/zhouziqiang/.codex/skills/restaurant-data-capture/assets/restaurant-source-packet.template.json`.
- Default output directory: `/Volumes/媒体/chopmap/data/restaurants/`
- Prefer the filename pattern `city__restaurant-slug__source-packet.json`.
- Keep the packet self-contained and reviewable without extra chat context.

## Access Rules

- Try direct access first for every website or platform page.
- If direct access fails or is materially incomplete because of dynamic rendering, anti-bot protection, interstitials, redirects, blocked content, login walls, or similar access friction, switch to Playwright before concluding the source is inaccessible.
- Apply this rule to official sites, delivery platforms, Tripadvisor, and Google Maps web surfaces.

## Search-Critical Must-Haves

Treat the following as required when building or refreshing a packet intended for search publication:

- `packet_meta`
- stable `seed`
- stable `identity`
- `observed.menus`
- `observed.review_signals`
- `observed.reviews_raw`
- `normalized.dishEntities`
- `normalized.cuisineCodes`
- `extracted.reviewInsights`
- `extracted.searchTerms`
- refined `field_status` for identity and search coverage
- `quality.servingReadiness`
- machine-readable `source_packet`

## Deferred / Non-Blocking Fields

These are useful but should not block a packet from being considered structurally aligned with V2:

- rich photo metadata
- extensive non-search-critical `inferred` fields
- exhaustive dietary and scene enrichment
- term-level provenance/confidence on every search candidate
- serving-layer signature derivation beyond `dishEntities.isPrimary` plus `reviewInsights.recommendedDishes`

## Scripts

### init_restaurant_packet.py

Generate a clean starter packet from a seed JSON file.
The script does not fetch data; it initializes the V2 structure and naming so later extraction stays consistent.

```bash
SKILL_DIR="/Users/zhouziqiang/.codex/skills/restaurant-data-capture"
python3 "$SKILL_DIR/scripts/init_restaurant_packet.py" \
  --seed "$SKILL_DIR/assets/restaurant-seed.example.json"
```

If `--output` is omitted, the script writes to `/Volumes/媒体/chopmap/data/restaurants/`.

### fetch_google_place.py

Fetch structured Google Maps data for a single restaurant via Places API.

```bash
SKILL_DIR="/Users/zhouziqiang/.codex/skills/restaurant-data-capture"
python3 "$SKILL_DIR/scripts/fetch_google_place.py" --packet /path/to/source-packet.json
python3 "$SKILL_DIR/scripts/fetch_google_place.py" --name "Lu Kitchen" --address "Simon-Dach-Straße 30, Berlin"
python3 "$SKILL_DIR/scripts/fetch_google_place.py" --name "Lu Kitchen" --address "Berlin" --raw
python3 "$SKILL_DIR/scripts/fetch_google_place.py" --packet /path/to/source-packet.json --dry-run
```

Requires `GOOGLE_PLACES_API_NEW_KEY` in environment or in `/Users/zhouziqiang/.codex/skills/restaurant-data-capture/scripts/.env`.

### batch_fetch_google_maps.py

Batch-fetch Google Maps data for multiple restaurants. Reads from CSV and/or existing packets.

```bash
SKILL_DIR="/Users/zhouziqiang/.codex/skills/restaurant-data-capture"
python3 "$SKILL_DIR/scripts/batch_fetch_google_maps.py" --csv restaurants.csv
python3 "$SKILL_DIR/scripts/batch_fetch_google_maps.py" --packets /Volumes/媒体/chopmap/data/restaurants/
python3 "$SKILL_DIR/scripts/batch_fetch_google_maps.py" --csv restaurants.csv --packets /Volumes/媒体/chopmap/data/restaurants/
python3 "$SKILL_DIR/scripts/batch_fetch_google_maps.py" --csv restaurants.csv --dry-run
python3 "$SKILL_DIR/scripts/batch_fetch_google_maps.py" --csv restaurants.csv --limit 5
```

CSV columns:

- `name_zh` / `中文名`
- `name_en` / `英文名` / `name`
- `address` / `地址`
- `city` / `城市`
- extra columns go to `seed.extra_fields`

## Deliverable

Return:

- the path to the JSON file you created or updated
- a short note on what is confirmed
- a short note on what still needs review or blocks `servingReadiness`
