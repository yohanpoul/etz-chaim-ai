"""etzchaim — top-level Typer app.

Commands are registered lazily via module imports below. Each command module
calls @app.command() on this `app` instance.

Keeping imports ordered : all command modules must import AFTER the `app =
typer.Typer(...)` line to avoid circular-import on first call.
"""
from __future__ import annotations

import typer

from etzchaim import __version__

app = typer.Typer(
    name="etzchaim",
    help="Etz Chaim AI — install and operate. Run `etzchaim onboard` to start.",
    no_args_is_help=True,
    add_completion=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"etzchaim {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show etzchaim version and exit.",
    ),
) -> None:
    """Root callback — only here to register --version."""
    return None


# Lazy registration — each import runs @app.command() decorators.
# Order doesn't matter functionally, kept alphabetical for readability.
from etzchaim.cli.commands import claude_bridge as _claude_bridge_cmd  # noqa: E402, F401
from etzchaim.cli.commands import demo as _demo_cmd  # noqa: E402, F401
from etzchaim.cli.commands import doctor as _doctor_cmd  # noqa: E402, F401
from etzchaim.cli.commands import info as _info_cmd  # noqa: E402, F401
from etzchaim.cli.commands import logs as _logs_cmd  # noqa: E402, F401
from etzchaim.cli.commands import onboard as _onboard_cmd  # noqa: E402, F401
from etzchaim.cli.commands import open as _open_cmd  # noqa: E402, F401
from etzchaim.cli.commands import start as _start_cmd  # noqa: E402, F401
from etzchaim.cli.commands import status as _status_cmd  # noqa: E402, F401
from etzchaim.cli.commands import stop as _stop_cmd  # noqa: E402, F401
from etzchaim.cli.commands import update as _update_cmd  # noqa: E402, F401
from etzchaim.cli.commands import version as _version_cmd  # noqa: E402, F401


if __name__ == "__main__":
    app()
