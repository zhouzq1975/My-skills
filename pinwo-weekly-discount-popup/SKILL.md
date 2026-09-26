---
name: pinwo-weekly-discount-popup
description: "Modify or validate Pinwo weekly coupon campaigns, copy, artwork, and claim behavior. Commit, push, and deployment follow separate authorization."
metadata:
  author: Ziqiang Zhou
  version: "1.0"
---

# Pinwo Weekly Discount Popup

Maintain only the requested parts of Pinwo's weekly coupon popup. A wording or CSS fix does not require a new campaign brief, regenerated artwork, or changes to campaign dates and claim logic. Preserve current product behavior.

## Choose the operating mode

- **Plan:** inspect the current campaign and propose content, visual hierarchy, timing, and behavior. Stay read-only.
- **Implement and preview:** update the requested campaign, assets, tests, and local preview. Do not commit or deploy unless asked.
- **Commit:** only when requested; validate and commit intended files locally. A commit request alone does not authorize pushing.
- **Push:** only when requested; push the intended branch and verify its remote commit. Check whether the branch triggers automatic deployment and surface that consequence if publication intent is unclear.
- **Deploy/publish:** only when requested or already authorized; perform the required release steps, wait for deployment, and verify production. Do not infer a production release from a local commit request.

When the request is ambiguous, complete the safe earlier mode and state what remains. A request to design a popup does not authorize production publication.

## Load only the needed references

- Read [references/campaign-brief.md](references/campaign-brief.md) when defining or replacing a campaign, its schedule, eligibility, or claim destination.
- Read [references/visual-and-copy-rules.md](references/visual-and-copy-rules.md) when creating or revising imagery, wording, hierarchy, or responsive layout.
- Read [references/preview-and-release-checklist.md](references/preview-and-release-checklist.md) when previewing, validating, committing, or deploying.

## Repository map

Verify these paths still own the behavior before editing:

- `src/components/WeeklyDiscountPopup.tsx`: localized content, artwork mapping, claim/auth interactions, preview routing, accessibility, and analytics.
- `src/components/WeeklyDiscountPopup.module.css`: desktop and mobile presentation.
- `src/lib/weekly-discount-popup.mjs`: campaign list, timing, selection, claim suppression, session suppression, and cooldown.
- `src/lib/weekly-discount-popup.test.mjs`: campaign and interaction invariants.
- `public/images/weekly-discount/`: campaign artwork and logos.

If ownership has moved, follow the current implementation rather than recreating the old structure.

## Stable product behavior

Preserve these defaults unless the user explicitly changes them:

- An eligible campaign may appear on the user's first visit to any page, not only the homepage.
- Dismissing with close, backdrop, Escape, or “暂时不要” starts a 12-hour global cooldown.
- Claiming while logged out opens the registration/login modal and completes the claim immediately after authentication.
- Claiming while logged in completes directly in the popup.
- After success, the CTA becomes the localized equivalent of “已领取，查看餐厅” and links to the restaurant page.
- A claimed campaign stops appearing. Override this only for an explicitly urgent or expiring campaign that the user wants to keep promoting after claim.
- Separate promotions remain separate campaign popups and separate creatives. Do not turn them into option 1/option 2 or imply that both can be received together.
- Keep campaign windows half-open: `startMs <= now < endMs`. Interpret human dates in `Europe/Berlin`, then store explicit UTC timestamps and test both boundaries.
- Keep Chinese, English, and German behavior equivalent even when the copy is not a literal translation.

Do not invent a coupon ID, restaurant slug, usage restriction, expiry, address, or campaign dates. Verify them from the repository, backend data available to the task, or user-provided evidence. Call out unresolved fields before a release.

## Implementation workflow

1. Inspect `git status`, the current campaign implementation, existing tests, and the relevant restaurant/coupon data. Preserve unrelated working-tree changes.
2. For a new or replaced campaign, capture the needed brief and distinguish coupon validity from popup display dates. Skip a new brief for a narrow correction.
3. Decide whether existing restaurant imagery can support the design. For generated or edited raster artwork, invoke the available image-generation skill and keep source provenance clear.
4. Update only affected configuration, locales, assets, preview keys, and tests. Do not regenerate unchanged assets or alter claim/auth logic for a wording correction. Flag material factual inconsistencies across locales before release.
5. Preview affected locales and layouts. A new campaign or shared layout/behavior change requires all three locales, desktop, and 390px mobile; a single-locale wording change needs focused rendering checks. Use actual rendered evidence.
6. Run focused validation. Treat unrelated full-repository failures as baseline and report them separately rather than broadening scope.
7. Execute only the authorized Git or deployment stages. If a requested push triggers an authorized automatic deployment, verify and report that deployment separately from the push.

## Completion standard

For implementation, completion means the requested change renders locally and affected checks pass. For commit-only work, completion is a verified local commit. For push-only work, verify the remote commit and report any deployment side effect separately. For an authorized release, also require successful deployment and live content/behavior verification; HTTP 200 or a successful push alone is not proof that the new campaign works.
