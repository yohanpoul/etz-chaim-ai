"""Helper for tests that need to run psql commands.

PSQL_BIN is resolved in this order:
  1. ETZ_PSQL_BIN environment variable (explicit override)
  2. shutil.which("psql") (found on PATH)
  3. None (caller must handle; tests should skip)

Portable on macOS (Homebrew), Linux (apt/dnf), Windows (install-path on PATH).
"""
from __future__ import annotations

import os
import shutil

PSQL_BIN: str | None = os.environ.get("ETZ_PSQL_BIN") or shutil.which("psql")
"""Absolute path to psql, or None if not found."""


def require_psql() -> str:
    """Return PSQL_BIN or raise RuntimeError with install hint."""
    if PSQL_BIN is None:
        raise RuntimeError(
            "psql non trouvé. Installe postgresql-client "
            "(brew install postgresql@17 / apt install postgresql-client) "
            "ou définis ETZ_PSQL_BIN=/path/to/psql."
        )
    return PSQL_BIN
