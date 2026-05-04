"""Contradiction resolution rectifier — SPEC-RECT-001.

Triggered when two memory entries are tagged as contradictory and neither
has been investigated for over 24 hours. Selects one of three remediation
branches (elevate the better-supported entry, park both pending evidence,
or open a dissensus ticket) and either reports, proposes, or applies the
choice depending on the requested rectification mode.

Public class: :class:`ContradictionResolutionRectifier`.

# Internal: tikkun_1
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from etzchaim._internal.rectifiers.base import (
    BaseRectifier,
    Deviation,
    Event,
    MemoryFaculty,
    RectificationMode,
    UndoRecipe,
)

STALE_HOURS_THRESHOLD: float = 24.0
WINNER_CONFIDENCE_FLOOR: float = 0.8
LOSER_CONFIDENCE_CEIL: float = 0.4
SIMILAR_CONFIDENCE_BAND: float = 0.2

ACTION_ELEVATE = "elevate_winner"
ACTION_PARK = "park_pending_evidence"
ACTION_OPEN_DISSENSUS = "open_dissensus"

STATUS_ACTIVE = "active"
STATUS_ELEVATED = "elevated"
STATUS_ARCHIVED = "archived"
STATUS_PARKED = "parked"
STATUS_DISSENSUS = "dissensus_open"


@dataclass(frozen=True)
class _Pair:
    """Normalized representation of a contradicting pair."""

    a_id: str
    b_id: str
    a_confidence: float
    b_confidence: float
    a_hours: float
    b_hours: float
    depth: str  # "shallow" | "deep"


def _read_entries(tree: Mapping[str, object]) -> Mapping[str, Mapping[str, object]]:
    memory = tree.get("memory") or {}
    if not isinstance(memory, Mapping):
        return {}
    entries = memory.get("entries") or {}
    if not isinstance(entries, Mapping):
        return {}
    return entries  # type: ignore[return-value]


def _iter_pairs(
    entries: Mapping[str, Mapping[str, object]],
) -> Iterable[_Pair]:
    seen: set[tuple[str, str]] = set()
    for entry_id, entry in entries.items():
        contradicts = entry.get("contradicts") or ()
        if not isinstance(contradicts, (list, tuple, set)):
            continue
        for other_id in contradicts:
            if other_id == entry_id or other_id not in entries:
                continue
            other = entries[other_id]
            other_contradicts = other.get("contradicts") or ()
            if entry_id not in other_contradicts:
                continue
            key = tuple(sorted((str(entry_id), str(other_id))))
            if key in seen:
                continue
            seen.add(key)
            a_id, b_id = key
            a, b = entries[a_id], entries[b_id]
            yield _Pair(
                a_id=a_id,
                b_id=b_id,
                a_confidence=float(a.get("confidence", 0.0)),
                b_confidence=float(b.get("confidence", 0.0)),
                a_hours=float(a.get("last_investigated_at_hours_ago", 0.0)),
                b_hours=float(b.get("last_investigated_at_hours_ago", 0.0)),
                depth=str(
                    a.get("concept_depth")
                    or b.get("concept_depth")
                    or "shallow"
                ),
            )


def _both_active(entries: Mapping[str, Mapping[str, object]], pair: _Pair) -> bool:
    return (
        entries[pair.a_id].get("status", STATUS_ACTIVE) == STATUS_ACTIVE
        and entries[pair.b_id].get("status", STATUS_ACTIVE) == STATUS_ACTIVE
    )


def _select_action(pair: _Pair) -> tuple[str, dict[str, object]]:
    """Pick which of the three branches applies to ``pair``.

    Returns the action name and a parameter dict describing target ids.
    """
    if pair.depth == "deep":
        return ACTION_OPEN_DISSENSUS, {"a_id": pair.a_id, "b_id": pair.b_id}

    high = max(pair.a_confidence, pair.b_confidence)
    low = min(pair.a_confidence, pair.b_confidence)
    if high > WINNER_CONFIDENCE_FLOOR and low < LOSER_CONFIDENCE_CEIL:
        if pair.a_confidence >= pair.b_confidence:
            winner, loser = pair.a_id, pair.b_id
        else:
            winner, loser = pair.b_id, pair.a_id
        return ACTION_ELEVATE, {"winner_id": winner, "loser_id": loser}

    if abs(pair.a_confidence - pair.b_confidence) <= SIMILAR_CONFIDENCE_BAND:
        return ACTION_PARK, {"a_id": pair.a_id, "b_id": pair.b_id}

    return ACTION_OPEN_DISSENSUS, {"a_id": pair.a_id, "b_id": pair.b_id}


class ContradictionResolutionRectifier(BaseRectifier):
    """Reconciles stale contradicting memory entries through a faculty channel.

    The rectifier never deletes entries. It mutates only ``status`` flags
    and, for the deepest case, opens a dissensus ticket via the supplied
    :class:`MemoryFaculty`. Every applied action attaches an
    :class:`UndoRecipe` so a reviewer can roll back through
    :meth:`BaseRectifier.apply_undo`.

    # Internal: tikkun_1
    """

    rectifier_id: str = "r01"
    spec_ref: str = "SPEC-RECT-001"

    def __init__(self, memory: MemoryFaculty) -> None:
        self._memory = memory

    def detect(self, tree: Mapping[str, object]) -> list[Deviation]:
        entries = _read_entries(tree)
        deviations: list[Deviation] = []
        oldest = 0.0
        stale_pairs: list[_Pair] = []
        for pair in _iter_pairs(entries):
            if not _both_active(entries, pair):
                continue
            if pair.a_hours <= STALE_HOURS_THRESHOLD:
                continue
            if pair.b_hours <= STALE_HOURS_THRESHOLD:
                continue
            stale_pairs.append(pair)
            oldest = max(oldest, pair.a_hours, pair.b_hours)

        for pair in stale_pairs:
            deviations.append(
                Deviation(
                    rectifier_id=self.rectifier_id,
                    pattern="stale_contradiction",
                    metrics={
                        "contradicting_pairs": len(stale_pairs),
                        "stale_24h_pairs": len(stale_pairs),
                        "oldest_pair_age_hours": oldest,
                        "pair": (pair.a_id, pair.b_id),
                        "confidences": (pair.a_confidence, pair.b_confidence),
                        "depth": pair.depth,
                    },
                    spec_ref=self.spec_ref,
                )
            )
        return deviations

    def rectify(
        self,
        deviations: Sequence[Deviation],
        mode: RectificationMode,
    ) -> list[Event]:
        events: list[Event] = []
        for deviation in deviations:
            if deviation.rectifier_id != self.rectifier_id:
                continue
            pair_ids = deviation.metrics.get("pair")
            if not isinstance(pair_ids, tuple) or len(pair_ids) != 2:
                continue
            confidences = deviation.metrics.get("confidences", (0.0, 0.0))
            depth = deviation.metrics.get("depth", "shallow")
            pair = _Pair(
                a_id=str(pair_ids[0]),
                b_id=str(pair_ids[1]),
                a_confidence=float(confidences[0]),  # type: ignore[index]
                b_confidence=float(confidences[1]),  # type: ignore[index]
                a_hours=0.0,
                b_hours=0.0,
                depth=str(depth),
            )
            action, params = _select_action(pair)
            if mode == RectificationMode.OBSERVE:
                events.append(self._observe_event(deviation, action, params))
            elif mode == RectificationMode.SUGGEST:
                events.append(self._propose_event(deviation, action, params))
            elif mode == RectificationMode.ACT:
                events.append(self._apply_event(deviation, action, params))
            else:
                raise ValueError(f"unknown rectification mode: {mode!r}")
        return events

    # ------------------------------------------------------------------
    # Event builders
    # ------------------------------------------------------------------

    def _observe_event(
        self,
        deviation: Deviation,
        action: str,
        params: Mapping[str, object],
    ) -> Event:
        return Event(
            type="r01_deviation_observed",
            rectifier_id=self.rectifier_id,
            payload={
                "spec_ref": deviation.spec_ref,
                "candidate_action": action,
                "params": dict(params),
                "metrics": dict(deviation.metrics),
            },
        )

    def _propose_event(
        self,
        deviation: Deviation,
        action: str,
        params: Mapping[str, object],
    ) -> Event:
        return Event(
            type="r01_action_proposed",
            rectifier_id=self.rectifier_id,
            payload={
                "spec_ref": deviation.spec_ref,
                "action": action,
                "params": dict(params),
            },
        )

    def _apply_event(
        self,
        deviation: Deviation,
        action: str,
        params: Mapping[str, object],
    ) -> Event:
        if action == ACTION_ELEVATE:
            applied, undo = self._apply_elevate(
                str(params["winner_id"]),
                str(params["loser_id"]),
            )
        elif action == ACTION_PARK:
            applied, undo = self._apply_park(
                str(params["a_id"]),
                str(params["b_id"]),
            )
        elif action == ACTION_OPEN_DISSENSUS:
            applied, undo = self._apply_open_dissensus(
                str(params["a_id"]),
                str(params["b_id"]),
                reason=str(deviation.metrics.get("pattern", "stale_contradiction")),
            )
        else:
            raise ValueError(f"unknown action: {action!r}")
        return Event(
            type="r01_action_applied",
            rectifier_id=self.rectifier_id,
            payload={
                "spec_ref": deviation.spec_ref,
                "action": action,
                "params": dict(params),
                "applied": applied,
            },
            undo=undo,
        )

    # ------------------------------------------------------------------
    # Apply branches (idempotent — each checks current status first)
    # ------------------------------------------------------------------

    def _apply_elevate(
        self,
        winner_id: str,
        loser_id: str,
    ) -> tuple[bool, UndoRecipe]:
        prior_winner = self._memory.get_status(winner_id)
        prior_loser = self._memory.get_status(loser_id)
        applied = False
        if prior_winner != STATUS_ELEVATED:
            self._memory.set_status(winner_id, STATUS_ELEVATED)
            applied = True
        if prior_loser != STATUS_ARCHIVED:
            self._memory.set_status(loser_id, STATUS_ARCHIVED)
            applied = True
        undo = UndoRecipe(
            action=ACTION_ELEVATE,
            args={
                "winner_id": winner_id,
                "loser_id": loser_id,
                "prior_winner_status": prior_winner,
                "prior_loser_status": prior_loser,
            },
        )
        return applied, undo

    def _apply_park(
        self,
        a_id: str,
        b_id: str,
    ) -> tuple[bool, UndoRecipe]:
        prior_a = self._memory.get_status(a_id)
        prior_b = self._memory.get_status(b_id)
        applied = False
        if prior_a != STATUS_PARKED:
            self._memory.set_status(a_id, STATUS_PARKED)
            applied = True
        if prior_b != STATUS_PARKED:
            self._memory.set_status(b_id, STATUS_PARKED)
            applied = True
        undo = UndoRecipe(
            action=ACTION_PARK,
            args={
                "a_id": a_id,
                "b_id": b_id,
                "prior_a_status": prior_a,
                "prior_b_status": prior_b,
            },
        )
        return applied, undo

    def _apply_open_dissensus(
        self,
        a_id: str,
        b_id: str,
        *,
        reason: str,
    ) -> tuple[bool, UndoRecipe]:
        prior_a = self._memory.get_status(a_id)
        prior_b = self._memory.get_status(b_id)
        ticket_id: str | None = None
        applied = False
        if prior_a != STATUS_DISSENSUS or prior_b != STATUS_DISSENSUS:
            ticket_id = self._memory.open_dissensus_ticket(a_id, b_id, reason)
            if prior_a != STATUS_DISSENSUS:
                self._memory.set_status(a_id, STATUS_DISSENSUS)
            if prior_b != STATUS_DISSENSUS:
                self._memory.set_status(b_id, STATUS_DISSENSUS)
            applied = True
        undo = UndoRecipe(
            action=ACTION_OPEN_DISSENSUS,
            args={
                "a_id": a_id,
                "b_id": b_id,
                "prior_a_status": prior_a,
                "prior_b_status": prior_b,
                "ticket_id": ticket_id,
            },
        )
        return applied, undo

    # ------------------------------------------------------------------
    # Undo branches — invoked by BaseRectifier.apply_undo
    # ------------------------------------------------------------------

    def _undo_elevate_winner(
        self,
        *,
        winner_id: str,
        loser_id: str,
        prior_winner_status: str,
        prior_loser_status: str,
    ) -> None:
        self._memory.set_status(winner_id, prior_winner_status)
        self._memory.set_status(loser_id, prior_loser_status)

    def _undo_park_pending_evidence(
        self,
        *,
        a_id: str,
        b_id: str,
        prior_a_status: str,
        prior_b_status: str,
    ) -> None:
        self._memory.set_status(a_id, prior_a_status)
        self._memory.set_status(b_id, prior_b_status)

    def _undo_open_dissensus(
        self,
        *,
        a_id: str,
        b_id: str,
        prior_a_status: str,
        prior_b_status: str,
        ticket_id: str | None,
    ) -> None:
        if ticket_id is not None:
            self._memory.close_dissensus_ticket(ticket_id)
        self._memory.set_status(a_id, prior_a_status)
        self._memory.set_status(b_id, prior_b_status)
