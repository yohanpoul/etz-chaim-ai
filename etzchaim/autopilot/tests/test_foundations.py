"""Tests for autopilot foundations: config, state, runners, memory."""

from __future__ import annotations

import os
import tempfile
import time

import pytest

from etzchaim.autopilot.config import AutopilotConfig
from etzchaim.autopilot.runners.base import RunResult
from etzchaim.autopilot.runners.local import LocalRunner


@pytest.fixture(autouse=True)
def _isolate_state(monkeypatch):
    """Each test gets a fresh state dir."""
    tmp = tempfile.mkdtemp()
    monkeypatch.setenv("ETZCHAIM_STATE_DIR", tmp)
    yield tmp


# ─── config ──────────────────────────────────────────────────


def test_config_defaults_disabled():
    c = AutopilotConfig()
    assert c.enabled is False
    assert c.interval_seconds == 1800
    assert c.worker == "claude"


def test_config_excludes_internal_paths():
    c = AutopilotConfig()
    assert c.is_path_excluded("sifrei_yesod/sefer.yaml")
    assert c.is_path_excluded(".claude/skills/foo")
    assert not c.is_path_excluded("etzchaim/cli/app.py")


def test_config_from_missing_file_returns_defaults(tmp_path):
    c = AutopilotConfig.from_file(tmp_path / "nope.yaml")
    assert c.enabled is False


def test_config_from_yaml(tmp_path):
    (tmp_path / "cfg.yaml").write_text(
        "autopilot:\n  enabled: true\n  worker: codex\n  interval_seconds: 60\n"
    )
    c = AutopilotConfig.from_file(tmp_path / "cfg.yaml")
    assert c.enabled is True
    assert c.worker == "codex"
    assert c.interval_seconds == 60


# ─── state ───────────────────────────────────────────────────


def test_state_load_default():
    from etzchaim.autopilot.state import AutopilotState

    s = AutopilotState.load()
    assert s.last_autopilot == 0.0
    assert s.autopilot_pr_count_open == 0


def test_state_save_round_trip():
    from etzchaim.autopilot.state import AutopilotState

    s = AutopilotState(last_autopilot=time.time(), autopilot_pr_count_open=2)
    s.save()
    loaded = AutopilotState.load()
    assert loaded.autopilot_pr_count_open == 2
    assert loaded.last_autopilot > 0


# ─── runner ──────────────────────────────────────────────────


def test_local_runner_echo():
    r = LocalRunner()
    res = r.dispatch(["echo", "hello"])
    assert res.success
    assert "hello" in res.stdout
    assert isinstance(res, RunResult)


def test_local_runner_unknown_command():
    r = LocalRunner()
    res = r.dispatch(["__not_a_real_binary_zzz__"])
    assert not res.success
    assert res.exit_code == 127
