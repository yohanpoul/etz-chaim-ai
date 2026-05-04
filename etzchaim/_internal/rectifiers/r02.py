"""Rectifier 02 — Memory Bloat.

Detects accumulation of low-value entries (low confidence + low access count
over a 30-day window) that crowd out signal in the memory store, and
proposes (or applies, in ``act`` mode) an archive pass capped at 25% of the
active entries.

Internal: SPEC-RECT-002 — see ``specs/04_rectifiers/02.md``.
"""
from __future__ import annotations

import time
from typing import Any

from etzchaim._internal.rectifiers.base import (
    BaseRectifier,
    Deviation,
    Event,
    RectificationMode,
)

DAY: float = 86400.0

DEFAULT_TOTAL_ENTRIES_TRIGGER: int = 100
DEFAULT_BLOAT_RATIO_TRIGGER: float = 0.3
DEFAULT_CONFIDENCE_THRESHOLD: float = 0.3
DEFAULT_ACCESS_THRESHOLD: int = 2
DEFAULT_AGE_DAYS_THRESHOLD: float = 30.0
DEFAULT_ARCHIVE_CAP_RATIO: float = 0.25


def _now() -> float:
    return time.time()


# Internal: tikkun_2 — Tikkunei Dikna Tikkun 2.


class MemoryBloatRectifier(BaseRectifier):
    """Archive low-value entries crowding out signal in the memory store.

    The rectifier reads ``tree['memory_entries']`` (a mapping of id → entry)
    and never deletes any entry; it only flips ``status`` from ``active`` to
    ``archived``. An undo recipe restores prior status flags.
    """

    rectifier_id: str = "r02"
    spec_ref: str = "SPEC-RECT-002"

    def __init__(
        self,
        *,
        total_entries_trigger: int = DEFAULT_TOTAL_ENTRIES_TRIGGER,
        bloat_ratio_trigger: float = DEFAULT_BLOAT_RATIO_TRIGGER,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        access_threshold: int = DEFAULT_ACCESS_THRESHOLD,
        age_days_threshold: float = DEFAULT_AGE_DAYS_THRESHOLD,
        archive_cap_ratio: float = DEFAULT_ARCHIVE_CAP_RATIO,
        now_fn: Any = _now,
    ) -> None:
        if not 0.0 < archive_cap_ratio <= 1.0:
            raise ValueError("archive_cap_ratio must be in (0, 1]")
        self._total_entries_trigger = total_entries_trigger
        self._bloat_ratio_trigger = bloat_ratio_trigger
        self._confidence_threshold = confidence_threshold
        self._access_threshold = access_threshold
        self._age_days_threshold = age_days_threshold
        self._archive_cap_ratio = archive_cap_ratio
        self._now = now_fn

    # ------------------------------------------------------------------ detect

    def detect(self, tree: dict[str, Any]) -> list[Deviation]:
        entries = tree.get("memory_entries", {}) or {}
        active = [
            (eid, entry)
            for eid, entry in entries.items()
            if (entry.get("status") or "active") == "active"
        ]
        total_active = len(active)
        if total_active == 0:
            return []

        now = float(self._now())
        candidates: list[str] = []
        for eid, entry in active:
            if self._is_low_value(entry, now):
                candidates.append(eid)

        ratio = len(candidates) / total_active if total_active else 0.0

        if (
            total_active <= self._total_entries_trigger
            or ratio <= self._bloat_ratio_trigger
        ):
            return []

        sorted_candidates = sorted(
            candidates,
            key=lambda eid: self._archive_priority(entries[eid], now),
        )

        return [
            Deviation(
                rectifier_id=self.rectifier_id,
                pattern="memory_bloat",
                metrics={
                    "total_entries": total_active,
                    "low_confidence_low_access": len(candidates),
                    "ratio": ratio,
                },
                spec_ref=self.spec_ref,
                payload={"prune_candidates": sorted_candidates},
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

            candidates = list(deviation.payload.get("prune_candidates", []))
            capped = self._apply_cap(candidates, deviation.metrics["total_entries"])

            if mode == RectificationMode.SUGGEST:
                events.append(
                    Event(
                        rectifier_id=self.rectifier_id,
                        event_type="r02_action_proposed",
                        action="archive_low_value",
                        details={
                            "prune_candidates": capped,
                            "metrics": dict(deviation.metrics),
                        },
                    )
                )
                continue

            if mode == RectificationMode.ACT:
                if tree is None:
                    raise ValueError("act mode requires a tree to mutate")
                events.append(self._apply_archive(capped, tree))

        return events

    # --------------------------------------------------------------- internal

    def _is_low_value(self, entry: dict[str, Any], now: float) -> bool:
        confidence = float(entry.get("confidence", 1.0))
        access_count = int(entry.get("access_count", 0))
        created_at = float(entry.get("created_at", now))
        age_days = (now - created_at) / DAY
        return (
            confidence < self._confidence_threshold
            and access_count < self._access_threshold
            and age_days > self._age_days_threshold
        )

    def _archive_priority(
        self, entry: dict[str, Any], now: float
    ) -> tuple[float, int, float]:
        confidence = float(entry.get("confidence", 1.0))
        access_count = int(entry.get("access_count", 0))
        created_at = float(entry.get("created_at", now))
        age_days = (now - created_at) / DAY
        # Lower confidence first, then fewer accesses, then older entries.
        return (confidence, access_count, -age_days)

    def _apply_cap(self, candidates: list[str], total_active: int) -> list[str]:
        cap = int(total_active * self._archive_cap_ratio)
        if cap <= 0:
            return []
        return list(candidates[:cap])

    def _apply_archive(
        self, capped: list[str], tree: dict[str, Any]
    ) -> Event:
        entries = tree.setdefault("memory_entries", {})
        archived: list[str] = []
        prior_status: dict[str, Any] = {}

        for eid in capped:
            entry = entries.get(eid)
            if entry is None:
                continue
            current_status = entry.get("status") or "active"
            if current_status == "archived":
                continue
            prior_status[eid] = entry.get("status")
            entry["status"] = "archived"
            archived.append(eid)

        if not archived:
            return Event(
                rectifier_id=self.rectifier_id,
                event_type="r02_action_skipped",
                action="archive_low_value",
                details={"reason": "idempotent", "candidates": list(capped)},
            )

        undo = {
            "kind": "restore_archived_entries",
            "entries": prior_status,
        }
        return Event(
            rectifier_id=self.rectifier_id,
            event_type="r02_action_applied",
            action="archive_low_value",
            details={"archived": archived},
            undo=undo,
        )

    # ------------------------------------------------------------------- undo

    def apply_undo(self, undo: dict[str, Any], tree: dict[str, Any]) -> None:
        kind = undo.get("kind")
        if kind == "restore_archived_entries":
            entries = tree.get("memory_entries", {})
            for eid, status in undo.get("entries", {}).items():
                entry = entries.get(eid)
                if entry is None:
                    continue
                if status is None:
                    entry.pop("status", None)
                else:
                    entry["status"] = status
            return

        raise ValueError(f"unknown undo kind: {kind!r}")


__all__ = ["MemoryBloatRectifier"]
