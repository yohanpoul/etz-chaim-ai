"""Test Flask bind host resolution (container vs native)."""
from __future__ import annotations

import os


def _resolve_web_host() -> str:
    """Inline copy of the resolve logic in mitzvot.py (for testing)."""
    return (
        os.environ.get("WEB_HOST")
        or ("0.0.0.0" if os.environ.get("ETZCHAIM_IN_CONTAINER") == "1" else "127.0.0.1")
    )


def test_default_is_loopback_outside_container(monkeypatch):
    monkeypatch.delenv("WEB_HOST", raising=False)
    monkeypatch.delenv("ETZCHAIM_IN_CONTAINER", raising=False)
    assert _resolve_web_host() == "127.0.0.1"


def test_zero_bind_in_container(monkeypatch):
    monkeypatch.delenv("WEB_HOST", raising=False)
    monkeypatch.setenv("ETZCHAIM_IN_CONTAINER", "1")
    assert _resolve_web_host() == "0.0.0.0"


def test_env_override(monkeypatch):
    monkeypatch.setenv("WEB_HOST", "192.168.1.5")
    monkeypatch.setenv("ETZCHAIM_IN_CONTAINER", "1")
    assert _resolve_web_host() == "192.168.1.5"  # explicit wins over container
