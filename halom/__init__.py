"""Halom (חלום) — Agent rêveur kabbalistique.

Le rêve est 1/60ème de prophétie (Berakhot 57b).
1 part de signal pour 59 de bruit.

Cycle en 7 phases : Hod → Yegi'ah → Bitul → Chalom → Birur → Binah → Reshimu.
Gilgul (גלגול) : l'Ouroboros — le cycle appliqué à lui-même.

Usage:
    from halom.thompson import ThompsonBandit
    from halom.birur import Birur
    from halom.structural import StructuralAnalyzer
    from halom.reshimu import Reshimu
    from halom.gilgul import Genome, Mutation, GilgulReport
    from halom.models import DreamCandidate, DreamResult, Mechanism
"""
from halom.models import (
    AuditFinding,
    AuditState,
    CycleReport,
    DreamCandidate,
    DreamResult,
    Mechanism,
)
from halom.birur import Birur, RejectionReason
from halom.gilgul import Genome, GilgulReport, Mutation, VALID_VERDICTS
from halom.reshimu import Reshimu
from halom.structural import StructuralAnalyzer
from halom.thompson import ThompsonBandit

__all__ = [
    "AuditFinding",
    "AuditState",
    "Birur",
    "CycleReport",
    "DreamCandidate",
    "DreamResult",
    "Genome",
    "GilgulReport",
    "Mechanism",
    "Mutation",
    "RejectionReason",
    "Reshimu",
    "StructuralAnalyzer",
    "ThompsonBandit",
    "VALID_VERDICTS",
]
