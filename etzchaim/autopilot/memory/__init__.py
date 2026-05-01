"""Autopilot memory subsystem.

Three primitives :
- snapshot: frozen context (mission + operator preferences) loaded once per cycle
- search: FTS5 retrieval over past autopilot cycle logs
- trajectory: ShareGPT-format conversation export for downstream training data
"""

from __future__ import annotations

from etzchaim.autopilot.memory.snapshot import ContextSnapshot, load_frozen_snapshot

__all__ = ["ContextSnapshot", "load_frozen_snapshot"]
