# Pinwo Article Schema Reference

Primary repo: `/Volumes/媒体/chopmap`

Core files:

- `src/data/articles/types.ts`: article schema and admin override types.
- `src/data/articles/index.ts`: registry exports and public filtering.
- `src/data/articles/<slug>.ts`: one structured article per slug.
- `src/components/content/ArticlePage.tsx`: public renderer.
- `src/components/content/ArticleStructuredData.tsx`: Article JSON-LD.
- `src/data/homepage-editorial.ts`: homepage editorial slots derived from article slugs.
- `src/app/[locale]/stories/[slug]/page.tsx`: route lookup and metadata.
- `src/app/[locale]/stories/page.tsx`: public article index.
- `src/app/sitemap.ts` and `src/lib/seo.ts`: sitemap paths.

Treat `src/data/articles/types.ts` as the final authority. If this reference differs from the current exported types, follow the code and report the reference drift before publishing.

Required `ArticleEntry` fields:

- `slug`: lowercase kebab-case, stable URL slug.
- `kind`: `article`, `video`, or `about`.
- `primaryIntent`: one of `dish_guide`, `where_to_eat`, `restaurant_story`, `ingredient_explainer`, `coupon_news`, `about`.
- `publishedAt`, `updatedAt`: ISO-like strings.
- `author`, `readTime`: localized text.
- `locales.zh/en/de`: complete locale-native article content.
- `media.images`: every image needs `id`, `src`, localized `alt`, localized `caption`, `credit`, `aspect`, and `isHero`.
- `references.restaurantCatalogIds`: restaurant catalog identifiers only.
- `references.couponIds`: coupon ids only.
- `searchChips`: localized labels plus canonical backend `query`.
- `homepage`: hero/featured/pinned/order/card image metadata.
- `visibility`: published/hidden/noindex.

Locale content requirements:

- Include the current required UI strings plus `title`, `dek`, `author`, `date`, `readTime`, hero/logo fields, `seoTitle`, `seoDescription`, `aiSummary`, `tags`, `sections`, `quote`, `related`, and `faq`.
- Preserve `searchLinks` only when the article should open the shared search drawer from the page.
- Preserve `recommendation` only when the article has a restaurant/coupon CTA block.
- Use `hideHeading: true` for intro sections that should appear in body but not in table of contents.

Admin override compatibility:

- Public surfaces read Firestore `articleOverrides`.
- Overrides can hide articles, pin/order homepage cards, reorder tags, and apply selected string text/link/image corrections.
- Do not build article authoring flows in admin for first-scope CMS work.

Publishing checklist:

- Article has one primary intent.
- Trilingual content is complete and audience-appropriate.
- Search chips use canonical backend queries, not only localized display text.
- Restaurant/coupon references point to source-of-truth ids.
- Image rights are explicit.
- Metadata and AI-GEO summary are present.
- Article appears in registry, stories index, homepage slots if intended, and sitemap if public and indexable.
- Tests and typecheck pass.
- User-approved source copy and factual corrections remain intact unless the user explicitly requested editorial changes.
- Validation claims distinguish repository tests from browser, sitemap, deployment, and production checks that were not run.
