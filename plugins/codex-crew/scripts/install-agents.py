#!/usr/bin/env python3
"""Install Codex Crew custom agent templates."""

import argparse
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Install Codex Crew custom agents.")
    parser.add_argument(
        "--target",
        default=str(Path.home() / ".codex" / "agents"),
        help="Target agents directory. Defaults to ~/.codex/agents.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing agent files with the same names.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    source_dir = repo_root / "agents"
    target_dir = Path(args.target).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)

    installed: list[str] = []
    skipped: list[str] = []

    for source in sorted(source_dir.glob("*.toml")):
        target = target_dir / source.name
        if target.exists() and not args.force:
            skipped.append(str(target))
            continue
        shutil.copy2(source, target)
        installed.append(str(target))

    if installed:
        print("Installed:")
        for path in installed:
            print(f"- {path}")

    if skipped:
        print("Skipped existing files. Re-run with --force to overwrite:")
        for path in skipped:
            print(f"- {path}")

    if not installed and not skipped:
        print("No agent templates found.")


if __name__ == "__main__":
    main()
