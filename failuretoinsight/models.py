"""Modèles de données — Binah du sentier Lamed.

La taxonomie des Qliphoth comme système de classification des échecs.
Chaque Qliphah = le mode de défaillance SPÉCIFIQUE d'une Sephirah.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID


class Qliphah(str, Enum):
    """Les 10 Qliphoth — taxonomie des modes de défaillance."""

    GAMALIEL = "gamaliel"       # Yesod — corruption mémoire
    SAMAEL = "samael"           # Hod — fausse confiance, mauvais routage
    AARAB_ZARAQ = "aarab_zaraq" # Netzach — retries infinis, zombie
    THAGIRION = "thagirion"     # Tiferet — fausse synthèse, harmonie forcée
    GOLACHAB = "golachab"       # Gevurah — sur-filtrage destructeur
    GAMCHICOTH = "gamchicoth"   # Chesed — scope creep, accumulation infinie
    HATEHOM = "hatehom"         # Da'at — déconnexion intention/exécution
    SATARIEL = "satariel"       # Binah — faux patterns, causalité inventée
    GHAGIEL = "ghagiel"         # Chokmah — divergence sans convergence
    THAUMIEL = "thaumiel"       # Keter — intentions contradictoires
    UNKNOWN = "unknown"


class Severity(str, Enum):
    """4 niveaux de sévérité (Tanya ch. 7)."""

    NOGAH = "nogah"     # Warning — récupérable
    RUACH = "ruach"     # Error — se propage
    ANAN = "anan"       # Silent failure — semble OK mais corrompu
    MAMASH = "mamash"   # Fatal — reconstruction nécessaire


class InsightType(str, Enum):
    """Types de Nitzotzot (étincelles) extractibles."""

    PATTERN = "pattern"           # Motif récurrent identifié
    CONSTRAINT = "constraint"     # Contrainte découverte
    OPPORTUNITY = "opportunity"   # Direction prometteuse révélée
    WARNING = "warning"           # Danger à éviter
    ANTI_PATTERN = "anti_pattern" # Pattern à ne PAS reproduire


class EdgeType(str, Enum):
    """Types de liens dans le graphe des échecs."""

    SIMILAR_FAILURE = "similar_failure"
    SAME_ROOT_CAUSE = "same_root_cause"
    ESCALATION = "escalation"       # Nogah→Ruach→Anan→Mamash
    CONTRADICTS = "contradicts"     # Deux analyses se contredisent
    LEADS_TO = "leads_to"           # Un échec en cause un autre


@dataclass
class FailureAnalysis:
    """Analyse d'un échec — le résultat du Birur."""

    id: UUID
    source_type: str    # subtask, experiment, hypothesis, external
    source_id: UUID | None
    description: str
    qliphah: str        # classification via la taxonomie
    severity: str       # nogah, ruach, anan, mamash
    root_cause: str | None = None
    context: dict | None = None
    domain: str | None = None
    created_at: datetime | None = None
    insights: list[Insight] = field(default_factory=list)


@dataclass
class Insight:
    """Nitzotz — une étincelle extraite de la Qliphah.

    "Même dans les Qliphoth les plus denses, des Nitzotzot de lumière
    attendent d'être libérés" — Etz Chaim, Sha'ar HaKlipot.
    """

    id: UUID
    analysis_id: UUID
    content: str
    insight_type: str   # pattern, constraint, opportunity, warning, anti_pattern
    confidence: float
    domain: str | None = None
    epistememory_id: UUID | None = None
    created_at: datetime | None = None


@dataclass
class FailureGraphEdge:
    """Arête dans le graphe de connaissance des échecs."""

    id: UUID
    from_analysis_id: UUID
    to_analysis_id: UUID
    edge_type: str
    weight: float = 1.0
    created_at: datetime | None = None


@dataclass
class FailureKnowledgeGraph:
    """Le graphe complet — vue d'ensemble des échecs et de leurs liens."""

    analyses: list[FailureAnalysis]
    edges: list[FailureGraphEdge]
    patterns: dict[str, int]         # qliphah -> count
    domains_affected: list[str]
    most_common_qliphah: str | None
    total_insights: int


@dataclass
class HypothesisGuidance:
    """Guidance basée sur le graphe — éviter les chemins déjà empruntés.

    Lamed pointe vers Tiferet : la guidance aide la synthèse future.
    """

    avoid_patterns: list[str]       # qliphoth récurrentes
    promising_directions: list[str] # domaines/approches non essayés
    recurring_root_causes: list[str]
    total_failures_analyzed: int
    confidence: float
