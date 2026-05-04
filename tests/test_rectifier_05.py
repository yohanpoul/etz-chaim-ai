"""Tests for ``etzchaim._internal.rectifiers.r05``.

Covers the contract documented in ``specs/04_rectifiers/05.md``:

* detection threshold (positive + negative)
* the ``park_ticket`` and ``request_synthesis`` action branches
* idempotency on a second pass
* never auto-resolves a tension (status only flips to parked, never closed)
* undo recipe correctness for both action branches
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
from etzchaim._internal.rectifiers.r05 import (
    DEFAULT_FREEZE_DAYS,
    DEFAULT_PARK_DAYS,
    PARK_REASON_INSUFFICIENT,
    PARKED_STATUS,
    TensionFreezeRectifier,
)

NOW = 1_700_000_000.0
SECONDS_PER_DAY = 86_400.0


def _make_rectifier(
    *,
    freeze_days: float = DEFAULT_FREEZE_DAYS,
    park_days: float = DEFAULT_PARK_DAYS,
) -> TensionFreezeRectifier:
    return TensionFreezeRectifier(
        freeze_days=freeze_days,
        park_days=park_days,
        now_fn=lambda: NOW,
    )


def _ticket(
    age_days: float,
    *,
    status: str = "open",
    evidence: list | None = None,
    synthesis_attempts: int = 0,
) -> dict:
    return {
        "status": status,
        "opened_at": NOW - age_days * SECONDS_PER_DAY,
        "last_progress_at": NOW - age_days * SECONDS_PER_DAY,
        "evidence": evidence or [],
        "synthesis_attempts": synthesis_attempts,
    }


def _tree(tensions: dict) -> dict:
    return {"tensions": dict(tensions)}


def test_subclasses_base_rectifier() -> None:
    assert issubclass(TensionFreezeRectifier, BaseRectifier)
    rect = _make_rectifier()
    assert rect.rectifier_id == "r05"
    assert rect.spec_ref == "SPEC-RECT-005"
    assert rect.freeze_days == pytest.approx(DEFAULT_FREEZE_DAYS)
    assert rect.park_days == pytest.approx(DEFAULT_PARK_DAYS)


def test_detect_returns_empty_with_no_tensions() -> None:
    rect = _make_rectifier()
    assert rect.detect({"tensions": {}}) == []
    assert rect.detect({}) == []


def test_detect_ignores_active_tickets_under_threshold() -> None:
    tree = _tree({"t1": _ticket(age_days=3.0)})
    assert _make_rectifier().detect(tree) == []


def test_detect_flags_frozen_ticket() -> None:
    tree = _tree(
        {
            "fresh": _ticket(age_days=2.0),
            "stale": _ticket(age_days=10.0),
        }
    )
    deviations = _make_rectifier().detect(tree)
    assert len(deviations) == 1
    deviation = deviations[0]
    assert isinstance(deviation, Deviation)
    assert deviation.pattern == "tension_freeze"
    assert deviation.metrics["open_tickets"] == 2
    assert deviation.metrics["frozen_over_7d"] == 1
    assert deviation.metrics["oldest_age_days"] == pytest.approx(10.0)
    assert deviation.metrics["frozen_ticket_ids"] == ["stale"]
    assert deviation.payload["frozen"][0]["id"] == "stale"


def test_detect_skips_non_open_tickets() -> None:
    tree = _tree({"closed": _ticket(age_days=30.0, status="closed")})
    assert _make_rectifier().detect(tree) == []


def test_detect_orders_outliers_by_age_descending() -> None:
    tree = _tree(
        {
            "young": _ticket(age_days=8.0),
            "old": _ticket(age_days=20.0),
            "mid": _ticket(age_days=12.0),
        }
    )
    deviation = _make_rectifier().detect(tree)[0]
    assert deviation.metrics["frozen_ticket_ids"] == ["old", "mid", "young"]


def test_invalid_thresholds_rejected() -> None:
    with pytest.raises(ValueError):
        TensionFreezeRectifier(freeze_days=-1.0)
    with pytest.raises(ValueError):
        TensionFreezeRectifier(freeze_days=10.0, park_days=5.0)


def test_observe_mode_logs_only() -> None:
    tree = _tree({"t1": _ticket(age_days=20.0)})
    rect = _make_rectifier()
    deviations = rect.detect(tree)
    snapshot = copy.deepcopy(tree)
    events = rect.rectify(deviations, RectificationMode.OBSERVE)
    assert len(events) == 1
    assert events[0].event_type == "deviation_observed"
    assert events[0].undo is None
    assert tree == snapshot


def test_suggest_mode_emits_proposed_event() -> None:
    tree = _tree({"t1": _ticket(age_days=20.0)})
    rect = _make_rectifier()
    deviations = rect.detect(tree)
    snapshot = copy.deepcopy(tree)
    events = rect.rectify(deviations, RectificationMode.SUGGEST)
    assert len(events) == 1
    event = events[0]
    assert event.event_type == "r05_action_proposed"
    assert event.action == "force_advance"
    assert event.details["frozen_ticket_ids"] == ["t1"]
    assert tree == snapshot


def test_act_parks_ticket_with_no_evidence() -> None:
    tree = _tree({"t1": _ticket(age_days=20.0, evidence=[])})
    rect = _make_rectifier()
    events = rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    assert len(events) == 1
    event = events[0]
    assert event.event_type == "r05_action_applied"
    assert event.action == "park_ticket"
    assert event.details["ticket_id"] == "t1"
    assert event.details["reason"] == PARK_REASON_INSUFFICIENT
    assert tree["tensions"]["t1"]["status"] == PARKED_STATUS
    assert tree["tensions"]["t1"]["park_reason"] == PARK_REASON_INSUFFICIENT


def test_act_requests_synthesis_when_evidence_present() -> None:
    tree = _tree(
        {
            "t1": _ticket(
                age_days=20.0, evidence=[{"src": "a"}], synthesis_attempts=0
            )
        }
    )
    rect = _make_rectifier()
    events = rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    assert len(events) == 1
    event = events[0]
    assert event.event_type == "r05_action_applied"
    assert event.action == "request_synthesis"
    assert event.details["ticket_id"] == "t1"
    requests = tree["synthesis_requests"]
    assert len(requests) == 1
    assert requests[0]["tension_id"] == "t1"
    assert requests[0]["id"] == event.details["request_id"]
    assert tree["tensions"]["t1"]["status"] == "open"


def test_act_skips_when_synthesis_already_attempted() -> None:
    tree = _tree(
        {
            "t1": _ticket(
                age_days=20.0,
                evidence=[{"src": "a"}],
                synthesis_attempts=1,
            )
        }
    )
    rect = _make_rectifier()
    events = rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    assert len(events) == 1
    assert events[0].event_type == "r05_action_skipped"
    assert events[0].details["reason"] == "synthesis_already_attempted"


def test_act_does_not_act_below_park_threshold() -> None:
    tree = _tree({"t1": _ticket(age_days=10.0, evidence=[])})
    rect = _make_rectifier()
    snapshot = copy.deepcopy(tree)
    events = rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    assert events == []
    assert tree == snapshot


def test_act_never_resolves_a_tension() -> None:
    tree = _tree(
        {
            "no_evidence": _ticket(age_days=20.0, evidence=[]),
            "with_evidence": _ticket(age_days=20.0, evidence=[{"src": "a"}]),
        }
    )
    initial_keys = set(tree["tensions"])
    rect = _make_rectifier()
    rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    assert set(tree["tensions"]) == initial_keys
    statuses = {tid: t.get("status") for tid, t in tree["tensions"].items()}
    assert statuses["no_evidence"] == PARKED_STATUS
    assert statuses["with_evidence"] == "open"
    assert "closed" not in statuses.values()
    assert "resolved" not in statuses.values()


def test_act_idempotent_on_already_parked() -> None:
    tree = _tree({"t1": _ticket(age_days=20.0, evidence=[])})
    rect = _make_rectifier()
    first = rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    assert first[0].event_type == "r05_action_applied"
    snapshot = copy.deepcopy(tree)
    assert rect.detect(tree) == []
    stale = Deviation(
        rectifier_id="r05",
        pattern="tension_freeze",
        metrics={},
        spec_ref="SPEC-RECT-005",
        payload={
            "frozen": [
                {
                    "id": "t1",
                    "age_days": 21.0,
                    "has_evidence": False,
                    "has_synthesis_attempt": False,
                }
            ]
        },
    )
    second = rect.rectify([stale], RectificationMode.ACT, tree=tree)
    assert len(second) == 1
    assert second[0].event_type == "r05_action_skipped"
    assert second[0].details["reason"] == "not_open"
    assert tree == snapshot


def test_undo_park_restores_ticket_status() -> None:
    tree = _tree({"t1": _ticket(age_days=20.0, evidence=[])})
    rect = _make_rectifier()
    events = rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    assert tree["tensions"]["t1"]["status"] == PARKED_STATUS
    rect.apply_undo(events[0].undo, tree)
    assert tree["tensions"]["t1"]["status"] == "open"
    assert "park_reason" not in tree["tensions"]["t1"]
    assert "parked_at" not in tree["tensions"]["t1"]


def test_undo_synthesis_drops_request() -> None:
    tree = _tree(
        {"t1": _ticket(age_days=20.0, evidence=[{"src": "a"}])}
    )
    rect = _make_rectifier()
    events = rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    assert len(tree["synthesis_requests"]) == 1
    rect.apply_undo(events[0].undo, tree)
    assert tree["synthesis_requests"] == []
    assert tree["tensions"]["t1"]["status"] == "open"


def test_parked_ticket_remains_queryable_and_reopenable() -> None:
    tree = _tree({"t1": _ticket(age_days=20.0, evidence=[])})
    rect = _make_rectifier()
    rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    parked = tree["tensions"]["t1"]
    assert parked["status"] == PARKED_STATUS
    assert "opened_at" in parked
    parked["status"] = "open"
    parked.pop("park_reason", None)
    assert tree["tensions"]["t1"]["status"] == "open"
    assert tree["tensions"]["t1"]["opened_at"] is not None


def test_undo_rejects_unknown_kind() -> None:
    rect = _make_rectifier()
    with pytest.raises(ValueError):
        rect.apply_undo({"kind": "bogus"}, {"tensions": {}})


def test_rectify_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError):
        _make_rectifier().rectify([], "bogus")


def test_act_mode_requires_tree() -> None:
    tree = _tree({"t1": _ticket(age_days=20.0)})
    rect = _make_rectifier()
    deviations = rect.detect(tree)
    with pytest.raises(ValueError):
        rect.rectify(deviations, RectificationMode.ACT, tree=None)


def test_event_dataclass_default_undo_is_none() -> None:
    e = Event(rectifier_id="r05", event_type="deviation_observed")
    assert e.undo is None
    assert e.action is None
    assert e.details == {}
