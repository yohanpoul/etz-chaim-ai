"""etzchaim logs — tail docker compose logs (optionally filtered by service)."""
from __future__ import annotations

import typer

from etzchaim.cli import compose, detect
from etzchaim.cli.app import app


@app.command()
def logs(
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output."),
    tail: int = typer.Option(100, "--tail", "-n", help="Lines per service to show."),
    service: str = typer.Option(None, "--service", "-s", help="Filter to one service (app, daemon, postgres)."),
    profile: str = typer.Option(None, "--profile", help="Compose profile override."),
) -> None:
    """Tail compose logs. Use --service to focus on one container."""
    if not compose.compose_dir().exists():
        typer.echo("✗ Compose not configured. Run `etzchaim onboard` first.", err=True)
        raise typer.Exit(1)
    p = profile or detect.detect_compose_profile()
    compose.compose_logs(follow=follow, tail=tail, service=service, profile=p)
