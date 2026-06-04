"""Dormant macOS LaunchAgent template for Phase 3C supervision."""

from __future__ import annotations

import os
import plistlib
import shutil
from collections.abc import Mapping
from pathlib import Path

LABEL = "com.etzchaim.loop-once"
LOOP_ARGUMENTS = ["loop", "--once", "--json"]
PROGRAM_ARGUMENTS = ["etzchaim", *LOOP_ARGUMENTS]
PHASE = "3C"
REFUSAL_MESSAGE = "Real plist write requires --allow-real-write and exact --ack."
FORBIDDEN_TRIGGER_KEYS = (
    "StartInterval",
    "StartCalendarInterval",
    "WatchPaths",
    "QueueDirectories",
)
ALLOWED_KEYS = frozenset(
    {
        "Label",
        "ProgramArguments",
        "RunAtLoad",
        "KeepAlive",
        "Disabled",
    }
)


def default_launchagent_path(home: Path | None = None) -> Path:
    """Return the planned user LaunchAgent path without creating it."""

    root = home or Path.home()
    return root / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def resolve_executable(executable: str | None = None) -> str:
    """Resolve the etzchaim console script to an absolute launchd-safe path."""

    candidate = executable or "etzchaim"
    expanded = Path(candidate).expanduser()
    if expanded.is_absolute():
        return str(expanded)
    resolved = shutil.which(candidate)
    if not resolved:
        raise FileNotFoundError(f"Could not resolve executable on PATH: {candidate}")
    return resolved


def launchagent_payload(
    *,
    executable: str | None = None,
    disabled: bool = True,
) -> dict[str, object]:
    """Return a dormant LaunchAgent payload for one bounded loop cycle."""

    return {
        "Label": LABEL,
        "ProgramArguments": [resolve_executable(executable), *LOOP_ARGUMENTS],
        "RunAtLoad": False,
        "KeepAlive": False,
        "Disabled": disabled,
    }


def render_launchagent_plist(
    *,
    executable: str | None = None,
    disabled: bool = True,
) -> bytes:
    """Render the dormant LaunchAgent as XML plist bytes."""

    return plistlib.dumps(
        launchagent_payload(executable=executable, disabled=disabled),
        fmt=plistlib.FMT_XML,
        sort_keys=False,
    )


def parse_launchagent_plist(path: Path) -> dict[str, object]:
    """Parse a LaunchAgent plist and require a dictionary payload."""

    with path.open("rb") as handle:
        payload = plistlib.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("LaunchAgent plist must contain a dict")
    return payload


def _validate_program_arguments(value: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, list) or len(value) != 1 + len(LOOP_ARGUMENTS):
        return ["ProgramArguments must be absolute etzchaim loop --once --json"]
    executable = value[0]
    if not isinstance(executable, str) or not Path(executable).is_absolute():
        errors.append("ProgramArguments[0] must be an absolute executable path")
    elif not Path(executable).exists():
        errors.append("ProgramArguments[0] executable must exist")
    elif not os.access(executable, os.X_OK):
        errors.append("ProgramArguments[0] executable must be executable")
    if value[1:] != LOOP_ARGUMENTS:
        errors.append("ProgramArguments must end with loop --once --json")
    return errors


def validate_launchagent_payload(payload: Mapping[str, object]) -> list[str]:
    """Return validation errors for unsafe or unexpected LaunchAgent payloads."""

    errors: list[str] = []
    if payload.get("Label") != LABEL:
        errors.append(f"Label must be {LABEL}")
    errors.extend(_validate_program_arguments(payload.get("ProgramArguments")))
    if payload.get("RunAtLoad") is not False:
        errors.append("RunAtLoad must be false")
    if payload.get("KeepAlive") is not False:
        errors.append("KeepAlive must be false")
    if payload.get("Disabled") not in {True, False}:
        errors.append("Disabled must be a boolean")
    for key in FORBIDDEN_TRIGGER_KEYS:
        if key in payload:
            errors.append(f"{key} is not allowed in Phase 3C")
    for key in payload:
        if key not in ALLOWED_KEYS and key not in FORBIDDEN_TRIGGER_KEYS:
            errors.append(f"{key} is not allowed in Phase 3C")
    return errors


def write_launchagent_plist(
    *,
    home: Path | None = None,
    disabled: bool = True,
    target_path: Path | None = None,
) -> dict[str, object]:
    """Write the LaunchAgent plist to the single expected user path.

    ``home`` must be explicit so lower-level callers cannot accidentally write to
    the real user LaunchAgents directory by relying on ``Path.home()`` defaults.
    The CLI may pass ``Path.home()`` only after its double-confirmation guard.
    """

    if home is None:
        raise ValueError("explicit home is required for LaunchAgent plist writes")

    expected_path = default_launchagent_path(home=home)
    path = target_path or expected_path
    if path != expected_path:
        raise ValueError("target_path is outside the expected LaunchAgents path")

    rendered = render_launchagent_plist(disabled=disabled)
    payload = plistlib.loads(rendered)
    errors = validate_launchagent_payload(payload)
    if errors:
        raise ValueError("; ".join(errors))

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(rendered)
    return {
        "status": "written",
        "path": str(path),
        "bytes": len(rendered),
        "disabled": disabled,
    }


def _template_summary(
    *,
    executable: str = "etzchaim",
    disabled: bool = True,
) -> dict[str, object]:
    payload = launchagent_payload(executable=executable, disabled=disabled)
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


def install_dry_run_payload(
    home: Path | None = None,
    *,
    disabled: bool = True,
) -> dict[str, object]:
    """Return the planned plist write without writing any file."""

    target_path = default_launchagent_path(home=home)
    rendered = render_launchagent_plist(disabled=disabled)
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
        "template": _template_summary(disabled=disabled),
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
