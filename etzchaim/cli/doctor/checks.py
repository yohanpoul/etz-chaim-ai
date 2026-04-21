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
        return (False, f"Ollama not reachable at {host} ({type(e).__name__}) — run `ollama serve` or verify OLLAMA_HOST")
    return (False, f"Ollama at {host} returned unexpected status")


def check_api_key_present() -> tuple[bool, str]:
    if os.environ.get("ETZ_CHAIM_API_KEY"):
        return (True, "ETZ_CHAIM_API_KEY set")
    return (False, "ETZ_CHAIM_API_KEY not set — regenerate via `etzchaim onboard`")


CHECKS: list[tuple[str, Callable[[], tuple[bool, str]]]] = [
    ("docker_running", check_docker_running),
    ("compose_services_up", check_compose_services_up),
    ("postgres_healthy", check_postgres_healthy),
    ("ollama_reachable", check_ollama_reachable),
    ("etz_chaim_api_key_present", check_api_key_present),
]
