"""Tests du Tuner — apprentissage de seuils par feedback qualité."""

import pytest

from omer.tuner import (
    ThresholdState,
    TuneResult,
    compute_adjustment,
    run_tuning_cycle,
    apply_tune_results,
    MAX_ADJUSTMENT,
    MIN_SAMPLES,
)


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def quality_threshold():
    return ThresholdState(
        name="quality_threshold",
        module="autojudge",
        attr="quality_threshold",
        current=0.6,
        floor=0.4,
        ceiling=0.85,
    )


@pytest.fixture
def low_outcomes():
    """Outcomes de basse qualité → seuil trop restrictif."""
    return [{"quality": 0.3} for _ in range(30)]


@pytest.fixture
def high_outcomes():
    """Outcomes de haute qualité → seuil peut monter."""
    return [{"quality": 0.8} for _ in range(30)]


@pytest.fixture
def medium_outcomes():
    """Outcomes moyens → stable."""
    return [{"quality": 0.6} for _ in range(30)]


# ── Tests compute_adjustment ──────────────────────────────

class TestComputeAdjustment:

    def test_insufficient_samples_stays_stable(self, quality_threshold):
        outcomes = [{"quality": 0.3} for _ in range(5)]
        result = compute_adjustment(outcomes, quality_threshold)
        assert result.direction == "stable"
        assert result.new_value == quality_threshold.current

    def test_low_quality_lowers_threshold(self, quality_threshold, low_outcomes):
        result = compute_adjustment(low_outcomes, quality_threshold)
        assert result.direction == "down"
        assert result.new_value < quality_threshold.current
        assert result.new_value == quality_threshold.current - MAX_ADJUSTMENT

    def test_high_quality_raises_threshold(self, quality_threshold, high_outcomes):
        result = compute_adjustment(high_outcomes, quality_threshold)
        assert result.direction == "up"
        assert result.new_value > quality_threshold.current
        assert result.new_value == quality_threshold.current + MAX_ADJUSTMENT

    def test_medium_quality_stays_stable(self, quality_threshold, medium_outcomes):
        result = compute_adjustment(medium_outcomes, quality_threshold)
        assert result.direction == "stable"
        assert result.new_value == quality_threshold.current

    def test_respects_floor(self, low_outcomes):
        t = ThresholdState(
            name="test", module="m", attr="a",
            current=0.41, floor=0.4, ceiling=0.9,
        )
        result = compute_adjustment(low_outcomes, t)
        assert result.new_value >= t.floor

    def test_respects_ceiling(self, high_outcomes):
        t = ThresholdState(
            name="test", module="m", attr="a",
            current=0.84, floor=0.1, ceiling=0.85,
        )
        result = compute_adjustment(high_outcomes, t)
        assert result.new_value <= t.ceiling

    def test_max_adjustment_bounded(self, quality_threshold, low_outcomes):
        result = compute_adjustment(low_outcomes, quality_threshold)
        delta = abs(result.new_value - result.old_value)
        assert delta <= MAX_ADJUSTMENT + 0.001

    def test_result_has_all_fields(self, quality_threshold, low_outcomes):
        result = compute_adjustment(low_outcomes, quality_threshold)
        assert isinstance(result, TuneResult)
        assert result.threshold == "quality_threshold"
        assert result.n_samples == 30
        assert result.avg_quality > 0


# ── Tests run_tuning_cycle ────────────────────────────────

class TestRunTuningCycle:

    def test_returns_one_result_per_threshold(self, medium_outcomes):
        results = run_tuning_cycle(outcomes=medium_outcomes)
        assert len(results) == 3  # 3 tracked thresholds

    def test_all_stable_on_medium(self, medium_outcomes):
        results = run_tuning_cycle(outcomes=medium_outcomes)
        for r in results:
            assert r.direction == "stable"

    def test_all_down_on_low(self, low_outcomes):
        results = run_tuning_cycle(outcomes=low_outcomes)
        down_count = sum(1 for r in results if r.direction == "down")
        assert down_count >= 1  # au moins un seuil baisse

    def test_custom_thresholds(self, high_outcomes):
        custom = [ThresholdState(
            name="custom", module="m", attr="a",
            current=0.5, floor=0.1, ceiling=0.9,
        )]
        results = run_tuning_cycle(outcomes=high_outcomes, thresholds=custom)
        assert len(results) == 1
        assert results[0].threshold == "custom"

    def test_empty_outcomes_all_stable(self):
        results = run_tuning_cycle(outcomes=[])
        for r in results:
            assert r.direction == "stable"


# ── Tests apply_tune_results ──────────────────────────────

class TestApplyTuneResults:

    def test_apply_changes_attribute(self):
        class FakeModule:
            quality_threshold = 0.6
        tree = {"gevurah": FakeModule()}
        results = [TuneResult(
            threshold="quality_threshold",
            old_value=0.6, new_value=0.58,
            direction="down", reason="test",
            n_samples=30, avg_quality=0.4,
        )]
        changes = apply_tune_results(tree, results)
        assert len(changes) == 1
        assert tree["gevurah"].quality_threshold == 0.58

    def test_stable_results_not_applied(self):
        tree = {}
        results = [TuneResult(
            threshold="quality_threshold",
            old_value=0.6, new_value=0.6,
            direction="stable", reason="ok",
            n_samples=30, avg_quality=0.6,
        )]
        changes = apply_tune_results(tree, results)
        assert len(changes) == 0

    def test_decline_threshold_applied(self):
        class FakeMap:
            decline_threshold = 0.3
        tree = {"hod": FakeMap()}
        results = [TuneResult(
            threshold="decline_threshold",
            old_value=0.3, new_value=0.28,
            direction="down", reason="test",
            n_samples=30, avg_quality=0.4,
        )]
        changes = apply_tune_results(tree, results)
        assert tree["hod"].decline_threshold == 0.28
