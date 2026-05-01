"""LocalRunner — subprocess-based command execution on the host machine.

Wraps `subprocess.run` with timeout + structured result capture.
Inspiration acknowledged in LICENSE_THIRD_PARTY.md (terminal abstraction
pattern from NousResearch/hermes-agent, MIT). Reimplemented with our naming.
"""

from __future__ import annotations

import shlex
import subprocess
import time

from etzchaim.autopilot.runners.base import Runner, RunResult


class LocalRunner(Runner):
    """Executes commands on the local machine via subprocess."""

    def __init__(self, default_timeout: int = 300) -> None:
        self.default_timeout = default_timeout

    def dispatch(
        self,
        command: list[str] | str,
        cwd: str | None = None,
        timeout: int = 300,
        env: dict[str, str] | None = None,
        stdin: str | None = None,
    ) -> RunResult:
        start = time.monotonic()

        if isinstance(command, str):
            argv = shlex.split(command)
        else:
            argv = list(command)

        try:
            completed = subprocess.run(
                argv,
                cwd=cwd,
                timeout=timeout or self.default_timeout,
                env=env,
                input=stdin,
                capture_output=True,
                text=True,
                check=False,
            )
            return RunResult(
                exit_code=completed.returncode,
                stdout=completed.stdout or "",
                stderr=completed.stderr or "",
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        except subprocess.TimeoutExpired as exc:
            return RunResult(
                exit_code=124,
                stdout=(exc.stdout or b"").decode("utf-8", "replace"),
                stderr=f"timeout after {timeout}s: {exc}",
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        except FileNotFoundError as exc:
            return RunResult(
                exit_code=127,
                stdout="",
                stderr=f"command not found: {exc}",
                duration_ms=int((time.monotonic() - start) * 1000),
            )
