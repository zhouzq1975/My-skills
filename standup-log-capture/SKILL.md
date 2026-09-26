---
name: standup-log-capture
description: "Create concise, repository-grounded handoff logs with verified state, decisions, and a concrete next-session entry point."
metadata:
  author: Ziqiang Zhou
  version: "1.2"
---

# Standup Log Capture

## Purpose

Write standup logs as AI handoff context. The log should let a future Codex session understand the larger project, today's exact position in that project, what changed, what decisions are settled, and where to resume without reconstructing everything from chat history.

Do not write a polished human status report. Write a compact project memory artifact grounded in repository evidence.

## Core Rules

- Start with the larger project context, not today's task list.
- Point to the governing spec, plan, or product document whenever one exists.
- Ground claims in local evidence: git status, diffs, recent commits, touched files, relevant docs, and validation output.
- Distinguish directly verified facts, user-provided facts, and conservative inference. Label inference explicitly.
- Preserve decisions and rejected approaches that future AI should not reopen casually.
- Include file paths for implementation entry points and docs future AI should read first.
- Distinguish completed work, uncommitted work, ignored files, external state, and remaining risk.
- Do not force-add ignored docs unless the user explicitly asks. If the log path is ignored, say so.
- Keep the log concise enough to be scanned, but specific enough to resume work.
- Never describe a command, test, deployment, database write, or browser check as completed unless current evidence supports it.

## Workflow

1. Identify the date and target log file.
   - Use the user's requested date if provided.
   - Otherwise use the local current date.
   - Prefer `docs/dev_logs/YYYY-MM-DD-<topic>-standup-log.md` unless the repo has another convention.
   - Reuse a same-day log for the same project and topic; do not merge unrelated tasks merely because their dates match.

2. Establish project context.
   - Read the current request and recent conversation context.
   - Find and read relevant project-level docs, usually under `docs/specs/`, `docs/plans/`, or `docs/notes/`.
   - If the user names the overall project, use that wording.
   - If the project context is unclear, infer conservatively from docs and repo state, and label the inference.

3. Gather repository evidence.
   - Confirm the repository root and active branch before interpreting paths or git state.
   - Use `git status --short` and scoped diffs. Check ignore status only for relevant paths with `git check-ignore`; do not enumerate all ignored build artifacts.
   - Inspect diffs for important touched files; do not infer behavior from filenames alone.
   - Check recent commits with `git log --oneline --decorate -10` when commit history matters to continuation.
   - Read existing standup logs for the current project when they exist.
   - Read validation output or rerun lightweight validation if the user expects current verification.
   - Scale evidence gathering to the session: do not run unrelated broad tests or inspect unrelated dirty files merely to fill the template.

4. Write or update the log.
   - Use the template in `references/log-template.md`.
   - Keep `Project Context` first.
   - Include `Next Session Start Here` near the end.
   - Use concrete file paths and command names.
   - Avoid vague entries such as "improved UI" without naming the surface and implementation files.
   - Preserve unrelated user changes as workspace context without attributing them to the current session.

5. Report outcome.
   - Give the log path.
   - Mention whether it is tracked, untracked, or ignored if relevant.
   - Mention validation performed or not performed.
   - If the user asked to commit, respect ignored-file policy and commit only the intended scope.

## Minimum Handoff Content

Keep project context, current verified state and validation limits, important decisions, and a concrete next-session entry point. These may be short paragraphs for a small task; eight fixed sections are not required.

Add external data state, product/design decisions, technical detail, or commit status only when useful for continuation. Preserve explicit negative facts such as "production database not touched" when they prevent a dangerous assumption. Never invent activity to fill a template.

If no Git repository exists, ground the log in actual files and observed actions and state that Git evidence is unavailable.

## What To Capture In "Next Session Start Here"

This is not a generic tomorrow task list. It is an AI resume guide:

- files to read first;
- docs/specs/plans to read first;
- current implementation state;
- likely next inspection or edit;
- decisions not to reopen unless requirements change;
- known failed approaches or visual dead ends;
- verification still needed.

Make the first recommended action executable and specific. Prefer "read X, inspect Y, then run Z" over "continue implementation."

## Reference

Read `references/log-template.md` when creating or materially updating a log.
