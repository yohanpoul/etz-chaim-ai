"""Test etzchaim ceremony --preview subcommand."""
from __future__ import annotations

from typer.testing import CliRunner


def test_ceremony_preview_runs_without_error(monkeypatch):
    from etzchaim.cli import commands as _cmds  # noqa: F401 — make sure modules loaded
    from etzchaim.cli.commands import ceremony as _ceremony_mod

    calls: list[int] = []

    def _fake_play(*args, **kwargs):
        calls.append(1)
        from datetime import datetime, timezone

        from etzchaim.cli.ceremony._orchestrator import CeremonyResult
        return CeremonyResult(shem="Preview", birthtime=datetime.now(timezone.utc).astimezone())

    monkeypatch.setattr(_ceremony_mod, "play_ceremony", _fake_play)

    from etzchaim.cli.app import app
    runner = CliRunner()
    result = runner.invoke(app, ["ceremony", "--preview"])
    assert result.exit_code == 0, result.stdout
    assert calls == [1]


def test_ceremony_appears_in_help():
    from etzchaim.cli.app import app
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert "ceremony" in result.stdout


def test_start_prints_shem_and_birthtime(monkeypatch, tmp_path):
    monkeypatch.setenv("ETZCHAIM_STATE_DIR", str(tmp_path))
    from etzchaim._paths import compose_dir
    compose_dir().mkdir(parents=True, exist_ok=True)
    (compose_dir() / ".env").write_text(
        "WEB_PORT=8080\n"
        "ETZCHAIM_SHEM=Keter\n"
        "ETZCHAIM_BIRTHTIME=2026-04-21T22:34:18+02:00\n"
    )
    from etzchaim.cli import compose, detect
    monkeypatch.setattr(compose, "compose_up", lambda profile=None: 0)
    monkeypatch.setattr(detect, "detect_compose_profile", lambda: "docker")

    from etzchaim.cli.app import app
    runner = CliRunner()
    result = runner.invoke(app, ["start"])
    assert result.exit_code == 0, result.stdout
    assert "◉ Keter" in result.stdout
    assert "2026-04-21 22:34" in result.stdout
    assert "is awake" in result.stdout


def test_status_shows_shem_and_age(monkeypatch, tmp_path):
    from datetime import datetime, timedelta, timezone
    monkeypatch.setenv("ETZCHAIM_STATE_DIR", str(tmp_path))
    from etzchaim._paths import compose_dir
    compose_dir().mkdir(parents=True, exist_ok=True)
    past = (datetime.now(timezone.utc) - timedelta(hours=3, minutes=22)).isoformat()
    (compose_dir() / ".env").write_text(
        f"ETZCHAIM_SHEM=Keter\nETZCHAIM_BIRTHTIME={past}\n"
    )
    from etzchaim.cli import compose, detect
    monkeypatch.setattr(compose, "compose_ps", lambda profile=None: "")
    monkeypatch.setattr(detect, "detect_compose_profile", lambda: "docker")

    from etzchaim.cli.app import app
    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.stdout
    assert "◉ Keter" in result.stdout
    assert "3h 22m old" in result.stdout


def test_status_falls_back_when_birthtime_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("ETZCHAIM_STATE_DIR", str(tmp_path))
    from etzchaim._paths import compose_dir
    compose_dir().mkdir(parents=True, exist_ok=True)
    (compose_dir() / ".env").write_text("ETZCHAIM_SHEM=Keter\n")
    from etzchaim.cli import compose, detect
    monkeypatch.setattr(compose, "compose_ps", lambda profile=None: "")
    monkeypatch.setattr(detect, "detect_compose_profile", lambda: "docker")

    from etzchaim.cli.app import app
    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.stdout
    assert "◉ Keter" in result.stdout
    assert " old" not in result.stdout
