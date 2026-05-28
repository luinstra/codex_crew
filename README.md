# Crew

Crew is a Codex-native port of the Claude Crew workflow set. It packages:

- Persistent workflow hooks for build and measure-twice loops.
- A `crew` workflow skill that replaces the Claude slash commands.
- Tech-stack skills for Kotlin, Kotlin testing, Exposed, Gradle, Trino, Python, and Git.
- Custom agent templates for advisor, executor, reader, and documentation roles.

## Repository Shape

```text
codex_crew/
├── .agents/plugins/marketplace.json
└── plugins/
    └── codex-crew/
        ├── .codex-plugin/plugin.json
        ├── agents/
        ├── hooks/hooks.json
        ├── scripts/
        └── skills/
```

The actual Codex plugin lives in `plugins/codex-crew/`. The root marketplace file makes the repo shareable as a plugin marketplace.

## Install Locally

From Codex, add or install the marketplace using the repo path once this repository exists locally.

For development, the plugin root is:

```text
plugins/codex-crew
```

Codex will discover:

- Skills from `plugins/codex-crew/skills/`
- Hooks from `plugins/codex-crew/hooks/hooks.json`
- Plugin metadata from `plugins/codex-crew/.codex-plugin/plugin.json`

After installing or enabling the plugin, review and trust the bundled hooks with Codex's hook review flow. Codex intentionally requires trust review for plugin-bundled hooks.

## Custom Agents

Codex custom agents are not loaded from plugin manifests yet. Install the templates manually:

```bash
python3 plugins/codex-crew/scripts/install-agents.py
```

This copies templates into `~/.codex/agents/`:

- `crew_advisor`
- `crew_executor`
- `crew_reader`
- `crew_document_writer`

Use them only when you explicitly ask Codex to spawn subagents or name one of the agents.

## Workflow Prompts

Crew uses promptable workflows instead of Claude slash commands:

| Intent | Prompt |
| --- | --- |
| Plan | `crew plan: ...` |
| Execute | `crew execute: ...` |
| Review | `crew review this plan` |
| Build loop | `crew build: ...` |
| Measure twice | `crew measure twice: ...` |
| Status | `crew status` |
| Save context | `crew save context` |
| Restore context | `crew restore context` |
| Deepinit | `crew deepinit` |

State is stored under `.codex-crew/` in the active project.

## Development

Run the script tests:

```bash
python3 plugins/codex-crew/scripts/test-hooks.py
```

Inspect plugin files:

```bash
find plugins/codex-crew -maxdepth 3 -type f | sort
```

## Porting Notes

This repo intentionally does not try to copy Claude Crew one-to-one:

- Claude slash commands become a Codex workflow skill.
- Claude agent definitions become Codex custom agent templates.
- Claude `.crew/` state becomes `.codex-crew/` state.
- `CLAUDE.md` generation becomes `AGENTS.md` generation.
- Claude Stop hook continuation becomes Codex `decision: "block"` continuation.
