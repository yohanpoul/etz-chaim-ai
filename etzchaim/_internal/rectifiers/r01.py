"""Rectifier 01 — Contradiction Resolution.

Detects pairs of memory entries marked as contradictory that have remained
unresolved for more than 24 hours, and proposes (or applies, in ``act``
mode) a synthesis pass that elevates the better-supported entry, parks
both pending evidence, or opens a dissensus ticket.

Internal: SPEC-RECT-001 — see ``specs/04_rectifiers/01.md``.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from etzchaim._internal.rectifiers.base import (
    BaseRectifier,
    Deviation,
    Event,
    RectificationMode,
)

STALE_THRESHOLD_HOURS: float = 24.0
ELEVATE_HIGH_CONFIDENCE: float = 0.8
ELEVATE_LOW_CONFIDENCE: float = 0.4
PARK_CONFIDENCE_DELTA: float = 0.2


def _now() -> float:
    return time.time()


def _pair_key(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))  # type: ignore[return-value]


class ContradictionResolutionRectifier(BaseRectifier):
    """Resolve stale contradictions between memory entries.

    The rectifier reads ``tree['memory_entries']`` and ``tree['contradictions']``
    and never deletes any entry; it only flips status flags and appends new
    follow-up artefacts (``pending_questions`` or ``dissensus_tickets``).
    """

    rectifier_id: str = "r01"
    spec_ref: str = "SPEC-RECT-001"

    # Internal: tikkun_1 — Tikkunei Dikna Tikkun 1.

    def __init__(self, *, now_fn: Any = _now) -> None:
        self._now = now_fn

    # ------------------------------------------------------------------ detect

    def detect(self, tree: dict[str, Any]) -> list[Deviation]:
        contradictions = tree.get("contradictions", []) or []
        entries = tree.get("memory_entries", {}) or {}
        if not contradictions:
            return []

        now = float(self._now())
        stale_pairs: list[dict[str, Any]] = []
        oldest_age = 0.0

        for raw in contradictions:
            a_id = raw.get("a")
            b_id = raw.get("b")
            marked_at = float(raw.get("marked_at", 0.0))
            entry_a = entries.get(a_id)
            entry_b = entries.get(b_id)
            if entry_a is None or entry_b is None:
                continue

            last_a = entry_a.get("last_investigated_at") or 0.0
            last_b = entry_b.get("last_investigated_at") or 0.0
            reference = max(marked_at, float(last_a), float(last_b))
            age_hours = (now - reference) / 3600.0
            if age_hours <= STALE_THRESHOLD_HOURS:
                continue

            stale_pairs.append(
                {
                    "a": a_id,
                    "b": b_id,
                    "marked_at": marked_at,
                    "age_hours": age_hours,
                    "confidence_a": float(entry_a.get("confidence", 0.0)),
                    "confidence_b": float(entry_b.get("confidence", 0.0)),
                }
            )
            oldest_age = max(oldest_age, age_hours)

        if not stale_pairs:
            return []

        return [
            Deviation(
                rectifier_id=self.rectifier_id,
                pattern="stale_contradiction",
                metrics={
                    "contradicting_pairs": len(contradictions),
                    "stale_24h_pairs": len(stale_pairs),
                    "oldest_pair_age_hours": oldest_age,
                },
                spec_ref=self.spec_ref,
                payload={"stale_pairs": stale_pairs},
            )
        ]

    # ---------------------------------------------------------------- rectify

    def rectify(
        self,
        deviations: list[Deviation],
        mode: str,
        tree: dict[str, Any] | None = None,
    ) -> list[Event]:
        if mode not in RectificationMode.ALL:
            raise ValueError(f"unknown rectification mode: {mode!r}")

        events: list[Event] = []
        for deviation in deviations:
            if deviation.rectifier_id != self.rectifier_id:
                continue
            if mode == RectificationMode.OBSERVE:
                events.append(
                    Event(
                        rectifier_id=self.rectifier_id,
                        event_type="deviation_observed",
                        details={"metrics": deviation.metrics},
                    )
                )
                continue

            for pair in deviation.payload.get("stale_pairs", []):
                action = self._select_action(pair)
                if mode == RectificationMode.SUGGEST:
                    events.append(
                        Event(
                            rectifier_id=self.rectifier_id,
                            event_type="r01_action_proposed",
                            action=action,
                            details={"pair": dict(pair)},
                        )
                    )
                elif mode == RectificationMode.ACT:
                    if tree is None:
                        raise ValueError("act mode requires a tree to mutate")
                    event = self._apply(action, pair, tree)
                    events.append(event)
        return events

    # --------------------------------------------------------------- internal

    def _select_action(self, pair: dict[str, Any]) -> str:
        ca = float(pair["confidence_a"])
        cb = float(pair["confidence_b"])
        if (ca >= ELEVATE_HIGH_CONFIDENCE and cb <= ELEVATE_LOW_CONFIDENCE) or (
            cb >= ELEVATE_HIGH_CONFIDENCE and ca <= ELEVATE_LOW_CONFIDENCE
        ):
            return "elevate_winner"
        if abs(ca - cb) <= PARK_CONFIDENCE_DELTA:
            return "park_pending_evidence"
        return "open_dissensus"

    def _apply(
        self,
        action: str,
        pair: dict[str, Any],
        tree: dict[str, Any],
    ) -> Event:
        entries = tree.setdefault("memory_entries", {})
        a_id = pair["a"]
        b_id = pair["b"]
        entry_a = entries[a_id]
        entry_b = entries[b_id]

        if action == "elevate_winner":
            if float(pair["confidence_a"]) >= float(pair["confidence_b"]):
                winner_id, loser_id = a_id, b_id
                winner, loser = entry_a, entry_b
            else:
                winner_id, loser_id = b_id, a_id
                winner, loser = entry_b, entry_a

            if winner.get("status") == "elevated" and loser.get("status") == "archived":
                return Event(
                    rectifier_id=self.rectifier_id,
                    event_type="r01_action_skipped",
                    action=action,
                    details={"pair": dict(pair), "reason": "idempotent"},
                )

            undo = {
                "kind": "restore_status",
                "entries": {
                    winner_id: winner.get("status"),
                    loser_id: loser.get("status"),
                },
            }
            winner["status"] = "elevated"
            loser["status"] = "archived"
            return Event(
                rectifier_id=self.rectifier_id,
                event_type="r01_action_applied",
                action=action,
                details={"winner": winner_id, "loser": loser_id},
                undo=undo,
            )

        if action == "park_pending_evidence":
            if entry_a.get("status") == "parked" and entry_b.get("status") == "parked":
                return Event(
                    rectifier_id=self.rectifier_id,
                    event_type="r01_action_skipped",
                    action=action,
                    details={"pair": dict(pair), "reason": "idempotent"},
                )

            undo = {
                "kind": "restore_status_and_drop_question",
                "entries": {
                    a_id: entry_a.get("status"),
                    b_id: entry_b.get("status"),
                },
                "question_id": None,
            }
            entry_a["status"] = "parked"
            entry_b["status"] = "parked"

            question_id = f"q-{uuid.uuid4().hex[:8]}"
            tree.setdefault("pending_questions", []).append(
                {
                    "id": question_id,
                    "kind": "contradiction_followup",
                    "pair": [a_id, b_id],
                }
            )
            undo["question_id"] = question_id
            return Event(
                rectifier_id=self.rectifier_id,
                event_type="r01_action_applied",
                action=action,
                details={"pair": [a_id, b_id], "question_id": question_id},
                undo=undo,
            )

        if action == "open_dissensus":
            tickets = tree.setdefault("dissensus_tickets", [])
            existing = next(
                (t for t in tickets if set(t.get("pair", [])) == {a_id, b_id}),
                None,
            )
            if existing is not None:
                return Event(
                    rectifier_id=self.rectifier_id,
                    event_type="r01_action_skipped",
                    action=action,
                    details={"pair": [a_id, b_id], "reason": "idempotent"},
                )

            ticket_id = f"d-{uuid.uuid4().hex[:8]}"
            tickets.append(
                {
                    "id": ticket_id,
                    "pair": [a_id, b_id],
                    "opened_at": float(self._now()),
                }
            )
            undo = {"kind": "remove_dissensus_ticket", "ticket_id": ticket_id}
            return Event(
                rectifier_id=self.rectifier_id,
                event_type="r01_action_applied",
                action=action,
                details={"pair": [a_id, b_id], "ticket_id": ticket_id},
                undo=undo,
            )

        raise ValueError(f"unknown action: {action!r}")

    # ------------------------------------------------------------------- undo

    def apply_undo(self, undo: dict[str, Any], tree: dict[str, Any]) -> None:
        kind = undo.get("kind")
        if kind == "restore_status":
            entries = tree.get("memory_entries", {})
            for entry_id, status in undo.get("entries", {}).items():
                entry = entries.get(entry_id)
                if entry is None:
                    continue
                if status is None:
                    entry.pop("status", None)
                else:
                    entry["status"] = status
            return

        if kind == "restore_status_and_drop_question":
            entries = tree.get("memory_entries", {})
            for entry_id, status in undo.get("entries", {}).items():
                entry = entries.get(entry_id)
                if entry is None:
                    continue
                if status is None:
                    entry.pop("status", None)
                else:
                    entry["status"] = status
            qid = undo.get("question_id")
            if qid is not None:
                questions = tree.get("pending_questions", [])
                tree["pending_questions"] = [q for q in questions if q.get("id") != qid]
            return

        if kind == "remove_dissensus_ticket":
            tid = undo.get("ticket_id")
            tickets = tree.get("dissensus_tickets", [])
            tree["dissensus_tickets"] = [t for t in tickets if t.get("id") != tid]
            return

        raise ValueError(f"unknown undo kind: {kind!r}")


__all__ = ["ContradictionResolutionRectifier"]
