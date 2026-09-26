---
name: pinwo-report-delivery
description: "Generate and validate Pinwo operating reports, or retry authorized PDF, Drive, and Sites delivery without regenerating unchanged artifacts."
metadata:
  author: Ziqiang Zhou
  version: "1.0"
---

# Pinwo report delivery

## Scope

Use this workflow for a fresh weekly or monthly reporting cycle, or for retrying a failed Drive or Sites delivery. It does not authorize changing report business logic, rotating secrets, sending email, uploading HTML, or mutating unrelated Firestore data.

Weekly runs publish one consolidated internal report. Monthly runs publish one consolidated internal report plus merchant reports. Weekly delivery must not overwrite or delete monthly merchant reports.

## Fresh cycle

Use an explicit repository root and select exactly one cadence from the request. Weekly example:

```sh
PINWO_REPO="/Volumes/媒体/chopmap"
cd "$PINWO_REPO"
node reports/automation/run-reporting-cycle.mjs --cadence weekly
```

For a monthly cycle, run the same command with `--cadence monthly` instead. Do not run both unless requested.

Use `--as-of YYYY-MM-DD` only when the user requests a reproducible date. Preserve generated PDFs, manifests, and payloads so a failed delivery can be retried without regenerating.

## Required release gates

Complete every local gate before Drive upload or Sites sync. For a delivery-only retry, preserve the original PDFs, manifest, and payload: reuse prior passing checks only with recorded results tied to identical code, dependencies/environment, and artifact checksums. If that identity cannot be verified, rerun the relevant gates without regenerating reports. Never skip a failed or unverified gate.

```sh
cd "$PINWO_REPO"
node --test reports/automation/site-sync-core.test.mjs reports/automation/reporting-core.test.mjs reports/automation/pdf-delivery-core.test.mjs reports/automation/validation-core.test.mjs
node --check reports/automation/run-reporting-cycle.mjs
git diff --check -- reports/automation
node reports/automation/build-site-sync-payload.mjs --output /tmp/pinwo-structure-checked-payload.json
```

Then validate the Sites renderer:

```sh
cd "$PINWO_REPO/sites/jingying-data-report"
node --test tests/*.test.mjs
npm run build
```

The payload builder is the structure release gate. Do not sync when it fails. Validate the exact payload subsequently sent, not just a separately generated temporary file. Resolve subsequent report paths from PINWO_REPO, not the renderer working directory.

### Required report contract

Every report must contain, in order: conclusion, metric strip, trend analysis, trend chart, coupon analysis, coupon details, next-step recommendations, and data notes. The conclusion may use the historical ID `summary_story` or the current ID `summary`.

Every merchant report must also:

- use monthly cadence;
- provide exactly four within-month operating segments;
- include coupon data fields needed by the Sites introduction: coupon ID, offer, description, usage note, applicable merchant, expiry, and active status.

Customer structure and multi-store comparison are conditional modules. Their absence must not block release when the data is insufficient or the module does not apply.

If a required module is missing, stop before Sites sync. The sync endpoint upserts by report ID and does not delete old reports, so the current online report remains available. Fix the cause and retry only the failed stage.

## Delivery Authorization

A request to generate or preview reports does not authorize upload or publication. Execute only requested delivery destinations, using existing authorization without repeated confirmation. Creating recurring schedules is a separate task; this skill does not create one automatically.

## Drive delivery

Upload only PDFs listed in `reports/automated/drive-upload-manifest.json`. Deduplicate by filename, then re-list each destination and reconcile filenames, counts, and `application/pdf` MIME types.

- Weekly: `01-内部周报/YYYY-Www`
- Monthly: `02-内部月报/YYYY-MM` and `03-商户月报/YYYY-MM`

## Sites delivery

Read the existing project ID from `sites/jingying-data-report/.openai/hosting.json`. Sync `reports/automated/site-sync-payload.json` with the existing runtime SIWC bypass token in `X-Report-Sync-Token`. Never print, persist, rotate, or place the token in code or prompts.

A sync succeeds only when `ok=true` and the returned `reports` count equals the payload count. Stop on HTTP 401 instead of guessing or rotating credentials.

After sync, verify the production URL responds successfully and inspect the newest report:

- weekly: current consolidated report has its required sections and chart;
- monthly: current consolidated report plus one merchant report have the required sections; the merchant sample must show its coupon introduction and four month segments.

## Final status

Report generation, local gates, Drive, Sites sync, and online verification separately. State which stage failed and whether it can be retried without regeneration. Never describe a run as fully successful when only generation succeeded.
