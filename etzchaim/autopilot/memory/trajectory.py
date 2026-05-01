"""ShareGPT-format trajectory logging for autopilot cycles.

Each cycle appends one record to `~/.etz-chaim/autopilot/trajectories.jsonl`.
Format follows the widely-adopted ShareGPT convention so trajectories can be
fed into downstream training pipelines without conversion.

Inspiration acknowledged: ShareGPT format adopted by NousResearch/hermes-agent
(MIT) — pattern is public, our writer is independently authored.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ETZ_HOME = Path(os.environ.get("ETZCHAIM_STATE_DIR", "~/.etz-chaim")).expanduser()
TRAJECTORY_FILE = ETZ_HOME / "autopilot" / "trajectories.jsonl"


@dataclass
class Trajectory:
    """One autopilot cycle as a ShareGPT-style record."""

    conversations: list[dict[str, str]] = field(default_factory=list)
    model: str = ""
    timestamp: str = ""
    completed: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_turn(self, role: str, content: str) -> None:
        """Append one turn. Roles : `system`, `user`, `assistant`, `tool`."""
        self.conversations.append({"from": role, "value": content})

    def to_dict(self) -> dict[str, Any]:
        return {
            "conversations": self.conversations,
            "model": self.model,
            "timestamp": self.timestamp or datetime.now(timezone.utc).isoformat(),
            "completed": self.completed,
            "metadata": self.metadata,
        }


def append_trajectory(trajectory: Trajectory) -> None:
    """Append a trajectory to the JSONL log file (atomic)."""
    TRAJECTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(trajectory.to_dict(), ensure_ascii=False)
    with TRAJECTORY_FILE.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
