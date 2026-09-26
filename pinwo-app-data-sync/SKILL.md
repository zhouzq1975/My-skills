---
name: pinwo-app-data-sync
description: "Reconcile Pinwo evidence and live coupons into scoped partner app-database YAML changes or requested fork PRs. Keep the source repository read-only."
metadata:
  author: Ziqiang Zhou
  version: "1.1"
---

# Pinwo App Data Sync

## Purpose

Turn current, source-grounded Pinwo restaurant changes into narrowly scoped YAML pull requests for the public Pinwo app database in `Novawerk/berlin-chinese-food-map`.

Keep repositories and responsibilities separate:

- The Pinwo project repository is read-only during app-data delivery.
- The app database fork/clone is the only place where YAML, commits, and PR branches are created.
- The upstream maintainer approves workflows, reviews, and merges. Never perform those actions as part of this skill.

## Paths And Authority

Use explicit paths. Default Pinwo source repository:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/pinwo-app-data-sync"
PINWO_REPO="/Volumes/媒体/chopmap"
```

Discover or ask for a persistent app-database clone. If none exists and the user explicitly requests a PR, create or reuse a fork clone of `Novawerk/berlin-chinese-food-map`. A temporary clone is acceptable for a one-off run but must not be treated as durable state.

At the start of every run:

1. Read the current guide at `$PINWO_REPO/docs/PARTNER_GUIDE.md` (fall back to a case-insensitive matching filename only if needed).
2. Read the target clone's `data/restaurants/_schema.yaml`, `data/_tags.yaml`, `data/README.md`, and repository instructions.
3. Fetch upstream to inspect current `main`; fetching must not overwrite the working tree. Update or switch the checkout only when clean or when unrelated work is safely isolated. Never discard uncommitted changes.
4. If the guide and target schema disagree, follow the target schema and report the drift.

## Modes And Authorization

Infer the narrowest mode from the request:

- **Audit:** compare sources and report a reconciliation plan; remain read-only.
- **Prepare:** create YAML in an app-database branch and validate it; do not push or open a PR unless requested.
- **Submit PR:** create or reuse the fork, commit, push, and open the PR only when the user explicitly asks to submit or create a PR.

Submitting a PR does not authorize approving Actions, reviewing, merging, changing upstream settings, fixing Vercel fork authorization, or running the target Firestore sync. Stop after delivery and report any `action_required` maintainer gate.

## Source Hierarchy

- Restaurant identity, branch, address, coordinates, Place ID, operating evidence, names, and taxonomy evidence: current Pinwo Source Packet V3 files under `$PINWO_REPO/data/restaurants/*.json`.
- Coupon status and expiry: live Pinwo Firestore `coupons` joined to `merchants`, exported for the current Berlin date with `$PINWO_REPO/scripts/export-active-valid-coupons.cjs`.
- Existing app ids, filenames, fields, and discount state: latest upstream target YAML.
- A direct user or merchant correction is authoritative input, but record its confirmation date and re-check cheap, drift-prone machine state before submission.

Never treat a cached coupon export, Source Packet `servingReadiness`, review text, or a same-name restaurant as sufficient proof of current coupon or branch state.

## Reconciliation

Read [references/reconciliation.md](references/reconciliation.md) before deciding or generating changes.

For coupon work, export a fresh snapshot outside the read-only Pinwo source repository. The current exporter accepts the destination as its first positional argument; verify that contract if the script changes. Use existing target dependencies, running `npm ci` only when missing or inconsistent with the lockfile.

```bash
EXPORT_DIR="$(mktemp -d /tmp/pinwo-coupon-audit.XXXXXX)"
COUPON_EXPORT="$EXPORT_DIR/active-valid-coupons.json"
(cd "$PINWO_REPO" && node scripts/export-active-valid-coupons.cjs "$COUPON_EXPORT")
```

Set TARGET_REPO to the verified app-database clone, then run:

```bash
node "$SKILL_DIR/scripts/reconcile_app_coupons.mjs" \
  --source-repo "$PINWO_REPO" \
  --target-repo "$TARGET_REPO" \
  --coupon-export "$COUPON_EXPORT"
```

The script is audit-only. It never edits YAML or touches Git. Review every `activate`, `deactivate`, and `unmatched` result before changing files.

Match restaurants in this order:

1. frozen target filename/id;
2. exact Google Place ID;
3. one unambiguous coordinate match to the same branch;
4. name and address evidence reviewed manually.

Do not create a coupon-only change for a restaurant absent from the app database. Put the restaurant addition in a separate PR first.

## YAML Changes

- Modify only `data/restaurants/**`.
- Never delete or rename an existing restaurant file/id.
- Never modify `data/_tags.yaml`, app code, workflows, scripts, dependencies, generated data, or binary assets.
- Do not add `featured`, `editorialNote`, Google-generated fields, ratings, hours, photos, or runtime counters.
- Preserve existing field order and formatting.
- For a closed venue use `hidden: true` with dated evidence; never delete the file.
- For a relocation preserve the id, update address and coordinates, clear `placeId`, and explain the move in the PR.
- For a replacement business hide the old file and create a new id.

Coupon activation:

```yaml
hasDiscount: true
discountInfo:
  zh: "一句常驻优惠文案"
  en: "Short faithful translation"
```

Keep Chinese copy to one factual line, normally no more than 20 Chinese characters. Put dates and detailed terms in PR evidence, not YAML. When several coupons apply to one merchant, summarize them without inventing or dropping a material condition. Correct obvious translation errors only when the intended meaning is unambiguous; otherwise leave `en` empty and flag review.

Coupon removal requires both `hasDiscount: false` and complete removal of the `discountInfo` block.

## PR Scope And Validation

Use one theme per PR. Keep restaurant additions, coupon changes, and closures separate unless the user explicitly approves a combined scope. Prefer no more than about 30 files.

Before committing, run in the target clone:

```bash
cd "$TARGET_REPO/scripts/sync-to-firestore"
npm run check:tags
```

Return to "$TARGET_REPO" before the following repository-wide scope checks. Also verify:

- every target YAML parses;
- ids are unique across district folders;
- `git diff --check` passes;
- `git status --porcelain -- . ':!data/restaurants'` has no output;
- the diff contains exactly the reviewed files and no deletions or renames;
- every activation/removal still agrees with the fresh evidence used in the PR.

Read [references/pr-delivery.md](references/pr-delivery.md) before committing, pushing, or creating a PR.

## Report

Return the source snapshot date/timezone, reconciliation counts, unresolved matches, exact files changed, validation results, commit/PR URL when submitted, remote checks separately from local validation, and any maintainer-only action still outstanding.
