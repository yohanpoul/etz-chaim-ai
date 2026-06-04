from __future__ import annotations

import json
from datetime import UTC, datetime

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


def _relative_files(root):
    return sorted(
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file()
    )


def test_loop_help_mentions_once():
    from etzchaim.cli.app import app

    runner = CliRunner()
    result = runner.invoke(app, ["loop", "--help"])

    assert result.exit_code == 0
    assert "--once" in result.stdout


def test_loop_requires_once():
    from etzchaim.cli.app import app

    runner = CliRunner()
    result = runner.invoke(app, ["loop", "--dry-run", "--json"])

    assert result.exit_code != 0
    assert "Phase 3A loop only supports explicit --once." in result.stdout


def test_loop_dry_run_json_writes_no_files(monkeypatch, tmp_path):
    from etzchaim.cli.app import app
    from etzchaim.metacognition import report, runtime_loop

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("ETZCHAIM_STATE_DIR", raising=False)
    monkeypatch.setattr(report, "collect_events", lambda repo_root: [_sample_event()])
    monkeypatch.setattr(
        runtime_loop,
        "utc_now",
        lambda: datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
    )

    runner = CliRunner()
    result = runner.invoke(app, ["loop", "--once", "--dry-run", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["status"] == "dry-run"
    assert data["dry_run"] is True
    assert data["cycle_id"] == "loop-20260604T120000Z"
    assert data["improve"]["faculty_evaluation"]["guardian"]["verdict"] == "unavailable"
    assert all(
        action["applies_patch"] is False
        for action in data["improve"]["proposed_actions"]
    )
    assert _relative_files(tmp_path) == []


def test_loop_once_json_writes_only_under_temp_home(monkeypatch, tmp_path):
    from etzchaim.cli.app import app
    from etzchaim.metacognition import report, runtime_loop

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("ETZCHAIM_STATE_DIR", raising=False)
    monkeypatch.setattr(report, "collect_events", lambda repo_root: [_sample_event()])
    monkeypatch.setattr(
        runtime_loop,
        "utc_now",
        lambda: datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
    )

    runner = CliRunner()
    result = runner.invoke(app, ["loop", "--once", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    expected_files = [
        ".etz-chaim/runs/improve-20260604T120000Z.md",
        ".etz-chaim/state/improve_ledger.jsonl",
        ".etz-chaim/state/last_improve_run.json",
        ".etz-chaim/state/last_loop_run.json",
        ".etz-chaim/state/loop_heartbeat.jsonl",
    ]
    assert data["status"] == "written"
    assert data["cycle_id"] == "loop-20260604T120000Z"
    assert data["written"]["loop_state"].startswith(str(tmp_path))
    assert data["written"]["loop_heartbeat"].startswith(str(tmp_path))
    assert all(
        action["applies_patch"] is False
        for action in data["improve"]["proposed_actions"]
    )
    assert _relative_files(tmp_path) == expected_files
