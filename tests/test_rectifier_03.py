"""Tests for ``etzchaim._internal.rectifiers.r03``.

Covers the contract documented in ``specs/04_rectifiers/03.md``:

* detection threshold (positive + negative)
* the two action branches under ``act`` mode (ground, quarantine)
* bounded retry budget
* idempotency on a second pass
* undo recipe correctness for each branch
* reversibility of the quarantine flag
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
from etzchaim._internal.rectifiers.r03 import (
    DAY,
    InsightGroundingRectifier,
)

NOW = 1_700_000_000.0


def _make_rectifier(
    *,
    seek_provenance=None,
    ungrounded_count_trigger: int = 1,
    max_attempts: int = 3,
    window_seconds: float = DAY,
) -> InsightGroundingRectifier:
    return InsightGroundingRectifier(
        seek_provenance=seek_provenance,
        ungrounded_count_trigger=ungrounded_count_trigger,
        max_attempts=max_attempts,
        window_seconds=window_seconds,
        now_fn=lambda: NOW,
    )


def _insight(
    *,
    sources=None,
    age_hours: float = 1.0,
    status: str = "active",
) -> dict:
    return {
        "content": "x",
        "sources": list(sources) if sources is not None else None,
        "created_at": NOW - age_hours * 3600.0,
        "status": status,
    }


def _build_tree(*, ungrounded: int, grounded: int, age_hours: float = 1.0) -> dict:
    insights: dict = {}
    for i in range(ungrounded):
        insights[f"u-{i}"] = _insight(sources=None, age_hours=age_hours)
    for i in range(grounded):
        insights[f"g-{i}"] = _insight(
            sources=[f"corpus://ref/{i}"], age_hours=age_hours
        )
    return {"insights": insights}


def test_subclasses_base_rectifier() -> None:
    assert issubclass(InsightGroundingRectifier, BaseRectifier)
    rect = _make_rectifier()
    assert rect.rectifier_id == "r03"
    assert rect.spec_ref == "SPEC-RECT-003"


def test_detect_ungrounded_insight_triggers() -> None:
    tree = _build_tree(ungrounded=2, grounded=3)
    deviations = _make_rectifier().detect(tree)
    assert len(deviations) == 1
    deviation = deviations[0]
    assert isinstance(deviation, Deviation)
    assert deviation.pattern == "ungrounded_insight"
    assert deviation.metrics["ungrounded_count_24h"] == 2
    assert deviation.metrics["ratio_ungrounded"] == pytest.approx(0.4)
    ids = deviation.payload["ungrounded_ids"]
    assert sorted(ids) == ["u-0", "u-1"]


def test_detect_insight_with_provenance_no_deviation() -> None:
    tree = _build_tree(ungrounded=0, grounded=5)
    assert _make_rectifier().detect(tree) == []


def test_detect_empty_sources_list_is_ungrounded() -> None:
    tree = {"insights": {"i1": _insight(sources=[], age_hours=1.0)}}
    deviations = _make_rectifier().detect(tree)
    assert len(deviations) == 1
    assert deviations[0].payload["ungrounded_ids"] == ["i1"]


def test_detect_outside_window_excluded() -> None:
    # Ungrounded insight is older than the 24h window.
    tree = {"insights": {"i1": _insight(sources=None, age_hours=48.0)}}
    assert _make_rectifier().detect(tree) == []


def test_detect_quarantined_insight_excluded() -> None:
    tree = {
        "insights": {
            "i1": _insight(sources=None, age_hours=1.0, status="quarantined"),
        }
    }
    assert _make_rectifier().detect(tree) == []


def test_detect_below_count_trigger_no_deviation() -> None:
    rect = _make_rectifier(ungrounded_count_trigger=5)
    tree = _build_tree(ungrounded=2, grounded=3)
    assert rect.detect(tree) == []


def test_detect_returns_empty_when_store_empty() -> None:
    assert _make_rectifier().detect({"insights": {}}) == []


def test_observe_mode_logs_only() -> None:
    tree = _build_tree(ungrounded=2, grounded=3)
    rect = _make_rectifier()
    deviations = rect.detect(tree)
    snapshot = copy.deepcopy(tree)
    events = rect.rectify(deviations, RectificationMode.OBSERVE)
    assert len(events) == 1
    assert events[0].event_type == "deviation_observed"
    assert events[0].undo is None
    assert tree == snapshot


def test_suggest_mode_emits_proposed_event() -> None:
    tree = _build_tree(ungrounded=2, grounded=3)
    rect = _make_rectifier()
    deviations = rect.detect(tree)
    snapshot = copy.deepcopy(tree)
    events = rect.rectify(deviations, RectificationMode.SUGGEST)
    assert len(events) == 1
    event = events[0]
    assert event.event_type == "r03_action_proposed"
    assert event.action == "seek_provenance"
    assert sorted(event.details["ungrounded_ids"]) == ["u-0", "u-1"]
    assert event.details["max_attempts"] == 3
    assert tree == snapshot


def test_act_grounds_insight_when_provenance_found() -> None:
    sources = ["corpus://ref/found"]

    def seek(insight_id: str, tree: dict) -> list[str]:
        return list(sources)

    tree = _build_tree(ungrounded=1, grounded=0)
    rect = _make_rectifier(seek_provenance=seek)
    events = rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    assert len(events) == 1
    event = events[0]
    assert event.action == "ground_insight"
    assert event.event_type == "r03_action_applied"
    assert event.details["sources"] == sources
    assert event.details["attempts"] == 1
    assert tree["insights"]["u-0"]["sources"] == sources
    assert tree["insights"]["u-0"]["status"] == "active"


def test_act_quarantines_after_three_failed_attempts() -> None:
    calls: list[str] = []

    def seek(insight_id: str, tree: dict) -> list[str]:
        calls.append(insight_id)
        return []

    tree = _build_tree(ungrounded=1, grounded=0)
    rect = _make_rectifier(seek_provenance=seek)
    events = rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    assert len(events) == 1
    event = events[0]
    assert event.action == "quarantine_insight"
    assert event.event_type == "r03_action_applied"
    assert event.details["attempts"] == 3
    assert calls == ["u-0", "u-0", "u-0"]
    assert tree["insights"]["u-0"]["status"] == "quarantined"
    # Content untouched.
    assert tree["insights"]["u-0"]["content"] == "x"


def test_act_succeeds_on_second_attempt_within_budget() -> None:
    state = {"calls": 0}

    def seek(insight_id: str, tree: dict) -> list[str]:
        state["calls"] += 1
        if state["calls"] >= 2:
            return ["corpus://late"]
        return []

    tree = _build_tree(ungrounded=1, grounded=0)
    rect = _make_rectifier(seek_provenance=seek)
    events = rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    assert events[0].action == "ground_insight"
    assert events[0].details["attempts"] == 2
    assert tree["insights"]["u-0"]["sources"] == ["corpus://late"]


def test_act_never_modifies_insight_content() -> None:
    tree = _build_tree(ungrounded=2, grounded=1)
    contents = {iid: ins["content"] for iid, ins in tree["insights"].items()}
    rect = _make_rectifier(seek_provenance=lambda iid, t: [])
    rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    for iid, content in contents.items():
        assert tree["insights"][iid]["content"] == content


def test_act_never_deletes_insights() -> None:
    tree = _build_tree(ungrounded=2, grounded=1)
    initial_keys = set(tree["insights"])
    rect = _make_rectifier(seek_provenance=lambda iid, t: [])
    rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    assert set(tree["insights"]) == initial_keys


def test_act_is_idempotent_on_quarantine() -> None:
    tree = _build_tree(ungrounded=1, grounded=0)
    rect = _make_rectifier(seek_provenance=lambda iid, t: [])
    deviations = rect.detect(tree)
    first = rect.rectify(deviations, RectificationMode.ACT, tree=tree)
    assert first[0].action == "quarantine_insight"
    snapshot = copy.deepcopy(tree)
    # Second pass on the same deviation: insight already quarantined → skipped.
    second = rect.rectify(deviations, RectificationMode.ACT, tree=tree)
    assert second[0].event_type == "r03_action_skipped"
    assert tree == snapshot


def test_act_skips_already_grounded() -> None:
    tree = {"insights": {"i1": _insight(sources=None, age_hours=1.0)}}
    rect = _make_rectifier(seek_provenance=lambda iid, t: ["corpus://x"])
    deviations = rect.detect(tree)
    # Pre-ground manually so the act pass sees existing sources.
    tree["insights"]["i1"]["sources"] = ["corpus://prior"]
    events = rect.rectify(deviations, RectificationMode.ACT, tree=tree)
    assert events[0].event_type == "r03_action_skipped"
    assert events[0].details["reason"] == "already_grounded"
    assert tree["insights"]["i1"]["sources"] == ["corpus://prior"]


def test_undo_restores_sources_after_grounding() -> None:
    tree = _build_tree(ungrounded=1, grounded=0)
    rect = _make_rectifier(seek_provenance=lambda iid, t: ["corpus://r"])
    events = rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    assert tree["insights"]["u-0"]["sources"] == ["corpus://r"]
    rect.apply_undo(events[0].undo, tree)
    assert tree["insights"]["u-0"].get("sources") in (None,)


def test_undo_restores_status_after_quarantine() -> None:
    tree = _build_tree(ungrounded=1, grounded=0)
    rect = _make_rectifier(seek_provenance=lambda iid, t: [])
    events = rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    assert tree["insights"]["u-0"]["status"] == "quarantined"
    rect.apply_undo(events[0].undo, tree)
    assert tree["insights"]["u-0"]["status"] == "active"


def test_undo_rejects_unknown_kind() -> None:
    rect = _make_rectifier()
    with pytest.raises(ValueError):
        rect.apply_undo({"kind": "bogus"}, {"insights": {}})


def test_unquarantine_lifts_quarantine_flag() -> None:
    tree = _build_tree(ungrounded=1, grounded=0)
    rect = _make_rectifier(seek_provenance=lambda iid, t: [])
    rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    assert tree["insights"]["u-0"]["status"] == "quarantined"
    assert rect.unquarantine("u-0", tree) is True
    assert tree["insights"]["u-0"]["status"] == "active"


def test_unquarantine_returns_false_for_unknown_or_active() -> None:
    rect = _make_rectifier()
    tree = {"insights": {"i1": _insight(sources=["corpus://x"], age_hours=1.0)}}
    assert rect.unquarantine("missing", tree) is False
    assert rect.unquarantine("i1", tree) is False


def test_rectify_rejects_unknown_mode() -> None:
    rect = _make_rectifier()
    with pytest.raises(ValueError):
        rect.rectify([], "bogus")


def test_act_mode_requires_tree() -> None:
    tree = _build_tree(ungrounded=1, grounded=0)
    rect = _make_rectifier(seek_provenance=lambda iid, t: [])
    deviations = rect.detect(tree)
    with pytest.raises(ValueError):
        rect.rectify(deviations, RectificationMode.ACT, tree=None)


def test_invalid_constructor_args_rejected() -> None:
    with pytest.raises(ValueError):
        InsightGroundingRectifier(max_attempts=0)
    with pytest.raises(ValueError):
        InsightGroundingRectifier(ungrounded_count_trigger=0)
    with pytest.raises(ValueError):
        InsightGroundingRectifier(window_seconds=0)


def test_default_seek_provenance_yields_quarantine() -> None:
    # No seek_provenance injected → default returns [] → quarantine path.
    tree = _build_tree(ungrounded=1, grounded=0)
    rect = _make_rectifier()
    events = rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    assert events[0].action == "quarantine_insight"


def test_event_dataclass_default_undo_is_none() -> None:
    e = Event(rectifier_id="r03", event_type="deviation_observed")
    assert e.undo is None
    assert e.action is None
    assert e.details == {}
