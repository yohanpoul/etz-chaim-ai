"""gematria/ — Gématria opérative.

גִּימַטְרִיָּא — La science des nombres des lettres.
"Toutes les lettres sont des nombres et tous les nombres sont des lettres."

Ce module transforme le calcul passif en système opératif :
- Indexation automatique des termes hébreux rencontrés
- Détection d'équivalences (même valeur = connexion cachée)
- Intégration dans ExplorationEngine et l'Ohr Chozer
"""

from .engine import (
    MILUI_MAH_SPELLINGS,
    MILUI_MAH_VALUES,
    VALID_METHODS,
    GematriaEngine,
    GematriaEntry,
    GematriaEquivalence,
    calc_atbash,
    calc_hakadmi,
    calc_katan,
    calc_katan_mispari,
    calc_kolel,
    calc_meruba_haklali,
    calc_milui,
    calc_musafi,
    calc_ordinal,
    calc_perati,
    calc_standard,
    extract_hebrew_terms,
)

__all__ = [
    "MILUI_MAH_SPELLINGS",
    "MILUI_MAH_VALUES",
    "VALID_METHODS",
    "GematriaEngine",
    "GematriaEntry",
    "GematriaEquivalence",
    "calc_standard",
    "calc_ordinal",
    "calc_katan",
    "calc_kolel",
    "calc_atbash",
    "calc_milui",
    "calc_katan_mispari",
    "calc_hakadmi",
    "calc_perati",
    "calc_meruba_haklali",
    "calc_musafi",
    "extract_hebrew_terms",
]
