# Workflow Reference

Use `/Volumes/媒体/chopmap/docs/specs/2026-06-07-restaurant-source-packet-v3-design.md` as the current design baseline and `berlin__7-dumpling__source-packet.json` as the shape reference for packet JSON. When you refresh a restaurant packet, keep its top-level objects, menu structure, and field-status keys aligned to that sample.

New packets should write `packet_meta.schemaVersion: 3`. Existing packets may still carry older numeric versions until migrated.

Before or during packet initialization, normalize `seed.extra_fields.category` and `seed.extra_fields.categoryCode` against `/Users/zhouziqiang/.codex/skills/restaurant-data-capture/assets/category-taxonomy.json`. Store the taxonomy code in `categoryCode` and the matching taxonomy `zh` label in `category`.

## Source order

Work in this order unless the user provides a stronger source directly:

1. `google_places_api_new`
2. `official website`
3. `delivery_menu`
4. `tripadvisor`
5. `google_maps_menu_photo`

Delivery menu collection is mandatory whenever the branch has a live delivery platform presence. Collect Wolt, Uber Eats, Lieferando, or equivalent menus with `browser:control-in-app-browser` even if Google Maps menu photos or official menus already exist. The presence of another menu source does not waive delivery capture.

## What to collect from each source family

### 0. google_places_api_new

Use `scripts/fetch_google_place.py` early.

Prerequisite: `GOOGLE_PLACES_API_NEW_KEY` configured in the process environment or in the user-only configuration file linked at `scripts/.env`.

Collect:

- `identity.placeId`
- `identity.geo`
- `identity.addressNormalized`
- `identity.phone`
- `identity.website`
- `observed.opening_hours`
- `observed.review_signals.google`
- `observed.reviews_raw.google` for retained food-specific reviews only
- `observed.price`
- a machine-readable `source_packet` entry for the API call

After this step:

- skip Google Maps browser automation for fields already covered by the API
- still proceed with Google Maps menu/photo inspection if needed

If this step fails for a non-blocking reason:

- fall back to Google Maps browser automation as needed
- mark `field_status.google_places_api_new` as `not_obtained` with the correct `failureReason`

If this step fails because of a blocker:

- treat `503`, `429`, timeouts, transport failures, key-loading problems, and similar access/availability issues as blocking
- try to resolve the problem first
- if unresolved, stop the run and report to the user
- do not continue to official, delivery, Tripadvisor, or Google Maps menu-photo collection after an unresolved Google Places blocker

### 1. official

Look for:

- official website
- official menu page or PDF
- official social account links

Collect:

- menu links
- menu sections
- dish names
- item-level prices when visible, stored as `observed.menus[].items[].priceRaw`
- official social account links/handles only, under `identity.officialSocialAccounts`

Do not collect from official websites:

- opening hours
- address
- phone
- geo
- rating or reviews
- service modes
- social account posts, videos, comments, notes, or other account content

Use Google Maps / Places API for those core identity and operating facts when available.
Common official social platforms include Instagram, Facebook, Xiaohongshu, YouTube, and TikTok. If there is no official website or no social link on the site, use only official or semi-official surfaces such as Google Maps business profile links, delivery platform merchant pages, or storefront/menu photos that visibly show official handles.

Menu collection rule:

- if both Chinese and non-Chinese official menus exist, capture the Chinese menu first
- use German and English menu versions as supporting confirmation

### 2. delivery_menu

Look for:

- Wolt
- Uber Eats
- Lieferando
- local delivery apps

Priority rule:

- check delivery platforms in this order: `Wolt`, `Uber Eats`, `Lieferando`
- if `Wolt` yields a confirmed branch and usable menu evidence, stop delivery-platform collection there
- if `Wolt` does not yield usable evidence, check `Uber Eats` next
- if `Uber Eats` does not yield usable evidence, check `Lieferando` last
- use `browser:control-in-app-browser` for all delivery platform menu capture and branch confirmation
- do not rely on `curl` alone for delivery menus because many pages are JavaScript-rendered or anti-bot protected

Collect:

- menu availability
- menu completeness
- menu sections
- dish names
- item-level prices when visible, stored as `observed.menus[].items[].priceRaw`
- source-scoped `observed.menus` evidence when possible

When deriving `normalized.dishEntities` from collected menu evidence, use the global taxonomy at `/Volumes/媒体/chopmap/data/taxonomies/dish-code-taxonomy.json` only as an auxiliary lookup table for assigning `dishCode`. If no exact/high-confidence taxonomy match exists, leave `dishCode` as `null`; do not create a restaurant-local slug, menu number, or platform item ID as `dishCode`.

Do not treat the dish-code taxonomy as an output schema for the source packet. Copy only the selected `dishCode` into `normalized.dishEntities`; do not copy taxonomy `canonicalName`, `labels`, `facets`, `mergeFrom`, `avoid`, or `pinyin` into packet fields. Keep `canonicalName`, `nameZh`, `nameEn`, `nameDe`, and `aliases` grounded in the restaurant's observed menu names, official translations, pinyin/transliterations, or high-confidence review-derived names.

### 3. tripadvisor

Look for:

- confirmed Tripadvisor restaurant page for the same branch
- use `browser:control-in-app-browser` for Tripadvisor confirmation

Collect:

- rating
- review count
- review snippets or raw reviews when accessible
- dish mentions from review text
- source_packet entry

Do not use Tripadvisor for core identity or operating facts when Google Places / official / delivery sources are available.

### 4. google_maps_menu_photo

If Google Maps API already succeeded, skip Google Maps browser reads for geo, rating, review count, hours, phone, and website.

Look for:

- Google Maps official/input menu, if available through API or page data
- Google Maps menu photos
- photo timestamps / freshness signals when visible

Other places do not need to be collected.

Collect:

- first-hand menu text visible in Google Maps menu/photo surfaces
- multilingual labels, especially Chinese labels
- item-level prices when visible, stored as `observed.menus[].items[].priceRaw`
- OCR/manual transcription notes when photo text is hard to parse
- source_packet entries for captured menu-photo evidence

### 5. inferred

After collecting and normalizing evidence from the source layers, generate `inferred` before finishing the packet.

`inferred` is the AI-synthesized frontend summary layer. It must be populated from the evidence already present in the packet, and it should be concise enough to display directly in UI surfaces.

Required keys:

- `positioning_summary`
- `short_description_zh`
- `short_description_en`
- `short_description_de`
- `operating_status`
- `is_new_opening`

Rules:

- do not leave `inferred` empty when the packet has usable evidence
- derive the text from menu, review, identity, location, and operating signals already in the packet
- keep the wording factual and compact
- do not invent facts that are not supported by the packet evidence
- for open new restaurants, keep `operating_status: "operating"` and set `is_new_opening: true`; leave `is_new_opening: null` when newness is unknown
- if evidence is too sparse for a reliable summary, leave `quality.servingReadiness` as `not_ready` and document the gap in `quality.needsReview`

When normalizing cuisine/type identity, keep `normalized.cuisineCodes` as the canonical cuisine taxonomy field.
Populate it only with codes from `/Users/zhouziqiang/.codex/skills/restaurant-data-capture/assets/cuisine-code-taxonomy.json`, and preserve the taxonomy-defined order rather than ad-hoc packet-local ordering.
For `extracted.cuisineTags`, use aligned multilingual tag triplets from `/Users/zhouziqiang/.codex/skills/restaurant-data-capture/assets/cuisine-tag-taxonomy.json` instead of inventing packet-local phrasing. Use taxonomy `codeHints` when they help keep tags aligned with `normalized.cuisineCodes`, but allow empty hints for scene-only tags.

`positioning_summary` should be treated as the normalization-style summary inside `inferred`, not as a duplicate of the localized short descriptions.

- write `positioning_summary` in English only
- keep it to one concise sentence
- lead with neighborhood or branch context when available
- identify the venue format explicitly
- summarize 2-3 core menu anchors at the cuisine/style level
- end with a short evidence phrase describing the strongest current menu coverage
- prefer a stable pattern such as:
  - `[Neighborhood/branch] [descriptor] focused on [anchor 1], [anchor 2], and [anchor 3], with [evidence phrase].`
- use the `short_description_zh` / `short_description_en` / `short_description_de` fields for more natural localized presentation copy
- do not let `positioning_summary` drift into review narration, marketing language, or free-form ambience commentary

## Current serving checks

Before marking a packet `ready`, verify it is useful for the repository's current source-packet-to-catalog serving path:

- `extracted.cuisineTags.zh`, `en`, and `de` are all non-empty and aligned by position.
- `normalized.dishEntities` has localized dish names where available; English/German fields should not contain Chinese-only text.
- If `normalized.dishEntities` has five or more entries, at least one entry has `isPrimary: true`; keep primary dishes selective, usually 3-12 entries.
- `extracted.searchTerms` has at least one useful `dishAliases`, `cuisineAliases`, or `styleTerms` bucket.
- `quality.servingReadiness` is exactly `ready` or `not_ready`; do not write legacy values such as `partial` or `blocked`.

## Practical constraints

- if a site does not load directly, start `browser:control-in-app-browser` before marking it inaccessible
- do not stop if Google Maps web content is inaccessible after Google Places succeeded and the missing fields are non-critical
- do not merge branches unless identity is clear
- do not treat one review mention as menu confirmation
- if Google Maps API returns data, do not redundantly scrape the same fields via browser
- do not publish a packet as `ready` unless identity/location and dish/menu/search coverage are all sufficient

## Review emphasis

Escalate these items into `quality.needsReview` or `quality.blockingReasons` when weak:

- search menu coverage
- search review coverage
- conflicting identity or branch attribution
- conflicting hours
- sparse dish evidence for a dish-first search product
