"""Cross-platform path helpers for etzchaim state, config, compose.

Uses Path.home() and os.environ — portable across macOS, Linux, Windows.
Never hardcodes absolute paths.
"""
from __future__ import annotations

import os
from pathlib import Path


def state_dir() -> Path:
    """State directory (logs, PID, events, wizard resume state, compose files).

    Default: ~/.etz-chaim/
    Override: ETZCHAIM_STATE_DIR env var.
    """
    override = os.environ.get("ETZCHAIM_STATE_DIR")
    if override:
        return Path(override)
    return Path.home() / ".etz-chaim"


def ensure_state_dir() -> Path:
    """Return state_dir(), creating it (and parents) if missing."""
    p = state_dir()
    p.mkdir(parents=True, exist_ok=True)
    return p


def compose_dir() -> Path:
    """Directory where docker-compose templates + config.yaml + .env are extracted
    during onboard. Per design C2, the user's config.yaml lives here (next to the
    compose files), so compose `./config.yaml` bind-mount resolves correctly.
    """
    return state_dir() / "compose"


def config_path() -> Path:
    """Path to user config.yaml (copied from package at onboard, user-editable)."""
    return compose_dir() / "config.yaml"


def env_file() -> Path:
    """Path to generated .env file (chmod 600 on Unix, ACL on Windows)."""
    return compose_dir() / ".env"


def logs_dir() -> Path:
    return state_dir() / "logs"


def wizard_state_file() -> Path:
    """Where the wizard saves Ctrl+C resume state (JSON)."""
    return state_dir() / "onboard_state.json"


def daemon_pid_file() -> Path:
    """Daemon PID file (for non-container native runs)."""
    return state_dir() / "daemon.pid"


def daemon_log_file() -> Path:
    """Daemon log file (non-container fallback). In container, stdout is captured."""
    return state_dir() / "daemon.log"


def daemon_state_file() -> Path:
    """Daemon state JSON (last heartbeat, last tasks, etc.)."""
    return state_dir() / "daemon_state.json"


def daemon_events_file() -> Path:
    """Append-only JSONL of MazalEngine events."""
    return state_dir() / "daemon_events.jsonl"
