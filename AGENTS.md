# Crew

## Repository Expectations

- This repo is a Codex plugin marketplace. The plugin root is `plugins/codex-crew/`.
- Keep Claude-specific files out of this repo unless they are clearly documented as migration references.
- Prefer Codex-native terms: skills, hooks, custom agents, and `AGENTS.md`.
- Share Crew workflow state in `.crew/` so Codex and Claude can coordinate on the same project.
- Loop state files are session-scoped; plans and context snapshots are intentionally shared.

## Quick Commands

| Command | Purpose |
| --- | --- |
| `python3 plugins/codex-crew/scripts/test-hooks.py` | Run script tests |
| `python3 plugins/codex-crew/scripts/install-agents.py` | Install custom agent templates |
| `ln -sf ../../scripts/post-commit-version-bump.sh .git/hooks/post-commit` | Install version bump hook |
| `find plugins/codex-crew -maxdepth 3 -type f \| sort` | Inspect plugin contents |

## Architecture

- `.agents/plugins/marketplace.json` exposes the plugin for marketplace-style installation.
- `plugins/codex-crew/.codex-plugin/plugin.json` is the plugin manifest.
- `plugins/codex-crew/skills/` contains Codex skills.
- `plugins/codex-crew/hooks/hooks.json` registers lifecycle hooks.
- `plugins/codex-crew/scripts/` contains deterministic hook and state scripts.
- `plugins/codex-crew/agents/` contains custom agent templates that must be installed separately.

## Verification

Before considering changes complete:

- Run `python3 plugins/codex-crew/scripts/test-hooks.py`.
- Check JSON manifests parse cleanly.
- Search for accidental Claude-only command references in Codex-facing files.
