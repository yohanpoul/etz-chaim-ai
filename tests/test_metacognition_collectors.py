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


def test_p0_psql_known_issue_is_collected_when_current_reproduction_still_fails(tmp_path):
    from etzchaim.metacognition.collectors import collect_known_p0_events

    report = tmp_path / "strategy" / "codex-prompt" / "codex-plan" / "etzchaim-p0-preflight.md"
    report.parent.mkdir(parents=True)
    report.write_text("The full test reproduced /my/psql inter-test pollution.", encoding="utf-8")

    def fake_runner(command, cwd, timeout_seconds):
        return {
            "command": " ".join(command),
            "exit_code": 1,
            "passed": False,
            "stdout": "subprocess tried /my/psql after helper pollution",
            "stderr": "",
            "duration_seconds": 0.1,
            "timed_out": False,
        }

    events = collect_known_p0_events(tmp_path, runner=fake_runner)

    assert [event.id for event in events] == ["known-p0-psql-helper-pollution"]
    assert events[0].verified is False
    assert events[0].verification_result["passed"] is False


def test_p0_psql_known_issue_is_suppressed_when_current_reproduction_passes(tmp_path):
    from etzchaim.metacognition.collectors import collect_known_p0_events

    report = tmp_path / "strategy" / "codex-prompt" / "codex-plan" / "etzchaim-p0-preflight.md"
    report.parent.mkdir(parents=True)
    report.write_text("The full test reproduced /my/psql inter-test pollution.", encoding="utf-8")

    def fake_runner(command, cwd, timeout_seconds):
        return {
            "command": " ".join(command),
            "exit_code": 0,
            "passed": True,
            "stdout": "17 passed",
            "stderr": "",
            "duration_seconds": 0.16,
            "timed_out": False,
        }

    events = collect_known_p0_events(tmp_path, runner=fake_runner)

    assert events == []


def test_p0_psql_known_issue_is_suppressed_when_current_failure_is_different(tmp_path):
    from etzchaim.metacognition.collectors import collect_known_p0_events

    report = tmp_path / "strategy" / "codex-prompt" / "codex-plan" / "etzchaim-p0-preflight.md"
    report.parent.mkdir(parents=True)
    report.write_text("The full test reproduced /my/psql inter-test pollution.", encoding="utf-8")

    def fake_runner(command, cwd, timeout_seconds):
        return {
            "command": " ".join(command),
            "exit_code": 1,
            "passed": False,
            "stdout": "RuntimeError: psql non trouvé",
            "stderr": "",
            "duration_seconds": 0.1,
            "timed_out": False,
        }

    events = collect_known_p0_events(tmp_path, runner=fake_runner)

    assert events == []


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


def test_pytest_failures_become_events(tmp_path):
    from etzchaim.metacognition.collectors import collect_pytest_events

    calls = []

    def fake_runner(command, cwd, timeout_seconds):
        calls.append((command, cwd, timeout_seconds))
        return {
            "command": ".venv/bin/python -m pytest sifrei_yesod/tests/test_idra_corpus_fidelity.py::test_s1_each_tikkun_has_zohar_and_vital -q",
            "exit_code": 1,
            "passed": False,
            "stdout": "FAILED test_s1_each_tikkun_has_zohar_and_vital\nAssertionError: unrelated failure",
            "stderr": "",
            "duration_seconds": 0.42,
            "timed_out": False,
        }

    events = collect_pytest_events(
        tmp_path,
        paths=["sifrei_yesod/tests/test_idra_corpus_fidelity.py::test_s1_each_tikkun_has_zohar_and_vital"],
        runner=fake_runner,
    )

    assert len(events) == 1
    event = events[0]
    assert event.id == "pytest-bounded-subset-failed"
    assert event.source == "pytest"
    assert event.verified is False
    assert event.verification_result["exit_code"] == 1
    assert event.verification_command == (
        ".venv/bin/python -m pytest "
        "sifrei_yesod/tests/test_idra_corpus_fidelity.py::test_s1_each_tikkun_has_zohar_and_vital -q"
    )
    assert calls[0][0] == [
        ".venv/bin/python",
        "-m",
        "pytest",
        "sifrei_yesod/tests/test_idra_corpus_fidelity.py::test_s1_each_tikkun_has_zohar_and_vital",
        "-q",
    ]


def test_idra_corpus_gate_pytest_output_becomes_diagnostic_event(tmp_path):
    from etzchaim.metacognition.collectors import collect_pytest_events

    def fake_runner(command, cwd, timeout_seconds):
        return {
            "command": " ".join(command),
            "exit_code": 1,
            "passed": False,
            "stdout": """
FAILED sifrei_yesod/tests/test_idra_corpus_fidelity.py::test_s1_each_tikkun_has_zohar_and_vital
AssertionError: Tikkunim missing (other than expected T11): [1, 2, 3, 4, 5, 6, 9, 10, 12]
assert aid in id_to_seealso[t], f"Non-bidirectional: {aid}→{t} but not {t}→{aid}"
FAILED sifrei_yesod/tests/test_idra_corpus_fidelity.py::test_s3_see_also_bidirectional
AssertionError: Non-bidirectional: Z-IR-T08-001→EC-H3S2-T08-001 but not EC-H3S2-T08-001→Z-IR-T08-001
""",
            "stderr": "",
            "duration_seconds": 0.42,
            "timed_out": False,
        }

    events = collect_pytest_events(tmp_path, runner=fake_runner)

    assert len(events) == 1
    event = events[0]
    assert event.id == "pytest-corpus-gate-missing-tikkunim-non-bidir-links"
    assert event.source == "pytest"
    assert event.title == "Corpus gate pytest failed: missing tikkunim and non-bidirectional links"
    assert event.verified is False
    assert event.verification_result["exit_code"] == 1
    assert event.evidence[:3] == [
        "diagnostic_category=corpus-gate",
        "missing_tikkunim_unexpected=[1, 2, 3, 4, 5, 6, 9, 10, 12]",
        "non_bidirectional_first=Z-IR-T08-001→EC-H3S2-T08-001 missing reciprocal",
    ]
