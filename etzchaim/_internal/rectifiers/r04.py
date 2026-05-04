"""Rectifier 04 — Goal Drift.

Detects active intentions whose embedding has drifted from the mission
north star beyond a configurable cosine-distance threshold, and proposes
(or applies, in ``act`` mode) a parking pass that flags the outliers
``pending_alignment`` and emits a review request to the Tension faculty.

Internal: SPEC-RECT-004 — see ``specs/04_rectifiers/04.md``.
"""
from __future__ import annotations

import hashlib
import math
import time
import uuid
from collections import Counter
from typing import Any, Callable, Mapping, Sequence

from etzchaim._internal.rectifiers.base import (
    BaseRectifier,
    Deviation,
    Event,
    RectificationMode,
)

DEFAULT_DRIFT_THRESHOLD: float = 0.4
PARKED_STATUS: str = "pending_alignment"

EmbedFn = Callable[[str], Mapping[str, float] | Sequence[float]]


def _now() -> float:
    return time.time()


def _default_embed(text: str) -> Counter:
    """Lower-cased word bag-of-words counter used as a default embedding."""
    return Counter((text or "").lower().split())


def _hash_mission(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _to_mapping(vec: Mapping[str, float] | Sequence[float]) -> dict[Any, float]:
    if isinstance(vec, Mapping):
        return {k: float(v) for k, v in vec.items()}
    return {i: float(v) for i, v in enumerate(vec)}


def _cosine_distance(
    a: Mapping[str, float] | Sequence[float],
    b: Mapping[str, float] | Sequence[float],
) -> float:
    """Cosine distance in [0, 1]; 1.0 when either side is empty."""
    ma = _to_mapping(a)
    mb = _to_mapping(b)
    if not ma or not mb:
        return 1.0
    keys = set(ma) | set(mb)
    dot = sum(ma.get(k, 0.0) * mb.get(k, 0.0) for k in keys)
    norm_a = math.sqrt(sum(v * v for v in ma.values()))
    norm_b = math.sqrt(sum(v * v for v in mb.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 1.0
    similarity = dot / (norm_a * norm_b)
    similarity = max(-1.0, min(1.0, similarity))
    return max(0.0, min(1.0, 1.0 - similarity))


# Internal: tikkun_4 — Tikkunei Dikna Tikkun 4.


class GoalDriftRectifier(BaseRectifier):
    """Park intentions whose distance to the mission exceeds the threshold.

    The rectifier reads ``tree['intentions']`` (a mapping of id → intention)
    and ``tree['mission_text']``. It never deletes intentions; ``act`` mode
    only flips ``status`` to ``pending_alignment`` and appends a review
    request to ``tree['tension_requests']``. A mission text change resets
    the parking baseline so previously-parked intentions become eligible
    for a fresh evaluation.
    """

    rectifier_id: str = "r04"
    spec_ref: str = "SPEC-RECT-004"

    def __init__(
        self,
        *,
        embed_fn: EmbedFn | None = None,
        threshold: float = DEFAULT_DRIFT_THRESHOLD,
        now_fn: Callable[[], float] = _now,
    ) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be in [0, 1]")
        self._embed_fn: EmbedFn = embed_fn if embed_fn is not None else _default_embed
        self._threshold = float(threshold)
        self._now = now_fn

    @property
    def threshold(self) -> float:
        return self._threshold

    def detect(self, tree: dict[str, Any]) -> list[Deviation]:
        intentions = tree.get("intentions", {}) or {}
        mission_text = tree.get("mission_text") or ""
        if not intentions or not mission_text:
            return []

        current_hash = _hash_mission(mission_text)
        mission_vec = self._embed_fn(mission_text)

        evaluable: list[tuple[str, dict[str, Any]]] = []
        for iid, intention in intentions.items():
            status = intention.get("status") or "active"
            aligned_hash = intention.get("aligned_to_mission_hash")
            if status == PARKED_STATUS and aligned_hash == current_hash:
                continue
            if status not in ("active", PARKED_STATUS):
                continue
            evaluable.append((iid, intention))

        if not evaluable:
            return []

        outliers: list[dict[str, Any]] = []
        max_distance = 0.0
        for iid, intention in evaluable:
            text = intention.get("text") or ""
            distance = _cosine_distance(self._embed_fn(text), mission_vec)
            max_distance = max(max_distance, distance)
            if distance > self._threshold:
                outliers.append({"id": iid, "distance": distance})

        active_count = len(evaluable)
        avg_distance = (
            sum(_cosine_distance(self._embed_fn(i.get("text") or ""), mission_vec)
                for _, i in evaluable) / active_count
        )

        if not outliers:
            return []

        outliers.sort(key=lambda o: (-o["distance"], o["id"]))
        return [
            Deviation(
                rectifier_id=self.rectifier_id,
                pattern="goal_drift",
                metrics={
                    "active_intentions": active_count,
                    "avg_distance_to_mission": avg_distance,
                    "max_distance_to_mission": max_distance,
                    "outlier_intentions": [o["id"] for o in outliers],
                    "threshold": self._threshold,
                    "mission_hash": current_hash,
                },
                spec_ref=self.spec_ref,
                payload={
                    "outliers": outliers,
                    "mission_hash": current_hash,
                },
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

            outliers = list(deviation.payload.get("outliers", []))
            mission_hash = deviation.payload.get("mission_hash")

            if mode == RectificationMode.SUGGEST:
                events.append(
                    Event(
                        rectifier_id=self.rectifier_id,
                        event_type="r04_action_proposed",
                        action="park_outliers",
                        details={
                            "outlier_intentions": [o["id"] for o in outliers],
                            "threshold": self._threshold,
                            "metrics": dict(deviation.metrics),
                        },
                    )
                )
                continue

            if mode == RectificationMode.ACT:
                if tree is None:
                    raise ValueError("act mode requires a tree to mutate")
                events.extend(self._apply_act(outliers, mission_hash, tree))

        return events

    def _apply_act(
        self,
        outliers: list[dict[str, Any]],
        mission_hash: str | None,
        tree: dict[str, Any],
    ) -> list[Event]:
        intentions = tree.setdefault("intentions", {})
        events: list[Event] = []
        current_hash = mission_hash or _hash_mission(tree.get("mission_text") or "")

        for outlier in outliers:
            iid = outlier["id"]
            intention = intentions.get(iid)
            if intention is None:
                continue

            status = intention.get("status") or "active"
            aligned_hash = intention.get("aligned_to_mission_hash")
            if status == PARKED_STATUS and aligned_hash == current_hash:
                events.append(
                    Event(
                        rectifier_id=self.rectifier_id,
                        event_type="r04_action_skipped",
                        action="park_outlier",
                        details={"intention_id": iid, "reason": "idempotent"},
                    )
                )
                continue

            prior_status = intention.get("status")
            prior_aligned = intention.get("aligned_to_mission_hash")
            intention["status"] = PARKED_STATUS
            intention["aligned_to_mission_hash"] = current_hash

            request_id = f"t-{uuid.uuid4().hex[:8]}"
            tree.setdefault("tension_requests", []).append(
                {
                    "id": request_id,
                    "kind": "alignment_review",
                    "intention_id": iid,
                    "distance": float(outlier.get("distance", 0.0)),
                    "mission_hash": current_hash,
                    "opened_at": float(self._now()),
                }
            )

            undo = {
                "kind": "restore_intention",
                "intention_id": iid,
                "prior_status": prior_status,
                "prior_aligned_hash": prior_aligned,
                "request_id": request_id,
            }
            events.append(
                Event(
                    rectifier_id=self.rectifier_id,
                    event_type="r04_action_applied",
                    action="park_outlier",
                    details={
                        "intention_id": iid,
                        "distance": float(outlier.get("distance", 0.0)),
                        "request_id": request_id,
                    },
                    undo=undo,
                )
            )

        return events

    def apply_undo(self, undo: dict[str, Any], tree: dict[str, Any]) -> None:
        kind = undo.get("kind")
        if kind != "restore_intention":
            raise ValueError(f"unknown undo kind: {kind!r}")

        intentions = tree.get("intentions", {})
        iid = undo.get("intention_id")
        intention = intentions.get(iid) if iid is not None else None
        if intention is not None:
            prior_status = undo.get("prior_status")
            if prior_status is None:
                intention.pop("status", None)
            else:
                intention["status"] = prior_status

            prior_aligned = undo.get("prior_aligned_hash")
            if prior_aligned is None:
                intention.pop("aligned_to_mission_hash", None)
            else:
                intention["aligned_to_mission_hash"] = prior_aligned

        request_id = undo.get("request_id")
        if request_id is not None:
            requests = tree.get("tension_requests", [])
            tree["tension_requests"] = [
                r for r in requests if r.get("id") != request_id
            ]

    def apply_mission_change(self, tree: dict[str, Any]) -> int:
        """Clear parking flags whose mission hash no longer matches.

        Returns the number of intentions whose ``pending_alignment`` flag
        was lifted. The rectifier itself stays stateless; the mission hash
        lives on each parked intention.
        """
        intentions = tree.get("intentions", {}) or {}
        mission_text = tree.get("mission_text") or ""
        current_hash = _hash_mission(mission_text)
        cleared = 0
        for intention in intentions.values():
            status = intention.get("status")
            aligned = intention.get("aligned_to_mission_hash")
            if status == PARKED_STATUS and aligned != current_hash:
                intention["status"] = "active"
                intention.pop("aligned_to_mission_hash", None)
                cleared += 1
        return cleared


__all__ = ["GoalDriftRectifier", "DEFAULT_DRIFT_THRESHOLD", "PARKED_STATUS"]
