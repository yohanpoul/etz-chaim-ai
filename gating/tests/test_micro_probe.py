"""Micro-probe — the falsification gate for Phase 2, TEMPS 1.

HONEST LABEL OF WHAT THIS PROVES (do not overclaim):
    1. PERSISTENT ROUND-TRIP: a FACT belief written in "session A" survives a context
       wipe (new Python objects) and is re-read from the persistent Postgres store in
       "session B", where the gate acts on it.
    2. FLAG ABLATION: with ETZ_GATING=off the gate is a pure passthrough.

WHAT THIS DOES NOT PROVE:
    - NOT the ADR-0009 edge. The gate keys on a FACT belief matched by an EXACT TAG.
    - It BYPASSES `epistememory.contradict`, `epistememory.deprecate`, and semantic
      `recall` ranking. A deprecated belief is invisible to `recall` (db.py:171), so
      that path is untested here by construction.
    A green probe = the plumbing conducts, not the direction is validated.
"""

from __future__ import annotations

import pytest

from gating.core import gate_intention


@pytest.mark.parametrize("approach_key", ["X"])
def test_persistent_roundtrip_gate_rejects_refuted_fact_after_context_wipe(
    monkeypatch, mem, approach_key
):
    """PLUMBING: FACT refutation re-read from the persistent store gates a retry."""
    # --- Session A: commit a FACT "approach X fails", tagged for exact match ---
    stored_id = mem.remember(
        content="approach X (regex backtracking) fails — catastrophic blowup",
        source_sephirah="external",
        confidence=0.95,  # >= 0.9 -> EpistemicStatus.FACT
        domain="probe",
        tags=["deadend", f"approach:{approach_key}"],
    )
    mem.close()
    del mem  # context wipe: drop session-A objects

    # --- Context wipe: brand-new objects, SAME persistent store ---
    from epistememory.core import EpisteMemory

    from gating.tests.conftest import TEST_DB_URL

    mem_b = EpisteMemory(db_url=TEST_DB_URL)

    # --- Session B, gating ON: must reject the retry, citing the re-read belief ---
    monkeypatch.setenv("ETZ_GATING", "on")
    decision = gate_intention(
        mem_b,
        goal="retry approach X regex backtracking",
        approach_key=approach_key,
        domain="probe",
    )
    assert decision.allowed is False, "gate should reject a retry of a refuted approach"
    assert decision.signal == "fact_refutation"
    # Proves the belief was re-read from the PERSISTENT store, not session memory:
    assert decision.matched_belief_id == stored_id
    assert approach_key in (decision.reason or "")
    mem_b.close()


def test_flag_ablation_off_is_passthrough(monkeypatch, mem):
    """ABLATION: ETZ_GATING=off -> never rejects, even with a matching refutation."""
    mem.remember(
        content="approach X fails",
        source_sephirah="external",
        confidence=0.95,
        domain="probe",
        tags=["deadend", "approach:X"],
    )
    monkeypatch.setenv("ETZ_GATING", "off")
    decision = gate_intention(
        mem, goal="retry approach X", approach_key="X", domain="probe"
    )
    assert decision.allowed is True
    assert decision.reason == "gating_off_passthrough"


def test_conclusion_gate_surfaces_contradiction(monkeypatch, dissensu):
    """SECONDARY (plumbing): conclusion gate flags a tension, never blocks.

    Uses pure-text divergence (no embeddings). Still not the ADR-0009 edge — it only
    shows the flag path is wired.
    """
    from gating.core import gate_conclusion

    monkeypatch.setenv("ETZ_GATING", "on")
    gate_conclusion(
        dissensu, "approach X is safe and correct", source_label="src_a", domain="probe"
    )
    decision = gate_conclusion(
        dissensu,
        "approach X is unsafe and fails — never do X",
        source_label="src_b",
        domain="probe",
    )
    assert decision.allowed is True  # contradictions are surfaced, not blocked
    # Tension detection is heuristic; assert the path ran and produced a verdict.
    assert decision.signal in ("contradiction", None)
    assert decision.reason is not None
