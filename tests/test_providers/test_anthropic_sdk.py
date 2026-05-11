"""Test AnthropicSDKProvider (mocked client, no real API calls)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest


def _mock_client(text: str = "MOCKED_RESPONSE"):
    """Build a fake Anthropic client that returns a deterministic response."""
    client = MagicMock()
    response = MagicMock()
    content_block = MagicMock()
    content_block.type = "text"
    content_block.text = text
    response.content = [content_block]
    response.usage = MagicMock(input_tokens=10, output_tokens=5)
    client.messages.create.return_value = response
    return client


def test_generate_returns_text_and_latency():
    from etzchaim.providers.anthropic_sdk import AnthropicSDKProvider
    p = AnthropicSDKProvider(client=_mock_client("HELLO"))
    text, latency_ms = p.generate(prompt="test", model="opus", max_tokens=100)
    assert text == "HELLO"
    assert latency_ms >= 0


def test_generate_resolves_short_alias_to_full_slug():
    """Short alias is resolved through etzchaim.llm.model_registry."""
    from etzchaim.llm.model_registry import resolve_model
    from etzchaim.providers.anthropic_sdk import AnthropicSDKProvider
    client = _mock_client()
    p = AnthropicSDKProvider(client=client)
    p.generate(prompt="test", model="opus", max_tokens=100)
    call_kwargs = client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == resolve_model("opus")


def test_generate_passes_through_full_slug():
    """If caller provides a full API slug unknown to the registry, it passes through."""
    from etzchaim.providers.anthropic_sdk import AnthropicSDKProvider
    client = _mock_client()
    p = AnthropicSDKProvider(client=client)
    p.generate(prompt="test", model="claude-3-5-sonnet-20240620", max_tokens=100)
    call_kwargs = client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-3-5-sonnet-20240620"


def test_generate_temperature_and_max_tokens():
    from etzchaim.providers.anthropic_sdk import AnthropicSDKProvider
    client = _mock_client()
    p = AnthropicSDKProvider(client=client)
    p.generate(prompt="test", model="sonnet", max_tokens=500, temperature=0.2)
    call_kwargs = client.messages.create.call_args.kwargs
    assert call_kwargs["max_tokens"] == 500
    assert call_kwargs["temperature"] == 0.2


def test_generate_with_system_prompt_adds_cache_control():
    """System prompt uses ephemeral cache_control for prompt caching."""
    from etzchaim.providers.anthropic_sdk import AnthropicSDKProvider
    client = _mock_client()
    p = AnthropicSDKProvider(client=client)
    p.generate(
        prompt="test", model="opus", max_tokens=100,
        system_prompt="You are a Kabbalah scholar.",
    )
    call_kwargs = client.messages.create.call_args.kwargs
    assert isinstance(call_kwargs["system"], list)
    assert call_kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert "Kabbalah scholar" in call_kwargs["system"][0]["text"]


def test_generate_with_thinking_mode():
    """Briah Olam uses thinking=True → adds thinking block to request."""
    from etzchaim.providers.anthropic_sdk import AnthropicSDKProvider
    client = _mock_client()
    p = AnthropicSDKProvider(client=client)
    p.generate(prompt="test", model="opus", max_tokens=1000, thinking=True)
    call_kwargs = client.messages.create.call_args.kwargs
    assert call_kwargs["thinking"]["type"] == "enabled"
    assert "budget_tokens" in call_kwargs["thinking"]


def test_generate_without_thinking_omits_block():
    from etzchaim.providers.anthropic_sdk import AnthropicSDKProvider
    client = _mock_client()
    p = AnthropicSDKProvider(client=client)
    p.generate(prompt="test", model="sonnet", max_tokens=100, thinking=False)
    call_kwargs = client.messages.create.call_args.kwargs
    assert "thinking" not in call_kwargs


def test_generate_raises_on_missing_api_key(monkeypatch):
    """Calling AnthropicSDKProvider() without API key raises with clear hint."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from etzchaim.providers.anthropic_sdk import AnthropicSDKProvider
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        AnthropicSDKProvider()


def test_ignores_thinking_blocks_in_response():
    """Response content may contain thinking blocks — they must be filtered out."""
    from etzchaim.providers.anthropic_sdk import AnthropicSDKProvider
    client = MagicMock()
    response = MagicMock()
    thinking_block = MagicMock()
    thinking_block.type = "thinking"
    thinking_block.text = "INTERNAL_REASONING_SHOULD_NOT_LEAK"
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "VISIBLE_ANSWER"
    response.content = [thinking_block, text_block]
    client.messages.create.return_value = response

    p = AnthropicSDKProvider(client=client)
    text, _ = p.generate(prompt="q", model="opus", max_tokens=100, thinking=True)
    assert text == "VISIBLE_ANSWER"
    assert "INTERNAL_REASONING" not in text
