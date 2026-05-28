---
name: crew
description: >-
  Use when running Crew analyze, plan, execute, review, build/cancel, measure-twice, search, status, context, configure, or deepinit.
---

# Crew Workflows

Read [Workflow Reference](references/workflows.md) before running a Crew workflow.

## Core Rules

- Keep shared Crew state in `.crew/` and plans in `.crew/plans/`.
- Loop state files are session-scoped from Codex or Claude session/thread IDs; plans and context snapshots are intentionally shared with Claude Crew.
- Run verification before declaring implementation work complete.
- Use Codex subagents only when the user explicitly asks for subagents, delegation, parallel agents, or a named custom agent.
- For script commands, resolve `../../scripts/crew-state.py` relative to this `SKILL.md` file.

## Prompt Map

| Old Claude command | Codex prompt |
| --- | --- |
| `/crew:analyze "target"` | `crew analyze: target` |
| `/crew:plan "task"` | `crew plan: task` |
| `/crew:execute plan` | `crew execute: plan` |
| `/crew:review plan` | `crew review this plan` |
| `/crew:build "task"` | `crew build: task` |
| `/crew:cancel-build` | `crew cancel build` |
| `/crew:measure-twice "task"` | `crew measure twice: task` |
| `/crew:cancel-measure-twice` | `crew cancel measure twice` |
| `/crew:code-search "query"` | `crew code search: query` |
| `/crew:status` | `crew status` |
| `/crew:save-context` | `crew save context` |
| `/crew:restore-context` | `crew restore context` |
| `/crew:crew-config` | `crew configure` |
| `/crew:deepinit` | `crew deepinit` |

## Quick Commands

```bash
python3 ../../scripts/crew-state.py show bl
python3 ../../scripts/crew-state.py show mt
python3 ../../scripts/crew-state.py deactivate bl --reason "User cancelled"
python3 ../../scripts/crew-state.py deactivate mt --reason "User cancelled"
```

## Workflow Index

- Analyze, plan, execute, review, build loop, measure-twice, status, save/restore context, configure, and deepinit are documented in the workflow reference.
- `crew configure` is the Codex-native replacement for `crew-config`: create or update project-local `AGENTS.md`; ask before changing global Codex guidance.
- `crew code search` uses local search first; delegate to `crew_reader` only when the user explicitly asks for subagents or names the agent.
