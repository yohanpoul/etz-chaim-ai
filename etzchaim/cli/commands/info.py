"""etzchaim info — print system info (Python, OS, Docker runtime, deps)."""
from __future__ import annotations

import json as _json
import platform
import shutil
import sys

import typer

from etzchaim import __version__
from etzchaim.cli.app import app


def _gather_info() -> dict:
    return {
        "etzchaim_version": __version__,
        "os": platform.system(),
        "os_release": platform.release(),
        "arch": platform.machine(),
        "python": sys.version.split()[0],
        "docker": shutil.which("docker") or None,
        "psql": shutil.which("psql") or None,
        "ollama": shutil.which("ollama") or None,
        "claude": shutil.which("claude") or None,
    }


@app.command()
def info(
    json: bool = typer.Option(False, "--json", help="Structured JSON output."),
) -> None:
    """Print system info : OS, Python, Docker runtime, tool availability."""
    data = _gather_info()
    if json:
        typer.echo(_json.dumps(data, indent=2))
        return

    typer.echo(f"etzchaim {data['etzchaim_version']}")
    typer.echo(f"  OS          : {data['os']} {data['os_release']} ({data['arch']})")
    typer.echo(f"  Python      : {data['python']}")
    typer.echo(f"  Docker      : {data['docker'] or 'MISSING (install Docker Desktop or OrbStack)'}")
    typer.echo(f"  psql        : {data['psql'] or 'missing (optional, used by tests)'}")
    typer.echo(f"  ollama      : {data['ollama'] or 'missing (required for local models + embeddings)'}")
    typer.echo(f"  claude CLI  : {data['claude'] or 'missing (optional, SDK used if ANTHROPIC_API_KEY set)'}")
