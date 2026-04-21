"""Modèles de données — Binah de Tiferet.

La structure formelle du dissensus : tensions, synthèses, questions ouvertes.
Thagirion (les Disputeurs) = le mode de défaillance de Tiferet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID


class TensionType(str, Enum):
    """Types de tension entre conclusions."""

    CONTRADICTION = "contradiction"           # A et B s'excluent
    NUANCE = "nuance"                         # divergence non essentielle
    SCOPE_CONFLICT = "scope_conflict"         # contextes différents
    FRAMING_DIFFERENCE = "framing_difference" # même réalité, cadrage incompatible


class ResolutionStatus(str, Enum):
    """Statut de résolution d'une tension."""

    OPEN = "open"                     # non résolue
    RESOLVED = "resolved"             # résolue par synthèse
    IRREDUCIBLE = "irreducible"       # coincidentia oppositorum


class SynthesisMode(str, Enum):
    """Mode de sortie de l'engine."""

    SYNTHESIS = "synthesis"   # les sources convergent suffisamment
    DISSENSUS = "dissensus"   # refus de conclure — divergence trop forte


class SourceType(str, Enum):
    """Types de sources de conclusions."""

    PAPER = "paper"
    MODEL = "model"
    TRADITION = "tradition"
    EXPERIMENT = "experiment"
    HUMAN = "human"
    SYSTEM = "system"


class Priority(str, Enum):
    """Priorité d'une question ouverte."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Conclusion:
    """Une conclusion/claim d'une source spécifique.

    Chesed du processus : accueillir chaque voix sans la filtrer.
    """

    id: UUID
    content: str
    source_label: str        # qui affirme
    source_type: str         # paper, model, tradition, experiment, human, system
    domain: str | None = None
    confidence: float = 0.5
    metadata: dict | None = None
    created_at: datetime | None = None


@dataclass
class Tension:
    """Tension détectée entre deux conclusions.

    Gevurah du processus : identifier les incompatibilités.
    """

    id: UUID
    conclusion_a_id: UUID
    conclusion_b_id: UUID
    tension_type: str        # contradiction, nuance, scope_conflict, framing_difference
    divergence_score: float  # 0 = accord, 1 = contradiction totale
    description: str | None = None
    resolution_status: str = "open"
    resolved_by: UUID | None = None
    created_at: datetime | None = None


@dataclass
class Synthesis:
    """Synthèse ou dissensus — le verdict de Tiferet.

    Mode synthesis : les sources convergent → conclusion unifiée.
    Mode dissensus : les sources divergent → exposer la tension, refuser de conclure.

    "Jacob ne vainquit pas l'ange — il lutta jusqu'à l'aube et en sortit nommé."
    """

    id: UUID
    mode: str                    # synthesis ou dissensus
    content: str
    sources_used: list[UUID]
    source_coverage: float       # % de conclusions pertinentes incluses
    max_divergence: float        # divergence maximale dans l'ensemble
    confidence: float
    domain: str | None = None
    epistememory_id: UUID | None = None
    created_at: datetime | None = None


@dataclass
class OpenQuestion:
    """Question ouverte — pas un bug, une question vivante.

    "Les 70 faces de la Torah : le sens n'est jamais épuisé
    par une lecture unique."
    """

    id: UUID
    tension_id: UUID
    question: str
    missing_evidence: str | None = None
    priority: str = "medium"
    domain: str | None = None
    created_at: datetime | None = None
    resolved_at: datetime | None = None


@dataclass
class ConsistencyReport:
    """Rapport de cohérence — le diagnostic de Tiferet."""

    total_conclusions: int
    total_tensions: int
    tensions_by_type: dict[str, int]
    avg_divergence: float
    max_divergence: float
    open_questions: int
    source_labels: list[str]
    most_divergent_pair: tuple[UUID, UUID] | None = None
    health: str = "consistent"   # consistent, tensions_detected, highly_divergent
