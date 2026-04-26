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
    "docker-compose.claude-bridge.yml",
    "claude-stub.sh",
    "Dockerfile",
    "config.yaml",
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
    """Return `docker compose -f ... -f <override>` base command.

    Loads, in order :
      1. ``docker-compose.yml`` (base)
      2. ``docker-compose.{profile}.yml`` (OS/hardware override)
      3. Any other ``docker-compose.*.yml`` present in the compose dir,
         alphabetically — lets the user drop additional overrides
         (e.g. ``docker-compose.claude-bridge.yml``) without patching
         the CLI. The dev override is excluded — it's opt-in via
         ETZCHAIM_USE_BUILD=1.
    """
    d = compose_dir()
    cmd = ["docker", "compose", "-f", str(d / "docker-compose.yml")]
    profile_override = d / f"docker-compose.{profile}.yml"
    loaded: set[str] = {"docker-compose.yml"}
    if profile_override.exists():
        cmd += ["-f", str(profile_override)]
        loaded.add(profile_override.name)
    skip = {"docker-compose.dev.yml"}
    for extra in sorted(d.glob("docker-compose.*.yml")):
        if extra.name in loaded or extra.name in skip:
            continue
        cmd += ["-f", str(extra)]
        loaded.add(extra.name)
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


def list_etzchaim_volumes() -> list[str]:
    """Return docker volume names that belong to a previous etzchaim install.

    Compose names volumes `<project>_<volume>`. Our project is "etzchaim"
    so the postgres data volume is `etzchaim_etz_pg_data`. If the user
    re-onboards after deleting their .env (and therefore loses the old
    Postgres password), the new wizard generates a new random password
    that no longer matches the old volume's stored hash, and the app
    container will crash-loop on auth failure. Detecting these volumes
    up front lets us offer a clean wipe before bringing the stack up.
    """
    r = subprocess.run(
        ["docker", "volume", "ls", "--filter", "name=^etzchaim_", "--format", "{{.Name}}"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return []
    return [v for v in r.stdout.splitlines() if v.strip()]


def wipe_volumes(profile: str = "hybrid-host-ollama") -> int:
    """`docker compose down -v` — drop containers + named volumes.

    Used when the user opts to start fresh after a previous install
    leaves volumes whose Postgres password no longer matches `.env`.
    """
    cmd = compose_command(profile) + ["down", "-v"]
    return subprocess.call(cmd, cwd=str(compose_dir()))
