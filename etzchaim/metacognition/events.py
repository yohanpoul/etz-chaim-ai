"""Typed records for the Phase 1A metacognition surface."""

from __future__ import annotations

from dataclasses import dataclass, field

ACTION_TYPES = frozenset({"rule", "test", "patch", "alert"})


@dataclass(frozen=True)
class MetacognitionEvent:
    """A local signal observed by the safe improve loop."""

    id: str
    source: str
    severity: str
    title: str
    description: str
    evidence: list[str] = field(default_factory=list)
    priority: int = 0
    verification_command: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "evidence": list(self.evidence),
            "priority": self.priority,
            "verification_command": self.verification_command,
        }


@dataclass(frozen=True)
class ProposedAction:
    """A non-applied action proposed from one or more events."""

    id: str
    type: str
    title: str
    description: str
    event_ids: list[str]
    verification_command: str
    applies_patch: bool = False

    def __post_init__(self) -> None:
        if self.type not in ACTION_TYPES:
            allowed = ", ".join(sorted(ACTION_TYPES))
            raise ValueError(f"Unsupported action type: {self.type}. Expected one of: {allowed}")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "event_ids": list(self.event_ids),
            "verification_command": self.verification_command,
            "applies_patch": self.applies_patch,
        }
