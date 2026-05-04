"""Tests for the contradiction resolution rectifier (SPEC-RECT-001).

Covers detection thresholds, the three action branches under ``act`` mode,
idempotency on repeated apply, and undo recipe correctness.
"""
from __future__ import annotations

from copy import deepcopy

import pytest

from etzchaim.probes import (
    ContradictionResolutionRectifier,
    Event,
    RectifierMode,
)


class FakeMemory:
    """Minimal memory faculty stand-in for rectifier tests."""

    def __init__(self, entries: dict) -> None:
        self.entries = entries
        self.tickets: dict[str, dict] = {}
        self._next_ticket = 0
        self.calls: list[tuple] = []

    def get_status(self, entry_id: str) -> str:
        return str(self.entries[entry_id].get("status", "active"))

    def set_status(self, entry_id: str, status: str) -> None:
        self.calls.append(("set_status", entry_id, status))
        self.entries[entry_id]["status"] = status

    def open_dissensus_ticket(self, a_id: str, b_id: str, reason: str) -> str:
        self._next_ticket += 1
        ticket_id = f"t-{self._next_ticket}"
        self.tickets[ticket_id] = {"a": a_id, "b": b_id, "reason": reason, "open": True}
        self.calls.append(("open_dissensus_ticket", a_id, b_id, ticket_id))
        return ticket_id

    def close_dissensus_ticket(self, ticket_id: str) -> None:
        self.tickets[ticket_id]["open"] = False
        self.calls.append(("close_dissensus_ticket", ticket_id))


def _entry(
    entry_id: str,
    *,
    confidence: float,
    contradicts: list[str],
    hours: float,
    status: str = "active",
    depth: str = "shallow",
) -> dict:
    return {
        "id": entry_id,
        "confidence": confidence,
        "contradicts": contradicts,
        "last_investigated_at_hours_ago": hours,
        "status": status,
        "concept_depth": depth,
    }


def _tree(*entries: dict) -> dict:
    return {"memory": {"entries": {e["id"]: e for e in entries}}}


# ---------------------------------------------------------------------------
# Detection threshold
# ---------------------------------------------------------------------------


def test_detect_stale_pair_returns_deviation() -> None:
    tree = _tree(
        _entry("a", confidence=0.9, contradicts=["b"], hours=25.0),
        _entry("b", confidence=0.3, contradicts=["a"], hours=26.0),
    )
    rect = ContradictionResolutionRectifier(FakeMemory(tree["memory"]["entries"]))
    deviations = rect.detect(tree)
    assert len(deviations) == 1
    dev = deviations[0]
    assert dev.rectifier_id == "r01"
    assert dev.pattern == "stale_contradiction"
    assert dev.metrics["pair"] == ("a", "b")
    assert dev.spec_ref == "SPEC-RECT-001"


def test_detect_fresh_pair_returns_no_deviation() -> None:
    tree = _tree(
        _entry("a", confidence=0.9, contradicts=["b"], hours=1.0),
        _entry("b", confidence=0.3, contradicts=["a"], hours=2.0),
    )
    rect = ContradictionResolutionRectifier(FakeMemory(tree["memory"]["entries"]))
    assert rect.detect(tree) == []


def test_detect_unilateral_contradiction_ignored() -> None:
    tree = _tree(
        _entry("a", confidence=0.9, contradicts=["b"], hours=25.0),
        _entry("b", confidence=0.3, contradicts=[], hours=25.0),
    )
    rect = ContradictionResolutionRectifier(FakeMemory(tree["memory"]["entries"]))
    assert rect.detect(tree) == []


def test_detect_already_handled_status_ignored() -> None:
    tree = _tree(
        _entry(
            "a",
            confidence=0.9,
            contradicts=["b"],
            hours=25.0,
            status="parked",
        ),
        _entry(
            "b",
            confidence=0.3,
            contradicts=["a"],
            hours=25.0,
            status="parked",
        ),
    )
    rect = ContradictionResolutionRectifier(FakeMemory(tree["memory"]["entries"]))
    assert rect.detect(tree) == []


# ---------------------------------------------------------------------------
# Action branches (act mode)
# ---------------------------------------------------------------------------


def test_act_elevate_winner_branch() -> None:
    tree = _tree(
        _entry("a", confidence=0.9, contradicts=["b"], hours=25.0),
        _entry("b", confidence=0.3, contradicts=["a"], hours=25.0),
    )
    memory = FakeMemory(tree["memory"]["entries"])
    rect = ContradictionResolutionRectifier(memory)
    deviations = rect.detect(tree)
    events = rect.rectify(deviations, RectifierMode.ACT)
    assert len(events) == 1
    event = events[0]
    assert event.type == "r01_action_applied"
    assert event.payload["action"] == "elevate_winner"
    assert event.payload["params"] == {"winner_id": "a", "loser_id": "b"}
    assert memory.entries["a"]["status"] == "elevated"
    assert memory.entries["b"]["status"] == "archived"
    assert event.undo is not None
    assert event.undo.action == "elevate_winner"


def test_act_park_pending_evidence_branch() -> None:
    tree = _tree(
        _entry("a", confidence=0.55, contradicts=["b"], hours=30.0),
        _entry("b", confidence=0.5, contradicts=["a"], hours=30.0),
    )
    memory = FakeMemory(tree["memory"]["entries"])
    rect = ContradictionResolutionRectifier(memory)
    events = rect.rectify(rect.detect(tree), RectifierMode.ACT)
    assert len(events) == 1
    event = events[0]
    assert event.payload["action"] == "park_pending_evidence"
    assert memory.entries["a"]["status"] == "parked"
    assert memory.entries["b"]["status"] == "parked"
    assert event.undo is not None
    assert event.undo.action == "park_pending_evidence"


def test_act_open_dissensus_branch_via_depth() -> None:
    tree = _tree(
        _entry(
            "a", confidence=0.95, contradicts=["b"], hours=30.0, depth="deep"
        ),
        _entry(
            "b", confidence=0.1, contradicts=["a"], hours=30.0, depth="deep"
        ),
    )
    memory = FakeMemory(tree["memory"]["entries"])
    rect = ContradictionResolutionRectifier(memory)
    events = rect.rectify(rect.detect(tree), RectifierMode.ACT)
    assert len(events) == 1
    event = events[0]
    assert event.payload["action"] == "open_dissensus"
    assert memory.entries["a"]["status"] == "dissensus_open"
    assert memory.entries["b"]["status"] == "dissensus_open"
    assert len(memory.tickets) == 1
    ticket = next(iter(memory.tickets.values()))
    assert ticket["open"] is True
    assert event.undo is not None
    assert event.undo.action == "open_dissensus"


def test_act_open_dissensus_branch_via_unmatched_confidence_gap() -> None:
    tree = _tree(
        _entry("a", confidence=0.7, contradicts=["b"], hours=30.0),
        _entry("b", confidence=0.4, contradicts=["a"], hours=30.0),
    )
    memory = FakeMemory(tree["memory"]["entries"])
    rect = ContradictionResolutionRectifier(memory)
    events = rect.rectify(rect.detect(tree), RectifierMode.ACT)
    assert events[0].payload["action"] == "open_dissensus"


# ---------------------------------------------------------------------------
# Other modes
# ---------------------------------------------------------------------------


def test_observe_mode_emits_event_without_mutation() -> None:
    tree = _tree(
        _entry("a", confidence=0.9, contradicts=["b"], hours=25.0),
        _entry("b", confidence=0.3, contradicts=["a"], hours=25.0),
    )
    memory = FakeMemory(tree["memory"]["entries"])
    snapshot = deepcopy(memory.entries)
    rect = ContradictionResolutionRectifier(memory)
    events = rect.rectify(rect.detect(tree), RectifierMode.OBSERVE)
    assert events[0].type == "r01_deviation_observed"
    assert memory.entries == snapshot


def test_suggest_mode_proposes_without_mutation() -> None:
    tree = _tree(
        _entry("a", confidence=0.9, contradicts=["b"], hours=25.0),
        _entry("b", confidence=0.3, contradicts=["a"], hours=25.0),
    )
    memory = FakeMemory(tree["memory"]["entries"])
    snapshot = deepcopy(memory.entries)
    rect = ContradictionResolutionRectifier(memory)
    events = rect.rectify(rect.detect(tree), RectifierMode.SUGGEST)
    assert events[0].type == "r01_action_proposed"
    assert events[0].payload["action"] == "elevate_winner"
    assert memory.entries == snapshot


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "entries_factory,expected_action",
    [
        (
            lambda: (
                _entry("a", confidence=0.9, contradicts=["b"], hours=25.0),
                _entry("b", confidence=0.3, contradicts=["a"], hours=25.0),
            ),
            "elevate_winner",
        ),
        (
            lambda: (
                _entry("a", confidence=0.55, contradicts=["b"], hours=30.0),
                _entry("b", confidence=0.5, contradicts=["a"], hours=30.0),
            ),
            "park_pending_evidence",
        ),
        (
            lambda: (
                _entry(
                    "a",
                    confidence=0.95,
                    contradicts=["b"],
                    hours=30.0,
                    depth="deep",
                ),
                _entry(
                    "b",
                    confidence=0.1,
                    contradicts=["a"],
                    hours=30.0,
                    depth="deep",
                ),
            ),
            "open_dissensus",
        ),
    ],
)
def test_act_mode_is_idempotent(entries_factory, expected_action) -> None:
    tree = _tree(*entries_factory())
    memory = FakeMemory(tree["memory"]["entries"])
    rect = ContradictionResolutionRectifier(memory)
    deviations = rect.detect(tree)
    first = rect.rectify(deviations, RectifierMode.ACT)
    state_after_first = deepcopy(memory.entries)
    tickets_after_first = deepcopy(memory.tickets)
    rect.rectify(deviations, RectifierMode.ACT)
    assert first[0].payload["action"] == expected_action
    assert memory.entries == state_after_first
    if expected_action == "open_dissensus":
        assert memory.tickets == tickets_after_first


# ---------------------------------------------------------------------------
# Undo correctness
# ---------------------------------------------------------------------------


def test_undo_elevate_winner_restores_prior_status() -> None:
    tree = _tree(
        _entry("a", confidence=0.9, contradicts=["b"], hours=25.0),
        _entry("b", confidence=0.3, contradicts=["a"], hours=25.0),
    )
    memory = FakeMemory(tree["memory"]["entries"])
    snapshot = deepcopy(memory.entries)
    rect = ContradictionResolutionRectifier(memory)
    event = rect.rectify(rect.detect(tree), RectifierMode.ACT)[0]
    rect.apply_undo(event)
    assert memory.entries == snapshot


def test_undo_park_pending_evidence_restores_prior_status() -> None:
    tree = _tree(
        _entry("a", confidence=0.55, contradicts=["b"], hours=30.0),
        _entry("b", confidence=0.5, contradicts=["a"], hours=30.0),
    )
    memory = FakeMemory(tree["memory"]["entries"])
    snapshot = deepcopy(memory.entries)
    rect = ContradictionResolutionRectifier(memory)
    event = rect.rectify(rect.detect(tree), RectifierMode.ACT)[0]
    rect.apply_undo(event)
    assert memory.entries == snapshot


def test_undo_open_dissensus_closes_ticket_and_restores_status() -> None:
    tree = _tree(
        _entry(
            "a", confidence=0.95, contradicts=["b"], hours=30.0, depth="deep"
        ),
        _entry(
            "b", confidence=0.1, contradicts=["a"], hours=30.0, depth="deep"
        ),
    )
    memory = FakeMemory(tree["memory"]["entries"])
    snapshot = deepcopy(memory.entries)
    rect = ContradictionResolutionRectifier(memory)
    event = rect.rectify(rect.detect(tree), RectifierMode.ACT)[0]
    rect.apply_undo(event)
    assert memory.entries == snapshot
    assert all(not ticket["open"] for ticket in memory.tickets.values())


def test_apply_undo_without_recipe_raises() -> None:
    rect = ContradictionResolutionRectifier(FakeMemory({}))
    bare = Event(type="r01_action_applied", rectifier_id="r01", payload={})
    with pytest.raises(ValueError):
        rect.apply_undo(bare)
