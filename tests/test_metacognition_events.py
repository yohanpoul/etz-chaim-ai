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
