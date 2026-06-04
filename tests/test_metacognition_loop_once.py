from __future__ import annotations

import json
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
        verified=False,
        verification_result={"command": "fake", "exit_code": 1, "passed": False},
    )


def _relative_files(root):
    return sorted(
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file()
    )


def _assert_improve_payload_is_safe(improve_payload):
    assert improve_payload["faculty_evaluation"]["guardian"]["verdict"] == "unavailable"
    assert all(
        action["applies_patch"] is False
        for action in improve_payload["proposed_actions"]
    )


def test_loop_once_dry_run_is_read_only(monkeypatch, tmp_path):
    from etzchaim.metacognition import report, runtime_loop

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("ETZCHAIM_STATE_DIR", raising=False)
    monkeypatch.setattr(report, "collect_events", lambda repo_root: [_sample_event()])

    result = runtime_loop.run_loop_once(
        dry_run=True,
        repo_root=tmp_path,
        now=datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
    )

    assert result["status"] == "dry-run"
    assert result["dry_run"] is True
    assert result["cycle_id"] == "loop-20260604T120000Z"
    assert result["heartbeat"]["cycle_id"] == "loop-20260604T120000Z"
    assert result["heartbeat"]["status"] == "dry-run"
    assert result["heartbeat"]["improve_status"] == "dry-run"
    assert result["improve"]["status"] == "dry-run"
    assert result["would_write"]["loop_state"].endswith("last_loop_run.json")
    assert result["would_write"]["loop_heartbeat"].endswith("loop_heartbeat.jsonl")
    _assert_improve_payload_is_safe(result["improve"])
    assert not (tmp_path / ".etz-chaim").exists()


def test_loop_once_write_mode_writes_expected_files(monkeypatch, tmp_path):
    from etzchaim.metacognition import report, runtime_loop

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("ETZCHAIM_STATE_DIR", raising=False)
    monkeypatch.setattr(report, "collect_events", lambda repo_root: [_sample_event()])

    result = runtime_loop.run_loop_once(
        dry_run=False,
        repo_root=tmp_path,
        now=datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
    )

    expected_files = [
        ".etz-chaim/runs/improve-20260604T120000Z.md",
        ".etz-chaim/state/improve_ledger.jsonl",
        ".etz-chaim/state/last_improve_run.json",
        ".etz-chaim/state/last_loop_run.json",
        ".etz-chaim/state/loop_heartbeat.jsonl",
    ]
    assert _relative_files(tmp_path) == expected_files
    assert result["status"] == "written"
    assert result["cycle_id"] == "loop-20260604T120000Z"
    assert result["written"]["loop_state"].endswith("last_loop_run.json")
    assert result["written"]["loop_heartbeat"].endswith("loop_heartbeat.jsonl")
    _assert_improve_payload_is_safe(result["improve"])

    state_path = tmp_path / ".etz-chaim" / "state" / "last_loop_run.json"
    heartbeat_path = tmp_path / ".etz-chaim" / "state" / "loop_heartbeat.jsonl"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    heartbeat_lines = heartbeat_path.read_text(encoding="utf-8").splitlines()
    heartbeat = json.loads(heartbeat_lines[0])

    assert state["cycle_id"] == "loop-20260604T120000Z"
    assert state["status"] == "written"
    assert heartbeat_lines == [json.dumps(heartbeat, sort_keys=True)]
    assert heartbeat["cycle_id"] == "loop-20260604T120000Z"
    assert heartbeat["status"] == "written"
    assert heartbeat["guardian_verdict"] == "unavailable"
    assert heartbeat["applies_patch"] is False


def test_loop_once_heartbeat_appends(monkeypatch, tmp_path):
    from etzchaim.metacognition import report, runtime_loop

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("ETZCHAIM_STATE_DIR", raising=False)
    monkeypatch.setattr(report, "collect_events", lambda repo_root: [_sample_event()])

    runtime_loop.run_loop_once(
        dry_run=False,
        repo_root=tmp_path,
        now=datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
    )
    runtime_loop.run_loop_once(
        dry_run=False,
        repo_root=tmp_path,
        now=datetime(2026, 6, 4, 12, 1, tzinfo=UTC),
    )

    heartbeat_path = tmp_path / ".etz-chaim" / "state" / "loop_heartbeat.jsonl"
    entries = [
        json.loads(line)
        for line in heartbeat_path.read_text(encoding="utf-8").splitlines()
    ]

    assert [entry["cycle_id"] for entry in entries] == [
        "loop-20260604T120000Z",
        "loop-20260604T120100Z",
    ]
    assert all(entry["applies_patch"] is False for entry in entries)
