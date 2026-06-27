---
public_name: PredictionGate
module_path: etzchaim/_internal/prediction_gate.py
spec_id: SPEC-007
version: 0.1.0
internal_name: nahama_gate
internal_source: "Ramchal, Da'at Tevunot (nahama d'kisufa) ; Lurianic hester panim ; Etz Chaim Vital"
internal_e_label: E2
status: draft
validated_by: []
---

# Prediction Gate

## Purpose

Before the agent consumes any **consequential observation** (tool result, retrieved
document, test/oracle outcome), it must **commit a prediction + confidence**; the
observation is **withheld** until that commit. The **measured gap** (surprise) between
prediction and observation becomes an **externally-grounded control signal**:

- small gap → proceed cheaply;
- large gap → escalate (more compute / replan / flag for review).

The point that distinguishes this from existing gating: the signal is grounded in the
**observation itself (ground truth)**, not in the model's re-judgment of its own answer.
This sidesteps the documented unreliability of LLM self-correction (Huang et al., ICLR
2024) and the self-preference bias — a self-confidence gate inherits both; a
prediction-vs-observation gap does not.

> **Internal origin (E2, informational).** Structural analogy with *nahama d'kisufa*
> (« the bread of shame »): a receiver that takes a result without having co-produced it
> is in a structurally impoverished state (no derivation chain → no robustness/transfer).
> The fix is to make the receiver **earn** the result by producing its own attempt first.
> No interiority, merit, or experience is attributed to the agent — only a measurable
> derivation gap. Not required to use the module.

## Public API

```python
class PredictionGate:
    def __init__(self, escalate_threshold: float = 0.5) -> None: ...

    def open(self, observation_id: str, context: str) -> PredictionRequest:
        """Register a pending consequential observation; the result is now WITHHELD."""

    def submit_prediction(self, observation_id: str, pred: Prediction) -> None:
        """Commit the agent's prediction + confidence BEFORE it may observe."""

    def observe(self, observation_id: str, truth: Observation) -> GapVerdict:
        """Reveal the truth, compute the gap, and return the control verdict.
        Raises GateViolation if no prediction was committed for this id."""

    def trace(self) -> list[TraceRow]:
        """Append-only record of (prediction, observation, gap, decision)."""
```

## Invariants

1. **Withholding** — no observation is released to the agent before a prediction is
   committed for that `observation_id`. `observe()` before `submit_prediction()` raises
   `GateViolation`.
2. **External signal** — the escalation decision is a function of the measured gap
   `g = gap(prediction, observation)`, never of the predictor's self-confidence alone.
   (Confidence is recorded for *calibration analysis*, not used as the gate.)
3. **Ground-truth grounding** — `gap` is computed against the observation, not against a
   model re-evaluation of its own prediction.
4. **Traceability** — every `(observation_id, prediction, confidence, observation, gap,
   decision)` is appended to the trace exactly once.
5. **Determinism** — given the same prediction, observation and threshold, `observe()`
   returns the same `GapVerdict`.

## Type signatures

```python
@dataclass(frozen=True)
class Prediction:
    outcome: str            # categorical predicted outcome (oracle vocabulary)
    confidence: float       # 0..1, recorded for calibration ONLY (not the gate)
    detail: dict | None = None

@dataclass(frozen=True)
class Observation:
    outcome: str            # categorical actual outcome from the oracle
    detail: dict | None = None

@dataclass(frozen=True)
class GapVerdict:
    gap: float              # 0..1 ; 0 = predicted == actual
    decision: str           # "proceed" | "escalate"
    surprised: bool         # gap >= escalate_threshold

@dataclass(frozen=True)
class TraceRow:
    observation_id: str
    predicted: str
    confidence: float
    actual: str
    gap: float
    decision: str
```

## Gap metric (objective — the load-bearing definition)

The prediction is the **categorical outcome of the next action**, in the **oracle's own
vocabulary**. For a code/debug reference oracle:

- `outcome ∈ {will_pass, will_fail, will_error:<ErrType>}` for "run this candidate";
- or `{exists, absent}` / `{matches_ref, differs}` for a lookup against the reference.

`gap` is then **fully objective — the oracle decides**:

- **categorical** (default): `gap = 0.0 if predicted.outcome == actual.outcome else 1.0`;
- **graded** (optional): for structured outcomes (e.g. predicted error type vs actual),
  a fixed distance table in `[0,1]` (same type = 0, same family = 0.5, unrelated = 1.0).

No embedding, no LLM judge, no self-score enters the gap. This is what makes the signal
**external** and immune to the ADR-0009 information-equivalence collapse: the gap is
produced *by generating the prediction against a withheld truth* and cannot be
reconstructed from a markdown log of past steps.

## Falsifiable experiment (the reason this spec exists)

**Domain.** Multi-session, context-wiped **code/debug against a reference oracle**
(objective dead-end / contradiction / outcome labels — the oracle decides), as in
DIRECTION.md §6.

**Arms.**

- **A0** — bare agent: observes results immediately, no prediction.
- **A1 — baseline to beat (the ADR-0009 trap)** — native interleaved-thinking
  ("think before the tool") + **self-confidence gating** + Adaptive-RAG
  ("answer from memory first"). If A1 ties A2, the edge does not exist.
- **A2 — PredictionGate** — withhold + commit prediction + measured-gap escalation.

**Metrics (per task, across N sessions).**

1. **Escalation precision/recall** — does the gap predict real errors **better than the
   A1 self-confidence signal**, *especially on confident-but-wrong cases*? ← key metric.
2. **Tokens/$ to oracle pass** at iso-accuracy (compute efficiency).
3. **Wasted-step / dead-end re-attempt rate.**
4. **Final correctness.**

**Ablation (isolates the wire).** Keep the prediction step but **ignore the gap** (no
escalation from it) → A2 degenerates to "think-before-acting". If the gain **vanishes**,
the gap-signal is the cause. If it **persists**, the gain was only thinking-first →
**collapse to native, REFUTED**.

**Refutation criterion (REFUTED → pivot).** Refuted if **any** holds:
(i) A2 ≈ A1 on metrics 1+3 at iso 2+4; or
(ii) the gap is no better calibrated than A1 self-confidence on confident-but-wrong cases;
or (iii) the ablation does not drop the gain.
**Survival space** = A2 beats A1 *precisely where self-confidence fails*, due to the gap's
external grounding.

## Tests

`tests/test_prediction_gate.py` must cover:

- **Withholding** — `observe()` before `submit_prediction()` raises `GateViolation`.
- **Gap correctness** — categorical and graded gap match the table on fixed inputs.
- **Gate uses gap, not confidence** — a high-confidence + wrong prediction with large gap
  yields `escalate`; a low-confidence + correct prediction with zero gap yields `proceed`.
- **Determinism** — repeated `observe()` on equal inputs returns an equal `GapVerdict`.
- **Trace** — exactly one append per observation; trace is the full ledger.
- **Refutation gate logic** — given synthetic A1/A2/ablation result sets, the
  `refutation_gate()` returns REFUTED on (i)/(ii)/(iii) and SURVIVES otherwise.

## Non-goals

- Does **not** implement the model call or the oracle; both are injected callables
  (plug into `etzchaim/_internal/multi_provider_wrapper`).
- Does **not** perform self-confidence calibration; that is the **A1 baseline** it must beat.
- Does **not** decide *what* to escalate to; it emits `escalate` and leaves the policy
  (more compute / bigger model / replan) to the orchestrator.
