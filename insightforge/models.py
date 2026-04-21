"""Modèles de données pour InsightForge — Chokmah.

InsightSession : session de forge autour d'une question
CandidateInsight : insight candidat avant validation
NoveltyAssessment : évaluation de la nouveauté
InsightValidation : résultat de la triple validation
EmergenceSignal : signal d'émergence détecté
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class CandidateInsight:
    """Insight candidat — pas encore validé."""
    description: str
    source_module: str = ""
    domain: str = ""
    novelty_score: float = 0.0
    confidence: float = 0.5
    status: str = "candidate"   # candidate, validated, rejected, insight, pending
    rejection_reason: str = ""
    # Triple validation
    binah_validated: bool = False
    gevurah_validated: bool = False
    daat_validated: bool = False
    # Liens
    connects_domains: list[str] = field(default_factory=list)
    source_connections: list[UUID] = field(default_factory=list)

    id: UUID | None = None
    session_id: UUID | None = None
    created_at: datetime | None = None


@dataclass
class NoveltyAssessment:
    """Évaluation de la nouveauté d'un insight candidat."""
    is_genuinely_new: bool = False
    already_known: bool = False
    is_reformulation: bool = False
    is_trivial: bool = False
    is_cross_domain: bool = False
    novelty_score: float = 0.0
    reasoning: str = ""

    id: UUID | None = None
    candidate_id: UUID | None = None
    created_at: datetime | None = None


@dataclass
class InsightValidation:
    """Résultat de la triple validation Binah + Gevurah + Da'at."""
    is_valid: bool = False
    binah_ok: bool = False        # Causalité vérifiée
    gevurah_ok: bool = False      # Qualité suffisante
    daat_ok: bool = False         # Pas d'erreur prédite
    binah_detail: str = ""
    gevurah_detail: str = ""
    daat_detail: str = ""
    confidence: float = 0.5

    @property
    def triple_validated(self) -> bool:
        return self.binah_ok and self.gevurah_ok and self.daat_ok


@dataclass
class EmergenceSignal:
    """Signal d'émergence détecté dans le système."""
    signal_type: str = ""         # cross_domain, tension_resolved, non_deducible, synergy
    description: str = ""
    strength: float = 0.0         # 0.0 - 1.0
    modules_involved: list[str] = field(default_factory=list)
    evidence: str = ""


@dataclass
class InsightSession:
    """Session de forge — mobilisation de tous les modules."""
    question: str
    domain: str = ""
    status: str = "active"        # active, completed, aborted
    modules_consulted: list[str] = field(default_factory=list)
    shov_context: str = ""  # Ratzo v'Shov — guidance issue des rejets précédents
    # Résultats
    candidates: list[CandidateInsight] = field(default_factory=list)
    validated_insights: list[CandidateInsight] = field(default_factory=list)
    rejected: list[CandidateInsight] = field(default_factory=list)
    pending: list[CandidateInsight] = field(default_factory=list)
    novelty_assessments: list[NoveltyAssessment] = field(default_factory=list)
    validations: list[InsightValidation] = field(default_factory=list)
    emergence_signals: list[EmergenceSignal] = field(default_factory=list)
    # Compteurs
    total_candidates: int = 0
    insights_found: int = 0
    rejected_count: int = 0
    pearl_level: str = "association"

    id: UUID | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None

    def add_candidate(self, candidate: CandidateInsight) -> None:
        self.candidates.append(candidate)
        self.total_candidates += 1

    def mark_as_insight(
        self, candidate: CandidateInsight,
        novelty: NoveltyAssessment,
        validation: InsightValidation,
    ) -> None:
        candidate.status = "insight"
        candidate.novelty_score = novelty.novelty_score
        candidate.confidence = validation.confidence
        self.validated_insights.append(candidate)
        self.novelty_assessments.append(novelty)
        self.validations.append(validation)
        self.insights_found += 1

    def reject_candidate(self, candidate: CandidateInsight, reason: str) -> None:
        candidate.status = "rejected"
        candidate.rejection_reason = reason
        self.rejected.append(candidate)
        self.rejected_count += 1

    def defer_candidate(self, candidate: CandidateInsight, reason: str) -> None:
        """Mettre en attente — pas rejeté, réévaluable plus tard."""
        candidate.status = "pending"
        candidate.rejection_reason = reason
        self.pending.append(candidate)

    def surviving_candidates(self) -> list[CandidateInsight]:
        """Candidats non encore rejetés."""
        return [c for c in self.candidates if c.status == "candidate"]

    def complete(self) -> None:
        self.status = "completed"
        self.completed_at = datetime.now()
