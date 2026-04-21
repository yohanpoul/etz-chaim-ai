"""Integration tests — genome.json drives Birur and ThompsonBandit.

When /halom gilgul mutates the genome, the next /halom cycle must
use the mutated parameters. These tests verify the wiring.
"""
from __future__ import annotations

from halom.birur import Birur, RejectionReason
from halom.models import DreamCandidate, Mechanism
from halom.thompson import ThompsonBandit


def _candidate(bisociation: float = 0.5, prediction: str = "Real prediction") -> DreamCandidate:
    return DreamCandidate(
        concept_k="Test_K",
        concept_ia="Test_IA",
        mechanism=Mechanism.TZERUF,
        structure_commune="Test structure",
        prediction=prediction,
        score_brut=0.5,
        bisociation=bisociation,
    )


class TestBaselineEquivalence:
    """Genome v1 produces the same behavior as hardcoded defaults."""

    def test_birur_baseline_matches_defaults(self):
        """Birur with genome v1 values behaves like Birur()."""
        genome_birur = {"bisociation_min": 0.2, "bisociation_max": 0.8}
        birur_genome = Birur(
            bisociation_min=genome_birur["bisociation_min"],
            bisociation_max=genome_birur["bisociation_max"],
        )
        birur_default = Birur()
        c_trivial = _candidate(bisociation=0.1)
        c_absurd = _candidate(bisociation=0.9)
        c_good = _candidate(bisociation=0.5)
        assert birur_genome.pre_filter(c_trivial) == birur_default.pre_filter(c_trivial)
        assert birur_genome.pre_filter(c_absurd) == birur_default.pre_filter(c_absurd)
        assert birur_genome.pre_filter(c_good) == birur_default.pre_filter(c_good)

    def test_thompson_baseline_matches_defaults(self):
        """ThompsonBandit with genome v1 values behaves like ThompsonBandit()."""
        genome_thompson = {"epsilon": 0.05, "phase_boundaries": [0.3, 0.7]}
        bandit_genome = ThompsonBandit(
            seed=42,
            epsilon=genome_thompson["epsilon"],
            phase_boundaries=genome_thompson["phase_boundaries"],
        )
        bandit_default = ThompsonBandit(seed=42)
        for i in range(20):
            assert bandit_genome.select(turn=i, total_turns=20) == bandit_default.select(turn=i, total_turns=20)


class TestMutantApplication:
    """Mutated genome changes actual behavior."""

    def test_wider_bisociation_accepts_more(self):
        """bisociation_max=0.95 accepts candidates that default rejects."""
        c = _candidate(bisociation=0.85)
        birur_default = Birur()
        birur_mutant = Birur(bisociation_min=0.2, bisociation_max=0.95)
        assert birur_default.pre_filter(c) == RejectionReason.ABSURD
        assert birur_mutant.pre_filter(c) is None

    def test_narrower_bisociation_rejects_more(self):
        """bisociation range [0.4, 0.6] rejects what default accepts."""
        c = _candidate(bisociation=0.3)
        birur_default = Birur()
        birur_mutant = Birur(bisociation_min=0.4, bisociation_max=0.6)
        assert birur_default.pre_filter(c) is None
        assert birur_mutant.pre_filter(c) == RejectionReason.TRIVIAL

    def test_high_epsilon_increases_exploration(self):
        """epsilon=0.30 gives more uniform selections."""
        bandit_low = ThompsonBandit(seed=42, epsilon=0.05)
        bandit_high = ThompsonBandit(seed=42, epsilon=0.30)
        for _ in range(50):
            bandit_low.update(Mechanism.TZERUF, success=True)
            bandit_high.update(Mechanism.TZERUF, success=True)
        low_samael = sum(1 for _ in range(500) if bandit_low.select() == Mechanism.SAMAEL)
        high_samael = sum(1 for _ in range(500) if bandit_high.select() == Mechanism.SAMAEL)
        assert high_samael > low_samael
