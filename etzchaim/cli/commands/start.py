"""etzchaim start — bring services up via docker compose."""
from __future__ import annotations

import typer

from etzchaim._paths import env_file
from etzchaim.cli import compose, detect
from etzchaim.cli.app import app


def _read_web_port() -> str:
    """Return the host-facing port the user opens in their browser.

    Priority: HOST_WEB_PORT (set by onboard) > WEB_PORT (legacy) > 8080.
    The bare `WEB_PORT` is the container-internal bind and is NOT what the
    user should hit on the host — reading it as a fallback only.
    """
    path = env_file()
    if not path.exists():
        return "8080"
    host_port: str | None = None
    legacy_port: str | None = None
    for line in path.read_text().splitlines():
        if line.startswith("HOST_WEB_PORT="):
            host_port = line.split("=", 1)[1].strip() or None
        elif line.startswith("WEB_PORT="):
            legacy_port = line.split("=", 1)[1].strip() or None
    return host_port or legacy_port or "8080"


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

    # Warn if a foreign (non-Docker) process is sitting on the canonical 8080
    # port while we listen elsewhere. Without this, users open :8080 by reflex
    # and stare at someone else's dashboard, wondering why everything is empty.
    try:
        from etzchaim.cli.port_helpers import is_etzchaim_container_port, who_listens_on
        if str(web_port) != "8080":
            holder = who_listens_on(8080)
            if holder and not is_etzchaim_container_port(8080):
                typer.echo(
                    f"  ⚠ Heads-up   : PID {holder.pid} ({holder.command}) "
                    f"is holding :8080. Use :{web_port} for your dashboard, "
                    f"NOT :8080.",
                )
    except Exception:
        pass

    typer.echo("  Health check : etzchaim status")
    typer.echo("  Open         : etzchaim open")
