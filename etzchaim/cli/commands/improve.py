"""etzchaim improve - safe Phase 1A metacognition surface."""

from __future__ import annotations

import json as _json
from pathlib import Path

import typer

from etzchaim.cli.app import app
from etzchaim.metacognition import report


@app.command()
def improve(
    once: bool = typer.Option(False, "--once", help="Run one safe local improve cycle."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print what would be written."),
    json: bool = typer.Option(False, "--json", help="Structured JSON output."),
) -> None:
    """Observe local weaknesses and propose non-applied remediation actions."""

    if not once:
        message = "Phase 1A only supports explicit --once."
        if json:
            typer.echo(_json.dumps({"status": "error", "message": message}, indent=2))
        else:
            typer.echo(message)
        raise typer.Exit(1)

    payload = report.run_improve_once(dry_run=dry_run, repo_root=Path.cwd())
    if json:
        typer.echo(_json.dumps(payload, indent=2))
        return

    typer.echo(f"status: {payload['status']}")
    typer.echo(f"dry_run: {payload['dry_run']}")
    if dry_run:
        typer.echo("would_write:")
        for key, value in payload["would_write"].items():
            typer.echo(f"  {key}: {value}")
    else:
        typer.echo("written:")
        for key, value in payload["written"].items():
            typer.echo(f"  {key}: {value}")
