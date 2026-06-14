"""Offline proof that the task-parametric arms drive recurring_deadend — NO live model.

Two things, both BEFORE any spend:
  1. the gate fires on the NEW dead-end key ('naive') after a real context wipe, and the
     ETZ_GATING=off ablation passes through (mirror of test_gate_fires, new task);
  2. the arms (A0/A2 + ablation) run end-to-end on recurring_deadend with a STUBBED generator
     (canned naive code, zero network), the op-budget oracle flags the dead-end, and the gate
     reject path fires across the wipe under gating=True and is silent under gating=False.

The stub gen lets the full arm logic (gate query, reject -> regenerate, remember, metrics) run
deterministically offline. The live Haiku spend happens only in probe_reattempt / run --experiment.
"""

from __future__ import annotations

from gating.core import gate_intention

from benchmarks.gating_harness import provider
from benchmarks.gating_harness.arms import run_a0, run_a1, run_a2
from benchmarks.gating_harness.metrics import compute_metrics
from benchmarks.gating_harness.task import recurring_deadend as task
from benchmarks.gating_harness.tests.conftest import TEST_DB_URL

_NAIVE_RESPONSE = (
    "APPROACH: naive, sum each query slice\n"
    "```python\n"
    "def range_sums(arr, queries):\n"
    "    return [sum(arr[i:j]) for (i, j) in queries]\n"
    "```\n"
)
_PREFIX_RESPONSE = (
    "APPROACH: prefix sums then subtract\n"
    "```python\n"
    "from itertools import accumulate\n"
    "def range_sums(arr, queries):\n"
    "    pref = [0] + list(accumulate(arr))\n"
    "    return [pref[j] - pref[i] for (i, j) in queries]\n"
    "```\n"
)


def _stub(text: str):
    """A gen callable (messages -> ModelCall) that always returns the same canned text."""

    def gen(messages):  # noqa: ARG001 — stub ignores the prompt, returns fixed code
        return provider.ModelCall(
            text=text, prompt_tokens=12, completion_tokens=12, model="stub", provider="stub"
        )

    return gen


def _spy(text: str):
    """A stub gen that also records the messages it was called with (to assert prompt content)."""
    captured: list = []

    def gen(messages):
        captured.append(messages)
        return provider.ModelCall(
            text=text, prompt_tokens=12, completion_tokens=12, model="stub", provider="stub"
        )

    gen.captured = captured
    return gen


def _wipe_and_reopen(mem):
    mem.close()
    from epistememory.core import EpisteMemory

    return EpisteMemory(db_url=TEST_DB_URL)


# --------------------------------------------------------------------------- #
# 1. The gate fires on the new dead-end key, across a wipe; ablation passes through
# --------------------------------------------------------------------------- #


def test_gate_fires_on_recurring_deadend(monkeypatch, mem, fake_embed):
    stored_id = mem.remember(
        content=f"approach naive fails on {task.TASK_ID} — trap '{task.TRAP_CASE}'",
        source_sephirah="external",
        confidence=0.95,  # >= 0.9 -> EpistemicStatus.FACT
        domain=task.TASK_ID,
        tags=["deadend", "approach:naive"],
    )
    mem_b = _wipe_and_reopen(mem)  # context wipe, SAME persistent store

    key = task.infer_approach_key("", task.extract_code(_NAIVE_RESPONSE))
    assert key == task.DEADEND_APPROACH

    monkeypatch.setenv("ETZ_GATING", "on")
    decision = gate_intention(
        mem_b, goal="sum each query slice", approach_key=key, domain=task.TASK_ID
    )
    assert decision.allowed is False
    assert decision.signal == "fact_refutation"
    assert decision.matched_belief_id == stored_id

    monkeypatch.setenv("ETZ_GATING", "off")
    off = gate_intention(
        mem_b, goal="sum each query slice", approach_key=key, domain=task.TASK_ID
    )
    assert off.allowed is True
    mem_b.close()


def test_gate_allows_prefix_no_false_positive(monkeypatch, mem, fake_embed):
    mem.remember(
        content=f"approach naive fails on {task.TASK_ID}",
        source_sephirah="external",
        confidence=0.95,
        domain=task.TASK_ID,
        tags=["deadend", "approach:naive"],
    )
    mem_b = _wipe_and_reopen(mem)
    key = task.infer_approach_key("", task.extract_code(_PREFIX_RESPONSE))
    assert key == task.CORRECT_APPROACH
    monkeypatch.setenv("ETZ_GATING", "on")
    decision = gate_intention(
        mem_b, goal="prefix sums", approach_key=key, domain=task.TASK_ID
    )
    assert decision.allowed is True  # no FACT tagged approach:prefix -> not rejected
    mem_b.close()


# --------------------------------------------------------------------------- #
# 2. Arms run end-to-end on the new task with a stub gen (offline) + metrics compute
# --------------------------------------------------------------------------- #


def test_a0_stub_naive_hits_trap_and_metrics_compute():
    a0 = run_a0(2, task=task, gen=_stub(_NAIVE_RESPONSE))
    assert all(r.hit_trap for r in a0)         # op-budget flagged the naive dead-end
    assert all(r.approach_key == "naive" for r in a0)
    m = compute_metrics(a0)
    assert m["raw_dead_end_rate"] == 1.0
    assert m["dead_end_reattempt_rate"] is None  # A0 has no memory -> NA


def test_a2_gate_rejects_reattempt_across_wipe(mem, fake_embed):
    a2 = run_a2(3, mem, task=task, gen=_stub(_NAIVE_RESPONSE), gating=True)
    m = compute_metrics(a2)
    # Session 1 records the dead-end FACT; sessions 2-3 must be gate-rejected across the wipe.
    assert m["gate_rejections"] >= 1
    assert any(r.gate_rejected for r in a2)


def test_a2_ablation_no_rejection(mem, fake_embed):
    a2 = run_a2(3, mem, task=task, gen=_stub(_NAIVE_RESPONSE), gating=False)
    m = compute_metrics(a2)
    assert m["gate_rejections"] == 0  # gate disabled -> the wire does nothing


def test_a2_prefix_never_trapped_no_rejection(mem, fake_embed):
    a2 = run_a2(3, mem, task=task, gen=_stub(_PREFIX_RESPONSE), gating=True)
    m = compute_metrics(a2)
    assert m["final_correctness_passed_any"] is True
    assert m["gate_rejections"] == 0  # the correct approach is never refuted -> never gated


# --------------------------------------------------------------------------- #
# 3. SEEDED Stage-3a path: every session memory-conditioned; noise sweep plumbing
# --------------------------------------------------------------------------- #


def test_a1_seeded_changelog_carries_buried_refutation():
    from benchmarks.gating_harness.run import _noise

    spy = _spy(_NAIVE_RESPONSE)
    noise = _noise(5, deadend_key=task.DEADEND_APPROACH)
    recs = run_a1(2, task=task, gen=spy, changelog_noise=noise, seed_deadend=True)
    # every session is memory-conditioned (seed present from session 0), log frozen
    assert all(r.memory_had_deadend for r in recs)
    user_msg = spy.captured[0][1]["content"]
    assert "CHANGELOG" in user_msg
    assert task.DEADEND_APPROACH in user_msg   # the seed names the dead-end
    assert "variant-000" in user_msg           # the noise is present (buried)
    # stub always returns naive -> a re-attempt on a conditioned trial
    assert all(r.committed_refuted for r in recs)


def test_a2_seeded_gate_rejects_every_session_despite_noise(mem, fake_embed):
    from benchmarks.gating_harness.run import _noise

    a2 = run_a2(
        3, mem, task=task, gen=_stub(_NAIVE_RESPONSE), gating=True,
        seed_deadend=True, store_noise=_noise(10, deadend_key=task.DEADEND_APPROACH),
    )
    m = compute_metrics(a2)
    assert m["gate_rejections"] == 3              # seeded -> fires every session
    assert all(r.memory_had_deadend for r in a2)  # noise in other domains does not block the gate


def test_a2_seeded_ablation_floor(mem, fake_embed):
    from benchmarks.gating_harness.run import _noise

    a2 = run_a2(
        3, mem, task=task, gen=_stub(_NAIVE_RESPONSE), gating=False,
        seed_deadend=True, store_noise=_noise(5, deadend_key=task.DEADEND_APPROACH),
    )
    m = compute_metrics(a2)
    assert m["gate_rejections"] == 0              # gate off -> no suppression
    assert all(r.memory_had_deadend for r in a2)  # but memory HAS the dead-end (the floor)
    assert m["dead_end_reattempt_rate"] == 1.0    # stub naive, unsuppressed


def test_experiment_breakdown_counts():
    from benchmarks.gating_harness.run import _experiment_breakdown

    bd = _experiment_breakdown(15, [0, 10, 20, 40])
    assert bd == {"A0": 15, "A1": 60, "A2_gate": 120, "A2_ablation": 60, "total": 255}


def test_noise_excludes_deadend_key():
    from benchmarks.gating_harness.run import _noise

    entries = _noise(40, deadend_key=task.DEADEND_APPROACH)
    assert len(entries) == 40
    assert all(task.DEADEND_APPROACH not in e for e in entries)


def test_experiment_preflight_spends_nothing(capsys):
    from benchmarks.gating_harness.run import run_experiment

    out = run_experiment(
        task_name="recurring_deadend", k=15, noise_levels=[0, 10, 20, 40], confirm=False
    )
    assert out is None  # human gate: no --confirm -> returns None, no network
    printed = capsys.readouterr().out
    assert "PREFLIGHT" in printed
    assert "TOTAL=255" in printed
    assert "NOT spending" in printed
