---
public_name: SynthesisBridge
module_path: etzchaim/_internal/synthesis_bridge.py
spec_id: SPEC-002
version: 0.1.0
internal_name: daat
internal_source: "Etz Chaim Vital, Sha'ar HaKlalim 5:8"
internal_e_label: E2
status: draft
validated_by: []
---

# Synthesis Bridge

## Purpose

Cross-faculty bridge that synthesizes the outputs of the Insight faculty
and the Reason faculty into a single coherent claim. Acts as a meta-faculty
between the strategic configurations and the executive configurations.

## Public API

```python
class SynthesisBridge:
    def __init__(self, insight_source, reason_source) -> None: ...

    def synthesize(self, query: str) -> SynthesisResult:
        """Combine insight + causal reasoning into one claim with provenance."""
```

## Invariants

1. **No bypass** : the bridge cannot write directly to any faculty's state.
2. **Provenance preserved** : every output carries references to the insight
   and reason inputs that produced it.
3. **Determinism** : given identical inputs, the bridge produces identical
   output. No hidden randomness.

## Type signatures

```python
@dataclass
class SynthesisResult:
    claim: str
    insight_refs: list[str]
    reason_refs: list[str]
    confidence: float  # [0.0, 1.0]
```

## Tests

The implementation must include a `tests/test_synthesis_bridge.py` covering
at minimum :

- Construction with two valid sources.
- Synthesis returns a `SynthesisResult` with non-empty refs.
- Determinism : two calls with the same inputs return equal outputs.
- Refusal : insight or reason missing → raises `ValueError`.

## Non-goals

- This bridge does not implement causal inference itself; it composes the
  outputs of the Reason faculty (`causalengine/`).
- It does not implement insight generation; it composes outputs of the
  Insight faculty (`insightforge/`).
- It does not have its own learning trace; persistence lives in the source
  faculties.
