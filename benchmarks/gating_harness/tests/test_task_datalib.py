"""Offline mechanism proof for the datalib prior-trap task — NO live model.

Proves, deterministically and cheaply, BEFORE paying for a Haiku probe:
  - the AST classifier resolves every import form to the right datalib function;
  - the oracle FAILS a total-calling order_cost (and flags hit_trap) and PASSES a
    settle-calling one, through the sandboxed guarded importer;
  - code-first key inference works with no APPROACH line (the qwen failure mode);
  - ORACLE_CASES are locked to DATALIB_SOURCE and at least one case is discriminating.

Pure-function tests: no Postgres, no mem/fake_embed fixtures (those are for the gate).
"""

from __future__ import annotations

import pytest

from benchmarks.gating_harness.task import datalib_prior_trap as task


# --------------------------------------------------------------------------- #
# AST classifier across every import form
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "code,expected",
    [
        (
            "import datalib\ndef order_cost(lines):\n    return datalib.total(lines)\n",
            task.DEADEND_APPROACH,
        ),
        (
            "import datalib as dl\ndef order_cost(lines):\n    return dl.settle(lines)\n",
            task.CORRECT_APPROACH,
        ),
        (
            "from datalib import total, settle\n"
            "def order_cost(lines):\n    return total(lines)\n",
            task.DEADEND_APPROACH,
        ),
        (
            "from datalib import settle as s\n"
            "def order_cost(lines):\n    return s(lines)\n",
            task.CORRECT_APPROACH,
        ),
    ],
)
def test_classify_each_import_form(code, expected):
    assert task.classify_from_code(code) == expected


def test_classify_tie_settle_wins():
    code = (
        "import datalib\n"
        "def order_cost(lines):\n"
        "    t = datalib.total(lines)\n"
        "    return datalib.settle(lines)\n"
    )
    assert task.classify_from_code(code) == task.CORRECT_APPROACH


def test_classify_bypass_is_none():
    # Calls neither datalib function (a hand-rolled bypass) -> None (keyword fallback then 'unknown').
    code = "def order_cost(lines):\n    return sum(q * p for q, p in lines)\n"
    assert task.classify_from_code(code) is None


def test_classify_local_shadow_not_flagged():
    # A local def total() shadows the import name -> calling it is NOT the datalib trap.
    code = (
        "from datalib import total\n"
        "def total(lines):\n    return 0\n"
        "def order_cost(lines):\n    return total(lines)\n"
    )
    assert task.classify_from_code(code) is None


# --------------------------------------------------------------------------- #
# Oracle: trap FAILS, settle PASSES — through the sandbox + guarded importer
# --------------------------------------------------------------------------- #


def test_oracle_trap_fails_and_flags_hit_trap():
    res = task.run_oracle(
        "import datalib\ndef order_cost(lines):\n    return datalib.total(lines)\n"
    )
    assert res.passed is False
    assert res.hit_trap is True  # returned the naive total on a discriminating case


def test_oracle_settle_passes():
    res = task.run_oracle(
        "import datalib\ndef order_cost(lines):\n    return datalib.settle(lines)\n"
    )
    assert res.passed is True
    assert res.hit_trap is False
    assert res.failed_cases == []


def test_oracle_from_import_settle_passes():
    # Proves the guarded __import__ resolves the from-import form, not just attribute access.
    res = task.run_oracle(
        "from datalib import settle\ndef order_cost(lines):\n    return settle(lines)\n"
    )
    assert res.passed is True


def test_oracle_missing_order_cost():
    res = task.run_oracle("import datalib\nx = 1\n")
    assert res.passed is False
    assert res.error == "order_cost not defined"


def test_oracle_blocks_arbitrary_import():
    # Sandbox stays closed: importing anything other than datalib raises -> exec error.
    res = task.run_oracle(
        "import os\ndef order_cost(lines):\n    return os.getpid()\n"
    )
    assert res.passed is False
    assert res.error is not None and "error" in res.error.lower()


def test_oracle_does_not_leak_datalib_into_process():
    import sys

    before = "datalib" in sys.modules
    task.run_oracle("import datalib\ndef order_cost(lines):\n    return datalib.settle(lines)\n")
    after = "datalib" in sys.modules
    assert before == after  # sys.modules restored in finally


# --------------------------------------------------------------------------- #
# Code-first key inference with no APPROACH line (qwen failure mode parity)
# --------------------------------------------------------------------------- #


def test_infer_code_first_trap_no_approach_line():
    fixture = (
        "```python\nimport datalib\n"
        "def order_cost(lines):\n    return datalib.total(lines)\n```\n"
    )
    declared = task.extract_declared_approach(fixture)
    key = task.infer_approach_key(declared, task.extract_code(fixture))
    assert declared == ""
    assert key == task.DEADEND_APPROACH


def test_infer_code_first_settle_no_approach_line():
    fixture = (
        "```python\nimport datalib\n"
        "def order_cost(lines):\n    return datalib.settle(lines)\n```\n"
    )
    key = task.infer_approach_key(task.extract_declared_approach(fixture),
                                  task.extract_code(fixture))
    assert key == task.CORRECT_APPROACH


def test_infer_keyword_fallback_on_declared():
    # Non-parseable salvage but a declared line naming the naive total -> trap via fallback.
    declared = "naive total, just sum the lines"
    key = task.infer_approach_key(declared, code="def order_cost(lines): return  # truncated")
    assert key == task.DEADEND_APPROACH


# --------------------------------------------------------------------------- #
# Internal consistency: ORACLE_CASES locked to DATALIB_SOURCE; trap exercisable
# --------------------------------------------------------------------------- #


def test_oracle_cases_match_reference_settle_and_are_discriminating():
    mod = task._build_datalib_module()
    discriminating = 0
    for lines, expected in task.ORACLE_CASES:
        assert mod.settle(lines) == expected, f"ORACLE drift on {lines!r}"
        if mod.total(lines) != mod.settle(lines):
            discriminating += 1
    assert discriminating >= 1  # the trap must be provable by the oracle
