"""Regression for the Haiku provider wrapper — no live CLI call.

Asserts (1) chat_claude_cli maps the CLI's MEASURED usage + cost onto ModelCall and
resolves the current Haiku 4.5 slug, and (2) the stale-slug guard fails loud rather than
calling the model with a Phase-0-style outdated slug.
"""

from __future__ import annotations

import pytest

from benchmarks import claude_cli
from benchmarks.gating_harness import provider


def test_chat_claude_cli_maps_measured_tokens_and_cost(monkeypatch):
    class _FakeInvoker:
        def __init__(self, *a, **k):
            pass

        def invoke(self, prompt, **kw):
            assert kw["model"] == "claude-haiku-4-5"  # resolved slug, not the stale default
            return claude_cli.CLIInvocationResult(
                text="APPROACH: stack\n```python\ndef is_balanced(s):\n    return True\n```",
                success=True,
                duration_ms=123,
                duration_api_ms=100,
                cost_usd=0.0021,
                usage_input=42,
                usage_output=17,
                cache_creation_tokens=0,
                cache_read_tokens=0,
                num_turns=1,
                stop_reason="end_turn",
                model=kw["model"],
            )

    monkeypatch.setattr(claude_cli, "ClaudeCLIInvoker", _FakeInvoker)
    call = provider.chat_claude_cli(
        [{"role": "system", "content": "sys"}, {"role": "user", "content": "u"}]
    )
    assert (call.prompt_tokens, call.completion_tokens) == (42, 17)  # MEASURED
    assert call.cost_usd == 0.0021                                   # MEASURED
    assert call.model == "claude-haiku-4-5"
    assert call.provider == "anthropic_oauth_cli"


def test_chat_claude_cli_rejects_stale_slug(monkeypatch):
    # Simulate config resolving to the Phase-0 stale slug -> must refuse, never invoke.
    monkeypatch.setattr(
        provider, "resolve_model", lambda alias, profile=None: "claude-opus-4-20250514"
    )

    def _boom(*a, **k):  # the CLI must never be constructed if the guard works
        raise AssertionError("CLI invoked despite a stale slug")

    monkeypatch.setattr(claude_cli, "ClaudeCLIInvoker", _boom)
    with pytest.raises(RuntimeError, match="stale-slug"):
        provider.chat_claude_cli([{"role": "user", "content": "u"}])
