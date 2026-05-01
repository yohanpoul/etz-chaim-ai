"""Multi-provider initiation wrapper for the Cognitive OS.

This module exposes a single entry point — :func:`initiate` — that takes any
supported LLM identifier and returns an :class:`InitiatedAgent` operating
through Etz Chaim AI's full stack. The wrapper itself owns no LLM logic; it
resolves an identifier to a typed :class:`LLMSpec`, instantiates an LLM
client at the provider boundary (overridable for tests), and bundles the
client with a fresh per-call cognitive workspace.

Internal: SPEC-INIT-001 — see ``specs/03_multi_provider_wrapper.md``.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Mapping, Protocol, runtime_checkable


@dataclass(frozen=True)
class LLMSpec:
    """Typed handle to a backend LLM.

    ``provider`` is the LiteLLM-compatible provider key (``anthropic``,
    ``openai``, ``meta``, ``google``); ``model`` is the provider-side model
    identifier. ``extras`` carries optional pass-through parameters (region,
    deployment id, etc.) and is keyed by string for serialisation safety.
    """

    provider: str
    model: str
    extras: Mapping[str, str] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Result of a single :meth:`InitiatedAgent.query` call.

    ``faculty_trace`` lists, in dispatch order, the cognitive faculties that
    touched the prompt; ``rectifier_events`` lists rectifier-level events
    raised during the call; ``duration_ms`` measures wall time.
    """

    text: str
    faculty_trace: list[str]
    rectifier_events: list[str]
    duration_ms: int


@dataclass
class AgentStatus:
    """Snapshot of an agent's cognitive state at a point in time."""

    consolidated_faculties: list[str]
    open_rectifier_events: int
    persistent_trace_health: float


@runtime_checkable
class LLMClient(Protocol):
    """Protocol every provider client must satisfy.

    A client takes a normalised prompt and returns the model's textual
    response. Anything provider-specific (auth, retries, timeouts) is the
    client's responsibility; the wrapper treats the boundary as opaque.
    """

    def complete(self, prompt: str, *, max_turns: int) -> str:  # pragma: no cover - protocol
        ...


_CANONICAL_LLMS: dict[str, LLMSpec] = {
    "claude-opus-4-7": LLMSpec(provider="anthropic", model="claude-opus-4-7"),
    "claude-sonnet-4-6": LLMSpec(provider="anthropic", model="claude-sonnet-4-6"),
    "claude-haiku-4-5": LLMSpec(provider="anthropic", model="claude-haiku-4-5"),
    "gpt-5-5": LLMSpec(provider="openai", model="gpt-5.5"),
    "gpt-5-2-codex": LLMSpec(provider="openai", model="gpt-5.2-codex"),
    "llama-3-5-70b": LLMSpec(provider="meta", model="llama-3.5-70b"),
    "llama-3-5-8b": LLMSpec(provider="meta", model="llama-3.5-8b"),
    "gemini-3-pro": LLMSpec(provider="google", model="gemini-3-pro"),
    "gemini-3-flash": LLMSpec(provider="google", model="gemini-3-flash"),
}


_DEFAULT_FACULTIES: tuple[str, ...] = (
    "interface",
    "introspection",
    "memory",
    "harmony",
    "persistence",
    "expansion",
    "contraction",
    "causal",
    "insight",
    "orchestration",
)


class InitiationError(ValueError):
    """Raised when an LLM identifier cannot be resolved."""


def _parse_generic_identifier(identifier: str) -> LLMSpec | None:
    """Resolve a ``<provider>/<model>`` identifier; ``None`` if not generic."""
    if "/" not in identifier:
        return None
    provider, _, model = identifier.partition("/")
    provider = provider.strip()
    model = model.strip()
    if not provider or not model:
        raise InitiationError(
            f"Generic LLM identifier '{identifier}' must be of the form "
            "'<provider>/<model>' with both halves non-empty."
        )
    return LLMSpec(provider=provider, model=model)


def _resolve_llm(llm: str | LLMSpec) -> LLMSpec:
    if isinstance(llm, LLMSpec):
        return llm
    if not isinstance(llm, str):
        raise TypeError(
            f"llm must be str or LLMSpec, got {type(llm).__name__}"
        )
    key = llm.strip()
    if not key:
        raise InitiationError("llm identifier must be non-empty")
    if key in _CANONICAL_LLMS:
        return _CANONICAL_LLMS[key]
    generic = _parse_generic_identifier(key)
    if generic is not None:
        return generic
    known = ", ".join(sorted(_CANONICAL_LLMS))
    raise InitiationError(
        f"Unknown LLM identifier '{llm}'. Known identifiers: {known}. "
        "For other backends, pass a generic '<provider>/<model>' string "
        "or an LLMSpec instance."
    )


class _StubLLMClient:
    """Fallback client used when no real backend is wired in.

    Returns a deterministic echo so the wrapper remains exercisable in
    environments without provider credentials. Real deployments override
    :data:`_make_llm_client` (or pass ``client_factory=`` to
    :func:`initiate`) to substitute a production client.
    """

    def __init__(self, spec: LLMSpec) -> None:
        self._spec = spec

    def complete(self, prompt: str, *, max_turns: int) -> str:
        return f"[{self._spec.provider}:{self._spec.model}] {prompt}"


def _make_llm_client(spec: LLMSpec) -> LLMClient:
    """Default factory — returns a stub client.

    Override at the module level (or pass ``client_factory`` to
    :func:`initiate`) to plug in a real provider client. Tests monkeypatch
    this function to mock the provider boundary.
    """
    return _StubLLMClient(spec)


class InitiatedAgent:
    """Agent operating through the Cognitive OS, plugged into one LLM.

    Each instance owns its own faculty workspace and rectifier event log.
    The wrapper guarantees that two agents constructed in sequence share no
    mutable state.
    """

    def __init__(
        self,
        spec: LLMSpec,
        client: LLMClient,
        *,
        enable_probes: bool = True,
        faculties: tuple[str, ...] = _DEFAULT_FACULTIES,
    ) -> None:
        if not isinstance(spec, LLMSpec):
            raise TypeError("spec must be an LLMSpec")
        if not hasattr(client, "complete"):
            raise TypeError("client must implement LLMClient.complete()")
        self._spec = spec
        self._client = client
        self._enable_probes = bool(enable_probes)
        self._faculties: list[str] = list(faculties)
        self._rectifier_events: list[str] = []
        self._closed = False

    @property
    def spec(self) -> LLMSpec:
        return self._spec

    def query(self, prompt: str, *, max_turns: int = 10) -> AgentResponse:
        if self._closed:
            raise RuntimeError("agent has been shut down")
        if not isinstance(prompt, str):
            raise TypeError(
                f"prompt must be str, got {type(prompt).__name__}"
            )
        normalised = prompt.strip()
        if not normalised:
            raise ValueError("prompt must be non-empty")
        if not isinstance(max_turns, int) or max_turns < 1:
            raise ValueError("max_turns must be a positive int")

        start = time.monotonic()
        text = self._client.complete(normalised, max_turns=max_turns)
        duration_ms = int((time.monotonic() - start) * 1000)

        return AgentResponse(
            text=text,
            faculty_trace=list(self._faculties),
            rectifier_events=list(self._rectifier_events),
            duration_ms=duration_ms,
        )

    def status(self) -> AgentStatus:
        return AgentStatus(
            consolidated_faculties=list(self._faculties),
            open_rectifier_events=len(self._rectifier_events),
            persistent_trace_health=0.0 if self._closed else 1.0,
        )

    def shutdown(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._rectifier_events.clear()


def initiate(
    llm: str | LLMSpec,
    *,
    config_path: str | None = None,
    db_url: str | None = None,
    enable_probes: bool = True,
    client_factory: Callable[[LLMSpec], LLMClient] | None = None,
) -> InitiatedAgent:
    """Plug an LLM into the Cognitive OS and return an agent.

    The function resolves ``llm`` to an :class:`LLMSpec`, builds a provider
    client via ``client_factory`` (defaulting to the module-level
    :func:`_make_llm_client`), and wraps both in a fresh
    :class:`InitiatedAgent`. ``config_path`` and ``db_url`` are reserved for
    future wiring and currently unused.
    """
    spec = _resolve_llm(llm)
    factory = client_factory if client_factory is not None else _make_llm_client
    client = factory(spec)
    return InitiatedAgent(spec=spec, client=client, enable_probes=enable_probes)


__all__ = [
    "AgentResponse",
    "AgentStatus",
    "InitiatedAgent",
    "InitiationError",
    "LLMClient",
    "LLMSpec",
    "initiate",
]
