"""Daemon task: weekly pivot audit.

Invokes the `audit-pivot` skill via Claude Code subprocess. Default
interval : 7 days. Runs even if `autopilot.enabled` is false (audit is
governance, not work).
"""

from __future__ import annotations

import logging

log = logging.getLogger("etz-daemon")

INTERVAL_PIVOT_AUDIT = 7 * 86400  # 7 days


def task_pivot_audit(tree: dict) -> dict:
    """Run one pivot audit cycle."""
    try:
        from etzchaim.autopilot.config import AutopilotConfig
        from etzchaim.autopilot.runners.claude_skill import ClaudeSkillRunner
    except ImportError as exc:
        return {"task": "pivot_audit", "skipped": f"import error: {exc}"}

    cfg = AutopilotConfig.from_file("etzchaim/deploy/config.yaml")
    runner = ClaudeSkillRunner(binary=cfg.worker_paths.get("claude", "claude"))

    try:
        result = runner.invoke_skill(
            skill_name="audit-pivot",
            task_brief=(
                "Run the weekly pivot audit. Read MISSION.md and the last "
                "week of autopilot trajectories. Classify recent PRs, run "
                "the four adversarial check questions, compute drift score, "
                "and write an audit report. If drift score > 0.5 OR three "
                "weekly edge failures consecutive : trigger pivot."
            ),
            timeout=900,
        )
    except Exception as exc:
        log.exception("pivot_audit raised")
        return {"task": "pivot_audit", "error": str(exc)}

    log.info("pivot_audit: success=%s", result.success)
    return {
        "task": "pivot_audit",
        "success": result.success,
        "exit_code": result.exit_code,
        "stdout_tail": result.stdout[-500:] if result.stdout else "",
    }
