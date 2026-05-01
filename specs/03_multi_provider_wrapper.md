---
public_name: AgentInitiation
module_path: etzchaim/initiate.py
spec_id: SPEC-INIT-001
version: 0.1.0
status: draft
validated_by: []
---

# Multi-Provider Initiation Wrapper

## Purpose

Single public entry point that takes any frontier LLM identifier and returns
an agent operating through Etz Chaim AI's full stack (10 faculties,
6 configurations, 13 rectifiers, persistent traces).

This is the "plug-in" surface the README promises. After Phase 3, users do :

```python
from etzchaim import initiate

agent = initiate(llm="claude-opus-4-7")
response = agent.query("What are your typical failure modes ?")
```

## Public API

```python
def initiate(
    llm: str | LLMSpec,
    *,
    config_path: str | None = None,
    db_url: str | None = None,
    enable_probes: bool = True,
) -> InitiatedAgent:
    """Plug an LLM into the Cognitive OS and return an agent."""

class InitiatedAgent:
    def query(self, prompt: str, *, max_turns: int = 10) -> AgentResponse: ...
    def status(self) -> AgentStatus: ...
    def shutdown(self) -> None: ...
```

## Supported LLM identifiers (v1.0)

- `claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5`
- `gpt-5-5`, `gpt-5-2-codex`
- `llama-3-5-70b`, `llama-3-5-8b`
- `gemini-3-pro`, `gemini-3-flash`

Plus generic LiteLLM identifiers (`provider/model`) for arbitrary backends.

## Invariants

1. **Same delta structure across LLMs** : the structural transformation
   produced by the Cognitive OS must produce comparable metric deltas
   across all four named LLMs (within statistical noise).
2. **No leak across initiations** : two `initiate()` calls return fully
   independent agents; faculty state is not shared.
3. **Idempotent shutdown** : `agent.shutdown()` is safe to call multiple
   times; the second call is a no-op.

## Type signatures

```python
@dataclass(frozen=True)
class LLMSpec:
    provider: str
    model: str
    extras: dict[str, str] = field(default_factory=dict)

@dataclass
class AgentResponse:
    text: str
    faculty_trace: list[str]   # which faculties touched the prompt
    rectifier_events: list[str]
    duration_ms: int

@dataclass
class AgentStatus:
    consolidated_faculties: list[str]
    open_rectifier_events: int
    persistent_trace_health: float
```

## Tests

`tests/test_initiate.py` must cover :

- `initiate("claude-opus-4-7")` returns an `InitiatedAgent`.
- `agent.query("hello")` returns `AgentResponse` with non-empty
  `faculty_trace`.
- Two initiations are independent (modify A, B unaffected).
- `shutdown()` is idempotent.
- Unknown LLM identifier raises `ValueError` with a helpful message.
- Multi-LLM smoke : initiate each of the 4 named LLMs (mocked at the
  provider boundary), verify structural delta is computed.

## Non-goals

- Does not implement individual provider clients; uses LiteLLM under the hood.
- Does not include billing/quota; that is the user's responsibility.
- Does not persist conversation transcripts; the daemon handles persistence.
