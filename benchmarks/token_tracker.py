"""TrackedAnthropicProvider — wrapper qui capture usage tokens + cost.

Corrige la lacune de etzchaim/providers/anthropic_sdk.py:110-118 qui drop
silencieusement `response.usage`. Pour le benchmark, on a besoin de :

- input_tokens
- output_tokens
- cache_read_input_tokens (depuis prompt caching ephemeral)
- cache_creation_input_tokens (premiere ecriture cache)
- cost USD compute selon Opus 4.7 pricing

Usage :
    tracker = TrackedAnthropicProvider()
    result = tracker.generate(
        prompt="...",
        model="claude-opus-4-20250514",
        max_tokens=2048,
        temperature=0.0,
        system_prompt="...",
    )
    # result = TrackedResult(text, latency_ms, usage, cost_usd)
"""

from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass
from typing import Any


# Opus 4.7 pricing (avril 2026, $/M tokens)
# Source : https://www.anthropic.com/pricing
OPUS_PRICE_INPUT_PER_MTOKEN = 15.00
OPUS_PRICE_OUTPUT_PER_MTOKEN = 75.00
OPUS_PRICE_CACHE_READ_PER_MTOKEN = 1.50         # 10% du input
OPUS_PRICE_CACHE_CREATION_PER_MTOKEN = 18.75    # 125% du input


@dataclass
class TokenUsage:
    """Usage tokens capturés depuis Anthropic SDK response.usage."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0

    @property
    def total_input_equivalent(self) -> int:
        """Total tokens count incluant cache (pour reporting volume)."""
        return (
            self.input_tokens
            + self.cache_read_input_tokens
            + self.cache_creation_input_tokens
        )

    def cost_usd(
        self,
        price_input: float = OPUS_PRICE_INPUT_PER_MTOKEN,
        price_output: float = OPUS_PRICE_OUTPUT_PER_MTOKEN,
        price_cache_read: float = OPUS_PRICE_CACHE_READ_PER_MTOKEN,
        price_cache_creation: float = OPUS_PRICE_CACHE_CREATION_PER_MTOKEN,
    ) -> float:
        """Compute cost USD pour Opus 4.7 (defaults).

        Args overridables pour tester un autre modele (Sonnet, Haiku, etc.).
        """
        return (
            self.input_tokens * price_input / 1_000_000
            + self.output_tokens * price_output / 1_000_000
            + self.cache_read_input_tokens * price_cache_read / 1_000_000
            + self.cache_creation_input_tokens * price_cache_creation / 1_000_000
        )


@dataclass
class TrackedResult:
    """Resultat d'un appel LLM tracé."""

    text: str
    latency_ms: int
    usage: TokenUsage
    cost_usd: float
    model: str
    temperature: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "latency_ms": self.latency_ms,
            "usage": asdict(self.usage),
            "cost_usd": self.cost_usd,
            "model": self.model,
            "temperature": self.temperature,
        }


class TrackedAnthropicProvider:
    """Wrapper Anthropic SDK avec capture usage + cost tracking.

    Indépendant de olamot et de etzchaim/providers/anthropic_sdk.py
    pour ne pas modifier le code production. Utilisé uniquement par
    le benchmark harness.
    """

    def __init__(self, client: Any = None):
        if client is None:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                raise RuntimeError(
                    "ANTHROPIC_API_KEY non définie. "
                    "Required for benchmark runs : export ANTHROPIC_API_KEY=sk-ant-..."
                )
            try:
                from anthropic import Anthropic
            except ImportError as e:
                raise RuntimeError(
                    "Package `anthropic` non installé. "
                    "pip install 'anthropic>=0.40'"
                ) from e
            client = Anthropic()
        self.client = client

    def generate(
        self,
        prompt: str,
        model: str = "claude-opus-4-20250514",
        max_tokens: int = 2048,
        temperature: float = 0.0,
        system_prompt: str | None = None,
        thinking: bool = False,
        **extra: Any,
    ) -> TrackedResult:
        """Generate a completion + capture usage tokens + compute cost.

        Args:
            prompt: User message content.
            model: Model slug, défaut Opus 4.7 full slug.
            max_tokens: Max output tokens.
            temperature: 0.0 pour benchmarks déterministes.
            system_prompt: Optional system prompt (cacheable).
            thinking: Extended thinking mode (Briah equivalent).
            **extra: Passthrough vers Anthropic SDK.

        Returns:
            TrackedResult avec text, latency, usage, cost.

        Raises:
            anthropic.APIError on API failures (caller handles retry).
        """
        t0 = time.time()
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        if thinking:
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": 10000}
        kwargs.update(extra)

        response = self.client.messages.create(**kwargs)
        latency_ms = int((time.time() - t0) * 1000)

        # Extract text (skip thinking blocks)
        text_parts = [
            block.text for block in response.content
            if getattr(block, "type", "text") == "text"
        ]
        text = "".join(text_parts)

        # Capture usage — la lacune de anthropic_sdk.py corrigée ici
        usage = response.usage
        token_usage = TokenUsage(
            input_tokens=getattr(usage, "input_tokens", 0),
            output_tokens=getattr(usage, "output_tokens", 0),
            cache_read_input_tokens=getattr(usage, "cache_read_input_tokens", 0),
            cache_creation_input_tokens=getattr(
                usage, "cache_creation_input_tokens", 0
            ),
        )

        cost = token_usage.cost_usd()

        return TrackedResult(
            text=text,
            latency_ms=latency_ms,
            usage=token_usage,
            cost_usd=cost,
            model=model,
            temperature=temperature,
        )


def estimate_cost_for_volume(
    n_calls: int,
    avg_input_tokens: int,
    avg_output_tokens: int,
    cache_hit_rate: float = 0.0,
) -> float:
    """Estimate total cost USD pour un volume d'appels Opus 4.7.

    Args:
        n_calls: Nombre d'appels.
        avg_input_tokens: Moyenne tokens input par appel.
        avg_output_tokens: Moyenne tokens output par appel.
        cache_hit_rate: Fraction des input tokens depuis cache (0.0 - 1.0).

    Returns:
        Total cost USD estimé.
    """
    cached_input = avg_input_tokens * cache_hit_rate
    fresh_input = avg_input_tokens * (1.0 - cache_hit_rate)

    cost_per_call = (
        fresh_input * OPUS_PRICE_INPUT_PER_MTOKEN / 1_000_000
        + cached_input * OPUS_PRICE_CACHE_READ_PER_MTOKEN / 1_000_000
        + avg_output_tokens * OPUS_PRICE_OUTPUT_PER_MTOKEN / 1_000_000
    )
    return n_calls * cost_per_call


if __name__ == "__main__":
    # Smoke test offline (pas d'appel API)
    usage = TokenUsage(
        input_tokens=1000,
        output_tokens=500,
        cache_read_input_tokens=200,
        cache_creation_input_tokens=0,
    )
    print(f"Test usage: {usage}")
    print(f"Cost USD: ${usage.cost_usd():.4f}")
    print(f"Total input equivalent: {usage.total_input_equivalent} tokens")
    print()
    print("Estimation pour benchmark complet (5 arms × 950 prompts) :")
    estimated = estimate_cost_for_volume(
        n_calls=5 * 950,
        avg_input_tokens=350,
        avg_output_tokens=300,
        cache_hit_rate=0.3,
    )
    print(f"  Estimé : ${estimated:.2f}")
