"""etzchaim start — bring services up via docker compose."""
from __future__ import annotations

import typer

from etzchaim._paths import env_file
from etzchaim.cli import compose, detect
from etzchaim.cli.app import app


def _read_web_port() -> str:
    path = env_file()
    if not path.exists():
        return "8080"
    for line in path.read_text().splitlines():
        if line.startswith("WEB_PORT="):
            return line.split("=", 1)[1].strip() or "8080"
    return "8080"


@app.command()
def start(
    profile: str = typer.Option(None, "--profile", help="Compose profile override (auto-detected by default)."),
) -> None:
    """Start Etz Chaim AI services (docker compose up -d).

    If ~/.etz-chaim/compose/ is missing, runs `etzchaim onboard` hint.
    """
    if not compose.compose_dir().exists():
        typer.echo("✗ Compose not configured. Run `etzchaim onboard` first.", err=True)
        raise typer.Exit(1)

    if not detect.docker_is_running():
        from etzchaim.cli import runtime as _rt
        if not _rt.ensure_docker_running(timeout=60.0):
            typer.echo("✗ Docker unavailable. Aborting start.", err=True)
            raise typer.Exit(1)

    p = profile or detect.detect_compose_profile()
    typer.echo(f"Starting etzchaim (profile: {p})...")
    rc = compose.compose_up(profile=p)
    if rc != 0:
        typer.echo("✗ Start failed. Check `etzchaim logs` for details.", err=True)
        raise typer.Exit(rc)

    web_port = _read_web_port()
    typer.echo("")
    typer.echo(f"✓ Services started. Dashboard : http://localhost:{web_port}")
    typer.echo("  Health check : etzchaim status")
    typer.echo("  Open         : etzchaim open")
