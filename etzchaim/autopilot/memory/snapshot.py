"""Frozen context snapshot for the autopilot worker.

Two text files form the durable context surface :

- `~/.etz-chaim/autopilot/context.md` — autopilot operating notes (env quirks,
  conventions, current sprint focus). Inspired by Hermes-agent's memory.md
  pattern (MIT, NousResearch/hermes-agent — see LICENSE_THIRD_PARTY.md). Our
  implementation uses different paths and field names.

- `~/.etz-chaim/autopilot/operator.md` — operator (human) preferences.

Both files are loaded once per autopilot cycle as a frozen string. This
preserves the prompt prefix cache when the underlying LLM provider supports
caching (e.g. Anthropic's prompt caching).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ETZ_HOME = Path(os.environ.get("ETZCHAIM_STATE_DIR", "~/.etz-chaim")).expanduser()
AUTOPILOT_DIR = ETZ_HOME / "autopilot"
CONTEXT_FILE = AUTOPILOT_DIR / "context.md"
OPERATOR_FILE = AUTOPILOT_DIR / "operator.md"
MISSION_FILE = Path(__file__).resolve().parents[3] / "MISSION.md"


@dataclass(frozen=True)
class ContextSnapshot:
    """Frozen string context loaded once per cycle.

    Use as a prefix in LLM calls. The combination is stable across the cycle
    so providers can apply prompt caching to the prefix.
    """

    mission: str
    context: str
    operator: str

    def render(self) -> str:
        """Render the three sections into a single deterministic string."""
        parts: list[str] = []
        if self.mission:
            parts.append("# MISSION\n\n" + self.mission.strip())
        if self.operator:
            parts.append("# OPERATOR PREFERENCES\n\n" + self.operator.strip())
        if self.context:
            parts.append("# AUTOPILOT CONTEXT\n\n" + self.context.strip())
        return "\n\n---\n\n".join(parts)


def _read_or_empty(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def load_frozen_snapshot(mission_path: Path | None = None) -> ContextSnapshot:
    """Load the durable context surface for one autopilot cycle.

    Always returns a snapshot even if some files are missing; missing parts
    become empty strings.
    """
    AUTOPILOT_DIR.mkdir(parents=True, exist_ok=True)

    mission_file = mission_path or MISSION_FILE
    return ContextSnapshot(
        mission=_read_or_empty(mission_file),
        context=_read_or_empty(CONTEXT_FILE),
        operator=_read_or_empty(OPERATOR_FILE),
    )


def write_context(text: str) -> None:
    """Persist autopilot operating context."""
    AUTOPILOT_DIR.mkdir(parents=True, exist_ok=True)
    CONTEXT_FILE.write_text(text, encoding="utf-8")


def write_operator(text: str) -> None:
    """Persist operator preferences."""
    AUTOPILOT_DIR.mkdir(parents=True, exist_ok=True)
    OPERATOR_FILE.write_text(text, encoding="utf-8")
