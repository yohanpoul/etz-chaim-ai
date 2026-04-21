"""etzchaim version — print package version."""
from __future__ import annotations

import json as _json

import typer

from etzchaim import __version__
from etzchaim.cli.app import app


@app.command()
def version(
    json: bool = typer.Option(False, "--json", help="Structured JSON output for scripts."),
) -> None:
    """Print etzchaim version."""
    if json:
        typer.echo(_json.dumps({"name": "etzchaim", "version": __version__}))
    else:
        typer.echo(f"etzchaim {__version__}")
