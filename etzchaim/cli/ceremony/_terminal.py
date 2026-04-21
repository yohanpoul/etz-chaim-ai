"""Terminal capability detection for the birth ceremony.

All checks are read-only and side-effect-free. The orchestrator passes the
results to `play_ceremony` which picks between full / narrow / compact / skip.
"""
from __future__ import annotations

import os
import shutil
import sys


NARROW_THRESHOLD = 70


def _stdout_isatty() -> bool:
    """Wrapped for monkeypatching in tests."""
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


def _stdin_isatty() -> bool:
    """Wrapped for monkeypatching in tests."""
    try:
        return sys.stdin.isatty()
    except Exception:
        return False


def _in_ci() -> bool:
    return any(
        os.environ.get(var)
        for var in ("CI", "GITHUB_ACTIONS", "GITLAB_CI", "BUILDKITE", "CIRCLECI")
    )


def should_play_ceremony(*, non_interactive: bool, no_ceremony: bool) -> bool:
    """Return True iff the full animated ceremony should run.

    Any of these cause a skip (compact banner only) :
      - explicit --non-interactive or --no-ceremony
      - CI environment (CI, GITHUB_ACTIONS, ...)
      - TERM=dumb or unset
      - stdout not a TTY (piped, redirected)
    """
    if non_interactive or no_ceremony:
        return False
    if _in_ci():
        return False
    term = os.environ.get("TERM", "")
    if not term or term == "dumb":
        return False
    if not _stdout_isatty() or not _stdin_isatty():
        return False
    return True


def supports_color() -> bool:
    """False if NO_COLOR is set (any value) or TERM indicates no color."""
    if os.environ.get("NO_COLOR") is not None:
        return False
    term = os.environ.get("TERM", "")
    if term in ("", "dumb"):
        return False
    return True


def terminal_size() -> tuple[int, int]:
    """(columns, lines). Falls back to (80, 24)."""
    size = shutil.get_terminal_size((80, 24))
    return size.columns, size.lines


def is_narrow() -> bool:
    """True if the terminal is narrower than NARROW_THRESHOLD columns."""
    cols, _ = terminal_size()
    return cols < NARROW_THRESHOLD


def supports_utf8() -> bool:
    """Best-effort UTF-8 detection via LANG / LC_ALL / LC_CTYPE."""
    for var in ("LC_ALL", "LC_CTYPE", "LANG"):
        val = os.environ.get(var, "")
        if "UTF-8" in val.upper() or "UTF8" in val.upper():
            return True
    return False
