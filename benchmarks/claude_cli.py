"""Claude CLI wrapper avec capture usage + cost (forfait Max OAuth).

Le CLI Claude v2.1.119 retourne `total_cost_usd` et `usage` (input_tokens,
output_tokens, cache_read_input_tokens, cache_creation_input_tokens) dans
son JSON output — contrairement à ce que olamot.py:claude_code_generate
extrait (qui ne lit que `data["result"]`).

Ce module wrap le subprocess Claude CLI directement pour le benchmark,
sans dépendre de olamot (zéro modification production code).

Usage :
    cli = ClaudeCLIInvoker()
    result = cli.invoke(
        prompt="What is Tsimtsum?",
        system_prompt="Reply briefly.",
        model="claude-opus-4-20250514",
    )
    # result.text, result.cost_usd, result.usage_input, result.usage_output, ...
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import asdict, dataclass
from typing import Any


CLAUDE_BIN_DEFAULT = "/Users/fffff/.local/bin/claude"
DEFAULT_MODEL = "claude-opus-4-20250514"

# Default system prompt minimal — for raw arm
DEFAULT_SYSTEM_PROMPT = "You are a careful, honest, helpful assistant."

# CoT system prompt
COT_SYSTEM_PROMPT = (
    "You are a careful, honest, helpful assistant. "
    "Think step by step before answering, then provide a concise final answer."
)


@dataclass
class CLIInvocationResult:
    """Résultat d'une invocation Claude CLI avec usage + cost."""

    text: str
    success: bool
    duration_ms: int
    duration_api_ms: int
    cost_usd: float
    usage_input: int
    usage_output: int
    cache_creation_tokens: int
    cache_read_tokens: int
    num_turns: int
    stop_reason: str
    model: str
    error: str | None = None
    raw_stdout: str = ""
    raw_stderr: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ClaudeCLIInvoker:
    """Wrapper CLI subprocess + JSON parser avec retry+backoff.

    Plus léger que olamot.claude_code_generate (qui dispatch via Olamot
    sephirot config). Pour le benchmark on veut un raw call direct au
    Claude CLI avec contrôle total des flags.
    """

    def __init__(
        self,
        claude_bin: str | None = None,
        max_retries: int = 3,
        backoff_base: float = 5.0,
    ):
        self.claude_bin = claude_bin or os.environ.get("CLAUDE_BIN", CLAUDE_BIN_DEFAULT)
        self.max_retries = max_retries
        self.backoff_base = backoff_base

    def invoke(
        self,
        prompt: str,
        *,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        model: str = DEFAULT_MODEL,
        timeout: int = 180,
        max_turns: int = 1,  # 1 turn = direct response, no agentic loop
        no_tools: bool = True,
    ) -> CLIInvocationResult:
        """Invoke Claude CLI subprocess, parse JSON, return rich result.

        Args:
            prompt: User prompt (passed via stdin).
            system_prompt: System prompt injected via --system-prompt.
            model: Model slug (default Opus 4.7 full).
            timeout: subprocess timeout seconds.
            max_turns: Claude Code agent turn limit. 1 = single response.
            no_tools: Disable tool use (text-only).

        Returns:
            CLIInvocationResult.
        """
        cmd = [
            self.claude_bin, "-p",
            "--output-format", "json",
            "--model", model,
            "--no-session-persistence",
            "--max-turns", str(max_turns),
            "--system-prompt", system_prompt,
            "--disable-slash-commands",
            "--strict-mcp-config",
        ]
        if no_tools:
            cmd += ["--tools", ""]

        # Force OAuth path : no ANTHROPIC_API_KEY env
        clean_env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}

        for attempt in range(self.max_retries):
            t0 = time.monotonic()
            try:
                proc = subprocess.run(
                    cmd,
                    input=prompt,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    env=clean_env,
                )
            except subprocess.TimeoutExpired as e:
                wall_ms = int((time.monotonic() - t0) * 1000)
                stdout_text = (
                    e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
                )
                stderr_text = (
                    e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
                )
                return CLIInvocationResult(
                    text="", success=False,
                    duration_ms=wall_ms, duration_api_ms=0,
                    cost_usd=0.0, usage_input=0, usage_output=0,
                    cache_creation_tokens=0, cache_read_tokens=0,
                    num_turns=0, stop_reason="timeout", model=model,
                    error=f"Timeout after {timeout}s",
                    raw_stdout=stdout_text, raw_stderr=stderr_text,
                )
            except FileNotFoundError as e:
                return CLIInvocationResult(
                    text="", success=False,
                    duration_ms=0, duration_api_ms=0,
                    cost_usd=0.0, usage_input=0, usage_output=0,
                    cache_creation_tokens=0, cache_read_tokens=0,
                    num_turns=0, stop_reason="binary_not_found", model=model,
                    error=f"Claude CLI not found at {self.claude_bin}: {e}",
                )

            wall_ms = int((time.monotonic() - t0) * 1000)
            stderr_lower = (proc.stderr or "").lower()

            # Detect rate limit
            is_rate_limited = (
                proc.returncode != 0 and (
                    "rate limit" in stderr_lower
                    or "overloaded" in stderr_lower
                    or "429" in stderr_lower
                    or "too many requests" in stderr_lower
                )
            )
            if is_rate_limited and attempt < self.max_retries - 1:
                backoff = self.backoff_base * (2 ** attempt)
                time.sleep(backoff)
                continue

            # Parse JSON
            try:
                data = json.loads(proc.stdout)
            except json.JSONDecodeError as e:
                return CLIInvocationResult(
                    text="", success=False,
                    duration_ms=wall_ms, duration_api_ms=0,
                    cost_usd=0.0, usage_input=0, usage_output=0,
                    cache_creation_tokens=0, cache_read_tokens=0,
                    num_turns=0, stop_reason="json_decode_error", model=model,
                    error=f"JSON decode failed: {e}",
                    raw_stdout=proc.stdout[:1000], raw_stderr=proc.stderr[:1000],
                )

            text = (data.get("result") or "").strip()
            usage = data.get("usage") or {}
            success = bool(text) and not data.get("is_error", False)

            return CLIInvocationResult(
                text=text,
                success=success,
                duration_ms=int(data.get("duration_ms", wall_ms)),
                duration_api_ms=int(data.get("duration_api_ms", 0)),
                cost_usd=float(data.get("total_cost_usd", 0.0)),
                usage_input=int(usage.get("input_tokens", 0)),
                usage_output=int(usage.get("output_tokens", 0)),
                cache_creation_tokens=int(usage.get("cache_creation_input_tokens", 0)),
                cache_read_tokens=int(usage.get("cache_read_input_tokens", 0)),
                num_turns=int(data.get("num_turns", 1)),
                stop_reason=str(data.get("stop_reason", "unknown")),
                model=model,
                error=None if success else data.get("subtype", "no_result"),
                raw_stderr=proc.stderr[-500:] if proc.stderr else "",
            )

        # Exhausted retries
        return CLIInvocationResult(
            text="", success=False,
            duration_ms=0, duration_api_ms=0,
            cost_usd=0.0, usage_input=0, usage_output=0,
            cache_creation_tokens=0, cache_read_tokens=0,
            num_turns=0, stop_reason="max_retries_exceeded", model=model,
            error=f"Rate limited after {self.max_retries} retries",
        )


if __name__ == "__main__":
    # Smoke test live (requires Claude CLI OAuth-loggué)
    import sys

    invoker = ClaudeCLIInvoker()
    result = invoker.invoke(
        prompt="Say only the word 'pong'.",
        system_prompt="Reply briefly.",
    )
    print(f"success: {result.success}")
    print(f"text: {result.text!r}")
    print(f"duration_ms: {result.duration_ms} (api {result.duration_api_ms})")
    print(f"cost_usd: ${result.cost_usd:.4f}")
    print(f"usage: input={result.usage_input} output={result.usage_output}")
    print(f"cache: creation={result.cache_creation_tokens} read={result.cache_read_tokens}")
    print(f"stop_reason: {result.stop_reason}")
    if result.error:
        print(f"error: {result.error}")
        sys.exit(1)
    sys.exit(0)
