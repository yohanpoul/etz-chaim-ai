"""Tests for etzchaim.cli.ceremony._terminal capability detection."""
from __future__ import annotations


def test_should_play_ceremony_true_on_interactive_tty(monkeypatch):
    from etzchaim.cli.ceremony import _terminal
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.setattr(_terminal, "_stdout_isatty", lambda: True)
    monkeypatch.setattr(_terminal, "_stdin_isatty", lambda: True)
    assert _terminal.should_play_ceremony(non_interactive=False, no_ceremony=False) is True


def test_should_play_ceremony_false_on_non_interactive_flag(monkeypatch):
    from etzchaim.cli.ceremony import _terminal
    monkeypatch.setattr(_terminal, "_stdout_isatty", lambda: True)
    monkeypatch.setattr(_terminal, "_stdin_isatty", lambda: True)
    assert _terminal.should_play_ceremony(non_interactive=True, no_ceremony=False) is False


def test_should_play_ceremony_false_on_no_ceremony_flag(monkeypatch):
    from etzchaim.cli.ceremony import _terminal
    monkeypatch.setattr(_terminal, "_stdout_isatty", lambda: True)
    monkeypatch.setattr(_terminal, "_stdin_isatty", lambda: True)
    assert _terminal.should_play_ceremony(non_interactive=False, no_ceremony=True) is False


def test_should_play_ceremony_false_in_ci(monkeypatch):
    from etzchaim.cli.ceremony import _terminal
    monkeypatch.setenv("CI", "true")
    monkeypatch.setattr(_terminal, "_stdout_isatty", lambda: True)
    monkeypatch.setattr(_terminal, "_stdin_isatty", lambda: True)
    assert _terminal.should_play_ceremony(non_interactive=False, no_ceremony=False) is False


def test_should_play_ceremony_false_in_github_actions(monkeypatch):
    from etzchaim.cli.ceremony import _terminal
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setattr(_terminal, "_stdout_isatty", lambda: True)
    monkeypatch.setattr(_terminal, "_stdin_isatty", lambda: True)
    assert _terminal.should_play_ceremony(non_interactive=False, no_ceremony=False) is False


def test_should_play_ceremony_false_when_term_dumb(monkeypatch):
    from etzchaim.cli.ceremony import _terminal
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setenv("TERM", "dumb")
    monkeypatch.setattr(_terminal, "_stdout_isatty", lambda: True)
    monkeypatch.setattr(_terminal, "_stdin_isatty", lambda: True)
    assert _terminal.should_play_ceremony(non_interactive=False, no_ceremony=False) is False


def test_should_play_ceremony_false_when_stdout_piped(monkeypatch):
    from etzchaim.cli.ceremony import _terminal
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setenv("TERM", "xterm")
    monkeypatch.setattr(_terminal, "_stdout_isatty", lambda: False)
    monkeypatch.setattr(_terminal, "_stdin_isatty", lambda: True)
    assert _terminal.should_play_ceremony(non_interactive=False, no_ceremony=False) is False


def test_supports_color_false_when_no_color_set(monkeypatch):
    from etzchaim.cli.ceremony import _terminal
    monkeypatch.setenv("NO_COLOR", "1")
    assert _terminal.supports_color() is False


def test_supports_color_true_otherwise(monkeypatch):
    from etzchaim.cli.ceremony import _terminal
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    assert _terminal.supports_color() is True


def test_terminal_is_narrow_uses_columns_env(monkeypatch):
    from etzchaim.cli.ceremony import _terminal
    monkeypatch.setenv("COLUMNS", "60")
    assert _terminal.is_narrow() is True
    monkeypatch.setenv("COLUMNS", "120")
    assert _terminal.is_narrow() is False


def test_supports_utf8_true_when_utf8_locale(monkeypatch):
    from etzchaim.cli.ceremony import _terminal
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    assert _terminal.supports_utf8() is True


def test_supports_utf8_false_when_ascii_locale(monkeypatch):
    from etzchaim.cli.ceremony import _terminal
    monkeypatch.setenv("LANG", "C")
    monkeypatch.setenv("LC_ALL", "C")
    assert _terminal.supports_utf8() is False
