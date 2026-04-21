"""Tests for _paths.read_shem / read_birthtime helpers."""
from __future__ import annotations

from datetime import datetime, timezone


def _write_env(tmp_path, content: str):
    (tmp_path / ".env").write_text(content)


def test_read_shem_default_when_env_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("ETZCHAIM_STATE_DIR", str(tmp_path))
    from etzchaim._paths import read_shem, compose_dir
    compose_dir().mkdir(parents=True, exist_ok=True)
    assert read_shem() == "Etz Chaim"


def test_read_shem_returns_saved_value(monkeypatch, tmp_path):
    monkeypatch.setenv("ETZCHAIM_STATE_DIR", str(tmp_path))
    from etzchaim._paths import read_shem, compose_dir
    compose_dir().mkdir(parents=True, exist_ok=True)
    (compose_dir() / ".env").write_text(
        "FOO=bar\nETZCHAIM_SHEM=Keter\nBAZ=qux\n"
    )
    assert read_shem() == "Keter"


def test_read_shem_strips_quotes(monkeypatch, tmp_path):
    monkeypatch.setenv("ETZCHAIM_STATE_DIR", str(tmp_path))
    from etzchaim._paths import read_shem, compose_dir
    compose_dir().mkdir(parents=True, exist_ok=True)
    (compose_dir() / ".env").write_text('ETZCHAIM_SHEM="My Tree"\n')
    assert read_shem() == "My Tree"


def test_read_birthtime_none_when_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("ETZCHAIM_STATE_DIR", str(tmp_path))
    from etzchaim._paths import read_birthtime, compose_dir
    compose_dir().mkdir(parents=True, exist_ok=True)
    assert read_birthtime() is None


def test_read_birthtime_parses_iso8601(monkeypatch, tmp_path):
    monkeypatch.setenv("ETZCHAIM_STATE_DIR", str(tmp_path))
    from etzchaim._paths import read_birthtime, compose_dir
    compose_dir().mkdir(parents=True, exist_ok=True)
    (compose_dir() / ".env").write_text(
        "ETZCHAIM_BIRTHTIME=2026-04-21T22:34:18.127000+02:00\n"
    )
    dt = read_birthtime()
    assert dt is not None
    assert dt.tzinfo is not None
    assert dt.year == 2026 and dt.month == 4 and dt.day == 21


def test_read_birthtime_invalid_returns_none(monkeypatch, tmp_path):
    monkeypatch.setenv("ETZCHAIM_STATE_DIR", str(tmp_path))
    from etzchaim._paths import read_birthtime, compose_dir
    compose_dir().mkdir(parents=True, exist_ok=True)
    (compose_dir() / ".env").write_text("ETZCHAIM_BIRTHTIME=not-a-timestamp\n")
    assert read_birthtime() is None
