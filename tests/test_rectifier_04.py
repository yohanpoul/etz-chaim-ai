"""Tests for ``etzchaim._internal.rectifiers.r04``.

Covers the contract documented in ``specs/04_rectifiers/04.md``:

* detection threshold (positive + negative)
* the ``park_outlier`` action under ``act`` mode
* idempotency on a second pass
* mission-text change clears stale parking flags
* configurable threshold per project
* undo recipe correctness
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
from etzchaim._internal.rectifiers.r04 import (
    DEFAULT_DRIFT_THRESHOLD,
    PARKED_STATUS,
    GoalDriftRectifier,
)

NOW = 1_700_000_000.0
MISSION = "evolve cognitive operating system for llm agents"


def _embed_factory():
    """Embedding stub: word bag, but with overrides per text snippet."""
    overrides: dict[str, dict[str, float]] = {}

    def embed(text: str):
        if text in overrides:
            return overrides[text]
        from collections import Counter

        return Counter(text.lower().split())

    embed.overrides = overrides  # type: ignore[attr-defined]
    return embed


def _make_rectifier(
    *,
    embed_fn=None,
    threshold: float = DEFAULT_DRIFT_THRESHOLD,
) -> GoalDriftRectifier:
    return GoalDriftRectifier(
        embed_fn=embed_fn,
        threshold=threshold,
        now_fn=lambda: NOW,
    )


def _intention(text: str, *, status: str = "active", aligned_hash=None) -> dict:
    intent: dict = {"text": text, "status": status}
    if aligned_hash is not None:
        intent["aligned_to_mission_hash"] = aligned_hash
    return intent


def _tree(intentions: dict, *, mission: str = MISSION) -> dict:
    return {"mission_text": mission, "intentions": dict(intentions)}


def test_subclasses_base_rectifier() -> None:
    assert issubclass(GoalDriftRectifier, BaseRectifier)
    rect = _make_rectifier()
    assert rect.rectifier_id == "r04"
    assert rect.spec_ref == "SPEC-RECT-004"
    assert rect.threshold == pytest.approx(DEFAULT_DRIFT_THRESHOLD)


def test_detect_returns_empty_when_intentions_aligned() -> None:
    embed = _embed_factory()
    embed.overrides[MISSION] = {"a": 1.0, "b": 1.0}
    embed.overrides["i1"] = {"a": 1.0, "b": 1.0}
    embed.overrides["i2"] = {"a": 1.0, "b": 0.9}
    tree = _tree({"i1": _intention("i1"), "i2": _intention("i2")})
    rect = _make_rectifier(embed_fn=embed)
    assert rect.detect(tree) == []


def test_detect_flags_high_distance_intention() -> None:
    embed = _embed_factory()
    embed.overrides[MISSION] = {"a": 1.0, "b": 1.0}
    embed.overrides["aligned"] = {"a": 1.0, "b": 1.0}
    embed.overrides["drifted"] = {"x": 1.0, "y": 1.0}
    tree = _tree(
        {
            "k": _intention("aligned"),
            "drift": _intention("drifted"),
        }
    )
    deviations = _make_rectifier(embed_fn=embed).detect(tree)
    assert len(deviations) == 1
    deviation = deviations[0]
    assert isinstance(deviation, Deviation)
    assert deviation.pattern == "goal_drift"
    assert deviation.metrics["outlier_intentions"] == ["drift"]
    assert deviation.metrics["active_intentions"] == 2
    assert deviation.metrics["threshold"] == pytest.approx(DEFAULT_DRIFT_THRESHOLD)
    assert 0.0 < deviation.metrics["avg_distance_to_mission"] <= 1.0
    assert deviation.payload["outliers"][0]["id"] == "drift"


def test_detect_returns_empty_with_no_intentions() -> None:
    rect = _make_rectifier()
    assert rect.detect({"mission_text": MISSION, "intentions": {}}) == []


def test_detect_returns_empty_with_no_mission() -> None:
    rect = _make_rectifier()
    tree = {"mission_text": "", "intentions": {"i1": _intention("anything")}}
    assert rect.detect(tree) == []


def test_threshold_override_changes_outliers() -> None:
    embed = _embed_factory()
    embed.overrides[MISSION] = {"a": 1.0}
    embed.overrides["near"] = {"a": 1.0, "b": 0.4}
    tree = _tree({"i1": _intention("near")})

    strict = _make_rectifier(embed_fn=embed, threshold=0.05)
    assert len(strict.detect(tree)) == 1

    permissive = _make_rectifier(embed_fn=embed, threshold=0.5)
    assert permissive.detect(tree) == []


def test_observe_mode_logs_only() -> None:
    embed = _embed_factory()
    embed.overrides[MISSION] = {"a": 1.0}
    embed.overrides["drift"] = {"x": 1.0}
    tree = _tree({"i1": _intention("drift")})
    rect = _make_rectifier(embed_fn=embed)
    deviations = rect.detect(tree)
    snapshot = copy.deepcopy(tree)
    events = rect.rectify(deviations, RectificationMode.OBSERVE)
    assert len(events) == 1
    assert events[0].event_type == "deviation_observed"
    assert events[0].undo is None
    assert tree == snapshot


def test_suggest_mode_emits_proposed_event() -> None:
    embed = _embed_factory()
    embed.overrides[MISSION] = {"a": 1.0}
    embed.overrides["drift"] = {"x": 1.0}
    tree = _tree({"i1": _intention("drift")})
    rect = _make_rectifier(embed_fn=embed)
    deviations = rect.detect(tree)
    snapshot = copy.deepcopy(tree)
    events = rect.rectify(deviations, RectificationMode.SUGGEST)
    assert len(events) == 1
    event = events[0]
    assert event.event_type == "r04_action_proposed"
    assert event.action == "park_outliers"
    assert event.details["outlier_intentions"] == ["i1"]
    assert event.details["threshold"] == pytest.approx(DEFAULT_DRIFT_THRESHOLD)
    assert tree == snapshot


def test_act_parks_outlier_and_emits_tension_request() -> None:
    embed = _embed_factory()
    embed.overrides[MISSION] = {"a": 1.0}
    embed.overrides["aligned"] = {"a": 1.0}
    embed.overrides["drift"] = {"x": 1.0}
    tree = _tree(
        {
            "ok": _intention("aligned"),
            "bad": _intention("drift"),
        }
    )
    rect = _make_rectifier(embed_fn=embed)
    events = rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    assert len(events) == 1
    event = events[0]
    assert event.event_type == "r04_action_applied"
    assert event.action == "park_outlier"
    assert event.details["intention_id"] == "bad"
    assert tree["intentions"]["bad"]["status"] == PARKED_STATUS
    assert tree["intentions"]["ok"]["status"] == "active"
    requests = tree["tension_requests"]
    assert len(requests) == 1
    assert requests[0]["intention_id"] == "bad"
    assert requests[0]["kind"] == "alignment_review"
    assert requests[0]["id"] == event.details["request_id"]


def test_act_never_deletes_intentions() -> None:
    embed = _embed_factory()
    embed.overrides[MISSION] = {"a": 1.0}
    embed.overrides["drift"] = {"x": 1.0}
    tree = _tree({"i1": _intention("drift"), "i2": _intention("drift")})
    initial_keys = set(tree["intentions"])
    rect = _make_rectifier(embed_fn=embed)
    rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    assert set(tree["intentions"]) == initial_keys
    for intention in tree["intentions"].values():
        assert intention["text"] == "drift"


def test_act_idempotent_on_already_parked() -> None:
    embed = _embed_factory()
    embed.overrides[MISSION] = {"a": 1.0}
    embed.overrides["drift"] = {"x": 1.0}
    tree = _tree({"i1": _intention("drift")})
    rect = _make_rectifier(embed_fn=embed)

    first = rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    assert first[0].event_type == "r04_action_applied"
    snapshot = copy.deepcopy(tree)

    # Detection should now exclude the parked intention under same mission hash.
    assert rect.detect(tree) == []

    # Even if a stale deviation is replayed, act mode reports it as skipped.
    stale = Deviation(
        rectifier_id="r04",
        pattern="goal_drift",
        metrics={},
        spec_ref="SPEC-RECT-004",
        payload={
            "outliers": [{"id": "i1", "distance": 0.99}],
            "mission_hash": first[0].undo["prior_aligned_hash"]
            or tree["intentions"]["i1"]["aligned_to_mission_hash"],
        },
    )
    second = rect.rectify([stale], RectificationMode.ACT, tree=tree)
    assert second[0].event_type == "r04_action_skipped"
    assert tree == snapshot


def test_mission_change_clears_parking_flags() -> None:
    embed = _embed_factory()
    embed.overrides[MISSION] = {"a": 1.0}
    embed.overrides["drift"] = {"x": 1.0}
    tree = _tree({"i1": _intention("drift")})
    rect = _make_rectifier(embed_fn=embed)
    rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    assert tree["intentions"]["i1"]["status"] == PARKED_STATUS

    # Mission text changes — operator invokes the baseline reset.
    tree["mission_text"] = "new mission orientation"
    cleared = rect.apply_mission_change(tree)
    assert cleared == 1
    assert tree["intentions"]["i1"]["status"] == "active"
    assert "aligned_to_mission_hash" not in tree["intentions"]["i1"]


def test_mission_change_keeps_flags_under_same_hash() -> None:
    embed = _embed_factory()
    embed.overrides[MISSION] = {"a": 1.0}
    embed.overrides["drift"] = {"x": 1.0}
    tree = _tree({"i1": _intention("drift")})
    rect = _make_rectifier(embed_fn=embed)
    rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    assert rect.apply_mission_change(tree) == 0
    assert tree["intentions"]["i1"]["status"] == PARKED_STATUS


def test_undo_restores_status_and_drops_request() -> None:
    embed = _embed_factory()
    embed.overrides[MISSION] = {"a": 1.0}
    embed.overrides["drift"] = {"x": 1.0}
    tree = _tree({"i1": _intention("drift")})
    rect = _make_rectifier(embed_fn=embed)
    events = rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    assert tree["intentions"]["i1"]["status"] == PARKED_STATUS
    assert len(tree["tension_requests"]) == 1

    rect.apply_undo(events[0].undo, tree)
    assert tree["intentions"]["i1"]["status"] == "active"
    assert "aligned_to_mission_hash" not in tree["intentions"]["i1"]
    assert tree["tension_requests"] == []


def test_undo_rejects_unknown_kind() -> None:
    rect = _make_rectifier()
    with pytest.raises(ValueError):
        rect.apply_undo({"kind": "bogus"}, {"intentions": {}})


def test_rectify_rejects_unknown_mode() -> None:
    rect = _make_rectifier()
    with pytest.raises(ValueError):
        rect.rectify([], "bogus")


def test_act_mode_requires_tree() -> None:
    embed = _embed_factory()
    embed.overrides[MISSION] = {"a": 1.0}
    embed.overrides["drift"] = {"x": 1.0}
    tree = _tree({"i1": _intention("drift")})
    rect = _make_rectifier(embed_fn=embed)
    deviations = rect.detect(tree)
    with pytest.raises(ValueError):
        rect.rectify(deviations, RectificationMode.ACT, tree=None)


def test_invalid_threshold_rejected() -> None:
    with pytest.raises(ValueError):
        GoalDriftRectifier(threshold=-0.1)
    with pytest.raises(ValueError):
        GoalDriftRectifier(threshold=1.5)


def test_default_embed_distinguishes_overlap() -> None:
    rect = GoalDriftRectifier(threshold=0.4, now_fn=lambda: NOW)
    tree = {
        "mission_text": "alpha beta gamma delta",
        "intentions": {
            "near": {"text": "alpha beta gamma"},
            "far": {"text": "zeta theta iota kappa"},
        },
    }
    deviations = rect.detect(tree)
    assert len(deviations) == 1
    assert deviations[0].metrics["outlier_intentions"] == ["far"]


def test_event_dataclass_default_undo_is_none() -> None:
    e = Event(rectifier_id="r04", event_type="deviation_observed")
    assert e.undo is None
    assert e.action is None
    assert e.details == {}
