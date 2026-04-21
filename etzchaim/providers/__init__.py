"""etzchaim.providers — LLM provider abstractions.

Built-in providers :
- `AnthropicSDKProvider` : direct anthropic SDK (container-safe, no OAuth).
- `LiteLLMProvider` : unified gateway over 100+ backends (OpenAI, Google,
  xAI, Mistral, Cohere, DeepSeek, OpenRouter, Together, Groq, Fireworks,
  Perplexity, AWS Bedrock, Azure OpenAI, HuggingFace, NVIDIA NIM,
  Cloudflare, Replicate, vLLM, LM Studio, LocalAI, Ollama — all via
  `litellm`). Opt-in : install `pip install 'etzchaim[litellm]'`.
- `select_claude_backend()` : dispatcher that picks the best Claude backend
  (anthropic SDK vs legacy `claude` CLI subprocess) given what is installed.
"""
from __future__ import annotations

from etzchaim.providers.anthropic_sdk import MODEL_SLUGS, AnthropicSDKProvider
from etzchaim.providers.litellm_provider import LiteLLMProvider
from etzchaim.providers.registry import select_claude_backend

__all__ = [
    "AnthropicSDKProvider",
    "LiteLLMProvider",
    "MODEL_SLUGS",
    "select_claude_backend",
]
