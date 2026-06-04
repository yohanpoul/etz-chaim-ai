"""etzchaim loop - manual non-permanent Phase 3A runtime loop."""

from __future__ import annotations

import json as _json
from pathlib import Path

import typer

from etzchaim.cli.app import app
from etzchaim.metacognition import runtime_loop


def _echo_paths(paths: dict, indent: str = "  ") -> None:
    for key, value in paths.items():
        if isinstance(value, dict):
            typer.echo(f"{indent}{key}:")
            _echo_paths(value, indent=f"{indent}  ")
        else:
            typer.echo(f"{indent}{key}: {value}")


@app.command()
def loop(
    once: bool = typer.Option(False, "--once", help="Run one bounded loop cycle."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print what would be written."),
    json: bool = typer.Option(False, "--json", help="Structured JSON output."),
) -> None:
    """Run one non-permanent local runtime loop cycle."""

    if not once:
        message = "Phase 3A loop only supports explicit --once."
        if json:
            typer.echo(_json.dumps({"status": "error", "message": message}, indent=2))
        else:
            typer.echo(message)
        raise typer.Exit(1)

    payload = runtime_loop.run_loop_once(dry_run=dry_run, repo_root=Path.cwd())
    if json:
        typer.echo(_json.dumps(payload, indent=2))
        return

    typer.echo(f"status: {payload['status']}")
    typer.echo(f"dry_run: {payload['dry_run']}")
    typer.echo(f"cycle_id: {payload['cycle_id']}")
    typer.echo(f"improve_status: {payload['improve']['status']}")
    if dry_run:
        typer.echo("would_write:")
        _echo_paths(payload["would_write"])
    else:
        typer.echo("written:")
        _echo_paths(payload["written"])
