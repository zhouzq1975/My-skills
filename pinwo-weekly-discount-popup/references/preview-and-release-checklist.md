# Preview and release checklist

Use this reference for local QA and production publication.

## Local preview

1. Start or reuse the repository's local development server.
2. Add a campaign-specific non-production preview key such as `?preview=weekly-discount-<restaurant>`.
3. Check affected locales; new campaigns and shared behavior changes require Chinese, English, and German.
4. Check desktop and 390px mobile for new campaigns or layout changes. For narrow copy corrections, verify wrapping and affected layouts without rebuilding the campaign.
5. Exercise close, backdrop, Escape, “暂时不要”, logged-out claim, logged-in claim, claimed-state CTA, and restaurant navigation as relevant to the change.
6. Confirm normal scheduling and suppression remain bypassed only by the development preview path, never in production.

## Focused validation

Run the current equivalents of:

```bash
node --test src/lib/weekly-discount-popup.test.mjs
npm run typecheck
npx eslint src/components/WeeklyDiscountPopup.tsx src/lib/weekly-discount-popup.mjs src/lib/weekly-discount-popup.test.mjs
git diff --check
```

If full lint fails in unrelated generated or pre-existing files, report the baseline separately. Do not silently fix or commit unrelated files.

## Release

Execute only authorized stages: a local commit is not permission to push, and a push request is not automatically permission for an additional deployment command. Check production-branch auto-deploy behavior before pushing and resolve unclear publication intent. Already granted authorization need not be requested again.

1. Inspect branch, remotes, `git status`, full diff, untracked files, and asset dimensions.
2. Stage the exact popup code, tests, and intended assets. Exclude Playwright output, local tooling directories, screenshots, and unrelated worktree changes.
3. Review the cached diff and run `git diff --cached --check`.
4. For a commit request, commit only the intended changes and verify the local commit. Stop there unless pushing is authorized.
5. For an authorized push, verify the remote commit. Distinguish push completion from automatic deployment status.
6. For an authorized deployment, wait for Vercel/GitHub success or Ready.
7. Verify affected production routes, images, and actual campaign content/behavior. HTTP 200 alone does not establish that the intended campaign or interaction is live.

Report the commit hash, deployment state, verified routes, campaign start time, and any unrelated files intentionally left untouched.
