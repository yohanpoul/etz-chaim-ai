"""Port introspection helpers shared by onboard / doctor / status.

The onboard wizard, the doctor checks, and the status command all need to
identify which process is holding a given TCP port — otherwise users who
have a stale `python main.py web --port 8080` (or a launchd-managed dev
instance) get silently bumped to 8081 and end up staring at a foreign
dashboard, wondering why every panel is at zero.

Uses `lsof` (always present on macOS, ubiquitous on Linux). On platforms
without it, returns None — callers degrade gracefully.
"""
from __future__ import annotations

import shutil
import socket
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class PortHolder:
    pid: int
    command: str


def port_busy(port: int) -> bool:
    """True if no process can bind 127.0.0.1:port right now."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return False
        except OSError:
            return True


def who_listens_on(port: int) -> PortHolder | None:
    """Return PID + command of the process listening on `port`, if any.

    Returns None when the port is free, when `lsof` is unavailable, or when
    the lookup fails for any other reason — callers must degrade gracefully.
    """
    if shutil.which("lsof") is None:
        return None
    try:
        result = subprocess.run(
            ["lsof", f"-iTCP:{port}", "-sTCP:LISTEN", "-Pn", "-F", "pc"],
            capture_output=True, text=True, timeout=3,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    pid: int | None = None
    command: str = ""
    for line in result.stdout.splitlines():
        if not line:
            continue
        tag, value = line[0], line[1:]
        if tag == "p":
            try:
                pid = int(value)
            except ValueError:
                pid = None
        elif tag == "c" and pid is not None:
            command = value
            break
    if pid is None:
        return None
    return PortHolder(pid=pid, command=command or "?")


def is_etzchaim_container_port(port: int) -> bool:
    """True if `port` is bound by the etzchaim Docker stack (not a foreign squatter).

    Heuristic : the host-side mapping ${HOST_WEB_PORT}:8080 is owned by
    `com.docker.backend` / `vpnkit` on macOS, or `docker-proxy` on Linux.
    A native python (e.g. `main.py web`) is a foreign holder, even if it
    happens to be Etz Chaim source code running outside the container.
    """
    holder = who_listens_on(port)
    if holder is None:
        return False
    cmd = holder.command.lower()
    return any(needle in cmd for needle in ("docker", "vpnkit", "com.docke"))
