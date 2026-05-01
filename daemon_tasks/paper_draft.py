"""Daemon task: daily paper section drafting.

Invokes the `paper-writer` skill via Claude Code subprocess. Default
interval : 24 hours. Skips operator-only sections.
"""

from __future__ import annotations

import logging

log = logging.getLogger("etz-daemon")

INTERVAL_PAPER_DRAFT = 24 * 3600  # 24 hours


def task_paper_draft(tree: dict) -> dict:
    """Draft one paper section."""
    try:
        from etzchaim.autopilot.config import AutopilotConfig
        from etzchaim.autopilot.runners.claude_skill import ClaudeSkillRunner
    except ImportError as exc:
        return {"task": "paper_draft", "skipped": f"import error: {exc}"}

    cfg = AutopilotConfig.from_file("etzchaim/deploy/config.yaml")

    if not cfg.enabled:
        return {"task": "paper_draft", "skipped": "autopilot disabled"}

    runner = ClaudeSkillRunner(binary=cfg.worker_paths.get("claude", "claude"))

    try:
        result = runner.invoke_skill(
            skill_name="paper-writer",
            task_brief=(
                "Draft the next pending paper section per the outline at "
                "paper/sections/_outline.md. Skip operator-only sections "
                "(intro, theory, formal definitions, discussion, historical "
                "note). Run public surface guard. Open a PR titled "
                "paper(section <id>): draft."
            ),
            timeout=900,
        )
    except Exception as exc:
        log.exception("paper_draft raised")
        return {"task": "paper_draft", "error": str(exc)}

    log.info("paper_draft: success=%s", result.success)
    return {
        "task": "paper_draft",
        "success": result.success,
        "exit_code": result.exit_code,
        "stdout_tail": result.stdout[-500:] if result.stdout else "",
    }
