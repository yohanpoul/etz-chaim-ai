"""Modèles de données — AutoJudge (Gevurah).

Le vocabulaire du jugement :
- Decision : les 4 verdicts (accepted/rejected/quarantined/tension_detected)
- DomainScore : le jugement brut du domaine (la 'loss')
- MultiScore : l'évaluation multi-sephirothique (5 axes)
- Experiment : une tentative avec son verdict
- LoopResult : le bilan d'un cycle complet
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID


class Decision(str, Enum):
    """Les 4 verdicts de Gevurah."""
    ACCEPTED = "accepted"              # Amélioré → garder
    REJECTED = "rejected"              # Pas amélioré → rejeter + analyser via Lamed
    QUARANTINED = "quarantined"        # Prometteur mais pas assez bon (Chesed-dans-Gevurah)
    TENSION_DETECTED = "tension_detected"  # Contradiction → vérifier via Tiferet


class DomainType(str, Enum):
    """Domaines d'auto-jugement."""
    WRITING = "writing"
    CODE = "code"
    ANALYSIS = "analysis"
    RESEARCH = "research"


@dataclass
class DomainScore:
    """Score brut retourné par un DomainJudge.

    quality : 0-1, la métrique primaire du domaine (la 'loss').
    metrics : dict détaillé des sous-métriques du domaine.
    """
    quality: float
    metrics: dict[str, float] = field(default_factory=dict)
    explanation: str = ""


@dataclass
class MultiScore:
    """Évaluation multi-sephirothique — 5 axes au lieu d'une seule loss.

    Gevurah : qualité brute (la métrique dure).
    Chesed  : diversité / originalité des approches.
    Tiferet : cohérence avec l'ensemble existant.
    Hod     : interprétabilité / clarté.
    Yesod   : reproductibilité / fiabilité.
    """
    gevurah: float
    chesed: float
    tiferet: float
    hod: float
    yesod: float
    overall: float = 0.0

    def __post_init__(self):
        if self.overall == 0.0:
            self.overall = (
                self.gevurah * 0.35
                + self.chesed * 0.15
                + self.tiferet * 0.20
                + self.hod * 0.15
                + self.yesod * 0.15
            )


@dataclass
class DomainConfig:
    """Configuration d'un domaine d'auto-jugement."""
    id: str
    display_name: str
    loss_function: str
    config: dict = field(default_factory=dict)
    created_at: datetime | None = None


@dataclass
class Experiment:
    """Une expérience dans le Karpathy Loop."""
    id: UUID
    domain_id: str
    hypothesis: str
    original_content: str | None = None
    modified_content: str | None = None

    # Scores multi-sephirothiques
    score_gevurah: float | None = None
    score_chesed: float | None = None
    score_tiferet: float | None = None
    score_hod: float | None = None
    score_yesod: float | None = None
    score_overall: float | None = None

    # Décision
    decision: str | None = None

    # Lien vers FailureToInsight (sentier Lamed)
    failure_analysis_id: UUID | None = None
    nitzotzot_extracted: bool = False

    # Méta
    duration_seconds: float | None = None
    budget_seconds: float = 300.0
    loop_iteration: int | None = None
    created_at: datetime | None = None


@dataclass
class IterationResult:
    """Résultat d'une itération dans le loop."""
    iteration: int
    hypothesis: str
    domain_score: DomainScore
    multi_score: MultiScore
    decision: str
    failure_analysis_id: UUID | None = None
    nitzotzot_extracted: bool = False
    explanation: str = ""


@dataclass
class LoopResult:
    """Bilan d'un cycle complet du Karpathy Loop."""
    final_content: str
    iterations: list[IterationResult]
    accepted: int = 0
    rejected: int = 0
    quarantined: int = 0
    tension_detected: int = 0
    insights_extracted: int = 0

    def __post_init__(self):
        if not self.accepted and not self.rejected:
            self.accepted = sum(
                1 for i in self.iterations if i.decision == "accepted"
            )
            self.rejected = sum(
                1 for i in self.iterations if i.decision == "rejected"
            )
            self.quarantined = sum(
                1 for i in self.iterations if i.decision == "quarantined"
            )
            self.tension_detected = sum(
                1 for i in self.iterations if i.decision == "tension_detected"
            )
            self.insights_extracted = sum(
                1 for i in self.iterations if i.nitzotzot_extracted
            )

    @property
    def total(self) -> int:
        return len(self.iterations)

    @property
    def acceptance_rate(self) -> float:
        return self.accepted / self.total if self.total > 0 else 0.0

    @property
    def rejection_rate(self) -> float:
        return self.rejected / self.total if self.total > 0 else 0.0
