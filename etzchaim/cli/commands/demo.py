"""etzchaim demo — load seed data + print 5-act walkthrough."""
from __future__ import annotations

import typer

from etzchaim.cli.app import app


@app.command()
def demo(
    seed_only: bool = typer.Option(False, "--seed", help="Only load seed data, no walkthrough print."),
) -> None:
    """Load demo data into the running install and print a 5-act walkthrough."""
    from etzchaim.demo_data.load import load_seed
    typer.echo("Loading demo seed data...")
    rc = load_seed()
    if rc != 0:
        typer.echo(f"✗ Failed to load seed (rc={rc}). Ensure `etzchaim start` succeeded first.", err=True)
        raise typer.Exit(rc)
    typer.echo("✓ Demo data loaded.")
    if seed_only:
        return

    typer.echo("")
    typer.echo("═══════════════════════════════════════════════════════════")
    typer.echo("  Etz Chaim AI — Demo walkthrough (5 acts)")
    typer.echo("═══════════════════════════════════════════════════════════")
    typer.echo("")
    typer.echo("  [1/5] 5 concepts loaded in epistememory (Yesod, persistent memory)")
    typer.echo("  [2/5] 1 dialectical tension in dissensuengine (Tiferet, productive tension)")
    typer.echo("  [3/5] Web dashboard : http://localhost:8080")
    typer.echo("  [4/5] API modules status :")
    typer.echo("        curl -H 'Authorization: Bearer $ETZ_CHAIM_API_KEY' \\")
    typer.echo("          http://localhost:8080/api/modules/status")
    typer.echo("  [5/5] Explore the CLI :")
    typer.echo("        etzchaim --help    · list all commands")
    typer.echo("        etzchaim doctor    · run diagnostic checks")
    typer.echo("        etzchaim status    · services health snapshot")
    typer.echo("        etzchaim logs -f   · follow daemon logs")
    typer.echo("")
