"""Tests Itaruta + Teshuvah — auto-diagnostic ascendant."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from malakhim.adversarial.base_adversary import Attack, AttackResult
from sitra_achra.itaruta import Itaruta, ItarutaReport, TeshuvahRecord


@pytest.fixture
def itaruta():
    return Itaruta(db_url="postgresql://localhost/test")


def _make_result(success: bool, severity: str = "nogah", qliphah: str = "gamaliel") -> AttackResult:
    attack = Attack(
        agent_name="test", target_module="epistememory",
        description=f"test attack ({severity})",
        input_data={}, expected_qliphah=qliphah,
        expected_severity=severity,
    )
    return AttackResult(
        attack=attack, success=success,
        actual_response={}, exception=None,
        actual_qliphah=qliphah if success else "unknown",
        actual_severity=severity if success else None,
    )


class TestShouldTrigger:

    def test_no_flaws_no_trigger(self, itaruta):
        """Pas de failles → pas d'eveil."""
        results = [_make_result(success=False) for _ in range(10)]
        assert not itaruta.should_trigger(results)

    def test_one_mamash_triggers(self, itaruta):
        """1 faille fatale suffit pour l'eveil."""
        results = [_make_result(success=True, severity="mamash")]
        assert itaruta.should_trigger(results)

    def test_threshold_anan(self, itaruta):
        """2 failles anan declenchent l'eveil."""
        results = [
            _make_result(success=True, severity="anan"),
            _make_result(success=True, severity="anan"),
        ]
        assert itaruta.should_trigger(results)

    def test_below_threshold_no_trigger(self, itaruta):
        """Sous le seuil → pas d'eveil (bruit de fond)."""
        results = [_make_result(success=True, severity="nogah") for _ in range(5)]
        assert not itaruta.should_trigger(results)

    def test_nogah_threshold_8(self, itaruta):
        """8 nogah declenchent l'eveil."""
        results = [_make_result(success=True, severity="nogah") for _ in range(8)]
        assert itaruta.should_trigger(results)


class TestAutoDiagnostic:

    def test_empty_results(self, itaruta):
        """Pas de failles → rapport vide."""
        report = itaruta.auto_diagnostic("epistememory", [])
        assert report.flaw_count == 0
        assert report.patterns == []

    def test_identifies_patterns(self, itaruta):
        """Le diagnostic identifie les patterns de failles."""
        results = [
            _make_result(success=True, severity="ruach", qliphah="gamaliel"),
            _make_result(success=True, severity="ruach", qliphah="gamaliel"),
            _make_result(success=True, severity="anan", qliphah="samael"),
            _make_result(success=False),
        ]
        with patch.object(itaruta, "_store_in_memory", return_value=False):
            report = itaruta.auto_diagnostic("epistememory", results)

        assert report.flaw_count == 3
        assert report.critical_count == 1  # anan
        assert any("gamaliel" in p for p in report.patterns)

    def test_formulates_help_request(self, itaruta):
        """Le module formule une demande d'aide ascendante."""
        results = [
            _make_result(success=True, severity="mamash", qliphah="gamaliel"),
        ]
        with patch.object(itaruta, "_store_in_memory", return_value=False):
            report = itaruta.auto_diagnostic("epistememory", results)

        assert "epistememory" in report.help_request
        assert "gamaliel" in report.help_request
        assert "renforcer" in report.help_request

    def test_generates_teshuvah_records(self, itaruta):
        """Chaque faille produit un enregistrement Teshuvah."""
        results = [
            _make_result(success=True, severity="ruach", qliphah="gamaliel"),
        ]
        with patch.object(itaruta, "_store_in_memory", return_value=False):
            report = itaruta.auto_diagnostic("epistememory", results)

        assert len(report.teshuvah_records) == 1
        record = report.teshuvah_records[0]
        assert record["module"] == "epistememory"
        assert record["qliphah"] == "gamaliel"
        assert "test_regression" in record["regression_test"]


class TestTeshuvahRecord:

    def test_to_dict(self):
        record = TeshuvahRecord(
            module="test", flaw_description="test flaw",
            severity="ruach", qliphah="gamaliel",
            regression_test="test_regression_test",
        )
        d = record.to_dict()
        assert d["module"] == "test"
        assert d["regression_test"] == "test_regression_test"


class TestStoreInMemory:

    def test_stores_when_db_available(self, itaruta):
        """L'itaruta stocke la connaissance en epistememory."""
        report = ItarutaReport(
            module="epistememory",
            flaw_count=3,
            critical_count=1,
            patterns=["gamaliel: 2", "samael: 1"],
            help_request="Renforcer rigueur sur gamaliel",
        )

        mock_conn = MagicMock()
        mock_conn.closed = False  # evite la branche retry de pool.get_conn
        mock_cursor = MagicMock()
        # `with conn.cursor() as cur:` — __enter__ doit retourner mock_cursor
        mock_cursor.__enter__.return_value = mock_cursor
        mock_cursor.__exit__.return_value = False
        mock_conn.cursor.return_value = mock_cursor

        with patch("psycopg2.connect") as mock_connect:
            mock_connect.return_value = mock_conn
            result = itaruta._store_in_memory("epistememory", report)

        assert result is True
        mock_cursor.execute.assert_called_once()

    def test_graceful_on_db_failure(self, itaruta):
        """Echec DB → pas de crash, juste un warning."""
        report = ItarutaReport(module="test")

        with patch("psycopg2.connect") as mock_connect:
            mock_connect.side_effect = ConnectionError("DB down")
            result = itaruta._store_in_memory("test", report)

        assert result is False
