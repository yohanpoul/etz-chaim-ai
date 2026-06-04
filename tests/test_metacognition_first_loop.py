from __future__ import annotations

import builtins
import json
import subprocess
import sys
from datetime import UTC, datetime
from types import SimpleNamespace


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
    assert result["faculty_evaluation"]["failure_insight"]["status"] == "unavailable"
    assert result["faculty_evaluation"]["guardian"]["verdict"] == "unavailable"
    assert result["faculty_evaluation"]["intent"]["status"] == "no_active_intent"
    assert result["would_write"]["report"].endswith("improve-20260604T120000Z.md")
    assert "written" not in result
    assert not (tmp_path / ".etz-chaim").exists()


def test_build_run_payload_uses_explicit_faculty_adapters(monkeypatch, tmp_path):
    from etzchaim.metacognition import report

    class FakeFailureToInsight:
        def __init__(self):
            self.domains = []

        def guide_next_hypothesis(self, domain=None):
            self.domains.append(domain)
            return SimpleNamespace(
                recurring_root_causes=["fixture drift"],
                avoid_patterns=["implicit mutation"],
                promising_directions=["adapter injection"],
                confidence=0.82,
            )

    class FakeGuardian:
        def __init__(self):
            self.calls = []

        def evaluate_confidence(self, domain, query=""):
            self.calls.append((domain, query))
            return {
                "recommendation": "caution",
                "confidence": 0.64,
                "reason": "explicit fake guardian",
                "active_biases": ["automation-bias"],
            }

    class FakeIntentKeeper:
        def __init__(self):
            self.calls = []

        def summarize_event_intent(self, event, action=None):
            self.calls.append((event.id, action.id if action else None))
            return {
                "status": "linked",
                "intent_id": "intent-p2d",
                "summary": "P2D intent linked explicitly",
            }

    failure = FakeFailureToInsight()
    guardian = FakeGuardian()
    intent = FakeIntentKeeper()

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("ETZCHAIM_STATE_DIR", raising=False)
    monkeypatch.setattr(report, "collect_events", lambda repo_root: [_sample_event()])

    result = report.build_run_payload(
        dry_run=True,
        repo_root=tmp_path,
        now=datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
        faculty_adapters={
            "failure_to_insight": failure,
            "guardian": guardian,
            "intentkeeper": intent,
        },
    )

    assert failure.domains == ["p0-preflight"]
    assert guardian.calls
    assert guardian.calls[0][0] == "p0-preflight"
    assert "Known /my/psql test helper pollution" in guardian.calls[0][1]
    assert intent.calls == [
        (
            "known-p0-psql-helper-pollution",
            "patch-known-p0-psql-helper-pollution",
        )
    ]
    assert result["faculty_evaluation"]["failure_insight"]["status"] == "available"
    assert (
        result["faculty_evaluation"]["failure_insight"]["source"]
        == "failuretoinsight.guide_next_hypothesis"
    )
    assert "fixture drift" in result["faculty_evaluation"]["failure_insight"]["hypothesis"]
    assert result["faculty_evaluation"]["guardian"]["verdict"] == "caution"
    assert result["faculty_evaluation"]["guardian"]["active_biases"] == [
        "automation-bias"
    ]
    assert result["faculty_evaluation"]["intent"]["status"] == "linked"
    assert result["faculty_evaluation"]["intent"]["intent_id"] == "intent-p2d"
    assert all(action["applies_patch"] is False for action in result["proposed_actions"])
    assert not (tmp_path / ".etz-chaim").exists()


def test_run_improve_once_accepts_explicit_faculty_adapters(monkeypatch, tmp_path):
    from etzchaim.metacognition import report

    class FakeFailureToInsight:
        def guide_next_hypothesis(self, domain=None):
            return SimpleNamespace(
                recurring_root_causes=["pytest signal"],
                avoid_patterns=[],
                promising_directions=[],
                confidence=0.51,
            )

    class FakeGuardian:
        def evaluate_confidence(self, domain, query=""):
            return {
                "recommendation": "caution",
                "confidence": 0.44,
                "reason": "explicit run adapter",
                "active_biases": [],
            }

    class FakeIntentKeeper:
        def summarize_event_intent(self, event, action=None):
            return {
                "status": "linked",
                "intent_id": "intent-run",
                "summary": "run adapter linked",
            }

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("ETZCHAIM_STATE_DIR", raising=False)
    monkeypatch.setattr(report, "collect_events", lambda repo_root: [_sample_event()])

    result = report.run_improve_once(
        dry_run=True,
        repo_root=tmp_path,
        now=datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
        faculty_adapters={
            "failure_to_insight": FakeFailureToInsight(),
            "guardian": FakeGuardian(),
            "intentkeeper": FakeIntentKeeper(),
        },
    )

    assert result["status"] == "dry-run"
    assert result["faculty_evaluation"]["failure_insight"]["status"] == "available"
    assert result["faculty_evaluation"]["guardian"]["verdict"] == "caution"
    assert result["faculty_evaluation"]["intent"]["status"] == "linked"
    assert all(action["applies_patch"] is False for action in result["proposed_actions"])
    assert not (tmp_path / ".etz-chaim").exists()


def test_first_loop_default_faculties_stay_unavailable(monkeypatch, tmp_path):
    from etzchaim.metacognition import report

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("ETZCHAIM_STATE_DIR", raising=False)
    monkeypatch.setattr(report, "collect_events", lambda repo_root: [_sample_event()])

    result = report.build_run_payload(
        dry_run=True,
        repo_root=tmp_path,
        now=datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
    )

    assert result["faculty_evaluation"]["failure_insight"]["status"] == "unavailable"
    assert result["faculty_evaluation"]["guardian"]["verdict"] == "unavailable"
    assert result["faculty_evaluation"]["intent"]["status"] == "no_active_intent"
    assert all(action["applies_patch"] is False for action in result["proposed_actions"])


def test_first_loop_default_does_not_import_faculty_or_db_modules(
    monkeypatch,
    tmp_path,
):
    from etzchaim.metacognition import report

    def is_forbidden_module(name: str) -> bool:
        return (
            name == "selfmodel.guardian"
            or name.startswith("selfmodel.guardian.")
            or name.startswith("failuretoinsight")
            or name.startswith("intentkeeper")
            or name.startswith("psycopg")
        )

    for module_name in list(sys.modules):
        if is_forbidden_module(module_name):
            monkeypatch.delitem(sys.modules, module_name, raising=False)

    imported: list[str] = []
    original_import = builtins.__import__

    def tracking_import(name, *args, **kwargs):
        if is_forbidden_module(name):
            imported.append(name)
        return original_import(name, *args, **kwargs)

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("ETZCHAIM_STATE_DIR", raising=False)
    monkeypatch.setattr(builtins, "__import__", tracking_import)
    monkeypatch.setattr(report, "collect_events", lambda repo_root: [_sample_event()])

    result = report.build_run_payload(
        dry_run=True,
        repo_root=tmp_path,
        now=datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
    )

    loaded = sorted(name for name in sys.modules if is_forbidden_module(name))
    assert imported == []
    assert loaded == []
    assert result["faculty_evaluation"]["failure_insight"]["status"] == "unavailable"
    assert result["faculty_evaluation"]["guardian"]["verdict"] == "unavailable"
    assert result["faculty_evaluation"]["intent"]["status"] == "no_active_intent"


def test_build_run_payload_does_not_call_analyze_failure_adapter(
    monkeypatch,
    tmp_path,
):
    from etzchaim.metacognition import report

    class AnalyzeOnlyFailureToInsight:
        called = False

        def analyze_failure(self, **kwargs):
            self.called = True
            raise AssertionError("analyze_failure must not be called by report")

    adapter = AnalyzeOnlyFailureToInsight()

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("ETZCHAIM_STATE_DIR", raising=False)
    monkeypatch.setattr(report, "collect_events", lambda repo_root: [_sample_event()])

    result = report.build_run_payload(
        dry_run=True,
        repo_root=tmp_path,
        now=datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
        faculty_adapters={"failure_to_insight": adapter},
    )

    assert adapter.called is False
    assert result["faculty_evaluation"]["failure_insight"]["status"] == "unavailable"
    assert (
        "not read-only by default"
        in result["faculty_evaluation"]["failure_insight"]["hypothesis"]
    )


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
    rendered_report = report_path.read_text(encoding="utf-8")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert "Known /my/psql test helper pollution" in rendered_report
    assert "## Faculty Bridge" in rendered_report
    assert state["faculty_evaluation"]["guardian"]["verdict"] in {
        "proceed",
        "caution",
        "veto",
        "unavailable",
    }
    assert state["top_issue"]["id"] == (
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
    assert entries[0]["guardian_verdict"] in {"proceed", "caution", "veto", "unavailable"}
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
