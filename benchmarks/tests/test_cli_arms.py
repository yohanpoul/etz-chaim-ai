"""Tests offline pour benchmarks/arms.py — instantiation + cache flow.

Live tests requièrent Claude CLI OAuth-loggué et sont skipped par défaut.
Ces tests valident :
- Tous les 3 arms instanciables
- Cache hit short-circuits CLI subprocess (pas d'appel réseau)
- ArmResult format consistent
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from benchmarks.arms import (
    ALL_ARMS,
    ArmResult,
    CoTCLIArm,
    EtzArm,
    RawCLIArm,
    make_arm,
)
from benchmarks.cache import CacheEntry, LLMCache, cache_key
from benchmarks.claude_cli import (
    COT_SYSTEM_PROMPT,
    DEFAULT_SYSTEM_PROMPT,
    CLIInvocationResult,
    ClaudeCLIInvoker,
)


@pytest.fixture
def tmp_cache():
    with tempfile.TemporaryDirectory() as tmp:
        yield LLMCache(Path(tmp) / "cache")


class TestArmsRegistry:
    def test_all_arms_listed(self):
        assert ALL_ARMS == ["raw_cli", "cot_cli", "etz_yosher"]

    def test_make_arm_factory(self, tmp_cache):
        for name in ALL_ARMS:
            arm = make_arm(name, tmp_cache)
            assert arm.name == name

    def test_unknown_arm_raises(self, tmp_cache):
        with pytest.raises(ValueError, match="Unknown arm"):
            make_arm("nonexistent", tmp_cache)


class TestRawCLIArmCache:
    """RawCLIArm uses cache transparently to avoid duplicate Claude CLI calls."""

    def test_cache_hit_short_circuits_invoker(self, tmp_cache):
        # Pre-populate cache
        from benchmarks.arms import OPUS_FULL_SLUG

        prompt = "Test prompt"
        key = cache_key(OPUS_FULL_SLUG, prompt, 0.0, DEFAULT_SYSTEM_PROMPT, thinking=False)
        tmp_cache.put(key, CacheEntry(
            response_text="Cached response",
            latency_ms=100,
            tokens_input=10,
            tokens_output=20,
            cost_usd=0.001,
            model=OPUS_FULL_SLUG,
        ))

        # Use mock invoker that should NOT be called
        mock_invoker = MagicMock(spec=ClaudeCLIInvoker)
        arm = RawCLIArm(tmp_cache, invoker=mock_invoker)

        result = arm.run(prompt)

        # Verify cache hit, no invoker call
        mock_invoker.invoke.assert_not_called()
        assert result.response == "Cached response"
        assert result.cache_hits == 1
        assert result.cost_usd == 0.0  # cache hit = no new cost
        assert result.success

    def test_cache_miss_calls_invoker(self, tmp_cache):
        mock_invoker = MagicMock(spec=ClaudeCLIInvoker)
        mock_invoker.invoke.return_value = CLIInvocationResult(
            text="Fresh response",
            success=True,
            duration_ms=1500,
            duration_api_ms=1490,
            cost_usd=0.04,
            usage_input=10,
            usage_output=20,
            cache_creation_tokens=0,
            cache_read_tokens=0,
            num_turns=1,
            stop_reason="end_turn",
            model="claude-opus-4-20250514",
        )

        arm = RawCLIArm(tmp_cache, invoker=mock_invoker)
        result = arm.run("Fresh prompt")

        mock_invoker.invoke.assert_called_once()
        assert result.response == "Fresh response"
        assert result.cache_hits == 0
        assert result.cost_usd == 0.04


class TestCoTCLIArm:
    def test_uses_cot_system_prompt(self, tmp_cache):
        mock_invoker = MagicMock(spec=ClaudeCLIInvoker)
        mock_invoker.invoke.return_value = CLIInvocationResult(
            text="Step-by-step answer",
            success=True,
            duration_ms=2000, duration_api_ms=1990,
            cost_usd=0.05, usage_input=15, usage_output=50,
            cache_creation_tokens=0, cache_read_tokens=0,
            num_turns=1, stop_reason="end_turn",
            model="claude-opus-4-20250514",
        )

        arm = CoTCLIArm(tmp_cache, invoker=mock_invoker)
        result = arm.run("Hard question")

        # Verify CoT system prompt was used
        call_kwargs = mock_invoker.invoke.call_args.kwargs
        assert call_kwargs["system_prompt"] == COT_SYSTEM_PROMPT
        assert result.response == "Step-by-step answer"


class TestArmResult:
    def test_to_dict_roundtrip(self):
        r = ArmResult(
            response="test",
            arm_name="raw_cli",
            cost_usd=0.04,
            tokens_input=10,
            tokens_output=20,
            latency_ms=1500,
            n_internal_calls=1,
            cache_hits=0,
        )
        d = r.to_dict()
        assert d["response"] == "test"
        assert d["arm_name"] == "raw_cli"
        assert d["cost_usd"] == 0.04


class TestEtzArm:
    """EtzArm uses subprocess (heavier mock setup)."""

    def test_etz_failure_path(self, tmp_cache):
        from benchmarks.etz_invoke import EtzInvocationResult

        # Mock invoke_etz to return a failure
        with patch("benchmarks.etz_invoke.invoke_etz") as mock:
            mock.return_value = EtzInvocationResult(
                success=False,
                error="Test failure",
                total_latency_s=2.0,
            )
            arm = EtzArm(tmp_cache, profile="claude_max")
            result = arm.run("Test")

            assert not result.success
            assert result.error == "Test failure"
            assert result.latency_ms == 2000

    def test_etz_success_path(self, tmp_cache):
        from benchmarks.etz_invoke import EtzInvocationResult

        with patch("benchmarks.etz_invoke.invoke_etz") as mock:
            mock.return_value = EtzInvocationResult(
                response="Etz response",
                success=True,
                confidence=0.85,
                world_path=["assiah", "yetzirah"],
                generation_olam="yetzirah",
                quality_verdict="excellent",
                total_latency_s=8.5,
            )
            arm = EtzArm(tmp_cache, profile="claude_max")
            result = arm.run("Test")

            assert result.success
            assert result.response == "Etz response"
            assert result.n_internal_calls == 2  # len(world_path)
            assert result.metadata["confidence"] == 0.85
            assert result.metadata["world_path"] == ["assiah", "yetzirah"]

    def test_etz_ablation_passed_via_env(self, tmp_cache):
        from benchmarks.etz_invoke import EtzInvocationResult

        with patch("benchmarks.etz_invoke.invoke_etz") as mock:
            mock.return_value = EtzInvocationResult(
                response="ok", success=True,
                world_path=["yetzirah"], total_latency_s=4.0,
            )
            arm = EtzArm(
                tmp_cache, profile="claude_max",
                ablation_disable=["sitra_achra", "hitbonenut"],
            )
            arm.run("Test")

            call_kwargs = mock.call_args.kwargs
            extra_env = call_kwargs.get("extra_env") or {}
            assert "ETZCHAIM_ABLATION_DISABLE" in extra_env
            assert extra_env["ETZCHAIM_ABLATION_DISABLE"] == "sitra_achra,hitbonenut"
