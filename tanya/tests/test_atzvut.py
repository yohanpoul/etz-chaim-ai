"""Tests — AtzvutManager (gestion de la tristesse systémique).

Vérifie : détection d'atzvut, vidouï time, transformation en simcha.
"""

import pytest

from tanya.atzvut import AtzvutManager, AtzvutState, AtzvutDiagnosis


@pytest.fixture
def manager():
    return AtzvutManager()


# ─── detect_atzvut ─────────────────────────────────────────


class TestDetectAtzvut:
    def test_no_problems_is_simcha(self, manager):
        result = manager.detect_atzvut({})
        assert result.state == AtzvutState.SIMCHA
        assert result.negative_count == 0

    def test_few_problems_is_merirut(self, manager):
        result = manager.detect_atzvut({
            "qliphoth_alerts": 2,
        })
        assert result.state == AtzvutState.MERIRUT
        assert result.negative_count == 2

    def test_many_problems_is_atzvut(self, manager):
        result = manager.detect_atzvut({
            "qliphoth_alerts": 3,
            "failed_insights": 2,
            "low_scores_count": 1,
        })
        assert result.state == AtzvutState.ATZVUT
        assert result.negative_count >= 5

    def test_returns_diagnosis(self, manager):
        result = manager.detect_atzvut({"qliphoth_alerts": 1})
        assert isinstance(result, AtzvutDiagnosis)
        assert isinstance(result.state, AtzvutState)
        assert isinstance(result.recommendation, str)
        assert result.recommendation  # non vide

    def test_atzvut_during_vidui_different_recommendation(self, manager):
        manager.enter_vidui()
        result = manager.detect_atzvut({
            "qliphoth_alerts": 5,
            "failed_insights": 3,
        })
        assert result.state == AtzvutState.ATZVUT
        assert result.is_vidui_time is True
        assert "Vidouï" in result.recommendation

    def test_atzvut_outside_vidui_says_stop(self, manager):
        result = manager.detect_atzvut({
            "qliphoth_alerts": 5,
            "failed_insights": 3,
        })
        assert result.state == AtzvutState.ATZVUT
        assert result.is_vidui_time is False
        assert "STOP" in result.recommendation


# ─── is_vidui_time ──────────────────────────────────────────


class TestVidui:
    def test_default_not_vidui(self, manager):
        assert manager.is_vidui_time() is False

    def test_enter_vidui(self, manager):
        manager.enter_vidui()
        assert manager.is_vidui_time() is True

    def test_exit_vidui(self, manager):
        manager.enter_vidui()
        manager.exit_vidui()
        assert manager.is_vidui_time() is False


# ─── should_skip_diagnostic ────────────────────────────────


class TestShouldSkipDiagnostic:
    def test_skip_during_avodah(self, manager):
        assert manager.should_skip_diagnostic("avodah") is True

    def test_skip_during_hitbonenut(self, manager):
        assert manager.should_skip_diagnostic("hitbonenut") is True

    def test_skip_during_response(self, manager):
        assert manager.should_skip_diagnostic("response") is True

    def test_allow_during_vidui(self, manager):
        assert manager.should_skip_diagnostic("vidui") is False

    def test_allow_during_daemon_report(self, manager):
        assert manager.should_skip_diagnostic("daemon_report") is False

    def test_allow_during_rapport(self, manager):
        assert manager.should_skip_diagnostic("rapport") is False


# ─── transform_atzvut_to_simcha ─────────────────────────────


class TestTransformToSimcha:
    def test_known_source(self, manager):
        result = manager.transform_atzvut_to_simcha("causal_engine_weak")
        assert "intention" in result
        assert "action_type" in result
        assert "priority" in result
        assert result["action_type"] == "explore_causal"

    def test_hitbonenut_low_is_high_priority(self, manager):
        result = manager.transform_atzvut_to_simcha("low_hitbonenut_score")
        assert result["priority"] == "high"

    def test_qliphoth_alerts_is_high_priority(self, manager):
        result = manager.transform_atzvut_to_simcha("too_many_qliphoth_alerts")
        assert result["priority"] == "high"

    def test_unknown_source_returns_generic(self, manager):
        result = manager.transform_atzvut_to_simcha("something_unknown")
        assert result["action_type"] == "generic_improvement"
        assert "something_unknown" in result["intention"]

    def test_all_known_sources_have_actions(self, manager):
        sources = [
            "causal_engine_weak",
            "low_hitbonenut_score",
            "too_many_qliphoth_alerts",
            "insight_rejection_rate_high",
            "low_birur_rate",
        ]
        for src in sources:
            result = manager.transform_atzvut_to_simcha(src)
            assert result["intention"]
            assert result["action_type"] != "generic_improvement"
