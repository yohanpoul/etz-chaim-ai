"""Runner abstraction. Subclasses implement subprocess / LLM invocation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class RunResult:
    """Outcome of a runner dispatch.

    `metadata` carries per-call cross-cutting data such as token usage
    (`input_tokens`, `output_tokens`, `cache_creation_input_tokens`,
    `cache_read_input_tokens`, `total_cost_usd`) when the runner can
    extract them. Empty by default for runners that have no envelope to
    parse (e.g., LocalRunner).
    """

    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    metadata: dict[str, str] = field(default_factory=dict)

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
