"""IsolatedWorker — restricted-tool worker dispatch.

Pattern inspiration acknowledged: NousResearch/hermes-agent (MIT) used a
ThreadPool-based subagent with tool-stripping to prevent recursion. Our
implementation is independent: we spawn one worker per cycle (no pool of
peers), and we use the runner abstraction directly rather than building
on Anthropic SDK's tool framework.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from etzchaim.autopilot.memory.snapshot import ContextSnapshot
from etzchaim.autopilot.runners.base import Runner, RunResult


# Tool categories the worker is forbidden from invoking. Names map to
# Claude Code's tool surface; the prompt instructs the worker explicitly.
RESTRICTED_TOOLS: tuple[str, ...] = (
    "delegate_task",
    "memory_write",
    "code_execution_unsandboxed",
    "git_push_main",
)


@dataclass
class WorkerResult:
    success: bool
    output: str
    duration_ms: int
    skill_name: str
    metadata: dict[str, str] = field(default_factory=dict)


class IsolatedWorker:
    """Dispatch one skill invocation to a runner with restricted toolset.

    The worker is `isolated` in the sense that :
    - It only sees the prompt + frozen snapshot (no autopilot internals).
    - The system prompt instructs it not to touch restricted tools.
    - It writes its output and exits; the autopilot loop does the next step.
    """

    def __init__(self, runner: Runner) -> None:
        self.runner = runner

    def run(
        self,
        skill_name: str,
        skill_body: str,
        task_brief: str,
        snapshot: ContextSnapshot,
        cwd: str | Path | None = None,
        timeout: int = 600,
    ) -> WorkerResult:
        prompt = self._build_prompt(skill_name, skill_body, task_brief, snapshot)
        cwd_str = str(cwd) if cwd is not None else None
        result = self.runner.dispatch(prompt, cwd=cwd_str, timeout=timeout)
        return self._wrap(result, skill_name)

    @staticmethod
    def _build_prompt(
        skill_name: str,
        skill_body: str,
        task_brief: str,
        snapshot: ContextSnapshot,
    ) -> str:
        restricted_list = ", ".join(f"`{t}`" for t in RESTRICTED_TOOLS)
        sections = [
            "# Frozen context",
            snapshot.render() or "(no snapshot loaded)",
            "",
            "# Skill in use",
            f"Skill `{skill_name}`. Follow the procedure exactly.",
            "",
            "# Skill body",
            skill_body.strip(),
            "",
            "# Task",
            task_brief.strip(),
            "",
            "# Restrictions",
            f"You MUST NOT invoke any of: {restricted_list}.",
            "Public surface neutrality is non-negotiable; run "
            "`bash scripts/check_public_surface.sh` and abort on failure.",
        ]
        return "\n".join(sections)

    @staticmethod
    def _wrap(result: RunResult, skill_name: str) -> WorkerResult:
        return WorkerResult(
            success=result.success,
            output=result.stdout,
            duration_ms=result.duration_ms,
            skill_name=skill_name,
            metadata={
                "exit_code": str(result.exit_code),
                "stderr_tail": result.stderr[-2000:] if result.stderr else "",
            },
        )
