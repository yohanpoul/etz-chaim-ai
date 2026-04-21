"""Anthropic SDK provider — container-safe alternative to `claude` CLI subprocess.

Replaces the `claude` CLI subprocess call (which needs interactive OAuth auth,
impossible in Docker) with the `anthropic` Python SDK that reads ANTHROPIC_API_KEY.

Supports :
- Short model aliases (opus/sonnet/haiku) via MODEL_SLUGS
- Extended thinking via thinking=True (Briah Olam)
- Prompt caching via cache_control on constant system prompts
- Structured tool_use passthrough

Used by `olamot.claude_code_generate` when ANTHROPIC_API_KEY is set. Falls back
to the legacy CLI path when only `claude` binary is available.

Requires : anthropic>=0.40, ANTHROPIC_API_KEY env var.
"""
from __future__ import annotations

import os
import time
from typing import Any

# Short alias → full API slug (avril 2026 état du SDK Anthropic).
# Users can also pass full slugs in config.yaml (the resolver passes through).
MODEL_SLUGS = {
    # Claude 4.x family — shortcut aliases used in config.yaml
    "opus": "claude-opus-4-20250514",
    "sonnet": "claude-sonnet-4-5-20250929",
    "haiku": "claude-haiku-4-20250801",
}


def _resolve_model(m: str) -> str:
    """Return full API slug from short alias, or pass through if already full."""
    return MODEL_SLUGS.get(m, m)


class AnthropicSDKProvider:
    """Provider wrapping the `anthropic` Python SDK.

    Usage :
        provider = AnthropicSDKProvider()  # reads ANTHROPIC_API_KEY from env
        text, latency_ms = provider.generate(
            prompt="What is Tsimtsum ?",
            model="opus",          # or full slug "claude-opus-4-..."
            max_tokens=4096,
            temperature=0.3,
            system_prompt="You are a Kabbalah scholar.",  # cacheable
            thinking=True,         # Briah Olam extended thinking
        )

    Never makes real API calls in tests — inject a mock client via client=...
    """

    def __init__(self, client: Any = None):
        if client is None:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                raise RuntimeError(
                    "ANTHROPIC_API_KEY non définie. Pour utiliser le provider "
                    "anthropic SDK : export ANTHROPIC_API_KEY=sk-ant-... ou "
                    "basculer au profil ollama_local (pas de clé requise)."
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
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: str | None = None,
        thinking: bool = False,
        **extra: Any,
    ) -> tuple[str, int]:
        """Generate a completion. Returns (text, latency_ms).

        Raises on API errors (caller handles retry/circuit-breaker).
        """
        t0 = time.time()
        kwargs: dict[str, Any] = {
            "model": _resolve_model(model),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            # Prompt caching on the constant system prompt → ~90% token cost savings
            # on repeated calls (Anthropic SDK ≥0.40 supports ephemeral cache_control).
            kwargs["system"] = [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        if thinking:
            # Extended thinking for Briah Olam — budget tunable.
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": 10000}
        # Pass-through for tool_use, tool_choice, metadata, etc.
        kwargs.update(extra)

        response = self.client.messages.create(**kwargs)
        latency_ms = int((time.time() - t0) * 1000)

        # Extract text from content blocks, ignoring thinking blocks.
        text_parts = [
            block.text for block in response.content
            if getattr(block, "type", "text") == "text"
        ]
        return "".join(text_parts), latency_ms
