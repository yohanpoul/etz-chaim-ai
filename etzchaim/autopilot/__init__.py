"""etzchaim.autopilot — internal autonomous coding loop.

Continuously works toward MISSION.md targets by delegating to LLM workers
(Claude Code or Codex), reading specs, opening PRs, and respecting public
surface neutrality at every gate.

Disabled by default. Enable via config.yaml: `autopilot.enabled: true`.

Architecture inspiration acknowledged in LICENSE_THIRD_PARTY.md.
"""

from __future__ import annotations

__version__ = "0.1.0"

from etzchaim.autopilot.config import AutopilotConfig
from etzchaim.autopilot.state import AutopilotState

__all__ = ["AutopilotConfig", "AutopilotState"]
