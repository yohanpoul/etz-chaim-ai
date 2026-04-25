"""5 MVP diagnostic checks. Each returns (ok: bool, message: str).

Phase FULL will extend to 20 checks + --fix auto-repair.
"""
from __future__ import annotations

import json as _json
import os
import urllib.request
from typing import Callable

from etzchaim.cli import compose, detect


def check_docker_running() -> tuple[bool, str]:
    if detect.docker_is_running():
        return (True, "Docker runtime up")
    return (False, "Docker not running — start Docker Desktop / OrbStack / Colima")


def _compose_services_parsed() -> list[dict]:
    if not compose.compose_dir().exists():
        return []
    try:
        raw = compose.compose_ps().strip()
        if not raw:
            return []
        if raw.startswith("["):
            return _json.loads(raw)
        return [_json.loads(line) for line in raw.splitlines() if line.strip()]
    except Exception:
        return []


def check_compose_services_up() -> tuple[bool, str]:
    services = _compose_services_parsed()
    running = [s for s in services if s.get("State") == "running"]
    if running:
        return (True, f"{len(running)} services running")
    return (False, "No services up — run `etzchaim start`")


def check_postgres_healthy() -> tuple[bool, str]:
    services = _compose_services_parsed()
    for s in services:
        name = s.get("Service", s.get("Name", ""))
        if "postgres" in name.lower():
            health = s.get("Health", "")
            if health == "healthy":
                return (True, "PostgreSQL healthy")
            return (False, f"PostgreSQL state: {s.get('State')}/{health or 'no health info'} — check `etzchaim logs -s postgres`")
    return (False, "PostgreSQL service not found — run `etzchaim start`")


def check_ollama_reachable() -> tuple[bool, str]:
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    try:
        with urllib.request.urlopen(f"{host}/api/tags", timeout=3) as r:
            if r.status == 200:
                return (True, f"Ollama reachable at {host}")
    except Exception as e:
        # Don't surface a red ✗ for a profile that doesn't actually need
        # Ollama — anthropic_full / openai_full / bedrock_full route
        # everything (incl. embeddings) through their cloud SDK.
        if not _active_profile_uses_ollama():
            return (True, f"Ollama not running but active profile doesn't need it")
        return (False, f"Ollama not reachable at {host} ({type(e).__name__}) — run `brew services start ollama` (macOS)")
    return (False, f"Ollama at {host} returned unexpected status")


def _active_profile_uses_ollama() -> bool:
    """Inspect ~/.etz-chaim/compose/config.yaml for ollama usage in the
    active profile (either generation or embeddings). Conservative : on
    any read error, assume Ollama IS needed (we'd rather show a noisy
    check than silently hide a real configuration problem)."""
    try:
        import yaml as _yaml
        cfg_path = compose.compose_dir() / "config.yaml"
        if not cfg_path.exists():
            return True
        cfg = _yaml.safe_load(cfg_path.read_text()) or {}
        active = cfg.get("active_profile")
        prof = (cfg.get("profiles") or {}).get(active) or {}
        if (prof.get("embedding") or {}).get("provider") == "ollama":
            return True
        for tier in (prof.get("olamot") or {}).values():
            if (tier or {}).get("provider") == "ollama":
                return True
        return False
    except Exception:
        return True


def _load_compose_env_var(name: str) -> str | None:
    """Read a variable from ~/.etz-chaim/compose/.env (fallback when shell env is empty).

    The CLI is often invoked from a shell that never sourced the compose .env,
    so a check that only looks at os.environ gives false negatives even when the
    variable is correctly wired into the running containers.
    """
    env_file = compose.compose_dir() / ".env"
    if not env_file.exists():
        return None
    prefix = f"{name}="
    try:
        for raw in env_file.read_text().splitlines():
            line = raw.strip()
            if line.startswith(prefix):
                value = line[len(prefix):].strip().strip('"').strip("'")
                return value or None
    except OSError:
        return None
    return None


def check_api_key_present() -> tuple[bool, str]:
    if os.environ.get("ETZ_CHAIM_API_KEY"):
        return (True, "ETZ_CHAIM_API_KEY set (shell env)")
    if _load_compose_env_var("ETZ_CHAIM_API_KEY"):
        return (True, f"ETZ_CHAIM_API_KEY set (in {compose.compose_dir()}/.env)")
    return (False, "ETZ_CHAIM_API_KEY not set — regenerate via `etzchaim onboard`")


CHECKS: list[tuple[str, Callable[[], tuple[bool, str]]]] = [
    ("docker_running", check_docker_running),
    ("compose_services_up", check_compose_services_up),
    ("postgres_healthy", check_postgres_healthy),
    ("ollama_reachable", check_ollama_reachable),
    ("etz_chaim_api_key_present", check_api_key_present),
]
