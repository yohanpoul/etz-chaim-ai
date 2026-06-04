from __future__ import annotations

import json
import os
import plistlib
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
    assert "--status" in result.stdout
    assert "--bootstrap" in result.stdout
    assert "--kickstart" in result.stdout
    assert "--bootout" in result.stdout
    assert "--disable" in result.stdout
    assert "--write" in result.stdout
    assert "--allow-real-write" in result.stdout
    assert "--allow-real-launchctl" in result.stdout
    assert "--ack" in result.stdout
    assert "--plist-state" in result.stdout


def test_supervision_preflight_json_is_read_only(monkeypatch, tmp_path):
    from etzchaim.cli.app import app

    monkeypatch.setenv("HOME", str(tmp_path))
    calls = _guard_activation_commands(monkeypatch)

    runner = CliRunner()
    result = runner.invoke(app, ["supervision", "--preflight", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["status"] == "ok"
    assert data["phase"] == "3C"
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
    assert data["phase"] == "3C"
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


def test_supervision_install_write_without_allow_flag_refuses(monkeypatch, tmp_path):
    from etzchaim.cli.app import app

    monkeypatch.setenv("HOME", str(tmp_path))
    calls = _guard_activation_commands(monkeypatch)

    runner = CliRunner()
    result = runner.invoke(app, ["supervision", "--install", "--write", "--json"])

    assert result.exit_code != 0
    data = json.loads(result.stdout)
    assert data["status"] == "refused"
    assert data["phase"] == "3C"
    assert data["mode"] == "write-refused"
    assert data["message"] == "Real plist write requires --allow-real-write and exact --ack."
    assert _relative_files(tmp_path) == []
    assert calls == []


def test_supervision_install_write_with_wrong_ack_refuses(monkeypatch, tmp_path):
    from etzchaim.cli.app import app

    monkeypatch.setenv("HOME", str(tmp_path))
    calls = _guard_activation_commands(monkeypatch)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "supervision",
            "--install",
            "--write",
            "--allow-real-write",
            "--ack",
            "WRONG",
            "--json",
        ],
    )

    assert result.exit_code != 0
    data = json.loads(result.stdout)
    assert data["status"] == "refused"
    assert data["mode"] == "write-refused"
    assert _relative_files(tmp_path) == []
    assert calls == []


def test_supervision_install_write_disabled_plist_under_tmp_home(monkeypatch, tmp_path):
    from etzchaim.cli.app import app

    monkeypatch.setenv("HOME", str(tmp_path))
    calls = _guard_activation_commands(monkeypatch)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "supervision",
            "--install",
            "--write",
            "--allow-real-write",
            "--ack",
            "WRITE PHASE 3C DISABLED PLIST",
            "--json",
        ],
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    plist_path = tmp_path / "Library" / "LaunchAgents" / "com.etzchaim.loop-once.plist"
    assert data["status"] == "written"
    assert data["mode"] == "install-write"
    assert data["written"]["path"] == str(plist_path)
    assert _relative_files(tmp_path) == ["Library/LaunchAgents/com.etzchaim.loop-once.plist"]
    plist = plistlib.loads(plist_path.read_bytes())
    assert plist["Disabled"] is True
    assert plist["RunAtLoad"] is False
    assert plist["KeepAlive"] is False
    assert plist["ProgramArguments"] == ["etzchaim", "loop", "--once", "--json"]
    assert calls == []


def test_supervision_install_write_enabled_plist_under_tmp_home(monkeypatch, tmp_path):
    from etzchaim.cli.app import app

    monkeypatch.setenv("HOME", str(tmp_path))
    calls = _guard_activation_commands(monkeypatch)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "supervision",
            "--install",
            "--write",
            "--plist-state",
            "enabled",
            "--allow-real-write",
            "--ack",
            "WRITE PHASE 3C ENABLED PLIST FOR BOOTSTRAP",
            "--json",
        ],
    )

    assert result.exit_code == 0
    plist_path = tmp_path / "Library" / "LaunchAgents" / "com.etzchaim.loop-once.plist"
    plist = plistlib.loads(plist_path.read_bytes())
    assert plist["Disabled"] is False
    assert plist["RunAtLoad"] is False
    assert plist["KeepAlive"] is False
    assert "StartInterval" not in plist
    assert "StartCalendarInterval" not in plist
    assert _relative_files(tmp_path) == ["Library/LaunchAgents/com.etzchaim.loop-once.plist"]
    assert calls == []


def test_supervision_launchctl_dry_run_modes_return_plans_without_subprocess(monkeypatch, tmp_path):
    from etzchaim.cli.app import app

    monkeypatch.setenv("HOME", str(tmp_path))
    calls = _guard_activation_commands(monkeypatch)
    runner = CliRunner()

    expected_first_actions = {
        "--bootstrap": "bootstrap",
        "--kickstart": "kickstart",
        "--bootout": "bootout",
        "--disable": "disable",
    }

    for mode, action in expected_first_actions.items():
        result = runner.invoke(app, ["supervision", mode, "--dry-run", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["status"] == "dry-run"
        assert data["mode"] == action
        assert data["command"][0] == "launchctl"

    assert _relative_files(tmp_path) == []
    assert calls == []


def test_supervision_status_dry_run_returns_print_plan_without_subprocess(monkeypatch, tmp_path):
    from etzchaim.cli.app import app

    monkeypatch.setenv("HOME", str(tmp_path))
    calls = _guard_activation_commands(monkeypatch)

    runner = CliRunner()
    result = runner.invoke(app, ["supervision", "--status", "--dry-run", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["status"] == "dry-run"
    assert data["mode"] == "status"
    assert data["read_only"] is True
    assert data["command"][0:2] == ["launchctl", "print"]
    assert _relative_files(tmp_path) == []
    assert calls == []


def test_supervision_mutable_launchctl_modes_require_exact_ack_before_subprocess(monkeypatch, tmp_path):
    from etzchaim.cli.app import app
    from etzchaim.supervision import launchagent

    monkeypatch.setenv("HOME", str(tmp_path))
    launchagent.write_launchagent_plist(home=tmp_path, disabled=False)
    calls = _guard_activation_commands(monkeypatch)
    runner = CliRunner()

    for mode in ["--bootstrap", "--kickstart", "--bootout", "--disable"]:
        result = runner.invoke(
            app,
            [
                "supervision",
                mode,
                "--allow-real-launchctl",
                "--ack",
                "WRONG",
                "--json",
            ],
        )

        assert result.exit_code != 0
        data = json.loads(result.stdout)
        assert data["status"] == "refused"
        assert data["message"] == "Real launchctl action requires --allow-real-launchctl and exact --ack."

    assert calls == []


def test_supervision_mutable_launchctl_modes_are_mocked(monkeypatch, tmp_path):
    from etzchaim.cli.app import app
    from etzchaim.supervision import launchagent

    monkeypatch.setenv("HOME", str(tmp_path))
    launchagent.write_launchagent_plist(home=tmp_path, disabled=False)

    calls: list[list[str]] = []

    class Completed:
        returncode = 0
        stdout = "mocked"
        stderr = ""

    def fake_run(command, **kwargs):
        calls.append(command)
        assert kwargs["shell"] is False
        return Completed()

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner = CliRunner()

    cases = [
        ("--bootstrap", "BOOTSTRAP PHASE 3C LAUNCHAGENT", "bootstrap"),
        ("--kickstart", "KICKSTART PHASE 3C LOOP ONCE", "kickstart"),
        ("--bootout", "BOOTOUT PHASE 3C LAUNCHAGENT", "bootout"),
        ("--disable", "DISABLE PHASE 3C LAUNCHAGENT", "disable"),
    ]

    for mode, ack, action in cases:
        result = runner.invoke(
            app,
            [
                "supervision",
                mode,
                "--allow-real-launchctl",
                "--ack",
                ack,
                "--json",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["status"] == "completed"
        assert data["mode"] == action
        assert data["result"]["returncode"] == 0

    assert [call[:2] for call in calls] == [
        ["launchctl", "bootstrap"],
        ["launchctl", "kickstart"],
        ["launchctl", "bootout"],
        ["launchctl", "disable"],
    ]


def test_supervision_preflight_and_install_together_is_invalid(monkeypatch, tmp_path):
    from etzchaim.cli.app import app

    monkeypatch.setenv("HOME", str(tmp_path))
    calls = _guard_activation_commands(monkeypatch)

    runner = CliRunner()
    result = runner.invoke(app, ["supervision", "--preflight", "--install", "--json"])

    assert result.exit_code != 0
    data = json.loads(result.stdout)
    assert data["status"] == "error"
    assert data["message"] == (
        "Choose exactly one mode: --preflight, --status, --install, --bootstrap, "
        "--kickstart, --bootout, or --disable."
    )
    assert _relative_files(tmp_path) == []
    assert calls == []
