"""Tests External Scanner — integration Promptfoo + Garak dans le cycle Sitra Achra."""

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sitra_achra.external_scanner import (
    ScanResult,
    _parse_garak_report,
    _parse_promptfoo_output,
    detect_regression,
    feed_results_to_system,
    run_garak_scan,
    run_promptfoo_scan,
    task_external_scan,
)


# ---------------------------------------------------------------------------
# ScanResult
# ---------------------------------------------------------------------------


class TestScanResult:

    def test_empty_result(self):
        """Resultat vide → zero partout."""
        r = ScanResult(scanner="promptfoo")
        assert r.flaw_count == 0
        assert r.critical_count == 0
        assert r.attack_success_rate == 0.0
        assert r.error is None

    def test_flaw_count(self):
        """flaw_count = nombre de vulnerabilites."""
        r = ScanResult(
            scanner="garak",
            vulnerabilities=[
                {"name": "v1", "severity": "low"},
                {"name": "v2", "severity": "high"},
            ],
        )
        assert r.flaw_count == 2

    def test_critical_count(self):
        """critical_count = high + critical seulement."""
        r = ScanResult(
            scanner="garak",
            vulnerabilities=[
                {"name": "v1", "severity": "low"},
                {"name": "v2", "severity": "high"},
                {"name": "v3", "severity": "critical"},
                {"name": "v4", "severity": "medium"},
            ],
        )
        assert r.critical_count == 2

    def test_to_dict_roundtrip(self):
        """to_dict contient tous les champs."""
        r = ScanResult(scanner="promptfoo", total_tests=10, passed=8, failed=2)
        d = r.to_dict()
        assert d["scanner"] == "promptfoo"
        assert d["total_tests"] == 10
        assert d["passed"] == 8
        assert d["failed"] == 2
        assert "flaw_count" in d
        assert "critical_count" in d


# ---------------------------------------------------------------------------
# Promptfoo parser
# ---------------------------------------------------------------------------


class TestParsePromptfooOutput:

    def test_parses_pass_fail(self):
        """Extrait passed/failed de la sortie CLI."""
        output = "Results: 48 passed (96.0%), 2 failed (4.0%)"
        r = _parse_promptfoo_output(output, ScanResult(scanner="promptfoo"))
        assert r.passed == 48
        assert r.failed == 2
        assert r.total_tests == 50
        assert r.attack_success_rate == pytest.approx(0.04)

    def test_parses_vulnerabilities(self):
        """Extrait les types de vulnerabilites avec ASR."""
        output = (
            "48 passed, 2 failed\n"
            "SQL Injection: 15.0% attack success rate\n"
            "Prompt Injection: 5.0% attack success rate\n"
        )
        r = _parse_promptfoo_output(output, ScanResult(scanner="promptfoo"))
        assert len(r.vulnerabilities) == 2
        names = [v["name"] for v in r.vulnerabilities]
        assert "SQL Injection" in names
        assert "Prompt Injection" in names

    def test_zero_asr_not_added(self):
        """0% ASR → pas de vulnerabilite ajoutee."""
        output = "48 passed, 0 failed\nSQL Injection: 0.0%"
        r = _parse_promptfoo_output(output, ScanResult(scanner="promptfoo"))
        assert len(r.vulnerabilities) == 0

    def test_empty_output(self):
        """Sortie vide → zero partout."""
        r = _parse_promptfoo_output("", ScanResult(scanner="promptfoo"))
        assert r.total_tests == 0

    def test_severity_classification(self):
        """ASR >= 10% → high, sinon medium."""
        output = "SQL Injection: 15.0%\nHallucination: 3.0%"
        r = _parse_promptfoo_output(output, ScanResult(scanner="promptfoo"))
        sevs = {v["name"]: v["severity"] for v in r.vulnerabilities}
        assert sevs["SQL Injection"] == "high"
        assert sevs["Hallucination"] == "medium"


# ---------------------------------------------------------------------------
# Garak parser
# ---------------------------------------------------------------------------


class TestParseGarakReport:

    def test_parses_jsonl(self, tmp_path):
        """Parse un rapport JSONL Garak."""
        report = tmp_path / "scan.report.jsonl"
        entries = [
            {"entry_type": "eval", "probe": "dan", "detector": "mitigation",
             "status": "complete", "total": 10, "passed": 8},
            {"entry_type": "eval", "probe": "encoding", "detector": "reject",
             "status": "complete", "total": 5, "passed": 5},
        ]
        report.write_text("\n".join(json.dumps(e) for e in entries))

        r = _parse_garak_report(report, ScanResult(scanner="garak"))
        assert r.passed == 13
        assert r.failed == 2
        assert r.total_tests == 15
        assert len(r.vulnerabilities) == 1
        assert "dan" in r.vulnerabilities[0]["name"]

    def test_empty_report(self, tmp_path):
        """Rapport vide → zero."""
        report = tmp_path / "empty.report.jsonl"
        report.write_text("")
        r = _parse_garak_report(report, ScanResult(scanner="garak"))
        assert r.total_tests == 0

    def test_malformed_json_skipped(self, tmp_path):
        """Lignes JSON invalides → ignorees."""
        report = tmp_path / "bad.report.jsonl"
        report.write_text("not json\n{bad\n")
        r = _parse_garak_report(report, ScanResult(scanner="garak"))
        assert r.total_tests == 0

    def test_severity_thresholds(self, tmp_path):
        """ASR >= 20% → high, >= 5% → medium, sinon low."""
        report = tmp_path / "sev.report.jsonl"
        entries = [
            {"entry_type": "eval", "probe": "p1", "detector": "d1",
             "total": 10, "passed": 7},   # 30% fail → high
            {"entry_type": "eval", "probe": "p2", "detector": "d2",
             "total": 100, "passed": 92},  # 8% fail → medium
            {"entry_type": "eval", "probe": "p3", "detector": "d3",
             "total": 100, "passed": 98},  # 2% fail → low
        ]
        report.write_text("\n".join(json.dumps(e) for e in entries))

        r = _parse_garak_report(report, ScanResult(scanner="garak"))
        sevs = {v["probe"]: v["severity"] for v in r.vulnerabilities}
        assert sevs["p1"] == "high"
        assert sevs["p2"] == "medium"
        assert sevs["p3"] == "low"


# ---------------------------------------------------------------------------
# run_promptfoo_scan
# ---------------------------------------------------------------------------


class TestRunPromptfooScan:

    def test_not_installed(self):
        """Promptfoo absent → erreur propre."""
        with patch("shutil.which", return_value=None):
            with patch("pathlib.Path.exists", return_value=False):
                r = run_promptfoo_scan()
        assert r.error == "promptfoo not installed"

    def test_timeout(self):
        """Timeout → erreur timeout."""
        import subprocess

        with patch("shutil.which", return_value="/usr/bin/promptfoo"), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 600)):
            r = run_promptfoo_scan()
        assert "timeout" in r.error


# ---------------------------------------------------------------------------
# run_garak_scan
# ---------------------------------------------------------------------------


class TestRunGarakScan:

    def test_venv_not_found(self):
        """Garak venv absent → erreur propre."""
        with patch("pathlib.Path.exists", return_value=False):
            r = run_garak_scan()
        assert r.error == "garak venv not found"


# ---------------------------------------------------------------------------
# feed_results_to_system
# ---------------------------------------------------------------------------


class TestFeedResultsToSystem:

    def test_error_scan_not_fed(self):
        """Scan en erreur → rien n'est injecte."""
        r = ScanResult(scanner="promptfoo", error="timeout")
        fed = feed_results_to_system(r, "postgresql://localhost/test")
        assert fed["flaws_registered"] == 0
        assert fed["stored_in_memory"] is False

    def test_flaws_fed_to_budget(self):
        """Failles detectees → injectees dans le budget."""
        r = ScanResult(
            scanner="garak",
            vulnerabilities=[{"name": "v1", "severity": "high"}],
        )
        with patch("sitra_achra.budget_parasitaire.BudgetParasitaire") as MockBP, \
             patch("sitra_achra.external_scanner._save_to_history"), \
             patch("psycopg2.connect", side_effect=Exception("no db")):
            bp_inst = MockBP.return_value
            fed = feed_results_to_system(r, "postgresql://localhost/test")

        assert fed["flaws_registered"] == 1
        bp_inst.register_flaw.assert_called_once_with(1)

    def test_stores_in_epistememory(self):
        """Resultats stockes en epistememory quand DB disponible."""
        r = ScanResult(
            scanner="promptfoo",
            total_tests=50,
            passed=48,
            failed=2,
            attack_success_rate=0.04,
            vulnerabilities=[{"name": "v1", "severity": "medium"}],
        )
        mock_conn = MagicMock()
        mock_conn.closed = False  # evite la branche retry de pool.get_conn
        mock_cur = MagicMock()
        # `with conn.cursor() as cur:` — __enter__ doit retourner mock_cur
        mock_cur.__enter__.return_value = mock_cur
        mock_cur.__exit__.return_value = False
        mock_conn.cursor.return_value = mock_cur

        with patch("sitra_achra.budget_parasitaire.BudgetParasitaire"), \
             patch("sitra_achra.external_scanner._save_to_history"), \
             patch("psycopg2.connect", return_value=mock_conn):
            fed = feed_results_to_system(r, "postgresql://localhost/test")

        assert fed["stored_in_memory"] is True
        mock_cur.execute.assert_called_once()
        sql_arg = mock_cur.execute.call_args[0][0]
        assert "INSERT INTO epistememory" in sql_arg


# ---------------------------------------------------------------------------
# detect_regression
# ---------------------------------------------------------------------------


class TestDetectRegression:

    def test_no_history(self, tmp_path):
        """Pas d'historique → None."""
        with patch("sitra_achra.external_scanner._SCAN_HISTORY", tmp_path / "nope.json"):
            assert detect_regression("promptfoo") is None

    def test_single_scan_no_comparison(self, tmp_path):
        """Un seul scan → pas de comparaison possible."""
        hist = tmp_path / "history.json"
        hist.write_text(json.dumps([
            {"scanner": "promptfoo", "flaw_count": 2, "attack_success_rate": 0.1},
        ]))
        with patch("sitra_achra.external_scanner._SCAN_HISTORY", hist):
            assert detect_regression("promptfoo") is None

    def test_regression_detected(self, tmp_path):
        """Plus de failles → regression."""
        hist = tmp_path / "history.json"
        hist.write_text(json.dumps([
            {"scanner": "garak", "flaw_count": 1, "attack_success_rate": 0.05},
            {"scanner": "garak", "flaw_count": 4, "attack_success_rate": 0.15},
        ]))
        with patch("sitra_achra.external_scanner._SCAN_HISTORY", hist):
            result = detect_regression("garak")
        assert result["regression"] is True
        assert result["delta_flaws"] == 3

    def test_no_regression(self, tmp_path):
        """Moins de failles → pas de regression."""
        hist = tmp_path / "history.json"
        hist.write_text(json.dumps([
            {"scanner": "promptfoo", "flaw_count": 5, "attack_success_rate": 0.2},
            {"scanner": "promptfoo", "flaw_count": 3, "attack_success_rate": 0.1},
        ]))
        with patch("sitra_achra.external_scanner._SCAN_HISTORY", hist):
            result = detect_regression("promptfoo")
        assert result["regression"] is False

    def test_asr_spike_triggers_regression(self, tmp_path):
        """ASR augmente > 5% meme si flaw_count stable → regression."""
        hist = tmp_path / "history.json"
        hist.write_text(json.dumps([
            {"scanner": "garak", "flaw_count": 2, "attack_success_rate": 0.10},
            {"scanner": "garak", "flaw_count": 2, "attack_success_rate": 0.20},
        ]))
        with patch("sitra_achra.external_scanner._SCAN_HISTORY", hist):
            result = detect_regression("garak")
        assert result["regression"] is True


# ---------------------------------------------------------------------------
# _save_to_history
# ---------------------------------------------------------------------------


class TestSaveToHistory:

    def test_creates_history_file(self, tmp_path):
        """Cree le fichier si inexistant."""
        from sitra_achra.external_scanner import _save_to_history

        hist = tmp_path / "sub" / "history.json"
        with patch("sitra_achra.external_scanner._SCAN_HISTORY", hist):
            _save_to_history(ScanResult(scanner="test"))

        assert hist.exists()
        data = json.loads(hist.read_text())
        assert len(data) == 1
        assert data[0]["scanner"] == "test"

    def test_appends_to_existing(self, tmp_path):
        """Ajoute au fichier existant."""
        from sitra_achra.external_scanner import _save_to_history

        hist = tmp_path / "history.json"
        hist.write_text(json.dumps([{"scanner": "old", "timestamp": 0}]))

        with patch("sitra_achra.external_scanner._SCAN_HISTORY", hist):
            _save_to_history(ScanResult(scanner="new"))

        data = json.loads(hist.read_text())
        assert len(data) == 2

    def test_caps_at_50(self, tmp_path):
        """Historique plafonne a 50 entrees."""
        from sitra_achra.external_scanner import _save_to_history

        hist = tmp_path / "history.json"
        existing = [{"scanner": f"s{i}", "timestamp": i} for i in range(55)]
        hist.write_text(json.dumps(existing))

        with patch("sitra_achra.external_scanner._SCAN_HISTORY", hist):
            _save_to_history(ScanResult(scanner="latest"))

        data = json.loads(hist.read_text())
        assert len(data) == 50
        assert data[-1]["scanner"] == "latest"


# ---------------------------------------------------------------------------
# task_external_scan (orchestrateur)
# ---------------------------------------------------------------------------


class TestTaskExternalScan:

    def test_runs_both_scanners(self):
        """Lance Promptfoo et Garak."""
        pf_result = ScanResult(scanner="promptfoo", total_tests=10, passed=9, failed=1)
        gk_result = ScanResult(scanner="garak", total_tests=5, passed=4, failed=1)

        with patch("sitra_achra.external_scanner.run_promptfoo_scan", return_value=pf_result), \
             patch("sitra_achra.external_scanner.run_garak_scan", return_value=gk_result), \
             patch("sitra_achra.external_scanner.feed_results_to_system"), \
             patch("sitra_achra.external_scanner.detect_regression", return_value=None):
            results = task_external_scan()

        assert "promptfoo" in results
        assert "garak" in results

    def test_skip_promptfoo(self):
        """run_promptfoo=False → pas de scan Promptfoo."""
        gk_result = ScanResult(scanner="garak")

        with patch("sitra_achra.external_scanner.run_garak_scan", return_value=gk_result), \
             patch("sitra_achra.external_scanner.feed_results_to_system"), \
             patch("sitra_achra.external_scanner.detect_regression", return_value=None):
            results = task_external_scan(run_promptfoo=False)

        assert "promptfoo" not in results
        assert "garak" in results

    def test_regression_included(self):
        """Regression detectee → dans les resultats."""
        pf_result = ScanResult(scanner="promptfoo", total_tests=10, passed=8, failed=2)
        reg = {"regression": True, "prev_flaws": 1, "curr_flaws": 3, "delta_flaws": 2}

        with patch("sitra_achra.external_scanner.run_promptfoo_scan", return_value=pf_result), \
             patch("sitra_achra.external_scanner.feed_results_to_system"), \
             patch("sitra_achra.external_scanner.detect_regression", return_value=reg):
            results = task_external_scan(run_garak=False)

        assert "promptfoo_regression" in results
        assert results["promptfoo_regression"]["delta_flaws"] == 2
