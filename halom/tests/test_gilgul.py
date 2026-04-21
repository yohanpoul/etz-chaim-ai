"""Tests for Gilgul (Ouroboros) data models.

Gilgul = Halom dreaming about its own genome.
Pure data: Genome, Mutation, GilgulReport.
"""
from __future__ import annotations

import json

from halom.gilgul import Genome, GilgulReport, Mutation, VALID_VERDICTS
from halom.models import CycleReport, Mechanism


class TestGenome:
    """Genome — full parameter set of Halom."""

    def test_create_genome(self):
        """Minimal genome with defaults."""
        g = Genome(version=1)
        assert g.version == 1
        assert g.ancestor is None
        assert g.mutations_applied == []
        assert g.thompson == {}
        assert g.birur == {}
        assert g.cycle == {}
        assert g.mechanisms == {}
        assert g.meta == {}

    def test_genome_to_dict(self):
        """Serialization preserves all fields."""
        g = Genome(
            version=3,
            ancestor=2,
            mutations_applied=["lower_birur_threshold"],
            thompson={"alpha": 1, "beta": 1},
            birur={"threshold": 0.4},
            cycle={"max_candidates": 50},
            mechanisms={"tzeruf": {"weight": 0.5}},
            meta={"origin": "test"},
        )
        d = g.to_dict()
        assert d["version"] == 3
        assert d["ancestor"] == 2
        assert d["mutations_applied"] == ["lower_birur_threshold"]
        assert d["thompson"]["alpha"] == 1
        assert d["birur"]["threshold"] == 0.4
        assert d["meta"]["origin"] == "test"

    def test_genome_from_dict(self):
        """Deserialization round-trip from dict."""
        data = {
            "version": 5,
            "ancestor": 4,
            "mutations_applied": ["add_samael_boost"],
            "thompson": {"alpha": 2},
            "birur": {},
            "cycle": {},
            "mechanisms": {},
            "meta": {},
        }
        g = Genome.from_dict(data)
        assert g.version == 5
        assert g.ancestor == 4
        assert g.mutations_applied == ["add_samael_boost"]
        assert g.thompson == {"alpha": 2}

    def test_genome_json_roundtrip(self):
        """Full JSON serialize/deserialize preserves identity."""
        g = Genome(
            version=7,
            ancestor=6,
            mutations_applied=["m1", "m2"],
            thompson={"alpha": 3, "beta": 5},
            birur={"threshold": 0.35},
            cycle={"max_candidates": 100},
            mechanisms={"structural": {"enabled": True}},
            meta={"note": "roundtrip test"},
        )
        json_str = json.dumps(g.to_dict())
        g2 = Genome.from_dict(json.loads(json_str))
        assert g2.version == g.version
        assert g2.ancestor == g.ancestor
        assert g2.mutations_applied == g.mutations_applied
        assert g2.thompson == g.thompson
        assert g2.birur == g.birur
        assert g2.cycle == g.cycle
        assert g2.mechanisms == g.mechanisms
        assert g2.meta == g.meta


class TestMutation:
    """Mutation — a single proposed change to the genome."""

    def test_create_mutation(self):
        """Standard testable mutation."""
        m = Mutation(
            mutation_id="mut-001",
            mechanism=Mechanism.SAMAEL,
            target="birur.threshold",
            old_value=0.5,
            new_value=0.35,
            mutation_type="modify",
            rationale="Lower threshold to let more candidates through",
            prediction="Survival ratio increases from 0.02 to 0.05",
            testable=True,
        )
        assert m.mutation_id == "mut-001"
        assert m.mechanism == Mechanism.SAMAEL
        assert m.target == "birur.threshold"
        assert m.old_value == 0.5
        assert m.new_value == 0.35
        assert m.mutation_type == "modify"
        assert m.testable is True

    def test_mutation_to_dict(self):
        """Serialization includes mechanism value."""
        m = Mutation(
            mutation_id="mut-002",
            mechanism=Mechanism.TZERUF,
            target="thompson.alpha",
            old_value=1,
            new_value=2,
            mutation_type="modify",
            rationale="Boost exploration",
            prediction="More diverse candidates",
            testable=True,
        )
        d = m.to_dict()
        assert d["mutation_id"] == "mut-002"
        assert d["mechanism"] == "tzeruf"
        assert d["target"] == "thompson.alpha"
        assert d["old_value"] == 1
        assert d["new_value"] == 2
        assert d["testable"] is True

    def test_mutation_non_testable(self):
        """Non-testable mutation (e.g., meta change)."""
        m = Mutation(
            mutation_id="mut-003",
            mechanism=Mechanism.ABDUCTION,
            target="meta.description",
            old_value="old desc",
            new_value="new desc",
            mutation_type="modify",
            rationale="Clarify genome purpose",
            prediction="No measurable effect",
            testable=False,
        )
        assert m.testable is False
        d = m.to_dict()
        assert d["testable"] is False


class TestGilgulReport:
    """GilgulReport — full Ouroboros cycle report."""

    def test_create_report(self):
        """Report with two genomes and a verdict."""
        g_current = Genome(version=1)
        g_mutant = Genome(version=2, ancestor=1, mutations_applied=["m1"])
        report = GilgulReport(
            gilgul_number=1,
            date="2026-04-11",
            genome_current=g_current,
            genome_mutant=g_mutant,
            mutations_generated=5,
            mutations_survivors=2,
            test_cycle_report=None,
            verdict="ADOPTE",
            verdict_rationale="Mutant outperforms current on survival ratio",
        )
        assert report.gilgul_number == 1
        assert report.genome_current.version == 1
        assert report.genome_mutant.version == 2
        assert report.genome_mutant.ancestor == 1
        assert report.mutations_generated == 5
        assert report.mutations_survivors == 2
        assert report.test_cycle_report is None
        assert report.verdict == "ADOPTE"

    def test_valid_verdicts(self):
        """VALID_VERDICTS contains exactly the three expected values."""
        assert VALID_VERDICTS == frozenset({"ADOPTE", "FUSION", "REVERT"})
        assert isinstance(VALID_VERDICTS, frozenset)
