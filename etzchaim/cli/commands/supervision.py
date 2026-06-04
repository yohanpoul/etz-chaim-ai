"""etzchaim supervision - Phase 3C controlled macOS supervision surface."""

from __future__ import annotations

import json as _json
from pathlib import Path
from typing import Literal

import typer

from etzchaim.cli.app import app
from etzchaim.supervision import launchagent, launchctl

WRITE_ACK_DISABLED = "WRITE PHASE 3C DISABLED PLIST"
WRITE_ACK_ENABLED = "WRITE PHASE 3C ENABLED PLIST FOR BOOTSTRAP"
LAUNCHCTL_ACKS = {
    "bootstrap": "BOOTSTRAP PHASE 3C LAUNCHAGENT",
    "kickstart": "KICKSTART PHASE 3C LOOP ONCE",
    "bootout": "BOOTOUT PHASE 3C LAUNCHAGENT",
    "disable": "DISABLE PHASE 3C LAUNCHAGENT",
    "enable": "ENABLE PHASE 3C LAUNCHAGENT",
}


def _emit_payload(payload: dict[str, object], *, json: bool) -> None:
    if json:
        typer.echo(_json.dumps(payload, indent=2))
        return

    typer.echo(f"status: {payload['status']}")
    typer.echo(f"phase: {payload['phase']}")
    typer.echo(f"mode: {payload['mode']}")
    message = payload.get("message")
    if message:
        typer.echo(f"message: {message}")


def _error_payload(message: str, *, mode: str = "invalid") -> dict[str, object]:
    return {
        "status": "error",
        "phase": "3C",
        "mode": mode,
        "message": message,
        "read_only": True,
        "real_install_allowed": False,
        "activation_allowed": False,
    }


def _refusal_payload(message: str, *, mode: str) -> dict[str, object]:
    return {
        "status": "refused",
        "phase": "3C",
        "mode": mode,
        "message": message,
        "read_only": True,
        "real_install_allowed": False,
        "activation_allowed": False,
    }


def _plist_disabled(plist_state: str) -> bool:
    return plist_state != "enabled"


def _expected_write_ack(disabled: bool) -> str:
    return WRITE_ACK_DISABLED if disabled else WRITE_ACK_ENABLED


def _plist_status() -> dict[str, object]:
    path = launchagent.default_launchagent_path()
    payload: dict[str, object] = {
        "path": str(path),
        "exists": path.exists(),
        "valid": False,
        "errors": [],
    }
    if path.exists():
        try:
            data = launchagent.parse_launchagent_plist(path)
            errors = launchagent.validate_launchagent_payload(data)
            payload["valid"] = not errors
            payload["errors"] = errors
        except Exception as exc:
            payload["errors"] = [str(exc)]
    return payload


def _launchctl_command_for(mode: str) -> list[str]:
    plist_path = launchagent.default_launchagent_path()
    if mode == "status":
        return launchctl.print_command()
    if mode == "bootstrap":
        return launchctl.bootstrap_command(plist_path)
    if mode == "kickstart":
        return launchctl.kickstart_command()
    if mode == "bootout":
        return launchctl.bootout_command()
    if mode == "disable":
        return launchctl.disable_command()
    if mode == "enable":
        return launchctl.enable_command()
    raise ValueError(f"Unsupported launchctl mode: {mode}")


def _launchctl_payload(mode: str, *, dry_run: bool) -> dict[str, object]:
    plist = _plist_status()
    command = _launchctl_command_for(mode)
    return {
        "status": "dry-run" if dry_run else "planned",
        "phase": "3C",
        "mode": mode,
        "read_only": dry_run,
        "real_install_allowed": False,
        "activation_allowed": False,
        "plist": plist,
        "command": command,
    }


@app.command()
def supervision(
    preflight: bool = typer.Option(
        False,
        "--preflight",
        help="Print read-only supervision status.",
    ),
    status: bool = typer.Option(
        False,
        "--status",
        help="Inspect LaunchAgent status.",
    ),
    install: bool = typer.Option(
        False,
        "--install",
        help="Show or write the LaunchAgent plist.",
    ),
    bootstrap: bool = typer.Option(
        False,
        "--bootstrap",
        help="Plan or run launchctl bootstrap.",
    ),
    kickstart: bool = typer.Option(
        False,
        "--kickstart",
        help="Plan or run one launchctl kickstart.",
    ),
    bootout: bool = typer.Option(
        False,
        "--bootout",
        help="Plan or run launchctl bootout.",
    ),
    disable: bool = typer.Option(
        False,
        "--disable",
        help="Plan or run launchctl disable.",
    ),
    enable: bool = typer.Option(
        False,
        "--enable",
        help="Plan or run launchctl enable after a guarded rollback disable.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show planned action without writing files or running launchctl.",
    ),
    write: bool = typer.Option(
        False,
        "--write",
        help="Write the LaunchAgent plist when explicitly confirmed.",
    ),
    allow_real_write: bool = typer.Option(
        False,
        "--allow-real-write",
        help="Allow a real plist write when paired with exact --ack.",
    ),
    allow_real_launchctl: bool = typer.Option(
        False,
        "--allow-real-launchctl",
        help="Allow launchctl execution when paired with exact --ack.",
    ),
    ack: str | None = typer.Option(
        None,
        "--ack",
        help="Exact acknowledgement phrase for guarded operations.",
    ),
    plist_state: Literal["disabled", "enabled"] = typer.Option(
        "disabled",
        "--plist-state",
        help="Plist Disabled state for write/dry-run.",
    ),
    json: bool = typer.Option(False, "--json", help="Structured JSON output."),
) -> None:
    """Inspect or prepare the controlled Phase 3C supervision surface."""

    modes = {
        "preflight": preflight,
        "status": status,
        "install": install,
        "bootstrap": bootstrap,
        "kickstart": kickstart,
        "bootout": bootout,
        "disable": disable,
        "enable": enable,
    }
    selected = [name for name, enabled in modes.items() if enabled]

    if len(selected) != 1:
        payload = _error_payload(
            "Choose exactly one mode: --preflight, --status, --install, --bootstrap, "
            "--kickstart, --bootout, --disable, or --enable.",
        )
        _emit_payload(payload, json=json)
        raise typer.Exit(1)

    if dry_run and (write or allow_real_write or allow_real_launchctl):
        payload = _error_payload(
            "--dry-run cannot be combined with --write or real allow flags.",
        )
        _emit_payload(payload, json=json)
        raise typer.Exit(1)

    mode = selected[0]

    if mode == "preflight":
        _emit_payload(launchagent.preflight_payload(), json=json)
        return

    if mode == "install":
        disabled = _plist_disabled(plist_state)
        if dry_run:
            _emit_payload(launchagent.install_dry_run_payload(disabled=disabled), json=json)
            return
        if not write:
            _emit_payload(
                _refusal_payload(
                    "Use --dry-run or guarded --write for Phase 3C plist installation.",
                    mode="install-refused",
                ),
                json=json,
            )
            raise typer.Exit(1)
        if not allow_real_write or ack != _expected_write_ack(disabled):
            _emit_payload(
                _refusal_payload(
                    "Real plist write requires --allow-real-write and exact --ack.",
                    mode="write-refused",
                ),
                json=json,
            )
            raise typer.Exit(1)
        written = launchagent.write_launchagent_plist(home=Path.home(), disabled=disabled)
        _emit_payload(
            {
                "status": "written",
                "phase": "3C",
                "mode": "install-write",
                "read_only": False,
                "real_install_allowed": True,
                "activation_allowed": False,
                "written": written,
                "template": launchagent.install_dry_run_payload(disabled=disabled)["template"],
            },
            json=json,
        )
        return

    if mode == "status":
        payload = _launchctl_payload(mode, dry_run=dry_run)
        if dry_run:
            _emit_payload(payload, json=json)
            return
        result = launchctl.run_launchctl(payload["command"])  # type: ignore[arg-type]
        payload["status"] = "completed"
        payload["read_only"] = True
        payload["result"] = result
        _emit_payload(payload, json=json)
        raise typer.Exit(int(result["returncode"]))

    payload = _launchctl_payload(mode, dry_run=dry_run)
    if dry_run:
        _emit_payload(payload, json=json)
        return

    if not payload["plist"]["exists"] or not payload["plist"]["valid"]:  # type: ignore[index]
        _emit_payload(
            _refusal_payload(
                "LaunchAgent plist must exist and validate before launchctl execution.",
                mode=f"{mode}-refused",
            ),
            json=json,
        )
        raise typer.Exit(1)

    if not allow_real_launchctl or ack != LAUNCHCTL_ACKS[mode]:
        _emit_payload(
            _refusal_payload(
                "Real launchctl action requires --allow-real-launchctl and exact --ack.",
                mode=f"{mode}-refused",
            ),
            json=json,
        )
        raise typer.Exit(1)

    result = launchctl.run_launchctl(payload["command"], allow_mutation=True)  # type: ignore[arg-type]
    payload["status"] = "completed"
    payload["read_only"] = False
    payload["activation_allowed"] = True
    payload["result"] = result
    _emit_payload(payload, json=json)
    raise typer.Exit(int(result["returncode"]))
