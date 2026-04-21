"""Cross-platform path helpers for etzchaim state, config, compose.

Uses Path.home() and os.environ — portable across macOS, Linux, Windows.
Never hardcodes absolute paths.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

DEFAULT_SHEM = "Etz Chaim"


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


def _read_env_var(key: str) -> str | None:
    """Read a single KEY=value line from compose/.env. Strips surrounding quotes.

    Returns None if the file doesn't exist or the key isn't found.
    """
    path = env_file()
    if not path.exists():
        return None
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() != key:
            continue
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
            v = v[1:-1]
        return v
    return None


def read_shem() -> str:
    """Return the saved instance name, or the default 'Etz Chaim'."""
    value = _read_env_var("ETZCHAIM_SHEM")
    return value or DEFAULT_SHEM


def read_birthtime() -> datetime | None:
    """Return the saved birthtime as an aware datetime, or None if unset/invalid."""
    value = _read_env_var("ETZCHAIM_BIRTHTIME")
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt
