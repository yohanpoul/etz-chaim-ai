"""Test etzchaim version + info commands (no Docker required)."""
from __future__ import annotations

import json
import sys

from typer.testing import CliRunner


def test_version_prints_package_version():
    from etzchaim.cli.app import app
    runner = CliRunner()
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "etzchaim" in result.stdout.lower()
    assert "0.2." in result.stdout


def test_version_json():
    from etzchaim.cli.app import app
    runner = CliRunner()
    result = runner.invoke(app, ["version", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["name"] == "etzchaim"
    assert data["version"].startswith("0.")


def test_info_prints_python_version():
    from etzchaim.cli.app import app
    runner = CliRunner()
    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0
    assert str(sys.version_info.major) in result.stdout


def test_info_json():
    from etzchaim.cli.app import app
    runner = CliRunner()
    result = runner.invoke(app, ["info", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "etzchaim_version" in data
    assert "os" in data
    assert "python" in data


def test_help_shows_all_commands():
    from etzchaim.cli.app import app
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ["version", "info", "onboard", "start", "stop", "status",
                "logs", "doctor", "demo", "update"]:
        assert cmd in result.stdout, f"Command '{cmd}' not listed in --help"
