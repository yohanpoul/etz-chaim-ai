"""Rectifier 03 — Insight Grounding.

Detects insights emitted with no traceable provenance to the source corpus
or to prior memory entries (an ungrounded-generation proxy), and proposes
(or applies, in ``act`` mode) a re-grounding pass that either attaches the
provenance returned by the Insight faculty's ``seek_provenance`` callable
or, after a bounded number of failed attempts, demotes the insight to a
``quarantined`` state.

Internal: SPEC-RECT-003 — see ``specs/04_rectifiers/03.md``.
"""
from __future__ import annotations

import time
from typing import Any, Callable

from etzchaim._internal.rectifiers.base import (
    BaseRectifier,
    Deviation,
    Event,
    RectificationMode,
)

DAY: float = 86400.0

DEFAULT_WINDOW_SECONDS: float = DAY
DEFAULT_UNGROUNDED_COUNT_TRIGGER: int = 1
DEFAULT_MAX_GROUNDING_ATTEMPTS: int = 3

SeekProvenance = Callable[[str, dict[str, Any]], list[str]]


def _now() -> float:
    return time.time()


def _empty_seek_provenance(insight_id: str, tree: dict[str, Any]) -> list[str]:
    return []


# Internal: tikkun_3 — Tikkunei Dikna Tikkun 3.


class InsightGroundingRectifier(BaseRectifier):
    """Re-ground insights lacking provenance, or quarantine them after retries.

    The rectifier reads ``tree['insights']`` (a mapping of id → insight) and
    never modifies insight content; it only attaches ``sources`` returned by
    the injected ``seek_provenance`` callable, or flips ``status`` from
    ``active`` to ``quarantined`` after the bounded retry budget is exhausted.
    """

    rectifier_id: str = "r03"
    spec_ref: str = "SPEC-RECT-003"

    def __init__(
        self,
        *,
        seek_provenance: SeekProvenance | None = None,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
        ungrounded_count_trigger: int = DEFAULT_UNGROUNDED_COUNT_TRIGGER,
        max_attempts: int = DEFAULT_MAX_GROUNDING_ATTEMPTS,
        now_fn: Callable[[], float] = _now,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if ungrounded_count_trigger < 1:
            raise ValueError("ungrounded_count_trigger must be >= 1")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        self._seek_provenance: SeekProvenance = (
            seek_provenance if seek_provenance is not None else _empty_seek_provenance
        )
        self._window_seconds = window_seconds
        self._ungrounded_count_trigger = ungrounded_count_trigger
        self._max_attempts = max_attempts
        self._now = now_fn

    # ------------------------------------------------------------------ detect

    def detect(self, tree: dict[str, Any]) -> list[Deviation]:
        insights = tree.get("insights", {}) or {}
        if not insights:
            return []

        now = float(self._now())
        cutoff = now - self._window_seconds

        active_in_window: list[str] = []
        ungrounded: list[str] = []
        for iid, insight in insights.items():
            if (insight.get("status") or "active") != "active":
                continue
            created_at = float(insight.get("created_at", now))
            if created_at < cutoff:
                continue
            active_in_window.append(iid)
            if not self._has_provenance(insight):
                ungrounded.append(iid)

        total_window = len(active_in_window)
        ungrounded_count = len(ungrounded)
        if ungrounded_count < self._ungrounded_count_trigger:
            return []

        ratio = ungrounded_count / total_window if total_window else 0.0
        sorted_ungrounded = sorted(
            ungrounded,
            key=lambda iid: float(insights[iid].get("created_at", now)),
        )

        return [
            Deviation(
                rectifier_id=self.rectifier_id,
                pattern="ungrounded_insight",
                metrics={
                    "ungrounded_count_24h": ungrounded_count,
                    "ratio_ungrounded": ratio,
                    "total_window": total_window,
                },
                spec_ref=self.spec_ref,
                payload={"ungrounded_ids": sorted_ungrounded},
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
                        details={"metrics": dict(deviation.metrics)},
                    )
                )
                continue

            ungrounded_ids = list(deviation.payload.get("ungrounded_ids", []))

            if mode == RectificationMode.SUGGEST:
                events.append(
                    Event(
                        rectifier_id=self.rectifier_id,
                        event_type="r03_action_proposed",
                        action="seek_provenance",
                        details={
                            "ungrounded_ids": ungrounded_ids,
                            "max_attempts": self._max_attempts,
                            "metrics": dict(deviation.metrics),
                        },
                    )
                )
                continue

            if mode == RectificationMode.ACT:
                if tree is None:
                    raise ValueError("act mode requires a tree to mutate")
                events.extend(self._apply_act(ungrounded_ids, tree))

        return events

    # --------------------------------------------------------------- internal

    def _has_provenance(self, insight: dict[str, Any]) -> bool:
        sources = insight.get("sources")
        if sources is None:
            return False
        try:
            return len(sources) > 0
        except TypeError:
            return False

    def _apply_act(
        self, ungrounded_ids: list[str], tree: dict[str, Any]
    ) -> list[Event]:
        insights = tree.setdefault("insights", {})
        events: list[Event] = []
        for iid in ungrounded_ids:
            insight = insights.get(iid)
            if insight is None:
                continue
            if (insight.get("status") or "active") != "active":
                events.append(
                    Event(
                        rectifier_id=self.rectifier_id,
                        event_type="r03_action_skipped",
                        action="seek_provenance",
                        details={"insight_id": iid, "reason": "idempotent"},
                    )
                )
                continue
            if self._has_provenance(insight):
                events.append(
                    Event(
                        rectifier_id=self.rectifier_id,
                        event_type="r03_action_skipped",
                        action="seek_provenance",
                        details={"insight_id": iid, "reason": "already_grounded"},
                    )
                )
                continue

            attempts = 0
            found_sources: list[str] = []
            while attempts < self._max_attempts:
                attempts += 1
                result = self._seek_provenance(iid, tree)
                if result:
                    found_sources = list(result)
                    break

            if found_sources:
                events.append(self._apply_grounding(iid, insight, found_sources, attempts))
            else:
                events.append(self._apply_quarantine(iid, insight, attempts))

        return events

    def _apply_grounding(
        self,
        iid: str,
        insight: dict[str, Any],
        sources: list[str],
        attempts: int,
    ) -> Event:
        prior_sources = insight.get("sources")
        insight["sources"] = list(sources)
        undo = {
            "kind": "restore_sources",
            "insight_id": iid,
            "prior_sources": prior_sources,
        }
        return Event(
            rectifier_id=self.rectifier_id,
            event_type="r03_action_applied",
            action="ground_insight",
            details={
                "insight_id": iid,
                "sources": list(sources),
                "attempts": attempts,
            },
            undo=undo,
        )

    def _apply_quarantine(
        self,
        iid: str,
        insight: dict[str, Any],
        attempts: int,
    ) -> Event:
        prior_status = insight.get("status")
        insight["status"] = "quarantined"
        undo = {
            "kind": "restore_quarantine",
            "insight_id": iid,
            "prior_status": prior_status,
        }
        return Event(
            rectifier_id=self.rectifier_id,
            event_type="r03_action_applied",
            action="quarantine_insight",
            details={"insight_id": iid, "attempts": attempts},
            undo=undo,
        )

    # ------------------------------------------------------------------- undo

    def apply_undo(self, undo: dict[str, Any], tree: dict[str, Any]) -> None:
        kind = undo.get("kind")
        insights = tree.get("insights", {})
        iid = undo.get("insight_id")
        insight = insights.get(iid) if iid is not None else None

        if kind == "restore_sources":
            if insight is None:
                return
            prior_sources = undo.get("prior_sources")
            if prior_sources is None:
                insight.pop("sources", None)
            else:
                insight["sources"] = list(prior_sources)
            return

        if kind == "restore_quarantine":
            if insight is None:
                return
            prior_status = undo.get("prior_status")
            if prior_status is None:
                insight.pop("status", None)
            else:
                insight["status"] = prior_status
            return

        raise ValueError(f"unknown undo kind: {kind!r}")

    # -------------------------------------------------------------- public api

    def unquarantine(self, insight_id: str, tree: dict[str, Any]) -> bool:
        insights = tree.get("insights", {})
        insight = insights.get(insight_id)
        if insight is None:
            return False
        if (insight.get("status") or "active") != "quarantined":
            return False
        insight["status"] = "active"
        return True


__all__ = ["InsightGroundingRectifier"]
