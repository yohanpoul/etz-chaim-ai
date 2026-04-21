"""Tests for Halom data models."""
from __future__ import annotations

from halom.models import (
    DreamCandidate,
    DreamResult,
    AuditFinding,
    AuditState,
    CycleReport,
    Mechanism,
)


class TestDreamCandidate:
    """DreamCandidate — a single generated mapping idea."""

    def test_creation_with_required_fields(self):
        """Minimum viable candidate."""
        c = DreamCandidate(
            concept_k="Reshimu",
            concept_ia="Residual connections",
            mechanism=Mechanism.TZERUF,
            structure_commune="Information preserved through contraction",
            prediction="Skip connection strength ∝ compression ratio",
        )
        assert c.concept_k == "Reshimu"
        assert c.mechanism == Mechanism.TZERUF
        assert c.score_brut == 0.0
        assert c.metadata == {}

    def test_mechanism_enum_values(self):
        """4 mechanisms match the spec."""
        assert Mechanism.TZERUF.value == "tzeruf"
        assert Mechanism.STRUCTURAL.value == "structural"
        assert Mechanism.ABDUCTION.value == "abduction"
        assert Mechanism.SAMAEL.value == "samael"


class TestDreamResult:
    """DreamResult — outcome after Birur filtering."""

    def test_accepted_result(self):
        candidate = DreamCandidate(
            concept_k="Reshimu",
            concept_ia="Residual connections",
            mechanism=Mechanism.TZERUF,
            structure_commune="Trace through contraction",
            prediction="Testable prediction",
            score_brut=0.73,
        )
        r = DreamResult(candidate=candidate, accepted=True, adversaire_verdict="tient")
        assert r.accepted is True
        assert r.candidate.score_brut == 0.73

    def test_rejected_result(self):
        candidate = DreamCandidate(
            concept_k="X",
            concept_ia="Y",
            mechanism=Mechanism.SAMAEL,
            structure_commune="Forced",
            prediction="None",
            score_brut=0.2,
        )
        r = DreamResult(candidate=candidate, accepted=False, adversaire_verdict="ne tient pas")
        assert r.accepted is False


class TestAuditState:
    """AuditState — snapshot of project health."""

    def test_creation(self):
        state = AuditState(
            total_elements=474,
            mapped_elements=200,
            weak_mappings=[
                AuditFinding(concept_k="X", concept_ia="Y", score=0.3, problem="Weak analogy"),
            ],
            orphan_k=["Reshimu"],
            orphan_ia=["MoE routing"],
            contradictions=[],
        )
        assert state.total_elements == 474
        assert len(state.weak_mappings) == 1
        assert state.weak_mappings[0].score == 0.3


class TestCycleReport:
    """CycleReport — full report of a dream cycle."""

    def test_creation(self):
        import pytest
        report = CycleReport(
            cycle_number=1,
            date="2026-04-10",
            candidates_generated=50,
            pre_filter_survivors=8,
            adversaire_survivors=2,
            results=[],
            thompson_state={"tzeruf": {"alpha": 2, "beta": 10}},
        )
        assert report.cycle_number == 1
        assert report.candidates_generated == 50
        assert report.ratio == pytest.approx(2 / 50, abs=0.01)
