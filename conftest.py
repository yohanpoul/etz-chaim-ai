"""Pytest root conftest — ensures repo root is on sys.path for top-level modules.

Etz Chaim AI has a number of single-file modules at the repository root
(`pool.py`, `main.py`, `daemon.py`, ...) that are imported by tests but not
included in the installed package (which uses `setuptools.packages.find`).

When pytest runs with `--import-mode=importlib` (configured in pyproject.toml),
it does NOT automatically add the rootdir to `sys.path`, so those imports
fail in CI (`pip install -e .` + `pytest ...`).

This conftest adds the repo root to `sys.path` so every test collected from
any subdirectory can still `import pool`, `import main`, etc. without CI-specific
workflow tricks.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
