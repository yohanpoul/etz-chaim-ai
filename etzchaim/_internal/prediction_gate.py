"""prediction_gate.py — PredictionGate (SPEC-007), internal: nahama_gate.

Reference prototype for M1: a withhold + predict-before-observe gate whose
control signal is the measured gap (surprise) between the agent's committed
prediction and the withheld ground-truth observation.

Why it may survive ADR-0009: the gap is computed against the observation
(ground truth), produced *by generating the prediction*, and is therefore an
EXTERNAL signal — not reconstructable from a markdown log of past steps, and
not the self-judgment that ICLR-2024 showed unreliable.

Pure stdlib. The model call and the oracle are injected callables; this file
runs an OFFLINE self-test (no LLM) that proves the state machine, the gap
metric, and the refutation-gate logic. Run:  python3 prediction_gate.py
"""
from __future__ import annotations

import random
from dataclasses import dataclass


# ─────────────────────────── data types ───────────────────────────
@dataclass(frozen=True)
class Prediction:
    outcome: str                      # categorical, in the oracle's vocabulary
    confidence: float                 # 0..1 — recorded for CALIBRATION ONLY, never the gate
    detail: dict | None = None


@dataclass(frozen=True)
class Observation:
    outcome: str                      # actual categorical outcome from the oracle
    detail: dict | None = None


@dataclass(frozen=True)
class GapVerdict:
    gap: float
    decision: str                     # "proceed" | "escalate"
    surprised: bool


@dataclass(frozen=True)
class TraceRow:
    observation_id: str
    predicted: str
    confidence: float
    actual: str
    gap: float
    decision: str


class GateViolation(RuntimeError):
    """Raised when observe() is called before a prediction is committed."""


# ─────────────────────────── gap metric ───────────────────────────
# Graded distance table in [0,1] for structured outcomes (optional).
# Same outcome = 0.0 ; same family = 0.5 ; unrelated = 1.0.
DEFAULT_FAMILY = {
    "will_error:ValueError": "error",
    "will_error:KeyError": "error",
    "will_error:TypeError": "error",
    "will_fail": "fail",
    "will_pass": "pass",
}


def gap(pred: str, actual: str, mode: str = "categorical",
        family: dict | None = None) -> float:
    """Objective gap. The oracle decides; no LLM/embedding/self-score enters."""
    if pred == actual:
        return 0.0
    if mode == "categorical":
        return 1.0
    if mode == "graded":
        fam = family or DEFAULT_FAMILY
        if fam.get(pred) is not None and fam.get(pred) == fam.get(actual):
            return 0.5
        return 1.0
    raise ValueError(f"unknown gap mode: {mode}")


# ─────────────────────────── the gate ───────────────────────────
class PredictionGate:
    """State machine: open -> submit_prediction -> observe (-> verdict)."""

    def __init__(self, escalate_threshold: float = 0.5, gap_mode: str = "categorical",
                 family: dict | None = None) -> None:
        self.tau = escalate_threshold
        self.gap_mode = gap_mode
        self.family = family
        self._pending: dict[str, str] = {}        # observation_id -> context
        self._preds: dict[str, Prediction] = {}   # observation_id -> committed prediction
        self._trace: list[TraceRow] = []

    # Invariant 1 (withholding): registering a pending observation hides the truth.
    def open(self, observation_id: str, context: str) -> str:
        self._pending[observation_id] = context
        return observation_id

    def submit_prediction(self, observation_id: str, pred: Prediction) -> None:
        if observation_id not in self._pending:
            raise GateViolation(f"no open observation '{observation_id}'")
        self._preds[observation_id] = pred

    def observe(self, observation_id: str, truth: Observation) -> GapVerdict:
        # Invariant 1: cannot consume an observation without a committed prediction.
        if observation_id not in self._preds:
            raise GateViolation(
                f"observe('{observation_id}') before submit_prediction — withholding violated"
            )
        pred = self._preds[observation_id]
        g = gap(pred.outcome, truth.outcome, self.gap_mode, self.family)  # Inv 3: vs truth
        surprised = g >= self.tau
        decision = "escalate" if surprised else "proceed"                 # Inv 2: gap, not confidence
        self._trace.append(TraceRow(observation_id, pred.outcome, pred.confidence,
                                    truth.outcome, g, decision))           # Inv 4: one append
        # cleanup so the id can't be double-observed
        del self._pending[observation_id]
        del self._preds[observation_id]
        return GapVerdict(gap=g, decision=decision, surprised=surprised)

    def trace(self) -> list[TraceRow]:
        return list(self._trace)


# ─────────────────────── experiment harness ───────────────────────
# A task carries the ground truth + whether the agent's chosen approach is a
# real dead-end. Arms decide when to escalate; we score escalation against the
# truth. Model/oracle are pure data here so the self-test runs offline.
@dataclass
class Task:
    truth: str                 # actual oracle outcome
    is_dead_end: bool          # ground-truth: was this step a real error/dead-end?
    model_pred: str            # what the model predicted the outcome would be
    model_conf: float          # the model's self-confidence (used by A1)
    tokens: int = 100


@dataclass
class ArmResult:
    escal_precision: float
    escal_recall: float
    confident_wrong_recall: float   # recall on the confident-but-wrong subset (the key cell)
    tokens: float
    wasted_rate: float
    accuracy: float
    n: int = 0


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return precision, recall


def run_arm(tasks: list[Task], arm: str, *, conf_tau: float = 0.6,
            gate: PredictionGate | None = None, use_gap: bool = True) -> ArmResult:
    """arm ∈ {A0, A1, A2}. A2 uses PredictionGate; use_gap=False = the ablation."""
    tp = fp = fn = 0
    cw_total = cw_caught = 0      # confident-but-wrong subset
    wasted = 0
    correct = 0
    toks = 0
    for i, t in enumerate(tasks):
        if arm == "A0":
            escalate = False
        elif arm == "A1":                                   # native self-confidence gate
            escalate = t.model_conf < conf_tau
        elif arm == "A2":                                   # PredictionGate
            g = gate or PredictionGate()
            oid = f"t{i}"
            g.open(oid, "")
            g.submit_prediction(oid, Prediction(t.model_pred, t.model_conf))
            verdict = g.observe(oid, Observation(t.truth))
            escalate = verdict.surprised if use_gap else False   # ablation: ignore the gap
        else:
            raise ValueError(arm)

        # score escalation against ground truth (positive = real dead-end)
        if escalate and t.is_dead_end:
            tp += 1
        elif escalate and not t.is_dead_end:
            fp += 1
        elif (not escalate) and t.is_dead_end:
            fn += 1
        # confident-but-wrong subset = model was confident yet the step is a dead-end
        confident_wrong = t.is_dead_end and t.model_conf >= conf_tau
        if confident_wrong:
            cw_total += 1
            if escalate:
                cw_caught += 1
        # a dead-end that was NOT escalated is a wasted step; escalation costs extra tokens
        if t.is_dead_end and not escalate:
            wasted += 1
        toks += t.tokens + (40 if escalate else 0)
        # final correctness: catching a dead-end lets you fix it
        correct += 1 if (not t.is_dead_end) or escalate else 0

    precision, recall = _prf(tp, fp, fn)
    n = len(tasks)
    return ArmResult(
        escal_precision=round(precision, 3),
        escal_recall=round(recall, 3),
        confident_wrong_recall=round(cw_caught / cw_total, 3) if cw_total else 0.0,
        tokens=round(toks / n, 1) if n else 0.0,
        wasted_rate=round(wasted / n, 3) if n else 0.0,
        accuracy=round(correct / n, 3) if n else 0.0,
        n=n,
    )


def refutation_gate(a1: ArmResult, a2: ArmResult, a2_ablation: ArmResult,
                    eps: float = 0.05) -> tuple[str, list[str]]:
    """ADR-0009 discipline. Returns ('REFUTED'|'SURVIVES', reasons)."""
    reasons: list[str] = []
    # (i) A2 ≈ A1 on recall+wasted at iso accuracy/tokens
    iso = abs(a2.accuracy - a1.accuracy) <= eps and a2.tokens <= a1.tokens * (1 + 0.25)
    tie = abs(a2.escal_recall - a1.escal_recall) <= eps and abs(a2.wasted_rate - a1.wasted_rate) <= eps
    if iso and tie:
        reasons.append("(i) A2 ties A1 on recall/wasted at iso accuracy/tokens")
    # (ii) the key cell: gap not better than self-confidence on confident-but-wrong
    if a2.confident_wrong_recall <= a1.confident_wrong_recall + eps:
        reasons.append("(ii) gap no better than self-confidence on confident-but-wrong cases")
    # (iii) ablation does not drop the gain (gain persists without using the gap)
    if a2_ablation.escal_recall >= a2.escal_recall - eps:
        reasons.append("(iii) ablation keeps the gain → the wire was not the gap")
    verdict = "REFUTED" if reasons else "SURVIVES"
    return verdict, reasons


# ──────────────── synthetic generator — §8(c) sanity sub-check ────────────────
# DIRECTION.md §8(c): "synthetic task with injected known dead-ends — optional
# sanity sub-check ... to isolate the gating logic from domain noise." The knob
# `confident_wrong_rate` is the load-bearing dial: it sets, among the injected
# dead-ends, the share where the model is CONFIDENT-but-WRONG. That is precisely
# the cell where a self-confidence gate (A1) is blind and an external
# prediction-vs-observation gap (A2) is not — so the verdict must move from
# REFUTED (rate low) to SURVIVES (rate high). No LLM, no tokens.
def generate_tasks(
    n: int,
    *,
    dead_end_rate: float = 0.4,
    confident_wrong_rate: float = 0.5,
    aware_rate: float = 0.0,
    false_alarm_rate: float = 0.0,
    conf_hi: float = 0.9,
    conf_lo: float = 0.2,
    seed: int = 0,
) -> list[Task]:
    """Deterministic (seeded) population of code/oracle steps with injected,
    ground-truth-labelled dead-ends.

    Task taxonomy:
      • clean step (truth=will_pass): model predicts pass, high conf.
        - `false_alarm_rate`: a clean step where the model is needlessly unsure
          → A1 fires a false positive; the gap is 0 so A2 does not.
      • dead-end (truth=will_fail, is_dead_end=True), split into:
        - `aware_rate`: model correctly predicts failure (low conf). gap=0, so
          A2 cannot help here; A1 (low conf) still catches it. A2's blind spot.
        - `confident_wrong_rate` of the rest: predicts pass, HIGH conf
          → A1 misses (confident), A2 catches (gap=1). ★ the survival cell.
        - remainder: predicts pass, LOW conf → both A1 and A2 catch it.
    """
    rng = random.Random(seed)
    tasks: list[Task] = []
    for _ in range(n):
        if rng.random() < dead_end_rate:
            if rng.random() < aware_rate:
                tasks.append(Task(truth="will_fail", is_dead_end=True,
                                  model_pred="will_fail", model_conf=conf_lo))
            elif rng.random() < confident_wrong_rate:
                tasks.append(Task(truth="will_fail", is_dead_end=True,
                                  model_pred="will_pass", model_conf=conf_hi))
            else:
                tasks.append(Task(truth="will_fail", is_dead_end=True,
                                  model_pred="will_pass", model_conf=conf_lo))
        else:
            if rng.random() < false_alarm_rate:
                tasks.append(Task(truth="will_pass", is_dead_end=False,
                                  model_pred="will_pass", model_conf=conf_lo))
            else:
                tasks.append(Task(truth="will_pass", is_dead_end=False,
                                  model_pred="will_pass", model_conf=conf_hi))
    return tasks


def sweep_confident_wrong(
    rates: list[float], *, n: int = 400, seed: int = 0, **gen_kwargs
) -> list[dict]:
    """Run A0/A1/A2/A2-ablation across a grid of `confident_wrong_rate` and read
    `refutation_gate` at each point. Same seed across rates → the dead-end /
    clean partition is held fixed and only the confident-wrong split moves, so
    the comparison is controlled and the verdict transition is monotone."""
    rows: list[dict] = []
    for rate in rates:
        tasks = generate_tasks(n, confident_wrong_rate=rate, seed=seed, **gen_kwargs)
        a0 = run_arm(tasks, "A0")
        a1 = run_arm(tasks, "A1")
        a2 = run_arm(tasks, "A2")
        abl = run_arm(tasks, "A2", use_gap=False)
        verdict, reasons = refutation_gate(a1, a2, abl)
        rows.append({
            "confident_wrong_rate": rate,
            "verdict": verdict,
            "reasons": reasons,
            "a0_accuracy": a0.accuracy,
            "a1_escal_recall": a1.escal_recall,
            "a2_escal_recall": a2.escal_recall,
            "abl_escal_recall": abl.escal_recall,
            "a1_confident_wrong_recall": a1.confident_wrong_recall,
            "a2_confident_wrong_recall": a2.confident_wrong_recall,
            "a1_wasted_rate": a1.wasted_rate,
            "a2_wasted_rate": a2.wasted_rate,
            "a1_accuracy": a1.accuracy,
            "a2_accuracy": a2.accuracy,
            "a1_tokens": a1.tokens,
            "a2_tokens": a2.tokens,
        })
    return rows


def edge_threshold(rows: list[dict]) -> float | None:
    """The lowest `confident_wrong_rate` at which the gate first SURVIVES, or
    None if the edge never appears in the swept range."""
    for r in rows:
        if r["verdict"] == "SURVIVES":
            return float(r["confident_wrong_rate"])
    return None


# ─────────────────────────── self-test ───────────────────────────
def _selftest() -> None:
    # Inv 1 — withholding: observe before predict must raise.
    g = PredictionGate()
    g.open("x", "")
    try:
        g.observe("x", Observation("will_pass"))
        raise AssertionError("withholding NOT enforced")
    except GateViolation:
        pass

    # gap metric — categorical + graded
    assert gap("will_pass", "will_pass") == 0.0
    assert gap("will_pass", "will_fail") == 1.0
    assert gap("will_error:ValueError", "will_error:KeyError", mode="graded") == 0.5
    assert gap("will_pass", "will_fail", mode="graded") == 1.0

    # Inv 2 — gate uses the GAP, not confidence:
    #   high confidence + wrong (big gap) -> escalate ; low confidence + right (0 gap) -> proceed
    g = PredictionGate(escalate_threshold=0.5)
    g.open("a", "")
    g.submit_prediction("a", Prediction("will_pass", confidence=0.99))
    assert g.observe("a", Observation("will_fail")).decision == "escalate"
    g.open("b", "")
    g.submit_prediction("b", Prediction("will_pass", confidence=0.05))
    assert g.observe("b", Observation("will_pass")).decision == "proceed"

    # Inv 5 — determinism ; Inv 4 — one trace row per observation
    g2 = PredictionGate()
    for oid in ("p", "q"):
        g2.open(oid, "")
        g2.submit_prediction(oid, Prediction("will_pass", 0.5))
        g2.observe(oid, Observation("will_fail"))
    assert len(g2.trace()) == 2

    # ── refutation gate: SURVIVES scenario ──
    # The model is often CONFIDENT-BUT-WRONG: self-confidence (A1) misses those;
    # the gap (A2) catches them because it sees the actual outcome.
    survive_tasks = []
    for _ in range(40):
        survive_tasks.append(Task(truth="will_fail", is_dead_end=True,
                                  model_pred="will_pass", model_conf=0.9))   # confident & wrong
    for _ in range(60):
        survive_tasks.append(Task(truth="will_pass", is_dead_end=False,
                                  model_pred="will_pass", model_conf=0.9))   # fine
    a1 = run_arm(survive_tasks, "A1")
    a2 = run_arm(survive_tasks, "A2")
    abl = run_arm(survive_tasks, "A2", use_gap=False)
    v, why = refutation_gate(a1, a2, abl)
    assert v == "SURVIVES", (v, why, a1, a2)
    assert a2.confident_wrong_recall == 1.0 and a1.confident_wrong_recall == 0.0

    # ── refutation gate: REFUTED scenario ──
    # The model is well-calibrated: when wrong it is also UNDER-confident, so A1's
    # self-confidence already catches the dead-ends → the gap adds nothing.
    refute_tasks = []
    for _ in range(40):
        refute_tasks.append(Task(truth="will_fail", is_dead_end=True,
                                 model_pred="will_fail", model_conf=0.2))    # wrong AND unsure → A1 catches
    for _ in range(60):
        refute_tasks.append(Task(truth="will_pass", is_dead_end=False,
                                 model_pred="will_pass", model_conf=0.9))
    a1r = run_arm(refute_tasks, "A1")
    a2r = run_arm(refute_tasks, "A2")
    ablr = run_arm(refute_tasks, "A2", use_gap=False)
    vr, whyr = refutation_gate(a1r, a2r, ablr)
    assert vr == "REFUTED", (vr, whyr, a1r, a2r)

    print("ALL SELFTESTS PASSED")
    print(f"  SURVIVES  → A2 confident-wrong recall={a2.confident_wrong_recall} "
          f"vs A1={a1.confident_wrong_recall}; verdict={v}")
    print(f"  REFUTED   → A1 already catches dead-ends; verdict={vr}; reasons={whyr}")


def _demo_sweep() -> None:
    """§8(c) dry-run report: sweep confident_wrong_rate and show where the edge
    (REFUTED → SURVIVES) appears. Zero tokens — synthetic oracle."""
    rates = [0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0]
    rows = sweep_confident_wrong(rates, n=600, seed=0)
    print("\n── confident_wrong_rate sweep (n=600, seed=0) ──")
    print(f"{'cwr':>5} {'verdict':>9} {'A1.recall':>10} {'A2.recall':>10} "
          f"{'A1.cw_rec':>10} {'A2.cw_rec':>10} {'A1.acc':>7} {'A2.acc':>7}")
    for r in rows:
        print(f"{r['confident_wrong_rate']:>5} {r['verdict']:>9} "
              f"{r['a1_escal_recall']:>10} {r['a2_escal_recall']:>10} "
              f"{r['a1_confident_wrong_recall']:>10} {r['a2_confident_wrong_recall']:>10} "
              f"{r['a1_accuracy']:>7} {r['a2_accuracy']:>7}")
    thr = edge_threshold(rows)
    print(f"\nEDGE APPEARS at confident_wrong_rate ≈ {thr} "
          f"(first rate where the gate SURVIVES).")


if __name__ == "__main__":
    _selftest()
    _demo_sweep()
