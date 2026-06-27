"""Tests for PredictionGate (SPEC-007).

Covers the six cases from specs/07_prediction_gate.md §Tests plus the synthetic
task generator that drives the §8(c) sanity sub-check (DIRECTION.md): a knobbed
`confident_wrong_rate` must move `refutation_gate` from REFUTED (low) to SURVIVES
(high). No LLM, no tokens — pure offline dry-run.
"""
from __future__ import annotations

import pytest

from etzchaim._internal import prediction_gate as pg
from etzchaim._internal.prediction_gate import (
    GapVerdict,
    GateViolation,
    Observation,
    Prediction,
    PredictionGate,
    gap,
    refutation_gate,
    run_arm,
)


# ─────────────────── spec §Tests case 1 — Withholding ───────────────────
class TestWithholding:
    def test_observe_before_predict_raises(self):
        g = PredictionGate()
        g.open("x", "")
        with pytest.raises(GateViolation):
            g.observe("x", Observation("will_pass"))

    def test_submit_on_unopened_id_raises(self):
        g = PredictionGate()
        with pytest.raises(GateViolation):
            g.submit_prediction("nope", Prediction("will_pass", 0.5))


# ─────────────────── spec §Tests case 2 — Gap correctness ───────────────────
class TestGapMetric:
    def test_categorical(self):
        assert gap("will_pass", "will_pass") == 0.0
        assert gap("will_pass", "will_fail") == 1.0

    def test_graded_same_family(self):
        assert gap("will_error:ValueError", "will_error:KeyError", mode="graded") == 0.5

    def test_graded_same_outcome_is_zero(self):
        assert gap("will_error:ValueError", "will_error:ValueError", mode="graded") == 0.0

    def test_graded_unrelated_is_one(self):
        assert gap("will_pass", "will_fail", mode="graded") == 1.0

    def test_unknown_mode_raises(self):
        with pytest.raises(ValueError):
            gap("will_pass", "will_fail", mode="bogus")


# ───────────── spec §Tests case 3 — Gate uses gap, not confidence ─────────────
class TestGateUsesGapNotConfidence:
    def test_high_confidence_wrong_escalates(self):
        g = PredictionGate(escalate_threshold=0.5)
        g.open("a", "")
        g.submit_prediction("a", Prediction("will_pass", confidence=0.99))
        assert g.observe("a", Observation("will_fail")).decision == "escalate"

    def test_low_confidence_correct_proceeds(self):
        g = PredictionGate(escalate_threshold=0.5)
        g.open("b", "")
        g.submit_prediction("b", Prediction("will_pass", confidence=0.05))
        assert g.observe("b", Observation("will_pass")).decision == "proceed"


# ─────────────────── spec §Tests case 4 — Determinism ───────────────────
class TestDeterminism:
    def test_equal_inputs_give_equal_verdict(self):
        v1 = self._observe_once()
        v2 = self._observe_once()
        assert v1 == v2
        assert isinstance(v1, GapVerdict)

    @staticmethod
    def _observe_once() -> GapVerdict:
        g = PredictionGate(escalate_threshold=0.5)
        g.open("d", "")
        g.submit_prediction("d", Prediction("will_pass", 0.7))
        return g.observe("d", Observation("will_fail"))


# ─────────────────── spec §Tests case 5 — Trace ───────────────────
class TestTrace:
    def test_one_append_per_observation(self):
        g = PredictionGate()
        for oid in ("p", "q", "r"):
            g.open(oid, "")
            g.submit_prediction(oid, Prediction("will_pass", 0.5))
            g.observe(oid, Observation("will_fail"))
        rows = g.trace()
        assert len(rows) == 3
        assert [r.observation_id for r in rows] == ["p", "q", "r"]
        assert all(r.gap == 1.0 and r.decision == "escalate" for r in rows)

    def test_trace_is_copy_not_internal_ref(self):
        g = PredictionGate()
        g.open("a", "")
        g.submit_prediction("a", Prediction("will_pass", 0.5))
        g.observe("a", Observation("will_pass"))
        snap = g.trace()
        snap.clear()
        assert len(g.trace()) == 1  # mutating the snapshot must not touch the ledger


# ─────────────── spec §Tests case 6 — Refutation gate logic ───────────────
class TestRefutationGateLogic:
    """Hand-built ArmResult triples force each REFUTED clause and the SURVIVES path."""

    @staticmethod
    def _ar(**kw) -> pg.ArmResult:
        base = dict(
            escal_precision=1.0, escal_recall=1.0, confident_wrong_recall=1.0,
            tokens=100.0, wasted_rate=0.0, accuracy=1.0, n=100,
        )
        base.update(kw)
        return pg.ArmResult(**base)

    def test_survives_when_a2_beats_a1_on_confident_wrong(self):
        a1 = self._ar(escal_recall=0.5, confident_wrong_recall=0.0, wasted_rate=0.2, accuracy=0.8)
        a2 = self._ar(escal_recall=1.0, confident_wrong_recall=1.0, wasted_rate=0.0, accuracy=1.0)
        abl = self._ar(escal_recall=0.0, confident_wrong_recall=0.0, wasted_rate=0.4, accuracy=0.6)
        verdict, reasons = refutation_gate(a1, a2, abl)
        assert verdict == "SURVIVES", reasons

    def test_refuted_clause_i_tie_at_iso(self):
        # A2 ties A1 on recall/wasted at iso accuracy/tokens.
        a1 = self._ar(escal_recall=1.0, wasted_rate=0.0, accuracy=1.0, tokens=100.0)
        a2 = self._ar(escal_recall=1.0, wasted_rate=0.0, accuracy=1.0, tokens=100.0)
        abl = self._ar(escal_recall=0.0)
        verdict, reasons = refutation_gate(a1, a2, abl)
        assert verdict == "REFUTED"
        assert any(r.startswith("(i)") for r in reasons)

    def test_refuted_clause_ii_gap_no_better_on_confident_wrong(self):
        a1 = self._ar(escal_recall=0.5, confident_wrong_recall=0.9, wasted_rate=0.2, accuracy=0.8)
        a2 = self._ar(escal_recall=1.0, confident_wrong_recall=0.9, wasted_rate=0.0, accuracy=1.0)
        abl = self._ar(escal_recall=0.0)
        verdict, reasons = refutation_gate(a1, a2, abl)
        assert verdict == "REFUTED"
        assert any(r.startswith("(ii)") for r in reasons)

    def test_refuted_clause_iii_ablation_keeps_gain(self):
        a1 = self._ar(escal_recall=0.5, confident_wrong_recall=0.0, wasted_rate=0.2, accuracy=0.8)
        a2 = self._ar(escal_recall=1.0, confident_wrong_recall=1.0, wasted_rate=0.0, accuracy=1.0)
        abl = self._ar(escal_recall=1.0)  # ablation keeps the recall → wire was not the gap
        verdict, reasons = refutation_gate(a1, a2, abl)
        assert verdict == "REFUTED"
        assert any(r.startswith("(iii)") for r in reasons)


# ─────────────── synthetic generator — §8(c) sanity sub-check ───────────────
class TestSyntheticGenerator:
    def test_generator_is_deterministic_for_a_seed(self):
        a = pg.generate_tasks(200, confident_wrong_rate=0.5, seed=7)
        b = pg.generate_tasks(200, confident_wrong_rate=0.5, seed=7)
        assert a == b

    def test_different_seeds_differ(self):
        a = pg.generate_tasks(200, confident_wrong_rate=0.5, seed=1)
        b = pg.generate_tasks(200, confident_wrong_rate=0.5, seed=2)
        assert a != b

    def test_confident_wrong_rate_is_honored(self):
        tasks = pg.generate_tasks(2000, dead_end_rate=0.5, confident_wrong_rate=0.7, seed=3)
        dead = [t for t in tasks if t.is_dead_end]
        confident_wrong = [t for t in dead if t.model_conf >= 0.6 and t.model_pred != t.truth]
        assert dead, "generator produced no dead-ends"
        frac = len(confident_wrong) / len(dead)
        assert abs(frac - 0.7) < 0.06, frac

    def test_low_confident_wrong_rate_refutes(self):
        tasks = pg.generate_tasks(600, confident_wrong_rate=0.0, seed=11)
        a1 = run_arm(tasks, "A1")
        a2 = run_arm(tasks, "A2")
        abl = run_arm(tasks, "A2", use_gap=False)
        verdict, _ = refutation_gate(a1, a2, abl)
        assert verdict == "REFUTED"

    def test_high_confident_wrong_rate_survives(self):
        tasks = pg.generate_tasks(600, confident_wrong_rate=0.85, seed=11)
        a1 = run_arm(tasks, "A1")
        a2 = run_arm(tasks, "A2")
        abl = run_arm(tasks, "A2", use_gap=False)
        verdict, reasons = refutation_gate(a1, a2, abl)
        assert verdict == "SURVIVES", reasons

    def test_a2_catches_confident_wrong_that_a1_misses(self):
        tasks = pg.generate_tasks(600, confident_wrong_rate=0.85, seed=4)
        a1 = run_arm(tasks, "A1")
        a2 = run_arm(tasks, "A2")
        assert a2.confident_wrong_recall > a1.confident_wrong_recall


# ─────────────── sweep — locate where the edge appears ───────────────
class TestSweep:
    RATES = [0.0, 0.1, 0.3, 0.6, 0.9]

    def test_sweep_returns_a_verdict_per_rate(self):
        rows = pg.sweep_confident_wrong(self.RATES, n=400, seed=5)
        assert [r["confident_wrong_rate"] for r in rows] == self.RATES
        assert all(r["verdict"] in {"REFUTED", "SURVIVES"} for r in rows)

    def test_verdict_is_monotone_refuted_then_survives(self):
        rows = pg.sweep_confident_wrong(self.RATES, n=400, seed=5)
        verdicts = [r["verdict"] for r in rows]
        # once it SURVIVES it must not fall back to REFUTED
        first_survive = next((i for i, v in enumerate(verdicts) if v == "SURVIVES"), None)
        assert first_survive is not None, verdicts
        assert all(v == "SURVIVES" for v in verdicts[first_survive:]), verdicts
        assert verdicts[0] == "REFUTED", verdicts

    def test_edge_threshold_is_between_zero_and_one(self):
        rows = pg.sweep_confident_wrong(self.RATES, n=400, seed=5)
        thr = pg.edge_threshold(rows)
        assert thr is not None
        assert 0.0 < thr <= 0.6
