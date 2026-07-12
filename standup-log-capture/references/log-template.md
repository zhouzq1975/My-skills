# AI Continuation Standup Log Template

Use this template for daily project logs that future AI sessions will read before continuing work. Keep sections with no content only when they carry useful "none / not touched / not verified" information.

```md
# <Project / Area> Standup Log

记录日期：YYYY-MM-DD
记录目的：AI continuation context, not human-facing status reporting.

## Project Context

- 当前项目：
  <Name the larger project. Example: Pinwo 网站整体升级改造.>

- 项目总目标：
  <State the broad goal that frames all daily work.>

- 总文档 / 必读文档：
  - Spec: `<path>`
  - Plan: `<path>`
  - Related log / note: `<path>`

- 当前阶段：
  <Example: visual-system convergence, detail-page implementation, data import cleanup, validation, etc.>

- 本日工作在总项目中的位置：
  <Explain how today's work advances the larger project.>

## Session Scope

- 起点：
  <What state the repo/product was in at the beginning of this work.>

- 用户明确目标：
  <Summarize user instructions that matter for continuity.>

- 证据边界：
  <State what was directly verified, what came from the user, and what remains inference.>

- 当前分支：
  `<branch>`

- 主要入口页面 / URL：
  - `<route or local URL>`

- 相关实现入口：
  - `<file>`

## Completed Work

### <Area 1>

- 做了什么：
- 关键文件：
- 关键行为变化：
- 重要细节：

### <Area 2>

- 做了什么：
- 关键文件：
- 关键行为变化：
- 重要细节：

## Product / Design Decisions

- 决策：
  <Decision and rationale.>
  适用范围：<routes/components/locales>

- 不再采用：
  <Rejected approach and why future AI should not repeat it.>

## Technical Decisions

- 决策：
  <Implementation choice.>
  相关文件：`<file>`
  注意事项：<constraints, edge cases, coupling>

## Data / External State

- 远端数据库：
  <Not touched / changed; include collection/doc identifiers if touched.>

- 生成文件 / 导入：
  <Exports, backups, generated assets, import commands.>

- 需要下次重新验证：
  <Anything that cannot be trusted from git alone.>

## Validation

- 已运行：
  - `<command>`：<result>

- 未运行：
  - `<command or browser check>`：<why not, risk>

- 已知风险：
  <Remaining uncertainty.>

- 证据说明：
  <Call out any user-reported or inferred state that was not independently verified.>

## Current Workspace State

- 已提交：
  - `<commit hash> <message>` or `None`

- 未提交但应保留：
  - `<file>`：<why>

- ignored 但重要：
  - `<file>`：<why; mention if not force-added>

- 新增资产：
  - `<file>`：<usage>

## Next Session Start Here

1. 先读：
   - `<project spec / plan>`
   - `<today log>`
   - `<primary implementation file>`

2. 再检查：
   - `<route / component / test / browser state>`

3. 建议下一步：
   - <Concrete next action.>

4. 不要重复做：
   - <Settled decision, rejected approach, or known trap.>
```

## Style Notes

- Prefer bullets over long paragraphs.
- Write enough context for an AI without conversation history.
- Include exact file paths; use repo-relative paths inside the log.
- Include exact commands and outcomes for validation.
- Keep visual language concrete: name the component, page, token, or CSS variable.
- Mark inference explicitly when project context is inferred from docs rather than stated by the user.
