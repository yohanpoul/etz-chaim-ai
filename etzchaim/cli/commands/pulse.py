"""etzchaim pulse — Operator Bridge cockpit command."""
# ruff: noqa: B008
from __future__ import annotations

import json as _json
from pathlib import Path

import typer

from etzchaim import operator_bridge
from etzchaim.cli.app import app


def _emit_text(payload: dict) -> None:
    provider = payload.get("provider", {})
    codex = payload.get("codex", {})
    loop = payload.get("loop", {})
    packet = payload.get("work_packet", {})
    typer.echo(f"status: {payload.get('status')}")
    typer.echo(f"generated_at: {payload.get('generated_at')}")
    typer.echo(f"repo_root: {payload.get('repo_root')}")
    typer.echo(f"active_profile: {provider.get('active_profile')}")
    typer.echo(f"codex_cli_configured: {provider.get('codex_cli_configured')}")
    typer.echo(f"uses_api_key: {provider.get('uses_api_key')}")
    typer.echo(f"codex_status: {codex.get('status')}")
    typer.echo(f"codex_version: {codex.get('version')}")
    typer.echo(f"cycle_id: {loop.get('cycle_id')}")
    typer.echo(f"work_packet: {packet.get('id')}")
    if payload.get("written"):
        typer.echo("written:")
        for key, value in payload["written"].items():
            typer.echo(f"  {key}: {value}")


@app.command()
def pulse(
    run_loop: bool = typer.Option(
        False,
        "--run-loop",
        help="Run one bounded loop cycle before building the pulse.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Do not write loop state or vault files; show planned payload only.",
    ),
    write_vault: bool = typer.Option(
        False,
        "--write-vault",
        help="Write/update the Obsidian Operator Kernel cockpit.",
    ),
    vault_dir: Path | None = typer.Option(
        None,
        "--vault-dir",
        help="Obsidian cockpit directory. Defaults to $ETZCHAIM_OPERATOR_VAULT_DIR or ~/Documents/mon-cerveau/00-system/operator-kernel.",
    ),
    repo_root: Path = typer.Option(
        Path.cwd(),
        "--repo-root",
        help="Repo root observed by the loop and included in work packets.",
    ),
    config_path: Path | None = typer.Option(
        None,
        "--config-path",
        help="Provider config path. Defaults to repo_root/config.yaml when available.",
    ),
    codex_smoke: bool = typer.Option(
        False,
        "--codex-smoke",
        help="Run one explicit Codex CLI read-only ephemeral smoke call.",
    ),
    codex_model: str = typer.Option(
        "gpt-5.5",
        "--codex-model",
        help="Model for --codex-smoke only.",
    ),
    json: bool = typer.Option(False, "--json", help="Structured JSON output."),
) -> None:
    """Build an operator-facing pulse from loop state + Codex CLI readiness."""

    loop_payload = None
    if run_loop:
        loop_payload = operator_bridge.run_loop_for_pulse(dry_run=dry_run, repo_root=repo_root)

    codex_status = operator_bridge.codex_cli_status(
        model=codex_model,
        smoke=codex_smoke,
        repo_root=repo_root,
    )
    payload = operator_bridge.build_pulse_payload(
        repo_root=repo_root,
        config_path=config_path,
        vault_dir=vault_dir,
        loop_payload=loop_payload,
        codex_status=codex_status,
    )

    if write_vault:
        if dry_run:
            payload["would_write_vault"] = {
                key: value
                for key, value in payload.get("vault", {}).items()
                if key in {"index", "pulse", "work_packet", "agents"}
            }
        else:
            payload["written"] = operator_bridge.write_vault_pulse(payload)

    if json:
        typer.echo(_json.dumps(payload, indent=2))
        return
    _emit_text(payload)
