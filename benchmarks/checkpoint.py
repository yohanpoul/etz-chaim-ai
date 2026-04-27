"""Atomic checkpoint state — kill-9 resilient bench progress tracking.

Discipline POSIX : write tmp file → fsync → rename. Renaming sur le même
filesystem est atomique (POSIX). Kill-9 entre les étapes laisse soit l'ancien
état (rien perdu), soit le nouveau état (rien perdu) — jamais corrompu.

Usage :
    state = BenchState.load_or_create("results/runs/2026-04-27_run1")
    if not state.is_done("raw", "truthfulqa", 42):
        # ... run inference ...
        state.mark_done("raw", "truthfulqa", 42, cost_usd=0.04)
        state.save()  # atomic
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class BenchState:
    """État atomique d'une session benchmark.

    Structure plate pour serialisation JSON facile, lookup O(1) sur done set.
    """

    run_id: str
    state_dir: Path = field(default_factory=Path)
    # done[arm][bench] = set of prompt_ids
    done: dict[str, dict[str, set[int]]] = field(default_factory=dict)
    total_cost_usd: float = 0.0
    total_calls: int = 0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    started_at: float = field(default_factory=time.time)
    last_updated_at: float = field(default_factory=time.time)

    @classmethod
    def load_or_create(cls, state_dir: Path | str, run_id: str | None = None) -> BenchState:
        """Charger un état existant ou créer un nouveau."""
        state_dir = Path(state_dir)
        state_dir.mkdir(parents=True, exist_ok=True)

        state_file = state_dir / "bench_state.json"
        if state_file.exists():
            return cls._load(state_file)

        rid = run_id or time.strftime("%Y-%m-%d_%H%M%S")
        state = cls(run_id=rid, state_dir=state_dir)
        state.save()
        return state

    @classmethod
    def _load(cls, state_file: Path) -> BenchState:
        """Internal load from JSON, converting lists back to sets."""
        data = json.loads(state_file.read_text())
        done_raw = data.get("done", {})
        done: dict[str, dict[str, set[int]]] = {}
        for arm, by_bench in done_raw.items():
            done[arm] = {bench: set(ids) for bench, ids in by_bench.items()}

        return cls(
            run_id=data["run_id"],
            state_dir=state_file.parent,
            done=done,
            total_cost_usd=data.get("total_cost_usd", 0.0),
            total_calls=data.get("total_calls", 0),
            total_tokens_input=data.get("total_tokens_input", 0),
            total_tokens_output=data.get("total_tokens_output", 0),
            started_at=data.get("started_at", time.time()),
            last_updated_at=data.get("last_updated_at", time.time()),
        )

    def save(self) -> None:
        """Atomic write : tmp file → fsync → rename."""
        self.last_updated_at = time.time()
        state_file = self.state_dir / "bench_state.json"
        tmp_file = state_file.with_suffix(".json.tmp")

        # Convert sets to sorted lists for JSON
        done_serializable = {
            arm: {bench: sorted(ids) for bench, ids in by_bench.items()}
            for arm, by_bench in self.done.items()
        }

        payload = {
            "run_id": self.run_id,
            "done": done_serializable,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "total_calls": self.total_calls,
            "total_tokens_input": self.total_tokens_input,
            "total_tokens_output": self.total_tokens_output,
            "started_at": self.started_at,
            "last_updated_at": self.last_updated_at,
        }

        # Write tmp + fsync + atomic rename
        with tmp_file.open("w") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        tmp_file.replace(state_file)

    def is_done(self, arm: str, bench: str, prompt_id: int) -> bool:
        """O(1) lookup : prompt déjà traité ?"""
        return prompt_id in self.done.get(arm, {}).get(bench, set())

    def mark_done(
        self,
        arm: str,
        bench: str,
        prompt_id: int,
        cost_usd: float = 0.0,
        tokens_input: int = 0,
        tokens_output: int = 0,
    ) -> None:
        """Marquer un prompt comme traité avec compteurs cost/tokens.

        Note : l'appelant doit `save()` après pour persister.
        On laisse le save explicit pour permettre des batches.
        """
        if arm not in self.done:
            self.done[arm] = {}
        if bench not in self.done[arm]:
            self.done[arm][bench] = set()
        if prompt_id in self.done[arm][bench]:
            return  # idempotent
        self.done[arm][bench].add(prompt_id)
        self.total_cost_usd += cost_usd
        self.total_calls += 1
        self.total_tokens_input += tokens_input
        self.total_tokens_output += tokens_output

    def progress(self, arm: str, bench: str, total: int) -> tuple[int, int, float]:
        """Retourner (done_count, total, fraction) pour un (arm, bench)."""
        done = len(self.done.get(arm, {}).get(bench, set()))
        frac = done / total if total > 0 else 0.0
        return done, total, frac

    def summary(self) -> dict[str, Any]:
        """Résumé concis pour affichage."""
        per_arm = {
            arm: {bench: len(ids) for bench, ids in by_bench.items()}
            for arm, by_bench in self.done.items()
        }
        return {
            "run_id": self.run_id,
            "total_cost_usd": round(self.total_cost_usd, 4),
            "total_calls": self.total_calls,
            "total_tokens": {
                "input": self.total_tokens_input,
                "output": self.total_tokens_output,
            },
            "elapsed_s": round(time.time() - self.started_at, 1),
            "per_arm_per_bench": per_arm,
        }

    def append_response(self, record: dict[str, Any]) -> None:
        """Append a response record to responses.jsonl atomically.

        Args:
            record: dict avec arm, bench, prompt_id, response, tokens, latency, etc.
        """
        responses_file = self.state_dir / "responses.jsonl"
        line = json.dumps(record, ensure_ascii=False)
        # Append atomique sur POSIX (write < PIPE_BUF est atomique)
        with responses_file.open("a") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())


if __name__ == "__main__":
    # Smoke test
    import tempfile
    import shutil

    tmp = Path(tempfile.mkdtemp())
    try:
        state = BenchState.load_or_create(tmp / "test_run")
        assert not state.is_done("raw", "truthfulqa", 0)
        state.mark_done("raw", "truthfulqa", 0, cost_usd=0.04, tokens_input=300, tokens_output=100)
        state.mark_done("raw", "truthfulqa", 1, cost_usd=0.05)
        state.save()

        # Reload and verify
        state2 = BenchState.load_or_create(tmp / "test_run")
        assert state2.is_done("raw", "truthfulqa", 0)
        assert state2.is_done("raw", "truthfulqa", 1)
        assert not state2.is_done("raw", "truthfulqa", 2)
        assert abs(state2.total_cost_usd - 0.09) < 1e-9
        assert state2.total_tokens_input == 300

        state2.append_response({
            "arm": "raw", "bench": "truthfulqa", "prompt_id": 0,
            "response": "test", "tokens": {"input": 300, "output": 100},
        })

        responses_file = tmp / "test_run" / "responses.jsonl"
        assert responses_file.exists()
        line = responses_file.read_text().strip()
        assert json.loads(line)["response"] == "test"

        print("PASS — checkpoint atomic save+load+append working")
    finally:
        shutil.rmtree(tmp)
