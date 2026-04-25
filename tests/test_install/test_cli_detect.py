"""Test etzchaim.cli.detect helpers."""
from __future__ import annotations

from unittest.mock import patch


def test_detect_os_returns_known():
    from etzchaim.cli.detect import detect_os
    result = detect_os()
    assert result in ("macos", "linux", "windows", "unknown")


def test_detect_compose_profile_macos():
    with patch("platform.system", return_value="Darwin"):
        from etzchaim.cli.detect import detect_compose_profile
        assert detect_compose_profile() == "hybrid-host-ollama"


def test_detect_compose_profile_linux_cpu(monkeypatch):
    with patch("platform.system", return_value="Linux"):
        monkeypatch.setattr("shutil.which", lambda c: None)
        with patch("pathlib.Path.exists", return_value=False):
            from etzchaim.cli.detect import detect_compose_profile
            assert detect_compose_profile() == "full-cpu"


def test_detect_compose_profile_linux_nvidia(monkeypatch):
    def fake_which(c):
        return "/usr/bin/nvidia-smi" if c == "nvidia-smi" else None
    with patch("platform.system", return_value="Linux"):
        monkeypatch.setattr("shutil.which", fake_which)
        from etzchaim.cli.detect import detect_compose_profile
        assert detect_compose_profile() == "full-nvidia"


def test_docker_is_running_false_when_not_installed(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda c: None)
    from etzchaim.cli.detect import docker_is_running
    assert docker_is_running() is False


def test_detect_docker_runtime_none_when_missing(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda c: None)
    # Also stub the macOS /Applications/ fallback so the test is hermetic
    # regardless of what's installed on the host running pytest.
    monkeypatch.setattr("etzchaim.cli.detect.platform.system", lambda: "Linux")
    from etzchaim.cli.detect import detect_docker_runtime
    assert detect_docker_runtime() is None


def test_detect_docker_runtime_orbstack(monkeypatch):
    def fake_which(c):
        return "/Applications/OrbStack.app/Contents/MacOS/xbin/docker" if c == "docker" else None
    monkeypatch.setattr("shutil.which", fake_which)
    from etzchaim.cli.detect import detect_docker_runtime
    assert detect_docker_runtime() == "orbstack"
