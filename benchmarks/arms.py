"""3 benchmark arms — OAuth Max edition (Claude CLI subprocess).

Arms :
    1. RawCLIArm     — 1 call CLI Opus 4.7 system minimal
    2. CoTCLIArm     — 1 call CLI avec system "think step by step"
    3. EtzArm        — pipeline Etz complet via subprocess main.py

Tous retournent ArmResult uniforme.

Self-consistency abandonné : sans temperature control via CLI, les samples
seraient identiques. La défense compute parity se fait via ablation matrix.

Cost USD est extrait de `total_cost_usd` du JSON output Claude CLI v2.1.119.
Pour OAuth Max, ces coûts sont indicatifs (forfait absorbe une partie).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from benchmarks.cache import CacheEntry, LLMCache, cache_key
from benchmarks.claude_cli import (
    COT_SYSTEM_PROMPT,
    DEFAULT_SYSTEM_PROMPT,
    ClaudeCLIInvoker,
    CLIInvocationResult,
)


OPUS_FULL_SLUG = "claude-opus-4-20250514"


@dataclass
class ArmResult:
    """Résultat uniforme d'un arm sur un prompt."""

    response: str
    arm_name: str
    cost_usd: float = 0.0
    tokens_input: int = 0
    tokens_output: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    latency_ms: int = 0
    n_internal_calls: int = 1
    cache_hits: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# CLI-based arms (raw + CoT)
# ---------------------------------------------------------------------------


class _ClaudeCLIArmBase:
    """Helper : appel Claude CLI avec cache transparent."""

    def __init__(
        self,
        cache: LLMCache,
        invoker: ClaudeCLIInvoker | None = None,
        model: str = OPUS_FULL_SLUG,
    ):
        self.cache = cache
        self.invoker = invoker or ClaudeCLIInvoker()
        self.model = model

    def _call_cli(
        self,
        prompt: str,
        system_prompt: str,
        max_turns: int = 1,
    ) -> tuple[CLIInvocationResult, bool]:
        """Call Claude CLI with transparent cache. Returns (result, was_cached)."""
        key = cache_key(self.model, prompt, 0.0, system_prompt, thinking=False)
        cached = self.cache.get(key)
        if cached is not None:
            return (
                CLIInvocationResult(
                    text=cached.response_text,
                    success=True,
                    duration_ms=cached.latency_ms,
                    duration_api_ms=cached.latency_ms,
                    cost_usd=0.0,  # cache hit = no new cost
                    usage_input=cached.tokens_input,
                    usage_output=cached.tokens_output,
                    cache_creation_tokens=cached.tokens_cache_creation,
                    cache_read_tokens=cached.tokens_cache_read,
                    num_turns=1,
                    stop_reason="cache_hit",
                    model=self.model,
                ),
                True,
            )

        result = self.invoker.invoke(
            prompt=prompt,
            system_prompt=system_prompt,
            model=self.model,
            max_turns=max_turns,
        )

        if result.success:
            self.cache.put(key, CacheEntry(
                response_text=result.text,
                latency_ms=result.duration_ms,
                tokens_input=result.usage_input,
                tokens_output=result.usage_output,
                tokens_cache_read=result.cache_read_tokens,
                tokens_cache_creation=result.cache_creation_tokens,
                cost_usd=result.cost_usd,
                model=self.model,
            ))

        return result, False


class RawCLIArm(_ClaudeCLIArmBase):
    """Arm 1 : Claude CLI raw — 1 call avec system minimal."""

    name = "raw_cli"

    def run(self, prompt_text: str) -> ArmResult:
        result, was_cached = self._call_cli(
            prompt_text,
            system_prompt=DEFAULT_SYSTEM_PROMPT,
        )
        return ArmResult(
            response=result.text,
            arm_name=self.name,
            cost_usd=result.cost_usd,
            tokens_input=result.usage_input,
            tokens_output=result.usage_output,
            cache_creation_tokens=result.cache_creation_tokens,
            cache_read_tokens=result.cache_read_tokens,
            latency_ms=result.duration_ms,
            n_internal_calls=1,
            cache_hits=1 if was_cached else 0,
            success=result.success,
            error=result.error,
            metadata={"stop_reason": result.stop_reason},
        )


class CoTCLIArm(_ClaudeCLIArmBase):
    """Arm 2 : Claude CLI + Chain-of-Thought."""

    name = "cot_cli"

    def run(self, prompt_text: str) -> ArmResult:
        result, was_cached = self._call_cli(
            prompt_text,
            system_prompt=COT_SYSTEM_PROMPT,
        )
        return ArmResult(
            response=result.text,
            arm_name=self.name,
            cost_usd=result.cost_usd,
            tokens_input=result.usage_input,
            tokens_output=result.usage_output,
            cache_creation_tokens=result.cache_creation_tokens,
            cache_read_tokens=result.cache_read_tokens,
            latency_ms=result.duration_ms,
            n_internal_calls=1,
            cache_hits=1 if was_cached else 0,
            success=result.success,
            error=result.error,
            metadata={"stop_reason": result.stop_reason},
        )


# ---------------------------------------------------------------------------
# Etz Chaim arm via subprocess main.py
# ---------------------------------------------------------------------------


class EtzArm:
    """Arm 3 : Claude+EtzChaim Yosher — pipeline complet via subprocess.

    Le subprocess invoke `python main.py ask` qui orchestre la descente Yosher
    (Keter→Malkuth) avec 1-3 calls Claude CLI internes (Hishtalshelut),
    selon le profile actif de config.yaml (claude_max recommandé pour bench).
    """

    name = "etz_yosher"

    def __init__(
        self,
        cache: LLMCache,  # cache non-utilisé pour Etz (subprocess opaque)
        profile: str = "claude_max",
        timeout: int = 600,
        ablation_disable: list[str] | None = None,
    ):
        self.cache = cache
        self.profile = profile
        self.timeout = timeout
        # Ablation : list de modules à désactiver via env var
        self.ablation_disable = ablation_disable or []

    def run(self, prompt_text: str) -> ArmResult:
        from benchmarks.etz_invoke import invoke_etz

        extra_env: dict[str, str] = {}
        if self.ablation_disable:
            extra_env["ETZCHAIM_ABLATION_DISABLE"] = ",".join(self.ablation_disable)

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

        # Estimate cost from world_path : chaque world traversé ≈ 1 CLI call
        # Hypothèse : avg 350 input + 400 output tokens par call
        n_calls_est = max(1, len(result.world_path) or 1)

        # Cost estimation conservative : Opus 4.7 ~$0.04/call avec cache partiel
        est_cost = 0.04 * n_calls_est

        return ArmResult(
            response=result.response,
            arm_name=self.name,
            cost_usd=est_cost,
            tokens_input=350 * n_calls_est,
            tokens_output=400 * n_calls_est,
            cache_creation_tokens=0,
            cache_read_tokens=0,
            latency_ms=int(result.total_latency_s * 1000),
            n_internal_calls=n_calls_est,
            cache_hits=0,
            metadata={
                "confidence": result.confidence,
                "world_path": result.world_path,
                "generation_olam": result.generation_olam,
                "quality_verdict": result.quality_verdict,
                "active_modules": result.active_modules,
                "ablation_disable": self.ablation_disable,
                "profile": self.profile,
            },
        )


# ---------------------------------------------------------------------------
# Arm registry + factory
# ---------------------------------------------------------------------------


def make_arm(name: str, cache: LLMCache, **kwargs: Any) -> Any:
    """Factory : créer un arm par nom."""
    arms_map = {
        "raw_cli": RawCLIArm,
        "cot_cli": CoTCLIArm,
        "etz_yosher": EtzArm,
    }
    cls = arms_map.get(name)
    if cls is None:
        raise ValueError(f"Unknown arm: {name}. Available: {list(arms_map)}")
    return cls(cache, **kwargs)


ALL_ARMS = ["raw_cli", "cot_cli", "etz_yosher"]
"""Liste ordonnée des 3 arms du benchmark v2 OAuth."""
