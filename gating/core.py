"""gating.core — thinnest ablatable gate over the persistent belief store.

Phase 2, TEMPS 1. Behind ETZ_GATING (default off = passthrough). Additive: no edits
to epistememory / intentkeeper / dissensuengine.

WHAT THE MICRO-PROBE PROVES (honest label — do not overclaim):
    PLUMBING ONLY — persistent round-trip + flag ablation.
    NOT the contradiction/deprecate edge of ADR-0009.

The intention gate keys on a FACT-status belief found via `EpisteMemory.recall(
epistemic_status=["fact"])` and then matched by an EXACT TAG (`deadend` +
`approach:<key>`). This is deliberate:
  - it BYPASSES semantic recall ranking (match is exact-tag, not cosine);
  - it does NOT use `epistememory.contradict` or `epistememory.deprecate`.

KNOWN DISCOVERY (epistememory/db.py:171): `search_by_embedding` filters
`epistemic_status != 'deprecated'`, so DEPRECATED beliefs are invisible to `recall`.
The ADR-0009 differentiator (gate on deprecated/contradicted beliefs) is therefore
NOT reachable through `recall`; it would need a dedicated lookup path. The gate here
uses a FACT "approach X fails" belief instead — which is why a green probe is
plumbing, not the edge. See ADR-0009 (Discovery 2026-06-13).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from uuid import UUID


def gating_enabled() -> bool:
    """Read the ablation flag per-call. Default OFF = passthrough (no behavior change)."""
    return os.environ.get("ETZ_GATING", "off").strip().lower() == "on"


@dataclass
class GateDecision:
    """Outcome of a gate check.

    allowed: False only when the intention gate REJECTS (a refuted approach is retried).
             Always True for the conclusion gate (contradictions are surfaced, not blocked).
    signal:  "fact_refutation" | "contradiction" | None
    """

    allowed: bool
    reason: str | None = None
    matched_belief_id: UUID | None = None
    matched_content: str | None = None
    signal: str | None = None
    flagged: bool = False  # conclusion gate: a contradiction was surfaced (still allowed)


def _is_refutation(tags: list[str], approach_key: str | None) -> bool:
    """Exact-tag match. NOT semantic. A belief refutes an approach iff it is tagged
    `deadend` and (when a key is given) `approach:<key>`."""
    tagset = set(tags or [])
    if "deadend" not in tagset:
        return False
    if approach_key is None:
        return True
    return f"approach:{approach_key}" in tagset


def gate_intention(
    memory,
    goal: str,
    *,
    approach_key: str | None = None,
    domain: str | None = None,
    limit: int = 50,
) -> GateDecision:
    """Pre-check before an intention is set.

    OFF  -> passthrough (allowed=True), no store query.
    ON   -> recall FACT-status beliefs for `goal`, reject if one is an exact-tag
            refutation of `approach_key`.

    Honest scope: matches by EXACT TAG (not semantic similarity), on a FACT belief
    (not a deprecated/contradicted one). Proves the gate can read a refutation back
    from the persistent store and act on it — plumbing, not the ADR-0009 edge.
    """
    if not gating_enabled():
        return GateDecision(allowed=True, reason="gating_off_passthrough")

    results = memory.recall(
        goal,
        limit=limit,
        epistemic_status=["fact"],
        domain=domain,
        include_contradictions=False,
    )
    for entry in results:
        if _is_refutation(entry.tags, approach_key):
            return GateDecision(
                allowed=False,
                reason=(
                    f"rejected: a committed FACT refutes this approach — "
                    f"'{entry.content}' (id={entry.id})"
                ),
                matched_belief_id=entry.id,
                matched_content=entry.content,
                signal="fact_refutation",
            )
    return GateDecision(allowed=True, reason="no_refutation_found")


def gate_conclusion(
    dissensu,
    content: str,
    source_label: str,
    *,
    source_type: str = "system",
    domain: str | None = None,
    confidence: float = 0.5,
) -> GateDecision:
    """Submit a conclusion, then surface contradiction with existing ones.

    OFF -> submit only (allowed=True, not flagged).
    ON  -> submit, then analyze_consistency(domain); if tensions exist, flag them.

    Never blocks — dissensus philosophy is to surface tension, not hide or veto it.
    """
    conclusion = dissensu.submit_conclusion(
        content=content,
        source_label=source_label,
        source_type=source_type,
        domain=domain,
        confidence=confidence,
    )
    if not gating_enabled():
        return GateDecision(allowed=True, reason="gating_off_no_check")

    report = dissensu.analyze_consistency(domain=domain)
    if getattr(report, "total_tensions", 0) > 0:
        return GateDecision(
            allowed=True,
            flagged=True,
            signal="contradiction",
            reason=(
                f"contradiction surfaced: {report.total_tensions} tension(s) "
                f"(max_divergence={getattr(report, 'max_divergence', 0.0):.2f}) "
                f"around conclusion {conclusion.id}"
            ),
        )
    return GateDecision(allowed=True, reason="no_tension")
