#!/usr/bin/env python3
"""Compatibility entrypoint for tooling that discovers test_*.py files."""

from pathlib import Path
import runpy


runpy.run_path(str(Path(__file__).with_name("test-hooks.py")), run_name="__main__")
