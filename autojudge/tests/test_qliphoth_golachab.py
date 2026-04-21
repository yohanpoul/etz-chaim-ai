"""Tests Qliphoth de Golachab — les 4 niveaux d'anti-Golachab.

Golachab (les Incendiaires) : Gevurah qui détruit au lieu de filtrer.
4 niveaux de diagnostic :
- Nogah : taux de rejet élevé (>70%) mais résultats OK
- Ruach : rejets non analysés (Nitzotzot perdues)
- Anan : 0 acceptés sur 10+ itérations
- Mamash : rejets malgré bon score (le juge se juge lui-même)
"""

import pytest

from autojudge.core import AutoJudge


TEST_DB_URL = "postgresql://localhost/etz_chaim_test"


class TestGolachabDiagnosis:
    """Auto-diagnostic anti-Golachab — Gevurah surveille Gevurah."""

    def test_healthy_when_empty(self, judge_bare):
        """Pas de données → healthy."""
        diag = judge_bare.self_diagnose()
        assert diag["level"] == "healthy"
        assert diag["issues"] == []

    def test_nogah_high_rejection_rate(self, db, judge_bare):
        """Nogah : taux de rejet > 70%."""
        # Register domain first
        db.upsert_domain("test", "Test Domain", "test_loss")
        # Create 10 experiments: 8 rejected, 2 accepted
        for i in range(8):
            db.create_experiment(
                domain_id="test",
                hypothesis=f"hyp_{i}",
                decision="rejected",
                nitzotzot_extracted=True,  # Analyzed, so not Ruach
                score_overall=0.3,
            )
        for i in range(2):
            db.create_experiment(
                domain_id="test",
                hypothesis=f"hyp_acc_{i}",
                decision="accepted",
                score_overall=0.7,
            )

        diag = judge_bare.self_diagnose()
        assert diag["level"] in ("nogah", "ruach", "anan", "mamash")
        assert any("Nogah" in issue for issue in diag["issues"])

    def test_ruach_unanalyzed_rejections(self, db, judge_bare):
        """Ruach : rejets non analysés (Nitzotzot perdues)."""
        db.upsert_domain("test", "Test Domain", "test_loss")
        for i in range(5):
            db.create_experiment(
                domain_id="test",
                hypothesis=f"hyp_{i}",
                decision="rejected",
                nitzotzot_extracted=False,  # NOT analyzed → Ruach
                score_overall=0.3,
            )
        for i in range(5):
            db.create_experiment(
                domain_id="test",
                hypothesis=f"hyp_acc_{i}",
                decision="accepted",
                score_overall=0.7,
            )

        diag = judge_bare.self_diagnose()
        assert any("Ruach" in issue for issue in diag["issues"])

    def test_anan_zero_accepted(self, db, judge_bare):
        """Anan : 0 acceptés sur 10+ itérations — destruction totale."""
        db.upsert_domain("test", "Test Domain", "test_loss")
        for i in range(12):
            db.create_experiment(
                domain_id="test",
                hypothesis=f"hyp_{i}",
                decision="rejected",
                nitzotzot_extracted=True,
                score_overall=0.3,
            )

        diag = judge_bare.self_diagnose()
        assert diag["level"] == "anan"
        assert any("Anan" in issue for issue in diag["issues"])

    def test_mamash_rejected_despite_good_score(self, db, judge_bare):
        """Mamash : rejets malgré score > seuil — Gevurah se juge lui-même à tort."""
        db.upsert_domain("test", "Test Domain", "test_loss")
        # Some normal accepted
        for i in range(5):
            db.create_experiment(
                domain_id="test",
                hypothesis=f"hyp_acc_{i}",
                decision="accepted",
                score_overall=0.8,
            )
        # Rejected DESPITE good score (Mamash)
        for i in range(3):
            db.create_experiment(
                domain_id="test",
                hypothesis=f"hyp_mamash_{i}",
                decision="rejected",
                score_overall=0.75,  # > quality_threshold (0.6)
                nitzotzot_extracted=True,
            )

        diag = judge_bare.self_diagnose()
        assert diag["level"] == "mamash"
        assert any("Mamash" in issue for issue in diag["issues"])

    def test_report_includes_diagnosis(self, db, judge_bare):
        """Le rapport inclut le diagnostic anti-Golachab."""
        db.upsert_domain("test", "Test Domain", "test_loss")
        for i in range(3):
            db.create_experiment(
                domain_id="test",
                hypothesis=f"hyp_{i}",
                decision="accepted",
                score_overall=0.8,
            )

        report = judge_bare.report()
        assert "AutoJudge Report" in report
        assert "Self-diagnosis" in report
        assert "healthy" in report

    def test_report_with_domain_filter(self, db, judge_bare):
        """Le rapport filtre par domaine."""
        db.upsert_domain("writing", "Writing", "text_quality")
        db.upsert_domain("code", "Code", "code_quality")
        for i in range(3):
            db.create_experiment(
                domain_id="writing",
                hypothesis=f"hyp_{i}",
                decision="accepted",
                score_overall=0.8,
            )
        db.create_experiment(
            domain_id="code",
            hypothesis="hyp_code",
            decision="rejected",
            score_overall=0.3,
        )

        report = judge_bare.report(domain_id="writing")
        assert "Rejection rate (writing)" in report

    def test_anti_golachab_in_evaluator(self):
        """Anti-Golachab intégré dans le MultiSephirothEvaluator."""
        from autojudge.evaluator import MultiSephirothEvaluator
        from autojudge.models import MultiScore

        ev = MultiSephirothEvaluator(golachab_rejection_ceiling=0.9)
        # Score bas → normalement rejeté
        ms = MultiScore(gevurah=0.1, chesed=0.1, tiferet=0.1, hod=0.1, yesod=0.1)
        # Mais rejection rate > ceiling → quarantined (anti-Golachab kicks in)
        decision = ev.holistic_decision(ms, recent_rejection_rate=0.95)
        assert decision == "quarantined"
