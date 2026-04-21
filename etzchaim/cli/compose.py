"""Docker Compose helpers : extract templates from package_data, run `docker compose`.

Compose files ship inside the etzchaim Python package (see pyproject.toml
[tool.setuptools.package-data]). They are extracted to ~/.etz-chaim/compose/
at first `etzchaim onboard`. After extraction, the user can edit them directly.
"""
from __future__ import annotations

import shutil
import subprocess
from importlib import resources
from pathlib import Path

from etzchaim._paths import compose_dir, ensure_state_dir

# Files copied from etzchaim.deploy package into ~/.etz-chaim/compose/
_COMPOSE_FILES = [
    "docker-compose.yml",
    "docker-compose.hybrid-host-ollama.yml",
    "docker-compose.dev.yml",
    "Dockerfile",
]


def extract_compose_files(force: bool = False) -> Path:
    """Copy compose templates from package into ~/.etz-chaim/compose/.

    - force=False (default) : only copies missing files (idempotent, preserves user edits).
    - force=True : overwrites everything (for `etzchaim update`).

    Returns the destination directory.
    """
    ensure_state_dir()
    dest = compose_dir()
    dest.mkdir(parents=True, exist_ok=True)

    pkg = resources.files("etzchaim.deploy")

    for fname in _COMPOSE_FILES:
        src = pkg / fname
        tgt = dest / fname
        if tgt.exists() and not force:
            continue
        with resources.as_file(src) as src_path:
            shutil.copyfile(src_path, tgt)

    # init-db/ folder
    init_db_dest = dest / "init-db"
    init_db_dest.mkdir(exist_ok=True)
    init_db_pkg = pkg / "init-db"
    for sql in init_db_pkg.iterdir():
        if sql.name.endswith(".sql"):
            tgt = init_db_dest / sql.name
            if tgt.exists() and not force:
                continue
            with resources.as_file(sql) as src_path:
                shutil.copyfile(src_path, tgt)

    return dest


def compose_command(profile: str = "hybrid-host-ollama") -> list[str]:
    """Return `docker compose -f ... -f <override>` base command."""
    d = compose_dir()
    cmd = ["docker", "compose", "-f", str(d / "docker-compose.yml")]
    override = d / f"docker-compose.{profile}.yml"
    if override.exists():
        cmd += ["-f", str(override)]
    return cmd


def compose_up(profile: str = "hybrid-host-ollama", detach: bool = True) -> int:
    """Run `docker compose up -d`."""
    cmd = compose_command(profile) + ["up"]
    if detach:
        cmd.append("-d")
    return subprocess.call(cmd, cwd=str(compose_dir()))


def compose_down(profile: str = "hybrid-host-ollama") -> int:
    """Run `docker compose down` (preserves named volumes)."""
    cmd = compose_command(profile) + ["down"]
    return subprocess.call(cmd, cwd=str(compose_dir()))


def compose_ps(profile: str = "hybrid-host-ollama") -> str:
    """Return `docker compose ps --format json` stdout (one JSON per line)."""
    cmd = compose_command(profile) + ["ps", "--format", "json"]
    r = subprocess.run(cmd, cwd=str(compose_dir()), capture_output=True, text=True)
    return r.stdout


def compose_logs(
    follow: bool = False,
    tail: int = 100,
    service: str | None = None,
    profile: str = "hybrid-host-ollama",
) -> int:
    cmd = compose_command(profile) + ["logs"]
    if follow:
        cmd.append("-f")
    cmd += ["--tail", str(tail)]
    if service:
        cmd.append(service)
    return subprocess.call(cmd, cwd=str(compose_dir()))


def compose_pull(profile: str = "hybrid-host-ollama") -> int:
    """Run `docker compose pull` to refresh images."""
    cmd = compose_command(profile) + ["pull"]
    return subprocess.call(cmd, cwd=str(compose_dir()))
