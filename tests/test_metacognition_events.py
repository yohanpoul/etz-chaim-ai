from __future__ import annotations

import pytest


def test_event_serialization_is_stable():
    from etzchaim.metacognition.events import MetacognitionEvent

    event = MetacognitionEvent(
        id="python-command-missing",
        source="python",
        severity="warning",
        title="python command is not available",
        description="The shell cannot resolve the python command.",
        evidence=["python was not found on PATH"],
        priority=30,
        verification_command="python --version",
    )

    assert event.to_dict() == {
        "id": "python-command-missing",
        "source": "python",
        "severity": "warning",
        "title": "python command is not available",
        "description": "The shell cannot resolve the python command.",
        "evidence": ["python was not found on PATH"],
        "priority": 30,
        "verification_command": "python --version",
    }


def test_action_types_are_restricted():
    from etzchaim.metacognition.events import ProposedAction

    action = ProposedAction(
        id="patch-known-psql-test-pollution",
        type="patch",
        title="Patch the psql helper pollution",
        description="Reset the helper state between tests.",
        event_ids=["known-p0-psql-helper-pollution"],
        verification_command=".venv/bin/python -m pytest tests/test_install/test_psql_helper.py sifrei_yesod/tests/test_folio_map.py -q",
    )
    assert action.to_dict()["applies_patch"] is False

    with pytest.raises(ValueError, match="Unsupported action type"):
        ProposedAction(
            id="invalid",
            type="mutation",
            title="Invalid action",
            description="Invalid action type.",
            event_ids=["known-p0-psql-helper-pollution"],
            verification_command="true",
        )


def test_top_issue_uses_priority_then_id():
    from etzchaim.metacognition.actions import choose_top_issue
    from etzchaim.metacognition.events import MetacognitionEvent

    lower = MetacognitionEvent(
        id="docker-not-running",
        source="doctor",
        severity="warning",
        title="Docker is not running",
        description="Docker is unavailable locally.",
        evidence=["doctor check failed"],
        priority=70,
        verification_command="etzchaim doctor --json",
    )
    higher = MetacognitionEvent(
        id="known-p0-psql-helper-pollution",
        source="p0-preflight",
        severity="error",
        title="Known /my/psql test helper pollution",
        description="The P0 preflight reproduced a leaked psql helper path.",
        evidence=["/my/psql appears in P0"],
        priority=100,
        verification_command=".venv/bin/python -m pytest tests/test_install/test_psql_helper.py sifrei_yesod/tests/test_folio_map.py -q",
    )

    assert choose_top_issue([lower, higher]).id == "known-p0-psql-helper-pollution"


def test_synthesize_maps_sources_to_action_types():
    from etzchaim.metacognition.actions import synthesize_actions
    from etzchaim.metacognition.events import MetacognitionEvent

    events = [
        MetacognitionEvent(
            id="pytest-bounded-subset-failed",
            source="pytest",
            severity="error",
            title="Bounded pytest observer found failures",
            description="A bounded pytest subset failed.",
            evidence=["FAILED tests/example.py"],
            priority=95,
            verification_command=".venv/bin/python -m pytest tests/example.py -q",
        ),
        MetacognitionEvent(
            id="doctor-postgres-healthy",
            source="doctor",
            severity="error",
            title="Doctor check failed: postgres-healthy",
            description="PostgreSQL service not found",
            evidence=["PostgreSQL service not found"],
            priority=85,
            verification_command=".venv/bin/etzchaim doctor --json",
        ),
        MetacognitionEvent(
            id="status-no-services-running",
            source="status",
            severity="warning",
            title="No Etz Chaim services are running",
            description="No running services.",
            evidence=["services=0"],
            priority=45,
            verification_command=".venv/bin/etzchaim status --json",
        ),
        MetacognitionEvent(
            id="python-command-missing",
            source="python",
            severity="warning",
            title="python command is not available",
            description="The shell cannot resolve python.",
            evidence=["python was not found on PATH"],
            priority=30,
            verification_command="python --version",
        ),
    ]

    actions = synthesize_actions(events)
    by_event = {action.event_ids[0]: action for action in actions}

    assert by_event["pytest-bounded-subset-failed"].type == "test"
    assert by_event["doctor-postgres-healthy"].type == "alert"
    assert by_event["status-no-services-running"].type == "alert"
    assert by_event["python-command-missing"].type == "rule"


def test_corpus_gate_pytest_action_is_concrete_and_non_applying():
    from etzchaim.metacognition.actions import propose_action
    from etzchaim.metacognition.events import MetacognitionEvent

    event = MetacognitionEvent(
        id="pytest-corpus-gate-missing-tikkunim-non-bidir-links",
        source="pytest",
        severity="error",
        title="Corpus gate pytest failed: missing tikkunim and non-bidirectional links",
        description="Bounded pytest found source-backed corpus debt.",
        evidence=[
            "diagnostic_category=corpus-gate",
            "missing_tikkunim_unexpected=[1, 2, 3, 4, 5, 6, 9, 10, 12]",
            "non_bidirectional_first=Z-IR-T08-001→EC-H3S2-T08-001 missing reciprocal",
        ],
        priority=95,
        verification_command=".venv/bin/python -m pytest sifrei_yesod/tests/test_idra_corpus_fidelity.py -q",
        verified=False,
    )

    action = propose_action(event)

    assert action.id == "test-pytest-corpus-gate-missing-tikkunim-non-bidir-links"
    assert action.type == "test"
    assert action.applies_patch is False
    assert "corpus-gate" in action.title.lower()
    assert "missing tikkunim" in action.description
    assert "non-bidirectional" in action.description
    assert "do not repair the corpus automatically" in action.description


def test_actions_never_apply_patch():
    from etzchaim.metacognition.actions import synthesize_actions
    from etzchaim.metacognition.events import MetacognitionEvent, ProposedAction

    events = [
        MetacognitionEvent(
            id="known-p0-psql-helper-pollution",
            source="p0-preflight",
            severity="error",
            title="Known /my/psql test helper pollution",
            description="The P0 preflight reproduced a leaked psql helper path.",
            evidence=["/my/psql appears in P0"],
            priority=100,
            verification_command=".venv/bin/python -m pytest tests/test_install/test_psql_helper.py sifrei_yesod/tests/test_folio_map.py -q",
        )
    ]

    assert all(action.applies_patch is False for action in synthesize_actions(events))
    with pytest.raises(ValueError, match="applies_patch must remain False"):
        ProposedAction(
            id="unsafe",
            type="patch",
            title="Unsafe action",
            description="This should be rejected.",
            event_ids=["known-p0-psql-helper-pollution"],
            verification_command="true",
            applies_patch=True,
        )
