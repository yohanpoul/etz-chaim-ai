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


def run_smoke(sessions: int = 2) -> tuple[dict, Path]:
    resolved = provider.resolve_local()  # header transparency + config-driven proof
    mem = _setup_store()
    try:
        a0 = run_a0(sessions)
        a1 = run_a1(sessions)
        a2 = run_a2(sessions, mem)
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="run the 1-task smoke")
    parser.add_argument("--full", action="store_true", help="NOT implemented")
    parser.add_argument("--sessions", type=int, default=2)
    args = parser.parse_args()

    if args.full:
        raise SystemExit(
            "full run not implemented: it needs a frontier model (Haiku min) + many "
            "tasks. This module is smoke-only by design (see docstring)."
        )

    t0 = time.time()
    results, path = run_smoke(sessions=args.sessions)
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
