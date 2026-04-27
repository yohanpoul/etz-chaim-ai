"""CLI entry point — python -m benchmarks.cli <command>.

Commands :
    list                          — show available benches and arms
    sizes                         — show prompt counts per bench
    estimate                      — estimate budget for a (bench, arm) pair
    run <bench> <arm>             — run a specific (bench, arm)
    all                           — run all combinations (5 arms × 5 benches)
    stats <run_dir>               — show summary of an existing run
    cache-stats                   — show cache size and hit rate

Examples :
    python -m benchmarks.cli list
    python -m benchmarks.cli run truthfulqa raw --limit 200 --budget 30
    python -m benchmarks.cli all --limit 200 --budget 400
    python -m benchmarks.cli stats results/runs/2026-04-27_run1
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from benchmarks.arms import ALL_ARMS
from benchmarks.cache import LLMCache
from benchmarks.checkpoint import BenchState
from benchmarks.datasets.loader import bench_sizes
from benchmarks.runner import BenchmarkRunner
from benchmarks.token_tracker import estimate_cost_for_volume


_ALL_BENCHES = ["truthfulqa", "harmbench", "xstest", "reasoning_hard", "alpacaeval"]

# Default paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RUN_ROOT = PROJECT_ROOT / "benchmarks" / "results" / "runs"
DEFAULT_CACHE_DIR = PROJECT_ROOT / "benchmarks" / "results" / "cache"


def cmd_list(args: argparse.Namespace) -> int:
    """List available benches and arms."""
    print("Available benches :")
    for b in _ALL_BENCHES:
        print(f"  - {b}")
    print("\nAvailable arms :")
    for a in ALL_ARMS:
        print(f"  - {a}")
    return 0


def cmd_sizes(args: argparse.Namespace) -> int:
    """Show prompt counts per bench."""
    sizes = bench_sizes()
    total = sum(sizes.values())
    print("Bench sizes :")
    for b, n in sizes.items():
        print(f"  {b:18s} {n:4d} prompts")
    print(f"\n  TOTAL              {total:4d} prompts")
    return 0


def cmd_estimate(args: argparse.Namespace) -> int:
    """Estimate budget for a (bench, arm) pair or full sweep."""
    sizes = bench_sizes()
    total_prompts = sum(sizes.values())

    # Per-arm internal call multipliers (estimation)
    arm_multipliers = {
        "raw": 1.0,
        "cot": 1.0,
        "self_consistency": 3.0,
        "etz_yosher": 2.0,    # avg 2 internal calls (Hishtalshelut)
        "etz_deterministic": 2.0,
    }

    # Average input/output tokens (calibrated avant Day 5)
    avg_input = 350
    avg_output = 300

    print(f"Estimating with avg_input={avg_input}, avg_output={avg_output} tokens\n")

    per_arm_cost = {}
    for arm, mult in arm_multipliers.items():
        n_calls = int(total_prompts * mult)
        cost = estimate_cost_for_volume(
            n_calls=n_calls,
            avg_input_tokens=avg_input,
            avg_output_tokens=avg_output,
            cache_hit_rate=0.0,  # conservative
        )
        per_arm_cost[arm] = cost
        print(f"  {arm:25s} {n_calls:6d} calls  ~${cost:7.2f}")

    total = sum(per_arm_cost.values())
    print(f"\n  TOTAL (5 arms full sweep)        ~${total:7.2f}")
    print(f"  + ablation (~700 Etz runs)       ~$80")
    print(f"  + judge (GPT-4o-mini negligible) ~$0.50")
    print(f"\n  Grand total                      ~${total + 80 + 0.5:7.2f}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Run a specific (bench, arm) pair."""
    run_dir = Path(args.run_dir) if args.run_dir else DEFAULT_RUN_ROOT / args.run_id
    cache_dir = Path(args.cache_dir) if args.cache_dir else DEFAULT_CACHE_DIR

    runner = BenchmarkRunner(
        run_dir=run_dir,
        cache_dir=cache_dir,
        kill_daemon=not args.no_kill_daemon,
    )

    summary = runner.run(
        bench=args.bench,
        arm=args.arm,
        limit=args.limit,
        dollar_budget=args.budget,
        verbose=not args.quiet,
    )

    print(f"\n=== Run summary ===")
    for k, v in summary.__dict__.items():
        print(f"  {k:25s} {v}")

    return 0 if not summary.interrupted else 130


def cmd_all(args: argparse.Namespace) -> int:
    """Run all 5 arms × 5 benches with checkpoint resume."""
    run_dir = Path(args.run_dir) if args.run_dir else DEFAULT_RUN_ROOT / args.run_id
    cache_dir = Path(args.cache_dir) if args.cache_dir else DEFAULT_CACHE_DIR

    runner = BenchmarkRunner(
        run_dir=run_dir,
        cache_dir=cache_dir,
        kill_daemon=not args.no_kill_daemon,
    )

    # Order : commencer par les fast arms (raw < cot < SC < Etz)
    ordered_arms = ["raw", "cot", "self_consistency", "etz_yosher", "etz_deterministic"]
    if args.skip_etz:
        ordered_arms = [a for a in ordered_arms if not a.startswith("etz")]

    summaries = []
    for arm in ordered_arms:
        for bench in _ALL_BENCHES:
            if args.bench and bench != args.bench:
                continue
            print(f"\n{'='*60}\n  Run {arm} × {bench}\n{'='*60}")
            try:
                summary = runner.run(
                    bench=bench,
                    arm=arm,
                    limit=args.limit,
                    dollar_budget=args.budget,
                    verbose=not args.quiet,
                )
                summaries.append(summary)
                if summary.interrupted:
                    print("Interrupted, stopping all-runs", file=sys.stderr)
                    return 130
            except Exception as e:
                print(f"FAIL {arm} × {bench}: {type(e).__name__}: {e}",
                      file=sys.stderr)

    print(f"\n=== All runs completed ===")
    print(f"  total_cost: ${runner.state.total_cost_usd:.2f}")
    print(f"  total_calls: {runner.state.total_calls}")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Show summary of an existing run."""
    state = BenchState.load_or_create(args.run_dir)
    summary = state.summary()
    print(json.dumps(summary, indent=2, default=str))
    return 0


def cmd_cache_stats(args: argparse.Namespace) -> int:
    """Show cache size and hit rate."""
    cache_dir = Path(args.cache_dir) if args.cache_dir else DEFAULT_CACHE_DIR
    if not cache_dir.exists():
        print(f"Cache dir does not exist: {cache_dir}", file=sys.stderr)
        return 1
    cache = LLMCache(cache_dir)
    print(f"Cache dir: {cache_dir}")
    print(f"  entries: {cache.count()}")
    print(f"  size: {cache.size_bytes()} bytes ({cache.size_bytes() / 1024 / 1024:.1f} MB)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="benchmarks.cli",
        description="Benchmark Claude+EtzChaim vs Claude raw — Opus 4.7",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List available benches and arms")
    sub.add_parser("sizes", help="Show prompt counts per bench")
    sub.add_parser("estimate", help="Estimate API budget")

    p_run = sub.add_parser("run", help="Run a specific (bench, arm)")
    p_run.add_argument("bench", choices=_ALL_BENCHES)
    p_run.add_argument("arm", choices=ALL_ARMS)
    p_run.add_argument("--limit", type=int, default=None)
    p_run.add_argument("--budget", type=float, default=500.0,
                       help="Hard cap USD (default 500)")
    p_run.add_argument("--run-id", default="default")
    p_run.add_argument("--run-dir", default=None)
    p_run.add_argument("--cache-dir", default=None)
    p_run.add_argument("--no-kill-daemon", action="store_true")
    p_run.add_argument("--quiet", action="store_true")

    p_all = sub.add_parser("all", help="Run all combos with resume")
    p_all.add_argument("--limit", type=int, default=None)
    p_all.add_argument("--budget", type=float, default=500.0)
    p_all.add_argument("--run-id", default="default")
    p_all.add_argument("--run-dir", default=None)
    p_all.add_argument("--cache-dir", default=None)
    p_all.add_argument("--no-kill-daemon", action="store_true")
    p_all.add_argument("--quiet", action="store_true")
    p_all.add_argument("--bench", default=None,
                       help="Run all arms only on this bench")
    p_all.add_argument("--skip-etz", action="store_true",
                       help="Skip Etz arms (raw + cot + SC only)")

    p_stats = sub.add_parser("stats", help="Show run summary")
    p_stats.add_argument("run_dir")

    p_cache = sub.add_parser("cache-stats", help="Cache size + hit rate")
    p_cache.add_argument("--cache-dir", default=None)

    args = parser.parse_args()

    handlers = {
        "list": cmd_list,
        "sizes": cmd_sizes,
        "estimate": cmd_estimate,
        "run": cmd_run,
        "all": cmd_all,
        "stats": cmd_stats,
        "cache-stats": cmd_cache_stats,
    }

    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        return 1
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
