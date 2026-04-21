"""Tests for Birur pre-filter.

Birur (בירור) = sorting signal from noise.
Berakhot 57b: dream is 1/60 of prophecy.
The pre-filter handles the deterministic part; the adversaire handles the rest.
"""
from __future__ import annotations

from halom.birur import Birur, RejectionReason
from halom.models import DreamCandidate, Mechanism


def _candidate(
    concept_k: str = "Reshimu",
    concept_ia: str = "Residual connections",
    mechanism: Mechanism = Mechanism.TZERUF,
    prediction: str = "Testable prediction here",
    bisociation: float = 0.5,
    mdl_score: float = 0.3,
) -> DreamCandidate:
    """Helper to create candidates with defaults."""
    return DreamCandidate(
        concept_k=concept_k,
        concept_ia=concept_ia,
        mechanism=mechanism,
        structure_commune="Some structure",
        prediction=prediction,
        score_brut=0.5,
        bisociation=bisociation,
        mdl_score=mdl_score,
    )


class TestBirurDuplication:
    """Reject candidates already explored."""

    def test_duplicate_rejected(self):
        """Exact same concept pair already in history → reject."""
        history = [{"concept_k": "Reshimu", "concept_ia": "Residual connections"}]
        birur = Birur(history=history)
        result = birur.pre_filter(_candidate())
        assert result is not None
        assert result == RejectionReason.DUPLICATE

    def test_novel_candidate_passes(self):
        """New concept pair → passes duplication check."""
        birur = Birur(history=[])
        result = birur.pre_filter(_candidate())
        assert result is None  # None = passed all filters


class TestBirurBisociation:
    """Reject candidates outside the fecund zone [0.2, 0.8]."""

    def test_too_trivial_rejected(self):
        """B < 0.2 → trivial, reject."""
        birur = Birur()
        result = birur.pre_filter(_candidate(bisociation=0.1))
        assert result == RejectionReason.TRIVIAL

    def test_too_absurd_rejected(self):
        """B > 0.8 → absurd, reject."""
        birur = Birur()
        result = birur.pre_filter(_candidate(bisociation=0.9))
        assert result == RejectionReason.ABSURD

    def test_fecund_zone_passes(self):
        """B = 0.5 → in fecund zone, passes."""
        birur = Birur()
        result = birur.pre_filter(_candidate(bisociation=0.5))
        assert result is None

    def test_boundary_low_passes(self):
        """B = 0.2 → on boundary, passes."""
        birur = Birur()
        result = birur.pre_filter(_candidate(bisociation=0.2))
        assert result is None

    def test_boundary_high_passes(self):
        """B = 0.8 → on boundary, passes."""
        birur = Birur()
        result = birur.pre_filter(_candidate(bisociation=0.8))
        assert result is None


class TestBirurFertility:
    """Reject candidates without testable predictions."""

    def test_empty_prediction_rejected(self):
        """No prediction → sterile, reject."""
        birur = Birur()
        result = birur.pre_filter(_candidate(prediction=""))
        assert result == RejectionReason.STERILE

    def test_vague_prediction_rejected(self):
        """'None' or 'N/A' prediction → sterile."""
        birur = Birur()
        result = birur.pre_filter(_candidate(prediction="None"))
        assert result == RejectionReason.STERILE

    def test_real_prediction_passes(self):
        """Actual testable prediction → passes."""
        birur = Birur()
        result = birur.pre_filter(_candidate(prediction="Removing skip connections causes vanishing gradient"))
        assert result is None


class TestBirurBatch:
    """Batch filtering of multiple candidates."""

    def test_batch_filter(self):
        """Filter a batch, return only survivors."""
        birur = Birur()
        candidates = [
            _candidate(bisociation=0.1),   # trivial → rejected
            _candidate(bisociation=0.5),   # good → passes
            _candidate(prediction=""),     # sterile → rejected
            _candidate(bisociation=0.5, concept_k="Tsimtsum", concept_ia="Information Bottleneck"),  # good → passes
        ]
        survivors = birur.filter_batch(candidates)
        assert len(survivors) == 2
        assert survivors[0].concept_k == "Reshimu"
        assert survivors[1].concept_k == "Tsimtsum"
