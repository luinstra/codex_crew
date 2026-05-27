#!/usr/bin/env python3
"""Tests for Codex Crew scripts."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
CREW_STATE = SCRIPT_DIR / "crew-state.py"
PERSISTENT_MODE = SCRIPT_DIR / "persistent-mode.py"
SESSION_START = SCRIPT_DIR / "session-start.py"


def run_script(script: Path, args: list[str], project_dir: Path, stdin: dict | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CODEX_PROJECT_DIR"] = str(project_dir)
    env["CODEX_SESSION_ID"] = "session-123"
    return subprocess.run(
        [sys.executable, str(script), *args],
        input=json.dumps(stdin) if stdin is not None else None,
        text=True,
        capture_output=True,
        check=False,
        env=env,
        cwd=project_dir,
    )


class CrewStateTests(unittest.TestCase):
    def test_build_loop_state_is_codex_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            result = run_script(
                CREW_STATE,
                ["init", "bl", "--prompt", "Fix auth", "--session-id", "session-123"],
                project_dir,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            state_file = project_dir / ".codex-crew" / "build-state-session-123.json"
            self.assertTrue(state_file.is_file())
            state = json.loads(state_file.read_text())
            self.assertTrue(state["active"])
            self.assertEqual(state["prompt"], "Fix auth")

    def test_measure_twice_auto_plan_uses_codex_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            result = run_script(
                CREW_STATE,
                ["init", "mt", "--task", "Add profiles", "--auto-plan", "--session-id", "session-123"],
                project_dir,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(".codex-crew/plans/add-profiles.md", result.stdout)
            self.assertTrue((project_dir / ".codex-crew" / "plans").is_dir())

    def test_stop_hook_blocks_active_build_loop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            init = run_script(
                CREW_STATE,
                ["init", "bl", "--prompt", "Fix auth", "--session-id", "session-123"],
                project_dir,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            result = run_script(
                PERSISTENT_MODE,
                [],
                project_dir,
                {"cwd": str(project_dir), "session_id": "session-123", "hook_event_name": "Stop"},
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["decision"], "block")
            self.assertIn("Codex Crew Build Loop", payload["reason"])

    def test_stop_hook_allows_when_no_loop_is_active(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            result = run_script(
                PERSISTENT_MODE,
                [],
                project_dir,
                {"cwd": str(project_dir), "session_id": "session-123", "hook_event_name": "Stop"},
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {})

    def test_session_start_injects_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            result = run_script(
                SESSION_START,
                [],
                project_dir,
                {"cwd": str(project_dir), "session_id": "session-123", "hook_event_name": "SessionStart"},
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            context = payload["hookSpecificOutput"]["additionalContext"]
            self.assertIn("Codex Crew is available", context)


if __name__ == "__main__":
    unittest.main()
