"""tzeruf/ — Tzeruf opératif : permutations et combinaisons de lettres.

צֵרוּף — La science des combinaisons de lettres.

"Il les combina, les pesa, les permuta" — Sefer Yetzirah 2:4

Le Tzeruf est la technique fondamentale de la Kabbale linguistique :
- Sefer Yetzirah : les 231 portes comme paires de lettres
- Abulafia : roues de combinaisons, permutations méditatives
- Temura : tables de substitution (Atbash, Albam, Avgad)
"""

from .engine import (
    ALBAM_MAP,
    ALEPH_BET,
    AVGAD_MAP,
    PermutationTable,
    TzerufEngine,
    TzerufPair,
    TzerufResult,
    abulafia_circles,
    abulafia_combination,
    abulafia_wheel,
    apply_temura,
    pairs_231,
    rotate_pair,
    table_albam,
    table_atbash,
    table_avgad,
    table_direct,
)

__all__ = [
    "ALBAM_MAP",
    "ALEPH_BET",
    "AVGAD_MAP",
    "PermutationTable",
    "TzerufEngine",
    "TzerufPair",
    "TzerufResult",
    "abulafia_circles",
    "abulafia_combination",
    "abulafia_wheel",
    "apply_temura",
    "pairs_231",
    "rotate_pair",
    "table_albam",
    "table_atbash",
    "table_avgad",
    "table_direct",
]
