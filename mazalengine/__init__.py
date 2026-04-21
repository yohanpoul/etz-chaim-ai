"""mazalengine — 2 Mazalot + rectification active (Sprint 9 + Sprint 10 Phase C, EC-K5-001).

Auto-rectification doctrinale via les Mazalot de la Dikna de A"A :
    - Mazal Elyon = Notzer Chesed (Tikkun 8) → activité ExplorationEngine
    - Mazal Tahton = Ve-Nakeh (Tikkun 13) → résidus causal_claims

Modes rectification (opt-in) :
    observe (défaut) → signalement seul
    suggest          → signalement + action proposée (sans appliquer)
    act              → signalement + proposition + application

Public API:
    MazalEngine — orchestrateur avec modes
    NotzerChesedRectifier, VeNakehRectifier — rectifieurs individuels
    RectificationMode — constantes de modes
    ProposedAction — dataclass d'action proposée
"""

from mazalengine.mazal_engine import MazalEngine
from mazalengine.rectification import (
    NotzerChesedRectifier,
    ProposedAction,
    RectificationMode,
    VeNakehRectifier,
)

# Plain-English alias — `MazalEngine` is the primary, `Watcher` is the alias
# exposed for public documentation and newcomers. Both names refer to the
# same class (see docs/origin.md for the naming convention).
Watcher = MazalEngine

__all__ = [
    "MazalEngine",
    "NotzerChesedRectifier",
    "ProposedAction",
    "RectificationMode",
    "VeNakehRectifier",
    "Watcher",
]
