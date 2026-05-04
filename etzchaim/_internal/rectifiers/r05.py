"""Rectifier 05 — Tension Freeze.

Detects open dissensus tickets in the Tension faculty that have stalled
past a configurable freeze threshold. In ``act`` mode, parks tickets that
froze without any evidence (reason: ``insufficient_evidence``) and routes
tickets that have evidence but no synthesis attempt to the Synthesis
Bridge as a synthesis request. The rectifier never auto-resolves a
tension ; it only parks or routes.

Internal: SPEC-RECT-005 — see ``specs/04_rectifiers/05.md``.
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Callable

from etzchaim._internal.rectifiers.base import (
    BaseRectifier,
    Deviation,
    Event,
    RectificationMode,
)

DEFAULT_FREEZE_DAYS: float = 7.0
DEFAULT_PARK_DAYS: float = 14.0
PARKED_STATUS: str = "parked"
PARK_REASON_INSUFFICIENT: str = "insufficient_evidence"

SECONDS_PER_DAY: float = 86_400.0


def _now() -> float:
    return time.time()


def _has_evidence(ticket: dict[str, Any]) -> bool:
    evidence = ticket.get("evidence")
    if evidence is None:
        return False
    if isinstance(evidence, (list, tuple, set, dict)):
        return len(evidence) > 0
    return bool(evidence)


def _has_synthesis_attempt(ticket: dict[str, Any]) -> bool:
    attempts = ticket.get("synthesis_attempts")
    if attempts is None:
        return False
    if isinstance(attempts, (list, tuple, set, dict)):
        return len(attempts) > 0
    if isinstance(attempts, (int, float)):
        return attempts > 0
    return bool(attempts)


def _last_progress(ticket: dict[str, Any]) -> float | None:
    for key in ("last_progress_at", "opened_at"):
        value = ticket.get(key)
        if value is not None:
            return float(value)
    return None


# Internal: tikkun_5 — Tikkunei Dikna Tikkun 5.


class TensionFreezeRectifier(BaseRectifier):
    """Park or route stalled dissensus tickets in the Tension faculty.

    The rectifier reads ``tree['tensions']`` (a mapping of id → ticket).
    A ticket is considered *frozen* when its age since last progress
    exceeds the configurable freeze threshold (default 7 days). Action
    only fires past the *park* threshold (default 14 days) ; tickets in
    between are reported but left untouched.
    """

    rectifier_id: str = "r05"
    spec_ref: str = "SPEC-RECT-005"

    def __init__(
        self,
        *,
        freeze_days: float = DEFAULT_FREEZE_DAYS,
        park_days: float = DEFAULT_PARK_DAYS,
        now_fn: Callable[[], float] = _now,
    ) -> None:
        if freeze_days < 0:
            raise ValueError("freeze_days must be >= 0")
        if park_days < freeze_days:
            raise ValueError("park_days must be >= freeze_days")
        self._freeze_days = float(freeze_days)
        self._park_days = float(park_days)
        self._now = now_fn

    @property
    def freeze_days(self) -> float:
        return self._freeze_days

    @property
    def park_days(self) -> float:
        return self._park_days

    def detect(self, tree: dict[str, Any]) -> list[Deviation]:
        tensions = tree.get("tensions", {}) or {}
        if not tensions:
            return []

        now = float(self._now())
        open_tickets = 0
        frozen: list[dict[str, Any]] = []
        oldest_age_days = 0.0

        for tid, ticket in tensions.items():
            status = ticket.get("status") or "open"
            if status != "open":
                continue
            open_tickets += 1
            last = _last_progress(ticket)
            if last is None:
                continue
            age_days = max(0.0, (now - last) / SECONDS_PER_DAY)
            oldest_age_days = max(oldest_age_days, age_days)
            if age_days <= self._freeze_days:
                continue
            frozen.append(
                {
                    "id": tid,
                    "age_days": age_days,
                    "has_evidence": _has_evidence(ticket),
                    "has_synthesis_attempt": _has_synthesis_attempt(ticket),
                }
            )

        if not frozen:
            return []

        frozen.sort(key=lambda f: (-f["age_days"], f["id"]))
        return [
            Deviation(
                rectifier_id=self.rectifier_id,
                pattern="tension_freeze",
                metrics={
                    "open_tickets": open_tickets,
                    "frozen_over_7d": len(frozen),
                    "oldest_age_days": oldest_age_days,
                    "freeze_days": self._freeze_days,
                    "park_days": self._park_days,
                    "frozen_ticket_ids": [f["id"] for f in frozen],
                },
                spec_ref=self.spec_ref,
                payload={"frozen": frozen},
            )
        ]

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
                        details={"metrics": dict(deviation.metrics)},
                    )
                )
                continue

            frozen = list(deviation.payload.get("frozen", []))

            if mode == RectificationMode.SUGGEST:
                events.append(
                    Event(
                        rectifier_id=self.rectifier_id,
                        event_type="r05_action_proposed",
                        action="force_advance",
                        details={
                            "frozen_ticket_ids": [f["id"] for f in frozen],
                            "park_days": self._park_days,
                            "metrics": dict(deviation.metrics),
                        },
                    )
                )
                continue

            if mode == RectificationMode.ACT:
                if tree is None:
                    raise ValueError("act mode requires a tree to mutate")
                events.extend(self._apply_act(frozen, tree))

        return events

    def _apply_act(
        self,
        frozen: list[dict[str, Any]],
        tree: dict[str, Any],
    ) -> list[Event]:
        tensions = tree.setdefault("tensions", {})
        events: list[Event] = []

        for entry in frozen:
            tid = entry["id"]
            ticket = tensions.get(tid)
            if ticket is None:
                continue

            age_days = float(entry.get("age_days", 0.0))
            if age_days <= self._park_days:
                continue

            status = ticket.get("status") or "open"
            if status != "open":
                events.append(
                    Event(
                        rectifier_id=self.rectifier_id,
                        event_type="r05_action_skipped",
                        action="force_advance",
                        details={"ticket_id": tid, "reason": "not_open"},
                    )
                )
                continue

            has_evidence = _has_evidence(ticket)
            has_synthesis = _has_synthesis_attempt(ticket)

            if not has_evidence:
                events.append(self._park_ticket(tid, ticket, age_days, tree))
                continue

            if not has_synthesis:
                events.append(self._request_synthesis(tid, ticket, age_days, tree))
                continue

            events.append(
                Event(
                    rectifier_id=self.rectifier_id,
                    event_type="r05_action_skipped",
                    action="force_advance",
                    details={
                        "ticket_id": tid,
                        "reason": "synthesis_already_attempted",
                    },
                )
            )

        return events

    def _park_ticket(
        self,
        tid: str,
        ticket: dict[str, Any],
        age_days: float,
        tree: dict[str, Any],
    ) -> Event:
        prior_status = ticket.get("status")
        prior_reason = ticket.get("park_reason")
        prior_parked_at = ticket.get("parked_at")

        ticket["status"] = PARKED_STATUS
        ticket["park_reason"] = PARK_REASON_INSUFFICIENT
        ticket["parked_at"] = float(self._now())

        undo = {
            "kind": "restore_ticket",
            "ticket_id": tid,
            "prior_status": prior_status,
            "prior_park_reason": prior_reason,
            "prior_parked_at": prior_parked_at,
        }
        return Event(
            rectifier_id=self.rectifier_id,
            event_type="r05_action_applied",
            action="park_ticket",
            details={
                "ticket_id": tid,
                "age_days": age_days,
                "reason": PARK_REASON_INSUFFICIENT,
            },
            undo=undo,
        )

    def _request_synthesis(
        self,
        tid: str,
        ticket: dict[str, Any],
        age_days: float,
        tree: dict[str, Any],
    ) -> Event:
        request_id = f"s-{uuid.uuid4().hex[:8]}"
        request = {
            "id": request_id,
            "kind": "synthesis_attempt",
            "tension_id": tid,
            "age_days": age_days,
            "opened_at": float(self._now()),
        }
        tree.setdefault("synthesis_requests", []).append(request)

        undo = {
            "kind": "drop_synthesis_request",
            "ticket_id": tid,
            "request_id": request_id,
        }
        return Event(
            rectifier_id=self.rectifier_id,
            event_type="r05_action_applied",
            action="request_synthesis",
            details={
                "ticket_id": tid,
                "age_days": age_days,
                "request_id": request_id,
            },
            undo=undo,
        )

    def apply_undo(self, undo: dict[str, Any], tree: dict[str, Any]) -> None:
        kind = undo.get("kind")
        if kind == "restore_ticket":
            self._undo_park(undo, tree)
            return
        if kind == "drop_synthesis_request":
            self._undo_synthesis(undo, tree)
            return
        raise ValueError(f"unknown undo kind: {kind!r}")

    def _undo_park(self, undo: dict[str, Any], tree: dict[str, Any]) -> None:
        tensions = tree.get("tensions", {})
        tid = undo.get("ticket_id")
        ticket = tensions.get(tid) if tid is not None else None
        if ticket is None:
            return
        prior_status = undo.get("prior_status")
        if prior_status is None:
            ticket.pop("status", None)
        else:
            ticket["status"] = prior_status

        prior_reason = undo.get("prior_park_reason")
        if prior_reason is None:
            ticket.pop("park_reason", None)
        else:
            ticket["park_reason"] = prior_reason

        prior_parked_at = undo.get("prior_parked_at")
        if prior_parked_at is None:
            ticket.pop("parked_at", None)
        else:
            ticket["parked_at"] = prior_parked_at

    def _undo_synthesis(self, undo: dict[str, Any], tree: dict[str, Any]) -> None:
        request_id = undo.get("request_id")
        if request_id is None:
            return
        requests = tree.get("synthesis_requests", [])
        tree["synthesis_requests"] = [
            r for r in requests if r.get("id") != request_id
        ]


__all__ = [
    "TensionFreezeRectifier",
    "DEFAULT_FREEZE_DAYS",
    "DEFAULT_PARK_DAYS",
    "PARKED_STATUS",
    "PARK_REASON_INSUFFICIENT",
]
