"""Benchmark runner — résilient, kill-9-resume, daemon-aware, budget-capped.

Orchestre :
- Charge prompts du bench (avec resume via checkpoint state)
- Pour chaque prompt non-done : run arm + cache + per-prompt atomic checkpoint
- Retry+backoff sur API errors
- Hard budget cap (--dollar-budget)
- Daemon Hitbonenut kill + atexit hook (évite consommation Opus parallèle)
- SIGINT/SIGTERM handler → flush + clean exit (resume restart où on était)

Usage :
    runner = BenchmarkRunner(
        run_dir="results/runs/2026-04-27",
        cache_dir="results/cache",
    )
    runner.run(bench="truthfulqa", arm="raw", limit=200, dollar_budget=50)
"""

from __future__ import annotations

import atexit
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from benchmarks.arms import ALL_ARMS, ArmResult, make_arm
from benchmarks.cache import LLMCache
from benchmarks.checkpoint import BenchState
from benchmarks.datasets.loader import Prompt, load_bench


# ---------------------------------------------------------------------------
# Daemon kill
# ---------------------------------------------------------------------------

_DAEMON_KILLED = False


def kill_daemon_hitbonenut() -> bool:
    """Kill daemon.py si tourne. Retourne True si killed.

    Évite consommation parallèle Opus pendant bench (Hitbonenut tourne en
    continu et appelle Opus toutes les ~5min, ce qui ferait diverger les
    runs).
    """
    global _DAEMON_KILLED
    if _DAEMON_KILLED:
        return False

    try:
        result = subprocess.run(
            ["pgrep", "-f", "daemon.py"],
            capture_output=True,
            text=True,
            check=False,
        )
        pids = [int(p) for p in result.stdout.strip().split("\n") if p.strip()]
        if not pids:
            print("  daemon.py not running", file=sys.stderr)
            _DAEMON_KILLED = True
            return False

        for pid in pids:
            os.kill(pid, signal.SIGTERM)
            print(f"  killed daemon.py PID={pid}", file=sys.stderr)
        _DAEMON_KILLED = True
        return True
    except (FileNotFoundError, ProcessLookupError, ValueError) as e:
        print(f"  daemon kill warning: {e}", file=sys.stderr)
        return False


def _atexit_warning() -> None:
    """Atexit hook : warn si l'utilisateur veut relancer le daemon."""
    print(
        "\n[bench] Daemon Hitbonenut désactivé pendant le bench. "
        "Pour le redémarrer : python daemon.py start",
        file=sys.stderr,
    )


# ---------------------------------------------------------------------------
# Signal handling for clean SIGINT/SIGTERM
# ---------------------------------------------------------------------------

_INTERRUPTED = False


def _handle_signal(signum: int, frame: Any) -> None:
    """SIGINT/SIGTERM → flag pour exit clean après le current prompt."""
    global _INTERRUPTED
    _INTERRUPTED = True
    print(
        f"\n[bench] Signal {signum} reçu. "
        f"Finition du current prompt puis exit clean...",
        file=sys.stderr,
    )


def _install_signal_handlers() -> None:
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)


# ---------------------------------------------------------------------------
# Retry+backoff
# ---------------------------------------------------------------------------


_RETRY_DELAYS = [5, 10, 20]  # seconds


def with_retry(fn, *args, max_retries: int = 3, **kwargs) -> Any:
    """Run fn with exponential backoff on retriable errors."""
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_exc = e
            err_msg = str(e)
            # Retriable : rate limit, timeout, connection
            retriable = any(
                marker in err_msg.lower()
                for marker in (
                    "rate limit", "timeout", "connection", "overloaded",
                    "503", "529", "502", "500",
                )
            )
            if not retriable or attempt >= max_retries:
                raise
            delay = _RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)]
            print(
                f"  retry {attempt + 1}/{max_retries} after {delay}s "
                f"({type(e).__name__}: {err_msg[:80]})",
                file=sys.stderr,
            )
            time.sleep(delay)
    if last_exc:
        raise last_exc


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


@dataclass
class RunSummary:
    """Résumé d'une session run."""

    bench: str
    arm: str
    prompts_done: int
    prompts_skipped: int
    prompts_failed: int
    total_cost_usd: float
    total_calls: int
    elapsed_s: float
    interrupted: bool = False


class BenchmarkRunner:
    """Orchestrateur résilient bench × arm × prompts."""

    def __init__(
        self,
        run_dir: Path | str,
        cache_dir: Path | str,
        kill_daemon: bool = True,
    ):
        self.run_dir = Path(run_dir)
        self.cache_dir = Path(cache_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.state = BenchState.load_or_create(self.run_dir)
        self.cache = LLMCache(self.cache_dir)

        if kill_daemon:
            kill_daemon_hitbonenut()
            atexit.register(_atexit_warning)

        _install_signal_handlers()

    def run(
        self,
        bench: str,
        arm: str,
        limit: int | None = None,
        dollar_budget: float = 500.0,
        verbose: bool = True,
    ) -> RunSummary:
        """Run un (bench, arm) avec resume + cache + budget cap.

        Args:
            bench: nom du bench ('truthfulqa' | 'harmbench' | ...)
            arm: nom de l'arm ('raw' | 'cot' | 'self_consistency' | 'etz_*')
            limit: limit de prompts (default = all)
            dollar_budget: hard cap USD (abort si depasse)
            verbose: print progress

        Returns:
            RunSummary.
        """
        global _INTERRUPTED
        if arm not in ALL_ARMS:
            raise ValueError(f"Unknown arm: {arm}. Available: {ALL_ARMS}")

        prompts = load_bench(bench, limit=limit)
        total = len(prompts)

        # Budget pre-check : combien déjà dépensé ?
        if self.state.total_cost_usd > dollar_budget:
            raise RuntimeError(
                f"Budget already exceeded : ${self.state.total_cost_usd:.2f} "
                f"> cap ${dollar_budget:.2f}"
            )

        # Build arm
        arm_obj = make_arm(arm, cache=self.cache)

        if verbose:
            done_already, _, _ = self.state.progress(arm, bench, total)
            print(
                f"\n[bench] {arm} × {bench} : "
                f"{done_already}/{total} déjà fait, "
                f"budget actuel ${self.state.total_cost_usd:.2f}/{dollar_budget}",
                file=sys.stderr,
            )

        t_start = time.time()
        n_done = 0
        n_skipped = 0
        n_failed = 0

        for prompt in prompts:
            if _INTERRUPTED:
                if verbose:
                    print(f"\n[bench] interrupted after {n_done} prompts",
                          file=sys.stderr)
                break

            if self.state.is_done(arm, bench, prompt.id):
                n_skipped += 1
                continue

            # Budget check before each call
            if self.state.total_cost_usd >= dollar_budget:
                print(
                    f"\n[bench] BUDGET CAP REACHED : "
                    f"${self.state.total_cost_usd:.2f} >= ${dollar_budget:.2f}",
                    file=sys.stderr,
                )
                break

            # Run arm with retry
            try:
                result = with_retry(arm_obj.run, prompt.text)
            except Exception as e:
                n_failed += 1
                if verbose:
                    print(
                        f"  [{prompt.id}] FAILED: {type(e).__name__}: "
                        f"{str(e)[:120]}",
                        file=sys.stderr,
                    )
                # Continue with next prompt
                continue

            # Persist : append response + mark done + save state
            self.state.append_response({
                "arm": arm,
                "bench": bench,
                "prompt_id": prompt.id,
                "prompt_text": prompt.text,
                "metadata": prompt.metadata,
                "response": result.response,
                "cost_usd": result.cost_usd,
                "tokens_input": result.tokens_input,
                "tokens_output": result.tokens_output,
                "latency_ms": result.latency_ms,
                "n_internal_calls": result.n_internal_calls,
                "cache_hits": result.cache_hits,
                "arm_metadata": result.metadata,
                "success": result.success,
                "error": result.error,
                "ts": time.time(),
            })
            self.state.mark_done(
                arm, bench, prompt.id,
                cost_usd=result.cost_usd,
                tokens_input=result.tokens_input,
                tokens_output=result.tokens_output,
            )
            self.state.save()

            n_done += 1

            if verbose and (n_done % 10 == 0 or n_done == 1):
                done_total, total_t, frac = self.state.progress(arm, bench, total)
                print(
                    f"  [{n_done:4d}] {arm} × {bench} {done_total}/{total_t} "
                    f"({frac*100:.0f}%)  cost=${self.state.total_cost_usd:.2f}",
                    file=sys.stderr,
                )

        elapsed = time.time() - t_start

        return RunSummary(
            bench=bench,
            arm=arm,
            prompts_done=n_done,
            prompts_skipped=n_skipped,
            prompts_failed=n_failed,
            total_cost_usd=self.state.total_cost_usd,
            total_calls=self.state.total_calls,
            elapsed_s=round(elapsed, 1),
            interrupted=_INTERRUPTED,
        )

    def summary(self) -> dict[str, Any]:
        """Résumé global de l'état."""
        cache_stats = self.cache.stats()
        return {
            "state": self.state.summary(),
            "cache": cache_stats,
        }


if __name__ == "__main__":
    # Smoke test offline (skip api calls if ANTHROPIC_API_KEY absent)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "ANTHROPIC_API_KEY not set — skipping live run, only validating "
            "instantiation",
            file=sys.stderr,
        )
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            runner = BenchmarkRunner(
                run_dir=Path(tmp) / "run",
                cache_dir=Path(tmp) / "cache",
                kill_daemon=False,
            )
            print(f"Runner instantiated, state={runner.state.run_id}",
                  file=sys.stderr)
            print(f"Available arms: {ALL_ARMS}", file=sys.stderr)
            print("PASS — runner ready (live run requires API key)",
                  file=sys.stderr)
    else:
        # Mini live run : 2 prompts × raw arm
        import tempfile
        tmp_dir = Path(tempfile.mkdtemp())
        runner = BenchmarkRunner(
            run_dir=tmp_dir / "run",
            cache_dir=tmp_dir / "cache",
        )
        summary = runner.run(
            bench="truthfulqa", arm="raw", limit=2, dollar_budget=1.0,
        )
        print(f"Live smoke test PASS")
        print(json.dumps(summary.__dict__, indent=2, default=str))
