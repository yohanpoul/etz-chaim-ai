"""Branch creation utilities for the autopilot."""

from __future__ import annotations

import re
import time

from etzchaim.autopilot.runners.local import LocalRunner

_runner = LocalRunner()
_SAFE = re.compile(r"[^a-z0-9-]+")


def _slugify(text: str) -> str:
    return _SAFE.sub("-", text.lower()).strip("-") or "task"


def create_branch(
    task_id: str,
    cwd: str | None = None,
    prefix: str = "feat/auto-",
) -> str:
    """Create and check out a fresh feature branch. Returns the branch name."""
    timestamp = int(time.time())
    name = f"{prefix}{_slugify(task_id)}-{timestamp}"
    res = _runner.dispatch(["git", "checkout", "-b", name], cwd=cwd, timeout=30)
    if not res.success:
        raise RuntimeError(f"git checkout -b {name} failed: {res.stderr}")
    return name


def current_branch(cwd: str | None = None) -> str:
    res = _runner.dispatch(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd, timeout=10
    )
    if not res.success:
        raise RuntimeError(f"git rev-parse failed: {res.stderr}")
    return res.stdout.strip()
