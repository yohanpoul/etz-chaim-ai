"""Tests for ``etzchaim._internal.rectifiers.r02``.

Covers the contract documented in ``specs/04_rectifiers/02.md``:

* detection threshold (positive + negative)
* the archive action under ``act`` mode
* idempotency on a second pass
* the 25% cap on archived entries
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
from etzchaim._internal.rectifiers.r02 import (
    DAY,
    MemoryBloatRectifier,
)

NOW = 1_700_000_000.0


def _make_rectifier(
    *,
    total_entries_trigger: int = 10,
    bloat_ratio_trigger: float = 0.3,
    archive_cap_ratio: float = 0.25,
) -> MemoryBloatRectifier:
    return MemoryBloatRectifier(
        total_entries_trigger=total_entries_trigger,
        bloat_ratio_trigger=bloat_ratio_trigger,
        archive_cap_ratio=archive_cap_ratio,
        now_fn=lambda: NOW,
    )


def _entry(
    *,
    confidence: float,
    access_count: int,
    age_days: float,
    status: str = "active",
) -> dict:
    return {
        "content": "x",
        "confidence": confidence,
        "access_count": access_count,
        "created_at": NOW - age_days * DAY,
        "status": status,
    }


def _build_tree(
    *,
    total: int,
    bloat: int,
    bloat_age_days: float = 45.0,
    healthy_confidence: float = 0.8,
    healthy_access_count: int = 5,
) -> dict:
    entries = {}
    for i in range(bloat):
        entries[f"bloat-{i}"] = _entry(
            confidence=0.1, access_count=0, age_days=bloat_age_days
        )
    for i in range(total - bloat):
        entries[f"ok-{i}"] = _entry(
            confidence=healthy_confidence,
            access_count=healthy_access_count,
            age_days=10.0,
        )
    return {"memory_entries": entries}


def test_subclasses_base_rectifier() -> None:
    assert issubclass(MemoryBloatRectifier, BaseRectifier)
    rect = _make_rectifier()
    assert rect.rectifier_id == "r02"
    assert rect.spec_ref == "SPEC-RECT-002"


def test_detect_bloat_above_threshold_triggers() -> None:
    tree = _build_tree(total=20, bloat=10)
    deviations = _make_rectifier().detect(tree)
    assert len(deviations) == 1
    deviation = deviations[0]
    assert isinstance(deviation, Deviation)
    assert deviation.pattern == "memory_bloat"
    assert deviation.metrics["total_entries"] == 20
    assert deviation.metrics["low_confidence_low_access"] == 10
    assert deviation.metrics["ratio"] == pytest.approx(0.5)
    candidates = deviation.payload["prune_candidates"]
    assert len(candidates) == 10
    assert all(c.startswith("bloat-") for c in candidates)


def test_detect_total_below_threshold_no_deviation() -> None:
    rect = _make_rectifier(total_entries_trigger=100)
    tree = _build_tree(total=20, bloat=10)
    assert rect.detect(tree) == []


def test_detect_ratio_below_threshold_no_deviation() -> None:
    # 1 bloat entry out of 20 total → ratio 0.05 < 0.3 trigger.
    tree = _build_tree(total=20, bloat=1)
    assert _make_rectifier().detect(tree) == []


def test_detect_recent_entries_excluded() -> None:
    # Bloat entries newer than 30 days should not count.
    tree = _build_tree(total=20, bloat=10, bloat_age_days=5.0)
    assert _make_rectifier().detect(tree) == []


def test_detect_high_access_excluded() -> None:
    tree = _build_tree(total=20, bloat=0)
    # Inject 10 entries that are old + low confidence but high access.
    for i in range(10):
        tree["memory_entries"][f"used-{i}"] = _entry(
            confidence=0.1, access_count=5, age_days=45.0
        )
    assert _make_rectifier().detect(tree) == []


def test_detect_skips_already_archived() -> None:
    tree = _build_tree(total=20, bloat=10)
    for i in range(10):
        tree["memory_entries"][f"bloat-{i}"]["status"] = "archived"
    # Only 10 active entries remain (all healthy) — no deviation.
    assert _make_rectifier().detect(tree) == []


def test_detect_returns_empty_when_store_empty() -> None:
    assert _make_rectifier().detect({"memory_entries": {}}) == []


def test_observe_mode_logs_only() -> None:
    tree = _build_tree(total=20, bloat=10)
    rect = _make_rectifier()
    deviations = rect.detect(tree)
    snapshot = copy.deepcopy(tree)
    events = rect.rectify(deviations, RectificationMode.OBSERVE)
    assert len(events) == 1
    assert events[0].event_type == "deviation_observed"
    assert events[0].undo is None
    assert tree == snapshot


def test_suggest_mode_emits_proposed_event_with_capped_candidates() -> None:
    tree = _build_tree(total=20, bloat=10)
    rect = _make_rectifier()
    deviations = rect.detect(tree)
    snapshot = copy.deepcopy(tree)
    events = rect.rectify(deviations, RectificationMode.SUGGEST)
    assert len(events) == 1
    event = events[0]
    assert event.event_type == "r02_action_proposed"
    assert event.action == "archive_low_value"
    # Cap = floor(0.25 * 20) = 5.
    assert len(event.details["prune_candidates"]) == 5
    assert tree == snapshot


def test_act_archives_only_matching_entries() -> None:
    tree = _build_tree(total=20, bloat=10)
    rect = _make_rectifier()
    deviations = rect.detect(tree)
    events = rect.rectify(deviations, RectificationMode.ACT, tree=tree)
    assert len(events) == 1
    event = events[0]
    assert event.action == "archive_low_value"
    assert event.event_type == "r02_action_applied"
    archived_ids = event.details["archived"]
    # Cap floor(0.25 * 20) = 5.
    assert len(archived_ids) == 5
    for eid in archived_ids:
        assert eid.startswith("bloat-")
        assert tree["memory_entries"][eid]["status"] == "archived"
    # Healthy entries untouched.
    for i in range(10):
        assert tree["memory_entries"][f"ok-{i}"]["status"] == "active"


def test_act_cap_25_percent_enforced() -> None:
    # 100 entries, 80 bloat. Cap = floor(0.25 * 100) = 25.
    tree = _build_tree(total=100, bloat=80)
    rect = _make_rectifier(total_entries_trigger=10)
    deviations = rect.detect(tree)
    events = rect.rectify(deviations, RectificationMode.ACT, tree=tree)
    archived_ids = events[0].details["archived"]
    assert len(archived_ids) == 25


def test_act_never_deletes_memory_entries() -> None:
    tree = _build_tree(total=20, bloat=10)
    initial_keys = set(tree["memory_entries"])
    rect = _make_rectifier()
    rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    assert set(tree["memory_entries"]) == initial_keys


def test_act_is_idempotent() -> None:
    tree = _build_tree(total=20, bloat=10)
    rect = _make_rectifier()
    deviations = rect.detect(tree)

    first = rect.rectify(deviations, RectificationMode.ACT, tree=tree)
    assert first[0].event_type == "r02_action_applied"
    snapshot = copy.deepcopy(tree)

    # Re-applying the same deviation must not archive anything new.
    second = rect.rectify(deviations, RectificationMode.ACT, tree=tree)
    assert second[0].event_type == "r02_action_skipped"
    assert tree == snapshot


def test_act_priority_orders_lowest_confidence_first() -> None:
    tree = {
        "memory_entries": {
            **{
                f"bloat-{i}": _entry(
                    confidence=0.05 + 0.001 * i,
                    access_count=0,
                    age_days=45.0,
                )
                for i in range(10)
            },
            **{
                f"ok-{i}": _entry(
                    confidence=0.9, access_count=5, age_days=10.0
                )
                for i in range(10)
            },
        }
    }
    rect = _make_rectifier()
    events = rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    archived = events[0].details["archived"]
    # Confidences ascend with index → ids 0..4 archived first.
    assert archived == [f"bloat-{i}" for i in range(5)]


def test_undo_restores_archived_entries() -> None:
    tree = _build_tree(total=20, bloat=10)
    rect = _make_rectifier()
    events = rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    archived_ids = list(events[0].details["archived"])
    assert all(
        tree["memory_entries"][eid]["status"] == "archived"
        for eid in archived_ids
    )
    rect.apply_undo(events[0].undo, tree)
    for eid in archived_ids:
        assert tree["memory_entries"][eid]["status"] == "active"


def test_undo_rejects_unknown_kind() -> None:
    rect = _make_rectifier()
    with pytest.raises(ValueError):
        rect.apply_undo({"kind": "bogus"}, {"memory_entries": {}})


def test_rectify_rejects_unknown_mode() -> None:
    rect = _make_rectifier()
    with pytest.raises(ValueError):
        rect.rectify([], "bogus")


def test_act_mode_requires_tree() -> None:
    tree = _build_tree(total=20, bloat=10)
    rect = _make_rectifier()
    deviations = rect.detect(tree)
    with pytest.raises(ValueError):
        rect.rectify(deviations, RectificationMode.ACT, tree=None)


def test_invalid_archive_cap_ratio_rejected() -> None:
    with pytest.raises(ValueError):
        MemoryBloatRectifier(archive_cap_ratio=0.0)
    with pytest.raises(ValueError):
        MemoryBloatRectifier(archive_cap_ratio=1.5)


def test_event_dataclass_default_undo_is_none() -> None:
    e = Event(rectifier_id="r02", event_type="deviation_observed")
    assert e.undo is None
    assert e.action is None
    assert e.details == {}
