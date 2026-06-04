from __future__ import annotations


def test_doctor_failures_become_events(monkeypatch):
    from etzchaim.metacognition import collectors

    monkeypatch.setattr(
        collectors,
        "DOCTOR_CHECKS",
        [
            ("docker_running", lambda: (False, "Docker not running")),
            ("postgres_healthy", lambda: (False, "PostgreSQL service not found")),
            ("dashboard_port", lambda: (True, "Dashboard on canonical :8080")),
        ],
    )

    events = collectors.collect_doctor_events()
    ids = {event.id for event in events}

    assert "doctor-docker-running" in ids
    assert "doctor-postgres-healthy" in ids
    assert "doctor-dashboard-port" not in ids


def test_missing_python_command_becomes_rule_event(monkeypatch):
    from etzchaim.metacognition import collectors

    monkeypatch.setattr(
        collectors.shutil,
        "which",
        lambda command: None if command == "python" else f"/usr/bin/{command}",
    )

    events = collectors.collect_python_events()

    assert any(event.id == "python-command-missing" for event in events)


def test_p0_psql_known_issue_is_collected_when_report_exists(tmp_path):
    from etzchaim.metacognition.collectors import collect_known_p0_events

    report = tmp_path / "strategy" / "codex-prompt" / "codex-plan" / "etzchaim-p0-preflight.md"
    report.parent.mkdir(parents=True)
    report.write_text("The full test reproduced /my/psql inter-test pollution.", encoding="utf-8")

    events = collect_known_p0_events(tmp_path)

    assert [event.id for event in events] == ["known-p0-psql-helper-pollution"]


def test_collector_exception_becomes_event(monkeypatch, tmp_path):
    from etzchaim.metacognition import collectors

    def broken_collector(_repo_root):
        raise RuntimeError("boom")

    monkeypatch.setattr(collectors, "COLLECTORS", [broken_collector])

    events = collectors.collect_events(tmp_path)

    assert len(events) == 1
    assert events[0].source == "collector"
    assert events[0].severity == "warning"
    assert "boom" in events[0].description
