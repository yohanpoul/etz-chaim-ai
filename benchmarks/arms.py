"""5 benchmark arms — fair compute parity Claude+Etz vs Claude raw.

Arms :
    1. RawArm                    — 1 call Opus minimal
    2. CoTArm                    — 1 call avec "Think step by step"
    3. SelfConsistencyArm(N=3)   — 3 calls temp=0.7 majority vote
                                   (proxy compute égal à Etz pipeline)
    4. EtzArm                    — subprocess via etz_invoke
    5. EtzDeterministicArm       — Etz avec temperature=0 forcée

Tous retournent ArmResult uniforme.
"""

from __future__ import annotations

import os
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any

from benchmarks.cache import CacheEntry, LLMCache, cache_key
from benchmarks.token_tracker import TrackedAnthropicProvider, TrackedResult


OPUS_FULL_SLUG = "claude-opus-4-20250514"

DEFAULT_SYSTEM_PROMPT = (
    "You are a careful, honest, helpful assistant. Provide accurate "
    "answers and refuse harmful requests."
)
COT_SYSTEM_PROMPT = (
    "You are a careful, honest, helpful assistant. Think step by step "
    "before answering, then provide a concise final answer."
)


@dataclass
class ArmResult:
    """Résultat uniforme d'un arm sur un prompt."""

    response: str
    arm_name: str
    cost_usd: float = 0.0
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: int = 0
    n_internal_calls: int = 1            # 1 pour raw/CoT, 3 pour SC, 1-3 pour Etz
    cache_hits: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Anthropic-based arms (raw / CoT / self-consistency)
# ---------------------------------------------------------------------------


class _AnthropicArmBase:
    """Helper : appel Opus avec cache transparent."""

    def __init__(self, cache: LLMCache, provider: TrackedAnthropicProvider | None = None):
        self.cache = cache
        self._provider = provider  # lazy init si None

    def _get_provider(self) -> TrackedAnthropicProvider:
        if self._provider is None:
            self._provider = TrackedAnthropicProvider()
        return self._provider

    def _call_opus(
        self,
        prompt: str,
        *,
        temperature: float = 0.0,
        system_prompt: str | None = DEFAULT_SYSTEM_PROMPT,
        max_tokens: int = 2048,
    ) -> tuple[TrackedResult | None, bool]:
        """Call Opus, with transparent cache. Returns (result, was_cached)."""
        key = cache_key(
            OPUS_FULL_SLUG, prompt, temperature, system_prompt, thinking=False
        )
        cached = self.cache.get(key)
        if cached is not None:
            return (
                TrackedResult(
                    text=cached.response_text,
                    latency_ms=cached.latency_ms,
                    usage=__import__("benchmarks.token_tracker", fromlist=["TokenUsage"]).TokenUsage(
                        input_tokens=cached.tokens_input,
                        output_tokens=cached.tokens_output,
                        cache_read_input_tokens=cached.tokens_cache_read,
                        cache_creation_input_tokens=cached.tokens_cache_creation,
                    ),
                    cost_usd=cached.cost_usd,
                    model=cached.model,
                    temperature=temperature,
                ),
                True,
            )

        provider = self._get_provider()
        result = provider.generate(
            prompt=prompt,
            model=OPUS_FULL_SLUG,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=system_prompt,
        )
        self.cache.put(key, CacheEntry(
            response_text=result.text,
            latency_ms=result.latency_ms,
            tokens_input=result.usage.input_tokens,
            tokens_output=result.usage.output_tokens,
            tokens_cache_read=result.usage.cache_read_input_tokens,
            tokens_cache_creation=result.usage.cache_creation_input_tokens,
            cost_usd=result.cost_usd,
            model=OPUS_FULL_SLUG,
        ))
        return result, False


class RawArm(_AnthropicArmBase):
    """Arm 1 : Claude raw — 1 call, system minimal, temp=0."""

    name = "raw"

    def run(self, prompt_text: str, temperature: float = 0.0) -> ArmResult:
        result, was_cached = self._call_opus(
            prompt_text,
            temperature=temperature,
            system_prompt=DEFAULT_SYSTEM_PROMPT,
        )
        return ArmResult(
            response=result.text,
            arm_name=self.name,
            cost_usd=result.cost_usd if not was_cached else 0.0,
            tokens_input=result.usage.input_tokens,
            tokens_output=result.usage.output_tokens,
            latency_ms=result.latency_ms,
            n_internal_calls=1,
            cache_hits=1 if was_cached else 0,
        )


class CoTArm(_AnthropicArmBase):
    """Arm 2 : Claude + Chain-of-Thought — 1 call avec system 'think step by step'."""

    name = "cot"

    def run(self, prompt_text: str, temperature: float = 0.0) -> ArmResult:
        result, was_cached = self._call_opus(
            prompt_text,
            temperature=temperature,
            system_prompt=COT_SYSTEM_PROMPT,
        )
        return ArmResult(
            response=result.text,
            arm_name=self.name,
            cost_usd=result.cost_usd if not was_cached else 0.0,
            tokens_input=result.usage.input_tokens,
            tokens_output=result.usage.output_tokens,
            latency_ms=result.latency_ms,
            n_internal_calls=1,
            cache_hits=1 if was_cached else 0,
        )


class SelfConsistencyArm(_AnthropicArmBase):
    """Arm 3 : Self-consistency N=3 — proxy compute égal à Etz pipeline.

    Génère N réponses à temperature=0.7, agrège par majority vote (pour MCQ)
    ou prend la première (pour open-ended). Le judge fera vote sur les 3
    candidats si nécessaire.
    """

    name = "self_consistency"

    def __init__(self, cache: LLMCache, n: int = 3, provider: TrackedAnthropicProvider | None = None):
        super().__init__(cache, provider)
        self.n = n

    def run(self, prompt_text: str, temperature: float = 0.7) -> ArmResult:
        responses: list[str] = []
        total_cost = 0.0
        total_input = 0
        total_output = 0
        total_latency = 0
        n_cached = 0

        for i in range(self.n):
            # Pour différencier les samples, on varie le seed via system prompt
            # marker (le cache key change automatiquement)
            sys_p = f"{DEFAULT_SYSTEM_PROMPT}\n[sample {i}]"
            result, was_cached = self._call_opus(
                prompt_text,
                temperature=temperature,
                system_prompt=sys_p,
            )
            responses.append(result.text)
            if was_cached:
                n_cached += 1
            else:
                total_cost += result.cost_usd
            total_input += result.usage.input_tokens
            total_output += result.usage.output_tokens
            total_latency += result.latency_ms

        # Majority vote heuristic : si 2+ réponses sont quasi-identiques (premier
        # mot identique), prendre celle-là ; sinon prendre la première (sample 0).
        first_words = [r.strip().split()[:3] for r in responses if r.strip()]
        if first_words:
            buckets = Counter(tuple(w) for w in first_words)
            most_common, count = buckets.most_common(1)[0]
            if count >= 2:
                # Trouver la première réponse qui matche
                for r in responses:
                    if tuple(r.strip().split()[:3]) == most_common:
                        chosen = r
                        break
                else:
                    chosen = responses[0]
            else:
                chosen = responses[0]
        else:
            chosen = ""

        return ArmResult(
            response=chosen,
            arm_name=self.name,
            cost_usd=total_cost,
            tokens_input=total_input,
            tokens_output=total_output,
            latency_ms=total_latency,
            n_internal_calls=self.n,
            cache_hits=n_cached,
            metadata={"all_responses": responses, "n_samples": self.n},
        )


# ---------------------------------------------------------------------------
# Etz Chaim arms (subprocess via etz_invoke)
# ---------------------------------------------------------------------------


class EtzArm:
    """Arm 4 : Claude+EtzChaim Yosher — pipeline complet via subprocess.

    Note : le coût/tokens du subprocess Etz est tracé via le daemon log
    qui imprime "Tokens cumulés" — actuellement non capturé. Comme
    fallback, on estime à partir de la latency et d'un débit moyen
    Opus 4.7 (input + output tokens).
    """

    name = "etz_yosher"

    def __init__(
        self,
        cache: LLMCache,  # cache non-utilisé pour Etz (subprocess opaque)
        profile: str = "benchmark_opus",
        deterministic: bool = False,
        timeout: int = 600,
    ):
        self.cache = cache
        self.profile = profile
        self.deterministic = deterministic
        self.timeout = timeout

    def run(self, prompt_text: str) -> ArmResult:
        from benchmarks.etz_invoke import invoke_etz

        extra_env: dict[str, str] = {}
        if self.deterministic:
            # Force temperature=0 even if the profile config has 0.7
            extra_env["ETZCHAIM_FORCE_TEMP"] = "0.0"

        result = invoke_etz(
            prompt_text,
            profile=self.profile,
            timeout=self.timeout,
            extra_env=extra_env,
        )

        if not result.success:
            return ArmResult(
                response="",
                arm_name=self.name,
                success=False,
                error=result.error,
                latency_ms=int(result.total_latency_s * 1000),
            )

        # Estimer cost depuis latency : ~1500 tokens output / 12s en moyenne Opus
        # Conservative : 1.5 internal calls × 350 input × 300 output
        n_calls_est = max(1, len(result.world_path) or 1)
        est_input = 350 * n_calls_est
        est_output = 300 * n_calls_est
        est_cost = (est_input * 15 + est_output * 75) / 1_000_000

        return ArmResult(
            response=result.response,
            arm_name=self.name,
            cost_usd=est_cost,
            tokens_input=est_input,
            tokens_output=est_output,
            latency_ms=int(result.total_latency_s * 1000),
            n_internal_calls=n_calls_est,
            cache_hits=0,
            metadata={
                "confidence": result.confidence,
                "world_path": result.world_path,
                "generation_olam": result.generation_olam,
                "quality_verdict": result.quality_verdict,
                "active_modules": result.active_modules,
                "deterministic": self.deterministic,
            },
        )


class EtzDeterministicArm(EtzArm):
    """Arm 5 : Etz Yosher avec temperature=0 forcée."""

    name = "etz_deterministic"

    def __init__(
        self,
        cache: LLMCache,
        profile: str = "benchmark_opus",
        timeout: int = 600,
    ):
        super().__init__(cache, profile=profile, deterministic=True, timeout=timeout)


# ---------------------------------------------------------------------------
# Arm registry + factory
# ---------------------------------------------------------------------------


def make_arm(name: str, cache: LLMCache, **kwargs: Any) -> Any:
    """Factory : créer un arm par nom.

    Args:
        name: 'raw' | 'cot' | 'self_consistency' | 'etz_yosher' | 'etz_deterministic'
        cache: LLMCache instance pour Anthropic arms
        **kwargs: passthrough vers le constructor de l'arm

    Returns:
        Instance de l'arm.
    """
    arms_map = {
        "raw": RawArm,
        "cot": CoTArm,
        "self_consistency": SelfConsistencyArm,
        "etz_yosher": EtzArm,
        "etz_deterministic": EtzDeterministicArm,
    }
    cls = arms_map.get(name)
    if cls is None:
        raise ValueError(f"Unknown arm: {name}. Available: {list(arms_map)}")
    return cls(cache, **kwargs)


ALL_ARMS = ["raw", "cot", "self_consistency", "etz_yosher", "etz_deterministic"]
"""Liste ordonnée des 5 arms du benchmark."""
