"""Sprint 7 Finding 2 — /api/daemon/state must never return null while a daemon is running.

The original bug: during launchd KeepAlive restart windows (old PID killed,
new PID not yet published to daemon.pid), the endpoint silently set pid=null
and uptime=null while a daemon was actually live. These tests cover:

  - happy path (valid PID file, live process)
  - stale PID file + ps-fallback discovery
  - missing PID file + no daemon → {active: false, pid: null} (expected)
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest


def _build_state_file(tmp_path: Path) -> dict:
    state_file = tmp_path / "daemon_state.json"
    payload = {
        "last_gc": 1776459895.0,
        "last_hitbonenut": 1776554122.9,
        "last_insightforge": 1776459895.0,
        "_daemon_pid": 92968,
    }
    state_file.write_text(json.dumps(payload))
    return payload


def test_read_daemon_state_happy_path(tmp_path, monkeypatch):
    """PID file valid + process alive → active, pid, uptime non-null."""
    from web.blueprints import api as api_mod

    pid_file = tmp_path / "daemon.pid"
    pid_file.write_text("99999\n")
    _build_state_file(tmp_path)

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path.parent))
    # rehome .etz-chaim under tmp_path.parent
    etz = tmp_path.parent / ".etz-chaim"
    etz.mkdir(exist_ok=True)
    (etz / "daemon.pid").write_text("99999\n")
    (etz / "daemon_state.json").write_text(json.dumps({"last_gc": 1.0}))

    with patch.object(api_mod.os, "kill", return_value=None):
        result = api_mod._read_daemon_state()

    assert result["active"] is True
    assert result["pid"] == 99999
    assert result["uptime"] is not None
    assert result["pid_source"] == "pid_file"
    assert result["last_cycle"] is not None


def test_read_daemon_state_ps_fallback_when_pid_file_stale(tmp_path, monkeypatch):
    """Stale PID in file + live daemon visible via ps → fallback finds it."""
    from web.blueprints import api as api_mod

    etz = tmp_path / ".etz-chaim"
    etz.mkdir()
    (etz / "daemon.pid").write_text("11111\n")  # dead
    (etz / "daemon_state.json").write_text(json.dumps({"last_gc": 1.0}))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    def _kill_raises(pid, _sig):
        raise ProcessLookupError("no such process")

    with patch.object(api_mod.os, "kill", side_effect=_kill_raises), \
         patch.object(api_mod, "_scan_live_daemon_pid",
                      return_value=(22222, 1776525064.0)):
        result = api_mod._read_daemon_state()

    assert result["active"] is True
    assert result["pid"] == 22222
    assert result["uptime"] is not None
    assert result["pid_source"] == "ps_scan"
    assert result["pid_file_stale"] == 11111


def test_read_daemon_state_no_daemon(tmp_path, monkeypatch):
    """No PID file + ps scan empty → {active: false} but no crash."""
    from web.blueprints import api as api_mod

    etz = tmp_path / ".etz-chaim"
    etz.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    with patch.object(api_mod, "_scan_live_daemon_pid", return_value=None):
        result = api_mod._read_daemon_state()

    assert result["active"] is False
    assert result["pid"] is None
    assert result["uptime"] is None
    assert result["pid_source"] is None


@pytest.mark.requires_daemon
def test_endpoint_returns_live_daemon_metrics():
    """Integration: when a daemon is actually running, endpoint returns its PID."""
    from web.blueprints.api import _read_daemon_state

    result = _read_daemon_state()
    if not result["active"]:
        pytest.skip("no live daemon")
    assert result["pid"] is not None
    assert isinstance(result["pid"], int) and result["pid"] > 0
    assert result["uptime"] is not None
    assert result["uptime"] >= 0
    assert result["last_cycle"] is not None
    keys = set(result["last_cycle"].keys())
    assert any(k.startswith("last_") for k in keys)
