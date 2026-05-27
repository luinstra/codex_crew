---
name: codex-crew
description: Use this skill for Codex Crew workflows: planning a non-trivial task, executing an existing plan, running a verified build loop, running a measure-twice plan-review loop, saving or restoring working context, checking crew status, or creating AGENTS.md project guidance. Trigger when the user says "crew", "plan this", "execute the plan", "build loop", "measure twice", "save context", "restore context", "deepinit", or asks for persistent verified work.
---

# Codex Crew Workflows

This skill ports the Claude Crew workflow model to Codex. It provides promptable workflows rather than slash commands.

## Core Rules

- Do simple work directly.
- For multi-step work, maintain an explicit plan or task list.
- Use Codex subagents only when the user explicitly asks for subagents, delegation, parallel agents, or a named custom agent.
- Keep state in `.codex-crew/`.
- Store plans in `.codex-crew/plans/`.
- Run verification before declaring implementation work complete.
- When running bundled scripts, resolve `../../scripts/crew-state.py` relative to this `SKILL.md` file.

## Replacing Slash Commands

Use these prompt forms:

| Old Claude command | Codex prompt |
| --- | --- |
| `/crew:plan "task"` | "Use Codex Crew to plan: task" |
| `/crew:execute plan` | "Use Codex Crew to execute: plan" |
| `/crew:review plan` | "Use Codex Crew to review this plan" |
| `/crew:build "task"` | "Use Codex Crew build loop for: task" |
| `/crew:measure-twice "task"` | "Use Codex Crew measure twice for: task" |
| `/crew:status` | "Use Codex Crew status" |
| `/crew:save-context` | "Use Codex Crew save context" |
| `/crew:restore-context` | "Use Codex Crew restore context" |
| `/crew:deepinit` | "Use Codex Crew deepinit" |

## Status

Run:

```bash
python3 ../../scripts/crew-state.py show bl
python3 ../../scripts/crew-state.py show mt
```

Then check whether `.codex-crew/context-snapshot.md` exists.

Report:

- Build loop: active or inactive, iteration, task.
- Measure-twice loop: active or inactive, iteration, task, plan path.
- Context snapshot: present or absent.

## Planning Workflow

Use when the user asks to plan or when implementation would benefit from a written plan.

1. If the request names a file path, read it and treat it as requirements.
2. Otherwise ask only the missing product or preference questions needed to plan safely.
3. Inspect the codebase yourself for implementation facts.
4. Write the plan to `.codex-crew/plans/{descriptive-name}.md`.
5. Return a concise summary and the plan path.

Plan format:

```markdown
# Plan: {Name}

## Context
- Original request
- Relevant codebase facts
- Decisions made

## Objectives
- Core objective
- Definition of done

## Scope
- In scope
- Out of scope

## Tasks
1. [Task] - [Acceptance criteria]
2. [Task] - [Acceptance criteria]

## Risks
| Risk | Mitigation |
| --- | --- |

## Verification
- Commands and checks to run
```

## Execute Workflow

Use when the user asks to execute a plan or task.

1. If the user references a plan, locate it under `.codex-crew/plans/` and read it.
2. Implement the work directly unless the user explicitly asks for subagents.
3. If subagents are explicitly requested, use the custom agent guidance below.
4. Run the verification from the plan, or the closest repo-native checks.
5. Summarize changes, verification, and any residual risks.

## Review Workflow

Use a code-review stance. Findings come first.

For plans:

- Check clarity, completeness, testability, dependencies, edge cases, and whether a worker could execute without guessing.
- Verdicts:
  - `APPROVED`: Ready to execute.
  - `REVISE`: Needs changes. Classify each issue as `[BLOCKING]` or `[MINOR]`.
  - `REJECT`: Fundamental approach problem.

For implementation:

- Prioritize correctness, behavior regressions, security, performance, and missing tests.
- Cite files and line numbers.
- Avoid style-only feedback unless it hides a concrete risk.

## Build Loop

Use for persistent implementation work that should continue until verified.

Start by activating state:

```bash
python3 ../../scripts/crew-state.py init bl --prompt "<task>"
```

Then:

1. Implement the task.
2. Run builds/tests.
3. Review the diff against the original request.
4. If complete, deactivate:

```bash
python3 ../../scripts/crew-state.py deactivate bl --reason "Verified complete"
```

If the Stop hook interrupts, continue from the hook message. Do not call the task complete until the loop is deactivated.

## Measure-Twice Loop

Use when the user wants a plan to be reviewed and revised before execution.

Activate:

```bash
python3 ../../scripts/crew-state.py init mt --task "<task>" --auto-plan
```

Then:

1. Generate the plan at the path printed by the command.
2. Review the plan using the Review Workflow.
3. If there are `[BLOCKING]` issues, revise the plan and review again.
4. If approved or only `[MINOR]` issues remain, deactivate:

```bash
python3 ../../scripts/crew-state.py deactivate mt --reason "Plan approved"
```

5. Present the final plan and ask whether to execute.

## Save Context

Create `.codex-crew/context-snapshot.md`:

```markdown
# Context Snapshot
Saved: {UTC timestamp}

## Current Task
{specific task}

## Progress
- [x] Completed
- [ ] Pending

## Key Decisions
- {Decision}: {Rationale}

## Files Modified This Session
- `path` - {what changed}

## Important Context
{gotchas, user preferences, risks}

## Next Steps
1. {next action}
```

## Restore Context

If `.codex-crew/context-snapshot.md` exists:

1. Read it.
2. Summarize current task, progress, decisions, modified files, and next steps.
3. Rename it to `.codex-crew/context-snapshot.restored.md` after restoration.

If absent, tell the user no snapshot exists.

## Deepinit

Create Codex project guidance using `AGENTS.md`, not `CLAUDE.md`.

1. Map the project structure.
2. Create a root `AGENTS.md` with setup, commands, architecture, and project conventions.
3. Add nested `AGENTS.md` or `AGENTS.override.md` only for important subtrees with distinct conventions.
4. Keep total guidance focused. Codex loads layered AGENTS files before work, so avoid generic boilerplate.

Root template:

```markdown
# {Project Name}

## Repository Expectations
- {command or rule}

## Quick Commands
| Command | Purpose |
| --- | --- |

## Architecture
{brief summary}

## Key Patterns
{actionable patterns}

## Verification
{required checks}
```

## Custom Agents

This repo includes custom agent templates under `agents/`. Install them with:

```bash
python3 scripts/install-agents.py
```

Use them only when the user explicitly asks for subagents or names one:

- `crew_advisor`: architecture, debugging, planning, and review.
- `crew_executor`: focused implementation after the approach is decided.
- `crew_reader`: read-only codebase and documentation search.
- `crew_document_writer`: documentation work.

If custom agents are not installed, use built-in `explorer` and `worker` roles where appropriate.
