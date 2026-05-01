"""Autopilot persistent state.

Reads/writes autopilot-specific state into the daemon state file:
`~/.etz-chaim/daemon_state.json`. Atomic via tmp+rename.

Keys added (no schema break):
- `last_autopilot`: unix timestamp of last cycle
- `last_pivot_audit`: unix timestamp of last pivot audit
- `last_edge_validation`: unix timestamp
- `last_paper_draft`: unix timestamp
- `autopilot_pr_count_open`: number of open auto-PRs (refreshed each cycle)
- `autopilot_tokens_consumed_month`: rolling monthly consumption counter
- `autopilot_tokens_consumed_month_anchor`: ISO date when month counter reset
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


def _etz_home() -> Path:
    return Path(os.environ.get("ETZCHAIM_STATE_DIR", "~/.etz-chaim")).expanduser()


def _state_file() -> Path:
    return _etz_home() / "daemon_state.json"


# Backward compat module attributes (callers that imported these names).
ETZ_HOME = _etz_home()
STATE_FILE = _state_file()


@dataclass
class AutopilotState:
    last_autopilot: float = 0.0
    last_pivot_audit: float = 0.0
    last_edge_validation: float = 0.0
    last_paper_draft: float = 0.0
    autopilot_pr_count_open: int = 0
    autopilot_tokens_consumed_month: int = 0
    autopilot_tokens_consumed_month_anchor: str = ""

    @classmethod
    def load(cls) -> "AutopilotState":
        path = _state_file()
        if not path.exists():
            return cls()

        try:
            with path.open() as fh:
                doc = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return cls()

        return cls(
            last_autopilot=float(doc.get("last_autopilot", 0.0)),
            last_pivot_audit=float(doc.get("last_pivot_audit", 0.0)),
            last_edge_validation=float(doc.get("last_edge_validation", 0.0)),
            last_paper_draft=float(doc.get("last_paper_draft", 0.0)),
            autopilot_pr_count_open=int(doc.get("autopilot_pr_count_open", 0)),
            autopilot_tokens_consumed_month=int(
                doc.get("autopilot_tokens_consumed_month", 0)
            ),
            autopilot_tokens_consumed_month_anchor=str(
                doc.get("autopilot_tokens_consumed_month_anchor", "")
            ),
        )

    def save(self) -> None:
        """Atomic write merging autopilot keys into the daemon state file."""
        path = _state_file()
        path.parent.mkdir(parents=True, exist_ok=True)

        existing: dict = {}
        if path.exists():
            try:
                with path.open() as fh:
                    existing = json.load(fh)
            except (OSError, json.JSONDecodeError):
                existing = {}

        existing.update(asdict(self))

        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(existing, indent=2))
        os.replace(str(tmp), str(path))

    def reset_monthly_budget_if_needed(self) -> None:
        """Roll over monthly token counter at month change."""
        now_anchor = datetime.now(timezone.utc).strftime("%Y-%m")
        if self.autopilot_tokens_consumed_month_anchor != now_anchor:
            self.autopilot_tokens_consumed_month = 0
            self.autopilot_tokens_consumed_month_anchor = now_anchor
