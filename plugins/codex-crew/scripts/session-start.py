#!/usr/bin/env python3
"""Crew SessionStart hook.

Restores active Crew loop context and injects lightweight skill guidance.
"""

import json
import os
import time
from pathlib import Path

from models import (
    SessionStartInput,
    SessionStartResult,
    get_file_age_days,
    read_hook_input,
)
from state_discovery import is_active_state_file, is_loop_state_file


MAX_AGE_DAYS = 7
MAX_AGE_SECONDS = MAX_AGE_DAYS * 86400
STALE_INACTIVE_SECONDS = 86400
VERBOSE_SESSION_START_VALUES = {"1", "true", "yes", "verbose", "full"}
CREW_DIR_NAME = ".crew"


def cleanup_stale_files(directory: Path) -> None:
    """Remove stale Crew state files."""
    if not directory.is_dir():
        return

    now = time.time()
    for json_file in directory.glob("*.json"):
        try:
            if not is_loop_state_file(json_file.name):
                continue
            age = now - json_file.stat().st_mtime
            if is_active_state_file(json_file):
                if age > MAX_AGE_SECONDS:
                    json_file.unlink()
            elif age > STALE_INACTIVE_SECONDS:
                json_file.unlink()
        except OSError:
            continue


def detect_project_stack(directory: Path) -> list[str]:
    """Detect stack hints used for skill reminder text."""
    hints: list[str] = []

    if list(directory.glob("**/*.kt"))[:1] or list(directory.glob("**/*.kts"))[:1]:
        hints.append("Kotlin")

    if list(directory.glob("**/*.gradle.kts"))[:1]:
        hints.append("Gradle")

    build_file = directory / "build.gradle.kts"
    if build_file.is_file():
        try:
            content = build_file.read_text()
        except OSError:
            content = ""
        lowered = content.lower()
        if "exposed" in lowered:
            hints.append("Exposed")
        if "trino" in lowered:
            hints.append("Trino")

    if list(directory.glob("**/*.py"))[:1]:
        hints.append("Python")

    return hints


def build_plugin_guidance(stack_hints: list[str]) -> str:
    lines = [
        "<system-reminder>",
        "Crew is available in this session.",
        "",
        "Use the `crew` skill for planning, execution workflows, build loops,",
        "measure-twice loops, context snapshots, status checks, and AGENTS.md deepinit.",
        "",
        "Use custom agents only when the user explicitly asks for subagents, delegation,",
        "parallel agents, or names one of the Crew agents.",
        "</system-reminder>",
    ]

    if stack_hints:
        lines.extend([
            "",
            "<system-reminder>",
            f"This project appears to use: {', '.join(stack_hints)}.",
            "Relevant skills may include:",
        ])
        if "Kotlin" in stack_hints:
            lines.append("- `kotlin` and `kotlin-testing`")
        if "Gradle" in stack_hints:
            lines.append("- `gradle`")
        if "Exposed" in stack_hints:
            lines.append("- `exposed`")
        if "Trino" in stack_hints:
            lines.append("- `trino`")
        if "Python" in stack_hints:
            lines.append("- `python`")
        lines.append("</system-reminder>")

    return "\n".join(lines)


def is_verbose_session_start() -> bool:
    """Return whether SessionStart should include generic guidance."""
    value = os.environ.get("CODEX_CREW_SESSION_START", "")
    return value.strip().lower() in VERBOSE_SESSION_START_VALUES


def crew_state_command() -> str:
    plugin_root = os.environ.get("PLUGIN_ROOT") or os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        return f'python3 "{plugin_root}/scripts/crew-state.py"'
    return "python3 <codex-crew-plugin-root>/scripts/crew-state.py"


def build_session_status(directory: Path, session_id: str = "") -> list[str]:
    messages: list[str] = []
    crew_dir = directory / CREW_DIR_NAME

    this_session_loops: list[str] = []
    other_session_loops: list[str] = []

    if crew_dir.is_dir():
        for json_file in crew_dir.glob("*.json"):
            if not is_loop_state_file(json_file.name):
                continue
            try:
                data = json.loads(json_file.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            if not data.get("active", False):
                continue

            file_session = data.get("session_id", "")
            is_this_session = not session_id or file_session in ("", session_id)

            if json_file.name.startswith("build-state"):
                deactivate_hint = ""
                if session_id:
                    deactivate_hint = (
                        f"\nDeactivate with: {crew_state_command()} deactivate bl "
                        f"--session-id {session_id} --reason \"Verified complete\""
                    )
                line = (
                    f"[Build Loop Active - {data.get('iteration', 1)}/{data.get('max_iterations', 10)}]\n"
                    f"Task: {data.get('prompt', '')}\n"
                    "Continue until implementation is verified and the loop is deactivated."
                    f"{deactivate_hint}"
                )
            elif json_file.name.startswith("measure-twice-state"):
                deactivate_hint = ""
                if session_id:
                    deactivate_hint = (
                        f"\nDeactivate with: {crew_state_command()} deactivate mt "
                        f"--session-id {session_id} --reason \"Plan approved\""
                    )
                line = (
                    f"[Measure-Twice Loop Active - {data.get('iteration', 1)}/{data.get('max_iterations', 10)}]\n"
                    f"Task: {data.get('task_description', '')}\n"
                    f"Plan: {data.get('plan_file', '')}\n"
                    "Continue until the plan is approved and the loop is deactivated."
                    f"{deactivate_hint}"
                )
            else:
                continue

            if is_this_session:
                this_session_loops.append(line)
            else:
                other_session_loops.append(line.splitlines()[0])

    messages.extend(this_session_loops)
    if other_session_loops:
        messages.append("[Other Crew Sessions]\n" + "\n".join(f"- {line}" for line in other_session_loops))

    context_snapshot = crew_dir / "context-snapshot.md"
    if context_snapshot.is_file() and get_file_age_days(context_snapshot) < MAX_AGE_DAYS:
        messages.append("[Context Snapshot Available]\nRead `.crew/context-snapshot.md` to restore context.")

    return messages


def main() -> None:
    data = read_hook_input()
    hook_input = SessionStartInput.from_dict(data)
    directory = hook_input.directory_path
    session_id = hook_input.session_id

    cleanup_stale_files(directory / CREW_DIR_NAME)

    context_parts: list[str] = []
    if is_verbose_session_start():
        context_parts.append(build_plugin_guidance(detect_project_stack(directory)))

    status_messages = build_session_status(directory, session_id)
    if status_messages:
        context_parts.append("\n\n".join(status_messages))

    print(SessionStartResult.with_context("\n\n".join(context_parts)).to_json())


if __name__ == "__main__":
    main()
