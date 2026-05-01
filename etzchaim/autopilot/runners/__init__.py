"""Runners — abstractions for executing commands and invoking LLM workers."""

from __future__ import annotations

from etzchaim.autopilot.runners.base import Runner, RunResult
from etzchaim.autopilot.runners.local import LocalRunner

__all__ = ["Runner", "RunResult", "LocalRunner"]
