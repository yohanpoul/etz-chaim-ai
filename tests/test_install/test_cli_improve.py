from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from typer.testing import CliRunner


def _sample_event():
    from etzchaim.metacognition.events import MetacognitionEvent

    return MetacognitionEvent(
        id="known-p0-psql-helper-pollution",
        source="p0-preflight",
        severity="error",
        title="Known /my/psql test helper pollution",
        description="The P0 preflight reproduced a leaked psql helper path.",
        evidence=["/my/psql appears in P0"],
        priority=100,
        verification_command=".venv/bin/python -m pytest tests/test_install/test_psql_helper.py sifrei_yesod/tests/test_folio_map.py -q",
        verified=False,
        verification_result={"command": "fake", "exit_code": 1, "passed": False},
    )


def test_help_shows_improve_command():
    from etzchaim.cli.app import app

    runner = CliRunner()
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "improve" in result.stdout


def test_improve_dry_run_json(monkeypatch, tmp_path):
    from etzchaim.cli.app import app
    from etzchaim.metacognition import report

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("ETZCHAIM_STATE_DIR", raising=False)
    monkeypatch.setattr(report, "collect_events", lambda repo_root: [_sample_event()])
    monkeypatch.setattr(
        report,
        "utc_now",
        lambda: datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
    )

    runner = CliRunner()
    result = runner.invoke(app, ["improve", "--once", "--dry-run", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["status"] == "dry-run"
    assert data["dry_run"] is True
    assert data["events"][0]["id"] == "known-p0-psql-helper-pollution"
    assert data["events"][0]["verified"] is False
    assert data["events"][0]["verification_result"]["passed"] is False
    assert data["faculty_evaluation"]["failure_insight"]["status"] == "unavailable"
    assert data["faculty_evaluation"]["guardian"]["verdict"] in {
        "proceed",
        "caution",
        "veto",
        "unavailable",
    }
    assert data["faculty_evaluation"]["intent"]["status"] == "no_active_intent"
    assert data["would_write"]["ledger"].startswith(str(tmp_path))
    assert not (tmp_path / ".etz-chaim").exists()


def test_improve_once_json_writes_only_under_temp_home(monkeypatch, tmp_path):
    from etzchaim.cli.app import app
    from etzchaim.metacognition import report

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("ETZCHAIM_STATE_DIR", raising=False)
    monkeypatch.setattr(report, "collect_events", lambda repo_root: [_sample_event()])
    monkeypatch.setattr(
        report,
        "utc_now",
        lambda: datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
    )

    runner = CliRunner()
    result = runner.invoke(app, ["improve", "--once", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    report_path = data["written"]["report"]
    state_path = data["written"]["state"]
    ledger_path = data["written"]["ledger"]
    assert report_path.startswith(str(tmp_path))
    assert state_path.startswith(str(tmp_path))
    assert ledger_path.startswith(str(tmp_path))
    assert data["faculty_evaluation"]["failure_insight"]["source"] in {
        "stub",
        "failuretoinsight.guide_next_hypothesis",
        "failuretoinsight.analyze_failure",
    }
    assert data["faculty_evaluation"]["guardian"]["verdict"] in {
        "proceed",
        "caution",
        "veto",
        "unavailable",
    }
    assert (tmp_path / ".etz-chaim" / "runs" / "improve-20260604T120000Z.md").exists()
    assert (tmp_path / ".etz-chaim" / "state" / "last_improve_run.json").exists()
    assert (tmp_path / ".etz-chaim" / "state" / "improve_ledger.jsonl").exists()


def test_improve_requires_once():
    from etzchaim.cli.app import app

    runner = CliRunner()
    result = runner.invoke(app, ["improve", "--json"])

    assert result.exit_code != 0
    assert "Phase 1A only supports explicit --once" in result.stdout


def test_make_doctor_target_exists():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert ".PHONY:" in makefile
    assert "doctor" in makefile
    assert "$(VENV)/bin/etzchaim doctor --json" in makefile
