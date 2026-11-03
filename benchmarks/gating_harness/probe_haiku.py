"""Cheap Haiku elicitation probe — does balanced_brackets elicit the count dead-end?

    python -m benchmarks.gating_harness.probe_haiku [--n 10]

Style A0 (no memory, no gate). N single-shot Haiku calls via the OAuth Max CLI. The
question is narrow and decided BEFORE paying for the full A0/A1/A2 run: does a frontier
model ever take the count-only dead-end on this task, or does it always solve it?

    - raw_deadend ≫ 0  -> the task elicits an exploitable dead-end -> full run justified.
    - raw_deadend ≈ 0  -> too easy for a frontier model -> redesign the task first.

Honesty invariants:
    - tokens + cost are MEASURED from the CLI response (usage.input_tokens /
      output_tokens, total_cost_usd) — never fabricated.
    - the model slug is resolved via config (current Haiku 4.5), never the stale default.

DIVERSITY (mandatory — N greedy calls ≈ 1 sample otherwise). Varying the brackets is
useless (the model writes one general function). The real lever is temperature or
framing. The claude CLI exposes NO temperature flag (checked: `claude --help`), so this
probe varies the FRAMING across trials — half "write a quick/simple check", half "handle
the nesting carefully" — to test whether a relaxed framing elicits the count-only
approach. The function spec and the oracle are unchanged. The report records the
mechanism so raw_deadend is read correctly. No fabricated variety.

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
from .task import balanced_brackets as task

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "benchmarks" / "results" / "gating_harness"

# Haiku 4.5 list pricing, $/1M tokens (source: claude-api skill, 2026-06-13). Used ONLY
# for a display estimate; the billed figure reported is the CLI's measured total_cost_usd.
HAIKU_4_5_IN_PER_MTOK = 1.00
HAIKU_4_5_OUT_PER_MTOK = 5.00

# Framing variants — the diversity lever (no CLI temperature flag available).
_FRAMING_RELAXED = "Write a quick, simple check — keep it short.\n\n"
_FRAMING_CAREFUL = "Be careful to correctly handle the nesting and ordering of brackets.\n\n"
DIVERSITY_MECHANISM = "framing_split (no CLI temperature flag; half relaxed / half careful)"


def _framing(i: int, n: int) -> tuple[str, str]:
    """First half relaxed, second half careful."""
    if i < n // 2:
        return _FRAMING_RELAXED, "relaxed"
    return _FRAMING_CAREFUL, "careful"


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
                "declared": declared,
                "oracle_passed": oracle.passed,
                "hit_trap": oracle.hit_trap,
                "failed_cases": oracle.failed_cases,
                "prompt_tokens": call.prompt_tokens,
                "completion_tokens": call.completion_tokens,
                "cost_usd": call.cost_usd,
            }
        )

    sum_in = sum(t["prompt_tokens"] for t in trials)
    sum_out = sum(t["completion_tokens"] for t in trials)
    keys = [t["approach_key"] for t in trials]
    agg = {
        "n": n,
        "model": slug,
        "diversity_mechanism": DIVERSITY_MECHANISM,
        "raw_deadend_rate": sum(t["hit_trap"] for t in trials) / n if n else None,
        "key_distribution": {
            "count": keys.count("count"),
            "stack": keys.count("stack"),
            "unknown": keys.count("unknown"),
        },
        "unknown_rate": keys.count("unknown") / n if n else None,
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
        "# Haiku elicitation probe — balanced_brackets (TEMPS 2c)",
        "",
        f"- run_id: `{run_id}`",
        f"- model (config-resolved, current Haiku 4.5, zero hardcode): `{agg['model']}`",
        f"- N single-shot trials, style A0 (no memory, no gate)",
        f"- diversity mechanism: {agg['diversity_mechanism']}",
        f"- tokens + cost MEASURED from the CLI response (never fabricated)",
        "",
        "## Result",
        "",
        f"- **raw_deadend rate** (took count-only, failed the trap): "
        f"**{agg['raw_deadend_rate']:.2f}**",
        f"- approach-key distribution: count={agg['key_distribution']['count']} · "
        f"stack={agg['key_distribution']['stack']} · "
        f"unknown={agg['key_distribution']['unknown']}",
        f"- key=unknown rate (parser robustness on real Haiku output): "
        f"{agg['unknown_rate']:.2f}",
        f"- oracle pass rate: {agg['pass_rate']:.2f}",
        f"- tokens: {agg['total_tokens']} total ({agg['tokens_in']} in / {agg['tokens_out']} out)",
        f"- cost: ${agg['cost_usd_cli_measured']:.4f} (CLI measured) · "
        f"${agg['cost_usd_listprice_estimate']:.4f} (list-price estimate @ $1/$5 per Mtok, "
        f"not the billed amount)",
        "",
        "## Per-trial",
        "",
        "| # | framing | key | passed | hit_trap | in | out |",
        "|---|---|---|---|---|---|---|",
    ]
    for t in trials:
        lines.append(
            f"| {t['i']} | {t['framing']} | {t['approach_key']} | "
            f"{'yes' if t['oracle_passed'] else 'no'} | "
            f"{'yes' if t['hit_trap'] else 'no'} | "
            f"{t['prompt_tokens']} | {t['completion_tokens']} |"
        )
    dr = agg["raw_deadend_rate"]
    lines += [
        "",
        "## Verdict (frank)",
        "",
    ]
    if dr and dr > 0:
        lines.append(
            f"- raw_deadend = {dr:.2f} > 0 → the task ELICITS an exploitable dead-end on "
            f"Haiku → the full A0/A1/A2 run is justified."
        )
    else:
        lines.append(
            "- raw_deadend ≈ 0 → Haiku's greedy solution is correct. Weak sample (single "
            "task, framing-only diversity, no temperature lever) but a STRONG hint the task "
            "is TOO EASY for a frontier model. REDESIGN a task that elicits a recurring "
            "dead-end before paying for the full run."
        )
    lines += [
        "",
        "## Caveats",
        "",
        "- No CLI temperature flag → diversity is framing-only; N measures consistency as "
        "much as distribution. Not fabricated variety — see DIVERSITY in the module docstring.",
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

    print(f"Haiku elicitation probe — N={args.n}, model resolving via config…")
    t0 = time.time()
    trials, agg, slug = run_probe(n=args.n)
    dt = time.time() - t0

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = RESULTS_DIR / f"probe_haiku_{run_id}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text(_render_report(trials, agg, run_id))
    (out / "trials.json").write_text(
        json.dumps({"trials": trials, "aggregate": agg}, indent=2, default=str)
    )

    print(f"\nmodel used: {slug}")
    print(f"diversity:  {agg['diversity_mechanism']}")
    print(f"raw_deadend rate: {agg['raw_deadend_rate']:.2f}")
    print(
        f"keys: count={agg['key_distribution']['count']} "
        f"stack={agg['key_distribution']['stack']} "
        f"unknown={agg['key_distribution']['unknown']} "
        f"(unknown_rate={agg['unknown_rate']:.2f})"
    )
    print(f"pass_rate: {agg['pass_rate']:.2f}")
    print(
        f"tokens: {agg['total_tokens']} | cost CLI ${agg['cost_usd_cli_measured']:.4f} "
        f"| list-price est ${agg['cost_usd_listprice_estimate']:.4f}"
    )
    print(f"\nprobe done in {dt:.1f}s — report: {out / 'report.md'}")
    print("STOP — probe only. Did NOT run the full A0/A1/A2 experiment.")


if __name__ == "__main__":
    main()
