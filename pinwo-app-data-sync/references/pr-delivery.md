# App Data PR Delivery

## Branch And Commit

Start from current upstream `main` in a clean target clone.

- Branch: `partner/YYYY-MM-DD-<topic>`
- Commit: `data(partner): <concise change summary>`
- Push to the user's fork, never upstream `main`.

## PR Description

Include a per-file change table, evidence source/date/timezone, unresolved items, and truthful checkboxes for YAML parsing, id uniqueness, tag checks, scope, and diff validation.

Never claim a check passed unless it ran on the final committed diff.

## Delivery Boundary

After opening the PR:

1. Read back title, base/head, commit, and changed files.
2. Confirm only intended `data/restaurants/**` YAML files are present.
3. Report local validation separately from remote checks.
4. If a fork workflow is `action_required`, report that the upstream maintainer must approve it.
5. Treat Vercel fork authorization failures as upstream integration state.
6. Do not approve, review, merge, or close the PR.
