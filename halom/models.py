"""Data models for the Halom dream cycle.

All structures are pure data — no LLM calls, no I/O.
Following the malakhim pattern: @dataclass with field(default_factory).
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class Mechanism(str, enum.Enum):
    """The 4 creative mechanisms of the Chalom phase.

    Tzeruf (צירוף) — collision of unrelated concepts (Abulafia).
    Structural — partial graph isomorphism (MCS + spectral).
    Abduction — minimum description length explanation.
    Samael (סמאל) — inversion of accepted mappings.
    """

    TZERUF = "tzeruf"
    STRUCTURAL = "structural"
    ABDUCTION = "abduction"
    SAMAEL = "samael"


@dataclass
class DreamCandidate:
    """A single mapping idea generated during the Chalom phase.

    Zohar I, 149b: the dream passes through Gabriel/Gevurah —
    constrained exploration, not free association.
    """

    concept_k: str
    concept_ia: str
    mechanism: Mechanism
    structure_commune: str
    prediction: str
    score_brut: float = 0.0
    bisociation: float = 0.5
    mdl_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DreamResult:
    """Outcome of a candidate after Birur filtering.

    Berakhot 57b: 1/60 ratio — only the signal survives.
    """

    candidate: DreamCandidate
    accepted: bool
    adversaire_verdict: str = ""
    adversaire_arguments: list[str] = field(default_factory=list)
    mapping_complet: str = ""


@dataclass
class AuditFinding:
    """A single weakness found during audit."""

    concept_k: str
    concept_ia: str
    score: float
    problem: str


@dataclass
class AuditState:
    """Snapshot of project health from Phase ① Hod.

    Hod = self-knowledge. The Halom must know the project
    before it can dream about it.
    """

    total_elements: int
    mapped_elements: int
    weak_mappings: list[AuditFinding] = field(default_factory=list)
    orphan_k: list[str] = field(default_factory=list)
    orphan_ia: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)


@dataclass
class CycleReport:
    """Full report of a dream cycle.

    Reshimu (רשימו) = the trace left behind.
    """

    cycle_number: int
    date: str
    candidates_generated: int
    pre_filter_survivors: int
    adversaire_survivors: int
    results: list[DreamResult] = field(default_factory=list)
    thompson_state: dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0

    @property
    def ratio(self) -> float:
        """Survival ratio — should approach 1/60 ≈ 0.017."""
        if self.candidates_generated == 0:
            return 0.0
        return self.adversaire_survivors / self.candidates_generated
