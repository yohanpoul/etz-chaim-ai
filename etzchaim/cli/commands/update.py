"""etzchaim update — one-command upgrade path for future releases.

Sequence :
  1. pipx upgrade etzchaim (or pip install --upgrade etzchaim if not pipx)
  2. docker compose pull                   (new images from ghcr.io)
  3. re-extract compose templates (force)  (preserves user edits with .bak)
  4. idempotent schema migrations          (re-run init-db/*.sql)
  5. restart services                      (compose down + up)
  6. run doctor                            (verify post-update health)

User data (PG volume, ~/.etz-chaim/state) never touched. Rollback :
`pipx install etzchaim==<old>` (or `pip install ...`) then `etzchaim update`.
"""
from __future__ import annotations

import shutil
import subprocess
import sys

import typer

from etzchaim import __version__
from etzchaim.cli import compose, detect
from etzchaim.cli.app import app


def _installed_via_pipx() -> bool:
    """True when the running interpreter lives inside a pipx-managed venv.

    pipx places venvs under ~/.local/pipx/venvs/<pkg>/ on POSIX or
    %LOCALAPPDATA%\\pipx\\pipx\\venvs\\<pkg>\\ on Windows. Detecting by
    path keeps us from having to import pipx itself.
    """
    return "pipx" in sys.executable.replace("\\", "/").split("/")


@app.command()
def update(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
    skip_images: bool = typer.Option(False, "--skip-images", help="Only pip upgrade, skip docker pull."),
    skip_restart: bool = typer.Option(False, "--skip-restart", help="No service restart after update."),
) -> None:
    """Upgrade etzchaim package + images + schemas in one command."""
    typer.echo(f"Current version : {__version__}")
    if not yes and not typer.confirm("Upgrade etzchaim ?"):
        typer.echo("Aborted.")
        raise typer.Exit(0)

    # 1. Package upgrade — pipx if installed via pipx, else pip
    if _installed_via_pipx() and shutil.which("pipx"):
        typer.echo("→ [1/5] Upgrading Python package via pipx...")
        rc = subprocess.run(["pipx", "upgrade", "etzchaim"], check=False).returncode
    else:
        typer.echo("→ [1/5] Upgrading Python package via pip...")
        rc = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "etzchaim"],
            check=False,
        ).returncode
    if rc != 0:
        typer.echo("✗ Package upgrade failed. See output above.", err=True)
        raise typer.Exit(rc)

    # 2. Re-extract compose templates
    typer.echo("→ [2/5] Extracting new compose templates...")
    compose.extract_compose_files(force=True)

    # 3-5 require Docker. If Docker isn't available, skip them with a
    # clear message so the package upgrade still succeeds — the user
    # can re-run `etzchaim update` once Docker is up.
    docker_available = detect.docker_is_running()
    if not docker_available:
        typer.echo(
            "⚠ Docker not running — skipping image pull, migrations, and restart.\n"
            "  Start Docker (OrbStack / Docker Desktop / Colima), then re-run `etzchaim update`."
        )
    else:
        # 3. Pull images
        profile = detect.detect_compose_profile()
        if not skip_images:
            typer.echo("→ [3/5] Pulling new Docker images...")
            rc = compose.compose_pull(profile=profile)
            if rc != 0:
                typer.echo("⚠ docker compose pull failed — restart may use cached images.", err=True)

        # 4. Schema migrations (MVP : re-run idempotent init-db SQL)
        typer.echo("→ [4/5] Applying schema migrations (idempotent)...")
        _apply_migrations()

        # 5. Restart
        if not skip_restart:
            typer.echo("→ [5/5] Restarting services...")
            compose.compose_down(profile=profile)
            compose.compose_up(profile=profile)

    typer.echo("")
    typer.echo("✓ Update complete. Running doctor...")
    typer.echo("")

    from etzchaim.cli.commands.doctor import doctor as _doctor_cmd
    try:
        _doctor_cmd(json=False)
    except typer.Exit as e:
        if e.exit_code != 0:
            typer.echo("⚠ Some post-update checks failed. See above.", err=True)
            raise


def _apply_migrations() -> None:
    """Re-run idempotent init-db/*.sql files (CREATE TABLE IF NOT EXISTS, etc.).

    Phase FULL will replace with versioned Alembic migrations.
    """
    init_db_dir = compose.compose_dir() / "init-db"
    if not init_db_dir.is_dir():
        typer.echo("    (no init-db/ directory, skipping)")
        return
    files = sorted(init_db_dir.glob("*.sql"))
    for sql_file in files:
        typer.echo(f"    applying {sql_file.name}...")
        cmd = [
            "docker", "compose",
            "exec", "-T", "postgres",
            "psql", "-U", "etz", "-d", "etz_chaim", "-q",
        ]
        with open(sql_file) as f:
            r = subprocess.run(
                cmd, cwd=str(compose.compose_dir()), stdin=f,
                capture_output=True, text=True,
            )
        if r.returncode != 0 and "already exists" not in r.stderr:
            typer.echo(f"    ⚠ {sql_file.name} : {r.stderr[:200]}", err=True)
