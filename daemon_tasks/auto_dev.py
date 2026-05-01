"""Daemon task: invoke one autopilot cycle.

Wired into `daemon.py` via the existing task registration pattern.
Default interval : 30 minutes. Disabled until `autopilot.enabled` is set.
"""

from __future__ import annotations

import logging

log = logging.getLogger("etz-daemon")

INTERVAL_AUTO_DEV = 1800  # 30 min


def task_auto_dev(tree: dict) -> dict:
    """Run one autopilot cycle. Returns a structured result."""
    try:
        from etzchaim.autopilot.loop import run_one_cycle
    except ImportError as exc:
        return {"task": "auto_dev", "skipped": f"import error: {exc}"}

    try:
        outcome = run_one_cycle(dry_run=False)
    except Exception as exc:  # never let the daemon die because of autopilot
        log.exception("auto_dev cycle raised")
        return {"task": "auto_dev", "error": str(exc)}

    log.info(
        "auto_dev: status=%s task=%s skill=%s",
        outcome.status, outcome.task_id, outcome.skill,
    )
    return {
        "task": "auto_dev",
        "status": outcome.status,
        "task_id": outcome.task_id,
        "skill": outcome.skill,
        "summary": outcome.summary[:500] if outcome.summary else "",
    }
