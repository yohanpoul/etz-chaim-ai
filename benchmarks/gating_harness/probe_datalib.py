"""Cheap Haiku elicitation probe — does the datalib prior-trap elicit the `total` dead-end?

    python -m benchmarks.gating_harness.probe_datalib [--n 10]

Style A0 (no memory, no gate). N single-shot Haiku calls via the OAuth Max CLI. The
question, decided BEFORE paying for the full A0/A1/A2 run: does a frontier model
recurrently reach for the obvious-but-wrong ``datalib.total`` (the obsolete-API trap), or
does it read the library and pick ``datalib.settle``?

    - 0 < raw_deadend < 1  -> the task elicits an exploitable dead-end -> full run justified.
    - raw_deadend ≈ 0      -> Haiku reads its way to settle; the phenomenon does not
                              reproduce cheaply on Haiku for this trap (report, do not torture).
    - raw_deadend ≈ 1      -> the fix is not discoverable enough -> make it MORE discoverable.

HONEST CALIBRATION (founder constraint, 2026-06-14): the trap must make Haiku reach for
``total`` NATURALLY (a realistic obsolete-API footgun — the obvious name is wrong because
the business rule moved on). ``settle`` is fully inlined and discoverable. Cap calibration
at 2-3 cheap iterations; if the rate will not enter (0, 1) without burying ``settle`` to
deceive the model, STOP and report. Do NOT over-tune the trap to force a fall.

Honesty invariants (shared with probe_haiku):
    - tokens + cost are MEASURED from the CLI response (usage.input/output_tokens,
      total_cost_usd) — never fabricated.
    - the slug is resolved via config (current Haiku 4.5) with a stale-slug guard inside
      ``provider.chat_claude_cli``.

DIVERSITY (mandatory). The claude CLI exposes NO temperature flag (re-confirmed
2026-06-14: ``claude --help`` has none), so this probe varies the FRAMING — half "write a
quick, simple solution", half "read the datalib source carefully before choosing a
function". The careful framing does NOT name ``settle`` (that would be a hint, not
diversity). The function spec and oracle are unchanged. No fabricated variety.

A fourth observable state — calling NEITHER datalib function (a bypass / reimplementation)
— is reported separately: it is neither the trap firing nor a library-correct solution.
The conditioned rate ``trap / (trap + settle)`` is reported alongside the raw rate so a
bypass surge cannot be misread as "the trap did not fire".

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
from .task import datalib_prior_trap as task

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "benchmarks" / "results" / "gating_harness"

# Haiku 4.5 list pricing, $/1M tokens (source: claude-api skill, 2026-06-13). Display
# estimate only; the billed figure reported is the CLI's measured total_cost_usd.
HAIKU_4_5_IN_PER_MTOK = 1.00
HAIKU_4_5_OUT_PER_MTOK = 5.00

# Framing variants — the diversity lever (no CLI temperature flag available). The careful
# framing encourages reading the library WITHOUT naming the correct function.
_FRAMING_RELAXED = "Write a quick, simple solution — keep it short.\n\n"
_FRAMING_CAREFUL = (
    "Read the provided `datalib` source carefully before choosing which function to call.\n\n"
)
DIVERSITY_MECHANISM = "framing_split (no CLI temperature flag; half quick / half careful)"


def _framing(i: int, n: int) -> tuple[str, str]:
    """First half relaxed, second half careful."""
    if i < n // 2:
        return _FRAMING_RELAXED, "relaxed"
    return _FRAMING_CAREFUL, "careful"


def _bucket(key: str, oracle: task.OracleResult) -> str:
    """Reporting bucket. ``total``/``settle`` come straight from the AST key. A key of
    'unknown' splits into 'bypass' (order_cost ran — a reimplementation that called
    neither datalib fn) vs 'unknown' (unparseable / order_cost not defined / exec error).
    """
    if key in (task.DEADEND_APPROACH, task.CORRECT_APPROACH):
        return key
    ran = oracle.error is None  # order_cost was defined and callable
    return "bypass" if ran else "unknown"


def run_probe(n: int = 10) -> tuple[list[dict], dict, str]:
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
                "bucket": _bucket(key, oracle),
                "declared": declared,
                "oracle_passed": oracle.passed,
                "hit_trap": oracle.hit_trap,
                "failed_cases": oracle.failed_cases,
                "oracle_error": oracle.error,
                "prompt_tokens": call.prompt_tokens,
                "completion_tokens": call.completion_tokens,
                "cost_usd": call.cost_usd,
            }
        )

    sum_in = sum(t["prompt_tokens"] for t in trials)
    sum_out = sum(t["completion_tokens"] for t in trials)
    buckets = [t["bucket"] for t in trials]
    n_trap = buckets.count(task.DEADEND_APPROACH)
    n_settle = buckets.count(task.CORRECT_APPROACH)
    n_engaged = n_trap + n_settle
    agg = {
        "n": n,
        "model": slug,
        "diversity_mechanism": DIVERSITY_MECHANISM,
        "raw_deadend_rate": (n_trap / n) if n else None,
        "conditioned_deadend_rate": (n_trap / n_engaged) if n_engaged else None,
        "key_distribution": {
            "total": n_trap,
            "settle": n_settle,
            "bypass": buckets.count("bypass"),
            "unknown": buckets.count("unknown"),
        },
        "bypass_rate": buckets.count("bypass") / n if n else None,
        "unknown_rate": buckets.count("unknown") / n if n else None,
        "pass_rate": sum(t["oracle_passed"] for t in trials) / n if n else None,
        "hit_trap_rate": sum(t["hit_trap"] for t in trials) / n if n else None,
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
        "# Haiku elicitation probe — datalib prior-trap (TEMPS 2d)",
        "",
        f"- run_id: `{run_id}`",
        f"- model (config-resolved, current Haiku 4.5, zero hardcode): `{agg['model']}`",
        "- N single-shot trials, style A0 (no memory, no gate)",
        f"- diversity mechanism: {agg['diversity_mechanism']}",
        "- tokens + cost MEASURED from the CLI response (never fabricated)",
        "",
        "## Result",
        "",
        "- **raw dead-end rate** (called `datalib.total`): **{:.2f}**".format(
            agg["raw_deadend_rate"]
        ),
        f"- **conditioned dead-end rate** (`total / (total + settle)`): "
        f"{'NA' if agg['conditioned_deadend_rate'] is None else format(agg['conditioned_deadend_rate'], '.2f')}",
        f"- key distribution: total={agg['key_distribution']['total']} · "
        f"settle={agg['key_distribution']['settle']} · "
        f"bypass={agg['key_distribution']['bypass']} · "
        f"unknown={agg['key_distribution']['unknown']}",
        f"- bypass rate (reimplemented, called neither fn): {agg['bypass_rate']:.2f}",
        f"- unknown rate (unparseable / no order_cost): {agg['unknown_rate']:.2f}",
        f"- oracle pass rate: {agg['pass_rate']:.2f}",
        f"- behavioural hit_trap rate (returned the naive total on a discriminating case): "
        f"{agg['hit_trap_rate']:.2f}",
        f"- tokens: {agg['total_tokens']} total ({agg['tokens_in']} in / {agg['tokens_out']} out)",
        f"- cost: ${agg['cost_usd_cli_measured']:.4f} (CLI measured) · "
        f"${agg['cost_usd_listprice_estimate']:.4f} (list-price estimate @ $1/$5 per Mtok, "
        f"not the billed amount)",
        "",
        "## Per-trial",
        "",
        "| # | framing | bucket | key | passed | hit_trap | in | out |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for t in trials:
        lines.append(
            f"| {t['i']} | {t['framing']} | {t['bucket']} | {t['approach_key']} | "
            f"{'yes' if t['oracle_passed'] else 'no'} | "
            f"{'yes' if t['hit_trap'] else 'no'} | "
            f"{t['prompt_tokens']} | {t['completion_tokens']} |"
        )
    dr = agg["raw_deadend_rate"]
    lines += ["", "## Verdict (frank)", ""]
    if dr is not None and 0 < dr < 1:
        lines.append(
            f"- raw dead-end = {dr:.2f} ∈ (0, 1) → the task elicits a recurrent dead-end on "
            f"Haiku NATURALLY → the full A0/A1/A2 run is justified."
        )
    elif dr == 0:
        lines.append(
            "- raw dead-end = 0.00 → Haiku read the library and chose `settle` every time. "
            "Honest reading: the obsolete-API phenomenon does not reproduce cheaply on Haiku "
            "for this trap as framed. ONE honest knob may be tried (strengthen the verb-match "
            "/ ordering salience, weight framing toward 'quick') — but do NOT bury `settle` to "
            "deceive. If a centered, honest config cannot elicit it within 2-3 iters, STOP and "
            "report NO-GO."
        )
    else:  # dr == 1 (or None)
        lines.append(
            "- raw dead-end ≈ 1.00 → Haiku never found `settle`. The fix may not be discoverable "
            "enough; make it MORE discoverable (a one-line module breadcrumb, more 'careful' "
            "framings) and re-probe. This direction increases honesty, not deception."
        )
    if agg["bypass_rate"] and agg["bypass_rate"] > 0:
        lines.append(
            f"- bypass_rate = {agg['bypass_rate']:.2f} > 0 → some trials reimplemented instead of "
            f"using `datalib`; read the CONDITIONED rate, and consider strengthening the 'use the "
            f"provided datalib' contract if bypass dominates."
        )
    lines += [
        "",
        "## Caveats",
        "",
        "- No CLI temperature flag → diversity is framing-only; N measures consistency as much "
        "as distribution. Not fabricated variety — see DIVERSITY in the module docstring.",
        "- Single task, single-shot. This is a go/no-go probe, not the experiment.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=10, help="number of single-shot trials")
    parser.add_argument("--full", action="store_true", help="NOT implemented (probe only)")
    args = parser.parse_args()
    if args.full:
        raise SystemExit(
            "probe-only module: it does not build or run the A0/A1/A2 experiment."
        )

    print(f"datalib prior-trap probe — N={args.n}, model resolving via config…")
    t0 = time.time()
    trials, agg, slug = run_probe(n=args.n)
    dt = time.time() - t0

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = RESULTS_DIR / f"probe_datalib_{run_id}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text(_render_report(trials, agg, run_id))
    (out / "trials.json").write_text(
        json.dumps({"trials": trials, "aggregate": agg}, indent=2, default=str)
    )

    cond = agg["conditioned_deadend_rate"]
    print(f"\nmodel used: {slug}")
    print(f"diversity:  {agg['diversity_mechanism']}")
    print(f"raw dead-end rate: {agg['raw_deadend_rate']:.2f}", end="")
    print(f" | conditioned: {'NA' if cond is None else format(cond, '.2f')}")
    print(
        f"keys: total={agg['key_distribution']['total']} "
        f"settle={agg['key_distribution']['settle']} "
        f"bypass={agg['key_distribution']['bypass']} "
        f"unknown={agg['key_distribution']['unknown']}"
    )
    print(f"pass_rate: {agg['pass_rate']:.2f} | hit_trap_rate: {agg['hit_trap_rate']:.2f}")
    print(
        f"tokens: {agg['total_tokens']} | cost CLI ${agg['cost_usd_cli_measured']:.4f} "
        f"| list-price est ${agg['cost_usd_listprice_estimate']:.4f}"
    )
    print(f"\nprobe done in {dt:.1f}s — report: {out / 'report.md'}")
    print("STOP — probe only. Did NOT run the full A0/A1/A2 experiment.")


if __name__ == "__main__":
    main()
