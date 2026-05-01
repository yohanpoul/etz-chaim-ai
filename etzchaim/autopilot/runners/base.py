"""Runner abstraction. Subclasses implement subprocess / LLM invocation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RunResult:
    """Outcome of a runner dispatch."""

    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int

    @property
    def success(self) -> bool:
        return self.exit_code == 0


class Runner(ABC):
    """Abstract interface for executing commands."""

    @abstractmethod
    def dispatch(
        self,
        command: list[str] | str,
        cwd: str | None = None,
        timeout: int = 300,
        env: dict[str, str] | None = None,
        stdin: str | None = None,
    ) -> RunResult:
        """Execute a command and return a structured result."""
        raise NotImplementedError
