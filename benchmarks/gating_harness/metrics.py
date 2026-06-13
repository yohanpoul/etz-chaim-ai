"""The four metrics of DIRECTION §6, computed from per-session records.

All labels are OBJECTIVE (oracle-derived) or mechanical (token counts, gate signals) —
no LLM judge anywhere, which is the property Risk #1 (secondary) demands.

    SessionRecord captures one session of one arm. ``memory_had_deadend`` is the key
    conditioning flag: it is True when, AT SESSION START, that arm's external memory
    (A1 CHANGELOG / A2 belief store) already knew the dead-end. A0 has no memory, so it
    is always False for A0 — which is correct: A0 is the no-memory control, and
    "re-attempt of a *known* dead-end" is undefined without memory (reported as NA).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class SessionRecord:
    arm: str
    session_idx: int
    declared_approach: str
    approach_key: str
    oracle_passed: bool
    hit_trap: bool                  # this session's FINAL candidate failed the trap
    prompt_tokens: int
    completion_tokens: int
    generations: int = 1            # model calls this session (a gate reject => 2)
    gate_rejected: bool = False     # A2: gate blocked the initial intention
    memory_had_deadend: bool = False  # dead-end already known at session start
    committed_refuted: bool = False   # final declared approach == the refuted one

    def to_dict(self) -> dict:
        return asdict(self)


def _rate(num: int, den: int) -> float | None:
    return (num / den) if den else None


def compute_metrics(records: list[SessionRecord]) -> dict:
    """Return the four metrics (+ supporting counts) for one arm's session list."""
    n = len(records)

    # (1) dead-end re-attempt rate — memory-conditioned (the DIRECTION metric) + raw.
    known = [r for r in records if r.memory_had_deadend]
    known_reattempt = _rate(sum(r.hit_trap for r in known), len(known))
    raw_deadend = _rate(sum(r.hit_trap for r in records), n)

    # (2) self-contradiction rate — re-committed an already-refuted approach.
    self_contradiction = _rate(sum(r.committed_refuted for r in records), n)

    # (3) iterations / tokens to oracle.
    total_generations = sum(r.generations for r in records)
    total_tokens = sum(r.prompt_tokens + r.completion_tokens for r in records)
    first_pass_session = next(
        (r.session_idx for r in records if r.oracle_passed), None
    )

    # (4) final correctness.
    passed_any = any(r.oracle_passed for r in records)
    final_passed = records[-1].oracle_passed if records else False

    return {
        "n_sessions": n,
        # (1)
        "dead_end_reattempt_rate": known_reattempt,   # NA if no session had prior knowledge
        "raw_dead_end_rate": raw_deadend,
        "n_sessions_with_prior_knowledge": len(known),
        # (2)
        "self_contradiction_rate": self_contradiction,
        # (3)
        "total_generations": total_generations,
        "total_tokens": total_tokens,
        "first_pass_session": first_pass_session,
        # (4)
        "final_correctness_passed_any": passed_any,
        "final_correctness_last_session": final_passed,
        # supporting
        "gate_rejections": sum(r.gate_rejected for r in records),
    }
