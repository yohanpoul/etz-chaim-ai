"""LiteLLM provider — unified gateway over 100+ LLM backends.

Routes any `model="<provider>/<model-name>"` string (for example
`anthropic/claude-opus-4-7`, `openai/gpt-5`, `gemini/gemini-2.5-pro`,
`bedrock/anthropic.claude-opus-4-7-v1:0`, `ollama/qwen3.5:9b`) through the
[LiteLLM](https://docs.litellm.ai) SDK.

LiteLLM reads credentials from the conventional env vars (ANTHROPIC_API_KEY,
OPENAI_API_KEY, AWS_ACCESS_KEY_ID, AZURE_API_KEY, etc.) — see .env.example
for the exhaustive list.

Opt-in : activated by writing `provider: litellm` under an olam in
config.yaml. Legacy providers (`anthropic_sdk`, `ollama`, `claude_code`)
remain fully functional and take precedence when explicitly selected.

Requires : litellm>=1.50.0. If the package is missing, the provider raises
a clear ImportError with the install command.
"""
from __future__ import annotations

import time
from typing import Any


class LiteLLMProvider:
    """Provider wrapping LiteLLM's unified completion API.

    Usage :
        provider = LiteLLMProvider()
        text, latency_ms = provider.generate(
            prompt="What is Tsimtsum ?",
            model="anthropic/claude-opus-4-7",
            max_tokens=4096,
            temperature=0.3,
            system_prompt="You are a Kabbalah scholar.",
            thinking=False,
        )

    Features passed through to LiteLLM :
    - `thinking=True` → `thinking={"type": "enabled", "budget_tokens": ...}`
      (supported by Anthropic, OpenAI o-series, Gemini 2.5 Pro).
    - `fallback` model/provider → automatic retry on the fallback backend
      when the primary returns a rate limit or transient error.
    - Usage tracking via LiteLLM's completion_cost helper.
    """

    def __init__(self) -> None:
        try:
            import litellm
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "LiteLLM is not installed. Install with :\n"
                "  pip install 'etzchaim[litellm]'\n"
                "or directly :\n"
                "  pip install 'litellm>=1.50.0'"
            ) from e
        self._litellm = litellm
        litellm.drop_params = True
        litellm.set_verbose = False

    def generate(
        self,
        prompt: str,
        model: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: str | None = None,
        thinking: bool = False,
        thinking_budget: int = 8192,
        fallback: str | None = None,
        timeout: int = 120,
        **extra: Any,
    ) -> tuple[str, int]:
        """Send a completion request. Returns (text, latency_ms).

        Args:
            prompt: user message.
            model: LiteLLM slug, e.g. ``anthropic/claude-opus-4-7``.
            max_tokens: generation budget.
            temperature: sampling temperature (ignored by reasoning models).
            system_prompt: optional system-level instruction.
            thinking: enable extended thinking on capable providers.
            thinking_budget: token budget for thinking traces.
            fallback: LiteLLM slug to try if the primary fails.
            timeout: per-request timeout in seconds.
            **extra: forwarded to ``litellm.completion``.

        Raises:
            RuntimeError: both primary and fallback fail.
        """
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "timeout": timeout,
        }
        if thinking:
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
        if fallback:
            kwargs["fallbacks"] = [fallback]
        kwargs.update(extra)

        start = time.monotonic()
        try:
            response = self._litellm.completion(**kwargs)
        except Exception as e:  # pragma: no cover — re-raised with context
            raise RuntimeError(
                f"LiteLLM completion failed for model {model!r} : {e}. "
                f"Check the corresponding API key env var is set."
            ) from e

        latency_ms = int((time.monotonic() - start) * 1000)
        text = response.choices[0].message.content or ""
        return text, latency_ms

    def embed(
        self,
        texts: list[str],
        model: str,
        *,
        dimensions: int | None = None,
        timeout: int = 60,
    ) -> list[list[float]]:
        """Embed a batch of texts. Returns a list of vectors."""
        kwargs: dict[str, Any] = {
            "model": model,
            "input": texts,
            "timeout": timeout,
        }
        if dimensions:
            kwargs["dimensions"] = dimensions
        response = self._litellm.embedding(**kwargs)
        return [item["embedding"] for item in response.data]

    @staticmethod
    def available_providers() -> list[str]:
        """Return the list of provider prefixes known to LiteLLM.

        Useful for wizard multi-select / provider discovery. Comes from the
        LiteLLM routing table at import time.
        """
        try:
            import litellm
            return sorted(litellm.provider_list)
        except ImportError:
            return []
