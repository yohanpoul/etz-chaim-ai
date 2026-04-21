"""Birth ceremony for `etzchaim onboard`.

Public API:
    play_ceremony(width: int = 80) -> CeremonyResult
    play_compact() -> CeremonyResult
    CeremonyResult (dataclass: shem: str, birthtime: datetime)

The orchestrator module owns timing and keypress handling. Callers are
responsible for persisting (shem, birthtime) to the .env file.
"""
from __future__ import annotations

from etzchaim.cli.ceremony._orchestrator import (
    CeremonyResult,
    play_ceremony,
    play_compact,
)

__all__ = ["CeremonyResult", "play_ceremony", "play_compact"]
