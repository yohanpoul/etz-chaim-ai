---
public_name: MetaOrchestrator
module_path: etzchaim/_internal/meta_orchestrator.py
spec_id: SPEC-001
version: 0.1.0
internal_name: keter
internal_source: "Etz Chaim Vital, Sha'ar Atik, perek 1-3"
internal_e_label: E2
status: draft
validated_by: []
---

# Meta Orchestrator

## Purpose

Top-level meta-faculty that coordinates all 10 cognitive faculties + 6 mature
configurations + 13 rectifiers. Holds invariants the system must never break,
delegates execution to lower-level configurations, and decides when to halt.

The orchestrator does not perform reasoning itself; it sequences which
faculty/configuration acts when. Think `init` for a Cognitive OS — it brings
faculties online in order and supervises lifecycle.

## Public API

```python
class MetaOrchestrator:
    def __init__(self, faculties: FacultyMap, configurations: ConfigurationMap) -> None: ...

    def boot(self) -> BootReport:
        """Bring faculties online in the prescribed sequential order."""

    def dispatch(self, event: AgentEvent) -> DispatchResult:
        """Route an event through the appropriate configuration."""

    def halt(self, reason: str) -> HaltRecord:
        """Stop all faculties; record the halt cause for post-mortem."""
```

## Invariants

1. **Sequential consolidation** : faculty `n` is brought online only after
   `n-1` has reported `consolidated`. No skipping.
2. **No direct writes to aggregate scores** : the orchestrator delegates to
   faculty channels; never updates `overall_score` itself.
3. **Halt is irreversible within one run** : once `halt(reason)` is called,
   `dispatch` returns `HALTED` until process restart.
4. **Determinism of boot order** : given the same faculty map, boot produces
   the same boot report regardless of clock or random state.

## Type signatures

```python
@dataclass
class BootReport:
    consolidated: list[str]
    failed: list[tuple[str, str]]  # (faculty_name, reason)
    duration_ms: int

@dataclass
class DispatchResult:
    configuration: str
    output: dict
    trace_ids: list[str]

@dataclass
class HaltRecord:
    reason: str
    timestamp: float
    last_dispatched_event: str | None
```

## Tests

`tests/test_meta_orchestrator.py` must cover :

- Boot consolidates faculties in order; out-of-order faculty raises.
- Dispatch routes by event type to the right configuration.
- Halt makes subsequent dispatch return `HALTED`.
- Determinism : two boots with the same input produce equal `BootReport`.
- No direct writes : the orchestrator never touches a configuration's
  aggregate state directly (verified by static check).

## Non-goals

- Does not implement faculty logic; faculties live in their own modules.
- Does not implement configuration composition; configurations are owned by
  `etzchaim/configurations/`.
- Does not implement rectification; rectifiers run inside the probe
  orchestrator (`etzchaim/probes/`).
