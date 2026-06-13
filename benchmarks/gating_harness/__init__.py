"""gating_harness — Phase 2, TEMPS 2 falsifiable test of ADR-0009.

Multi-session, context-wiped code/debug task against a reference oracle, with three
arms:

    A0  bare model, fresh context each session, no external memory
    A1  bare model + a CHANGELOG of failed approaches (the native baseline to beat)
    A2  bare model + EtzChaim gate (gating.core.gate_intention on the persistent
        Postgres belief store) — auto-rejects a re-attempt of a refuted approach

DECISION = (A), TREATED AS A KILL TEST (see docs/DIRECTION.md §6/§8, ADR-0009 "A vs B").
    A2 matches a refuted approach by an EXACT TAG via a *stipulated-perfect* approach
    classifier. That perfect identification is the UPPER BOUND of what enforcement can
    buy: real deployment needs fuzzy/semantic matching + the deprecate/contradict
    lifecycle, which is strictly harder. Therefore:
        - A2 <= A1  ->  PIVOT (an enforced gate cannot even beat an advisory log).
        - A2 >  A1  ->  floor crossed, NOT validated. It only means the upper bound is
                        above the baseline; the real claim (B) still has to be tested
                        with real matching + the contradiction/deprecate lifecycle.

HONESTY INVARIANTS (baked into the code, not just the prose):
    - Tokens are MEASURED from the provider response (Ollama prompt_eval_count /
      eval_count). Never fabricated. (Contrast benchmarks/arms.py:240 which fabricates
      350/400 * n_calls.)
    - The model is resolved via etzchaim.llm.model_registry.resolve_model(alias,
      profile) — zero hardcoded slug. (Contrast benchmarks/arms.py:31.)
    - The SMOKE runs a single task x 2 sessions on a small LOCAL model (Ollama qwen),
      then STOPS. The real run needs a frontier model (Haiku minimum); the smoke only
      proves the harness tics end-to-end and the four metrics compute.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.0.1-temps2-smoke"
