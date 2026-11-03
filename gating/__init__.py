"""gating — the thinnest ablatable metacognitive gate (Phase 2, TEMPS 1).

Additive, behind the ETZ_GATING env flag (default off = passthrough). Queries the
persistent belief store BEFORE an intention is set, or flags contradiction when a
conclusion is submitted. Does NOT modify epistememory / intentkeeper / dissensuengine.

HONEST SCOPE — read before trusting anything here:
The accompanying micro-probe proves PLUMBING only: (1) a belief survives a context
wipe and is re-read from the persistent Postgres store, and (2) the ETZ_GATING flag
truly ablates the behavior. It does NOT validate the ADR-0009 direction. The gate
keys on a FACT-status belief matched by an EXACT TAG; it deliberately bypasses
`epistememory.contradict`, `epistememory.deprecate`, and semantic `recall` ranking.
A green probe = the wire conducts, not the edge exists.
"""

from .core import GateDecision, gate_conclusion, gate_intention, gating_enabled

__all__ = ["GateDecision", "gate_intention", "gate_conclusion", "gating_enabled"]
