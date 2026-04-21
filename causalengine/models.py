"""Modèles de données pour CausalEngine — Binah.

CausalGraph : DAG causal avec noeuds et arêtes
CausalClaim : affirmation causale individuelle vérifiable
Confounder : variable confondante détectée
EvidenceLevel, PearlLevel : niveaux de preuve
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID


class PearlLevel(str, Enum):
    """Les 3 niveaux de la hiérarchie causale de Pearl."""
    ASSOCIATION = "association"           # P(Y|X) — observer
    INTERVENTION = "intervention"        # P(Y|do(X)) — intervenir
    COUNTERFACTUAL = "counterfactual"    # P(Y_x|X', Y') — imaginer


class EvidenceLevel(str, Enum):
    """Niveau de preuve d'une affirmation causale."""
    CORRELATION_ONLY = "correlation_only"
    OBSERVED_ASSOCIATION = "observed_association"
    PROBABLE_CAUSATION = "probable_causation"
    DEMONSTRATED_CAUSATION = "demonstrated_causation"


# Hiérarchie stricte pour comparaisons
EVIDENCE_RANK = {
    "correlation_only": 0,
    "observed_association": 1,
    "probable_causation": 2,
    "demonstrated_causation": 3,
}


class DirectionVerdict(str, Enum):
    """Résultat de la vérification de direction causale."""
    FORWARD = "forward"         # A → B confirmé
    REVERSE = "reverse"         # B → A plus plausible
    BIDIRECTIONAL = "bidirectional"  # A ↔ B
    INDETERMINATE = "indeterminate"  # On ne sait pas


@dataclass
class CausalNode:
    """Noeud dans un DAG causal."""
    node_id: str
    name: str
    node_type: str = "variable"   # variable, intervention, outcome
    domain: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.node_id,
            "name": self.name,
            "type": self.node_type,
            "domain": self.domain,
        }


@dataclass
class CausalEdge:
    """Arête dans un DAG causal."""
    source: str       # node_id source
    target: str       # node_id cible
    edge_type: str = "causes"   # causes, confounds, mediates
    confidence: float = 0.5
    evidence_level: str = "correlation_only"

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "edge_type": self.edge_type,
            "confidence": self.confidence,
            "evidence_level": self.evidence_level,
        }


@dataclass
class CausalGraph:
    """DAG causal — le cœur de Binah."""
    name: str
    nodes: list[CausalNode] = field(default_factory=list)
    edges: list[CausalEdge] = field(default_factory=list)
    domain: str = ""
    description: str = ""
    confounders_checked: bool = False
    evidence_level: str = "association"
    source_data: dict = field(default_factory=dict)

    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def node_ids(self) -> set[str]:
        return {n.node_id for n in self.nodes}

    def get_node(self, node_id: str) -> CausalNode | None:
        for n in self.nodes:
            if n.node_id == node_id:
                return n
        return None

    def parents(self, node_id: str) -> list[str]:
        """Noeuds parents (causes directes)."""
        return [e.source for e in self.edges if e.target == node_id]

    def children(self, node_id: str) -> list[str]:
        """Noeuds enfants (effets directs)."""
        return [e.target for e in self.edges if e.source == node_id]


@dataclass
class Confounder:
    """Variable confondante détectée."""
    confounder_name: str
    confounder_domain: str = ""
    plausibility: float = 0.5
    controlled: bool = False
    how_controlled: str = ""

    id: UUID | None = None
    claim_id: UUID | None = None
    created_at: datetime | None = None


@dataclass
class CausalClaim:
    """Affirmation causale individuelle — "A cause B"."""
    cause: str
    effect: str
    evidence_level: str = "correlation_only"
    known_confounders: list[str] = field(default_factory=list)
    confounders_controlled: bool = False
    direction_verified: bool = False
    reverse_plausible: bool | None = None
    appropriate_language: str = ""
    confidence: float = 0.5

    id: UUID | None = None
    graph_id: UUID | None = None
    created_at: datetime | None = None


@dataclass
class DirectionAssessment:
    """Résultat de verify_direction."""
    verdict: str = "indeterminate"  # forward, reverse, bidirectional, indeterminate
    forward_plausibility: float = 0.5
    reverse_plausibility: float = 0.5
    reasoning: str = ""


@dataclass
class LanguageCorrection:
    """Correction de langage — remplacement d'une affirmation causale."""
    original: str
    corrected: str
    evidence_level: str = "correlation_only"
    reason: str = ""


@dataclass
class CausalAssessment:
    """Résultat complet d'un check_claim."""
    claim: CausalClaim
    confounders: list[Confounder] = field(default_factory=list)
    direction: DirectionAssessment = field(default_factory=DirectionAssessment)
    pearl_level: str = "association"
    language_correction: LanguageCorrection | None = None
    warnings: list[str] = field(default_factory=list)
