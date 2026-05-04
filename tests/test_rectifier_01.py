"""Tests for ``etzchaim._internal.rectifiers.r01``.

Covers the contract documented in ``specs/04_rectifiers/01.md``:

* detection threshold (positive + negative)
* each of the three action branches (elevate / park / dissensus) under ``act``
* idempotency on a second pass
* undo recipe correctness for each action type
"""
from __future__ import annotations

import copy

import pytest

from etzchaim._internal.rectifiers import (
    BaseRectifier,
    Deviation,
    Event,
    RectificationMode,
)
from etzchaim._internal.rectifiers.r01 import (
    ContradictionResolutionRectifier,
)

HOUR = 3600.0
NOW = 1_700_000_000.0


def _build_tree(*, age_hours: float, conf_a: float, conf_b: float) -> dict:
    marked_at = NOW - age_hours * HOUR
    return {
        "memory_entries": {
            "a": {"content": "X is Y", "confidence": conf_a, "status": "active"},
            "b": {"content": "X is not Y", "confidence": conf_b, "status": "active"},
        },
        "contradictions": [{"a": "a", "b": "b", "marked_at": marked_at}],
        "pending_questions": [],
        "dissensus_tickets": [],
    }


def _make_rectifier() -> ContradictionResolutionRectifier:
    return ContradictionResolutionRectifier(now_fn=lambda: NOW)


def test_subclasses_base_rectifier() -> None:
    assert issubclass(ContradictionResolutionRectifier, BaseRectifier)
    rect = _make_rectifier()
    assert rect.rectifier_id == "r01"
    assert rect.spec_ref == "SPEC-RECT-001"


def test_detect_stale_contradiction_triggers() -> None:
    tree = _build_tree(age_hours=25.0, conf_a=0.9, conf_b=0.3)
    deviations = _make_rectifier().detect(tree)
    assert len(deviations) == 1
    deviation = deviations[0]
    assert isinstance(deviation, Deviation)
    assert deviation.pattern == "stale_contradiction"
    assert deviation.metrics["stale_24h_pairs"] == 1
    assert deviation.metrics["contradicting_pairs"] == 1
    assert deviation.metrics["oldest_pair_age_hours"] == pytest.approx(25.0)
    assert deviation.payload["stale_pairs"][0]["a"] == "a"


def test_detect_fresh_contradiction_no_deviation() -> None:
    tree = _build_tree(age_hours=1.0, conf_a=0.9, conf_b=0.3)
    deviations = _make_rectifier().detect(tree)
    assert deviations == []


def test_detect_recent_investigation_resets_clock() -> None:
    tree = _build_tree(age_hours=48.0, conf_a=0.9, conf_b=0.3)
    tree["memory_entries"]["a"]["last_investigated_at"] = NOW - 1 * HOUR
    deviations = _make_rectifier().detect(tree)
    assert deviations == []


def test_detect_returns_empty_when_no_contradictions() -> None:
    tree = {"memory_entries": {}, "contradictions": []}
    assert _make_rectifier().detect(tree) == []


def test_observe_mode_logs_only() -> None:
    tree = _build_tree(age_hours=25.0, conf_a=0.9, conf_b=0.3)
    rect = _make_rectifier()
    deviations = rect.detect(tree)
    events = rect.rectify(deviations, RectificationMode.OBSERVE)
    assert len(events) == 1
    assert events[0].event_type == "deviation_observed"
    assert events[0].undo is None
    # Tree was not mutated.
    assert tree["memory_entries"]["a"]["status"] == "active"
    assert tree["memory_entries"]["b"]["status"] == "active"


def test_suggest_mode_emits_proposed_event() -> None:
    tree = _build_tree(age_hours=25.0, conf_a=0.9, conf_b=0.3)
    rect = _make_rectifier()
    deviations = rect.detect(tree)
    events = rect.rectify(deviations, RectificationMode.SUGGEST)
    assert len(events) == 1
    event = events[0]
    assert event.event_type == "r01_action_proposed"
    assert event.action == "elevate_winner"
    # Tree unchanged.
    assert tree["memory_entries"]["a"]["status"] == "active"


def test_act_elevate_winner_branch() -> None:
    tree = _build_tree(age_hours=25.0, conf_a=0.9, conf_b=0.3)
    rect = _make_rectifier()
    deviations = rect.detect(tree)
    events = rect.rectify(deviations, RectificationMode.ACT, tree=tree)
    assert len(events) == 1
    event = events[0]
    assert event.action == "elevate_winner"
    assert event.event_type == "r01_action_applied"
    assert tree["memory_entries"]["a"]["status"] == "elevated"
    assert tree["memory_entries"]["b"]["status"] == "archived"
    assert event.undo == {
        "kind": "restore_status",
        "entries": {"a": "active", "b": "active"},
    }


def test_act_park_pending_evidence_branch() -> None:
    tree = _build_tree(age_hours=25.0, conf_a=0.55, conf_b=0.5)
    rect = _make_rectifier()
    deviations = rect.detect(tree)
    events = rect.rectify(deviations, RectificationMode.ACT, tree=tree)
    assert len(events) == 1
    event = events[0]
    assert event.action == "park_pending_evidence"
    assert tree["memory_entries"]["a"]["status"] == "parked"
    assert tree["memory_entries"]["b"]["status"] == "parked"
    assert len(tree["pending_questions"]) == 1
    qid = tree["pending_questions"][0]["id"]
    assert event.undo["kind"] == "restore_status_and_drop_question"
    assert event.undo["question_id"] == qid
    assert event.undo["entries"] == {"a": "active", "b": "active"}


def test_act_open_dissensus_branch() -> None:
    tree = _build_tree(age_hours=25.0, conf_a=0.85, conf_b=0.55)
    rect = _make_rectifier()
    deviations = rect.detect(tree)
    events = rect.rectify(deviations, RectificationMode.ACT, tree=tree)
    assert len(events) == 1
    event = events[0]
    assert event.action == "open_dissensus"
    assert len(tree["dissensus_tickets"]) == 1
    tid = tree["dissensus_tickets"][0]["id"]
    assert event.undo == {"kind": "remove_dissensus_ticket", "ticket_id": tid}
    # Status flags untouched: dissensus tickets do not flip status.
    assert tree["memory_entries"]["a"]["status"] == "active"
    assert tree["memory_entries"]["b"]["status"] == "active"


def test_act_never_deletes_memory_entries() -> None:
    tree = _build_tree(age_hours=25.0, conf_a=0.9, conf_b=0.3)
    rect = _make_rectifier()
    rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    # Entry ids preserved after rectification.
    assert set(tree["memory_entries"]) == {"a", "b"}


@pytest.mark.parametrize(
    "conf_a,conf_b,expected_action",
    [
        (0.9, 0.3, "elevate_winner"),
        (0.55, 0.5, "park_pending_evidence"),
        (0.85, 0.55, "open_dissensus"),
    ],
)
def test_act_is_idempotent(
    conf_a: float, conf_b: float, expected_action: str
) -> None:
    tree = _build_tree(age_hours=25.0, conf_a=conf_a, conf_b=conf_b)
    rect = _make_rectifier()

    first_events = rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    assert first_events[0].action == expected_action
    snapshot = copy.deepcopy(tree)

    second_events = rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    if second_events:
        # When the second pass still detects (possible for dissensus since
        # status is unchanged), the action must short-circuit.
        assert second_events[0].event_type == "r01_action_skipped"
    assert tree == snapshot


def test_undo_restores_elevate_winner() -> None:
    tree = _build_tree(age_hours=25.0, conf_a=0.9, conf_b=0.3)
    rect = _make_rectifier()
    events = rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    rect.apply_undo(events[0].undo, tree)
    assert tree["memory_entries"]["a"]["status"] == "active"
    assert tree["memory_entries"]["b"]["status"] == "active"


def test_undo_restores_park_pending_evidence() -> None:
    tree = _build_tree(age_hours=25.0, conf_a=0.55, conf_b=0.5)
    rect = _make_rectifier()
    events = rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    rect.apply_undo(events[0].undo, tree)
    assert tree["memory_entries"]["a"]["status"] == "active"
    assert tree["memory_entries"]["b"]["status"] == "active"
    assert tree["pending_questions"] == []


def test_undo_removes_dissensus_ticket() -> None:
    tree = _build_tree(age_hours=25.0, conf_a=0.85, conf_b=0.55)
    rect = _make_rectifier()
    events = rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    rect.apply_undo(events[0].undo, tree)
    assert tree["dissensus_tickets"] == []


def test_rectify_rejects_unknown_mode() -> None:
    rect = _make_rectifier()
    with pytest.raises(ValueError):
        rect.rectify([], "bogus")


def test_act_mode_requires_tree() -> None:
    tree = _build_tree(age_hours=25.0, conf_a=0.9, conf_b=0.3)
    rect = _make_rectifier()
    deviations = rect.detect(tree)
    with pytest.raises(ValueError):
        rect.rectify(deviations, RectificationMode.ACT, tree=None)


def test_event_dataclass_default_undo_is_none() -> None:
    e = Event(rectifier_id="r01", event_type="deviation_observed")
    assert e.undo is None
    assert e.action is None
    assert e.details == {}
