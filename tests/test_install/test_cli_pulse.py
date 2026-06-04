from __future__ import annotations

import json

from typer.testing import CliRunner


def test_pulse_help_works():
    from etzchaim.cli.app import app

    runner = CliRunner()
    result = runner.invoke(app, ["pulse", "--help"])

    assert result.exit_code == 0
    assert "--run-loop" in result.stdout
    assert "--write-vault" in result.stdout
    assert "--vault-dir" in result.stdout
    assert "--codex-smoke" in result.stdout


def test_pulse_dry_run_json_does_not_write_vault(monkeypatch, tmp_path):
    from etzchaim.cli.app import app
    from etzchaim.cli.commands import pulse as pulse_command

    vault_dir = tmp_path / "vault" / "00-system" / "operator-kernel"

    monkeypatch.setattr(
        pulse_command.operator_bridge,
        "build_pulse_payload",
        lambda **kwargs: {
            "status": "ready",
            "generated_at": "2026-06-04T21:05:00Z",
            "repo_root": str(tmp_path),
            "provider": {"active_profile": "codex_cli", "uses_api_key": False, "codex_cli_configured": True},
            "codex": {"status": "ok", "path": "/bin/codex", "version": "codex-cli 0.128.0"},
            "loop": {"cycle_id": "loop-20260604T210000Z"},
            "work_packet": {"id": "work-packet-loop-20260604T210000Z"},
            "vault": {"dir": str(vault_dir)},
        },
    )
    monkeypatch.setattr(
        pulse_command.operator_bridge,
        "codex_cli_status",
        lambda *args, **kwargs: {"status": "ok", "path": "/bin/codex", "version": "codex-cli 0.128.0"},
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["pulse", "--dry-run", "--vault-dir", str(vault_dir), "--json"],
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["status"] == "ready"
    assert data["provider"]["active_profile"] == "codex_cli"
    assert data["provider"]["uses_api_key"] is False
    assert not vault_dir.exists()


def test_pulse_write_vault_calls_writer(monkeypatch, tmp_path):
    from etzchaim.cli.app import app
    from etzchaim.cli.commands import pulse as pulse_command

    vault_dir = tmp_path / "vault" / "00-system" / "operator-kernel"
    written = {}

    payload = {
        "status": "ready",
        "generated_at": "2026-06-04T21:05:00Z",
        "repo_root": str(tmp_path),
        "provider": {"active_profile": "codex_cli", "uses_api_key": False, "codex_cli_configured": True},
        "codex": {"status": "ok", "path": "/bin/codex", "version": "codex-cli 0.128.0"},
        "loop": {"cycle_id": "loop-20260604T210000Z"},
        "work_packet": {"id": "work-packet-loop-20260604T210000Z"},
        "vault": {"dir": str(vault_dir)},
    }

    monkeypatch.setattr(pulse_command.operator_bridge, "build_pulse_payload", lambda **kwargs: payload)
    monkeypatch.setattr(
        pulse_command.operator_bridge,
        "codex_cli_status",
        lambda *args, **kwargs: {"status": "ok", "path": "/bin/codex", "version": "codex-cli 0.128.0"},
    )

    def fake_writer(payload_arg):
        written["payload"] = payload_arg
        return {
            "index": str(vault_dir / "index.md"),
            "pulse": str(vault_dir / "pulses" / "pulse.md"),
            "work_packet": str(vault_dir / "work-packets" / "packet.md"),
            "agents": str(vault_dir / "AGENTS.md"),
        }

    monkeypatch.setattr(pulse_command.operator_bridge, "write_vault_pulse", fake_writer)

    runner = CliRunner()
    result = runner.invoke(app, ["pulse", "--write-vault", "--vault-dir", str(vault_dir), "--json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["written"]["index"].endswith("index.md")
    assert written["payload"] is payload
