# codex-crew

Persistent workflows, stack skills, hooks, and custom agent templates for Codex.

## Contents

- `skills/codex-crew/` - workflow replacement for the Claude Crew slash commands.
- `skills/{kotlin,kotlin-testing,exposed,gradle,trino,python,git}/` - tech-stack guidance.
- `hooks/hooks.json` - SessionStart and Stop hook configuration.
- `scripts/` - state CLI, hook implementations, and tests.
- `agents/` - custom agent templates for optional manual installation.

## Test

```bash
python3 scripts/test-hooks.py
```

## Workflow Prompts

- `crew analyze: ...`
- `crew plan: ...`
- `crew execute: ...`
- `crew review this plan`
- `crew build: ...`
- `crew cancel build`
- `crew measure twice: ...`
- `crew cancel measure twice`
- `crew code search: ...`
- `crew status`
- `crew save context`
- `crew restore context`
- `crew configure`
- `crew deepinit`

`crew configure` maps the old Claude Crew config command to Codex-native `AGENTS.md` guidance.

## Agent Templates

```bash
python3 scripts/install-agents.py
```
