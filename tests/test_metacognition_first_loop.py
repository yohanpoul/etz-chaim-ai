from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime


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
    )


def test_dry_run_returns_would_write_without_creating_state(monkeypatch, tmp_path):
    from etzchaim.metacognition import report

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("ETZCHAIM_STATE_DIR", raising=False)
    monkeypatch.setattr(report, "collect_events", lambda repo_root: [_sample_event()])

    result = report.run_improve_once(
        dry_run=True,
        repo_root=tmp_path,
        now=datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
    )

    assert result["status"] == "dry-run"
    assert result["dry_run"] is True
    assert result["would_write"]["report"].endswith("improve-20260604T120000Z.md")
    assert "written" not in result
    assert not (tmp_path / ".etz-chaim").exists()


def test_once_writes_report_and_state_under_temp_home(monkeypatch, tmp_path):
    from etzchaim.metacognition import report

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("ETZCHAIM_STATE_DIR", raising=False)
    monkeypatch.setattr(report, "collect_events", lambda repo_root: [_sample_event()])

    result = report.run_improve_once(
        dry_run=False,
        repo_root=tmp_path,
        now=datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
    )

    report_path = tmp_path / ".etz-chaim" / "runs" / "improve-20260604T120000Z.md"
    state_path = tmp_path / ".etz-chaim" / "state" / "last_improve_run.json"

    assert result["status"] == "written"
    assert result["written"]["report"] == str(report_path)
    assert result["written"]["state"] == str(state_path)
    assert report_path.exists()
    assert state_path.exists()
    assert "Known /my/psql test helper pollution" in report_path.read_text(encoding="utf-8")
    assert json.loads(state_path.read_text(encoding="utf-8"))["top_issue"]["id"] == (
        "known-p0-psql-helper-pollution"
    )


def test_ledger_appends_one_line_per_run(monkeypatch, tmp_path):
    from etzchaim.metacognition import report

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("ETZCHAIM_STATE_DIR", raising=False)
    monkeypatch.setattr(report, "collect_events", lambda repo_root: [_sample_event()])

    report.run_improve_once(
        dry_run=False,
        repo_root=tmp_path,
        now=datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
    )
    report.run_improve_once(
        dry_run=False,
        repo_root=tmp_path,
        now=datetime(2026, 6, 4, 12, 1, tzinfo=UTC),
    )

    ledger_path = tmp_path / ".etz-chaim" / "state" / "improve_ledger.jsonl"
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    entries = [json.loads(line) for line in lines]

    assert len(entries) == 2
    assert entries[0]["top_issue_id"] == "known-p0-psql-helper-pollution"
    assert entries[0]["action_id"] == "patch-known-p0-psql-helper-pollution"
    assert entries[0]["action_type"] == "patch"
    assert entries[0]["applies_patch"] is False
    assert entries[0]["guardian_verdict"] == "not_evaluated_p2b"
    assert entries[1]["timestamp"] == "2026-06-04T12:01:00Z"


def test_dry_run_writes_no_ledger(monkeypatch, tmp_path):
    from etzchaim.metacognition import report

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("ETZCHAIM_STATE_DIR", raising=False)
    monkeypatch.setattr(report, "collect_events", lambda repo_root: [_sample_event()])

    result = report.run_improve_once(
        dry_run=True,
        repo_root=tmp_path,
        now=datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
    )

    assert result["dry_run"] is True
    assert not (tmp_path / ".etz-chaim").exists()


def test_first_loop_does_not_start_services_or_run_migrations(monkeypatch, tmp_path):
    from etzchaim.metacognition import report

    calls = []

    def forbidden_call(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("subprocess should not be called")

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(subprocess, "call", forbidden_call)
    monkeypatch.setattr(subprocess, "run", forbidden_call)
    monkeypatch.setattr(report, "collect_events", lambda repo_root: [_sample_event()])

    result = report.run_improve_once(
        dry_run=True,
        repo_root=tmp_path,
        now=datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
    )

    assert result["status"] == "dry-run"
    assert calls == []
