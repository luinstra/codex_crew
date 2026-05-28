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

Clone the marketplace repo, then add or install the marketplace from Codex using the local checkout:

```bash
git clone https://github.com/luinstra/codex_crew.git
cd codex_crew
```

Marketplace file:

```text
.agents/plugins/marketplace.json
```

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
| Analyze | `crew analyze: ...` |
| Plan | `crew plan: ...` |
| Execute | `crew execute: ...` |
| Review | `crew review this plan` |
| Build loop | `crew build: ...` |
| Cancel build loop | `crew cancel build` |
| Measure twice | `crew measure twice: ...` |
| Cancel measure twice | `crew cancel measure twice` |
| Code search | `crew code search: ...` |
| Status | `crew status` |
| Save context | `crew save context` |
| Restore context | `crew restore context` |
| Configure project | `crew configure` |
| Deepinit | `crew deepinit` |

State is stored under `.codex-crew/` in the active project.

`crew configure` is intentionally not a direct copy of Claude Crew's `/crew:crew-config`. In Codex, the project guidance path is `AGENTS.md`; use `crew configure` or `crew deepinit` to create or update project-local guidance instead of copying Claude-specific config.

## SessionStart Hook Output

The SessionStart hook is quiet by default. It emits context only when Crew state needs attention, such as an active build loop, an active measure-twice loop, another active Crew session, or a saved context snapshot.

To restore generic Crew guidance and stack-skill hints on every session start, launch Codex with:

```bash
CODEX_CREW_SESSION_START=verbose
```

## Version Bump Hook

Install the local Git hook if you want plugin changes to bump `plugins/codex-crew/.codex-plugin/plugin.json` automatically after commits:

```bash
ln -sf ../../scripts/post-commit-version-bump.sh .git/hooks/post-commit
```

The hook follows conventional commit subjects: `feat:` triggers a minor bump, breaking-change markers trigger a major bump, and other plugin changes trigger a patch bump. Add `[skip version]` or `[no bump]` to a commit message to skip it.

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
