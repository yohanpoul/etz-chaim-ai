"""Runtime auto-start helpers — Docker + Ollama.

If a required service is installed but not running, try to start it
ourselves (open -a OrbStack on macOS, brew services start ollama, …)
and poll until it responds. The user should never have to leave the
terminal to babysit dependencies before `etzchaim onboard`.

These helpers are best-effort. They fall back to a clear instruction
when auto-start is impossible (service not installed, sandbox refuses,
poll times out).
"""
from __future__ import annotations

import shutil
import subprocess
import time
import urllib.error
import urllib.request
from typing import Callable

import typer

from etzchaim.cli import detect


def _wait_for(predicate: Callable[[], bool], timeout: float, label: str) -> bool:
    """Poll predicate every 0.5s, dot-print progress, return final state."""
    deadline = time.time() + timeout
    typer.echo(f"  Waiting for {label} to come up", nl=False)
    while time.time() < deadline:
        if predicate():
            typer.echo(" ✓")
            return True
        typer.echo(".", nl=False)
        time.sleep(0.5)
    typer.echo(" ✗ (timeout)")
    return False


# ─── Docker ──────────────────────────────────────────────────────────

_DOCKER_APP_NAME = {
    "orbstack": "OrbStack",
    "docker-desktop": "Docker",
    "rancher": "Rancher Desktop",
}


def ensure_docker_running(timeout: float = 60.0) -> bool:
    """Make sure Docker is reachable, auto-starting it if needed.

    Returns True iff `docker info` succeeds at the end.
    """
    if detect.docker_is_running():
        return True

    runtime = detect.detect_docker_runtime()
    if runtime is None:
        typer.echo("✗ Docker runtime not installed.")
        return False

    os_ = detect.detect_os()
    started = False

    if os_ == "macos":
        app = _DOCKER_APP_NAME.get(runtime)
        if app:
            typer.echo(f"→ Starting {app}...")
            r = subprocess.run(["open", "-a", app], capture_output=True)
            started = r.returncode == 0
        elif runtime == "colima":
            typer.echo("→ Starting Colima...")
            r = subprocess.run(["colima", "start"], capture_output=False)
            started = r.returncode == 0
    elif os_ == "linux":
        # systemd user service if present, else assume daemon comes up via socket activation
        if shutil.which("systemctl"):
            typer.echo("→ Starting docker via systemctl...")
            r = subprocess.run(
                ["systemctl", "--user", "start", "docker"],
                capture_output=True,
            )
            if r.returncode != 0:
                # try system-wide (may prompt for sudo)
                r = subprocess.run(["sudo", "systemctl", "start", "docker"], capture_output=False)
            started = r.returncode == 0

    if not started:
        typer.echo(
            f"⚠ Could not auto-start {runtime}. Start it manually then re-run `etzchaim onboard`."
        )
        return False

    return _wait_for(detect.docker_is_running, timeout=timeout, label=runtime)


# ─── Ollama ──────────────────────────────────────────────────────────

OLLAMA_DEFAULT_HOST = "http://localhost:11434"


def ollama_is_reachable(host: str = OLLAMA_DEFAULT_HOST) -> bool:
    """True if HTTP GET on the Ollama root returns 200."""
    try:
        with urllib.request.urlopen(host, timeout=2) as r:
            return r.status == 200
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        return False


def ensure_ollama_running(timeout: float = 30.0) -> bool:
    """Make sure Ollama is reachable, auto-starting it if needed.

    Strategy, in priority order :
      1. macOS Ollama.app (most common — `Ollama.dmg` from ollama.com
         installs an .app, not a Homebrew formula). `open -a Ollama`
         launches the app and starts the menu-bar daemon.
      2. Homebrew service (`brew services start ollama`) — persistent
         across reboots, used when Ollama was installed via brew.
      3. Background `ollama serve` — fallback for any case the above
         can't handle (Linux / podman / SSH-only sessions).
    """
    if ollama_is_reachable():
        return True

    os_ = detect.detect_os()
    started = False

    # 1. macOS .app — check before brew because the .app is the default
    # install path on ollama.com and brew may also have a stale formula.
    from pathlib import Path
    if os_ == "macos" and Path("/Applications/Ollama.app").exists():
        typer.echo("→ Starting Ollama.app...")
        r = subprocess.run(["open", "-a", "Ollama"], capture_output=True)
        started = r.returncode == 0

    # 2. Homebrew service
    if not started and os_ == "macos" and shutil.which("brew"):
        # Quick check : does brew know about ollama ?
        r = subprocess.run(
            ["brew", "services", "list"], capture_output=True, text=True,
        )
        if r.returncode == 0 and "ollama" in r.stdout:
            typer.echo("→ Starting Ollama via brew services...")
            r = subprocess.run(
                ["brew", "services", "start", "ollama"],
                capture_output=True, text=True,
            )
            started = r.returncode == 0

    # 3. Background `ollama serve`
    if not started and shutil.which("ollama"):
        typer.echo("→ Starting `ollama serve` in background...")
        try:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            started = True
        except (OSError, FileNotFoundError):
            started = False

    if not started:
        typer.echo(
            "⚠ Could not auto-start Ollama. Install it from https://ollama.com\n"
            "  or run `brew install ollama`, then re-run `etzchaim onboard`."
        )
        return False

    return _wait_for(ollama_is_reachable, timeout=timeout, label="Ollama")
