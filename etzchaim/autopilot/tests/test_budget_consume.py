"""Tests for autopilot budget tracker wiring + PR count sync.

Regression coverage for v0.2.30 fixes :
- `loop.run_one_cycle` extracts billable tokens from Claude CLI usage
  envelope (propagated via `RunResult.metadata` → `WorkerResult.metadata`)
  and calls `TokenBudget.consume(N)` so the monthly cap is enforceable.
- `loop.run_one_cycle` persists `_open_pr_count()` into
  `state.autopilot_pr_count_open` so the max-PRs guard reads live data.
"""

from __future__ import annotations

import json
import tempfile
from unittest.mock import MagicMock

import pytest

from etzchaim.autopilot.budget import TokenBudget
from etzchaim.autopilot.config import AutopilotConfig
from etzchaim.autopilot.runners.base import RunResult
from etzchaim.autopilot.runners.claude_skill import ClaudeSkillRunner
from etzchaim.autopilot.state import AutopilotState


@pytest.fixture(autouse=True)
def _isolate_state(monkeypatch):
    tmp = tempfile.mkdtemp()
    monkeypatch.setenv("ETZCHAIM_STATE_DIR", tmp)
    yield tmp


def test_budget_consume_increments_state():
    """Direct TokenBudget.consume() persists into state."""
    cfg = AutopilotConfig(budget_tokens_monthly=10_000)
    st = AutopilotState()
    budget = TokenBudget(cfg, st)
    assert st.autopilot_tokens_consumed_month == 0

    check = budget.consume(2500)
    assert check.consumed == 2500
    assert check.remaining == 7500

    reloaded = AutopilotState.load()
    assert reloaded.autopilot_tokens_consumed_month == 2500


def test_runner_metadata_propagates_tokens():
    """ClaudeSkillRunner extracts usage from JSON envelope into metadata."""
    fake_local = MagicMock()
    envelope = {
        "type": "result",
        "result": "done",
        "usage": {
            "input_tokens": 100,
            "output_tokens": 200,
            "cache_creation_input_tokens": 300,
            "cache_read_input_tokens": 50,
        },
        "total_cost_usd": 0.0123,
    }
    fake_local.dispatch.return_value = RunResult(
        exit_code=0,
        stdout=json.dumps(envelope),
        stderr="",
        duration_ms=500,
    )
    runner = ClaudeSkillRunner(local=fake_local)
    result = runner.dispatch("hello")

    assert result.exit_code == 0
    assert result.stdout == "done"
    assert result.metadata["input_tokens"] == "100"
    assert result.metadata["output_tokens"] == "200"
    assert result.metadata["cache_creation_input_tokens"] == "300"
    assert result.metadata["cache_read_input_tokens"] == "50"
    assert result.metadata["total_cost_usd"] == "0.0123"


def test_runner_metadata_empty_when_no_envelope():
    """Plain text stdout falls through with no metadata."""
    fake_local = MagicMock()
    fake_local.dispatch.return_value = RunResult(
        exit_code=0,
        stdout="not json",
        stderr="",
        duration_ms=100,
    )
    runner = ClaudeSkillRunner(local=fake_local)
    result = runner.dispatch("hello")
    assert result.metadata == {}


def test_subagent_wrap_propagates_runner_metadata():
    """IsolatedWorker._wrap merges runner metadata into WorkerResult."""
    from etzchaim.autopilot.delegation.subagent import IsolatedWorker

    rr = RunResult(
        exit_code=0,
        stdout="ok",
        stderr="",
        duration_ms=42,
        metadata={"input_tokens": "10", "output_tokens": "20"},
    )
    wr = IsolatedWorker._wrap(rr, "implement-spec")
    assert wr.success
    assert wr.metadata["exit_code"] == "0"
    assert wr.metadata["input_tokens"] == "10"
    assert wr.metadata["output_tokens"] == "20"


def test_pr_count_sync_persists_to_state(monkeypatch):
    """run_one_cycle writes _open_pr_count() result into state."""
    from etzchaim.autopilot import loop as loop_mod

    cfg = AutopilotConfig(enabled=True, max_open_prs=10, budget_tokens_monthly=1_000_000)
    st = AutopilotState()

    monkeypatch.setattr(loop_mod, "_open_pr_count", lambda cwd=None: 4)
    monkeypatch.setattr(loop_mod, "pick_next_task", lambda: None)

    outcome = loop_mod.run_one_cycle(config=cfg, state=st)
    assert outcome.status == "skipped"
    assert outcome.summary == "no pending tasks"

    reloaded = AutopilotState.load()
    assert reloaded.autopilot_pr_count_open == 4


def test_pr_count_sync_no_write_on_gh_failure(monkeypatch):
    """If `gh pr list` fails (returns -1), state is not overwritten."""
    from etzchaim.autopilot import loop as loop_mod

    cfg = AutopilotConfig(enabled=True, max_open_prs=10, budget_tokens_monthly=1_000_000)
    st = AutopilotState(autopilot_pr_count_open=7)
    st.save()

    monkeypatch.setattr(loop_mod, "_open_pr_count", lambda cwd=None: -1)
    monkeypatch.setattr(loop_mod, "pick_next_task", lambda: None)

    loop_mod.run_one_cycle(config=cfg, state=st)
    reloaded = AutopilotState.load()
    assert reloaded.autopilot_pr_count_open == 7
