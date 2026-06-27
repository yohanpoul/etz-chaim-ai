"""Tests for the real-oracle adapter (SPEC-007 ÉTAPE 2).

The adapter turns a real (model, code/debug oracle) interaction into the SAME
`Task` dataclass that ÉTAPE 1's `run_arm`/`refutation_gate` already consume, so
the analysis layer is reused unchanged. Every test here runs OFFLINE: the model
is a `MockModelClient` (zero API, zero tokens); only the oracle executes real
Python in a sandboxed subprocess.
"""
from __future__ import annotations

from etzchaim._internal import oracle_adapter as oa
from etzchaim._internal.oracle_adapter import (
    BUG_SUITE,
    Bug,
    CallResult,
    MockModelClient,
    attempt_task,
    run_oracle,
    run_pilot,
)
from etzchaim._internal.prediction_gate import Task


# ─────────────────────────── oracle ───────────────────────────
class TestOracle:
    PASS_TEST = "from cand import f\nassert f(2) == 4\nassert f(3) == 6\n"

    def test_correct_candidate_passes(self):
        assert run_oracle("def f(x):\n    return x * 2\n", self.PASS_TEST) == "will_pass"

    def test_wrong_candidate_fails(self):
        assert run_oracle("def f(x):\n    return x + 2\n", self.PASS_TEST) == "will_fail"

    def test_raising_candidate_is_error(self):
        out = run_oracle("def f(x):\n    return x / 0\n", self.PASS_TEST)
        assert out.startswith("will_error:"), out
        assert "ZeroDivisionError" in out

    def test_timeout_is_handled(self):
        out = run_oracle("def f(x):\n    while True:\n        pass\n", self.PASS_TEST, timeout=2)
        assert out in {"will_fail", "will_error:Timeout"}

    def test_outcome_is_in_oracle_vocabulary(self):
        # gap() (from prediction_gate) must accept whatever the oracle emits.
        from etzchaim._internal.prediction_gate import gap
        out = run_oracle("def f(x):\n    return x + 2\n", self.PASS_TEST)
        assert gap("will_pass", out) in {0.0, 1.0}


# ─────────────────────────── bug suite ───────────────────────────
class TestBugSuite:
    def test_suite_size_is_five_to_eight(self):
        assert 5 <= len(BUG_SUITE) <= 8

    def test_reference_solution_passes_its_own_test(self):
        for bug in BUG_SUITE:
            assert run_oracle(bug.reference, bug.test_code) == "will_pass", bug.id

    def test_buggy_code_actually_fails(self):
        # each injected bug is a real dead-end against its own oracle
        for bug in BUG_SUITE:
            assert run_oracle(bug.buggy, bug.test_code) != "will_pass", bug.id

    def test_ids_are_unique(self):
        ids = [b.id for b in BUG_SUITE]
        assert len(ids) == len(set(ids))


# ─────────────────────────── mock client (zero token) ───────────────────────────
class TestMockModelClient:
    def test_returns_callresult_with_token_counts(self):
        client = MockModelClient(script={})
        r = client.complete("hello")
        assert isinstance(r, CallResult)
        assert r.in_tokens > 0 and r.out_tokens > 0

    def test_is_deterministic(self):
        c1 = MockModelClient(seed=1)
        c2 = MockModelClient(seed=1)
        assert c1.complete("p").text == c2.complete("p").text


# ─────────────────────────── attempt → Task ───────────────────────────
class TestAttemptTask:
    def _bug(self) -> Bug:
        return BUG_SUITE[0]

    def test_confident_correct_attempt_maps_to_passing_task(self):
        bug = self._bug()
        # mock returns the reference fix, predicts pass, high confidence
        client = MockModelClient(forced={"fix": bug.reference, "prediction": "will_pass",
                                          "confidence": 0.95})
        task = attempt_task(bug, client)
        assert isinstance(task, Task)
        assert task.truth == "will_pass"
        assert task.is_dead_end is False
        assert task.model_pred == "will_pass"
        assert task.model_conf == 0.95
        assert task.tokens > 0

    def test_confident_wrong_attempt_is_a_dead_end(self):
        bug = self._bug()
        # mock returns the BUGGY code but predicts pass with high confidence
        client = MockModelClient(forced={"fix": bug.buggy, "prediction": "will_pass",
                                          "confidence": 0.9})
        task = attempt_task(bug, client)
        assert task.truth != "will_pass"          # oracle says it failed
        assert task.is_dead_end is True
        assert task.model_pred == "will_pass"      # but the model was confident it'd pass
        # → this is exactly a confident-but-wrong cell


# ─────────────────────────── pilot (zero token) ───────────────────────────
class TestRunPilot:
    def test_pilot_runs_offline_and_reports_three_metric_groups(self):
        client = MockModelClient(seed=7)
        report = run_pilot(BUG_SUITE, client, conf_tau=0.6)
        # (a) THE number
        assert 0.0 <= report.confident_wrong_rate <= 1.0
        # (b) precision + false-escalation cost, not just recall
        assert 0.0 <= report.a2_precision <= 1.0
        assert 0.0 <= report.a2_false_escalation_rate <= 1.0
        assert report.a2_false_positives >= 0
        # (c) tokens A1 vs A2 + accuracies for the iso-accuracy read
        assert report.a1_tokens > 0 and report.a2_tokens > 0
        assert 0.0 <= report.accuracy_a1 <= 1.0 and 0.0 <= report.accuracy_a2 <= 1.0
        assert report.n == len(BUG_SUITE)

    def test_confident_wrong_rate_matches_definition(self):
        # force every attempt to be confident-but-wrong → rate must be 1.0
        bad = MockModelClient(forced_per_bug={
            b.id: {"fix": b.buggy, "prediction": "will_pass", "confidence": 0.95}
            for b in BUG_SUITE
        })
        report = run_pilot(BUG_SUITE, bad, conf_tau=0.6)
        assert report.confident_wrong_rate == 1.0
        assert report.confident_wrong_count == len(BUG_SUITE)

    def test_no_false_escalations_when_all_predictions_correct(self):
        # model always fixes correctly AND predicts pass → A2 should never escalate
        good = MockModelClient(forced_per_bug={
            b.id: {"fix": b.reference, "prediction": "will_pass", "confidence": 0.9}
            for b in BUG_SUITE
        })
        report = run_pilot(BUG_SUITE, good, conf_tau=0.6)
        assert report.a2_false_positives == 0
        assert report.confident_wrong_rate == 0.0

    def test_pilot_uses_no_real_network(self):
        # MockModelClient has no API surface; calling the pilot must not require one.
        client = MockModelClient(seed=1)
        assert not hasattr(client, "_anthropic")
        run_pilot(BUG_SUITE, client)  # must not raise


# ─────────────── real client is lazy — constructed, never auto-called ───────────────
class TestRealClientIsLazy:
    def test_building_real_client_makes_no_call(self):
        # AnthropicModelClient must defer SDK import/auth until .complete() is used.
        client = oa.AnthropicModelClient(model_alias="haiku")
        assert client.model_alias == "haiku"
        assert client._client is None  # nothing constructed, nothing called, zero tokens
