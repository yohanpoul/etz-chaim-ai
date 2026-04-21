"""Tests for wait_for_any_key (mocked stdin)."""
from __future__ import annotations

import pytest


def test_wait_for_any_key_returns_first_byte(monkeypatch):
    from etzchaim.cli.ceremony import _hineni
    monkeypatch.setattr(_hineni, "_read_one_raw", lambda: "x")
    assert _hineni.wait_for_any_key() == "x"


def test_wait_for_any_key_raises_on_ctrl_c(monkeypatch):
    from etzchaim.cli.ceremony import _hineni

    def _raise_kb():
        raise KeyboardInterrupt()
    monkeypatch.setattr(_hineni, "_read_one_raw", _raise_kb)
    with pytest.raises(KeyboardInterrupt):
        _hineni.wait_for_any_key()


def test_wait_for_any_key_falls_back_to_input_when_no_raw(monkeypatch):
    """On terminals where termios/msvcrt aren't available, fall back to input()."""
    from etzchaim.cli.ceremony import _hineni

    def _raise_err():
        raise RuntimeError("no termios")
    monkeypatch.setattr(_hineni, "_read_one_raw", _raise_err)
    monkeypatch.setattr("builtins.input", lambda prompt="": "")
    # Fallback returns an empty string (user pressed Enter)
    assert _hineni.wait_for_any_key() == ""


def test_wait_for_any_key_treats_etx_as_ctrl_c(monkeypatch):
    """Raw mode doesn't convert Ctrl-C to KeyboardInterrupt — _hineni must."""
    from etzchaim.cli.ceremony import _hineni
    monkeypatch.setattr(_hineni, "_read_one_raw", lambda: "\x03")  # ETX
    with pytest.raises(KeyboardInterrupt):
        _hineni.wait_for_any_key()
