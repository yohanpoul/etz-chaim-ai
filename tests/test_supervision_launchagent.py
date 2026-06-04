from __future__ import annotations

import os
import plistlib
import subprocess
from pathlib import Path


def test_disabled_plist_is_default_and_dormant():
    from etzchaim.supervision import launchagent

    rendered = launchagent.render_launchagent_plist()
    data = plistlib.loads(rendered)

    assert data["Label"] == "com.etzchaim.loop-once"
    assert Path(data["ProgramArguments"][0]).is_absolute()
    assert data["ProgramArguments"][1:] == ["loop", "--once", "--json"]
    assert data["RunAtLoad"] is False
    assert data["KeepAlive"] is False
    assert data["Disabled"] is True
    assert "StartInterval" not in data
    assert "StartCalendarInterval" not in data
    assert "WatchPaths" not in data
    assert "QueueDirectories" not in data


def test_enabled_plist_is_only_disabled_false_and_still_dormant():
    from etzchaim.supervision import launchagent

    rendered = launchagent.render_launchagent_plist(disabled=False)
    data = plistlib.loads(rendered)

    assert data["Label"] == "com.etzchaim.loop-once"
    assert Path(data["ProgramArguments"][0]).is_absolute()
    assert data["ProgramArguments"][1:] == ["loop", "--once", "--json"]
    assert data["RunAtLoad"] is False
    assert data["KeepAlive"] is False
    assert data["Disabled"] is False
    assert "StartInterval" not in data
    assert "StartCalendarInterval" not in data


def test_validate_rejects_start_interval():
    from etzchaim.supervision import launchagent

    payload = launchagent.launchagent_payload()
    payload["StartInterval"] = 3600

    assert "StartInterval is not allowed in Phase 3C" in launchagent.validate_launchagent_payload(payload)


def test_validate_rejects_start_calendar_interval():
    from etzchaim.supervision import launchagent

    payload = launchagent.launchagent_payload()
    payload["StartCalendarInterval"] = {"Hour": 12}

    assert (
        "StartCalendarInterval is not allowed in Phase 3C"
        in launchagent.validate_launchagent_payload(payload)
    )


def test_validate_rejects_watch_paths_and_queue_directories():
    from etzchaim.supervision import launchagent

    cases = {
        "WatchPaths": ["/tmp"],
        "QueueDirectories": ["/tmp"],
    }

    for key, value in cases.items():
        payload = launchagent.launchagent_payload()
        payload[key] = value

        assert f"{key} is not allowed in Phase 3C" in launchagent.validate_launchagent_payload(payload)


def test_validate_rejects_unknown_launchd_keys():
    from etzchaim.supervision import launchagent

    payload = launchagent.launchagent_payload()
    payload["StartOnMount"] = True

    assert "StartOnMount is not allowed in Phase 3C" in launchagent.validate_launchagent_payload(payload)


def test_validate_rejects_relative_program_executable():
    from etzchaim.supervision import launchagent

    payload = launchagent.launchagent_payload(executable="/usr/bin/true")
    payload["ProgramArguments"] = ["etzchaim", "loop", "--once", "--json"]

    assert "ProgramArguments[0] must be an absolute executable path" in launchagent.validate_launchagent_payload(payload)


def test_write_launchagent_plist_requires_explicit_home(monkeypatch, tmp_path):
    from etzchaim.supervision import launchagent

    monkeypatch.setenv("HOME", str(tmp_path))

    try:
        launchagent.write_launchagent_plist()
    except ValueError as exc:
        assert "explicit home" in str(exc)
    else:
        raise AssertionError("expected implicit default HOME write to be refused")

    assert sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*") if path.is_file()) == []


def test_write_launchagent_plist_writes_only_expected_tmp_home_path(monkeypatch, tmp_path):
    from etzchaim.supervision import launchagent

    monkeypatch.setenv("HOME", str(tmp_path))

    result = launchagent.write_launchagent_plist(home=tmp_path)
    written_path = tmp_path / "Library" / "LaunchAgents" / "com.etzchaim.loop-once.plist"

    assert result["status"] == "written"
    assert result["path"] == str(written_path)
    assert written_path.exists()
    data = launchagent.parse_launchagent_plist(written_path)
    assert data["Disabled"] is True
    assert Path(data["ProgramArguments"][0]).is_absolute()
    assert data["ProgramArguments"][1:] == ["loop", "--once", "--json"]
    assert sorted(
        str(path.relative_to(tmp_path))
        for path in tmp_path.rglob("*")
        if path.is_file()
    ) == ["Library/LaunchAgents/com.etzchaim.loop-once.plist"]


def test_write_launchagent_plist_refuses_invalid_target_if_home_escape_attempt(tmp_path):
    from etzchaim.supervision import launchagent

    outside = tmp_path.parent / "outside-home"

    try:
        launchagent.write_launchagent_plist(home=tmp_path, target_path=outside / "agent.plist")
    except ValueError as exc:
        assert "outside the expected LaunchAgents path" in str(exc)
    else:
        raise AssertionError("expected home escape write to be refused")


def test_launchagent_renderer_does_not_call_activation_commands(monkeypatch, tmp_path):
    from etzchaim.supervision import launchagent

    calls: list[object] = []

    def forbidden_call(*args, **kwargs):
        calls.append(args[0] if args else kwargs)
        raise AssertionError(f"unexpected activation command: {args!r} {kwargs!r}")

    monkeypatch.setattr(subprocess, "run", forbidden_call)
    monkeypatch.setattr(subprocess, "Popen", forbidden_call)
    monkeypatch.setattr(os, "system", forbidden_call)
    monkeypatch.setattr(os, "popen", forbidden_call)

    rendered = launchagent.render_launchagent_plist()
    preflight = launchagent.preflight_payload(home=tmp_path)
    dry_run = launchagent.install_dry_run_payload(home=tmp_path)
    refused = launchagent.refused_install_payload(home=tmp_path)

    assert b"launchctl" not in rendered
    assert preflight["activation_allowed"] is False
    assert dry_run["activation_allowed"] is False
    assert refused["activation_allowed"] is False
    assert calls == []


def test_parse_launchagent_plist_rejects_non_dict(tmp_path):
    from etzchaim.supervision import launchagent

    path = Path(tmp_path) / "bad.plist"
    path.write_bytes(plistlib.dumps(["not", "a", "dict"]))

    try:
        launchagent.parse_launchagent_plist(path)
    except ValueError as exc:
        assert "must contain a dict" in str(exc)
    else:
        raise AssertionError("expected non-dict plist to be refused")
