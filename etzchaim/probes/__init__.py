"""etzchaim.probes — public namespace for the probe orchestrator.

Public neutral facade over the internal `mazalengine/` package. Use this
namespace in user-facing code, docs, and examples. The internal package
remains accessible for developers who need direct module access.
"""

from __future__ import annotations

from mazalengine import (
    MazalEngine as ProbeOrchestrator,
    NotzerChesedRectifier as ExplorationStarvationRectifier,
    ProposedAction,
    RectificationMode,
    VeNakehRectifier as StaleClaimsRectifier,
    Watcher,
)

__all__ = [
    "ProbeOrchestrator",
    "Watcher",
    "RectificationMode",
    "ProposedAction",
    "ExplorationStarvationRectifier",
    "StaleClaimsRectifier",
]
