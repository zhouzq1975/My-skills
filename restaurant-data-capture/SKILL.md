---
name: restaurant-data-capture
description: Create or refresh source-grounded Pinwo restaurant Source Packet V3 JSON files under data/restaurants. Use when collecting one or more restaurant branches from Google Places, official sites, delivery menus, Tripadvisor, or Google Maps menu photos; normalizing identity, menu, review, cuisine, dish, and search evidence; or deciding whether a packet is ready for restaurantCatalog/search publication. Do not use for editing restaurant UI, directly authoring restaurantCatalog serving documents, generic restaurant research, or publishing editorial articles.
metadata:
  author: Ziqiang Zhou
  version: 1.3
---

# Restaurant Data Capture

Build or refresh evidence-rich restaurant source packets. The packet is the local source-of-truth layer for later compilation; it is not a frontend serving document.

Default to one branch and one JSON file unless the user explicitly requests a batch. Resolve branch ambiguity before deep collection.

## Paths And Required References

Set paths explicitly because the current working directory may differ from the Pinwo repository:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/restaurant-data-capture"
PINWO_REPO="/Volumes/媒体/chopmap"
```

Before creating or materially refreshing a packet:

1. Read [`references/workflow.md`](references/workflow.md) for source order, blocking rules, and source-specific collection policy.
2. Read [`references/schema.md`](references/schema.md) for field shapes, controlled values, and publishability rules.
3. Inspect the current repository baseline at `$PINWO_REPO/docs/specs/2026-06-07-restaurant-source-packet-v3-design.md` and the structural sample at `$PINWO_REPO/data/restaurants/berlin__7-dumpling__source-packet.json`.
4. If the repository contract and this skill disagree, stop and report the drift before writing packet data. Do not silently choose an older shape.

Use the bundled template at `assets/restaurant-source-packet.template.json` for new packets.

## Invariants

- Write `packet_meta.schemaVersion: 3` for new or refreshed packets.
- Preserve the evidence layers: `observed`, `normalized`, `extracted`, and `inferred`.
- Keep evidence and provenance in the source packet; derive `restaurantCatalog` later.
- Use only taxonomy values from the bundled category/cuisine assets and the repository dish-code taxonomy.
- Never turn a review mention into a confirmed menu fact.
- Never invent a signature dish, dish code, cuisine code, source, review, price, or operating fact.
- Keep opening hours exclusively from Google Places / Google Maps API in the packet.
- Mark unresolved gaps and conflicts instead of smoothing them over in prose.

The required `field_status` keys are:

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

Do not emit legacy keys or structures documented as obsolete in `references/schema.md`.

## Browser And Access Policy

Use direct HTTP or APIs when they provide complete, attributable data. When a dynamic page, redirect, anti-bot screen, interstitial, or login wall prevents reliable access, use the available `browser:control-in-app-browser` skill before declaring the source inaccessible.

Use the in-app browser for Wolt, Uber Eats, Lieferando, Tripadvisor, Google Maps menu/photo surfaces, and comparable dynamic pages. Do not hardcode a plugin-cache version path; invoke the currently available browser skill by name.

Record access outcomes in `source_packet`, including sources that were found but not accessed, required login, failed, or referred to another branch.

## Workflow

### 1. Confirm branch identity

Confirm canonical name, branch, normalized address, geo or location evidence, and source URLs that refer to the same branch. Do not merge evidence across branches.

### 2. Initialize or inspect the packet

For a new packet, run:

```bash
python3 "$SKILL_DIR/scripts/init_restaurant_packet.py" \
  --seed "$SKILL_DIR/assets/restaurant-seed.example.json"
```

For an existing packet, inspect its schema version and current evidence before fetching. Preserve valid evidence and provenance; do not replace the whole file merely to refresh one source.

### 3. Run Google Places enrichment early

When `field_status.google_places_api_new` is missing or `not_obtained`, run:

```bash
python3 "$SKILL_DIR/scripts/fetch_google_place.py" --packet /path/to/source-packet.json
```

Use API results for place ID, geo, normalized address, phone, website, official social links, opening hours, Google rating/review signals, retained food-specific reviews, and price level.

Treat `429`, `503`, timeouts, transport failures, and key-loading failures as operational blockers. Try a bounded retry or fix an obvious local configuration/request issue. If unresolved, stop the collection run and report the blocker; do not continue into later sources. `api_no_results` for a correctly identified branch is non-blocking and may proceed to browser-based fallback.

The API key must come from the process environment or the user-only configuration file linked at `scripts/.env`. Never print, copy into packet data, or include the key in logs or reports.

### 4. Gather remaining sources in order

Follow the exact source order and stop conditions in `references/workflow.md`:

1. Google Places API
2. official website/menu/social links
3. one usable delivery menu, checked in the order Wolt -> Uber Eats -> Lieferando
4. Tripadvisor
5. Google Maps menu/photo evidence

Delivery menu capture is required when a live branch listing exists. Other sources complement rather than replace menu evidence.

### 5. Populate layers without crossing boundaries

- `observed`: source-scoped identity, menu, price, review, and access evidence.
- `normalized`: canonical cuisine codes and restaurant-specific dish entities.
- `extracted`: multilingual cuisine tags, review insights, and conservative search candidates.
- `inferred`: concise consumer-facing positioning and localized descriptions derived from packet evidence.

Keep detailed menu, review, taxonomy, and allowed-value rules in `references/schema.md` and `references/workflow.md`. In particular:

- retain visible item prices as source-formatted `priceRaw`;
- assign `dishCode` only from `$PINWO_REPO/data/taxonomies/dish-code-taxonomy.json`, otherwise use `null`;
- keep `extracted.cuisineTags.zh/en/de` position-aligned and sourced from `assets/cuisine-tag-taxonomy.json`;
- keep raw food-specific reviews grouped by platform;
- use `dishEntities.isPrimary` selectively when there are at least five dishes;
- keep `inferred.operating_status: "operating"` for an open new restaurant and use `inferred.is_new_opening: true` as the new-opening signal.

Do not put workflow commentary, review notes, or data-cleaning language in consumer-facing `inferred` copy.

### 6. Decide publishability

Set every important field group to `confirmed`, `partial`, or `not_obtained` with a controlled `failureReason` when needed. Then set `quality.servingReadiness` to exactly:

- `ready` when identity/location are usable, menu or dish evidence exists, search candidates exist, aligned trilingual cuisine tags exist, and no identity/location conflict blocks compilation;
- `not_ready` when the branch is unopened, permanently closed, materially conflicted, or too sparse for reliable compilation.

Review coverage helps quality but is not a hard prerequisite for `ready`. Record remaining uncertainty in `quality.needsReview` or `quality.blockingReasons`.

### 7. Validate the finished packet

Before returning:

- parse the JSON successfully;
- compare top-level shape and `field_status` keys with the current V3 sample;
- check taxonomy membership and trilingual tag alignment;
- check `source_packet` coverage and provenance;
- check readiness against `references/schema.md` rather than intuition;
- inspect the diff so unrelated packet evidence was not removed.

## Scripts

Single-place lookup and merge:

```bash
python3 "$SKILL_DIR/scripts/fetch_google_place.py" --packet /path/to/source-packet.json
python3 "$SKILL_DIR/scripts/fetch_google_place.py" --name "Lu Kitchen" --address "Berlin" --raw
python3 "$SKILL_DIR/scripts/fetch_google_place.py" --packet /path/to/source-packet.json --dry-run
```

Batch collection only when the user explicitly requests it:

```bash
python3 "$SKILL_DIR/scripts/batch_fetch_google_maps.py" --csv restaurants.csv --dry-run
python3 "$SKILL_DIR/scripts/batch_fetch_google_maps.py" --packets "$PINWO_REPO/data/restaurants/" --limit 5
```

## Output

- Write one self-contained JSON file per branch.
- Default to `$PINWO_REPO/data/restaurants/city__restaurant-slug__source-packet.json`.
- Return the created or updated path, confirmed coverage, unresolved review items, readiness value, and validation performed.
- Do not publish to `restaurantCatalog`, Firestore, or Typesense unless the user separately asks for that downstream action.
