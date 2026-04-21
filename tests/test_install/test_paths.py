"""Test cross-platform etzchaim._paths helpers."""
from __future__ import annotations

import importlib


def _reload_paths():
    from etzchaim import _paths
    return importlib.reload(_paths)


def test_state_dir_default(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("ETZCHAIM_STATE_DIR", raising=False)
    paths = _reload_paths()
    assert paths.state_dir() == tmp_path / ".etz-chaim"


def test_state_dir_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("ETZCHAIM_STATE_DIR", str(tmp_path / "custom"))
    paths = _reload_paths()
    assert paths.state_dir() == tmp_path / "custom"


def test_ensure_state_dir_creates_if_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("ETZCHAIM_STATE_DIR", raising=False)
    paths = _reload_paths()
    p = paths.ensure_state_dir()
    assert p.exists()
    assert p.is_dir()


def test_compose_dir_is_under_state(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("ETZCHAIM_STATE_DIR", raising=False)
    paths = _reload_paths()
    assert paths.compose_dir() == tmp_path / ".etz-chaim" / "compose"


def test_config_and_env_in_compose_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("ETZCHAIM_STATE_DIR", raising=False)
    paths = _reload_paths()
    assert paths.config_path() == tmp_path / ".etz-chaim" / "compose" / "config.yaml"
    assert paths.env_file() == tmp_path / ".etz-chaim" / "compose" / ".env"


def test_daemon_files_paths(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("ETZCHAIM_STATE_DIR", raising=False)
    paths = _reload_paths()
    assert paths.daemon_pid_file().name == "daemon.pid"
    assert paths.daemon_state_file().name == "daemon_state.json"
    assert paths.daemon_events_file().name == "daemon_events.jsonl"
