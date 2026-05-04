"""Rectifier 06 — Self-Model Overconfidence.

Detects miscalibration of the self-model's confidence head : when the
Brier score on the recent prediction window exceeds a threshold, the
self-model is treating uncertain calls as confident ones. In ``act``
mode, the rectifier picks a temperature in ``(0.5, 1.5)`` that minimises
the Brier score over the same window and writes it to
``tree['self_model']['temperature']``. The underlying model weights are
never touched ; only the post-hoc calibration value.

Internal: SPEC-RECT-006 — see ``specs/04_rectifiers/06.md``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable

from etzchaim._internal.rectifiers.base import (
    BaseRectifier,
    Deviation,
    Event,
    RectificationMode,
)

DEFAULT_BRIER_THRESHOLD: float = 0.25
DEFAULT_WINDOW: int = 100
DEFAULT_BINS: int = 10
DEFAULT_TEMPERATURE: float = 1.0
TEMPERATURE_BOUND: float = 0.5
MIN_TEMPERATURE: float = DEFAULT_TEMPERATURE - TEMPERATURE_BOUND
MAX_TEMPERATURE: float = DEFAULT_TEMPERATURE + TEMPERATURE_BOUND
TEMPERATURE_EPSILON: float = 1e-3
GRID_STEP: float = 0.05
SECONDS_PER_DAY: float = 86_400.0


@dataclass(frozen=True)
class _Prediction:
    confidence: float
    outcome: float
    timestamp: float | None


def _coerce_predictions(
    raw: Iterable[dict[str, Any]] | None,
) -> list[_Prediction]:
    if not raw:
        return []
    out: list[_Prediction] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        if "predicted" not in entry or "outcome" not in entry:
            continue
        try:
            confidence = float(entry["predicted"])
            outcome = float(entry["outcome"])
        except (TypeError, ValueError):
            continue
        if not 0.0 <= confidence <= 1.0:
            continue
        if outcome not in (0.0, 1.0):
            continue
        ts = entry.get("timestamp")
        out.append(
            _Prediction(
                confidence=confidence,
                outcome=outcome,
                timestamp=float(ts) if ts is not None else None,
            )
        )
    return out


def _temperature_scale(p: float, temperature: float) -> float:
    """Apply temperature scaling to a probability.

    ``temperature == 1`` is the identity ; ``> 1`` softens (less
    confident), ``< 1`` sharpens (more confident).
    """
    if temperature <= 0.0:
        raise ValueError("temperature must be > 0")
    if temperature == 1.0:
        return p
    clipped = min(max(p, 1e-9), 1.0 - 1e-9)
    logit = math.log(clipped / (1.0 - clipped))
    return 1.0 / (1.0 + math.exp(-logit / temperature))


def _brier(predictions: list[_Prediction], temperature: float) -> float:
    if not predictions:
        return 0.0
    total = 0.0
    for entry in predictions:
        scaled = _temperature_scale(entry.confidence, temperature)
        total += (scaled - entry.outcome) ** 2
    return total / len(predictions)


def _calibration_curve_deviation(
    predictions: list[_Prediction],
    temperature: float,
    bins: int = DEFAULT_BINS,
) -> float:
    if not predictions or bins <= 0:
        return 0.0
    bucket_conf: list[float] = [0.0] * bins
    bucket_acc: list[float] = [0.0] * bins
    bucket_n: list[int] = [0] * bins
    for entry in predictions:
        scaled = _temperature_scale(entry.confidence, temperature)
        idx = min(int(scaled * bins), bins - 1)
        bucket_conf[idx] += scaled
        bucket_acc[idx] += entry.outcome
        bucket_n[idx] += 1
    total = len(predictions)
    weighted = 0.0
    for i in range(bins):
        n = bucket_n[i]
        if n == 0:
            continue
        gap = abs((bucket_conf[i] / n) - (bucket_acc[i] / n))
        weighted += gap * (n / total)
    return weighted


def _predictions_24h(
    predictions: list[_Prediction],
    now: float | None,
) -> int:
    if now is None:
        return sum(1 for p in predictions if p.timestamp is not None)
    cutoff = now - SECONDS_PER_DAY
    count = 0
    for entry in predictions:
        if entry.timestamp is None:
            continue
        if entry.timestamp >= cutoff:
            count += 1
    return count


# Internal: tikkun_6 — Tikkunei Dikna Tikkun 6.


class SelfModelOverconfidenceRectifier(BaseRectifier):
    """Rein in an overconfident self-model via output-side calibration.

    The rectifier reads ``tree['self_model']`` :

    * ``predictions`` — list of ``{"predicted": float, "outcome": 0|1,
      "timestamp": float?}`` records.
    * ``temperature`` — current calibration scalar (defaults to ``1.0``).

    Detection fires when the Brier score, computed under the current
    temperature on the trailing window, exceeds ``brier_threshold``.
    """

    rectifier_id: str = "r06"
    spec_ref: str = "SPEC-RECT-006"

    def __init__(
        self,
        *,
        brier_threshold: float = DEFAULT_BRIER_THRESHOLD,
        window: int = DEFAULT_WINDOW,
        bins: int = DEFAULT_BINS,
    ) -> None:
        if brier_threshold < 0.0 or brier_threshold > 1.0:
            raise ValueError("brier_threshold must be within [0, 1]")
        if window <= 0:
            raise ValueError("window must be > 0")
        if bins <= 0:
            raise ValueError("bins must be > 0")
        self._brier_threshold = float(brier_threshold)
        self._window = int(window)
        self._bins = int(bins)

    @property
    def brier_threshold(self) -> float:
        return self._brier_threshold

    @property
    def window(self) -> int:
        return self._window

    def detect(self, tree: dict[str, Any]) -> list[Deviation]:
        self_model = tree.get("self_model") or {}
        predictions_all = _coerce_predictions(self_model.get("predictions"))
        if not predictions_all:
            return []
        predictions = predictions_all[-self._window :]
        if not predictions:
            return []
        temperature = float(self_model.get("temperature", DEFAULT_TEMPERATURE))
        brier = _brier(predictions, temperature)
        if brier <= self._brier_threshold:
            return []
        deviation_curve = _calibration_curve_deviation(
            predictions, temperature, self._bins
        )
        latest_ts = max(
            (p.timestamp for p in predictions if p.timestamp is not None),
            default=None,
        )
        metrics = {
            "predictions_window": len(predictions),
            "predictions_24h": _predictions_24h(predictions, latest_ts),
            "brier_score": brier,
            "calibration_curve_deviation": deviation_curve,
            "current_temperature": temperature,
            "brier_threshold": self._brier_threshold,
        }
        payload = {
            "predictions": [
                {
                    "predicted": p.confidence,
                    "outcome": p.outcome,
                    "timestamp": p.timestamp,
                }
                for p in predictions
            ],
            "current_temperature": temperature,
        }
        return [
            Deviation(
                rectifier_id=self.rectifier_id,
                pattern="selfmodel_overconfidence",
                metrics=metrics,
                spec_ref=self.spec_ref,
                payload=payload,
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

            if mode == RectificationMode.SUGGEST:
                events.append(
                    Event(
                        rectifier_id=self.rectifier_id,
                        event_type="r06_action_proposed",
                        action="recalibrate",
                        details={
                            "metrics": dict(deviation.metrics),
                            "temperature_bounds": [
                                MIN_TEMPERATURE,
                                MAX_TEMPERATURE,
                            ],
                        },
                    )
                )
                continue

            if mode == RectificationMode.ACT:
                if tree is None:
                    raise ValueError("act mode requires a tree to mutate")
                events.append(self._apply_act(deviation, tree))

        return events

    def _apply_act(
        self,
        deviation: Deviation,
        tree: dict[str, Any],
    ) -> Event:
        predictions = _coerce_predictions(deviation.payload.get("predictions"))
        prior_temperature = float(deviation.payload.get("current_temperature", DEFAULT_TEMPERATURE))
        target_temperature, brier_after = self._search_best_temperature(
            predictions, prior_temperature
        )
        brier_before = _brier(predictions, prior_temperature)
        delta = brier_before - brier_after

        if abs(target_temperature - prior_temperature) < TEMPERATURE_EPSILON:
            return Event(
                rectifier_id=self.rectifier_id,
                event_type="r06_action_skipped",
                action="recalibrate",
                details={
                    "reason": "no_improvement",
                    "temperature": prior_temperature,
                    "brier_before": brier_before,
                    "brier_after": brier_after,
                },
            )

        if not _within_bounds(target_temperature):
            return Event(
                rectifier_id=self.rectifier_id,
                event_type="r06_action_skipped",
                action="recalibrate",
                details={
                    "reason": "out_of_bounds",
                    "temperature": prior_temperature,
                    "candidate_temperature": target_temperature,
                },
            )

        self_model = tree.setdefault("self_model", {})
        self_model["temperature"] = target_temperature
        history = self_model.setdefault("calibration_history", [])
        history.append(
            {
                "prior_temperature": prior_temperature,
                "new_temperature": target_temperature,
                "brier_before": brier_before,
                "brier_after": brier_after,
                "calibration_delta": delta,
            }
        )

        undo = {
            "kind": "restore_temperature",
            "prior_temperature": prior_temperature,
            "history_index": len(history) - 1,
        }
        return Event(
            rectifier_id=self.rectifier_id,
            event_type="r06_action_applied",
            action="recalibrate",
            details={
                "prior_temperature": prior_temperature,
                "new_temperature": target_temperature,
                "brier_before": brier_before,
                "brier_after": brier_after,
                "calibration_delta": delta,
            },
            undo=undo,
        )

    def _search_best_temperature(
        self,
        predictions: list[_Prediction],
        prior_temperature: float,
    ) -> tuple[float, float]:
        best_t = prior_temperature
        best_brier = _brier(predictions, prior_temperature)
        if not predictions:
            return best_t, best_brier
        candidates = _temperature_grid(prior_temperature)
        for t in candidates:
            score = _brier(predictions, t)
            if score + TEMPERATURE_EPSILON < best_brier:
                best_brier = score
                best_t = t
        return best_t, best_brier

    def apply_undo(self, undo: dict[str, Any], tree: dict[str, Any]) -> None:
        kind = undo.get("kind")
        if kind == "restore_temperature":
            self_model = tree.setdefault("self_model", {})
            self_model["temperature"] = float(
                undo.get("prior_temperature", DEFAULT_TEMPERATURE)
            )
            history = self_model.get("calibration_history")
            idx = undo.get("history_index")
            if isinstance(history, list) and isinstance(idx, int):
                if 0 <= idx < len(history):
                    history.pop(idx)
            return
        raise ValueError(f"unknown undo kind: {kind!r}")

    def reset_calibration(self, tree: dict[str, Any]) -> None:
        """Restore the self-model temperature to the neutral baseline."""
        self_model = tree.setdefault("self_model", {})
        self_model["temperature"] = DEFAULT_TEMPERATURE


def _within_bounds(temperature: float) -> bool:
    return abs(temperature - DEFAULT_TEMPERATURE) < TEMPERATURE_BOUND


def _temperature_grid(prior: float) -> list[float]:
    grid: list[float] = []
    t = MIN_TEMPERATURE + GRID_STEP
    while t < MAX_TEMPERATURE:
        if abs(t - prior) >= TEMPERATURE_EPSILON:
            grid.append(round(t, 6))
        t += GRID_STEP
    return grid


__all__ = [
    "SelfModelOverconfidenceRectifier",
    "DEFAULT_BRIER_THRESHOLD",
    "DEFAULT_WINDOW",
    "DEFAULT_TEMPERATURE",
    "MIN_TEMPERATURE",
    "MAX_TEMPERATURE",
]
