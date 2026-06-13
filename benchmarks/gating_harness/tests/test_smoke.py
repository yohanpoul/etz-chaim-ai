"""Smoke / falsification gate for the TEMPS-2 harness (fast + deterministic).

These tests prove the harness WIRING end-to-end without depending on a slow live model:
the oracle is judge-free, the provider token path is asserted against a canned response
(measured, never fabricated), and the A2 gate-forces-pivot mechanism is driven by a
provider double across a real context wipe on the persistent Postgres store.

The LIVE end-to-end smoke (real Ollama, real measured tokens, report.md) is
``python -m benchmarks.gating_harness.run --smoke`` — run separately.
"""

from __future__ import annotations

import json

import pytest

from benchmarks.gating_harness import provider
from benchmarks.gating_harness.arms import run_a2
from benchmarks.gating_harness.metrics import SessionRecord, compute_metrics
from benchmarks.gating_harness.task import balanced_brackets as task

# --- canned model outputs (test doubles, NOT the harness fabricating) --------- #

_COUNT_OUT = (
    "APPROACH: count opening and closing brackets of each type\n"
    "```python\n"
    "def is_balanced(s):\n"
    "    return (s.count('(')==s.count(')') and s.count('[')==s.count(']')\n"
    "            and s.count('{')==s.count('}'))\n"
    "```\n"
)
_STACK_OUT = (
    "APPROACH: use a stack, push openers and pop-match on closers\n"
    "```python\n"
    "def is_balanced(s):\n"
    "    pairs={')':'(',']':'[','}':'{'}\n"
    "    st=[]\n"
    "    for c in s:\n"
    "        if c in '([{':\n"
    "            st.append(c)\n"
    "        elif c in pairs:\n"
    "            if not st or st.pop()!=pairs[c]:\n"
    "                return False\n"
    "    return not st\n"
    "```\n"
)


# --------------------------------------------------------------------------- #
# Oracle is judge-free and discriminates the dead-end objectively
# --------------------------------------------------------------------------- #


def test_oracle_count_hits_trap_stack_passes():
    count_res = task.run_oracle(task.extract_code(_COUNT_OUT))
    assert count_res.passed is False
    assert count_res.hit_trap is True  # objective dead-end: fails "([)]"

    stack_res = task.run_oracle(task.extract_code(_STACK_OUT))
    assert stack_res.passed is True
    assert stack_res.hit_trap is False


def test_classify_and_parse():
    assert task.classify_approach("count brackets of each type") == task.DEADEND_APPROACH
    assert task.classify_approach("push on a stack, pop on close") == task.CORRECT_APPROACH
    assert task.classify_approach("draw a picture") == "unknown"
    assert task.extract_declared_approach(_COUNT_OUT).lower().startswith("count")
    assert "def is_balanced" in (task.extract_code(_STACK_OUT) or "")


def test_oracle_no_code_is_failure():
    res = task.run_oracle(None)
    assert res.passed is False and res.error


# bare code (no fence, no APPROACH line) — the observed qwen failure mode
_COUNT_CODE_BARE = (
    "def is_balanced(s):\n"
    "    return (s.count('(')==s.count(')') and s.count('[')==s.count(']')\n"
    "            and s.count('{')==s.count('}'))\n"
)
_STACK_CODE_BARE = (
    "def is_balanced(s):\n"
    "    pairs={')':'(',']':'[','}':'{'}\n"
    "    st=[]\n"
    "    for c in s:\n"
    "        if c in '([{':\n"
    "            st.append(c)\n"
    "        elif c in pairs:\n"
    "            if not st or st.pop()!=pairs[c]:\n"
    "                return False\n"
    "    return not st\n"
)


def test_classify_from_code_structural():
    assert task.classify_from_code(_COUNT_CODE_BARE) == task.DEADEND_APPROACH
    assert task.classify_from_code(_STACK_CODE_BARE) == task.CORRECT_APPROACH
    assert task.classify_from_code("def f():\n    return 1\n") is None       # neither
    assert task.classify_from_code("def is_balanced(s): return (((") is None  # unparsable


def test_extract_code_salvages_unfenced():
    # No ``` fence, no APPROACH line, with trailing prose -> salvage from the def.
    text = "Sure, here is the function.\n" + _COUNT_CODE_BARE + "\nThat checks counts."
    code = task.extract_code(text)
    assert code is not None and "def is_balanced" in code
    # AST parse fails on the trailing prose -> keyword fallback still yields 'count'.
    assert task.infer_approach_key("", code) == task.DEADEND_APPROACH


def test_infer_approach_key_is_code_first_without_approach_line():
    assert task.infer_approach_key("", _COUNT_CODE_BARE) == task.DEADEND_APPROACH
    assert task.infer_approach_key("", _STACK_CODE_BARE) == task.CORRECT_APPROACH
    assert task.infer_approach_key("", None) == "unknown"


# --------------------------------------------------------------------------- #
# Provider: tokens are MEASURED from the response, never fabricated
# --------------------------------------------------------------------------- #


class _FakeResp:
    def __init__(self, payload: dict):
        self._b = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self._b


def test_provider_reads_measured_tokens(monkeypatch):
    payload = {
        "message": {"content": "hi"},
        "prompt_eval_count": 11,
        "eval_count": 5,
        "done_reason": "stop",
    }
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda req, timeout=None: _FakeResp(payload)
    )
    call = provider.chat([{"role": "user", "content": "x"}])
    assert (call.prompt_tokens, call.completion_tokens) == (11, 5)
    assert call.total_tokens == 16
    assert call.text == "hi"
    # config-resolved, zero hardcode: local_only -> qwen
    assert call.model == "qwen3.5:9b"


def test_provider_refuses_to_fabricate_missing_tokens(monkeypatch):
    payload = {"message": {"content": "hi"}}  # no token counts
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda req, timeout=None: _FakeResp(payload)
    )
    with pytest.raises(RuntimeError, match="token counts"):
        provider.chat([{"role": "user", "content": "x"}])


# --------------------------------------------------------------------------- #
# Metrics compute, with NA handling
# --------------------------------------------------------------------------- #


def test_metrics_compute_and_na():
    recs = [
        SessionRecord("X", 0, "count", "count", False, True, 10, 5,
                      memory_had_deadend=False),
        SessionRecord("X", 1, "stack", "stack", True, False, 20, 8,
                      memory_had_deadend=True),
    ]
    m = compute_metrics(recs)
    assert m["raw_dead_end_rate"] == 0.5
    assert m["dead_end_reattempt_rate"] == 0.0  # the 1 known session did NOT re-attempt
    assert m["final_correctness_passed_any"] is True
    assert m["total_tokens"] == 43

    # no prior-knowledge sessions -> memory-conditioned metric is NA, not 0
    none_known = [SessionRecord("X", 0, "count", "count", False, True, 1, 1)]
    assert compute_metrics(none_known)["dead_end_reattempt_rate"] is None


# --------------------------------------------------------------------------- #
# A2 end-to-end: the gate catches a re-attempt across a context wipe and forces
# a pivot to the correct approach (this is the harness "runs end-to-end" proof).
# --------------------------------------------------------------------------- #


def test_a2_gate_forces_pivot_across_sessions(monkeypatch, mem, fake_embed):
    def _fake_chat(messages, **kwargs):
        last = messages[-1]["content"]
        out = _STACK_OUT if "REJECTED by memory gate" in last else _COUNT_OUT
        # token fields are a test double; the measured-token guarantee is asserted
        # in test_provider_reads_measured_tokens above.
        return provider.ModelCall(
            text=out, prompt_tokens=50, completion_tokens=30,
            model="qwen3.5:9b", provider="ollama",
        )

    monkeypatch.setattr("benchmarks.gating_harness.provider.chat", _fake_chat)

    records = run_a2(sessions=2, mem=mem)
    s0, s1 = records

    # Session 0: no prior knowledge, takes the dead-end, records the FACT.
    assert s0.memory_had_deadend is False
    assert s0.hit_trap is True
    assert s0.gate_rejected is False

    # Session 1 (context wiped): store still knows the dead-end -> gate rejects the
    # re-attempt -> model pivots to the stack approach -> oracle passes.
    assert s1.memory_had_deadend is True
    assert s1.gate_rejected is True
    assert s1.generations == 2
    assert s1.approach_key == task.CORRECT_APPROACH
    assert s1.oracle_passed is True
    assert s1.hit_trap is False

    m = compute_metrics(records)
    assert m["gate_rejections"] == 1
    assert m["dead_end_reattempt_rate"] == 0.0  # known dead-end NOT re-walked
    assert m["self_contradiction_rate"] == 0.0
