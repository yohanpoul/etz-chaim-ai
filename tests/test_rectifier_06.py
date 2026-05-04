"""Tests for ``etzchaim._internal.rectifiers.r06``.

Covers the contract documented in ``specs/04_rectifiers/06.md``:

* detection threshold (positive + negative)
* the ``recalibrate`` action branch (apply + skip when no improvement)
* idempotency on a second pass
* invariants : weights untouched, ``|T - 1.0| < 0.5``, reset restores 1.0
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
from etzchaim._internal.rectifiers.r06 import (
    DEFAULT_BRIER_THRESHOLD,
    DEFAULT_TEMPERATURE,
    DEFAULT_WINDOW,
    MAX_TEMPERATURE,
    MIN_TEMPERATURE,
    SelfModelOverconfidenceRectifier,
)


def _overconfident_predictions(
    n: int = 50,
    *,
    confidence: float = 0.9,
) -> list[dict]:
    """Return predictions that are overconfident at ``T=1``.

    Half are correct, half wrong, but the model claims ``confidence`` on
    every call. Brier at ``T=1`` is ``(c-1)^2/2 + c^2/2``.
    """
    predictions: list[dict] = []
    for i in range(n):
        outcome = 1.0 if i % 2 == 0 else 0.0
        predictions.append({"predicted": confidence, "outcome": outcome})
    return predictions


def _calibrated_predictions(n: int = 50) -> list[dict]:
    """Return well-calibrated predictions (Brier ~ 0)."""
    out: list[dict] = []
    for i in range(n):
        if i % 2 == 0:
            out.append({"predicted": 0.99, "outcome": 1.0})
        else:
            out.append({"predicted": 0.01, "outcome": 0.0})
    return out


def _tree(predictions: list[dict], *, temperature: float = 1.0) -> dict:
    return {
        "self_model": {
            "predictions": list(predictions),
            "temperature": temperature,
        }
    }


def test_subclasses_base_rectifier() -> None:
    assert issubclass(SelfModelOverconfidenceRectifier, BaseRectifier)
    rect = SelfModelOverconfidenceRectifier()
    assert rect.rectifier_id == "r06"
    assert rect.spec_ref == "SPEC-RECT-006"
    assert rect.brier_threshold == pytest.approx(DEFAULT_BRIER_THRESHOLD)
    assert rect.window == DEFAULT_WINDOW


def test_invalid_thresholds_rejected() -> None:
    with pytest.raises(ValueError):
        SelfModelOverconfidenceRectifier(brier_threshold=-0.1)
    with pytest.raises(ValueError):
        SelfModelOverconfidenceRectifier(brier_threshold=1.5)
    with pytest.raises(ValueError):
        SelfModelOverconfidenceRectifier(window=0)
    with pytest.raises(ValueError):
        SelfModelOverconfidenceRectifier(bins=0)


def test_detect_returns_empty_on_missing_self_model() -> None:
    rect = SelfModelOverconfidenceRectifier()
    assert rect.detect({}) == []
    assert rect.detect({"self_model": {}}) == []
    assert rect.detect({"self_model": {"predictions": []}}) == []


def test_detect_negative_when_brier_under_threshold() -> None:
    tree = _tree(_calibrated_predictions(n=50))
    assert SelfModelOverconfidenceRectifier().detect(tree) == []


def test_detect_positive_when_brier_over_threshold() -> None:
    tree = _tree(_overconfident_predictions(n=50, confidence=0.9))
    deviations = SelfModelOverconfidenceRectifier().detect(tree)
    assert len(deviations) == 1
    deviation = deviations[0]
    assert isinstance(deviation, Deviation)
    assert deviation.pattern == "selfmodel_overconfidence"
    assert deviation.metrics["predictions_window"] == 50
    assert deviation.metrics["brier_score"] > DEFAULT_BRIER_THRESHOLD
    assert deviation.metrics["current_temperature"] == pytest.approx(1.0)
    assert "calibration_curve_deviation" in deviation.metrics


def test_detect_window_caps_predictions_used() -> None:
    rect = SelfModelOverconfidenceRectifier(window=20)
    predictions = _calibrated_predictions(n=10) + _overconfident_predictions(n=20)
    tree = _tree(predictions)
    deviations = rect.detect(tree)
    assert len(deviations) == 1
    assert deviations[0].metrics["predictions_window"] == 20


def test_detect_skips_malformed_records() -> None:
    rect = SelfModelOverconfidenceRectifier()
    tree = {
        "self_model": {
            "predictions": [
                {"predicted": 1.5, "outcome": 1.0},  # confidence out of [0,1]
                {"predicted": 0.5, "outcome": 0.5},  # outcome not in {0,1}
                {"predicted": "bad", "outcome": 0.0},  # cannot coerce
                {"predicted": 0.9, "outcome": 0.0},  # valid
                {"outcome": 1.0},  # missing predicted
            ]
        }
    }
    deviations = rect.detect(tree)
    assert len(deviations) == 1
    assert deviations[0].metrics["predictions_window"] == 1


def test_observe_mode_logs_only() -> None:
    rect = SelfModelOverconfidenceRectifier()
    tree = _tree(_overconfident_predictions(n=40))
    deviations = rect.detect(tree)
    snapshot = copy.deepcopy(tree)
    events = rect.rectify(deviations, RectificationMode.OBSERVE)
    assert len(events) == 1
    assert events[0].event_type == "deviation_observed"
    assert events[0].undo is None
    assert tree == snapshot


def test_suggest_mode_emits_proposed_event() -> None:
    rect = SelfModelOverconfidenceRectifier()
    tree = _tree(_overconfident_predictions(n=40))
    deviations = rect.detect(tree)
    snapshot = copy.deepcopy(tree)
    events = rect.rectify(deviations, RectificationMode.SUGGEST)
    assert len(events) == 1
    event = events[0]
    assert event.event_type == "r06_action_proposed"
    assert event.action == "recalibrate"
    assert event.details["temperature_bounds"] == [
        MIN_TEMPERATURE,
        MAX_TEMPERATURE,
    ]
    assert tree == snapshot


def test_act_adjusts_temperature_within_bounds() -> None:
    rect = SelfModelOverconfidenceRectifier()
    tree = _tree(_overconfident_predictions(n=40, confidence=0.95))
    deviations = rect.detect(tree)
    events = rect.rectify(deviations, RectificationMode.ACT, tree=tree)
    assert len(events) == 1
    event = events[0]
    assert event.event_type == "r06_action_applied"
    assert event.action == "recalibrate"

    new_temperature = tree["self_model"]["temperature"]
    assert new_temperature != pytest.approx(DEFAULT_TEMPERATURE)
    assert abs(new_temperature - DEFAULT_TEMPERATURE) < 0.5
    assert MIN_TEMPERATURE < new_temperature < MAX_TEMPERATURE
    assert event.details["new_temperature"] == pytest.approx(new_temperature)
    assert event.details["calibration_delta"] >= 0.0
    assert event.details["brier_after"] <= event.details["brier_before"]
    assert event.undo is not None
    assert event.undo["kind"] == "restore_temperature"


def test_act_does_not_modify_underlying_predictions() -> None:
    """Invariant 1 : weights / inputs untouched, only output calibration."""
    rect = SelfModelOverconfidenceRectifier()
    original = _overconfident_predictions(n=40)
    tree = _tree(original)
    rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    assert tree["self_model"]["predictions"] == original


def test_act_records_calibration_history() -> None:
    rect = SelfModelOverconfidenceRectifier()
    tree = _tree(_overconfident_predictions(n=40))
    rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    history = tree["self_model"]["calibration_history"]
    assert len(history) == 1
    entry = history[0]
    assert entry["prior_temperature"] == pytest.approx(DEFAULT_TEMPERATURE)
    assert entry["new_temperature"] == pytest.approx(
        tree["self_model"]["temperature"]
    )
    assert entry["calibration_delta"] >= 0.0


def test_act_skips_when_no_temperature_improves() -> None:
    """If the deviation payload is already optimal, ``act`` skips."""
    rect = SelfModelOverconfidenceRectifier()
    deviation = Deviation(
        rectifier_id="r06",
        pattern="selfmodel_overconfidence",
        metrics={},
        spec_ref="SPEC-RECT-006",
        payload={
            "predictions": _calibrated_predictions(n=40),
            "current_temperature": DEFAULT_TEMPERATURE,
        },
    )
    tree: dict = {"self_model": {"temperature": DEFAULT_TEMPERATURE}}
    events = rect.rectify([deviation], RectificationMode.ACT, tree=tree)
    assert len(events) == 1
    assert events[0].event_type == "r06_action_skipped"
    assert events[0].details["reason"] == "no_improvement"
    assert tree["self_model"]["temperature"] == pytest.approx(
        DEFAULT_TEMPERATURE
    )


def test_act_idempotent_on_second_pass() -> None:
    rect = SelfModelOverconfidenceRectifier()
    tree = _tree(_overconfident_predictions(n=40, confidence=0.85))
    rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    first_temperature = tree["self_model"]["temperature"]
    snapshot = copy.deepcopy(tree)

    second_deviations = rect.detect(tree)
    rect.rectify(second_deviations, RectificationMode.ACT, tree=tree)
    assert tree["self_model"]["temperature"] == pytest.approx(
        first_temperature
    )
    if not second_deviations:
        assert tree == snapshot


def test_undo_restores_prior_temperature_and_history() -> None:
    rect = SelfModelOverconfidenceRectifier()
    tree = _tree(_overconfident_predictions(n=40))
    events = rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    applied = events[0]
    rect.apply_undo(applied.undo, tree)
    assert tree["self_model"]["temperature"] == pytest.approx(
        DEFAULT_TEMPERATURE
    )
    assert tree["self_model"]["calibration_history"] == []


def test_undo_rejects_unknown_kind() -> None:
    rect = SelfModelOverconfidenceRectifier()
    with pytest.raises(ValueError):
        rect.apply_undo({"kind": "bogus"}, {"self_model": {}})


def test_reset_calibration_restores_baseline() -> None:
    rect = SelfModelOverconfidenceRectifier()
    tree = _tree(_overconfident_predictions(n=40), temperature=1.4)
    rect.reset_calibration(tree)
    assert tree["self_model"]["temperature"] == pytest.approx(
        DEFAULT_TEMPERATURE
    )


def test_rectify_rejects_unknown_mode() -> None:
    rect = SelfModelOverconfidenceRectifier()
    with pytest.raises(ValueError):
        rect.rectify([], "bogus")


def test_act_mode_requires_tree() -> None:
    rect = SelfModelOverconfidenceRectifier()
    tree = _tree(_overconfident_predictions(n=40))
    deviations = rect.detect(tree)
    with pytest.raises(ValueError):
        rect.rectify(deviations, RectificationMode.ACT, tree=None)


def test_act_event_has_undo_recipe() -> None:
    rect = SelfModelOverconfidenceRectifier()
    tree = _tree(_overconfident_predictions(n=40))
    events = rect.rectify(rect.detect(tree), RectificationMode.ACT, tree=tree)
    assert isinstance(events[0], Event)
    assert events[0].undo is not None
    assert "prior_temperature" in events[0].undo
