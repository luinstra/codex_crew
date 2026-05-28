#!/usr/bin/env python3
"""Tests for Crew scripts."""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PLUGIN_ROOT.parent.parent
CREW_STATE = SCRIPT_DIR / "crew-state.py"
PERSISTENT_MODE = SCRIPT_DIR / "persistent-mode.py"
SESSION_START = SCRIPT_DIR / "session-start.py"
INSTALL_AGENTS = SCRIPT_DIR / "install-agents.py"
VERSION_BUMP = REPO_ROOT / "scripts" / "post-commit-version-bump.sh"
PLUGIN_MANIFEST = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
CREW_SKILL = PLUGIN_ROOT / "skills" / "codex-crew" / "SKILL.md"
KOTLIN_SKILL = PLUGIN_ROOT / "skills" / "kotlin" / "SKILL.md"


def run_script(
    script: Path,
    args: list[str],
    project_dir: Path,
    stdin: dict | None = None,
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CODEX_PROJECT_DIR"] = str(project_dir)
    env["CODEX_SESSION_ID"] = "session-123"
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        [sys.executable, str(script), *args],
        input=json.dumps(stdin) if stdin is not None else None,
        text=True,
        capture_output=True,
        check=False,
        env=env,
        cwd=project_dir,
    )


def skill_description(skill_path: Path) -> str:
    text = skill_path.read_text()
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return ""
    in_description = False
    parts: list[str] = []
    for line in lines[1:]:
        if line == "---":
            break
        if line.startswith("description:"):
            value = line.split(":", 1)[1].strip()
            if value in (">-", "|"):
                in_description = True
                continue
            return value.strip('"')
        if in_description:
            if line.startswith("  "):
                parts.append(line.strip())
            else:
                break
    return " ".join(parts)


def run_git(project_dir: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        text=True,
        capture_output=True,
        check=False,
        cwd=project_dir,
    )


def write_minimal_manifest(project_dir: Path, version: str = "0.1.0") -> Path:
    manifest = project_dir / "plugins" / "codex-crew" / ".codex-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({
        "name": "codex-crew",
        "version": version,
        "interface": {"displayName": "Crew"},
    }, indent=2))
    return manifest


def init_version_bump_repo(project_dir: Path) -> Path:
    manifest = write_minimal_manifest(project_dir)
    plugin_readme = project_dir / "plugins" / "codex-crew" / "README.md"
    plugin_readme.write_text("# Crew\n")

    for args in [
        ["init"],
        ["config", "user.email", "test@example.com"],
        ["config", "user.name", "Test User"],
        ["add", "."],
        ["commit", "-m", "chore: initial [skip version]"],
    ]:
        result = run_git(project_dir, args)
        if result.returncode != 0:
            raise AssertionError(result.stderr)

    return manifest


class CrewStateTests(unittest.TestCase):
    def test_manifest_has_marketplace_urls_and_usable_prompt_count(self) -> None:
        manifest = json.loads(PLUGIN_MANIFEST.read_text())
        interface = manifest["interface"]

        self.assertIn("websiteURL", interface)
        self.assertIn("privacyPolicyURL", interface)
        self.assertIn("termsOfServiceURL", interface)
        self.assertLessEqual(len(interface["defaultPrompt"]), 3)

    def test_crew_skill_documents_all_claude_command_replacements(self) -> None:
        text = CREW_SKILL.read_text()

        for prompt in [
            "crew cancel build",
            "crew cancel measure twice",
            "crew code search",
            "crew configure",
        ]:
            self.assertIn(prompt, text)

    def test_kotlin_skill_references_codex_skill_name(self) -> None:
        text = KOTLIN_SKILL.read_text()

        self.assertNotIn("sk:kotlin-testing", text)
        self.assertIn("kotlin-testing", text)

    def test_skill_descriptions_use_concise_use_when_triggers(self) -> None:
        for skill_path in sorted((PLUGIN_ROOT / "skills").glob("*/SKILL.md")):
            description = skill_description(skill_path)

            self.assertIn("Use when", description, skill_path)
            self.assertLessEqual(len(description), 220, skill_path)

    def test_large_skills_use_progressive_disclosure_references(self) -> None:
        for skill_path in sorted((PLUGIN_ROOT / "skills").glob("*/SKILL.md")):
            lines = skill_path.read_text().splitlines()
            references_dir = skill_path.parent / "references"

            self.assertLessEqual(len(lines), 180, skill_path)
            self.assertTrue(references_dir.is_dir(), skill_path)

    def test_build_loop_state_uses_shared_crew_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            result = run_script(
                CREW_STATE,
                ["init", "bl", "--prompt", "Fix auth", "--session-id", "session-123"],
                project_dir,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            state_file = project_dir / ".crew" / "build-state-session-123.json"
            self.assertTrue(state_file.is_file())
            self.assertFalse((project_dir / ".codex-crew").exists())
            state = json.loads(state_file.read_text())
            self.assertTrue(state["active"])
            self.assertEqual(state["prompt"], "Fix auth")
            self.assertEqual(state["session_id"], "session-123")

    def test_measure_twice_auto_plan_uses_shared_crew_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            result = run_script(
                CREW_STATE,
                ["init", "mt", "--task", "Add profiles", "--auto-plan", "--session-id", "session-123"],
                project_dir,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(".crew/plans/add-profiles.md", result.stdout)
            self.assertTrue((project_dir / ".crew" / "plans").is_dir())
            state_file = project_dir / ".crew" / "measure-twice-state-session-123.json"
            state = json.loads(state_file.read_text())
            self.assertEqual(state["plan_file"], ".crew/plans/add-profiles.md")

    def test_state_uses_codex_thread_id_when_session_id_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            result = run_script(
                CREW_STATE,
                ["init", "bl", "--prompt", "Fix auth"],
                project_dir,
                env_overrides={"CODEX_SESSION_ID": "", "CODEX_THREAD_ID": "thread-123"},
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            state_file = project_dir / ".crew" / "build-state-thread-123.json"
            self.assertTrue(state_file.is_file())
            state = json.loads(state_file.read_text())
            self.assertEqual(state["session_id"], "thread-123")

    def test_deactivate_records_reason_and_completion_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            init = run_script(
                CREW_STATE,
                ["init", "bl", "--prompt", "Fix auth", "--session-id", "session-123"],
                project_dir,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            result = run_script(
                CREW_STATE,
                ["deactivate", "bl", "--reason", "Verified complete", "--session-id", "session-123"],
                project_dir,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((project_dir / ".crew" / "build-state-session-123.json").read_text())
            self.assertFalse(state["active"])
            self.assertEqual(state["reason"], "Verified complete")
            self.assertIn("completed_at", state)

    def test_session_scoped_conflicts_ignore_other_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            for session_id in ["s1", "s2"]:
                result = run_script(
                    CREW_STATE,
                    ["init", "bl", "--prompt", f"Task {session_id}", "--session-id", session_id],
                    project_dir,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

            own_conflict = run_script(CREW_STATE, ["check-conflicts", "--session-id", "s1"], project_dir)
            other_session = run_script(CREW_STATE, ["check-conflicts", "--session-id", "s3"], project_dir)

            self.assertEqual(own_conflict.returncode, 1)
            self.assertIn("build loop is already active", own_conflict.stderr)
            self.assertEqual(other_session.returncode, 0, other_session.stderr)

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
            self.assertIn("Crew Build Loop", payload["reason"])
            self.assertIn("--session-id session-123", payload["reason"])

    def test_stop_hook_blocks_active_measure_twice_loop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            init = run_script(
                CREW_STATE,
                ["init", "mt", "--task", "Design auth", "--auto-plan", "--session-id", "session-123"],
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
            self.assertIn("Crew Measure-Twice Loop", payload["reason"])
            self.assertIn("--session-id session-123", payload["reason"])

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

    def test_session_start_is_quiet_without_active_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            result = run_script(
                SESSION_START,
                [],
                project_dir,
                {"cwd": str(project_dir), "session_id": "session-123", "hook_event_name": "SessionStart"},
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {})

    def test_session_start_verbose_mode_injects_guidance_and_stack_hints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            (project_dir / "src").mkdir()
            (project_dir / "src" / "Example.kt").write_text("fun main() {}\n")
            (project_dir / "build.gradle.kts").write_text(
                "dependencies { implementation(\"org.jetbrains.exposed:exposed-core:1.0.0\") }\n"
                "// trino\n"
            )
            (project_dir / "tool.py").write_text("print('hello')\n")
            crew_dir = project_dir / ".crew"
            crew_dir.mkdir()
            (crew_dir / "context-snapshot.md").write_text("# Snapshot\n")

            result = run_script(
                SESSION_START,
                [],
                project_dir,
                {"cwd": str(project_dir), "session_id": "session-123", "hook_event_name": "SessionStart"},
                {"CODEX_CREW_SESSION_START": "verbose"},
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
            for expected in [
                "Crew is available",
                "Kotlin",
                "Gradle",
                "Exposed",
                "Trino",
                "Python",
                "Context Snapshot Available",
            ]:
                self.assertIn(expected, context)
            self.assertIn(".crew/context-snapshot.md", context)

    def test_session_start_reports_context_snapshot_without_stack_hints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            (project_dir / "tool.py").write_text("print('hello')\n")
            crew_dir = project_dir / ".crew"
            crew_dir.mkdir()
            (crew_dir / "context-snapshot.md").write_text("# Snapshot\n")

            result = run_script(
                SESSION_START,
                [],
                project_dir,
                {"cwd": str(project_dir), "session_id": "session-123", "hook_event_name": "SessionStart"},
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
            self.assertIn("Context Snapshot Available", context)
            self.assertIn(".crew/context-snapshot.md", context)
            self.assertNotIn("Relevant skills may include", context)

    def test_session_start_reports_other_active_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            crew_dir = project_dir / ".crew"
            crew_dir.mkdir()
            (crew_dir / "build-state-other.json").write_text(json.dumps({
                "active": True,
                "prompt": "Other task",
                "iteration": 1,
                "max_iterations": 10,
                "session_id": "other",
            }))

            result = run_script(
                SESSION_START,
                [],
                project_dir,
                {"cwd": str(project_dir), "session_id": "session-123", "hook_event_name": "SessionStart"},
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
            self.assertIn("Other Crew Sessions", context)

    def test_session_start_cleans_stale_loop_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            crew_dir = project_dir / ".crew"
            crew_dir.mkdir()
            inactive = crew_dir / "build-state-stale.json"
            active = crew_dir / "measure-twice-state-old.json"
            inactive.write_text(json.dumps({"active": False, "session_id": "stale"}))
            active.write_text(json.dumps({"active": True, "session_id": "old"}))

            now = time.time()
            two_days_ago = now - (2 * 86400)
            eight_days_ago = now - (8 * 86400)
            os.utime(inactive, (two_days_ago, two_days_ago))
            os.utime(active, (eight_days_ago, eight_days_ago))

            result = run_script(
                SESSION_START,
                [],
                project_dir,
                {"cwd": str(project_dir), "session_id": "session-123", "hook_event_name": "SessionStart"},
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(inactive.exists())
            self.assertFalse(active.exists())

    def test_install_agents_copies_all_templates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            result = subprocess.run(
                [sys.executable, str(INSTALL_AGENTS), "--target", str(target)],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                sorted(path.name for path in target.glob("*.toml")),
                [
                    "crew_advisor.toml",
                    "crew_document_writer.toml",
                    "crew_executor.toml",
                    "crew_reader.toml",
                ],
            )

    def test_version_bump_script_updates_codex_plugin_manifest(self) -> None:
        self.assertTrue(VERSION_BUMP.is_file())

        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            manifest = init_version_bump_repo(project_dir)
            plugin_readme = project_dir / "plugins" / "codex-crew" / "README.md"
            plugin_readme.write_text("# Crew\n\nUpdated behavior.\n")

            for args in [
                ["add", "."],
                ["commit", "-m", "fix: quiet session-start hook"],
            ]:
                result = run_git(project_dir, args)
                self.assertEqual(result.returncode, 0, result.stderr)

            result = subprocess.run(
                [str(VERSION_BUMP)],
                text=True,
                capture_output=True,
                check=False,
                cwd=project_dir,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(manifest.read_text())["version"], "0.1.1")

            log = run_git(project_dir, ["log", "-1", "--format=%s"])
            self.assertEqual(
                log.stdout.strip(),
                "chore: bump version (codex-crew 0.1.0 -> 0.1.1)",
            )

    def test_version_bump_script_skips_non_plugin_changes(self) -> None:
        self.assertTrue(VERSION_BUMP.is_file())

        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            manifest = init_version_bump_repo(project_dir)
            (project_dir / "notes.md").write_text("Internal note.\n")

            for args in [
                ["add", "."],
                ["commit", "-m", "docs: add internal note"],
            ]:
                result = run_git(project_dir, args)
                self.assertEqual(result.returncode, 0, result.stderr)

            result = subprocess.run(
                [str(VERSION_BUMP)],
                text=True,
                capture_output=True,
                check=False,
                cwd=project_dir,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(manifest.read_text())["version"], "0.1.0")


if __name__ == "__main__":
    unittest.main()
