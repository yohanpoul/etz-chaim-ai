"""etzchaim status — print services health + daemon + providers snapshot."""
from __future__ import annotations

import json as _json

import typer

from etzchaim.cli import compose, detect
from etzchaim.cli.app import app


@app.command()
def status(
    json: bool = typer.Option(False, "--json", help="Structured JSON output."),
    profile: str = typer.Option(None, "--profile", help="Compose profile override."),
) -> None:
    """Print status of services, daemon, and providers."""
    p = profile or detect.detect_compose_profile()

    services: list[dict] = []
    if compose.compose_dir().exists():
        try:
            raw = compose.compose_ps(profile=p).strip()
            if raw:
                # docker compose ps --format json outputs one JSON object per line (newer versions)
                # or a single JSON array. Handle both.
                if raw.startswith("["):
                    services = _json.loads(raw)
                else:
                    services = [_json.loads(line) for line in raw.splitlines() if line.strip()]
        except Exception as e:
            if json:
                typer.echo(_json.dumps({"error": str(e), "services": []}))
            else:
                typer.echo(f"⚠ Could not parse compose status : {e}", err=True)
            return

    if json:
        typer.echo(_json.dumps({"profile": p, "services": services}, indent=2))
        return

    typer.echo(f"Etz Chaim AI — status (profile: {p})")
    typer.echo("")
    typer.echo("Services :")
    if not services:
        typer.echo("  (none running — run `etzchaim start` to launch)")
        return
    for svc in services:
        name = svc.get("Service", svc.get("Name", "?"))
        state = svc.get("State", "?")
        health = svc.get("Health", "")
        if health == "healthy":
            marker = "✓"
        elif state == "running":
            marker = "⚠"
        else:
            marker = "✗"
        health_str = f" · {health}" if health else ""
        typer.echo(f"  {marker} {name} ({state}{health_str})")
