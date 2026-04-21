"""Modèles de données pour SelfModel — Da'at.

SelfState : état du système à un instant T
Prediction : prédiction d'erreur vérifiable
BiasEntry : biais détecté
EvolutionSnapshot : santé du système dans le temps
SelfDescription : réponse à "qui suis-je ?"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID


class BiasType(str, Enum):
    OVERCONFIDENCE = "overconfidence"
    UNDERCONFIDENCE = "underconfidence"
    DOMAIN_BLIND_SPOT = "domain_blind_spot"
    RECENCY_BIAS = "recency_bias"
    CONFIRMATION_BIAS = "confirmation_bias"
    ANCHORING = "anchoring"
    SCOPE_CREEP = "scope_creep"
    PREMATURE_CLOSURE = "premature_closure"


class Trend(str, Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"


@dataclass
class SelfState:
    """État du système à un instant T — photographie de Da'at."""

    id: UUID | None = None
    captured_at: datetime | None = None

    # Agrégation depuis les 6 Sephiroth
    yesod_stats: dict = field(default_factory=dict)
    hod_stats: dict = field(default_factory=dict)
    netzach_stats: dict = field(default_factory=dict)
    tiferet_stats: dict = field(default_factory=dict)
    gevurah_stats: dict = field(default_factory=dict)
    chesed_stats: dict = field(default_factory=dict)

    # Synthèse Da'at
    known_biases: list[dict] = field(default_factory=list)
    predicted_weaknesses: list[str] = field(default_factory=list)
    predicted_strengths: list[str] = field(default_factory=list)
    model_confidence: float = 0.5


@dataclass
class Prediction:
    """Prédiction d'erreur — le cœur de Da'at."""

    prediction: str
    domain: str = ""
    predicted_error_type: str = ""
    predicted_confidence: float = 0.5

    # Vérification
    id: UUID | None = None
    predicted_at: datetime | None = None
    verified_at: datetime | None = None
    was_correct: bool | None = None
    actual_outcome: str = ""
    prediction_accuracy_running: float | None = None


@dataclass
class BiasEntry:
    """Biais détecté dans le système."""

    bias_type: str
    description: str
    evidence: dict = field(default_factory=dict)
    severity: float = 0.5
    domain: str = ""
    mitigation: str = ""
    still_active: bool = True

    id: UUID | None = None
    detected_at: datetime | None = None


@dataclass
class EvolutionSnapshot:
    """Santé du système dans le temps — tendances."""

    # Santé par Sephirah (0-1)
    yesod_health: float = 0.5
    hod_health: float = 0.5
    netzach_health: float = 0.5
    tiferet_health: float = 0.5
    gevurah_health: float = 0.5
    chesed_health: float = 0.5

    # Synthèse
    overall_health: float = 0.5
    trend: str = "stable"
    trend_details: dict = field(default_factory=dict)

    id: UUID | None = None
    snapshot_at: datetime | None = None

    @property
    def health_by_sephirah(self) -> dict[str, float]:
        return {
            "yesod": self.yesod_health,
            "hod": self.hod_health,
            "netzach": self.netzach_health,
            "tiferet": self.tiferet_health,
            "gevurah": self.gevurah_health,
            "chesed": self.chesed_health,
        }


@dataclass
class SelfDescription:
    """Réponse à 'qui suis-je ?' — le fruit de Da'at."""

    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    biases: list[BiasEntry] = field(default_factory=list)
    blind_spots: list[str] = field(default_factory=list)
    evolution_trend: str = "stable"
    prediction_accuracy: float | None = None
    confidence_in_self_model: float = 0.5

    # Santé par Sephirah
    health_by_sephirah: dict[str, float] = field(default_factory=dict)
