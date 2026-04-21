"""End-to-end: onboard in --non-interactive runs compact ceremony + writes env keys."""
from __future__ import annotations

import re


def test_onboard_non_interactive_writes_shem_and_birthtime(monkeypatch, tmp_path):
    """--non-interactive must produce compact ceremony + valid .env with both keys."""
    monkeypatch.setenv("ETZCHAIM_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("CI", "true")

    from etzchaim.cli import compose, detect, installers
    monkeypatch.setattr(detect, "detect_os", lambda: "darwin")
    monkeypatch.setattr(detect, "detect_docker_runtime", lambda: "docker")
    monkeypatch.setattr(detect, "detect_compose_profile", lambda: "docker")
    monkeypatch.setattr(detect, "docker_is_running", lambda: True)
    monkeypatch.setattr(compose, "extract_compose_files", lambda: None)
    monkeypatch.setattr(compose, "compose_up", lambda profile=None: 0)
    monkeypatch.setattr(installers, "install_ollama",
                        lambda non_interactive, yes, pull_models: True)

    from typer.testing import CliRunner

    from etzchaim.cli.app import app
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["onboard", "--non-interactive", "--preset", "local-only", "--no-browser"],
    )
    assert result.exit_code == 0, result.stdout

    env_path = tmp_path / "compose" / ".env"
    assert env_path.exists()
    content = env_path.read_text()
    assert re.search(r"^ETZCHAIM_SHEM=Etz Chaim$", content, re.MULTILINE)
    assert re.search(r"^ETZCHAIM_BIRTHTIME=\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
                     content, re.MULTILINE)


def test_onboard_no_ceremony_flag_skips_animation(monkeypatch, tmp_path):
    """--no-ceremony flag routes to play_compact."""
    monkeypatch.setenv("ETZCHAIM_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("CI", "true")

    from etzchaim.cli import compose, detect, installers
    monkeypatch.setattr(detect, "detect_os", lambda: "darwin")
    monkeypatch.setattr(detect, "detect_docker_runtime", lambda: "docker")
    monkeypatch.setattr(detect, "detect_compose_profile", lambda: "docker")
    monkeypatch.setattr(detect, "docker_is_running", lambda: True)
    monkeypatch.setattr(compose, "extract_compose_files", lambda: None)
    monkeypatch.setattr(compose, "compose_up", lambda profile=None: 0)
    monkeypatch.setattr(installers, "install_ollama",
                        lambda non_interactive, yes, pull_models: True)

    from etzchaim.cli import ceremony as _cer
    called = {"n": 0}
    real_compact = _cer.play_compact

    def _spy_compact():
        called["n"] += 1
        return real_compact()

    monkeypatch.setattr(_cer, "play_compact", _spy_compact)

    from typer.testing import CliRunner

    from etzchaim.cli.app import app
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["onboard", "--non-interactive", "--preset", "local-only",
         "--no-browser", "--no-ceremony"],
    )
    assert result.exit_code == 0, result.stdout
    assert called["n"] >= 1
