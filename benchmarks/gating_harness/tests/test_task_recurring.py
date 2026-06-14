"""Offline mechanism proof for the recurring-deadend performance-trap task — NO live model.

Proves, deterministically and cheaply, BEFORE paying for a Haiku probe:
  - the AST classifier maps naive ``sum(arr[i:j])`` -> naive and prefix-sum -> prefix;
  - the DETERMINISTIC op-budget oracle FAILS a naive re-sum (and flags hit_trap) and PASSES
    every O(n)/O(n+q) approach (accumulate, manual prefix), through the int-subclass meter;
  - the op-counter catches a manual inner-loop naive that the AST classifier does NOT label
    (the behavioural op-budget is the independent ground truth);
  - a casting-naive (``int(x)`` per element) ESCAPES the meter — documented limitation;
  - ORACLE_CASES expected sums are locked to the reference and the large case is discriminating
    (naive_ops > OP_BUDGET > prefix_ops).

Pure-function tests: no Postgres, no mem/fake_embed fixtures (those are for the gate).
"""

from __future__ import annotations

from benchmarks.gating_harness.task import recurring_deadend as task

# --------------------------------------------------------------------------- #
# Canonical solutions
# --------------------------------------------------------------------------- #

_NAIVE = (
    "def range_sums(arr, queries):\n"
    "    return [sum(arr[i:j]) for (i, j) in queries]\n"
)
_PREFIX_ACCUMULATE = (
    "from itertools import accumulate\n"
    "def range_sums(arr, queries):\n"
    "    pref = [0] + list(accumulate(arr))\n"
    "    return [pref[j] - pref[i] for (i, j) in queries]\n"
)
_PREFIX_MANUAL = (
    "def range_sums(arr, queries):\n"
    "    pref = [0]\n"
    "    for x in arr:\n"
    "        pref.append(pref[-1] + x)\n"
    "    return [pref[j] - pref[i] for (i, j) in queries]\n"
)
_NAIVE_MANUAL_LOOP = (  # no sum(slice): AST can't label it, but the op-counter must catch it
    "def range_sums(arr, queries):\n"
    "    res = []\n"
    "    for (i, j) in queries:\n"
    "        s = 0\n"
    "        for k in range(i, j):\n"
    "            s = s + arr[k]\n"
    "        res.append(s)\n"
    "    return res\n"
)
_NAIVE_CASTING = (  # explicit int(x) cast unwraps the _Probe -> escapes the meter (documented)
    "def range_sums(arr, queries):\n"
    "    return [sum(int(x) for x in arr[i:j]) for (i, j) in queries]\n"
)


# --------------------------------------------------------------------------- #
# AST classifier
# --------------------------------------------------------------------------- #


def test_classify_naive_sum_of_slice():
    assert task.classify_from_code(_NAIVE) == task.DEADEND_APPROACH


def test_classify_prefix_accumulate():
    assert task.classify_from_code(_PREFIX_ACCUMULATE) == task.CORRECT_APPROACH


def test_classify_prefix_manual_difference():
    assert task.classify_from_code(_PREFIX_MANUAL) == task.CORRECT_APPROACH


def test_classify_manual_naive_is_none_oracle_is_truth():
    # No sum(slice) and no prefix difference -> AST returns None (keyword fallback).
    # The behavioural op-counter (below) is what actually flags this as the dead-end.
    assert task.classify_from_code(_NAIVE_MANUAL_LOOP) is None


def test_classify_unparseable_is_none():
    assert task.classify_from_code("def range_sums(arr, queries): return  # truncated") is None


# --------------------------------------------------------------------------- #
# Deterministic op-budget oracle: naive FAILS + hit_trap, prefix PASSES
# --------------------------------------------------------------------------- #


def test_oracle_naive_fails_and_flags_hit_trap():
    res = task.run_oracle(_NAIVE)
    assert res.passed is False
    assert res.hit_trap is True  # blew OP_BUDGET on the large discriminating case


def test_oracle_prefix_accumulate_passes():
    res = task.run_oracle(_PREFIX_ACCUMULATE)
    assert res.passed is True
    assert res.hit_trap is False
    assert res.failed_cases == []


def test_oracle_prefix_manual_passes():
    res = task.run_oracle(_PREFIX_MANUAL)
    assert res.passed is True
    assert res.hit_trap is False


def test_oracle_manual_naive_loop_caught_by_op_counter():
    # AST cannot label it (test above), but the op-budget catches the O(q*n) work.
    res = task.run_oracle(_NAIVE_MANUAL_LOOP)
    assert res.passed is False
    assert res.hit_trap is True


def test_oracle_casting_naive_escapes_meter_DOCUMENTED():
    # DOCUMENTED LIMITATION: an explicit int(x) cast unwraps the _Probe, so the meter sees 0
    # arithmetic ops and the (still O(q*n)) re-sum is NOT flagged. The Stage-2 probe eyeballs
    # 1-2 real Haiku naive outputs as the backstop for this hole.
    res = task.run_oracle(_NAIVE_CASTING)
    assert res.hit_trap is False   # meter escaped
    assert res.passed is True      # answer is still correct


def test_oracle_missing_range_sums():
    res = task.run_oracle("x = 1\n")
    assert res.passed is False
    assert res.error == "range_sums not defined"


def test_oracle_blocks_arbitrary_import():
    res = task.run_oracle(
        "import os\ndef range_sums(arr, queries):\n    return [os.getpid()]\n"
    )
    assert res.passed is False
    assert res.error is not None and "error" in res.error.lower()


def test_oracle_no_code():
    res = task.run_oracle(None)
    assert res.passed is False
    assert res.error == "no code extracted"


# --------------------------------------------------------------------------- #
# Code-first key inference with no APPROACH line (qwen failure mode parity)
# --------------------------------------------------------------------------- #


def test_infer_code_first_naive_no_approach_line():
    fixture = "```python\n" + _NAIVE + "```\n"
    declared = task.extract_declared_approach(fixture)
    key = task.infer_approach_key(declared, task.extract_code(fixture))
    assert declared == ""
    assert key == task.DEADEND_APPROACH


def test_infer_code_first_prefix_no_approach_line():
    fixture = "```python\n" + _PREFIX_ACCUMULATE + "```\n"
    key = task.infer_approach_key(
        task.extract_declared_approach(fixture), task.extract_code(fixture)
    )
    assert key == task.CORRECT_APPROACH


def test_infer_keyword_fallback_on_declared():
    # Manual-loop naive (AST None) rescued by a declared 'naive, re-sum each query'.
    key = task.infer_approach_key("naive, re-sum each query", code=_NAIVE_MANUAL_LOOP)
    assert key == task.DEADEND_APPROACH


# --------------------------------------------------------------------------- #
# Internal consistency: ORACLE_CASES locked + the large case is discriminating
# --------------------------------------------------------------------------- #


def test_oracle_cases_match_reference_sums():
    for arr, queries, expected, _metered in task.ORACLE_CASES:
        ref = [sum(arr[i:j]) for (i, j) in queries]
        assert ref == expected, f"ORACLE drift on {(arr[:3], queries[:3])!r}"


def test_op_budget_separates_naive_from_prefix():
    arr, queries, _expected = task._large_case()

    def naive(a, q):
        return [sum(a[i:j]) for (i, j) in q]

    def prefix(a, q):
        from itertools import accumulate

        pref = [0] + list(accumulate(a))
        return [pref[j] - pref[i] for (i, j) in q]

    arr_probe = [task._Probe(x) for x in arr]

    task._reset_ops()
    naive(arr_probe, queries)
    naive_ops = task._read_ops()

    task._reset_ops()
    prefix(arr_probe, queries)
    prefix_ops = task._read_ops()

    assert naive_ops > task.OP_BUDGET, f"naive only {naive_ops} ops"
    assert prefix_ops < task.OP_BUDGET, f"prefix {prefix_ops} ops"
    assert naive_ops > prefix_ops  # the trap is provable + discriminating
