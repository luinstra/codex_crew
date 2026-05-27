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

## Agent Templates

```bash
python3 scripts/install-agents.py
```
