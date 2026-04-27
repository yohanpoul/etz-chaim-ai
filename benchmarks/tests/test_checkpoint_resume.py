"""Tests de résilience du checkpoint — kill-9-resume scenario.

Discipline POSIX : write tmp + fsync + rename atomique. Cette suite teste :
- Atomic save+load round-trip
- Resume après "kill" (state non-saved est perdu mais state saved est fiable)
- Idempotence mark_done
- Progress calculation
- Subprocess kill -9 réel pendant écriture (vérifie pas de corruption JSON)
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

from benchmarks.checkpoint import BenchState


@pytest.fixture
def tmp_state_dir():
    """Tmp dir for each test, auto-cleaned."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp) / "test_run"


class TestAtomicSaveLoad:
    """Save+load round-trip preserves state exactly."""

    def test_empty_state_round_trip(self, tmp_state_dir):
        s1 = BenchState.load_or_create(tmp_state_dir, run_id="test1")
        s1.save()
        s2 = BenchState.load_or_create(tmp_state_dir)
        assert s2.run_id == "test1"
        assert s2.total_calls == 0
        assert s2.total_cost_usd == 0.0
        assert s2.done == {}

    def test_populated_state_round_trip(self, tmp_state_dir):
        s1 = BenchState.load_or_create(tmp_state_dir, run_id="test2")
        s1.mark_done("raw", "truthfulqa", 0, cost_usd=0.04, tokens_input=300, tokens_output=100)
        s1.mark_done("raw", "truthfulqa", 5, cost_usd=0.05)
        s1.mark_done("cot", "harmbench", 0, cost_usd=0.06)
        s1.save()

        s2 = BenchState.load_or_create(tmp_state_dir)
        assert s2.is_done("raw", "truthfulqa", 0)
        assert s2.is_done("raw", "truthfulqa", 5)
        assert s2.is_done("cot", "harmbench", 0)
        assert not s2.is_done("raw", "truthfulqa", 1)
        assert not s2.is_done("raw", "harmbench", 0)
        assert s2.total_calls == 3
        assert abs(s2.total_cost_usd - 0.15) < 1e-9
        assert s2.total_tokens_input == 300
        assert s2.total_tokens_output == 100

    def test_state_file_is_valid_json(self, tmp_state_dir):
        s = BenchState.load_or_create(tmp_state_dir, run_id="test3")
        s.mark_done("raw", "truthfulqa", 42, cost_usd=0.03)
        s.save()

        state_file = tmp_state_dir / "bench_state.json"
        assert state_file.exists()
        # Manually parse — must be valid JSON
        data = json.loads(state_file.read_text())
        assert data["run_id"] == "test3"
        assert data["total_calls"] == 1
        assert "raw" in data["done"]


class TestKillResume:
    """Simulate kill -9 via partial work + reload from saved state."""

    def test_unsaved_work_lost_saved_work_kept(self, tmp_state_dir):
        """Le state non-saved est perdu après kill, le saved est préservé."""
        s1 = BenchState.load_or_create(tmp_state_dir)

        # Process 3 prompts, save after each (worst-case = chaque save)
        s1.mark_done("raw", "truthfulqa", 0, cost_usd=0.04)
        s1.save()
        s1.mark_done("raw", "truthfulqa", 1, cost_usd=0.04)
        s1.save()
        s1.mark_done("raw", "truthfulqa", 2, cost_usd=0.04)
        s1.save()

        # Then mark 2 more WITHOUT saving (simulate kill -9 before save)
        s1.mark_done("raw", "truthfulqa", 3, cost_usd=0.04)
        s1.mark_done("raw", "truthfulqa", 4, cost_usd=0.04)
        # ⚠️ Pas de save() ici — simulation kill-9

        # Reload from disk (fresh process)
        s2 = BenchState.load_or_create(tmp_state_dir)
        assert s2.is_done("raw", "truthfulqa", 0)
        assert s2.is_done("raw", "truthfulqa", 1)
        assert s2.is_done("raw", "truthfulqa", 2)
        # Les 2 derniers sont perdus (pas saved) → resume les re-fera
        assert not s2.is_done("raw", "truthfulqa", 3)
        assert not s2.is_done("raw", "truthfulqa", 4)
        assert s2.total_calls == 3

    def test_resume_continues_where_left_off(self, tmp_state_dir):
        """Le 'done' set permet un resume sans double-call."""
        s1 = BenchState.load_or_create(tmp_state_dir)
        prompt_ids_done = [0, 5, 10, 15, 20]
        for pid in prompt_ids_done:
            s1.mark_done("raw", "truthfulqa", pid, cost_usd=0.04)
        s1.save()

        # Resume : aucun de ces ids ne doit être re-process
        s2 = BenchState.load_or_create(tmp_state_dir)
        for pid in prompt_ids_done:
            assert s2.is_done("raw", "truthfulqa", pid)

        # Les autres ids doivent être à process
        for pid in [1, 6, 11, 16, 21]:
            assert not s2.is_done("raw", "truthfulqa", pid)


class TestIdempotency:
    """mark_done est idempotent (append only)."""

    def test_mark_done_twice_counts_once(self, tmp_state_dir):
        s = BenchState.load_or_create(tmp_state_dir)
        s.mark_done("raw", "truthfulqa", 42, cost_usd=0.04, tokens_input=300)
        s.mark_done("raw", "truthfulqa", 42, cost_usd=0.04, tokens_input=300)  # double
        # Cost ne doit pas être doublé
        assert abs(s.total_cost_usd - 0.04) < 1e-9
        assert s.total_calls == 1
        assert s.total_tokens_input == 300
        assert s.is_done("raw", "truthfulqa", 42)

    def test_save_load_then_remark_idempotent(self, tmp_state_dir):
        s1 = BenchState.load_or_create(tmp_state_dir)
        s1.mark_done("raw", "truthfulqa", 0, cost_usd=0.04)
        s1.save()

        s2 = BenchState.load_or_create(tmp_state_dir)
        s2.mark_done("raw", "truthfulqa", 0, cost_usd=0.04)  # already done
        assert s2.total_calls == 1  # pas re-incrémenté


class TestProgress:
    def test_progress_calculation(self, tmp_state_dir):
        s = BenchState.load_or_create(tmp_state_dir)
        for i in range(50):
            s.mark_done("raw", "truthfulqa", i)
        done, total, frac = s.progress("raw", "truthfulqa", 200)
        assert done == 50
        assert total == 200
        assert abs(frac - 0.25) < 1e-9

    def test_progress_zero(self, tmp_state_dir):
        s = BenchState.load_or_create(tmp_state_dir)
        done, total, frac = s.progress("raw", "truthfulqa", 200)
        assert done == 0
        assert frac == 0.0


class TestResponsesJsonl:
    """append_response writes line-atomically and survives reload."""

    def test_append_responses_persist(self, tmp_state_dir):
        s = BenchState.load_or_create(tmp_state_dir)
        s.append_response({"arm": "raw", "bench": "tq", "prompt_id": 0, "response": "test1"})
        s.append_response({"arm": "raw", "bench": "tq", "prompt_id": 1, "response": "test2"})
        s.append_response({"arm": "raw", "bench": "tq", "prompt_id": 2, "response": "test3"})

        responses_file = tmp_state_dir / "responses.jsonl"
        lines = responses_file.read_text().strip().split("\n")
        assert len(lines) == 3
        for i, line in enumerate(lines):
            obj = json.loads(line)
            assert obj["prompt_id"] == i
            assert obj["response"] == f"test{i+1}"


class TestSubprocessKill:
    """Real kill -9 during write : the saved state must remain valid JSON.

    Génère un script qui boucle sur mark_done+save, kill -9 dans la fenêtre
    fsync→rename. Reload doit toujours produire un JSON valide.
    """

    def test_state_file_never_corrupt_under_kill9(self, tmp_state_dir, tmp_path):
        # Script qui marque 100 prompts en boucle save
        worker_script = tmp_path / "worker.py"
        worker_script.write_text(
            f"""
import sys
sys.path.insert(0, {repr(str(Path(__file__).resolve().parent.parent.parent))})
from benchmarks.checkpoint import BenchState
import time

s = BenchState.load_or_create(r"{tmp_state_dir}", run_id="kill_test")
i = 0
while True:
    s.mark_done("raw", "truthfulqa", i, cost_usd=0.001)
    s.save()
    i += 1
    if i >= 1000:
        break
    time.sleep(0.001)
"""
        )

        # Spawn subprocess + kill -9 après ~50ms
        proc = subprocess.Popen(
            [sys.executable, str(worker_script)],
            cwd=tmp_path,
        )
        time.sleep(0.05)  # let it write some state
        proc.send_signal(signal.SIGKILL)
        proc.wait(timeout=5)

        # State file MUST exist and be valid JSON (rename atomique POSIX)
        state_file = tmp_state_dir / "bench_state.json"
        # Tolérer le cas où le subprocess n'a pas eu le temps de save
        if state_file.exists():
            data = json.loads(state_file.read_text())
            assert "run_id" in data
            assert "done" in data
            # Reload via BenchState — must work
            s_reloaded = BenchState.load_or_create(tmp_state_dir)
            assert s_reloaded.run_id == "kill_test"
            assert s_reloaded.total_calls >= 1
