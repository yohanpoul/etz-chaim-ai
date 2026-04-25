"""etzchaim open — launch the dashboard in the default browser.

Reads the configured WEB_PORT + ETZ_CHAIM_API_KEY from the .env generated
by `etzchaim onboard`. Useful when you forgot where the dashboard is, or
want to display your API key again (openclaw-style access recovery).
"""
from __future__ import annotations

import typer

from etzchaim._paths import env_file
from etzchaim.cli.app import app


def _read_env_file() -> dict[str, str]:
    path = env_file()
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


@app.command()
def open(  # noqa: A001 — CLI subcommand, shadowing built-in is fine
    show_key: bool = typer.Option(
        True, "--show-key/--no-show-key",
        help="Display the API key in the terminal (default : on).",
    ),
    no_browser: bool = typer.Option(
        False, "--no-browser", help="Print URL only, don't launch the browser.",
    ),
) -> None:
    """Open the dashboard + display the API key.

    Exits 1 if no configuration is found (run `etzchaim onboard` first).
    """
    env = _read_env_file()
    if not env:
        typer.echo(
            f"✗ No .env found at {env_file()}. Run `etzchaim onboard` first.",
            err=True,
        )
        raise typer.Exit(1)

    # HOST_WEB_PORT is the host-facing mapping (what the browser hits).
    # WEB_PORT is the container-internal bind (always 8080), kept as fallback
    # only for legacy installs that pre-date the HOST_WEB_PORT split.
    web_port = env.get("HOST_WEB_PORT") or env.get("WEB_PORT", "8080")
    api_key = env.get("ETZ_CHAIM_API_KEY", "")
    allow_anon = env.get("ETZ_CHAIM_ALLOW_ANON", "0") == "1"

    url = f"http://localhost:{web_port}"
    typer.echo("")
    typer.echo(f"  Dashboard   : {url}")
    if show_key and api_key:
        typer.echo(f"  API key     : {api_key}")
    elif allow_anon:
        typer.echo("  Auth        : ETZ_CHAIM_ALLOW_ANON=1 — anonymous access enabled")
    else:
        typer.echo("  API key     : (hidden — rerun with --show-key)")
    typer.echo(f"  .env        : {env_file()}")
    typer.echo("")

    # Warn if a foreign (non-Docker) process is currently squatting the
    # canonical 8080 port — common pitfall when a `python main.py web` or a
    # launchd-managed dev instance is running alongside the Docker stack.
    try:
        from etzchaim.cli.port_helpers import is_etzchaim_container_port, who_listens_on
        if str(web_port) != "8080":
            holder_8080 = who_listens_on(8080)
            if holder_8080 and not is_etzchaim_container_port(8080):
                typer.echo(
                    f"  ⚠ Note      : :8080 is held by PID {holder_8080.pid} "
                    f"({holder_8080.command}). That is NOT your etzchaim "
                    f"dashboard — yours is on :{web_port}.",
                )
    except Exception:
        pass  # Diagnostics must never break `etzchaim open`.

    if no_browser:
        return

    try:
        import webbrowser
        webbrowser.open(url)
        typer.echo(f"  Opening {url} ...")
    except Exception as e:
        typer.echo(f"  Could not launch browser ({e}). Visit {url} manually.", err=True)
