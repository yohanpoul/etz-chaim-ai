"""Gilgul (גלגול) — Ouroboros data models for Halom self-modification.

Gilgul = transmigration. Here: Halom dreams about its own genome,
proposing mutations, testing them, and deciding whether to adopt.

Pure data — no LLM calls, no I/O.
Following the malakhim pattern: @dataclass with field(default_factory).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from halom.models import CycleReport, Mechanism


# -------------------------------------------------------------------
# Valid verdicts for a Gilgul cycle
# -------------------------------------------------------------------
VALID_VERDICTS: frozenset[str] = frozenset({"ADOPTE", "FUSION", "REVERT"})


# -------------------------------------------------------------------
# Genome — full parameter set of Halom
# -------------------------------------------------------------------
@dataclass
class Genome:
    """The complete parameter set (DNA) of a Halom instance.

    Each Gilgul cycle produces a mutant Genome that is tested
    against the current one. The winner becomes the new baseline.
    """

    version: int
    ancestor: int | None = None
    mutations_applied: list[str] = field(default_factory=list)
    thompson: dict[str, Any] = field(default_factory=dict)
    birur: dict[str, Any] = field(default_factory=dict)
    cycle: dict[str, Any] = field(default_factory=dict)
    mechanisms: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (JSON-safe)."""
        return {
            "version": self.version,
            "ancestor": self.ancestor,
            "mutations_applied": list(self.mutations_applied),
            "thompson": dict(self.thompson),
            "birur": dict(self.birur),
            "cycle": dict(self.cycle),
            "mechanisms": dict(self.mechanisms),
            "meta": dict(self.meta),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Genome:
        """Deserialize from a plain dict."""
        return cls(
            version=data["version"],
            ancestor=data.get("ancestor"),
            mutations_applied=list(data.get("mutations_applied", [])),
            thompson=dict(data.get("thompson", {})),
            birur=dict(data.get("birur", {})),
            cycle=dict(data.get("cycle", {})),
            mechanisms=dict(data.get("mechanisms", {})),
            meta=dict(data.get("meta", {})),
        )


# -------------------------------------------------------------------
# Mutation — a single proposed change to the genome
# -------------------------------------------------------------------
@dataclass
class Mutation:
    """A single proposed change to the Halom genome.

    Each mutation targets a specific parameter path (e.g. "birur.threshold"),
    records old/new values, and carries a testable prediction.
    """

    mutation_id: str
    mechanism: Mechanism
    target: str
    old_value: Any
    new_value: Any
    mutation_type: str  # "modify" | "add" | "remove"
    rationale: str
    prediction: str
    testable: bool

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (JSON-safe)."""
        return {
            "mutation_id": self.mutation_id,
            "mechanism": self.mechanism.value,
            "target": self.target,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "mutation_type": self.mutation_type,
            "rationale": self.rationale,
            "prediction": self.prediction,
            "testable": self.testable,
        }


# -------------------------------------------------------------------
# GilgulReport — full Ouroboros cycle report
# -------------------------------------------------------------------
@dataclass
class GilgulReport:
    """Full report of a Gilgul (Ouroboros) cycle.

    Records: current genome, mutant genome, mutations applied,
    test results, and the final verdict (ADOPTE / FUSION / REVERT).
    """

    gilgul_number: int
    date: str
    genome_current: Genome
    genome_mutant: Genome
    mutations_generated: int
    mutations_survivors: int
    test_cycle_report: CycleReport | None
    verdict: str
    verdict_rationale: str
