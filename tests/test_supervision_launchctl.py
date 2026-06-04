from __future__ import annotations

import subprocess
from pathlib import Path


def test_launchctl_command_builders_use_fixed_argument_lists():
    from etzchaim.supervision import launchctl

    plist = Path("/tmp/com.etzchaim.loop-once.plist")

    assert launchctl.user_domain(uid=501) == "gui/501"
    assert launchctl.service_target(uid=501) == "gui/501/com.etzchaim.loop-once"
    assert launchctl.print_command(uid=501) == [
        "launchctl",
        "print",
        "gui/501/com.etzchaim.loop-once",
    ]
    assert launchctl.bootstrap_command(plist, uid=501) == [
        "launchctl",
        "bootstrap",
        "gui/501",
        "/tmp/com.etzchaim.loop-once.plist",
    ]
    assert launchctl.kickstart_command(uid=501) == [
        "launchctl",
        "kickstart",
        "-k",
        "gui/501/com.etzchaim.loop-once",
    ]
    assert launchctl.bootout_command(uid=501) == [
        "launchctl",
        "bootout",
        "gui/501/com.etzchaim.loop-once",
    ]
    assert launchctl.disable_command(uid=501) == [
        "launchctl",
        "disable",
        "gui/501/com.etzchaim.loop-once",
    ]


def test_run_launchctl_uses_subprocess_run_shell_false(monkeypatch):
    from etzchaim.supervision import launchctl

    calls: list[dict] = []

    class Completed:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(command, **kwargs):
        calls.append({"command": command, **kwargs})
        return Completed()

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = launchctl.run_launchctl(["launchctl", "print", "gui/501/com.etzchaim.loop-once"])

    assert result["returncode"] == 0
    assert calls == [
        {
            "command": ["launchctl", "print", "gui/501/com.etzchaim.loop-once"],
            "shell": False,
            "capture_output": True,
            "text": True,
            "check": False,
        }
    ]


def test_run_launchctl_refuses_mutating_commands_without_explicit_allow(monkeypatch):
    from etzchaim.supervision import launchctl

    calls: list[object] = []

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("subprocess must not run without explicit mutation allow")

    monkeypatch.setattr(subprocess, "run", fake_run)

    try:
        launchctl.run_launchctl(["launchctl", "bootstrap", "gui/501", "/tmp/agent.plist"])
    except ValueError as exc:
        assert "explicit mutation allow" in str(exc)
    else:
        raise AssertionError("expected mutable launchctl command to be refused")

    assert calls == []


def test_run_launchctl_refuses_unsupported_subcommands_even_with_explicit_allow(monkeypatch):
    from etzchaim.supervision import launchctl

    calls: list[object] = []

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("unsupported launchctl command must not run")

    monkeypatch.setattr(subprocess, "run", fake_run)

    for command in [
        ["launchctl", "enable", "gui/501/com.etzchaim.loop-once"],
        ["launchctl", "start", "gui/501/com.etzchaim.loop-once"],
        ["launchctl", "load", "/tmp/agent.plist"],
    ]:
        try:
            launchctl.run_launchctl(command, allow_mutation=True)
        except ValueError as exc:
            assert "unsupported launchctl subcommand" in str(exc)
        else:
            raise AssertionError(f"expected unsupported command to be refused: {command}")

    assert calls == []


def test_run_launchctl_captures_returncode_stdout_stderr(monkeypatch):
    from etzchaim.supervision import launchctl

    class Completed:
        returncode = 42
        stdout = "stdout text"
        stderr = "stderr text"

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: Completed())

    result = launchctl.run_launchctl(["launchctl", "print", "target"])

    assert result == {
        "command": ["launchctl", "print", "target"],
        "returncode": 42,
        "stdout": "stdout text",
        "stderr": "stderr text",
    }


def test_no_load_start_enable_commands_are_built():
    from etzchaim.supervision import launchctl

    commands = [
        launchctl.print_command(uid=501),
        launchctl.bootstrap_command(Path("/tmp/agent.plist"), uid=501),
        launchctl.kickstart_command(uid=501),
        launchctl.bootout_command(uid=501),
        launchctl.disable_command(uid=501),
    ]

    command_words = {word for command in commands for word in command}
    assert "load" not in command_words
    assert "start" not in command_words
    assert "enable" not in command_words
