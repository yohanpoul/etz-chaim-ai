"""Tests for ``etzchaim.initiate``.

The provider boundary is exercised through a fake :class:`LLMClient` so the
wrapper contract is tested in isolation from any real LLM backend.
"""
from __future__ import annotations

import sys

import pytest

from etzchaim.initiate import (
    AgentResponse,
    AgentStatus,
    InitiatedAgent,
    InitiationError,
    LLMClient,
    LLMSpec,
    initiate,
)


class FakeLLMClient:
    def __init__(self, spec: LLMSpec, reply: str = "ok") -> None:
        self.spec = spec
        self.reply = reply
        self.calls: list[tuple[str, int]] = []

    def complete(self, prompt: str, *, max_turns: int) -> str:
        self.calls.append((prompt, max_turns))
        return f"{self.reply}::{self.spec.model}::{prompt}"


def _factory(reply: str = "ok"):
    def make(spec: LLMSpec) -> LLMClient:
        return FakeLLMClient(spec, reply=reply)
    return make


def test_initiate_returns_initiated_agent_for_canonical_id() -> None:
    agent = initiate("claude-opus-4-7", client_factory=_factory())
    assert isinstance(agent, InitiatedAgent)
    assert agent.spec.provider == "anthropic"
    assert agent.spec.model == "claude-opus-4-7"


def test_query_returns_response_with_non_empty_faculty_trace() -> None:
    agent = initiate("claude-opus-4-7", client_factory=_factory())
    response = agent.query("hello")
    assert isinstance(response, AgentResponse)
    assert response.text
    assert response.faculty_trace
    assert response.duration_ms >= 0


def test_query_rejects_empty_prompt() -> None:
    agent = initiate("claude-opus-4-7", client_factory=_factory())
    with pytest.raises(ValueError):
        agent.query("")
    with pytest.raises(ValueError):
        agent.query("   ")


def test_query_rejects_non_string_prompt() -> None:
    agent = initiate("claude-opus-4-7", client_factory=_factory())
    with pytest.raises(TypeError):
        agent.query(123)  # type: ignore[arg-type]


def test_query_rejects_non_positive_max_turns() -> None:
    agent = initiate("claude-opus-4-7", client_factory=_factory())
    with pytest.raises(ValueError):
        agent.query("hello", max_turns=0)
    with pytest.raises(ValueError):
        agent.query("hello", max_turns=-1)


def test_two_initiations_are_independent() -> None:
    agent_a = initiate("claude-opus-4-7", client_factory=_factory())
    agent_b = initiate("gpt-5-5", client_factory=_factory())

    agent_a._rectifier_events.append("event-A")
    agent_a._faculties.append("extra-A")

    assert "event-A" not in agent_b._rectifier_events
    assert "extra-A" not in agent_b._faculties
    assert agent_a.spec != agent_b.spec


def test_shutdown_is_idempotent() -> None:
    agent = initiate("claude-opus-4-7", client_factory=_factory())
    agent.shutdown()
    agent.shutdown()
    assert agent.status().persistent_trace_health == 0.0


def test_query_after_shutdown_raises() -> None:
    agent = initiate("claude-opus-4-7", client_factory=_factory())
    agent.shutdown()
    with pytest.raises(RuntimeError):
        agent.query("hello")


def test_unknown_identifier_raises_value_error_with_helpful_message() -> None:
    with pytest.raises(ValueError) as exc:
        initiate("not-a-real-llm")
    msg = str(exc.value)
    assert "not-a-real-llm" in msg
    assert "claude-opus-4-7" in msg


def test_initiation_error_is_value_error() -> None:
    assert issubclass(InitiationError, ValueError)


def test_empty_identifier_raises() -> None:
    with pytest.raises(ValueError):
        initiate("")
    with pytest.raises(ValueError):
        initiate("   ")


def test_non_string_non_spec_identifier_raises_type_error() -> None:
    with pytest.raises(TypeError):
        initiate(123)  # type: ignore[arg-type]


def test_generic_provider_slash_model_identifier_resolves() -> None:
    agent = initiate("ollama/qwen3-9b", client_factory=_factory())
    assert agent.spec.provider == "ollama"
    assert agent.spec.model == "qwen3-9b"


def test_malformed_generic_identifier_raises() -> None:
    with pytest.raises(InitiationError):
        initiate("/no-provider", client_factory=_factory())
    with pytest.raises(InitiationError):
        initiate("no-model/", client_factory=_factory())


def test_llmspec_passthrough() -> None:
    spec = LLMSpec(provider="custom", model="my-model")
    agent = initiate(spec, client_factory=_factory())
    assert agent.spec is spec


def test_status_reports_consolidated_faculties() -> None:
    agent = initiate("claude-opus-4-7", client_factory=_factory())
    status = agent.status()
    assert isinstance(status, AgentStatus)
    assert status.consolidated_faculties
    assert status.open_rectifier_events == 0
    assert 0.0 <= status.persistent_trace_health <= 1.0


def test_multi_llm_smoke_each_named_llm_initiates_with_mocked_provider() -> None:
    identifiers = [
        "claude-opus-4-7",
        "gpt-5-5",
        "llama-3-5-70b",
        "gemini-3-pro",
    ]
    factory = _factory(reply="r")
    for ident in identifiers:
        agent = initiate(ident, client_factory=factory)
        response = agent.query("structural delta probe")
        assert response.text.startswith("r::")
        assert response.faculty_trace


def test_module_level_factory_is_used_when_no_factory_passed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel: list[LLMSpec] = []

    def fake_make(spec: LLMSpec) -> LLMClient:
        sentinel.append(spec)
        return FakeLLMClient(spec)

    initiate_module = sys.modules["etzchaim.initiate"]
    monkeypatch.setattr(initiate_module, "_make_llm_client", fake_make)
    initiate("claude-opus-4-7")
    assert len(sentinel) == 1
    assert sentinel[0].model == "claude-opus-4-7"


def test_initiated_agent_rejects_wrong_spec_type() -> None:
    class FakeSpec:
        pass

    with pytest.raises(TypeError):
        InitiatedAgent(FakeSpec(), FakeLLMClient(LLMSpec("a", "b")))  # type: ignore[arg-type]


def test_initiated_agent_rejects_client_without_complete() -> None:
    class NotAClient:
        pass

    with pytest.raises(TypeError):
        InitiatedAgent(LLMSpec("a", "b"), NotAClient())  # type: ignore[arg-type]


def test_protocol_runtime_checkable() -> None:
    client = FakeLLMClient(LLMSpec("a", "b"))
    assert isinstance(client, LLMClient)
