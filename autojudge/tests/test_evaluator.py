"""Tests MultiSephirothEvaluator — 5 axes + décision harmonisée."""

import pytest

from autojudge.evaluator import MultiSephirothEvaluator
from autojudge.models import DomainScore, MultiScore


class TestMultiSephirothEvaluator:
    """Évaluation multi-sephirothique."""

    def test_evaluate_returns_multi_score(self):
        ev = MultiSephirothEvaluator()
        ds = DomainScore(quality=0.7, metrics={"a": 0.6, "b": 0.8})
        ms = ev.evaluate(ds, "original text here", "modified text with changes")
        assert isinstance(ms, MultiScore)
        assert 0 <= ms.gevurah <= 1
        assert 0 <= ms.chesed <= 1
        assert 0 <= ms.tiferet <= 1
        assert 0 <= ms.hod <= 1
        assert 0 <= ms.yesod <= 1

    def test_gevurah_equals_domain_quality(self):
        ev = MultiSephirothEvaluator()
        ds = DomainScore(quality=0.85, metrics={"x": 0.85})
        ms = ev.evaluate(ds, "text", "text slightly changed")
        assert ms.gevurah == 0.85

    def test_overall_weighted_average(self):
        ms = MultiScore(gevurah=1.0, chesed=1.0, tiferet=1.0, hod=1.0, yesod=1.0)
        assert abs(ms.overall - 1.0) < 0.01

    def test_overall_weights_correct(self):
        ms = MultiScore(gevurah=0.5, chesed=0.0, tiferet=0.0, hod=0.0, yesod=0.0)
        expected = 0.5 * 0.35
        assert abs(ms.overall - expected) < 0.001

    def test_chesed_diversity_identical_text(self):
        ev = MultiSephirothEvaluator()
        ds = DomainScore(quality=0.5, metrics={})
        ms = ev.evaluate(ds, "same text", "same text")
        # Identical text → low chesed (no new words)
        assert ms.chesed <= 0.4

    def test_tiferet_consistency_identical(self):
        ev = MultiSephirothEvaluator()
        ds = DomainScore(quality=0.5, metrics={})
        ms = ev.evaluate(ds, "the quick brown fox", "the quick brown fox")
        assert ms.tiferet == 1.0

    def test_tiferet_consistency_divergent(self):
        ev = MultiSephirothEvaluator()
        ds = DomainScore(quality=0.5, metrics={})
        ms = ev.evaluate(ds, "alpha beta gamma delta", "zeta theta omega epsilon")
        assert ms.tiferet < 0.2

    def test_yesod_reproducibility_consistent_metrics(self):
        ev = MultiSephirothEvaluator()
        ds = DomainScore(quality=0.7, metrics={"a": 0.7, "b": 0.7, "c": 0.7})
        ms = ev.evaluate(ds, "text", "modified text")
        assert ms.yesod > 0.8

    def test_yesod_reproducibility_scattered_metrics(self):
        ev = MultiSephirothEvaluator()
        ds = DomainScore(quality=0.5, metrics={"a": 0.1, "b": 0.9, "c": 0.5})
        ms = ev.evaluate(ds, "text", "modified text")
        assert ms.yesod < 0.8


class TestHolisticDecision:
    """Décision harmonisée — anti-Golachab + anti-Thagirion."""

    def test_high_score_accepted(self):
        ev = MultiSephirothEvaluator(quality_threshold=0.6)
        ms = MultiScore(gevurah=0.8, chesed=0.7, tiferet=0.8, hod=0.7, yesod=0.7)
        assert ev.holistic_decision(ms) == "accepted"

    def test_low_score_rejected(self):
        ev = MultiSephirothEvaluator(quality_threshold=0.6, quarantine_threshold=0.4)
        ms = MultiScore(gevurah=0.2, chesed=0.1, tiferet=0.2, hod=0.1, yesod=0.1)
        assert ev.holistic_decision(ms) == "rejected"

    def test_medium_score_quarantined(self):
        ev = MultiSephirothEvaluator(quality_threshold=0.6, quarantine_threshold=0.4)
        ms = MultiScore(gevurah=0.5, chesed=0.5, tiferet=0.5, hod=0.5, yesod=0.5)
        assert ev.holistic_decision(ms) == "quarantined"

    def test_anti_golachab_relaxes_on_high_rejection_rate(self):
        """Si on rejette trop → quarantine au lieu de rejeter (anti-Golachab)."""
        ev = MultiSephirothEvaluator(golachab_rejection_ceiling=0.9)
        ms = MultiScore(gevurah=0.2, chesed=0.1, tiferet=0.2, hod=0.1, yesod=0.1)
        # Sans high rejection: rejected
        assert ev.holistic_decision(ms, recent_rejection_rate=0.5) == "rejected"
        # Avec high rejection: quarantined (anti-Golachab)
        assert ev.holistic_decision(ms, recent_rejection_rate=0.95) == "quarantined"

    def test_anti_thagirion_detects_tension(self):
        """Qualité haute + cohérence basse → tension_detected (anti-Thagirion)."""
        ev = MultiSephirothEvaluator(tension_check_enabled=True)
        ms = MultiScore(gevurah=0.9, chesed=0.5, tiferet=0.2, hod=0.5, yesod=0.5)
        assert ev.holistic_decision(ms) == "tension_detected"

    def test_tension_disabled(self):
        """Quand tension_check disabled, pas de tension_detected."""
        ev = MultiSephirothEvaluator(tension_check_enabled=False)
        ms = MultiScore(gevurah=0.9, chesed=0.5, tiferet=0.2, hod=0.5, yesod=0.5)
        result = ev.holistic_decision(ms)
        assert result != "tension_detected"
