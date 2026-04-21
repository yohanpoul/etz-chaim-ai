"""Modèles de données — ExplorationEngine (Chesed).

Le vocabulaire de l'exploration :
- ConnectionType : les 5 types de connexion inter-domaines
- Connection : un pont entre deux concepts de domaines différents
- Exploration : une session d'exploration avec budget et résultats
- ExplorationResult : le bilan d'une exploration complète
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID


class ConnectionType(str, Enum):
    """Les 6 types de connexion inter-domaines."""
    ANALOGY = "analogy"              # A est structurellement similaire à B
    CAUSAL = "causal"                # A pourrait causer/influencer B
    CONTRADICTS = "contradicts"      # A contredit B (tension productive)
    COMPLEMENTS = "complements"      # A complète B
    PATTERN_SHARED = "pattern_shared"  # A et B partagent un pattern commun
    GEMATRIA_EQUIVALENCE = "gematria_equivalence"  # A et B partagent la même valeur gématrique


class ExplorationStatus(str, Enum):
    """Statut d'une exploration."""
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED_NOVELTY = "stopped_novelty"    # Anti-Gamchicoth : plus rien de nouveau
    STOPPED_BUDGET = "stopped_budget"      # Budget épuisé


@dataclass
class Connection:
    """Un pont entre deux concepts de domaines différents."""
    concept_a: str
    domain_a: str
    concept_b: str
    domain_b: str
    connection_type: str
    description: str
    novelty_score: float = 0.0
    relevance_score: float = 0.0
    confidence: float = 0.5
    id: UUID | None = None
    exploration_id: UUID | None = None
    epistememory_id: UUID | None = None
    created_at: datetime | None = None


@dataclass
class Exploration:
    """Une session d'exploration inter-domaines."""
    id: UUID
    seed_query: str
    seed_domain: str
    target_domains: list[str] = field(default_factory=list)
    connections_found: int = 0
    novel_connections: int = 0
    max_connections: int = 50
    max_duration_seconds: int = 600
    novelty_threshold: float = 0.3
    status: str = "running"
    created_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass
class ExplorationResult:
    """Bilan d'une exploration complète."""
    exploration_id: UUID | None = None
    connections: list[Connection] = field(default_factory=list)
    status: str = "completed"
    domains_explored: list[str] = field(default_factory=list)

    @property
    def total_connections(self) -> int:
        return len(self.connections)

    @property
    def novel_connections(self) -> int:
        return sum(1 for c in self.connections if c.novelty_score >= 0.3)

    @property
    def avg_novelty(self) -> float:
        if not self.connections:
            return 0.0
        return sum(c.novelty_score for c in self.connections) / len(self.connections)

    @property
    def avg_relevance(self) -> float:
        if not self.connections:
            return 0.0
        return sum(c.relevance_score for c in self.connections) / len(self.connections)

    @property
    def by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for c in self.connections:
            counts[c.connection_type] = counts.get(c.connection_type, 0) + 1
        return counts
