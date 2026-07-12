---
name: standup-log-capture
description: Create or update repository-grounded daily standup, dev, handoff, or continuation logs intended to let a future AI session resume work. Use when the user asks for a standup log, dev log, handoff record, AI continuation context, or a durable record of today's repository work with specs, decisions, commits, diffs, validation, external state, and next-session entry points. Do not use for a casual chat recap, meeting minutes, a human performance/status report, release notes, or a generic project summary that does not need AI-resumable repository context.
metadata:
  author: Ziqiang Zhou
  version: 1.1
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
   - If a same-day log exists, update it rather than creating a duplicate unless the user asks for a new log.

2. Establish project context.
   - Read the current request and recent conversation context.
   - Find and read relevant project-level docs, usually under `docs/specs/`, `docs/plans/`, or `docs/notes/`.
   - If the user names the overall project, use that wording.
   - If the project context is unclear, infer conservatively from docs and repo state, and label the inference.

3. Gather repository evidence.
   - Confirm the repository root and active branch before interpreting paths or git state.
   - Run `git status --short --ignored` and `git diff --stat` when the worktree is relevant.
   - Inspect diffs for important touched files; do not infer behavior from filenames alone.
   - Check recent commits with `git log --oneline --decorate -N` when commit history matters to continuation.
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

## Required Sections

Every log must include:

- `Project Context`
- `Session Scope`
- `Completed Work`
- `Product / Design Decisions`
- `Technical Decisions`
- `Validation`
- `Current Workspace State`
- `Next Session Start Here`

Use `Data / External State` when the work touched remote databases, imports, generated exports, APIs, production config, or other non-git state.

Omit optional subsections that add no continuation value. Do not invent "none" entries merely to make the log look complete, except where an explicit negative fact such as "production database not touched" prevents a dangerous assumption.

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
