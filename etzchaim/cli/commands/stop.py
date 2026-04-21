"""etzchaim stop — bring services down (volumes preserved)."""
from __future__ import annotations

import typer

from etzchaim.cli import compose, detect
from etzchaim.cli.app import app


@app.command()
def stop(
    profile: str = typer.Option(None, "--profile", help="Compose profile (auto-detected by default)."),
) -> None:
    """Stop Etz Chaim AI services. Volumes preserved — `etzchaim start` to resume."""
    if not compose.compose_dir().exists():
        typer.echo("Nothing to stop (no install found).", err=True)
        raise typer.Exit(0)
    p = profile or detect.detect_compose_profile()
    typer.echo("Stopping etzchaim...")
    rc = compose.compose_down(profile=p)
    if rc != 0:
        raise typer.Exit(rc)
    typer.echo("✓ Services stopped. Volumes preserved.")
