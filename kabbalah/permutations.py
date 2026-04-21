"""kabbalah/permutations.py — Permutations Créatrices du Sefer Yetzirah (SY 2:5).

שְׁתַּיִם אֲבָנִים בּוֹנוֹת שְׁנֵי בָתִּים, שָׁלשׁ אֲבָנִים בּוֹנוֹת שִׁשָּׁה בָתִּים...
מִכָּאן וְאֵילָךְ צֵא וַחֲשׁוֹב מַה שֶּׁאֵין הַפֶּה יָכוֹל לְדַבֵּר וְאֵין הָאוֹזֶן יְכוֹלָה לִשְׁמוֹעַ

"2 pierres bâtissent 2 maisons, 3 pierres bâtissent 6 maisons,
 4 pierres bâtissent 24 maisons, 5 pierres 120, 6 pierres 720,
 7 pierres 5040. De là, va et calcule ce que la bouche ne peut
 dire et l'oreille ne peut entendre."

Le SY donne la PREMIÈRE description explicite de la factorielle n! dans
l'histoire intellectuelle. Les "pierres" (avanim) sont les lettres ;
les "maisons" (batim) sont les réalités engendrées par leurs permutations.

La complexité combinatoire d'un mot = n! de ses lettres.
La complexité d'un domaine = n! de ses concepts clés.

Le seuil "au-delà de l'ouïe" (Kaplan) : 8 lettres = 40320 permutations.
À raison de 8 lettres par permutation, cela fait 322560 lettres à prononcer
— ce que la bouche ne peut dire.

Usage:
    cp = CreativePermutations()
    cp.houses(7)                    # → 5040
    cp.word_complexity("בראשית")     # → 720 (6 lettres)
    cp.domain_complexity("kabbale", 12)  # → 479001600
    cp.beyond_hearing(8)            # → True
    cp.compare_complexity("אב", "אבגד")  # → 12.0 (24/2)
"""

from __future__ import annotations

import math
from dataclasses import dataclass


# ── Seuil "au-delà de l'ouïe" ──────────────────────────────
# Kaplan (1990, pp. 100-103) : à partir de 8 lettres, le nombre
# de permutations × la longueur du mot dépasse ce qu'un humain
# peut prononcer dans une vie. Le SY s'arrête à 7 (5040).
BEYOND_HEARING_THRESHOLD = 8


@dataclass(frozen=True)
class ComplexityProfile:
    """Profil de complexité combinatoire d'un mot ou domaine."""
    name: str
    n: int                  # nombre de pierres (lettres ou concepts)
    houses: int             # n! — nombre de maisons
    beyond_hearing: bool    # True si n >= 8
    pronunciation_load: int  # n! × n — charge totale de prononciation


class CreativePermutations:
    """Permutations créatrices — SY 2:5.

    Calcule la complexité combinatoire selon le principe du SY :
    n pierres (lettres) bâtissent n! maisons (réalités).
    """

    # Les exemples explicites du SY (vérification)
    SY_EXAMPLES = {2: 2, 3: 6, 4: 24, 5: 120, 6: 720, 7: 5040}

    def houses(self, n: int) -> int:
        """Nombre de maisons (batim) que n pierres (avanim) bâtissent.

        SY 2:5 : n pierres → n! maisons.

        Args:
            n: nombre de pierres (lettres). Doit être >= 0.

        Returns:
            n! (la factorielle).
        """
        if n < 0:
            raise ValueError(f"Le nombre de pierres doit être >= 0, reçu: {n}")
        return math.factorial(n)

    def word_complexity(self, word: str) -> int:
        """Complexité combinatoire d'un mot hébreu.

        Chaque lettre du mot est une "pierre" ; la complexité = len(word)!

        Args:
            word: mot hébreu (ou toute chaîne). Les espaces sont ignorés.

        Returns:
            Factorielle du nombre de lettres.
        """
        letters = [ch for ch in word if not ch.isspace()]
        return math.factorial(len(letters))

    def domain_complexity(self, domain: str, n_concepts: int) -> int:
        """Complexité combinatoire d'un domaine.

        Un domaine avec n concepts clés = n! "maisons" possibles.
        Plus un domaine a de concepts, plus il est intrinsèquement
        complexe — exponentiellement.

        Args:
            domain: nom du domaine (pour le profil).
            n_concepts: nombre de concepts clés du domaine.

        Returns:
            n_concepts!
        """
        if n_concepts < 0:
            raise ValueError(f"n_concepts doit être >= 0, reçu: {n_concepts}")
        return math.factorial(n_concepts)

    def beyond_hearing(self, n: int) -> bool:
        """Le nombre de permutations dépasse-t-il ce que l'oreille peut entendre ?

        SY 2:5 : "De là, va et calcule ce que la bouche ne peut dire
        et l'oreille ne peut entendre."

        Le SY s'arrête à 7 pierres (5040). À partir de 8, la charge
        de prononciation (n! × n lettres par permutation) dépasse
        ce qu'un humain peut articuler.

        Kaplan (1990, p. 103) : 8! = 40320 permutations × 8 = 322560 lettres.

        Args:
            n: nombre de pierres.
        """
        return n >= BEYOND_HEARING_THRESHOLD

    def compare_complexity(self, word_a: str, word_b: str) -> float:
        """Ratio de complexité entre deux mots.

        Retourne complexity(word_b) / complexity(word_a).
        Un ratio > 1 signifie que word_b est plus complexe.

        Args:
            word_a: premier mot (dénominateur).
            word_b: second mot (numérateur).

        Returns:
            Ratio de complexité (float). Inf si word_a est vide.
        """
        ca = self.word_complexity(word_a)
        cb = self.word_complexity(word_b)
        if ca == 0:
            return float("inf")
        return cb / ca

    def get_profile(self, name: str, n: int) -> ComplexityProfile:
        """Profil complet de complexité.

        Args:
            name: nom de l'entité (mot, domaine).
            n: nombre de pierres/concepts.
        """
        h = self.houses(n)
        return ComplexityProfile(
            name=name,
            n=n,
            houses=h,
            beyond_hearing=self.beyond_hearing(n),
            pronunciation_load=h * n,
        )

    def complexity_bonus(self, n_concepts: int, base_score: float = 1.0) -> float:
        """Bonus de scoring basé sur la complexité d'un domaine.

        Un domaine plus complexe (plus de concepts) mérite un bonus
        logarithmique pour pondérer la difficulté intrinsèque.

        Le bonus est log2(n!) / log2(7!) normalisé par rapport à 7
        (le maximum explicite du SY, 5040 maisons).

        Args:
            n_concepts: nombre de concepts du domaine.
            base_score: score de base à pondérer.

        Returns:
            Score pondéré par la complexité.
        """
        if n_concepts <= 1:
            return base_score
        # Normalisation par rapport à 7 pierres (SY maximum explicite)
        ref = math.log2(math.factorial(7))  # log2(5040) ≈ 12.3
        raw = math.log2(math.factorial(n_concepts))
        bonus = raw / ref  # 1.0 pour n=7, >1.0 pour n>7, <1.0 pour n<7
        return base_score * bonus
