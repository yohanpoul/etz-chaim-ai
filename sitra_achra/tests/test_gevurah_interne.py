"""Tests Gevurah Interne — self-critique distribuee.

Teste que chaque diagnostic module detecte correctement les
anomalies selon sa Qliphah specifique.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from sitra_achra.gevurah_interne import (
    Anomalie,
    DinStatus,
    GevurahInterne,
    GevurahReport,
    _check_epistememory,
    _check_selfmap,
    _check_autojudge,
)


# ---------------------------------------------------------------------------
# GevurahReport tests
# ---------------------------------------------------------------------------

class TestGevurahReport:
    def test_sain_report(self):
        r = GevurahReport(module="test", status=DinStatus.SAIN)
        assert r.anomaly_count == 0
        assert not r.has_critical
        assert r.status == DinStatus.SAIN

    def test_has_critical(self):
        r = GevurahReport(
            module="test",
            status=DinStatus.DEFAILLANCE,
            anomalies=[
                Anomalie(
                    module="test", qliphah="test", description="fatal",
                    severity="mamash", metric_name="x", metric_value=1, threshold=0,
                ),
            ],
        )
        assert r.has_critical
        assert r.anomaly_count == 1

    def test_to_dict(self):
        r = GevurahReport(module="ep", status=DinStatus.SAIN, metriques={"a": 1.0})
        d = r.to_dict()
        assert d["module"] == "ep"
        assert d["status"] == "sain"
        assert d["metriques"]["a"] == 1.0


# ---------------------------------------------------------------------------
# EpisteMemory diagnostic (Gamaliel)
# ---------------------------------------------------------------------------

def _mock_cursor(rows_sequence):
    """Helper : cree un curseur mock qui retourne des rows en sequence."""
    mock_cur = MagicMock()
    call_count = [0]

    def fetchone_side_effect():
        idx = call_count[0]
        call_count[0] += 1
        if idx < len(rows_sequence):
            return (rows_sequence[idx],)
        return (0,)

    mock_cur.fetchone = fetchone_side_effect
    mock_cur.__enter__ = MagicMock(return_value=mock_cur)
    mock_cur.__exit__ = MagicMock(return_value=False)
    return mock_cur


class TestCheckEpistememory:
    def test_sain_when_no_issues(self):
        # Sequence: total=100, contradictions=2, high_conf_no_src=0, expired=5
        mock_cur = _mock_cursor([100, 2, 0, 5])
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        with patch("psycopg2.connect", return_value=mock_conn):
            report = _check_epistememory("postgresql://localhost/test")

        assert report.status == DinStatus.SAIN
        assert report.anomaly_count == 0

    def test_detects_high_contradiction_rate(self):
        # total=100, contradictions=15 (15% > 10%), high_conf=0, expired=0
        mock_cur = _mock_cursor([100, 15, 0, 0])
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        with patch("psycopg2.connect", return_value=mock_conn):
            report = _check_epistememory("postgresql://localhost/test")

        assert report.status == DinStatus.DEBORDEMENT
        assert report.anomaly_count == 1
        assert report.anomalies[0].qliphah == "gamaliel"
        assert report.anomalies[0].severity == "ruach"

    def test_detects_silent_corruption(self):
        """Anan : haute confiance sans provenance = corruption silencieuse."""
        # total=100, contradictions=0, high_conf_no_src=10, expired=0
        mock_cur = _mock_cursor([100, 0, 10, 0])
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        with patch("psycopg2.connect", return_value=mock_conn):
            report = _check_epistememory("postgresql://localhost/test")

        assert report.status == DinStatus.DEFAILLANCE
        assert any(a.severity == "anan" for a in report.anomalies)

    def test_handles_exception_as_mamash(self):
        """Diagnostic impossible = mamash (fatal)."""
        with patch("psycopg2.connect", side_effect=ConnectionError("DB down")):
            report = _check_epistememory("postgresql://localhost/test")

        assert report.status == DinStatus.DEFAILLANCE
        assert report.anomalies[0].severity == "mamash"

    def test_empty_memory_is_sain(self):
        mock_cur = _mock_cursor([0])
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        with patch("psycopg2.connect", return_value=mock_conn):
            report = _check_epistememory("postgresql://localhost/test")

        assert report.status == DinStatus.SAIN


# ---------------------------------------------------------------------------
# SelfMap diagnostic (Samael)
# ---------------------------------------------------------------------------

class TestCheckSelfmap:
    def test_detects_overconfidence(self):
        """Samael : confiance > 0.8 mais Brier > 0.4 = sur-confiance."""
        mock_score = MagicMock()
        mock_score.domain = "fake_domain"
        mock_score.confidence = 0.9
        mock_score.brier = 0.5
        mock_score.last_eval_age_days = 1

        mock_report = MagicMock()
        mock_report.scores = [mock_score]
        mock_report.mean_brier = 0.25

        with patch("selfmap.core.SelfMap") as MockSM:
            MockSM.return_value.calibrate.return_value = mock_report
            report = _check_selfmap("postgresql://localhost/test")

        assert report.status == DinStatus.DEFAILLANCE
        assert any(a.qliphah == "samael" for a in report.anomalies)


# ---------------------------------------------------------------------------
# AutoJudge diagnostic (Golachab)
# ---------------------------------------------------------------------------

class TestCheckAutojudge:
    def test_detects_over_filtering(self):
        """Golachab : taux de rejet > 70% = sur-filtrage."""
        mock_improvement = {
            "avg_rejection_rate_recent": 0.85,
            "trend": "stable",
            "delta": 0.0,
        }

        with patch("insightforge.ratzo_v_shov.RatzoVShov") as MockRVS:
            MockRVS.return_value.track_improvement.return_value = mock_improvement
            report = _check_autojudge("postgresql://localhost/test")

        assert report.anomaly_count >= 1
        assert any(a.qliphah == "golachab" for a in report.anomalies)


# ---------------------------------------------------------------------------
# GevurahInterne orchestrator
# ---------------------------------------------------------------------------

class TestGevurahInterne:
    def test_diagnostiquer_unknown_module_returns_sain(self):
        gi = GevurahInterne()
        report = gi.diagnostiquer("nonexistent_module")
        assert report.status == DinStatus.SAIN
        assert report.module == "nonexistent_module"

    def test_register_module(self):
        """Modules futurs peuvent s'enregistrer dynamiquement."""
        def fake_diag(db_url):
            return GevurahReport(module="fake", status=DinStatus.SAIN)

        GevurahInterne.register_module("fake_module", fake_diag)
        gi = GevurahInterne()
        report = gi.diagnostiquer("fake_module")
        assert report.module == "fake"
        assert report.status == DinStatus.SAIN

    def test_modules_en_defaillance_filters(self):
        """Seuls les modules malades sont retournes."""
        def sain(db_url):
            return GevurahReport(module="ok", status=DinStatus.SAIN)

        def malade(db_url):
            return GevurahReport(
                module="bad", status=DinStatus.DEFAILLANCE,
                anomalies=[Anomalie(
                    module="bad", qliphah="test", description="broken",
                    severity="anan", metric_name="x", metric_value=1, threshold=0,
                )],
            )

        GevurahInterne.register_module("test_sain", sain)
        GevurahInterne.register_module("test_malade", malade)

        gi = GevurahInterne()
        malades = gi.modules_en_defaillance()
        modules_malades = [r.module for r in malades if r.module == "bad"]
        assert "bad" in modules_malades


# ---------------------------------------------------------------------------
# Klipa Taxonomy integration (Vital EC 49) — additif Sprint 1.1
# ---------------------------------------------------------------------------

class TestAnomalieKlipaCategory:
    """L'Anomalie porte automatiquement sa categorie ontologique Vital EC 49."""

    def test_nogah_anomaly_is_rectifiable(self):
        """Severite 'nogah' -> Klipat Nogah, rectifiable par Birur."""
        from sitra_achra.klipa_taxonomy import KlipaCategory

        a = Anomalie(
            module="x", qliphah="samael", description="warning",
            severity="nogah", metric_name="m", metric_value=1.0, threshold=0.5,
        )
        assert a.klipa_category == KlipaCategory.KLIPAT_NOGAH
        assert a.is_rectifiable is True

    @pytest.mark.parametrize("severity", ["ruach", "anan", "mamash"])
    def test_temeot_anomaly_not_rectifiable(self, severity):
        """Severites Ezekiel 1:4 -> 3 Klippot HaTeme'ot, confinement."""
        from sitra_achra.klipa_taxonomy import KlipaCategory

        a = Anomalie(
            module="x", qliphah="samael", description="critical",
            severity=severity, metric_name="m", metric_value=1.0, threshold=0.5,
        )
        assert a.klipa_category == KlipaCategory.KLIPAT_HA_TEMEOT
        assert a.is_rectifiable is False


class TestGevurahReportCategorySummary:
    """Le rapport agrege les anomalies par categorie ontologique."""

    def test_empty_report_summary(self):
        """Rapport sans anomalie -> 0 partout."""
        r = GevurahReport(module="x", status=DinStatus.SAIN)
        assert r.rectifiable_count == 0
        assert r.containment_count == 0
        assert r.category_summary == {
            "klipat_nogah": 0,
            "klipat_ha_temeot": 0,
        }

    def test_mixed_report_summary(self):
        """Rapport melange Nogah + HaTeme'ot."""
        r = GevurahReport(
            module="x",
            status=DinStatus.DEFAILLANCE,
            anomalies=[
                Anomalie(
                    module="x", qliphah="samael", description="w1",
                    severity="nogah", metric_name="m", metric_value=1, threshold=0,
                ),
                Anomalie(
                    module="x", qliphah="samael", description="w2",
                    severity="nogah", metric_name="m", metric_value=1, threshold=0,
                ),
                Anomalie(
                    module="x", qliphah="gamaliel", description="critical",
                    severity="anan", metric_name="m", metric_value=1, threshold=0,
                ),
            ],
        )
        assert r.rectifiable_count == 2
        assert r.containment_count == 1
        assert r.category_summary == {
            "klipat_nogah": 2,
            "klipat_ha_temeot": 1,
        }

    def test_to_dict_includes_categories(self):
        """to_dict() expose la dimension ontologique pour serialisation."""
        r = GevurahReport(
            module="x",
            status=DinStatus.DEFAILLANCE,
            anomalies=[
                Anomalie(
                    module="x", qliphah="samael", description="w",
                    severity="nogah", metric_name="m", metric_value=1, threshold=0,
                ),
                Anomalie(
                    module="x", qliphah="samael", description="c",
                    severity="mamash", metric_name="m", metric_value=1, threshold=0,
                ),
            ],
        )
        d = r.to_dict()
        # Categorie au niveau anomalie
        assert d["anomalies"][0]["klipa_category"] == "klipat_nogah"
        assert d["anomalies"][0]["is_rectifiable"] is True
        assert d["anomalies"][1]["klipa_category"] == "klipat_ha_temeot"
        assert d["anomalies"][1]["is_rectifiable"] is False
        # Resume au niveau rapport
        assert d["category_summary"]["klipat_nogah"] == 1
        assert d["category_summary"]["klipat_ha_temeot"] == 1
