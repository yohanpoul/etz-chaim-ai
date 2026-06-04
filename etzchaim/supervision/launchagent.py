"""Dormant macOS LaunchAgent template for Phase 3B supervision."""

from __future__ import annotations

import plistlib
from pathlib import Path

LABEL = "com.etzchaim.loop-once"
PROGRAM_ARGUMENTS = ["etzchaim", "loop", "--once", "--json"]
PHASE = "3B"
REFUSAL_MESSAGE = "Phase 3B refuses real LaunchAgent installation. Use --dry-run only."


def default_launchagent_path(home: Path | None = None) -> Path:
    """Return the planned user LaunchAgent path without creating it."""

    root = home or Path.home()
    return root / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def launchagent_payload(executable: str = "etzchaim") -> dict[str, object]:
    """Return a dormant LaunchAgent payload for one bounded loop cycle."""

    return {
        "Label": LABEL,
        "ProgramArguments": [executable, *PROGRAM_ARGUMENTS[1:]],
        "RunAtLoad": False,
        "KeepAlive": False,
        "Disabled": True,
    }


def render_launchagent_plist(executable: str = "etzchaim") -> bytes:
    """Render the dormant LaunchAgent as XML plist bytes."""

    return plistlib.dumps(
        launchagent_payload(executable=executable),
        fmt=plistlib.FMT_XML,
        sort_keys=False,
    )


def _template_summary(executable: str = "etzchaim") -> dict[str, object]:
    payload = launchagent_payload(executable=executable)
    return {
        "label": payload["Label"],
        "program_arguments": payload["ProgramArguments"],
        "run_at_load": payload["RunAtLoad"],
        "keep_alive": payload["KeepAlive"],
        "disabled": payload["Disabled"],
        "active_intervals": [],
    }


def preflight_payload(home: Path | None = None) -> dict[str, object]:
    """Return read-only status for the dormant supervision surface."""

    target_path = default_launchagent_path(home=home)
    return {
        "status": "ok",
        "phase": PHASE,
        "mode": "preflight",
        "read_only": True,
        "real_install_allowed": False,
        "activation_allowed": False,
        "label": LABEL,
        "target": {
            "path": str(target_path),
            "exists": target_path.exists(),
        },
        "template": _template_summary(),
    }


def install_dry_run_payload(home: Path | None = None) -> dict[str, object]:
    """Return the planned plist write without writing any file."""

    target_path = default_launchagent_path(home=home)
    rendered = render_launchagent_plist()
    return {
        "status": "dry-run",
        "phase": PHASE,
        "mode": "install-dry-run",
        "read_only": True,
        "real_install_allowed": False,
        "activation_allowed": False,
        "label": LABEL,
        "target": {
            "path": str(target_path),
            "exists": target_path.exists(),
        },
        "template": _template_summary(),
        "would_write": {
            "path": str(target_path),
            "bytes": len(rendered),
            "plist": rendered.decode("utf-8"),
        },
    }


def refused_install_payload(home: Path | None = None) -> dict[str, object]:
    """Return the Phase 3B refusal payload for real installation attempts."""

    target_path = default_launchagent_path(home=home)
    return {
        "status": "refused",
        "phase": PHASE,
        "mode": "install-refused",
        "read_only": True,
        "real_install_allowed": False,
        "activation_allowed": False,
        "label": LABEL,
        "message": REFUSAL_MESSAGE,
        "target": {
            "path": str(target_path),
            "exists": target_path.exists(),
        },
        "template": _template_summary(),
    }
