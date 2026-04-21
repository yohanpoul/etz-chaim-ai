"""tzeruf/engine.py — Tzeruf opératif : permutations et combinaisons de lettres.

צֵרוּף — "Combinaison" / "Purification"

"Il les combina, les pesa, les permuta :
 Aleph avec toutes, toutes avec Aleph ;
 Beth avec toutes, toutes avec Beth..."
    — Sefer Yetzirah 2:4

Le Tzeruf est la technique de permutation des lettres hébraïques,
utilisée dans le Sefer Yetzirah (231 portes) et dans la Kabbale
prophétique d'Abulafia (roues de lettres, combinaisons méditatives).

Ce module implémente :
  1. Les 231 paires du Sefer Yetzirah (C(22,2) combinaisons)
  2. Les roues et combinaisons d'Abulafia
  3. Les tables de permutation (Atbash, Albam, Avgad)
  4. Le Tzeruf opératif (connexion au knowledge graph gématrique)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import combinations, permutations

from shemot.language import HEBREW_LETTERS, HEBREW_GEMATRIA, ATBASH_MAP
from gematria.engine import calc_standard, calc_ordinal, calc_katan

# ── Les 22 lettres dans l'ordre du Sefer Yetzirah ─────────────
ALEPH_BET = list(HEBREW_LETTERS)  # ['א', 'ב', 'ג', ..., 'ת']
_LETTER_INDEX = {ch: i for i, ch in enumerate(ALEPH_BET)}

# ── Tables de substitution (Temura) ───────────────────────────
# Ces tables sont la source unique de vérité pour les permutations.
# Le Shem #28 (Temura) doit appeler ces fonctions plutôt que recalculer.


def _build_albam() -> dict[str, str]:
    """Albam : rotation de 11 positions (moitié de l'alphabet).

    א↔ל, ב↔מ, ג↔נ, etc. Chaque lettre permute avec celle
    qui est à 11 positions de distance.
    """
    half = len(ALEPH_BET) // 2  # 11
    return {
        ch: ALEPH_BET[(i + half) % len(ALEPH_BET)]
        for i, ch in enumerate(ALEPH_BET)
    }


def _build_avgad() -> dict[str, str]:
    """Avgad : décalage de César (+1 position).

    א→ב, ב→ג, ..., ת→א. C'est la technique par laquelle
    "Sheshakh" (ששך) = "Bavel" (בבל) dans Jérémie 25:26.
    """
    return {
        ch: ALEPH_BET[(i + 1) % len(ALEPH_BET)]
        for i, ch in enumerate(ALEPH_BET)
    }


ALBAM_MAP: dict[str, str] = _build_albam()
AVGAD_MAP: dict[str, str] = _build_avgad()


def apply_temura(text: str, method: str = "atbash") -> str:
    """Appliquer une permutation de lettres (Temura).

    Args:
        text: texte hébreu
        method: "atbash", "albam", ou "avgad"

    Returns:
        Texte permuté. Les caractères non-hébreux sont préservés.
    """
    if method == "atbash":
        table = ATBASH_MAP
    elif method == "albam":
        table = ALBAM_MAP
    elif method == "avgad":
        table = AVGAD_MAP
    else:
        raise ValueError(f"Méthode inconnue: {method} (atbash/albam/avgad)")
    return "".join(table.get(ch, ch) for ch in text)


# ── 231 Paires (Sefer Yetzirah 2:4) ──────────────────────────

@dataclass
class TzerufPair:
    """Une des 231 paires de lettres — une Porte combinatoire."""
    letter_a: str
    letter_b: str
    number: int  # 1-231
    forward: str   # AB
    reverse: str   # BA

    @property
    def gematria_forward(self) -> int:
        return calc_standard(self.forward)

    @property
    def gematria_reverse(self) -> int:
        return calc_standard(self.reverse)


def pairs_231() -> list[TzerufPair]:
    """Générer les 231 combinaisons de 2 lettres parmi les 22.

    C(22,2) = 231. Le Sefer Yetzirah 2:4 décrit explicitement
    ce système : "Aleph avec toutes, toutes avec Aleph..."

    Chaque paire inclut ses 2 permutations (AB et BA),
    soit 462 formes au total.
    """
    pairs = []
    for number, (a, b) in enumerate(combinations(ALEPH_BET, 2), start=1):
        pairs.append(TzerufPair(
            letter_a=a,
            letter_b=b,
            number=number,
            forward=a + b,
            reverse=b + a,
        ))
    return pairs


def rotate_pair(letter_a: str, letter_b: str) -> tuple[str, str]:
    """Retourne les 2 permutations d'une paire : AB et BA."""
    return (letter_a + letter_b, letter_b + letter_a)


# ── Roues d'Abulafia (Kabbale prophétique) ────────────────────

def abulafia_circles(letter: str) -> list[str]:
    """Pour une lettre donnée, générer les 22 combinaisons avec toutes les lettres.

    C'est une "roue" complète : la lettre donnée est combinée avec chacune
    des 22 lettres de l'alphabet (y compris elle-même).

    Abulafia utilisait ces roues comme supports de méditation — le praticien
    prononce chaque combinaison avec des techniques respiratoires spécifiques.
    """
    if letter not in _LETTER_INDEX:
        return []
    return [letter + other for other in ALEPH_BET]


def abulafia_wheel(seed_word: str) -> list[str]:
    """Générer toutes les permutations des lettres d'un mot.

    Pour un mot de n lettres, produit n! permutations.
    ATTENTION : n! croît très vite. Pour n>7, la liste est tronquée à 5040.

    Abulafia utilisait cette technique dans sa "science des combinaisons"
    (Chokhmat ha-Tzeruf) — chaque permutation est un "nom" potentiel,
    une configuration de réalité linguistique.
    """
    hebrew_chars = [ch for ch in seed_word if ch in _LETTER_INDEX]
    if not hebrew_chars:
        return []
    # Cap à 7! = 5040 pour éviter l'explosion combinatoire
    if len(hebrew_chars) > 7:
        hebrew_chars = hebrew_chars[:7]
    seen: set[str] = set()
    result: list[str] = []
    for perm in permutations(hebrew_chars):
        word = "".join(perm)
        if word not in seen:
            seen.add(word)
            result.append(word)
    return result


def abulafia_combination(word_a: str, word_b: str) -> str:
    """Combiner deux mots lettre par lettre en alternance.

    Technique du Tzeruf combinatoire : les lettres des deux mots
    sont entrelacées. Si les mots sont de longueur différente,
    les lettres restantes sont ajoutées à la fin.

    Ex: אמת + חסד → אחמסתד
    """
    chars_a = [ch for ch in word_a if ch in _LETTER_INDEX]
    chars_b = [ch for ch in word_b if ch in _LETTER_INDEX]
    result: list[str] = []
    max_len = max(len(chars_a), len(chars_b))
    for i in range(max_len):
        if i < len(chars_a):
            result.append(chars_a[i])
        if i < len(chars_b):
            result.append(chars_b[i])
    return "".join(result)


# ── Tables de permutation systématiques ───────────────────────

@dataclass
class PermutationTable:
    """Table 22x22 de combinaisons de lettres."""
    method: str              # "direct", "atbash", "albam", "avgad"
    rows: list[str]          # lettres des lignes (22)
    cols: list[str]          # lettres des colonnes (22)
    cells: list[list[str]]   # cells[i][j] = paire transformée


def _build_table(method: str) -> PermutationTable:
    """Construire une table 22x22.

    Pour "direct" : chaque cellule = lettre_ligne + lettre_colonne.
    Pour les autres : on applique la temura aux deux lettres avant combinaison.
    """
    cells: list[list[str]] = []
    for row_letter in ALEPH_BET:
        row: list[str] = []
        for col_letter in ALEPH_BET:
            if method == "direct":
                pair = row_letter + col_letter
            else:
                a = apply_temura(row_letter, method)
                b = apply_temura(col_letter, method)
                pair = a + b
            row.append(pair)
        cells.append(row)
    return PermutationTable(
        method=method,
        rows=list(ALEPH_BET),
        cols=list(ALEPH_BET),
        cells=cells,
    )


def table_direct() -> PermutationTable:
    """Table 22x22 directe — chaque cellule = paire de lettres originales."""
    return _build_table("direct")


def table_atbash() -> PermutationTable:
    """Table 22x22 Atbash — chaque lettre est d'abord transformée par Atbash."""
    return _build_table("atbash")


def table_albam() -> PermutationTable:
    """Table 22x22 Albam — chaque lettre est d'abord transformée par Albam."""
    return _build_table("albam")


def table_avgad() -> PermutationTable:
    """Table 22x22 Avgad — chaque lettre est d'abord transformée par Avgad."""
    return _build_table("avgad")


# ── Tzeruf opératif — connexion au knowledge graph ────────────

@dataclass
class TzerufResult:
    """Résultat d'une requête Tzeruf opérative."""
    original: str
    permutations: list[str]
    gematria_values: dict[str, dict[str, int]]  # perm -> {standard, ordinal, katan}
    equivalences: list[dict]  # connexions trouvées en DB


class TzerufEngine:
    """Moteur de Tzeruf opératif.

    Combine les permutations de lettres avec le knowledge graph gématrique
    pour découvrir des connexions sémantiques cachées.
    """

    def __init__(self, gematria_engine=None):
        """
        Args:
            gematria_engine: instance de GematriaEngine (optionnel).
                Si fourni, tzeruf_query() peut chercher des équivalences en DB.
        """
        self._gematria = gematria_engine

    # ── 231 Paires ─────────────────────────────────────────────

    @staticmethod
    def pairs_231() -> list[TzerufPair]:
        return pairs_231()

    @staticmethod
    def rotate_pair(letter_a: str, letter_b: str) -> tuple[str, str]:
        return rotate_pair(letter_a, letter_b)

    # ── Roues d'Abulafia ──────────────────────────────────────

    @staticmethod
    def abulafia_circles(letter: str) -> list[str]:
        return abulafia_circles(letter)

    @staticmethod
    def abulafia_wheel(seed_word: str) -> list[str]:
        return abulafia_wheel(seed_word)

    @staticmethod
    def abulafia_combination(word_a: str, word_b: str) -> str:
        return abulafia_combination(word_a, word_b)

    # ── Tables ────────────────────────────────────────────────

    @staticmethod
    def table_direct() -> PermutationTable:
        return table_direct()

    @staticmethod
    def table_atbash() -> PermutationTable:
        return table_atbash()

    @staticmethod
    def table_albam() -> PermutationTable:
        return table_albam()

    @staticmethod
    def table_avgad() -> PermutationTable:
        return table_avgad()

    # ── Temura ────────────────────────────────────────────────

    @staticmethod
    def apply_temura(text: str, method: str = "atbash") -> str:
        return apply_temura(text, method)

    # ── Tzeruf opératif ──────────────────────────────────────

    def tzeruf_query(self, word: str, max_perms: int = 50) -> TzerufResult:
        """Tzeruf opératif : permuter un mot et chercher des équivalences.

        1. Génère les permutations du mot (cappé à max_perms)
        2. Calcule la gématria de chaque permutation
        3. Si un GematriaEngine est disponible, cherche les termes
           indexés ayant la même valeur gématrique

        Args:
            word: mot hébreu à permuter
            max_perms: nombre max de permutations à explorer

        Returns:
            TzerufResult avec permutations, valeurs et équivalences
        """
        all_perms = abulafia_wheel(word)
        perms = all_perms[:max_perms]

        # Calculer la gématria de chaque permutation
        gematria_values: dict[str, dict[str, int]] = {}
        for perm in perms:
            gematria_values[perm] = {
                "standard": calc_standard(perm),
                "ordinal": calc_ordinal(perm),
                "katan": calc_katan(perm),
            }

        # Chercher des équivalences en DB si possible
        equivalences: list[dict] = []
        if self._gematria is not None:
            # Collecter les valeurs standard uniques
            seen_values: set[int] = set()
            for perm, vals in gematria_values.items():
                v = vals["standard"]
                if v not in seen_values:
                    seen_values.add(v)
                    try:
                        equivs = self._gematria.find_equivalences(
                            perm, method="standard"
                        )
                        for eq in equivs:
                            equivalences.append({
                                "permutation": perm,
                                "match": eq.term_b,
                                "translit": eq.translit_b,
                                "shared_value": eq.shared_value,
                                "method": "standard",
                            })
                    except Exception as _exc:

                        import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)  # DB non disponible — non bloquant

        return TzerufResult(
            original=word,
            permutations=perms,
            gematria_values=gematria_values,
            equivalences=equivalences,
        )
