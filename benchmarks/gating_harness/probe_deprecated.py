"""Cheap Haiku elicitation probe — does a REAL deprecated-API prior-trap elicit the dead-end?

    python -m benchmarks.gating_harness.probe_deprecated [--n 10]

Style A0 (no memory, no gate). For EACH available subtask (pandas / numpy), N single-shot
Haiku calls via the OAuth Max CLI. The question, decided BEFORE paying for the full
A0/A1/A2 run: does a frontier model recurrently reach for a REMOVED API (``DataFrame.append``
/ ``np.float``) — a genuine training-prior footgun — or does it write current-era code?

This is TEMPS 2e, the third and final cheap single-shot probe (option A). Two prior NO-GOs
(balanced_brackets, datalib_prior_trap) failed structurally; a REAL deprecated API is the only
honest way to elicit a single-shot dead-end without burying the modern solution. The most
likely (and most informative) outcome is a clean 3rd NO-GO that closes the cheap path and
clears the way to the multi-session fork (B/C) — ADR-0009's native domain.

    - 0 < raw_deadend < 1 on >=1 subtask -> the task elicits an exploitable dead-end -> GO.
    - raw_deadend ~= 0 on BOTH             -> 3rd NO-GO, decisive: single-shot is the wrong
                                              gate (report, do NOT torture the trap).

HONEST CALIBRATION (founder constraint, 2026-06-14): the prompts state the GOAL only and
NEVER name the deprecated method nor the modern fix. The framing-split is the diversity lever
(the claude CLI has no temperature flag — re-confirmed): half "quick/simple", half
"modern/clean/production-ready". The careful framing does NOT name the current API (that
would be a hint, not diversity). Do NOT bias the prompt toward the deprecated API to force a
fall; a NO-GO is a result.

Honesty invariants (shared with probe_datalib):
    - tokens + cost are MEASURED from the CLI response (usage.input/output_tokens,
      total_cost_usd) — never fabricated.
    - the slug is resolved via config (current Haiku 4.5) with a stale-slug guard inside
      ``provider.chat_claude_cli``.

A bucket calling NEITHER the deprecated nor a current-API path (a bypass) is reported
separately; the conditioned rate ``deprecated / (deprecated + correct)`` is reported
alongside the raw rate so a bypass surge cannot be misread as "the trap did not fire". A
subtask whose library is unavailable is reported ``skipped`` and excluded from the rates.

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
from .task import deprecated_api_trap as task

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "benchmarks" / "results" / "gating_harness"

# Haiku 4.5 list pricing, $/1M tokens (source: claude-api skill, 2026-06-13). Display
# estimate only; the billed figure reported is the CLI's measured total_cost_usd.
HAIKU_4_5_IN_PER_MTOK = 1.00
HAIKU_4_5_OUT_PER_MTOK = 5.00

# Framing variants — the diversity lever (no CLI temperature flag). Neither names the
# deprecated method nor the modern fix; "modern" is era-framing, not an API hint.
_FRAMING_RELAXED = "Write a quick, simple solution — keep it short, just make it work.\n\n"
_FRAMING_CAREFUL = "Write modern, clean, production-ready code following current best practices.\n\n"
DIVERSITY_MECHANISM = "framing_split (no CLI temperature flag; half quick / half modern)"


def _framing(i: int, n: int) -> tuple[str, str]:
    """First half relaxed, second half careful/modern."""
    if i < n // 2:
        return _FRAMING_RELAXED, "relaxed"
    return _FRAMING_CAREFUL, "modern"


def _bucket(key: str, oracle: task.OracleResult) -> str:
    """Reporting bucket. ``deprecated``/``correct`` come straight from the AST key. A
    capability-skipped subtask is ``skipped``. Otherwise a key of 'unknown' splits into
    'bypass' (the function ran — used neither API path) vs 'unknown' (unparseable / not
    defined / exec error)."""
    if oracle.skipped:
        return "skipped"
    if key in (task.DEADEND_APPROACH, task.CORRECT_APPROACH):
        return key
    ran = oracle.error is None
    return "bypass" if ran else "unknown"


def run_subtask(subtask: task.Subtask, n: int) -> tuple[list[dict], dict]:
    trials: list[dict] = []
    for i in range(n):
        framing, framing_label = _framing(i, n)
        call = provider.chat_claude_cli(
            [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": framing + subtask.PROMPT},
            ]
        )
        declared = task.extract_declared_approach(call.text)
        code = task.extract_code(call.text, subtask.func_name)
        key = task.infer_approach_key(declared, code, subtask)
        oracle = subtask.run_oracle(code)
        ast_hit = subtask.classify_from_code(code)
        trials.append(
            {
                "subtask": subtask.key,
                "i": i,
                "framing": framing_label,
                "approach_key": key,
                "bucket": _bucket(key, oracle),
                "declared": declared,
                "ast_hit": ast_hit,
                "oracle_passed": oracle.passed,
                "hit_trap": oracle.hit_trap,
                "oracle_skipped": oracle.skipped,
                "failed_cases": oracle.failed_cases,
                "oracle_error": oracle.error,
                "prompt_tokens": call.prompt_tokens,
                "completion_tokens": call.completion_tokens,
                "cost_usd": call.cost_usd,
            }
        )

    buckets = [t["bucket"] for t in trials]
    n_dep = buckets.count(task.DEADEND_APPROACH)
    n_cor = buckets.count(task.CORRECT_APPROACH)
    n_engaged = n_dep + n_cor
    agg = {
        "subtask": subtask.key,
        "lib": subtask.lib_name,
        "lib_version": subtask.version,
        "func_name": subtask.func_name,
        "n": n,
        "raw_deadend_rate": (n_dep / n) if n else None,
        "conditioned_deadend_rate": (n_dep / n_engaged) if n_engaged else None,
        "key_distribution": {
            "deprecated": n_dep,
            "correct": n_cor,
            "bypass": buckets.count("bypass"),
            "unknown": buckets.count("unknown"),
            "skipped": buckets.count("skipped"),
        },
        "pass_rate": sum(t["oracle_passed"] for t in trials) / n if n else None,
        "hit_trap_rate": sum(t["hit_trap"] for t in trials) / n if n else None,
        "tokens_in": sum(t["prompt_tokens"] for t in trials),
        "tokens_out": sum(t["completion_tokens"] for t in trials),
        "cost_usd_cli_measured": sum(t["cost_usd"] for t in trials),
    }
    return trials, agg


def run_probe(n: int = 10) -> tuple[list[dict], list[dict], dict, str]:
    slug = resolve_model("haiku", profile="anthropic_full")
    all_trials: list[dict] = []
    per_subtask: list[dict] = []
    for subtask in task.AVAILABLE_SUBTASKS:
        trials, agg = run_subtask(subtask, n)
        all_trials.extend(trials)
        per_subtask.append(agg)

    sum_in = sum(t["prompt_tokens"] for t in all_trials)
    sum_out = sum(t["completion_tokens"] for t in all_trials)
    buckets = [t["bucket"] for t in all_trials]
    n_dep = buckets.count(task.DEADEND_APPROACH)
    n_cor = buckets.count(task.CORRECT_APPROACH)
    n_engaged = n_dep + n_cor
    combined = {
        "n_total": len(all_trials),
        "model": slug,
        "diversity_mechanism": DIVERSITY_MECHANISM,
        "pandas_version": task.PANDAS_VERSION,
        "numpy_version": task.NUMPY_VERSION,
        "subtasks_run": [s.key for s in task.AVAILABLE_SUBTASKS],
        "raw_deadend_rate_combined": (n_dep / len(all_trials)) if all_trials else None,
        "conditioned_deadend_rate_combined": (n_dep / n_engaged) if n_engaged else None,
        "key_distribution": {
            "deprecated": n_dep,
            "correct": n_cor,
            "bypass": buckets.count("bypass"),
            "unknown": buckets.count("unknown"),
            "skipped": buckets.count("skipped"),
        },
        "total_tokens": sum_in + sum_out,
        "tokens_in": sum_in,
        "tokens_out": sum_out,
        "cost_usd_cli_measured": sum(t["cost_usd"] for t in all_trials),
        "cost_usd_listprice_estimate": (
            sum_in * HAIKU_4_5_IN_PER_MTOK + sum_out * HAIKU_4_5_OUT_PER_MTOK
        )
        / 1_000_000,
    }
    return all_trials, per_subtask, combined, slug


def _fmt(x) -> str:
    return "NA" if x is None else format(x, ".2f")


def _render_report(trials: list[dict], per_subtask: list[dict], combined: dict, run_id: str) -> str:
    lines = [
        "# Haiku elicitation probe — deprecated-API prior-trap (TEMPS 2e)",
        "",
        f"- run_id: `{run_id}`",
        f"- model (config-resolved, current Haiku 4.5, zero hardcode): `{combined['model']}`",
        f"- pandas: `{combined['pandas_version']}` · numpy: `{combined['numpy_version']}` (repro)",
        "- N single-shot trials per subtask, style A0 (no memory, no gate)",
        f"- diversity mechanism: {combined['diversity_mechanism']}",
        "- tokens + cost MEASURED from the CLI response (never fabricated)",
        "",
        "## Result — per subtask",
        "",
        "| subtask | lib | raw dead-end | conditioned | dep | correct | bypass | unknown | pass | hit_trap |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for a in per_subtask:
        kd = a["key_distribution"]
        lines.append(
            f"| {a['subtask']} | {a['lib']} {a['lib_version']} | "
            f"**{_fmt(a['raw_deadend_rate'])}** | {_fmt(a['conditioned_deadend_rate'])} | "
            f"{kd['deprecated']} | {kd['correct']} | {kd['bypass']} | {kd['unknown']} | "
            f"{_fmt(a['pass_rate'])} | {_fmt(a['hit_trap_rate'])} |"
        )
    kd = combined["key_distribution"]
    lines += [
        "",
        "## Result — combined",
        "",
        f"- **raw dead-end rate (combined)**: **{_fmt(combined['raw_deadend_rate_combined'])}**",
        f"- conditioned dead-end (combined, `dep / (dep + correct)`): "
        f"{_fmt(combined['conditioned_deadend_rate_combined'])}",
        f"- key distribution: deprecated={kd['deprecated']} · correct={kd['correct']} · "
        f"bypass={kd['bypass']} · unknown={kd['unknown']} · skipped={kd['skipped']}",
        f"- tokens: {combined['total_tokens']} total "
        f"({combined['tokens_in']} in / {combined['tokens_out']} out)",
        f"- cost: ${combined['cost_usd_cli_measured']:.4f} (CLI measured) · "
        f"${combined['cost_usd_listprice_estimate']:.4f} (list-price est @ $1/$5 per Mtok, "
        f"not the billed amount)",
        "",
        "## Per-trial",
        "",
        "| subtask | # | framing | bucket | key | ast_hit | passed | hit_trap | in | out |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for t in trials:
        lines.append(
            f"| {t['subtask']} | {t['i']} | {t['framing']} | {t['bucket']} | "
            f"{t['approach_key']} | {t['ast_hit']} | "
            f"{'yes' if t['oracle_passed'] else 'no'} | "
            f"{'yes' if t['hit_trap'] else 'no'} | "
            f"{t['prompt_tokens']} | {t['completion_tokens']} |"
        )

    lines += ["", "## Verdict (frank)", ""]
    raws = [(a["subtask"], a["raw_deadend_rate"]) for a in per_subtask]
    elicited = [s for s, r in raws if r is not None and 0 < r < 1]
    if elicited:
        lines.append(
            f"- raw dead-end ∈ (0, 1) on subtask(s) {elicited} → the deprecated-API trap "
            f"elicits a recurrent dead-end on Haiku NATURALLY → **GO**: the full A0/A1/A2 run "
            f"is justified. The real test remains the cross-wipe re-attempt: A2 must beat **A1 "
            f"CHANGELOG**, not A0; ablation must erase the gain."
        )
    elif all((r is not None and r == 0) for _, r in raws) and raws:
        lines.append(
            "- raw dead-end = 0.00 on EVERY subtask → even a real removed-API prior does not "
            "trap Haiku in a single shot. Honest reading: cheap single-shot elicitation is "
            "STRUCTURALLY the wrong gate (3rd NO-GO, decisive). Reprise = fork B/C "
            "(multi-session), ADR-0009's native domain, where the dead-end is a re-attempt "
            "across a wipe — not a first-shot mistake. Do NOT torture the trap to avoid this."
        )
    else:
        lines.append(
            "- mixed / boundary result (some subtask at 1.00 or NA) → inspect per-subtask "
            "table; a rate of 1.00 means the goal was under-specified (the model could not "
            "write the current API at all), NOT that the trap is good. Report honestly."
        )

    lines += [
        "",
        "## Caveats",
        "",
        "- No CLI temperature flag → diversity is framing-only; N measures consistency as much "
        "as distribution. Not fabricated variety — see DIVERSITY in the module docstring.",
        "- Single-shot, single task family. This is a go/no-go probe, not the experiment.",
        "- pandas installed test-only into the etz-chaim .venv (NOT in pyproject) so the "
        "df.append prior could be tested; version recorded above for repro.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=10, help="single-shot trials PER subtask")
    parser.add_argument("--full", action="store_true", help="NOT implemented (probe only)")
    args = parser.parse_args()
    if args.full:
        raise SystemExit(
            "probe-only module: it does not build or run the A0/A1/A2 experiment."
        )

    if not task.AVAILABLE_SUBTASKS:
        raise SystemExit(
            "no subtask is available (pandas absent/<2.0 AND numpy absent/<1.24) — "
            "install at least one target library before probing."
        )

    avail = ", ".join(f"{s.key}({s.version})" for s in task.AVAILABLE_SUBTASKS)
    print(f"deprecated-API prior-trap probe — N={args.n}/subtask, subtasks: {avail}")
    t0 = time.time()
    trials, per_subtask, combined, slug = run_probe(n=args.n)
    dt = time.time() - t0

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = RESULTS_DIR / f"probe_deprecated_{run_id}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text(_render_report(trials, per_subtask, combined, run_id))
    (out / "trials.json").write_text(
        json.dumps(
            {"trials": trials, "per_subtask": per_subtask, "combined": combined},
            indent=2,
            default=str,
        )
    )

    print(f"\nmodel used: {slug}")
    print(f"pandas {combined['pandas_version']} · numpy {combined['numpy_version']}")
    for a in per_subtask:
        kd = a["key_distribution"]
        print(
            f"[{a['subtask']:>6}] raw dead-end {_fmt(a['raw_deadend_rate'])} | "
            f"conditioned {_fmt(a['conditioned_deadend_rate'])} | "
            f"dep={kd['deprecated']} correct={kd['correct']} bypass={kd['bypass']} "
            f"unknown={kd['unknown']} | pass {_fmt(a['pass_rate'])} | hit_trap {_fmt(a['hit_trap_rate'])}"
        )
    print(
        f"COMBINED raw dead-end {_fmt(combined['raw_deadend_rate_combined'])} | "
        f"conditioned {_fmt(combined['conditioned_deadend_rate_combined'])}"
    )
    print(
        f"tokens: {combined['total_tokens']} | cost CLI ${combined['cost_usd_cli_measured']:.4f} "
        f"| list-price est ${combined['cost_usd_listprice_estimate']:.4f}"
    )
    print(f"\nprobe done in {dt:.1f}s — report: {out / 'report.md'}")
    print("STOP — probe only. Did NOT run the full A0/A1/A2 experiment.")


if __name__ == "__main__":
    main()
