from __future__ import annotations

import os
import plistlib
import subprocess


def test_rendered_launchagent_plist_is_valid_and_dormant():
    from etzchaim.supervision import launchagent

    rendered = launchagent.render_launchagent_plist()
    data = plistlib.loads(rendered)

    assert data["Label"] == "com.etzchaim.loop-once"
    assert data["ProgramArguments"] == ["etzchaim", "loop", "--once", "--json"]
    assert data["RunAtLoad"] is False
    assert data["KeepAlive"] is False
    assert data["Disabled"] is True
    assert "StartInterval" not in data
    assert "StartCalendarInterval" not in data
    assert "WatchPaths" not in data
    assert "QueueDirectories" not in data


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
