"""Modèles de données — Binah-de-Hod : classification structurée."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class DomainScore:
    """Résultat d'évaluation sur un domaine."""

    domain: str
    model_id: str
    score: float            # 0-1, proportion de réponses correctes
    brier_score: float      # calibration (0 = parfait)
    n_evals: int
    eval_results: list[EvalResult] = field(default_factory=list)
    last_eval: datetime | None = None


@dataclass
class EvalResult:
    """Résultat d'une question d'évaluation individuelle."""

    question: str
    expected: str
    actual: str
    correct: bool
    confidence: float       # confiance affichée par le modèle
    latency_ms: float = 0.0


@dataclass
class RouteDecision:
    """Décision de routage pour une requête."""

    query: str
    detected_domain: str
    competence_score: float
    routed_to: str          # model_id
    did_decline: bool
    decline_reason: str | None = None


@dataclass
class CalibrationReport:
    """Rapport de calibration — Brier score par domaine."""

    model_id: str
    by_domain: dict[str, float]     # domain -> brier_score
    avg_brier: float
    overconfident_domains: list[str]  # confiance > score réel
    underconfident_domains: list[str]
    uncalibrated_domains: list[str]  # jamais évalués


@dataclass
class SelfDescription:
    """Hod-de-Hod : le système se décrit lui-même."""

    model_id: str
    total_domains: int
    evaluated_domains: int
    strong_domains: list[str]       # score > 0.7
    weak_domains: list[str]         # score < 0.4
    unknown_domains: list[str]      # jamais évalués
    avg_competence: float
    avg_brier: float
    total_queries_routed: int
    total_declined: int
    decline_rate: float
