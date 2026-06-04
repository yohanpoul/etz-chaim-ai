"""Read-only command verification helpers for metacognition collectors."""

from __future__ import annotations

import os
import shlex
import subprocess
import time
from collections.abc import Sequence
from pathlib import Path

DEFAULT_TIMEOUT_SECONDS = 30
MAX_CAPTURE_CHARS = 4000


def _as_command_list(command: Sequence[str] | str) -> list[str]:
    if isinstance(command, str):
        return shlex.split(command)
    return [str(part) for part in command]


def _uses_pytest(command: list[str]) -> bool:
    return bool(command) and (
        command[0] == "pytest"
        or command[0].endswith("/pytest")
        or (len(command) >= 3 and command[1:3] == ["-m", "pytest"])
    )


def _normalize_command(command: Sequence[str] | str) -> list[str]:
    parts = _as_command_list(command)
    if not _uses_pytest(parts):
        return parts
    if parts[0] == "pytest" or parts[0].endswith("/pytest"):
        return [".venv/bin/python", "-m", "pytest", *parts[1:]]
    return [".venv/bin/python", "-m", "pytest", *parts[3:]]


def _command_string(command: Sequence[str]) -> str:
    return " ".join(command)


def _pytest_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    existing = env.get("PYTEST_ADDOPTS", "").strip()
    cache_flag = "-p no:cacheprovider"
    if cache_flag not in existing:
        env["PYTEST_ADDOPTS"] = f"{existing} {cache_flag}".strip()
    return env


def _truncate(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode(errors="replace")
    if len(value) <= MAX_CAPTURE_CHARS:
        return value
    return value[:MAX_CAPTURE_CHARS] + "\n...[truncated]"


def run_verification(
    command: Sequence[str] | str,
    cwd: Path | str,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    """Run an explicit local read-only command and return structured evidence."""

    normalized = _normalize_command(command)
    env = _pytest_env() if _uses_pytest(normalized) else None
    start = time.monotonic()
    try:
        run_kwargs = {
            "cwd": str(cwd),
            "capture_output": True,
            "text": True,
            "timeout": timeout_seconds,
        }
        if env is not None:
            run_kwargs["env"] = env
        completed = subprocess.run(
            normalized,
            **run_kwargs,
        )
        duration = time.monotonic() - start
        exit_code: int | None = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - start
        exit_code = None
        stdout = exc.stdout
        stderr = exc.stderr or f"Timed out after {timeout_seconds}s"
        timed_out = True

    return {
        "command": _command_string(normalized),
        "exit_code": exit_code,
        "passed": exit_code == 0,
        "stdout": _truncate(stdout),
        "stderr": _truncate(stderr),
        "duration_seconds": round(duration, 3),
        "timed_out": timed_out,
    }
