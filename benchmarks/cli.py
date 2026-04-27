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
    """Estimate budget for the OAuth Max bench (3 arms × 4 benches × 100)."""
    print("Plan v2 OAuth Max — bench Claude+EtzChaim vs Claude raw\n")

    bench_subset = 100  # par bench
    n_benches = 4  # truthfulqa, harmbench, xstest, reasoning_hard
    prompts_per_arm = bench_subset * n_benches  # 400

    arm_multipliers = {
        "raw_cli": 1.0,
        "cot_cli": 1.0,
        "etz_yosher": 2.0,  # avg 2 internal Claude CLI calls (Hishtalshelut)
    }

    # Cost approximation : ~$0.04/call avec cache partiel (Opus 4.7 OAuth Max)
    cost_per_call_estimate = 0.04

    print(f"Subset: {bench_subset}/bench × {n_benches} benches = {prompts_per_arm} prompts/arm\n")

    total_calls = 0
    total_cost = 0.0
    for arm, mult in arm_multipliers.items():
        n_calls = int(prompts_per_arm * mult)
        cost = n_calls * cost_per_call_estimate
        total_calls += n_calls
        total_cost += cost
        print(f"  {arm:15s} {n_calls:5d} calls  ~${cost:6.2f}")

    # Ablation : 50 prompts × 3 configs Etz off-modules × 2 calls/prompt = 300 calls
    ablation_calls = 50 * 3 * 2
    ablation_cost = ablation_calls * cost_per_call_estimate
    print(f"  {'ablation':15s} {ablation_calls:5d} calls  ~${ablation_cost:6.2f}")

    print(f"\n  TOTAL                  {total_calls + ablation_calls:5d} calls  ~${total_cost + ablation_cost:6.2f}")
    print(f"  Judging heuristic (CPU local, gratuit)            $0")
    print(f"  Grand total estimé                                 ~${total_cost + ablation_cost:6.2f}")
    print()
    print("Note: forfait Claude Max absorbe une partie (cost_usd dans CLI output est indicatif).")
    return 0


def cmd_cli_test(args: argparse.Namespace) -> int:
    """Smoke test : 1 prompt direct via Claude CLI subprocess."""
    from benchmarks.claude_cli import ClaudeCLIInvoker

    print("Testing Claude CLI subprocess pipeline...")
    invoker = ClaudeCLIInvoker()
    result = invoker.invoke(
        prompt=args.prompt,
        system_prompt="Reply briefly.",
        timeout=60,
    )
    print(f"\n  success    : {result.success}")
    print(f"  text       : {result.text!r}")
    print(f"  duration   : {result.duration_ms}ms")
    print(f"  cost_usd   : ${result.cost_usd:.4f}")
    print(f"  tokens     : input={result.usage_input} output={result.usage_output}")
    print(f"  cache      : creation={result.cache_creation_tokens} read={result.cache_read_tokens}")
    print(f"  stop_reason: {result.stop_reason}")
    if result.error:
        print(f"  error      : {result.error}")
    return 0 if result.success else 1


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

    p_clitest = sub.add_parser("cli-test", help="Smoke test Claude CLI direct")
    p_clitest.add_argument("prompt", nargs="?", default="Say only 'pong'.",
                           help="Prompt to test (default: 'Say only pong.')")

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
        "cli-test": cmd_cli_test,
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
