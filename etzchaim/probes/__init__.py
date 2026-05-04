"""etzchaim.probes — public namespace for the probe orchestrator.

Public neutral facade over the internal `mazalengine/` package. Use this
namespace in user-facing code, docs, and examples. The internal package
remains accessible for developers who need direct module access.
"""

from __future__ import annotations

from etzchaim._internal.rectifiers import (
    BaseRectifier,
    ContradictionResolutionRectifier,
    Deviation,
    Event,
    MemoryFaculty,
    UndoRecipe,
)
from etzchaim._internal.rectifiers import RectificationMode as RectifierMode
from mazalengine import (
    MazalEngine as ProbeOrchestrator,
)
from mazalengine import (
    NotzerChesedRectifier as ExplorationStarvationRectifier,
)
from mazalengine import (
    ProposedAction,
    RectificationMode,
    Watcher,
)
from mazalengine import (
    VeNakehRectifier as StaleClaimsRectifier,
)

__all__ = [
    "ProbeOrchestrator",
    "Watcher",
    "RectificationMode",
    "RectifierMode",
    "ProposedAction",
    "ExplorationStarvationRectifier",
    "StaleClaimsRectifier",
    "BaseRectifier",
    "ContradictionResolutionRectifier",
    "Deviation",
    "Event",
    "MemoryFaculty",
    "UndoRecipe",
]
