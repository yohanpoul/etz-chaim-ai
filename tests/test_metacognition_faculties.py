from __future__ import annotations

import builtins
from types import SimpleNamespace


def _event_and_action():
    from etzchaim.metacognition.actions import synthesize_actions
    from etzchaim.metacognition.events import MetacognitionEvent

    event = MetacognitionEvent(
        id="pytest-bounded-subset-failed",
        source="pytest",
        severity="error",
        title="Bounded pytest observer found failures",
        description="A bounded pytest subset failed.",
        evidence=["FAILED tests/example.py"],
        priority=95,
        verification_command=".venv/bin/python -m pytest tests/example.py -q",
        verified=False,
        verification_result={"passed": False, "exit_code": 1},
    )
    return event, synthesize_actions([event])[0]


def test_faculty_bridge_degrades_without_db():
    from etzchaim.metacognition.faculties import evaluate_faculties_for_event

    event, action = _event_and_action()

    result = evaluate_faculties_for_event(event, action)

    assert result["failure_insight"]["status"] == "unavailable"
    assert "FailureToInsight" in result["failure_insight"]["hypothesis"]
    assert result["guardian"]["verdict"] == "unavailable"
    assert "No explicit Guardian adapter" in result["guardian"]["reason"]
    assert result["intent"]["status"] == "no_active_intent"


def test_faculty_bridge_does_not_import_db_modules_without_adapters(monkeypatch):
    from etzchaim.metacognition.faculties import evaluate_faculties_for_event

    imported: list[str] = []
    original_import = builtins.__import__

    def tracking_import(name, *args, **kwargs):
        if name.startswith(("failuretoinsight", "intentkeeper")):
            imported.append(name)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", tracking_import)

    event, action = _event_and_action()
    result = evaluate_faculties_for_event(event, action)

    assert imported == []
    assert result["failure_insight"]["status"] == "unavailable"
    assert result["intent"]["status"] == "no_active_intent"


def test_analyze_failure_only_adapter_is_not_called_without_opt_in():
    from etzchaim.metacognition.faculties import evaluate_faculties_for_event

    class AnalyzeOnlyFailureToInsight:
        called = False

        def analyze_failure(self, **kwargs):
            self.called = True
            raise AssertionError("analyze_failure must not be called by default")

    adapter = AnalyzeOnlyFailureToInsight()
    event, action = _event_and_action()

    result = evaluate_faculties_for_event(
        event,
        action,
        adapters={"failure_to_insight": adapter},
    )

    assert adapter.called is False
    assert result["failure_insight"]["status"] == "unavailable"
    assert "not read-only by default" in result["failure_insight"]["hypothesis"]


def test_faculty_bridge_uses_injected_fakes():
    from etzchaim.metacognition.faculties import evaluate_faculties_for_event

    class FakeFailureToInsight:
        def guide_next_hypothesis(self, domain=None):
            return SimpleNamespace(
                recurring_root_causes=["fixture drift"],
                avoid_patterns=["stale corpus"],
                promising_directions=["tighten fixture coverage"],
                confidence=0.72,
            )

    class FakeGuardian:
        def evaluate_confidence(self, domain, query=""):
            return {
                "recommendation": "caution",
                "confidence": 0.42,
                "reason": f"domain={domain}; query={query[:12]}",
                "active_biases": ["confirmation"],
            }

    class FakeIntent:
        def summarize_event_intent(self, event, action=None):
            return {
                "status": "linked",
                "intent_id": "intent-123",
                "summary": f"{event.id}->{action.id}",
            }

    event, action = _event_and_action()
    result = evaluate_faculties_for_event(
        event,
        action,
        adapters={
            "failure_to_insight": FakeFailureToInsight(),
            "guardian": FakeGuardian(),
            "intentkeeper": FakeIntent(),
        },
    )

    assert result["failure_insight"]["status"] == "available"
    assert result["failure_insight"]["source"] == "failuretoinsight.guide_next_hypothesis"
    assert "fixture drift" in result["failure_insight"]["hypothesis"]
    assert result["guardian"]["verdict"] == "caution"
    assert result["guardian"]["active_biases"] == ["confirmation"]
    assert result["intent"]["status"] == "linked"
    assert result["intent"]["intent_id"] == "intent-123"


def test_faculty_bridge_handles_adapter_errors():
    from etzchaim.metacognition.faculties import evaluate_faculties_for_event

    class BrokenFailureToInsight:
        def guide_next_hypothesis(self, domain=None):
            raise RuntimeError("db offline")

    class BrokenGuardian:
        def evaluate_confidence(self, domain, query=""):
            raise RuntimeError("guardian offline")

    class BrokenIntent:
        def summarize_event_intent(self, event, action=None):
            raise RuntimeError("intent offline")

    event, action = _event_and_action()
    result = evaluate_faculties_for_event(
        event,
        action,
        adapters={
            "failure_to_insight": BrokenFailureToInsight(),
            "guardian": BrokenGuardian(),
            "intentkeeper": BrokenIntent(),
        },
    )

    assert result["failure_insight"]["status"] == "unavailable"
    assert "RuntimeError" in result["failure_insight"]["hypothesis"]
    assert result["guardian"]["verdict"] == "unavailable"
    assert "RuntimeError" in result["guardian"]["reason"]
    assert result["intent"]["status"] == "unavailable"


def test_faculty_bridge_keeps_actions_non_applying():
    from etzchaim.metacognition.actions import synthesize_actions

    event, _action = _event_and_action()

    actions = synthesize_actions([event])

    assert actions
    assert all(action.applies_patch is False for action in actions)
