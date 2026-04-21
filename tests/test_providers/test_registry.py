"""Test provider registry — select_claude_backend dispatcher."""
from __future__ import annotations

from unittest.mock import patch

import pytest


def test_selects_anthropic_sdk_when_key_set(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-mock")
    from etzchaim.providers.registry import select_claude_backend
    assert select_claude_backend() == "anthropic_sdk"


def test_selects_claude_cli_when_only_cli_available(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with patch("shutil.which", return_value="/usr/local/bin/claude"):
        from etzchaim.providers.registry import select_claude_backend
        assert select_claude_backend() == "claude_cli"


def test_raises_when_neither_available(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with patch("shutil.which", return_value=None):
        from etzchaim.providers.registry import select_claude_backend
        with pytest.raises(RuntimeError, match="Aucun backend Claude"):
            select_claude_backend()


def test_sdk_preferred_over_cli_when_both_available(monkeypatch):
    """When ANTHROPIC_API_KEY set AND claude CLI available, SDK wins (container-safe)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    with patch("shutil.which", return_value="/usr/local/bin/claude"):
        from etzchaim.providers.registry import select_claude_backend
        assert select_claude_backend() == "anthropic_sdk"
