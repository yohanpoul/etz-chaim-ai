"""Tests EvidenceScorer + PearlCriteria.

Anti-Satariel Nogah : dire "possible" sans vérifier = hedging paresseux.
Le score doit être GAGNÉ, pas supposé.
"""

import pytest

from causalengine.evidence_scorer import EvidenceScorer
from causalengine.models import (
    CausalClaim,
    Confounder,
    DirectionAssessment,
)
from causalengine.pearl_criteria import PearlCriteria


@pytest.fixture
def scorer():
    return EvidenceScorer()


@pytest.fixture
def pearl():
    return PearlCriteria()


def _make_confounders(n: int, controlled: int = 0, with_method: int = 0) -> list[Confounder]:
    """Helper : créer n confounders, dont controlled contrôlés."""
    confs = []
    for i in range(n):
        c = Confounder(
            confounder_name=f"conf_{i}",
            plausibility=0.7,
            controlled=i < controlled,
            how_controlled=f"method_{i}" if i < with_method else "",
        )
        confs.append(c)
    return confs


# ── Score de base ──────────────────────────────────────

class TestEvidenceScore:
    def test_default_is_correlation(self, scorer):
        claim = CausalClaim(cause="A", effect="B")
        level = scorer.score(claim, [])
        assert level == "correlation_only"

    def test_correlation_with_few_confounders(self, scorer):
        """Moins de 3 confounders → reste correlation_only."""
        claim = CausalClaim(cause="A", effect="B")
        confs = _make_confounders(2, controlled=2)
        direction = DirectionAssessment(verdict="forward", forward_plausibility=0.8)
        level = scorer.score(claim, confs, direction)
        assert level == "correlation_only"

    def test_probable_causation(self, scorer):
        """Direction OK + confounders contrôlés → probable_causation."""
        claim = CausalClaim(cause="A", effect="B")
        confs = _make_confounders(4, controlled=3)  # 75% > 50%
        direction = DirectionAssessment(verdict="forward", forward_plausibility=0.8)
        level = scorer.score(claim, confs, direction)
        assert level == "probable_causation"

    def test_no_direction_stays_correlation(self, scorer):
        """Pas de direction → même avec confounders → correlation_only."""
        claim = CausalClaim(cause="A", effect="B")
        confs = _make_confounders(5, controlled=5)
        level = scorer.score(claim, confs, None)
        assert level == "correlation_only"

    def test_direction_indeterminate_stays_correlation(self, scorer):
        claim = CausalClaim(cause="A", effect="B")
        confs = _make_confounders(5, controlled=5)
        direction = DirectionAssessment(verdict="indeterminate")
        level = scorer.score(claim, confs, direction)
        assert level == "correlation_only"

    def test_demonstrated_causation(self, scorer):
        """Direction + 80% contrôlés avec méthode → demonstrated_causation."""
        claim = CausalClaim(cause="A", effect="B")
        confs = _make_confounders(5, controlled=5, with_method=5)  # 100%
        direction = DirectionAssessment(verdict="forward", forward_plausibility=0.9)
        level = scorer.score(claim, confs, direction)
        assert level == "demonstrated_causation"

    def test_bidirectional_direction_is_adequate(self, scorer):
        """Bidirectional est accepté pour probable_causation."""
        claim = CausalClaim(cause="A", effect="B")
        confs = _make_confounders(4, controlled=3)
        direction = DirectionAssessment(
            verdict="bidirectional", forward_plausibility=0.7,
        )
        level = scorer.score(claim, confs, direction)
        assert level == "probable_causation"

    def test_claim_direction_verified_override(self, scorer):
        """Si le claim a direction_verified=True, direction OK."""
        claim = CausalClaim(cause="A", effect="B", direction_verified=True)
        confs = _make_confounders(4, controlled=3)
        level = scorer.score(claim, confs, None)
        assert level == "probable_causation"


# ── Confidence ─────────────────────────────────────────

class TestConfidence:
    def test_correlation_base_confidence(self, scorer):
        conf = scorer.compute_confidence("correlation_only", [])
        assert 0.25 <= conf <= 0.35

    def test_probable_base_confidence(self, scorer):
        conf = scorer.compute_confidence("probable_causation", [])
        assert 0.55 <= conf <= 0.65

    def test_demonstrated_base_confidence(self, scorer):
        conf = scorer.compute_confidence("demonstrated_causation", [])
        assert 0.8 <= conf <= 0.95

    def test_controlled_confounders_bonus(self, scorer):
        confs = _make_confounders(4, controlled=4)
        base = scorer.compute_confidence("correlation_only", [])
        with_bonus = scorer.compute_confidence("correlation_only", confs)
        assert with_bonus > base

    def test_forward_direction_bonus(self, scorer):
        direction = DirectionAssessment(verdict="forward", forward_plausibility=0.8)
        base = scorer.compute_confidence("probable_causation", [])
        with_dir = scorer.compute_confidence("probable_causation", [], direction)
        assert with_dir > base

    def test_indeterminate_penalty(self, scorer):
        direction = DirectionAssessment(verdict="indeterminate")
        base = scorer.compute_confidence("probable_causation", [])
        with_indet = scorer.compute_confidence("probable_causation", [], direction)
        assert with_indet < base

    def test_high_uncontrolled_penalty(self, scorer):
        confs = [Confounder(confounder_name="x", plausibility=0.9, controlled=False)]
        base = scorer.compute_confidence("probable_causation", [])
        with_uc = scorer.compute_confidence("probable_causation", confs)
        assert with_uc < base

    def test_confidence_bounds(self, scorer):
        """Confidence toujours dans [0.1, 0.95]."""
        conf_low = scorer.compute_confidence(
            "correlation_only",
            [Confounder(confounder_name=f"x{i}", plausibility=0.9, controlled=False) for i in range(20)],
            DirectionAssessment(verdict="indeterminate"),
        )
        assert conf_low >= 0.1

        conf_high = scorer.compute_confidence(
            "demonstrated_causation",
            _make_confounders(10, controlled=10),
            DirectionAssessment(verdict="forward", forward_plausibility=0.99),
        )
        assert conf_high <= 0.95


# ── Can upgrade ────────────────────────────────────────

class TestCanUpgrade:
    def test_same_level_is_true(self, scorer):
        ok, missing = scorer.can_upgrade(
            "correlation_only", "correlation_only", [], None,
        )
        assert ok is True
        assert missing == []

    def test_downgrade_is_true(self, scorer):
        ok, missing = scorer.can_upgrade(
            "probable_causation", "correlation_only", [], None,
        )
        assert ok is True

    def test_upgrade_missing_direction(self, scorer):
        ok, missing = scorer.can_upgrade(
            "correlation_only", "probable_causation",
            _make_confounders(5, controlled=5), None,
        )
        assert ok is False
        assert any("Direction" in m for m in missing)

    def test_upgrade_missing_confounders(self, scorer):
        direction = DirectionAssessment(verdict="forward", forward_plausibility=0.8)
        ok, missing = scorer.can_upgrade(
            "correlation_only", "probable_causation",
            _make_confounders(5, controlled=1), direction,
        )
        assert ok is False
        assert any("Confounder" in m for m in missing)

    def test_upgrade_to_demonstrated_needs_intervention(self, scorer):
        direction = DirectionAssessment(verdict="forward", forward_plausibility=0.9)
        ok, missing = scorer.can_upgrade(
            "probable_causation", "demonstrated_causation",
            _make_confounders(5, controlled=3, with_method=3), direction,
        )
        assert ok is False
        assert any("intervention" in m.lower() or "rct" in m.lower() for m in missing)


# ── Pearl Criteria ─────────────────────────────────────

class TestPearlClassify:
    def test_classify_correlation(self, pearl):
        claim = CausalClaim(cause="A", effect="B", evidence_level="correlation_only")
        assert pearl.classify_claim(claim) == "association"

    def test_classify_probable(self, pearl):
        claim = CausalClaim(cause="A", effect="B", evidence_level="probable_causation")
        assert pearl.classify_claim(claim) == "intervention"

    def test_classify_demonstrated(self, pearl):
        claim = CausalClaim(cause="A", effect="B", evidence_level="demonstrated_causation")
        assert pearl.classify_claim(claim) == "counterfactual"


class TestPearlWhatNeeded:
    def test_same_level(self, pearl):
        needed = pearl.what_is_needed("association", "association")
        assert needed == []

    def test_association_to_intervention(self, pearl):
        needed = pearl.what_is_needed("association", "intervention")
        assert len(needed) > 0
        assert any("P(Y|do(X))" in n for n in needed)

    def test_association_to_counterfactual(self, pearl):
        needed = pearl.what_is_needed("association", "counterfactual")
        assert any("P(Y|do(X))" in n for n in needed)
        assert any("P(Y_x|X', Y')" in n for n in needed)

    def test_intervention_to_counterfactual(self, pearl):
        needed = pearl.what_is_needed("intervention", "counterfactual")
        assert len(needed) > 0
        assert any("counterfactual" in n.lower() for n in needed)


class TestPearlUpgradeFeasibility:
    def test_at_max_level(self, pearl):
        claim = CausalClaim(cause="A", effect="B", evidence_level="demonstrated_causation")
        result = pearl.assess_upgrade_feasibility(claim, [])
        assert result["current_pearl"] == "counterfactual"
        assert result["next_pearl"] is None
        assert result["progress"] == 1.0

    def test_missing_everything(self, pearl):
        claim = CausalClaim(cause="A", effect="B", evidence_level="correlation_only")
        result = pearl.assess_upgrade_feasibility(claim, [])
        assert result["feasible"] is False
        assert len(result["missing"]) > 0
        assert result["progress"] < 1.0

    def test_partial_progress(self, pearl):
        claim = CausalClaim(
            cause="A", effect="B",
            evidence_level="correlation_only",
            direction_verified=True,
        )
        confs = _make_confounders(4, controlled=3)
        result = pearl.assess_upgrade_feasibility(claim, confs)
        assert 0 < result["progress"] < 1.0

    def test_format_pearl_level(self, pearl):
        desc = pearl.format_pearl_level("association")
        assert "P(Y|X)" in desc
        assert "Association" in desc
