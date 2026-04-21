"""Modèles de données — Binah-de-Netzach : structures de l'intention persistante."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class SubTask:
    """Une sous-tâche décomposée d'une intention."""

    id: UUID
    intention_id: UUID
    description: str
    status: str  # pending, in_progress, completed, failed, skipped
    order_index: int
    strategy_version: int = 1
    result: str | None = None
    failure_reason: str | None = None
    retries: int = 0
    max_retries: int = 3
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass
class Intention:
    """Une intention persistante avec ses méta-données."""

    id: UUID
    goal: str
    status: str  # active, completed, abandoned, paused
    max_duration_days: int
    abandon_threshold: float
    progress: float
    strategy: str | None = None
    strategy_version: int = 1
    total_subtasks: int = 0
    completed_subtasks: int = 0
    failed_subtasks: int = 0
    abandon_reason: str | None = None
    created_at: datetime | None = None
    deadline_at: datetime | None = None
    completed_at: datetime | None = None
    subtasks: list[SubTask] = field(default_factory=list)


@dataclass
class ProgressReport:
    """Rapport de progrès — Hod-de-Netzach."""

    intention_id: UUID
    goal: str
    progress: float
    time_elapsed_ratio: float  # 0-1, fraction du temps max écoulée
    subtasks_completed: int
    subtasks_total: int
    subtasks_failed: int
    strategy_version: int
    is_on_track: bool
    warning: str | None = None  # Qlipat Nogah si progrès lent
    days_since_activity: float | None = None


@dataclass
class AbandonDecision:
    """Décision d'abandon — anti-A'arab Zaraq.

    4 niveaux de sévérité :
    - healthy : tout va bien
    - nogah : progrès lent, warning
    - ruach : fuite de ressources, erreur
    - anan : faux progrès, défaillance silencieuse
    - mamash : zombie, fatal
    """

    should_abandon: bool
    reason: str | None
    level: str  # healthy, nogah, ruach, anan, mamash
    progress: float
    time_elapsed_ratio: float
    days_since_activity: float | None = None


@dataclass
class NewStrategy:
    """Nouvelle stratégie après échec — adaptation, pas retry."""

    intention_id: UUID
    old_strategy: str | None
    new_strategy: str
    new_version: int
    reason: str
    new_subtasks: list[str]
