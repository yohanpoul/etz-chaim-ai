"""etzchaim claude-bridge — manage the host bridge that proxies Claude CLI.

The Docker container can't reach the host's `claude` binary directly
(Node.js bundle, OAuth tokens, etc.). For the ``claude_max`` provider
profile to work, we run a tiny HTTP gateway on the host (port 11435)
that re-executes ``claude -p ...`` natively and returns the JSON to the
container, where a stub ``/usr/local/bin/claude`` forwards every call.

This command installs / starts / stops / inspects that bridge.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from importlib import resources
from pathlib import Path

import typer

from etzchaim.cli.app import app

bridge_app = typer.Typer(
    name="claude-bridge",
    help="Manage the host bridge that proxies Claude CLI into the Docker stack.",
    no_args_is_help=True,
)
app.add_typer(bridge_app, name="claude-bridge")


HOME = Path(os.path.expanduser("~"))
BRIDGE_DIR = HOME / ".etz-chaim" / "claude-bridge"
LAUNCHAGENT_PATH = HOME / "Library" / "LaunchAgents" / "com.etz-chaim.claude-bridge.plist"
BRIDGE_PORT = 11435


def _plist_xml() -> str:
    server_path = BRIDGE_DIR / "server.py"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.etz-chaim.claude-bridge</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>{server_path}</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>{HOME}/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{BRIDGE_DIR}/bridge.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>{BRIDGE_DIR}/bridge.stderr.log</string>
    <key>WorkingDirectory</key>
    <string>{BRIDGE_DIR}</string>
</dict>
</plist>
"""


def _copy_server_script() -> None:
    BRIDGE_DIR.mkdir(parents=True, exist_ok=True)
    pkg = resources.files("etzchaim.deploy") / "claude-bridge" / "server.py"
    with resources.as_file(pkg) as src:
        shutil.copyfile(src, BRIDGE_DIR / "server.py")
    (BRIDGE_DIR / "server.py").chmod(0o755)


def _bridge_listening() -> bool:
    try:
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{BRIDGE_PORT}/health", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


@bridge_app.command()
def install() -> None:
    """Install the host bridge (server.py + LaunchAgent) and start it.

    macOS only — the LaunchAgent backend is launchd-specific. Linux users
    should run ``server.py`` via systemd-user or any process supervisor.
    """
    if sys.platform != "darwin":
        typer.echo(
            "✗ This command targets macOS (launchd). On Linux, run\n"
            f"    {BRIDGE_DIR}/server.py\n"
            "  via systemd-user or a process supervisor instead.",
            err=True,
        )
        raise typer.Exit(1)

    if not shutil.which("claude"):
        typer.echo(
            "⚠ `claude` CLI not found on host PATH.\n"
            "  Install Claude Code first: npm install -g @anthropic-ai/claude-code\n"
            "  Then authenticate: `claude` (run interactively once for OAuth setup).",
            err=True,
        )

    typer.echo("→ Copying bridge server.py to ~/.etz-chaim/claude-bridge/")
    _copy_server_script()

    typer.echo("→ Writing LaunchAgent ~/Library/LaunchAgents/com.etz-chaim.claude-bridge.plist")
    LAUNCHAGENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAUNCHAGENT_PATH.write_text(_plist_xml())

    typer.echo("→ launchctl load")
    subprocess.run(["launchctl", "unload", str(LAUNCHAGENT_PATH)], check=False, capture_output=True)
    rc = subprocess.run(["launchctl", "load", str(LAUNCHAGENT_PATH)]).returncode
    if rc != 0:
        typer.echo("✗ launchctl load failed", err=True)
        raise typer.Exit(rc)

    import time
    for _ in range(15):
        if _bridge_listening():
            typer.echo(f"✓ Bridge UP on http://127.0.0.1:{BRIDGE_PORT}")
            typer.echo(
                "  Now switch active_profile in ~/.etz-chaim/compose/config.yaml to\n"
                "  `claude_max` and run `etzchaim start` to restart the stack."
            )
            return
        time.sleep(1)
    typer.echo("⚠ Bridge installed but not yet listening — check ~/.etz-chaim/claude-bridge/bridge.stderr.log", err=True)


@bridge_app.command()
def status() -> None:
    """Show whether the bridge is listening + LaunchAgent state."""
    typer.echo(f"plist            : {LAUNCHAGENT_PATH} {'(present)' if LAUNCHAGENT_PATH.exists() else '(MISSING)'}")
    typer.echo(f"server.py        : {BRIDGE_DIR / 'server.py'} {'(present)' if (BRIDGE_DIR / 'server.py').exists() else '(MISSING)'}")
    if sys.platform == "darwin":
        out = subprocess.run(["launchctl", "list", "com.etz-chaim.claude-bridge"], capture_output=True, text=True)
        typer.echo(f"launchctl        : {out.stdout.strip() or out.stderr.strip() or '(not loaded)'}")
    typer.echo(f"http://localhost:{BRIDGE_PORT}/health  →  {'UP ✓' if _bridge_listening() else 'down ✗'}")


@bridge_app.command()
def uninstall() -> None:
    """Stop the bridge and remove the LaunchAgent (server.py kept on disk)."""
    if sys.platform != "darwin":
        typer.echo("✗ macOS-only.", err=True)
        raise typer.Exit(1)
    if LAUNCHAGENT_PATH.exists():
        subprocess.run(["launchctl", "unload", str(LAUNCHAGENT_PATH)], check=False)
        LAUNCHAGENT_PATH.unlink()
        typer.echo(f"✓ Removed {LAUNCHAGENT_PATH}")
    else:
        typer.echo("(LaunchAgent already absent)")
    typer.echo(f"  server.py kept at {BRIDGE_DIR / 'server.py'} — delete manually if desired.")
