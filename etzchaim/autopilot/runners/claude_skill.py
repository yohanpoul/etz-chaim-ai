"""ClaudeSkillRunner — invoke `claude --print` (headless) with a skill.

Wraps the existing `olamot.py::claude_code_generate` pattern but adds skill
invocation : the worker is told to use a specific skill via system prompt
context. We do not pass `--skill` directly because Claude Code's CLI does
not currently expose that flag; instead we instruct in-context.

Subprocess output : JSON when `--output-format=json`, else plain text.
"""

from __future__ import annotations

import json
import os
import time

from etzchaim.autopilot.runners.base import Runner, RunResult
from etzchaim.autopilot.runners.local import LocalRunner
from etzchaim.llm.model_registry import resolve_model

DEFAULT_CLAUDE_BIN = os.environ.get("ETZ_CLAUDE_BIN", "claude")


class ClaudeSkillRunner(Runner):
    """Invoke Claude Code in headless mode with a directing system prompt."""

    def __init__(
        self,
        binary: str = DEFAULT_CLAUDE_BIN,
        model: str | None = None,
        max_turns: int = 60,
        local: LocalRunner | None = None,
    ) -> None:
        self.binary = binary
        self.model = model if model is not None else resolve_model("opus")
        self.max_turns = max_turns
        self.local = local or LocalRunner()

    def dispatch(
        self,
        command: list[str] | str,
        cwd: str | None = None,
        timeout: int = 600,
        env: dict[str, str] | None = None,
        stdin: str | None = None,
    ) -> RunResult:
        """The `command` argument here is the **prompt** to send to Claude.

        For the `Runner` interface we accept str or list; both are joined
        as the prompt body. The actual subprocess invocation builds its own
        argv.
        """
        prompt = command if isinstance(command, str) else " ".join(command)

        argv = [
            self.binary,
            "--print",
            "--output-format=json",
            "--model",
            self.model,
            "--max-turns",
            str(self.max_turns),
        ]

        start = time.monotonic()
        result = self.local.dispatch(
            argv,
            cwd=cwd,
            timeout=timeout,
            env=env,
            stdin=prompt,
        )

        # Try to parse JSON envelope and surface result text in stdout.
        # Also extract `usage` so the cycle loop can charge billable tokens
        # against the monthly budget tracker.
        if result.exit_code == 0 and result.stdout:
            try:
                doc = json.loads(result.stdout)
                text = str(doc.get("result", "")).strip()
                usage = doc.get("usage", {}) or {}
                meta = {
                    "input_tokens": str(usage.get("input_tokens", 0)),
                    "output_tokens": str(usage.get("output_tokens", 0)),
                    "cache_creation_input_tokens": str(usage.get("cache_creation_input_tokens", 0)),
                    "cache_read_input_tokens": str(usage.get("cache_read_input_tokens", 0)),
                    "total_cost_usd": str(doc.get("total_cost_usd", 0.0)),
                }
                if text:
                    return RunResult(
                        exit_code=0,
                        stdout=text,
                        stderr=result.stderr,
                        duration_ms=int((time.monotonic() - start) * 1000),
                        metadata=meta,
                    )
            except json.JSONDecodeError:
                pass

        return result

    def invoke_skill(
        self,
        skill_name: str,
        task_brief: str,
        context: str = "",
        cwd: str | None = None,
        timeout: int = 600,
    ) -> RunResult:
        """Convenience: build a system-style prompt instructing skill use.

        The prompt is plain text; Claude Code interprets it. The skill is
        named in-prompt because the CLI does not expose a `--skill` flag.
        """
        sections = [f"# Skill\n\nUse the `{skill_name}` skill."]
        if context:
            sections.append("# Context\n\n" + context.strip())
        sections.append("# Task\n\n" + task_brief.strip())
        prompt = "\n\n".join(sections)
        return self.dispatch(prompt, cwd=cwd, timeout=timeout)
