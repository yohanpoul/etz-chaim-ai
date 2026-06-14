"""Smoke orchestrator for the TEMPS-2 gating harness.

    python -m benchmarks.gating_harness.run --smoke

Runs ONE task (balanced_brackets) x N sessions (default 2) across A0/A1/A2 on the
LOCAL Ollama model, computes the four metrics, writes a report, then STOPS. It does
NOT run a full evaluation and refuses --full: the real run needs a frontier model
(Haiku minimum) and many tasks; the smoke only proves the harness tics end-to-end and
the metrics compute.
"""

from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

from . import provider
from .arms import run_a0, run_a1, run_a2
from .metrics import compute_metrics
from .task import balanced_brackets as task

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "benchmarks" / "results" / "gating_harness"
TEST_DB_URL = "postgresql://localhost/etz_chaim_test"

# Haiku 4.5 list pricing, $/1M tokens (display estimate only; billed = CLI total_cost_usd).
HAIKU_4_5_IN_PER_MTOK = 1.00
HAIKU_4_5_OUT_PER_MTOK = 5.00
# Rough per-call token estimate for the PRE-network budget preflight (measured post-run).
_EST_TOKENS_IN_PER_CALL = 600
_EST_TOKENS_OUT_PER_CALL = 320


def _resolve_task(name: str):
    """Import a task module by name from benchmarks.gating_harness.task (additive --task)."""
    return importlib.import_module(f"benchmarks.gating_harness.task.{name}")


# --------------------------------------------------------------------------- #
# Persistent store setup for A2 (mirrors gating/tests/conftest.py bootstrap)
# --------------------------------------------------------------------------- #


def _setup_store():
    """Ensure etz_chaim_test exists + schemas loaded + pool ready; return a clean mem."""
    import psycopg2

    from tests._psql import require_psql

    conn = psycopg2.connect("postgresql://localhost/postgres")
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'etz_chaim_test'")
    if not cur.fetchone():
        cur.execute("CREATE DATABASE etz_chaim_test")
    cur.close()
    conn.close()

    conn = psycopg2.connect(TEST_DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cur.close()
    conn.close()

    for schema in ("epistememory/schema.sql", "dissensuengine/schema.sql"):
        subprocess.run(
            [require_psql(), "-d", "etz_chaim_test", "-f", schema],
            cwd=str(PROJECT_ROOT), check=True, capture_output=True,
        )

    from pool import get_conn, init_pool

    init_pool(TEST_DB_URL)
    with get_conn() as c:  # clean slate for the smoke
        with c.cursor() as cu:
            cu.execute("TRUNCATE epistememory CASCADE")

    from epistememory.core import EpisteMemory

    return EpisteMemory(db_url=TEST_DB_URL)


def _truncate_store() -> None:
    """Clean slate on the persistent store (between independent A2 arms)."""
    from pool import get_conn

    with get_conn() as c:
        with c.cursor() as cu:
            cu.execute("TRUNCATE epistememory CASCADE")


# --------------------------------------------------------------------------- #
# Report rendering
# --------------------------------------------------------------------------- #


def _fmt(v) -> str:
    if v is None:
        return "NA"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)


def _render_report(results: dict, sessions: int, resolved, run_id: str) -> str:
    rows = ["A0", "A1", "A2"]
    keys = [
        ("dead_end_reattempt_rate", "dead-end re-attempt rate (memory-conditioned)"),
        ("raw_dead_end_rate", "raw dead-end rate (all sessions)"),
        ("self_contradiction_rate", "self-contradiction rate"),
        ("total_generations", "iterations (model generations)"),
        ("total_tokens", "tokens to oracle (measured)"),
        ("final_correctness_passed_any", "final correctness (passed any)"),
        ("gate_rejections", "gate rejections"),
    ]
    lines = [
        "# Gating harness — Phase 2 TEMPS 2 — SMOKE",
        "",
        f"- run_id: `{run_id}`",
        f"- task: `{task.TASK_ID}` (external; reference-oracle ground truth, no LLM judge)",
        f"- sessions per arm: {sessions}  ·  context-wiped between sessions",
        f"- model (config-resolved, zero hardcode): `{resolved.model}` "
        f"via provider `{resolved.provider}` @ `{resolved.host}`",
        f"- tokens: MEASURED from provider (`prompt_eval_count`+`eval_count`), never fabricated",
        "",
        "## Decision (A), treated as a KILL TEST",
        "",
        "A2 matches a refuted approach by an **exact tag** through a *stipulated-perfect* "
        "classifier — the **UPPER BOUND** of enforcement (real matching is fuzzy/semantic "
        "and strictly harder).",
        "",
        "- **A2 ≤ A1** → PIVOT (an enforced gate can't even beat an advisory CHANGELOG).",
        "- **A2 > A1** → floor crossed, **NOT validated**: only the upper bound clears the "
        "baseline; the real claim (B: real matching + deprecate/contradict lifecycle) "
        "remains untested.",
        "",
        "## Metrics",
        "",
        "| metric | A0 (bare) | A1 (CHANGELOG) | A2 (gate) |",
        "|---|---|---|---|",
    ]
    for k, label in keys:
        cells = [_fmt(results[a][1].get(k)) for a in rows]
        lines.append(f"| {label} | {cells[0]} | {cells[1]} | {cells[2]} |")

    a1m, a2m = results["A1"][1], results["A2"][1]
    lines += [
        "",
        "## Smoke read (NOT a verdict)",
        "",
        "This is **one task** on a **small local model** — statistically meaningless by "
        "construction. It exists to prove the harness runs end-to-end and the four "
        "metrics compute. The pivot/no-pivot decision needs the real run.",
        "",
        f"- A1 dead-end re-attempt (memory-conditioned): {_fmt(a1m.get('dead_end_reattempt_rate'))}",
        f"- A2 dead-end re-attempt (memory-conditioned): {_fmt(a2m.get('dead_end_reattempt_rate'))}",
        f"- A2 gate rejections fired: {a2m.get('gate_rejections')}",
        "",
        "## Caveats (load-bearing)",
        "",
        "- **Plumbing, not the edge.** A2 uses the TEMPS-1 FACT/exact-tag wire; it does "
        "NOT exercise `epistememory.deprecate`/`contradict` (deprecated beliefs are "
        "invisible to `recall`, db.py:171). Green here ≠ ADR-0009 validated.",
        "- **Real run needs a frontier model (Haiku minimum).** A 9B local model often "
        "solves this textbook task correctly, so it may never enter the dead-end; that "
        "leaves the gate path un-exercised by the live arms (the synthetic sub-check in "
        "`tests/test_smoke.py` covers the gate-reject path deterministically).",
        "- **Perfect classifier = upper bound.** `task.classify_approach` is stipulated "
        "perfect; a real deployment must do fuzzy/semantic approach matching.",
        "",
    ]
    return "\n".join(lines)


def _write(results: dict, report: str, run_id: str) -> Path:
    out = RESULTS_DIR / f"smoke_{run_id}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text(report)
    raw = {
        a: {
            "records": [r.to_dict() for r in recs],
            "metrics": m,
        }
        for a, (recs, m) in results.items()
    }
    (out / "records.json").write_text(json.dumps(raw, indent=2, default=str))
    return out / "report.md"


# --------------------------------------------------------------------------- #
# Entry
# --------------------------------------------------------------------------- #


def run_smoke(sessions: int = 2, task=task) -> tuple[dict, Path]:
    resolved = provider.resolve_local()  # header transparency + config-driven proof
    mem = _setup_store()
    try:
        a0 = run_a0(sessions, task=task)
        a1 = run_a1(sessions, task=task)
        a2 = run_a2(sessions, mem, task=task)
    finally:
        mem.close()

    results = {
        "A0": (a0, compute_metrics(a0)),
        "A1": (a1, compute_metrics(a1)),
        "A2": (a2, compute_metrics(a2)),
    }
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    report = _render_report(results, sessions, resolved, run_id)
    path = _write(results, report, run_id)
    return results, path


# --------------------------------------------------------------------------- #
# Experiment (TEMPS 3): multi-session re-attempt — A0 / A1 (noise sweep) / A2 / A2-ablation
# --------------------------------------------------------------------------- #

_DEFAULT_NOISE_LEVELS = [0, 5, 20, 50]


def _noise(n: int, *, deadend_key: str) -> list[str]:
    """N unrelated prior-failure CHANGELOG entries — the discriminant regime (Risk #1): a
    realistic noisy history that stresses A1's PASSIVE recall while the gate stays O(1) keyed.
    Guaranteed NOT to contain the dead-end key, so A1.memory_had_deadend is driven only by
    REAL refutations the run accumulates."""
    entries = []
    for k in range(n):
        e = (
            f"approach 'variant-{k:03d}' failed on unrelated-task-{k % 9}: "
            f"off-by-one on edge case {k}"
        )
        assert deadend_key not in e  # contract: noise must never name the dead-end
        entries.append(e)
    return entries


def _experiment_calls(k: int, noise_levels: list[int]) -> int:
    """Upper-bound Haiku call count for the preflight (A2 may double on a gate reject)."""
    a0 = k
    a1 = k * len(noise_levels)
    a2 = 2 * k        # gate-on: up to 2 generations/session on a reject
    a2_ablation = k   # gate off: never rejects -> 1 generation/session
    return a0 + a1 + a2 + a2_ablation


def _preflight(k: int, noise_levels: list[int]) -> dict:
    calls = _experiment_calls(k, noise_levels)
    est_in = calls * _EST_TOKENS_IN_PER_CALL
    est_out = calls * _EST_TOKENS_OUT_PER_CALL
    est_cost = (
        est_in * HAIKU_4_5_IN_PER_MTOK + est_out * HAIKU_4_5_OUT_PER_MTOK
    ) / 1_000_000
    return {"calls": calls, "est_in": est_in, "est_out": est_out, "est_cost_usd": est_cost}


def run_experiment(
    task_name: str = "recurring_deadend",
    k: int = 12,
    noise_levels: list[int] | None = None,
    confirm: bool = False,
) -> tuple[dict, Path] | None:
    """TEMPS-3 experiment. Shows a PRE-NETWORK budget preflight; without --confirm it is a
    human gate and returns None (spends nothing)."""
    task_mod = _resolve_task(task_name)
    levels = list(noise_levels) if noise_levels is not None else list(_DEFAULT_NOISE_LEVELS)
    pf = _preflight(k, levels)

    print("=" * 72)
    print(f"EXPERIMENT PREFLIGHT — task={task_name}  K={k}  noise_levels={levels}")
    print(f"  arms: A0 · A1 (×{len(levels)} noise levels) · A2 (gate ON) · A2 (ablation, gate OFF)")
    print("  model: Haiku 4.5 via OAuth CLI — tokens + cost MEASURED post-run (never fabricated)")
    print(f"  estimated Haiku calls (upper bound): {pf['calls']}")
    print(f"  estimated tokens: ~{pf['est_in']} in / ~{pf['est_out']} out")
    print(f"  estimated cost (list-price, NOT the billed amount): ${pf['est_cost_usd']:.2f}")
    print("=" * 72)
    if not confirm:
        print("\nNOT spending. Re-run with --confirm to execute the networked experiment.")
        return None

    gen = provider.chat_claude_cli  # frontier (Haiku), measured tokens + cost
    mem = _setup_store()
    try:
        a0 = run_a0(k, task=task_mod, gen=gen)

        a1_by_noise: dict[int, list] = {}
        for n in levels:
            a1_by_noise[n] = run_a1(
                k,
                task=task_mod,
                gen=gen,
                changelog_noise=_noise(n, deadend_key=task_mod.DEADEND_APPROACH),
            )

        _truncate_store()  # fresh store for the live gate arm
        a2 = run_a2(k, mem, task=task_mod, gen=gen, gating=True)

        _truncate_store()  # fresh store for the ablation arm
        a2_ablation = run_a2(k, mem, task=task_mod, gen=gen, gating=False)
    finally:
        mem.close()

    results = {
        "A0": (a0, compute_metrics(a0)),
        "A2": (a2, compute_metrics(a2)),
        "A2_ablation": (a2_ablation, compute_metrics(a2_ablation)),
    }
    for n in levels:
        results[f"A1_noise{n}"] = (a1_by_noise[n], compute_metrics(a1_by_noise[n]))

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    report = _render_experiment_report(task_mod, results, k, levels, run_id)
    path = _write_experiment(results, report, run_id)
    return results, path


def _render_experiment_report(task_mod, results: dict, k: int, levels: list[int],
                              run_id: str) -> str:
    a0m = results["A0"][1]
    a2m = results["A2"][1]
    abm = results["A2_ablation"][1]
    arms = ["A0"] + [f"A1_noise{n}" for n in levels] + ["A2", "A2_ablation"]
    keys = [
        ("dead_end_reattempt_rate", "dead-end re-attempt rate (memory-conditioned)"),
        ("raw_dead_end_rate", "raw dead-end rate"),
        ("self_contradiction_rate", "self-contradiction rate"),
        ("n_sessions_with_prior_knowledge", "sessions with prior knowledge"),
        ("total_generations", "iterations (generations)"),
        ("total_tokens", "tokens (measured)"),
        ("final_correctness_passed_any", "final correctness (passed any)"),
        ("gate_rejections", "gate rejections"),
    ]
    lines = [
        "# Gating harness — Phase 2 TEMPS 3 — EXPERIMENT (multi-session re-attempt)",
        "",
        f"- run_id: `{run_id}`",
        f"- task: `{task_mod.TASK_ID}` (reference-oracle ground truth, no LLM judge)",
        f"- K sessions per arm: {k}  ·  context-wiped between sessions  ·  model: Haiku 4.5 (OAuth CLI)",
        "- tokens + cost MEASURED from the CLI response, never fabricated",
        "",
        "## Metrics",
        "",
        "| metric | " + " | ".join(arms) + " |",
        "|" + "---|" * (len(arms) + 1),
    ]
    for kkey, label in keys:
        cells = [_fmt(results[a][1].get(kkey)) for a in arms]
        lines.append(f"| {label} | " + " | ".join(cells) + " |")

    lines += [
        "",
        "## Discriminant curve — A1 re-attempt vs CHANGELOG noise length",
        "",
        "| CHANGELOG noise length | A1 dead-end re-attempt (memory-conditioned) |",
        "|---|---|",
    ]
    for n in levels:
        lines.append(
            f"| {n} | {_fmt(results[f'A1_noise{n}'][1].get('dead_end_reattempt_rate'))} |"
        )
    lines += [
        f"| A2 (gate, reference) | {_fmt(a2m.get('dead_end_reattempt_rate'))} |",
        f"| A2 ablation (gate off) | {_fmt(abm.get('dead_end_reattempt_rate'))} |",
        "",
        "Hypothesis: A1 rises with noise length (passive recall loses the needle); A2 stays flat",
        "(O(1) keyed gate). If A1 holds flat even when long, the CHANGELOG suffices -> PIVOT.",
        "",
        "## Verdict scaffold (fill from the numbers above)",
        "",
        "- **A2 (tag-exact upper bound) <= best A1** -> PIVOT immediately (an enforced gate "
        "cannot beat an advisory CHANGELOG even at the upper bound; do not touch the lifecycle).",
        "- **A2 >> best A1 AND ablation erases the gain** -> floor crossed, NOT validated -> "
        "Stage 3b (real variant matching / deprecate-contradict via db.py:171).",
        "",
        f"- A0 raw dead-end rate: {_fmt(a0m.get('raw_dead_end_rate'))} "
        "(if ~0, the frontier never enters the dead-end -> the phenomenon does not exist here).",
        f"- A2 gate rejections fired: {a2m.get('gate_rejections')}  ·  "
        f"A2-ablation gate rejections: {abm.get('gate_rejections')} (must be 0).",
        "",
    ]
    return "\n".join(lines)


def _write_experiment(results: dict, report: str, run_id: str) -> Path:
    out = RESULTS_DIR / f"experiment_{run_id}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text(report)
    raw = {
        a: {"records": [r.to_dict() for r in recs], "metrics": m}
        for a, (recs, m) in results.items()
    }
    (out / "records.json").write_text(json.dumps(raw, indent=2, default=str))
    return out / "report.md"


# --------------------------------------------------------------------------- #
# Entry
# --------------------------------------------------------------------------- #


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="run the 1-task smoke (local Ollama)")
    parser.add_argument(
        "--experiment", action="store_true",
        help="run the TEMPS-3 multi-session re-attempt experiment (Haiku; needs --confirm to spend)",
    )
    parser.add_argument("--full", action="store_true", help="NOT implemented (legacy refusal)")
    parser.add_argument("--sessions", type=int, default=2, help="smoke sessions per arm")
    parser.add_argument("--task", default="balanced_brackets", help="task module name")
    parser.add_argument(
        "-k", "--k", type=int, default=12, help="experiment sessions per arm (10-15 recommended)"
    )
    parser.add_argument(
        "--noise-levels", type=int, nargs="+", default=None,
        help="CHANGELOG noise lengths for the A1 discriminant sweep (default 0 5 20 50)",
    )
    parser.add_argument(
        "--confirm", action="store_true",
        help="actually spend: execute the networked experiment after the preflight",
    )
    args = parser.parse_args()

    if args.full:
        raise SystemExit(
            "full run not implemented: it needs a frontier model (Haiku min) + many "
            "tasks. Use --experiment (TEMPS 3). This legacy flag stays refused by design."
        )

    if args.experiment:
        out = run_experiment(
            task_name=args.task, k=args.k, noise_levels=args.noise_levels, confirm=args.confirm
        )
        if out is None:
            return  # preflight-only (no --confirm) — spent nothing
        _results, path = out
        print(f"\nEXPERIMENT complete — report: {path}")
        print("STOP — review the table + curve before any Stage 3b edit (db.py:171).")
        return

    # default: smoke (local model, byte-stable on balanced_brackets)
    t0 = time.time()
    task_mod = _resolve_task(args.task)
    results, path = run_smoke(sessions=args.sessions, task=task_mod)
    dt = time.time() - t0
    print(f"\nSMOKE complete in {dt:.1f}s — report: {path}")
    for arm in ("A0", "A1", "A2"):
        m = results[arm][1]
        print(
            f"  {arm}: reattempt={m['dead_end_reattempt_rate']} "
            f"raw_deadend={m['raw_dead_end_rate']} "
            f"contradiction={m['self_contradiction_rate']} "
            f"gen={m['total_generations']} tok={m['total_tokens']} "
            f"pass_any={m['final_correctness_passed_any']} "
            f"gate_rejects={m['gate_rejections']}"
        )
    print("\nSTOP — smoke only. Do not run the full eval here (needs Haiku min).")


if __name__ == "__main__":
    main()
