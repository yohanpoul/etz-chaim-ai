"""Tests for play_ceremony / play_compact.

All animation sleeps are monkeypatched to a no-op via orchestrator._sleep so
tests run instantly. Keypress is monkeypatched to return 'x' immediately.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest


def _fake_input_once(responses: list[str]):
    """Return a side_effect function that returns responses in order, then ''."""
    it = iter(responses)

    def _fn(prompt: str = "") -> str:
        try:
            return next(it)
        except StopIteration:
            return ""

    return _fn


def test_play_compact_returns_defaults(monkeypatch):
    from etzchaim.cli.ceremony import _orchestrator
    monkeypatch.setattr(_orchestrator, "_sleep", lambda s: None)
    result = _orchestrator.play_compact()
    assert result.shem == "Etz Chaim"
    assert result.birthtime.tzinfo is not None
    delta = abs((datetime.now(timezone.utc) - result.birthtime).total_seconds())
    assert delta < 5


def test_play_ceremony_captures_birthtime_at_keypress(monkeypatch):
    from etzchaim.cli.ceremony import _orchestrator
    monkeypatch.setattr(_orchestrator, "_sleep", lambda s: None)
    monkeypatch.setattr(_orchestrator, "_wait_for_any_key", lambda: "x")
    monkeypatch.setattr("builtins.input", lambda prompt="": "")

    fixed = datetime(2026, 4, 21, 22, 34, 18, 127000, tzinfo=timezone.utc)
    monkeypatch.setattr(_orchestrator, "_now_utc", lambda: fixed)

    result = _orchestrator.play_ceremony(width=120)
    assert result.birthtime == fixed.astimezone()
    assert result.shem == "Etz Chaim"


def test_play_ceremony_accepts_user_name(monkeypatch):
    from etzchaim.cli.ceremony import _orchestrator
    monkeypatch.setattr(_orchestrator, "_sleep", lambda s: None)
    monkeypatch.setattr(_orchestrator, "_wait_for_any_key", lambda: "x")
    monkeypatch.setattr("builtins.input", _fake_input_once(["Keter"]))
    result = _orchestrator.play_ceremony(width=120)
    assert result.shem == "Keter"


def test_play_ceremony_rejects_invalid_then_accepts(monkeypatch):
    from etzchaim.cli.ceremony import _orchestrator
    monkeypatch.setattr(_orchestrator, "_sleep", lambda s: None)
    monkeypatch.setattr(_orchestrator, "_wait_for_any_key", lambda: "x")
    monkeypatch.setattr("builtins.input", _fake_input_once(["bad/name", "Keter"]))
    result = _orchestrator.play_ceremony(width=120)
    assert result.shem == "Keter"


def test_play_ceremony_falls_back_to_default_on_second_invalid(monkeypatch):
    from etzchaim.cli.ceremony import _orchestrator
    monkeypatch.setattr(_orchestrator, "_sleep", lambda s: None)
    monkeypatch.setattr(_orchestrator, "_wait_for_any_key", lambda: "x")
    monkeypatch.setattr("builtins.input", _fake_input_once(["bad/one", "bad\x00two"]))
    result = _orchestrator.play_ceremony(width=120)
    assert result.shem == "Etz Chaim"


def test_validate_shem_regex():
    from etzchaim.cli.ceremony._orchestrator import _validate_shem
    assert _validate_shem("Etz Chaim") is True
    assert _validate_shem("Keter-1") is True
    assert _validate_shem("תפארת") is True
    assert _validate_shem("My'Tree.v2") is True
    assert _validate_shem("") is False
    assert _validate_shem("a" * 41) is False
    assert _validate_shem("bad/name") is False
    assert _validate_shem("bad\x00name") is False
    assert _validate_shem("bad;rm -rf /") is False


def test_play_ceremony_honors_ctrl_c_during_hineni(monkeypatch):
    from etzchaim.cli.ceremony import _orchestrator

    monkeypatch.setattr(_orchestrator, "_sleep", lambda s: None)

    def _raise():
        raise KeyboardInterrupt

    monkeypatch.setattr(_orchestrator, "_wait_for_any_key", _raise)
    with pytest.raises(KeyboardInterrupt):
        _orchestrator.play_ceremony(width=120)


def test_ceremony_result_birthtime_is_local_tz_aware(monkeypatch):
    from etzchaim.cli.ceremony import _orchestrator
    monkeypatch.setattr(_orchestrator, "_sleep", lambda s: None)
    monkeypatch.setattr(_orchestrator, "_wait_for_any_key", lambda: "x")
    monkeypatch.setattr("builtins.input", lambda prompt="": "")
    result = _orchestrator.play_ceremony(width=120)
    assert result.birthtime.tzinfo is not None
