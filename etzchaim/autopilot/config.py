"""Autopilot configuration loader.

Reads `autopilot:` section from config.yaml. Defaults are conservative:
disabled, low concurrency, strict path exclusions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


DEFAULT_EXCLUDED_PATHS: tuple[str, ...] = (
    "sifrei_yesod/",
    ".claude/",
    "paper/sections/appendix_historical.md",
    "bridge/",
    "partzufim/",
    "mazalengine/",
    "specs/",
    "MISSION.md",
)


@dataclass(frozen=True)
class AutopilotConfig:
    """Autopilot runtime configuration."""

    enabled: bool = False
    worker: str = "claude"  # "claude" | "codex"
    interval_seconds: int = 1800  # 30 min
    max_open_prs: int = 5
    max_workers_threadpool: int = 3
    budget_tokens_monthly: int = 1_000_000
    excluded_paths: tuple[str, ...] = DEFAULT_EXCLUDED_PATHS
    pivot_audit_interval_days: int = 7
    edge_validation_interval_days: int = 7
    paper_draft_interval_hours: int = 24
    worker_paths: dict[str, str] = field(
        default_factory=lambda: {"claude": "claude", "codex": "codex"}
    )

    @classmethod
    def from_file(cls, path: str | Path) -> "AutopilotConfig":
        """Load configuration from a YAML file.

        Returns defaults if file missing or section absent.
        """
        p = Path(path)
        if not p.exists():
            return cls()

        with p.open() as fh:
            doc = yaml.safe_load(fh) or {}

        section = doc.get("autopilot") or {}
        return cls(
            enabled=bool(section.get("enabled", False)),
            worker=str(section.get("worker", "claude")),
            interval_seconds=int(section.get("interval_seconds", 1800)),
            max_open_prs=int(section.get("max_open_prs", 5)),
            max_workers_threadpool=int(section.get("max_workers_threadpool", 3)),
            budget_tokens_monthly=int(section.get("budget_tokens_monthly", 1_000_000)),
            excluded_paths=tuple(section.get("excluded_paths", DEFAULT_EXCLUDED_PATHS)),
            pivot_audit_interval_days=int(section.get("pivot_audit_interval_days", 7)),
            edge_validation_interval_days=int(
                section.get("edge_validation_interval_days", 7)
            ),
            paper_draft_interval_hours=int(
                section.get("paper_draft_interval_hours", 24)
            ),
            worker_paths=dict(
                section.get("worker_paths", {"claude": "claude", "codex": "codex"})
            ),
        )

    def is_path_excluded(self, path: str) -> bool:
        """Check if a repo-relative path is in the excluded list."""
        return any(path.startswith(excl) for excl in self.excluded_paths)

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "worker": self.worker,
            "interval_seconds": self.interval_seconds,
            "max_open_prs": self.max_open_prs,
            "max_workers_threadpool": self.max_workers_threadpool,
            "budget_tokens_monthly": self.budget_tokens_monthly,
            "excluded_paths": list(self.excluded_paths),
            "pivot_audit_interval_days": self.pivot_audit_interval_days,
            "edge_validation_interval_days": self.edge_validation_interval_days,
            "paper_draft_interval_hours": self.paper_draft_interval_hours,
            "worker_paths": dict(self.worker_paths),
        }
