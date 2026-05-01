"""WorkerSpawner — pick a worker implementation based on configuration."""

from __future__ import annotations

from etzchaim.autopilot.config import AutopilotConfig
from etzchaim.autopilot.delegation.subagent import IsolatedWorker
from etzchaim.autopilot.runners.base import Runner
from etzchaim.autopilot.runners.claude_skill import ClaudeSkillRunner
from etzchaim.autopilot.runners.local import LocalRunner


class WorkerSpawner:
    """Builds an `IsolatedWorker` matching the configured worker backend."""

    def __init__(self, config: AutopilotConfig) -> None:
        self.config = config

    def spawn(self) -> IsolatedWorker:
        runner = self._build_runner()
        return IsolatedWorker(runner=runner)

    def _build_runner(self) -> Runner:
        worker_name = (self.config.worker or "claude").lower()
        if worker_name == "claude":
            binary = self.config.worker_paths.get("claude", "claude")
            return ClaudeSkillRunner(binary=binary)
        if worker_name == "codex":
            # Codex CLI uses the same subprocess shape; the skill prompt is
            # delivered on stdin. We treat it as a generic local runner.
            return LocalRunner()
        raise ValueError(f"unknown worker backend: {worker_name!r}")
