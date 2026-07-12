---
name: pinwo-article-publishing
description: Publish or update Pinwo editorial content in the repository-managed structured trilingual ArticleEntry system. Use when turning a finished or near-finished draft into a Chinese/English/German Pinwo story page; adding article metadata, AI summary, FAQ, JSON-LD inputs, image credits, restaurant/coupon references, search chips, homepage placement, visibility, registry, sitemap, or article tests; or preparing a verified article release and handoff. Do not use for generic copywriting outside Pinwo, restaurant source-packet collection, admin-only corrections, or unstructured blog drafts that are not being integrated into the Pinwo repository.
metadata:
  author: Ziqiang Zhou
  version: 1.1
---

# Pinwo Article Publishing

Publish Pinwo articles through the repository's structured `ArticleEntry` system. Treat the admin dashboard as a post-publication correction layer for supported overrides, not as the primary authoring system.

## Repository And Contract

```bash
PINWO_REPO="/Volumes/媒体/chopmap"
```

Before editing:

1. Confirm the repository root, active branch, and current dirty state. Preserve unrelated user changes.
2. Read [`references/article-schema.md`](references/article-schema.md).
3. Read `$PINWO_REPO/src/data/articles/types.ts`; it is the final authority when this skill or reference has drifted.
4. Inspect `$PINWO_REPO/src/data/articles/index.ts` and the closest existing article of the same intent.
5. Identify one primary intent from the current `ArticleIntent` union. At this version: `dish_guide`, `where_to_eat`, `restaurant_story`, `ingredient_explainer`, `coupon_news`, or `about`.

If the repository contract differs materially from the skill, report the drift and follow the current type definition. Update this skill separately rather than encoding an obsolete field shape into a new article.

## Editorial Rules

- Preserve user-approved source text, factual corrections, grouping, and deliberate phrasing. Do not silently "improve" accepted copy.
- Treat Chinese, English, and German as locale-native editions. Adapt references and explanation for each audience without changing factual meaning.
- Keep one primary reader/search intent per article; secondary functions may support it but must not compete with it.
- Avoid generic AI tone, invented scene-setting, unsupported claims, and fake quotations.
- Keep canonical backend search queries separate from localized labels.
- Link restaurant facts through `restaurantCatalog` ids/slugs and coupon facts through coupon ids. Do not duplicate those systems as a new source of truth.
- Use source-grounded restaurant data when article claims depend on menu, branch, opening, or dish facts.

When the user supplies a final draft, make only the structural, locale, metadata, or explicitly requested editorial changes needed for publication. Surface any required schema-driven copy change before making it when it would alter meaning or voice.

## Publishing Workflow

### 1. Establish scope

Confirm the primary intent, target slug, publication state, homepage placement, source-language status, required locales, restaurant/coupon references, and available media rights. Ask only for information that cannot be derived safely from the draft and repository.

### 2. Build or update one article entry

Create or modify one file under `$PINWO_REPO/src/data/articles/` using the current `ArticleEntry` type and the nearest valid article as a structural example.

Complete all required top-level and `locales.zh/en/de` fields. Keep search chips canonical, references identifier-based, and homepage/visibility settings explicit. Use `hideHeading: true` only for body sections intentionally omitted from the table of contents.

### 3. Verify media rights

Every public image must include source, creator when known, license/permission state, usage classification, localized alt text, and caption. When rights are unclear, use `unknown_review_required`, keep the uncertainty visible in the handoff, and do not call the article publish-ready.

### 4. Wire public surfaces

Update the article registry and only the public surfaces affected by the article: story route/index, homepage editorial slots, sitemap, metadata, structured data, or tests. Do not change unrelated article infrastructure while publishing one article.

Respect Firestore `articleOverrides` compatibility. Do not overwrite or bypass supported hidden, homepage pin/order, tag-order, text, link, image, or content overrides without an explicit migration reason.

### 5. Validate proportionally

Discover current tests instead of assuming historical filenames:

```bash
cd "$PINWO_REPO"
rg --files | rg '(^|/)(articles|.*story.*content|seo).*\.test\.(mjs|js|ts|tsx)$' | sort
```

Run the smallest test set that covers the changed article, registry, SEO/sitemap, renderer, or structured-data behavior, then run:

```bash
npm run typecheck
```

Inspect the final diff for accidental source-copy rewrites, incomplete locales, broken ids/links, missing image rights, and unrelated workspace changes. Do not claim browser rendering, sitemap inclusion, or publication unless it was actually verified.

### 6. Hand off or release

Return the article path, slug and intent, locale status, references, media-rights status, public surfaces changed, tests run, and remaining risks. Commit, push, deploy, or change production/admin state only when the user asks.

## Conditional Skill Routing

Use another skill only when that subtask is actually in scope:

- `copywriting` for new marketing/editorial copy.
- `copy-editing` for revision of an existing draft.
- `ai-seo` for answer extraction and AI-search structure.
- `seo-audit` for indexing, sitemap, or technical SEO diagnosis.
- `schema` for structured-data changes or validation.
- `restaurant-data-capture` when restaurant facts require source-packet work.
- `standup-log-capture` when the user asks for a durable continuation log.

Do not load all related skills by default.
