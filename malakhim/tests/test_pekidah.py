"""Tests PekidahRegistry — registre de compétence + IYM + kategor/praklite."""

import pytest

from malakhim.models import MalakhStage
from malakhim.pekidah.registry import PekidahRegistry


# ── Registration ────────────────────────────────────────────────────────────


class TestPekidahRegistration:
    def test_register_agent(self):
        reg = PekidahRegistry()
        profile = reg.register("agent-1", ["code", "analysis"])
        assert profile.agent_id == "agent-1"
        assert profile.stage == MalakhStage.IBUR
        assert set(profile.domains) == {"code", "analysis"}

    def test_register_duplicate_returns_existing(self):
        reg = PekidahRegistry()
        p1 = reg.register("agent-1", ["code"])
        p2 = reg.register("agent-1", ["code", "analysis"])
        assert p1 is p2
        # Domains should NOT be updated on duplicate registration
        assert p1.domains == ["code"]


# ── Compétence ──────────────────────────────────────────────────────────────


class TestPekidahCompetence:
    def test_initial_score(self):
        reg = PekidahRegistry()
        reg.register("agent-1", ["code"])
        assert reg.get_score("agent-1", "code") == 0.5

    def test_can_handle_above_threshold(self):
        reg = PekidahRegistry()
        reg.register("agent-1", ["code"])
        assert reg.can_handle("agent-1", "code", min_score=0.3) is True

    def test_cannot_handle_below_threshold(self):
        reg = PekidahRegistry()
        reg.register("agent-1", ["code"])
        assert reg.can_handle("agent-1", "code", min_score=0.8) is False

    def test_cannot_handle_unknown_domain(self):
        reg = PekidahRegistry()
        reg.register("agent-1", ["code"])
        assert reg.can_handle("agent-1", "painting") is False

    def test_record_outcome_updates_score(self):
        reg = PekidahRegistry()
        reg.register("agent-1", ["code"])
        reg.record_outcome("agent-1", "code", score=0.9)
        # EMA: 0.2 * 0.9 + 0.8 * 0.5 = 0.18 + 0.40 = 0.58
        assert abs(reg.get_score("agent-1", "code") - 0.58) < 1e-9

    def test_record_multiple_outcomes(self):
        reg = PekidahRegistry()
        reg.register("agent-1", ["code"])
        for _ in range(5):
            reg.record_outcome("agent-1", "code", score=0.9)
        assert reg.get_score("agent-1", "code") > 0.7


# ── Maturation IYM ──────────────────────────────────────────────────────────


class TestPekidahMaturation:
    def test_starts_as_ibur(self):
        reg = PekidahRegistry()
        profile = reg.register("agent-1", ["code"])
        assert profile.stage == MalakhStage.IBUR

    def test_reaches_yenikah(self):
        reg = PekidahRegistry()
        reg.register("agent-1", ["code"])
        for _ in range(12):
            reg.record_outcome("agent-1", "code", score=0.5)
        profile = reg._agents["agent-1"]
        assert profile.stage == MalakhStage.YENIKAH

    def test_reaches_mochin(self):
        reg = PekidahRegistry()
        reg.register("agent-1", ["code"])
        for _ in range(55):
            reg.record_outcome("agent-1", "code", score=0.8)
        profile = reg._agents["agent-1"]
        assert profile.stage == MalakhStage.MOCHIN

    def test_regression_to_ibur(self):
        reg = PekidahRegistry()
        reg.register("agent-1", ["code"])
        # Monter en yenikah
        for _ in range(12):
            reg.record_outcome("agent-1", "code", score=0.5)
        assert reg._agents["agent-1"].stage == MalakhStage.YENIKAH
        # Faire chuter le score
        for _ in range(10):
            reg.record_outcome("agent-1", "code", score=0.1)
        assert reg._agents["agent-1"].stage == MalakhStage.IBUR


# ── Kategor ─────────────────────────────────────────────────────────────────


class TestPekidahKategor:
    def test_record_failure(self):
        reg = PekidahRegistry()
        pattern = reg.record_failure(
            "agent-1", "code", "timeout",
            "please analyze this complex code structure", 0.2,
        )
        assert pattern.active is True
        assert pattern.error_type == "timeout"
        assert pattern.domain == "code"
        assert len(pattern.prompt_keywords) > 0

    def test_check_before_execution(self):
        reg = PekidahRegistry()
        reg.record_failure(
            "agent-1", "code", "timeout",
            "please analyze this complex code structure", 0.2,
        )
        matches = reg.check_failures(
            "agent-1", "code",
            "analyze this complex code structure please",
        )
        assert len(matches) == 1
        assert matches[0].error_type == "timeout"

    def test_resolve_failure(self):
        reg = PekidahRegistry()
        pattern = reg.record_failure(
            "agent-1", "code", "timeout",
            "please analyze this complex code structure", 0.2,
        )
        reg.resolve_failure(pattern.pattern_id, "increased timeout to 60s")
        matches = reg.check_failures(
            "agent-1", "code",
            "analyze this complex code structure please",
        )
        assert len(matches) == 0


# ── Praklite ────────────────────────────────────────────────────────────────


class TestPekidahPraklite:
    def test_record_success(self):
        reg = PekidahRegistry()
        pattern = reg.record_success(
            "agent-1", "code", "chain-of-thought",
            {"focus": "clarity"}, 0.9,
        )
        assert pattern.domain == "code"
        assert pattern.score == 0.9
        assert pattern.strategy_used == "chain-of-thought"

    def test_get_best_strategies(self):
        reg = PekidahRegistry()
        reg.record_success("a1", "code", "cot", None, 0.7)
        reg.record_success("a2", "code", "few-shot", None, 0.9)
        reg.record_success("a3", "code", "direct", None, 0.5)

        best = reg.get_best_strategies("code", limit=2)
        assert len(best) == 2
        assert best[0].score == 0.9
        assert best[1].score == 0.7
