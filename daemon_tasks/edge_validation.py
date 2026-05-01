"""Daemon task: weekly edge validation.

Invokes the `validate-edge` skill via Claude Code subprocess. Default
interval : 7 days. Runs the Cognitive OS Evaluation Suite + 4 baselines.
Halts autopilot loop if edge degrades 3 weeks in a row.
"""

from __future__ import annotations

import logging

log = logging.getLogger("etz-daemon")

INTERVAL_EDGE_VALIDATION = 7 * 86400  # 7 days


def task_edge_validation(tree: dict) -> dict:
    """Run one edge validation cycle."""
    try:
        from etzchaim.autopilot.config import AutopilotConfig
        from etzchaim.autopilot.runners.claude_skill import ClaudeSkillRunner
    except ImportError as exc:
        return {"task": "edge_validation", "skipped": f"import error: {exc}"}

    cfg = AutopilotConfig.from_file("etzchaim/deploy/config.yaml")
    runner = ClaudeSkillRunner(binary=cfg.worker_paths.get("claude", "claude"))

    try:
        result = runner.invoke_skill(
            skill_name="validate-edge",
            task_brief=(
                "Run the weekly edge validation. Execute the Cognitive OS "
                "Evaluation Suite (8 metrics) against four baselines : LLM "
                "alone, LangChain, AutoGen, generic self-evolution. Compute "
                "statistical significance, render an edge report, and append "
                "to history. If three consecutive failures, write the "
                "EDGE_DEGRADATION flag for pivot-audit."
            ),
            timeout=1800,  # 30 min — benchmark runs are slow
        )
    except Exception as exc:
        log.exception("edge_validation raised")
        return {"task": "edge_validation", "error": str(exc)}

    log.info("edge_validation: success=%s", result.success)
    return {
        "task": "edge_validation",
        "success": result.success,
        "exit_code": result.exit_code,
        "stdout_tail": result.stdout[-500:] if result.stdout else "",
    }
