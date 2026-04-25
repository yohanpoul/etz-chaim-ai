"""etzchaim doctor — run MVP diagnostic checks."""
from __future__ import annotations

import json as _json

import typer

from etzchaim.cli.app import app
from etzchaim.cli.doctor.checks import CHECKS


@app.command()
def doctor(
    json: bool = typer.Option(False, "--json", help="Structured JSON output."),
) -> None:
    """Run diagnostic checks. Exits 1 if any fail."""
    results = []
    n_fail = 0
    for name, fn in CHECKS:
        try:
            ok, msg = fn()
        except Exception as e:
            ok, msg = False, f"check raised {type(e).__name__}: {e}"
        results.append({"name": name, "ok": ok, "message": msg})
        if not ok:
            n_fail += 1

    if json:
        typer.echo(_json.dumps({"checks": results, "n_fail": n_fail}, indent=2))
    else:
        typer.echo("Running diagnostic checks...")
        typer.echo("")
        for r in results:
            mark = "✓" if r["ok"] else "✗"
            typer.echo(f"  {mark} {r['name']} — {r['message']}")
        typer.echo("")
        if n_fail == 0:
            typer.echo(f"✓ All {len(results)} checks passed.")
        else:
            typer.echo(f"✗ {n_fail}/{len(results)} checks failed. See messages above.")

    if n_fail > 0:
        raise typer.Exit(1)
