from __future__ import annotations

import json
import os
import subprocess

from typer.testing import CliRunner


def _relative_files(root):
    return sorted(
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file()
    )


def _guard_activation_commands(monkeypatch):
    calls: list[object] = []

    def forbidden_call(*args, **kwargs):
        calls.append(args[0] if args else kwargs)
        raise AssertionError(f"unexpected activation command: {args!r} {kwargs!r}")

    monkeypatch.setattr(subprocess, "run", forbidden_call)
    monkeypatch.setattr(subprocess, "Popen", forbidden_call)
    monkeypatch.setattr(os, "system", forbidden_call)
    monkeypatch.setattr(os, "popen", forbidden_call)
    return calls


def test_supervision_help_works():
    from etzchaim.cli.app import app

    runner = CliRunner()
    result = runner.invoke(app, ["supervision", "--help"])

    assert result.exit_code == 0
    assert "--preflight" in result.stdout
    assert "--install" in result.stdout
    assert "--dry-run" in result.stdout


def test_supervision_preflight_json_is_read_only(monkeypatch, tmp_path):
    from etzchaim.cli.app import app

    monkeypatch.setenv("HOME", str(tmp_path))
    calls = _guard_activation_commands(monkeypatch)

    runner = CliRunner()
    result = runner.invoke(app, ["supervision", "--preflight", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["status"] == "ok"
    assert data["phase"] == "3B"
    assert data["mode"] == "preflight"
    assert data["read_only"] is True
    assert data["real_install_allowed"] is False
    assert data["activation_allowed"] is False
    assert data["label"] == "com.etzchaim.loop-once"
    assert data["target"]["path"].startswith(str(tmp_path))
    assert data["target"]["exists"] is False
    assert data["template"]["program_arguments"] == ["etzchaim", "loop", "--once", "--json"]
    assert _relative_files(tmp_path) == []
    assert calls == []


def test_supervision_install_dry_run_json_writes_no_files(monkeypatch, tmp_path):
    from etzchaim.cli.app import app

    monkeypatch.setenv("HOME", str(tmp_path))
    calls = _guard_activation_commands(monkeypatch)

    runner = CliRunner()
    result = runner.invoke(app, ["supervision", "--install", "--dry-run", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["status"] == "dry-run"
    assert data["phase"] == "3B"
    assert data["mode"] == "install-dry-run"
    assert data["read_only"] is True
    assert data["real_install_allowed"] is False
    assert data["activation_allowed"] is False
    assert data["would_write"]["path"].startswith(str(tmp_path))
    assert data["would_write"]["bytes"] > 0
    assert "com.etzchaim.loop-once" in data["would_write"]["plist"]
    assert "launchctl" not in data["would_write"]["plist"]
    assert _relative_files(tmp_path) == []
    assert calls == []


def test_supervision_real_install_is_refused(monkeypatch, tmp_path):
    from etzchaim.cli.app import app

    monkeypatch.setenv("HOME", str(tmp_path))
    calls = _guard_activation_commands(monkeypatch)

    runner = CliRunner()
    result = runner.invoke(app, ["supervision", "--install", "--json"])

    assert result.exit_code != 0
    data = json.loads(result.stdout)
    assert data["status"] == "refused"
    assert data["phase"] == "3B"
    assert data["mode"] == "install-refused"
    assert data["real_install_allowed"] is False
    assert data["activation_allowed"] is False
    assert data["message"] == "Phase 3B refuses real LaunchAgent installation. Use --dry-run only."
    assert _relative_files(tmp_path) == []
    assert calls == []


def test_supervision_preflight_and_install_together_is_invalid(monkeypatch, tmp_path):
    from etzchaim.cli.app import app

    monkeypatch.setenv("HOME", str(tmp_path))
    calls = _guard_activation_commands(monkeypatch)

    runner = CliRunner()
    result = runner.invoke(app, ["supervision", "--preflight", "--install", "--json"])

    assert result.exit_code != 0
    data = json.loads(result.stdout)
    assert data["status"] == "error"
    assert data["message"] == "Choose exactly one mode: --preflight or --install."
    assert _relative_files(tmp_path) == []
    assert calls == []
