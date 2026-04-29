# Workflow Reference

Use `berlin__7-dumpling__source-packet.json` as the shape reference for packet JSON. When you refresh a restaurant packet, keep its top-level objects, menu structure, and field-status keys aligned to that sample.

## Source order

Work in this order unless the user provides a stronger source directly:

1. `google_places_api_new`
2. `official website`
3. `delivery_menu`
4. `tripadvisor`
5. `google_maps_menu_photo`

Delivery menu collection is mandatory whenever the branch has a live delivery platform presence. Collect Wolt, Uber Eats, Lieferando, or equivalent menus with MCP Playwright even if Google Maps menu photos or official menus already exist. The presence of another menu source does not waive delivery capture.

## What to collect from each source family

### 0. google_places_api_new

Use `scripts/fetch_google_place.py` early.

Prerequisite: `GOOGLE_PLACES_API_NEW_KEY` configured in `scripts/.env` or environment.

Collect:

- `identity.placeId`
- `identity.geo`
- `identity.addressNormalized`
- `identity.phone`
- `identity.website`
- `observed.opening_hours`
- `observed.review_signals.google`
- `observed.reviews_raw.google`
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
- use MCP Playwright for all delivery platform menu capture and branch confirmation
- do not rely on `curl` alone for delivery menus because many pages are JavaScript-rendered or anti-bot protected

Collect:

- menu availability
- menu completeness
- menu sections
- dish names
- source-scoped `observed.menus` evidence when possible

### 3. tripadvisor

Look for:

- confirmed Tripadvisor restaurant page for the same branch

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
- `is_new_opening`

Rules:

- do not leave `inferred` empty when the packet has usable evidence
- derive the text from menu, review, identity, location, and operating signals already in the packet
- keep the wording factual and compact
- do not invent facts that are not supported by the packet evidence
- if evidence is too sparse for a reliable summary, leave the packet in `partial` state and document the gap in `quality.needsReview`

## Practical constraints

- if a site does not load directly, start Playwright before marking it inaccessible
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
