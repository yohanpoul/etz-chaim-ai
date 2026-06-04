"""etzchaim supervision - read-only Phase 3B macOS supervision surface."""

from __future__ import annotations

import json as _json

import typer

from etzchaim.cli.app import app
from etzchaim.supervision import launchagent


def _emit_payload(payload: dict[str, object], *, json: bool) -> None:
    if json:
        typer.echo(_json.dumps(payload, indent=2))
        return

    typer.echo(f"status: {payload['status']}")
    typer.echo(f"phase: {payload['phase']}")
    typer.echo(f"mode: {payload['mode']}")
    message = payload.get("message")
    if message:
        typer.echo(f"message: {message}")


@app.command()
def supervision(
    preflight: bool = typer.Option(
        False,
        "--preflight",
        help="Print read-only supervision status.",
    ),
    install: bool = typer.Option(
        False,
        "--install",
        help="Show or refuse LaunchAgent installation.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show planned installation without writing files.",
    ),
    json: bool = typer.Option(False, "--json", help="Structured JSON output."),
) -> None:
    """Inspect the dormant Phase 3B supervision surface."""

    if sum([preflight, install]) != 1:
        payload = {
            "status": "error",
            "phase": "3B",
            "mode": "invalid",
            "message": "Choose exactly one mode: --preflight or --install.",
            "read_only": True,
            "real_install_allowed": False,
            "activation_allowed": False,
        }
        _emit_payload(payload, json=json)
        raise typer.Exit(1)

    if preflight:
        _emit_payload(launchagent.preflight_payload(), json=json)
        return

    if dry_run:
        _emit_payload(launchagent.install_dry_run_payload(), json=json)
        return

    _emit_payload(launchagent.refused_install_payload(), json=json)
    raise typer.Exit(1)
