#!/usr/bin/env python3
"""Codex Crew Stop hook.

Blocks Stop while a build or measure-twice loop is active.
"""

import json
import os

from models import (
    BuildState,
    MeasureTwiceState,
    StopInput,
    read_hook_input,
)
from state_discovery import find_session_state_file


def allow() -> None:
    print("{}")


def block(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}))


def crew_state_command() -> str:
    plugin_root = os.environ.get("PLUGIN_ROOT") or os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        return f'python3 "{plugin_root}/scripts/crew-state.py"'
    return "python3 <codex-crew-plugin-root>/scripts/crew-state.py"


def main() -> None:
    data = read_hook_input()
    hook_input = StopInput.from_dict(data)
    directory = hook_input.directory_path
    session_id = hook_input.session_id
    crew_dir = directory / ".codex-crew"
    state_cmd = crew_state_command()

    build_file = find_session_state_file(crew_dir, "build-state", session_id)
    if build_file:
        build_state = BuildState.load(build_file)
        if build_state.active:
            if build_state.iteration < build_state.max_iterations:
                build_state.iteration += 1
                build_state.save(build_file)
                block(f"""[Codex Crew Build Loop - Iteration {build_state.iteration}/{build_state.max_iterations}]

Task: {build_state.prompt}

Continue working. Before completing:
1. Verify the implementation against the original task.
2. Run the relevant build, test, or lint checks.
3. If complete, run: {state_cmd} deactivate bl --reason "Verified complete"
4. If blocking issues remain, fix them and verify again.
""")
                return

            build_state.active = False
            build_state.save(build_file)
            block(f"""[Codex Crew Build Loop - Safety Limit Reached]

Maximum iterations ({build_state.max_iterations}) reached. The loop has been deactivated.

Summarize what was accomplished and call out any remaining risk.
""")
            return

    measure_file = find_session_state_file(crew_dir, "measure-twice-state", session_id)
    if measure_file:
        measure_state = MeasureTwiceState.load(measure_file)
        if measure_state.active:
            if measure_state.iteration < measure_state.max_iterations:
                measure_state.iteration += 1
                measure_state.save(measure_file)
                block(f"""[Codex Crew Measure-Twice Loop - Iteration {measure_state.iteration}/{measure_state.max_iterations}]

Task: {measure_state.task_description}
Plan: {measure_state.plan_file}

Continue refining the plan:
1. Address all [BLOCKING] review issues.
2. Review the plan again for clarity, completeness, and executability.
3. If approved or only [MINOR] issues remain, run: {state_cmd} deactivate mt --reason "Plan approved"
4. Present the final plan to the user.
""")
                return

            measure_state.active = False
            measure_state.save(measure_file)
            block(f"""[Codex Crew Measure-Twice Loop - Safety Limit Reached]

Maximum iterations ({measure_state.max_iterations}) reached. The loop has been deactivated.

Present the current plan and explain where it stands.
""")
            return

    allow()


if __name__ == "__main__":
    main()
