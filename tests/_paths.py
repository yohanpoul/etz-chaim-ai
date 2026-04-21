"""Cross-platform paths helper for tests.

PROJECT_ROOT is resolved relative to this file, not hardcoded.
Works on any machine that checks out the repo.
"""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
"""Absolute path to the repo root (etz-chaim-ai/)."""
