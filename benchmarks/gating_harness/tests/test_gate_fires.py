"""GO/NO-GO: the gate must REJECT a real dead-end matched from CODE, across a wipe.

No live model. Session B uses a FIXTURE model output = count-only code WITHOUT an
'APPROACH:' line (the observed qwen failure mode). The store is the real persistent
Postgres; embeddings are faked to isolate the exact-tag match from semantic noise,
exactly as the TEMPS-1 micro-probe does.

This is the decision gate for paying a frontier (Haiku) run: if the gate cannot fire
HERE — with a hardened, code-first classifier and a perfect tag — then enforcement has
no upper bound above the baseline and the frontier run is pointless.
"""

from __future__ import annotations

import pytest

from gating.core import gate_intention

from benchmarks.gating_harness.task import balanced_brackets as task
from benchmarks.gating_harness.tests.conftest import TEST_DB_URL

# Session-B fixtures: the count dead-end, NO 'APPROACH:' line. One fenced, one bare.
_COUNT_FENCED_NO_APPROACH = (
    "```python\n"
    "def is_balanced(s):\n"
    "    return s.count('(')==s.count(')') and s.count('[')==s.count(']') "
    "and s.count('{')==s.count('}')\n"
    "```\n"
)
_COUNT_BARE_NO_APPROACH = (
    "Here is a solution:\n"
    "def is_balanced(s):\n"
    "    return s.count('(')==s.count(')') and s.count('[')==s.count(']') "
    "and s.count('{')==s.count('}')\n"
)
_STACK_FENCED_NO_APPROACH = (
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


def _wipe_and_reopen(mem):
    """Close session-A objects; reopen a fresh EpisteMemory on the SAME store."""
    mem.close()
    from epistememory.core import EpisteMemory

    return EpisteMemory(db_url=TEST_DB_URL)


@pytest.mark.parametrize(
    "fixture", [_COUNT_FENCED_NO_APPROACH, _COUNT_BARE_NO_APPROACH]
)
def test_gate_fires_on_count_deadend_without_approach_line(
    monkeypatch, mem, fake_embed, fixture
):
    # --- Session A: commit the count dead-end as a FACT, exact-tagged ---
    stored_id = mem.remember(
        content="approach count fails — trap '([)]' (counts balanced, nesting wrong)",
        source_sephirah="external",
        confidence=0.95,  # >= 0.9 -> EpistemicStatus.FACT
        domain=task.TASK_ID,
        tags=["deadend", "approach:count"],
    )
    mem_b = _wipe_and_reopen(mem)  # context wipe, SAME persistent store

    # --- Session B: fixture output has NO 'APPROACH:' line -> code-first matching ---
    declared = task.extract_declared_approach(fixture)
    key = task.infer_approach_key(declared, task.extract_code(fixture))
    assert declared == ""                    # model emitted no APPROACH line
    assert key == task.DEADEND_APPROACH      # classifier deduced 'count' from the CODE

    # --- gate ON: reject the refuted approach, citing the re-read FACT ---
    monkeypatch.setenv("ETZ_GATING", "on")
    decision = gate_intention(
        mem_b,
        goal="validate brackets by counting each type",
        approach_key=key,
        domain=task.TASK_ID,
    )
    assert decision.allowed is False
    assert decision.signal == "fact_refutation"
    assert decision.matched_belief_id == stored_id  # re-read from the PERSISTENT store

    # --- ablation: gate OFF -> passthrough, no rejection ---
    monkeypatch.setenv("ETZ_GATING", "off")
    off = gate_intention(
        mem_b,
        goal="validate brackets by counting each type",
        approach_key=key,
        domain=task.TASK_ID,
    )
    assert off.allowed is True
    mem_b.close()


def test_gate_allows_stack_approach_no_false_positive(monkeypatch, mem, fake_embed):
    """Positive control: the correct (stack) approach is NOT rejected."""
    mem.remember(
        content="approach count fails — trap '([)]'",
        source_sephirah="external",
        confidence=0.95,
        domain=task.TASK_ID,
        tags=["deadend", "approach:count"],
    )
    mem_b = _wipe_and_reopen(mem)

    key = task.infer_approach_key("", task.extract_code(_STACK_FENCED_NO_APPROACH))
    assert key == task.CORRECT_APPROACH

    monkeypatch.setenv("ETZ_GATING", "on")
    decision = gate_intention(
        mem_b,
        goal="use a stack to match brackets",
        approach_key=key,
        domain=task.TASK_ID,
    )
    assert decision.allowed is True  # no FACT tagged approach:stack -> not rejected
    mem_b.close()
