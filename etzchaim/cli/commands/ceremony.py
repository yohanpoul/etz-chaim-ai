"""etzchaim ceremony — dev preview of the birth ceremony."""
from __future__ import annotations

import shutil

import typer

from etzchaim.cli.app import app
from etzchaim.cli.ceremony import play_ceremony


@app.command()
def ceremony(
    preview: bool = typer.Option(
        False, "--preview", help="Play the ceremony in isolation (no .env write).",
    ),
) -> None:
    """Developer helper — re-run the birth ceremony for iteration / demos."""
    if not preview:
        typer.echo("Use --preview to re-run the ceremony outside of onboard.", err=True)
        raise typer.Exit(2)

    cols = shutil.get_terminal_size((80, 24)).columns
    result = play_ceremony(width=cols)
    typer.echo("")
    typer.echo(f"  ◉ {result.shem} — preview complete")
    typer.echo(f"  birthtime : {result.birthtime.isoformat(timespec='seconds')}")
    typer.echo("  (nothing was written — this is a preview.)")
