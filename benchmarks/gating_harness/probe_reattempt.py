"""Cheap Haiku pre-check — does the recurring-deadend perf-trap elicit the `naive` dead-end?

    python -m benchmarks.gating_harness.probe_reattempt [--n 8]

Stage 2 of TEMPS 3 (option C). A0-style: N single-shot Haiku calls via the OAuth Max CLI,
fresh context each (the wipe), NO memory, NO gate. The go/no-go decided BEFORE paying for the
full A0/A1/A2 experiment: does a frontier model recurrently write the naive per-query re-sum
(``sum(arr[i:j])`` — O(q*n)), or does it precompute a prefix sum unprompted?

    - 0 < took_deadend          -> the frontier enters the dead-end -> the multi-session
                                   experiment has a real phenomenon to gate -> GO.
    - took_deadend ~ 0          -> Haiku precomputes by default; the perf trap does not
                                   reproduce on Haiku as framed -> NO-GO, STOP, report (a 4th
                                   honest NO-GO; do NOT torture the task to force a fall).

A high rate is FINE here (unlike the datalib trap): the naive is the natural neutral default,
and the experiment tests whether MEMORY suppresses its re-attempt across wipes — not whether
the model can find the fix unaided.

HONESTY INVARIANTS (shared with the other probes):
    - tokens + cost are MEASURED from the CLI response (never fabricated);
    - the slug is resolved via config (current Haiku 4.5) with a stale-slug guard inside
      ``provider.chat_claude_cli``;
    - the FULL model code is saved per trial so a human can EYEBALL 1-2 real naive outputs and
      confirm hit_trap fired (the deterministic op-meter is blind to an explicit int(x) cast —
      a documented escape; the eyeball is its backstop).

DIVERSITY (mandatory). The claude CLI exposes NO temperature flag, so this probe varies the
FRAMING. Both halves stay SCALE-NEUTRAL (no "efficient"/"performance"/"large"/"optimize" cue —
cueing optimization would bias AWAY from the dead-end and break the neutral-framing premise):
half "write a quick, simple solution", half a bare "implement the function".

This module is probe-only: it refuses --full and never builds the A0/A1/A2 experiment.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from etzchaim.llm.model_registry import resolve_model

from . import provider
from .arms import _SYSTEM
from .task import recurring_deadend as task

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "benchmarks" / "results" / "gating_harness"

# Haiku 4.5 list pricing, $/1M tokens (display estimate; billed = CLI total_cost_usd).
HAIKU_4_5_IN_PER_MTOK = 1.00
HAIKU_4_5_OUT_PER_MTOK = 5.00

_FRAMING_RELAXED = "Write a quick, simple solution — keep it short.\n\n"
_FRAMING_BARE = "Implement the function described below.\n\n"
DIVERSITY_MECHANISM = "framing_split (no CLI temperature; both halves scale-neutral)"


def _framing(i: int, n: int) -> tuple[str, str]:
    if i < n // 2:
        return _FRAMING_RELAXED, "relaxed"
    return _FRAMING_BARE, "bare"


def _took_deadend(key: str, oracle: task.OracleResult) -> bool:
    """A session 'took the dead-end' if the AST keyed it `naive` OR the op-budget tripped
    (catches the manual inner-loop naive the AST cannot label). A casting-naive escapes both —
    that is the documented meter hole the human eyeball covers."""
    return key == task.DEADEND_APPROACH or oracle.hit_trap


def run_probe(n: int = 8) -> tuple[list[dict], dict, str]:
    slug = resolve_model("haiku", profile="anthropic_full")
    trials: list[dict] = []
    for i in range(n):
        framing, framing_label = _framing(i, n)
        call = provider.chat_claude_cli(
            [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": framing + task.PROMPT},
            ]
        )
        declared = task.extract_declared_approach(call.text)
        code = task.extract_code(call.text)
        key = task.infer_approach_key(declared, code)
        oracle = task.run_oracle(code)
        trials.append(
            {
                "i": i,
                "framing": framing_label,
                "approach_key": key,
                "took_deadend": _took_deadend(key, oracle),
                "declared": declared,
                "oracle_passed": oracle.passed,
                "hit_trap": oracle.hit_trap,
                "failed_cases": oracle.failed_cases,
                "oracle_error": oracle.error,
                "code": code,  # FULL code saved for the human eyeball (Yohan's backstop)
                "prompt_tokens": call.prompt_tokens,
                "completion_tokens": call.completion_tokens,
                "cost_usd": call.cost_usd,
            }
        )

    sum_in = sum(t["prompt_tokens"] for t in trials)
    sum_out = sum(t["completion_tokens"] for t in trials)
    n_took = sum(t["took_deadend"] for t in trials)
    n_naive_ast = sum(t["approach_key"] == task.DEADEND_APPROACH for t in trials)
    n_prefix_ast = sum(t["approach_key"] == task.CORRECT_APPROACH for t in trials)
    agg = {
        "n": n,
        "model": slug,
        "diversity_mechanism": DIVERSITY_MECHANISM,
        "took_deadend_rate": (n_took / n) if n else None,
        "raw_deadend_rate_ast": (n_naive_ast / n) if n else None,
        "hit_trap_rate": sum(t["hit_trap"] for t in trials) / n if n else None,
        "key_distribution": {
            "naive": n_naive_ast,
            "prefix": n_prefix_ast,
            "other": n - n_naive_ast - n_prefix_ast,
        },
        "pass_rate": sum(t["oracle_passed"] for t in trials) / n if n else None,
        "total_tokens": sum_in + sum_out,
        "tokens_in": sum_in,
        "tokens_out": sum_out,
        "cost_usd_cli_measured": sum(t["cost_usd"] for t in trials),
        "cost_usd_listprice_estimate": (
            sum_in * HAIKU_4_5_IN_PER_MTOK + sum_out * HAIKU_4_5_OUT_PER_MTOK
        )
        / 1_000_000,
    }
    return trials, agg, slug


def _render_report(trials: list[dict], agg: dict, run_id: str) -> str:
    lines = [
        "# Haiku pre-check — recurring-deadend perf-trap (TEMPS 3, Stage 2)",
        "",
        f"- run_id: `{run_id}`",
        f"- model (config-resolved, current Haiku 4.5, zero hardcode): `{agg['model']}`",
        "- N single-shot trials, style A0 (no memory, no gate) — fresh context each (the wipe)",
        f"- diversity mechanism: {agg['diversity_mechanism']}",
        "- tokens + cost MEASURED from the CLI response (never fabricated)",
        "",
        "## Result",
        "",
        "- **took dead-end rate** (AST `naive` OR op-budget tripped): **{:.2f}**".format(
            agg["took_deadend_rate"]
        ),
        f"- raw dead-end rate (AST `naive` only): {agg['raw_deadend_rate_ast']:.2f}",
        f"- behavioural hit_trap rate (op-budget tripped): {agg['hit_trap_rate']:.2f}",
        f"- key distribution: naive={agg['key_distribution']['naive']} · "
        f"prefix={agg['key_distribution']['prefix']} · other={agg['key_distribution']['other']}",
        f"- oracle pass rate: {agg['pass_rate']:.2f}",
        f"- tokens: {agg['total_tokens']} total ({agg['tokens_in']} in / {agg['tokens_out']} out)",
        f"- cost: ${agg['cost_usd_cli_measured']:.4f} (CLI measured) · "
        f"${agg['cost_usd_listprice_estimate']:.4f} (list-price estimate, not billed)",
        "",
        "## Per-trial (eyeball the `naive` rows' code to confirm hit_trap)",
        "",
        "| # | framing | key | took_dead | passed | hit_trap | in | out |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for t in trials:
        lines.append(
            f"| {t['i']} | {t['framing']} | {t['approach_key']} | "
            f"{'yes' if t['took_deadend'] else 'no'} | "
            f"{'yes' if t['oracle_passed'] else 'no'} | "
            f"{'yes' if t['hit_trap'] else 'no'} | "
            f"{t['prompt_tokens']} | {t['completion_tokens']} |"
        )
    dr = agg["took_deadend_rate"]
    lines += ["", "## Verdict (frank)", ""]
    if dr is not None and dr > 0:
        lines.append(
            f"- took dead-end = {dr:.2f} > 0 -> Haiku enters the naive re-sum at least some of "
            f"the time -> the multi-session re-attempt experiment has a real phenomenon to "
            f"gate -> **GO**. (Eyeball 1-2 naive rows below to confirm hit_trap is genuine.)"
        )
    else:
        lines.append(
            "- took dead-end = 0.00 -> Haiku precomputes (prefix sums) by default on this "
            "neutral framing. Honest reading: the perf-trap phenomenon does not reproduce "
            "cheaply on Haiku -> **NO-GO**, STOP, report. A 4th honest NO-GO — do NOT bias the "
            "prompt toward the naive or hide the optimization."
        )
    lines += [
        "",
        "## Caveats",
        "",
        "- No CLI temperature flag -> diversity is framing-only; both framings scale-neutral.",
        "- Single-shot, single task. This is a go/no-go pre-check, not the experiment.",
        "- The op-meter is blind to an explicit `int(x)` cast (documented). EYEBALL the saved "
        "`code` of the naive trials in trials.json to confirm hit_trap reflects a real re-sum.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=8, help="number of single-shot trials (K)")
    parser.add_argument("--full", action="store_true", help="NOT implemented (probe only)")
    args = parser.parse_args()
    if args.full:
        raise SystemExit(
            "probe-only module: it does not build or run the A0/A1/A2 experiment."
        )

    # PRE-NETWORK preflight (cheap, but shown for discipline).
    est_in = args.n * 600
    est_out = args.n * 320
    est_cost = (
        est_in * HAIKU_4_5_IN_PER_MTOK + est_out * HAIKU_4_5_OUT_PER_MTOK
    ) / 1_000_000
    print(
        f"recurring-deadend pre-check — N={args.n} Haiku calls (style A0), "
        f"est ~${est_cost:.3f} (list-price). Resolving model via config…"
    )
    t0 = time.time()
    trials, agg, slug = run_probe(n=args.n)
    dt = time.time() - t0

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = RESULTS_DIR / f"probe_reattempt_{run_id}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text(_render_report(trials, agg, run_id))
    (out / "trials.json").write_text(
        json.dumps({"trials": trials, "aggregate": agg}, indent=2, default=str)
    )

    print(f"\nmodel used: {slug}")
    print(f"diversity:  {agg['diversity_mechanism']}")
    print(
        f"took dead-end rate: {agg['took_deadend_rate']:.2f} "
        f"(AST naive {agg['raw_deadend_rate_ast']:.2f} | hit_trap {agg['hit_trap_rate']:.2f})"
    )
    print(
        f"keys: naive={agg['key_distribution']['naive']} "
        f"prefix={agg['key_distribution']['prefix']} other={agg['key_distribution']['other']}"
    )
    print(f"pass_rate: {agg['pass_rate']:.2f}")
    print(
        f"tokens: {agg['total_tokens']} | cost CLI ${agg['cost_usd_cli_measured']:.4f} "
        f"| list-price est ${agg['cost_usd_listprice_estimate']:.4f}"
    )
    print(f"\nprobe done in {dt:.1f}s — report: {out / 'report.md'}")
    print("STOP — pre-check only. Did NOT run the full A0/A1/A2 experiment.")


if __name__ == "__main__":
    main()
