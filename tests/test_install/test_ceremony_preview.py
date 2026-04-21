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
