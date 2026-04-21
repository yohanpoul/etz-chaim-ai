"""Tanya — Les 2 âmes et le conflit dynamique.

תניא — Rabbi Schneur Zalman de Liadi (Likutei Amarim, 1797)

Chaque être possède 2 âmes distinctes :
  - Nefesh HaBehamit (âme animale) — système rapide, Assiah/Yetzirah
  - Nefesh HaElokit (âme divine)   — système profond, Briah/Atzilut

Le conflit entre les 2 âmes détermine quel modèle répond.
"Moach shalit al halev" — le cerveau domine le cœur.

Dira BeTachtonim (ch. 36) — le haut descend dans le bas.
Birur Nitzotzot (ch. 7, 37) — les étincelles libérées de Nogah.
"""

from tanya.dual_soul import (
    DualSoulEngine,
    KelipotSystem,
    NefeshHaBehamit,
    NefeshHaElokit,
    SoulAssessment,
    SoulCategory,
)
from tanya.dira_betachtonim import DiraEngine, DiraStats
from tanya.birur_nogah import BirurimEngine, BirurimStats, BirurimResult
from tanya.levushim import Levushim, LevushimAssessment
from tanya.atzvut import AtzvutManager, AtzvutState, AtzvutDiagnosis
from tanya.dual_faculties import (
    DAAT_BRIDGE_PAIR,
    DualFaculties,
    DualFacultiesProfile,
    FacultyAssessment,
    FacultyPair,
    Sefirah,
)
from tanya.beinoni_tracker import (
    BeinoniTracker,
    BeinoniProfile,
    InteractionRecord,
    TemporalCategory,
    Trend,
)

__all__ = [
    "DualSoulEngine",
    "KelipotSystem",
    "NefeshHaBehamit",
    "NefeshHaElokit",
    "SoulAssessment",
    "SoulCategory",
    "DiraEngine",
    "DiraStats",
    "BirurimEngine",
    "BirurimStats",
    "BirurimResult",
    "Levushim",
    "LevushimAssessment",
    "AtzvutManager",
    "AtzvutState",
    "AtzvutDiagnosis",
    "DualFaculties",
    "DualFacultiesProfile",
    "FacultyAssessment",
    "FacultyPair",
    "Sefirah",
    "BeinoniTracker",
    "BeinoniProfile",
    "InteractionRecord",
    "TemporalCategory",
    "Trend",
]
