"""Testable launchctl command builders for Phase 3C supervision."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence
from pathlib import Path

from etzchaim.supervision.launchagent import LABEL

MUTATING_SUBCOMMANDS = frozenset({"bootstrap", "kickstart", "bootout", "disable", "enable"})
READ_ONLY_SUBCOMMANDS = frozenset({"print"})
ALLOWED_SUBCOMMANDS = READ_ONLY_SUBCOMMANDS | MUTATING_SUBCOMMANDS


def user_domain(uid: int | None = None) -> str:
    """Return the current user's launchd GUI domain."""

    return f"gui/{uid if uid is not None else os.getuid()}"


def service_target(uid: int | None = None, label: str = LABEL) -> str:
    """Return the launchd service target for the label."""

    return f"{user_domain(uid)}/{label}"


def print_command(uid: int | None = None, label: str = LABEL) -> list[str]:
    return ["launchctl", "print", service_target(uid, label)]


def bootstrap_command(plist_path: Path, uid: int | None = None) -> list[str]:
    return ["launchctl", "bootstrap", user_domain(uid), str(plist_path)]


def kickstart_command(uid: int | None = None, label: str = LABEL) -> list[str]:
    return ["launchctl", "kickstart", "-k", service_target(uid, label)]


def bootout_command(uid: int | None = None, label: str = LABEL) -> list[str]:
    return ["launchctl", "bootout", service_target(uid, label)]


def disable_command(uid: int | None = None, label: str = LABEL) -> list[str]:
    return ["launchctl", "disable", service_target(uid, label)]


def enable_command(uid: int | None = None, label: str = LABEL) -> list[str]:
    return ["launchctl", "enable", service_target(uid, label)]


def run_launchctl(command: Sequence[str], *, allow_mutation: bool = False) -> dict[str, object]:
    """Run a launchctl command using fixed argv and no shell."""

    argv = list(command)
    if len(argv) < 2 or argv[0] != "launchctl":
        raise ValueError("launchctl command must start with launchctl and a subcommand")
    subcommand = argv[1]
    if subcommand not in ALLOWED_SUBCOMMANDS:
        raise ValueError(f"unsupported launchctl subcommand for Phase 3C: {subcommand}")
    if subcommand in MUTATING_SUBCOMMANDS and not allow_mutation:
        raise ValueError("launchctl mutation requires explicit mutation allow")
    completed = subprocess.run(
        argv,
        shell=False,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "command": argv,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
