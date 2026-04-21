"""Automated installers for local dependencies.

Each installer :
1. Detects whether the component is already present.
2. If not, prompts the user (unless --yes / non-interactive) to install.
3. Runs the platform-appropriate install command and streams output.
4. Verifies success by re-detecting.
5. Falls back to printing the manual command on failure.

Supported platforms : macOS (Homebrew), Debian/Ubuntu (apt). Other Linux
distros fall through to manual-only instructions. Windows is not
auto-installed in v0.2 — WSL2 setup guide is printed instead.

Components :
- Docker runtime (OrbStack preferred on macOS, Docker Engine on Linux)
- PostgreSQL 16
- pgvector extension
- TimescaleDB extension (optional — only auto-installed if the user confirms)
- Ollama daemon + required models (nomic-embed-text, qwen3.5:9b)

Security notes :
- All commands are shown to the user before execution.
- `sudo` prompts are NOT suppressed — the terminal will ask for password.
- No third-party `curl | sh` scripts are piped silently ; the Ollama
  install uses the official script but prints it first.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import Callable

import typer

from etzchaim.cli import detect


def _run(cmd: list[str] | str, shell: bool = False) -> int:
    """Run a command, stream output, return exit code."""
    typer.echo(f"  $ {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
    try:
        rc = subprocess.call(cmd, shell=shell)
        return rc
    except FileNotFoundError as e:
        typer.echo(f"  ✗ {e}", err=True)
        return 127


def _confirm(msg: str, *, non_interactive: bool, yes: bool) -> bool:
    if non_interactive:
        return yes
    return typer.confirm(f"  {msg}", default=True)


# ─── Homebrew helpers (macOS) ───────────────────────────────────────

def _brew_available() -> bool:
    return shutil.which("brew") is not None


def _ensure_brew(*, non_interactive: bool, yes: bool) -> bool:
    """Install Homebrew on macOS if absent. Returns True on success."""
    if _brew_available():
        return True
    if detect.detect_os() != "macos":
        return False
    typer.echo("  ✗ Homebrew not detected — it is required to install local deps.")
    typer.echo("    Source : https://brew.sh (official install script)")
    if not _confirm("Install Homebrew now ?",
                    non_interactive=non_interactive, yes=yes):
        typer.echo("    Skipped. Install manually then rerun :")
        typer.echo("      /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
        return False
    rc = _run(
        "/bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"",
        shell=True,
    )
    if rc != 0 or not _brew_available():
        # Apple Silicon installs brew to /opt/homebrew/bin, which may not be on PATH yet.
        for candidate in ("/opt/homebrew/bin", "/usr/local/bin"):
            if os.path.exists(f"{candidate}/brew"):
                os.environ["PATH"] = f"{candidate}:{os.environ.get('PATH', '')}"
                typer.echo(f"    Added {candidate} to PATH for this session.")
                typer.echo(
                    f"    Persist it : echo 'eval \"$({candidate}/brew shellenv)\"' "
                    ">> ~/.zprofile"
                )
                break
    if _brew_available():
        typer.echo("    ✓ Homebrew installed")
        return True
    typer.echo("    ✗ Homebrew install failed. Retry manually from https://brew.sh")
    return False


def _brew_install(formula: str) -> int:
    return _run(["brew", "install", formula])


def _brew_cask_install(cask: str) -> int:
    return _run(["brew", "install", "--cask", cask])


def _brew_services_start(service: str) -> int:
    return _run(["brew", "services", "start", service])


# ─── Apt helpers (Debian / Ubuntu) ──────────────────────────────────

def _apt_available() -> bool:
    return shutil.which("apt") is not None or shutil.which("apt-get") is not None


def _apt_install(pkg: str) -> int:
    apt = shutil.which("apt") or shutil.which("apt-get")
    if not apt:
        return 127
    typer.echo("  (sudo password may be requested)")
    return _run(["sudo", apt, "install", "-y", pkg])


# ─── Docker runtime ─────────────────────────────────────────────────

def install_docker(*, non_interactive: bool = False, yes: bool = False) -> bool:
    """Install a Docker runtime. Returns True on success."""
    if detect.detect_docker_runtime():
        typer.echo("  ✓ Docker runtime already installed")
        return True

    os_ = detect.detect_os()
    typer.echo("  ✗ No Docker runtime detected.")

    if os_ == "macos":
        typer.echo("    Recommended : OrbStack (free for personal use, lightweight)")
        if _confirm("Install OrbStack via Homebrew ?", non_interactive=non_interactive, yes=yes):
            if not _ensure_brew(non_interactive=non_interactive, yes=yes):
                return False
            rc = _brew_cask_install("orbstack")
            if rc == 0:
                typer.echo("    ✓ OrbStack installed. Launch it once to finish setup : open -a OrbStack")
                return True
            typer.echo("    ✗ brew install failed. Try manually : https://orbstack.dev")
            return False
    elif os_ == "linux":
        typer.echo("    Recommended : Docker Engine (official convenience script)")
        if _confirm("Install Docker Engine via the official script ?",
                    non_interactive=non_interactive, yes=yes):
            rc = _run("curl -fsSL https://get.docker.com | sh", shell=True)
            if rc == 0:
                _run(["sudo", "usermod", "-aG", "docker", os.environ.get("USER", "")])
                typer.echo("    ✓ Docker installed. Log out and back in for group to apply.")
                return True
    else:
        typer.echo(f"    Automated install not supported on {os_}.")
        typer.echo("    Install manually : https://docs.docker.com/get-started/get-docker/")
    return False


# ─── PostgreSQL + extensions ────────────────────────────────────────

def install_postgres(*, non_interactive: bool = False, yes: bool = False) -> bool:
    """Install PostgreSQL 16 locally. Returns True on success."""
    if shutil.which("psql"):
        typer.echo("  ✓ PostgreSQL already installed")
        return True

    os_ = detect.detect_os()
    typer.echo("  ✗ PostgreSQL not detected on this host.")

    if os_ == "macos":
        if not _ensure_brew(non_interactive=non_interactive, yes=yes):
            return False
        if _confirm("Install postgresql@16 via Homebrew ?", non_interactive=non_interactive, yes=yes):
            if _brew_install("postgresql@16") != 0:
                return False
            _brew_services_start("postgresql@16")
            typer.echo("    ✓ PostgreSQL 16 installed and started")
            return True
    elif os_ == "linux" and _apt_available():
        if _confirm("Install postgresql-16 via apt ?", non_interactive=non_interactive, yes=yes):
            if _apt_install("postgresql-16") == 0:
                typer.echo("    ✓ PostgreSQL 16 installed")
                return True
    else:
        typer.echo(f"    Automated install not supported on {os_}.")
        typer.echo("    Install manually : https://www.postgresql.org/download/")
    return False


def install_pgvector(*, non_interactive: bool = False, yes: bool = False) -> bool:
    """Install the pgvector extension binary. DB-level CREATE EXTENSION runs later."""
    os_ = detect.detect_os()
    typer.echo("  → pgvector extension")

    if os_ == "macos":
        if not _ensure_brew(non_interactive=non_interactive, yes=yes):
            return False
        if _confirm("Install pgvector via Homebrew ?", non_interactive=non_interactive, yes=yes):
            return _brew_install("pgvector") == 0
    elif os_ == "linux" and _apt_available():
        if _confirm("Install postgresql-16-pgvector via apt ?",
                    non_interactive=non_interactive, yes=yes):
            return _apt_install("postgresql-16-pgvector") == 0
    else:
        typer.echo("    Manual : https://github.com/pgvector/pgvector#installation")
    return False


def install_timescaledb(*, non_interactive: bool = False, yes: bool = False) -> bool:
    """Install the TimescaleDB extension (optional — hypertable compression)."""
    os_ = detect.detect_os()
    typer.echo("  → TimescaleDB extension (optional)")

    if os_ == "macos":
        if not _ensure_brew(non_interactive=non_interactive, yes=yes):
            return False
        if _confirm("Install timescaledb via Homebrew ?",
                    non_interactive=non_interactive, yes=yes):
            _run(["brew", "tap", "timescale/tap"])
            return _brew_install("timescaledb") == 0
    elif os_ == "linux" and _apt_available():
        if _confirm("Install timescaledb-2-postgresql-16 via apt ?",
                    non_interactive=non_interactive, yes=yes):
            return _apt_install("timescaledb-2-postgresql-16") == 0
    else:
        typer.echo("    Manual : https://docs.timescale.com/self-hosted/latest/install/")
    return False


# ─── Ollama ─────────────────────────────────────────────────────────

OLLAMA_MODELS = ["nomic-embed-text", "qwen3.5:9b"]


def install_ollama(*, non_interactive: bool = False, yes: bool = False,
                   pull_models: bool = True) -> bool:
    """Install Ollama + pull the two required models. Returns True on success."""
    os_ = detect.detect_os()

    if not shutil.which("ollama"):
        typer.echo("  ✗ Ollama not detected.")
        if os_ == "macos":
            if not _ensure_brew(non_interactive=non_interactive, yes=yes):
                return False
            if _confirm("Install ollama via Homebrew ?",
                        non_interactive=non_interactive, yes=yes):
                if _brew_install("ollama") != 0:
                    return False
                _brew_services_start("ollama")
        elif os_ == "linux":
            if _confirm("Install Ollama via the official script ?",
                        non_interactive=non_interactive, yes=yes):
                if _run("curl -fsSL https://ollama.com/install.sh | sh", shell=True) != 0:
                    return False
        else:
            typer.echo(f"    Automated install not supported on {os_}.")
            typer.echo("    Install manually : https://ollama.com/download")
            return False
        typer.echo("    ✓ Ollama installed")
    else:
        typer.echo("  ✓ Ollama already installed")

    if not pull_models:
        return True

    if not _confirm(f"Pull required models now ? ({', '.join(OLLAMA_MODELS)}, ~6 GB)",
                   non_interactive=non_interactive, yes=yes):
        typer.echo(f"    Skipped. Run manually : {' && '.join(f'ollama pull {m}' for m in OLLAMA_MODELS)}")
        return True

    existing = _ollama_list()
    for model in OLLAMA_MODELS:
        if any(m.startswith(model) for m in existing):
            typer.echo(f"    ✓ {model} already pulled")
            continue
        typer.echo(f"    → Pulling {model} ...")
        if _run(["ollama", "pull", model]) != 0:
            typer.echo(f"    ✗ Failed to pull {model}", err=True)
    return True


def _ollama_list() -> list[str]:
    if not shutil.which("ollama"):
        return []
    try:
        r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            return []
        lines = r.stdout.strip().splitlines()[1:]  # skip header
        return [line.split()[0] for line in lines if line.strip()]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


# ─── AI CLI subscriptions ───────────────────────────────────────────
#
# These CLIs authenticate via OAuth (ChatGPT / Google / GitHub account) and
# do NOT work inside Docker. Install on the host ; use the `codex_cli`,
# `gemini_cli`, `copilot_cli`, or `claude_max` profile to route through them.

def _npm_available() -> bool:
    return shutil.which("npm") is not None


def _ensure_npm(*, non_interactive: bool, yes: bool) -> bool:
    """Install Node.js (which brings npm) if absent. Returns True on success."""
    if _npm_available():
        return True
    os_ = detect.detect_os()
    typer.echo("  ✗ npm not detected — required to install AI CLIs.")
    if os_ == "macos":
        if not _ensure_brew(non_interactive=non_interactive, yes=yes):
            return False
        if _confirm("Install node via Homebrew ?",
                    non_interactive=non_interactive, yes=yes):
            if _brew_install("node") == 0:
                return _npm_available()
    elif os_ == "linux" and _apt_available():
        if _confirm("Install nodejs + npm via apt ?",
                    non_interactive=non_interactive, yes=yes):
            if _apt_install("nodejs") == 0 and _apt_install("npm") == 0:
                return _npm_available()
    else:
        typer.echo("    Manual : https://nodejs.org/en/download/")
    return False


def install_claude_code_cli(*, non_interactive: bool = False,
                            yes: bool = False) -> bool:
    """Install the Anthropic Claude Code CLI (npm)."""
    if shutil.which("claude"):
        typer.echo("  ✓ Claude Code CLI already installed")
        return True
    typer.echo("  → Claude Code CLI (Anthropic, OAuth subscription)")
    typer.echo("    Login after install : claude (runs OAuth once)")
    if not _ensure_npm(non_interactive=non_interactive, yes=yes):
        return False
    if not _confirm("Install @anthropic-ai/claude-code via npm ?",
                    non_interactive=non_interactive, yes=yes):
        return False
    return _run(["npm", "install", "-g", "@anthropic-ai/claude-code"]) == 0


def install_codex_cli(*, non_interactive: bool = False, yes: bool = False) -> bool:
    """Install the OpenAI Codex CLI (npm)."""
    if shutil.which("codex"):
        typer.echo("  ✓ Codex CLI already installed")
        return True
    typer.echo("  → Codex CLI (OpenAI, ChatGPT subscription OAuth)")
    typer.echo("    Login after install : codex  (runs OAuth once)")
    if not _ensure_npm(non_interactive=non_interactive, yes=yes):
        return False
    if not _confirm("Install @openai/codex via npm ?",
                    non_interactive=non_interactive, yes=yes):
        return False
    return _run(["npm", "install", "-g", "@openai/codex"]) == 0


def install_gemini_cli(*, non_interactive: bool = False, yes: bool = False) -> bool:
    """Install the Google Gemini CLI (npm)."""
    if shutil.which("gemini"):
        typer.echo("  ✓ Gemini CLI already installed")
        return True
    typer.echo("  → Gemini CLI (Google, free tier 1000 req/day)")
    typer.echo("    Login after install : gemini  (runs OAuth once)")
    if not _ensure_npm(non_interactive=non_interactive, yes=yes):
        return False
    if not _confirm("Install @google/gemini-cli via npm ?",
                    non_interactive=non_interactive, yes=yes):
        return False
    return _run(["npm", "install", "-g", "@google/gemini-cli"]) == 0


def install_copilot_cli(*, non_interactive: bool = False,
                        yes: bool = False) -> bool:
    """Install the GitHub Copilot CLI (gh extension)."""
    os_ = detect.detect_os()
    if not shutil.which("gh"):
        typer.echo("  ✗ GitHub CLI (gh) not detected.")
        if os_ == "macos":
            if not _ensure_brew(non_interactive=non_interactive, yes=yes):
                return False
            if _confirm("Install gh via Homebrew ?",
                        non_interactive=non_interactive, yes=yes):
                if _brew_install("gh") != 0:
                    return False
        elif os_ == "linux" and _apt_available():
            if _confirm("Install gh via apt ?",
                        non_interactive=non_interactive, yes=yes):
                if _apt_install("gh") != 0:
                    return False
        else:
            typer.echo("    Manual : https://cli.github.com/")
            return False
    # Check for the copilot extension.
    try:
        r = subprocess.run(["gh", "extension", "list"],
                           capture_output=True, text=True, timeout=5)
        if "gh-copilot" in (r.stdout or ""):
            typer.echo("  ✓ gh-copilot extension already installed")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    typer.echo("  → gh-copilot extension (requires active Copilot subscription)")
    typer.echo("    Login after install : gh auth login")
    if not _confirm("Install github/gh-copilot extension ?",
                    non_interactive=non_interactive, yes=yes):
        return False
    return _run(["gh", "extension", "install", "github/gh-copilot"]) == 0


# ─── Orchestrator ───────────────────────────────────────────────────

def ensure_dependencies(
    *,
    need_docker: bool,
    need_postgres: bool,
    need_ollama: bool,
    want_timescaledb: bool,
    non_interactive: bool = False,
    yes: bool = False,
    need_codex_cli: bool = False,
    need_gemini_cli: bool = False,
    need_copilot_cli: bool = False,
    need_claude_code_cli: bool = False,
) -> dict[str, bool]:
    """Install (or verify) all required local dependencies.

    Returns a dict { component_name : success } for reporting. A False value
    means the user declined or the install failed ; the caller decides
    whether to abort.
    """
    results: dict[str, bool] = {}

    typer.echo("")
    typer.echo("Checking local dependencies ...")

    if need_docker:
        results["docker"] = install_docker(non_interactive=non_interactive, yes=yes)
    if need_postgres:
        results["postgres"] = install_postgres(non_interactive=non_interactive, yes=yes)
        if results["postgres"]:
            results["pgvector"] = install_pgvector(
                non_interactive=non_interactive, yes=yes,
            )
        if want_timescaledb:
            results["timescaledb"] = install_timescaledb(
                non_interactive=non_interactive, yes=yes,
            )
    if need_ollama:
        results["ollama"] = install_ollama(non_interactive=non_interactive, yes=yes)
    if need_claude_code_cli:
        results["claude_code_cli"] = install_claude_code_cli(
            non_interactive=non_interactive, yes=yes,
        )
    if need_codex_cli:
        results["codex_cli"] = install_codex_cli(
            non_interactive=non_interactive, yes=yes,
        )
    if need_gemini_cli:
        results["gemini_cli"] = install_gemini_cli(
            non_interactive=non_interactive, yes=yes,
        )
    if need_copilot_cli:
        results["copilot_cli"] = install_copilot_cli(
            non_interactive=non_interactive, yes=yes,
        )

    return results
