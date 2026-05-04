"""etzchaim — CLI & deployment wrapper for Etz Chaim AI.

This package provides the `etzchaim` CLI command (onboard, start, stop, status,
logs, doctor, demo) and the docker-compose templates extracted to
~/.etz-chaim/compose/ at first onboard.
"""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _pkg_version

from etzchaim.initiate import (
    AgentResponse,
    AgentStatus,
    InitiatedAgent,
    InitiationError,
    LLMSpec,
    initiate,
)

try:
    __version__ = _pkg_version("etzchaim")
except PackageNotFoundError:
    __version__ = "0.0.0+dev"

__all__ = [
    "AgentResponse",
    "AgentStatus",
    "InitiatedAgent",
    "InitiationError",
    "LLMSpec",
    "__version__",
    "initiate",
]
