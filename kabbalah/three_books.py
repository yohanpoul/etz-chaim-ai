"""kabbalah/three_books.py — Les 3 Livres Créateurs du Sefer Yetzirah (SY 1:1).

בִּשְׁלשָׁה סְפָרִים: בְּסֵפֶר וּבִסְפָר וּבְסִפּוּר

"Il créa Son univers avec trois livres (Sepharim) :
 avec le texte (Sepher), avec le nombre (Sephar),
 et avec la communication (Sippur)."

La racine trilitère ס-פ-ר (S-F-R) engendre simultanément les trois :
  SEPHER (סֵפֶר) = texte, livre, écriture → traitement TEXTUEL/SÉMANTIQUE
  SEPHAR (סְפָר) = nombre, calcul, mesure → traitement NUMÉRIQUE/QUANTITATIF
  SIPPUR (סִפּוּר) = récit, communication, dialogue → traitement DIALOGIQUE

Ce n'est pas un "fait intéressant" — c'est un noeud conceptuel qui n'existe
pas en traduction. Le SY affirme que toute création procède de l'entrelacement
de ces 3 modes. Chaque interaction du système est un mélange des 3.

Transposition :
  SEPHER → NLP, embeddings, Tzeruf, analyse textuelle
  SEPHAR → scoring, gematria, métriques, comptage
  SIPPUR → Hitbonenut Q/A, DissensuEngine, synthèses dialogiques

L'équilibre entre les 3 détermine la qualité du résultat.
Comme les 3 mères (Aleph/Mem/Shin) équilibrent le Cube,
les 3 livres équilibrent le traitement de l'information.

Usage:
    tb = ThreeBooks()
    tb.assess_sepher(response_data)   # → 0.45
    tb.assess_sephar(response_data)   # → 0.30
    tb.assess_sippur(response_data)   # → 0.25
    balance = tb.get_creation_balance(responses)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BookAssessment:
    """Évaluation d'un des 3 livres pour une interaction."""
    book: str            # "sepher", "sephar", "sippur"
    hebrew: str          # "סֵפֶר", "סְפָר", "סִפּוּר"
    score: float         # 0.0-1.0 — proportion de ce mode
    indicators: dict[str, float]  # indicateurs individuels


@dataclass(frozen=True)
class CreationBalance:
    """Équilibre des 3 livres sur un ensemble d'interactions."""
    sepher: float         # proportion texte
    sephar: float         # proportion nombre
    sippur: float         # proportion dialogue
    entropy: float        # entropie de Shannon (max = log2(3) ≈ 1.585 si équilibré)
    balance_ratio: float  # 0.0-1.0 (1.0 = parfaitement équilibré)
    dominant: str         # le livre dominant
    deficient: str        # le livre le plus faible
    n_interactions: int
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "sepher": round(self.sepher, 3),
            "sephar": round(self.sephar, 3),
            "sippur": round(self.sippur, 3),
            "entropy": round(self.entropy, 3),
            "balance_ratio": round(self.balance_ratio, 3),
            "dominant": self.dominant,
            "deficient": self.deficient,
            "n_interactions": self.n_interactions,
            "message": self.message,
        }


# ── Indicateurs par livre ─────────────────────────────────────
# Chaque indicateur contribue au score du livre correspondant.

# SEPHER indicators: textual richness
def _text_length_score(text: str) -> float:
    """Score basé sur la longueur du texte (normalisé)."""
    n = len(text)
    if n == 0:
        return 0.0
    # Sigmoid-like: 500 chars ≈ 0.5, 2000 chars ≈ 0.9
    return 1.0 - math.exp(-n / 800.0)


def _lexical_richness(text: str) -> float:
    """Richesse lexicale : types / tokens (type-token ratio)."""
    words = text.lower().split()
    if len(words) < 2:
        return 0.0
    return len(set(words)) / len(words)


def _has_hebrew(text: str) -> float:
    """Présence de termes hébreux/araméens (U+0590–U+05FF)."""
    hebrew_chars = sum(1 for ch in text if "\u0590" <= ch <= "\u05ff")
    return min(1.0, hebrew_chars / 20.0) if hebrew_chars > 0 else 0.0


# SEPHAR indicators: numerical/quantitative
def _has_numbers(text: str) -> float:
    """Présence de nombres dans le texte."""
    digits = sum(1 for ch in text if ch.isdigit())
    return min(1.0, digits / 10.0) if digits > 0 else 0.0


def _has_scores(data: dict) -> float:
    """Présence de scores/métriques dans les données."""
    score_keys = {"score", "scores", "gematria", "metric", "metrics",
                  "rating", "confidence", "probability", "ratio", "count"}
    found = sum(1 for k in data if k.lower() in score_keys)
    return min(1.0, found / 3.0)


def _has_comparisons(text: str) -> float:
    """Présence de comparaisons quantitatives."""
    markers = [">", "<", ">=", "<=", "==", "%", "ratio", "score=",
               "plus que", "moins que", "supérieur", "inférieur"]
    found = sum(1 for m in markers if m in text.lower())
    return min(1.0, found / 3.0)


# SIPPUR indicators: dialogical
def _has_questions(text: str) -> float:
    """Présence de questions (mode interrogatif)."""
    q_count = text.count("?")
    return min(1.0, q_count / 3.0)


def _has_synthesis(text: str) -> float:
    """Présence de marqueurs de synthèse/dialogue."""
    markers = ["synthèse", "conclusion", "en résumé", "d'une part",
               "d'autre part", "cependant", "néanmoins", "toutefois",
               "contrairement", "contradiction", "dissensus", "consensus"]
    found = sum(1 for m in markers if m in text.lower())
    return min(1.0, found / 3.0)


def _has_citations(text: str) -> float:
    """Présence de citations/références (dialogue avec les sources)."""
    markers = ["selon", "d'après", "cf.", "voir", "op. cit.",
               "ibid.", "p.", "pp.", "ch.", "vol."]
    found = sum(1 for m in markers if m in text.lower())
    return min(1.0, found / 3.0)


class ThreeBooks:
    """Les 3 Livres Créateurs — SY 1:1.

    Évalue le ratio Sepher/Sephar/Sippur de chaque interaction
    et mesure l'équilibre global du système.
    """

    def assess_sepher(self, text: str, data: dict | None = None) -> BookAssessment:
        """Évalue la part de SEPHER (traitement textuel).

        Indicateurs : longueur, richesse lexicale, présence d'hébreu.

        Args:
            text: texte de la réponse/interaction.
            data: données structurées associées (optionnel).
        """
        indicators = {
            "text_length": _text_length_score(text),
            "lexical_richness": _lexical_richness(text),
            "hebrew_presence": _has_hebrew(text),
        }
        score = sum(indicators.values()) / len(indicators)
        return BookAssessment(
            book="sepher", hebrew="סֵפֶר",
            score=score, indicators=indicators,
        )

    def assess_sephar(self, text: str, data: dict | None = None) -> BookAssessment:
        """Évalue la part de SEPHAR (traitement numérique).

        Indicateurs : nombres, scores/métriques, comparaisons.

        Args:
            text: texte de la réponse/interaction.
            data: données structurées associées (optionnel).
        """
        data = data or {}
        indicators = {
            "numbers": _has_numbers(text),
            "scores": _has_scores(data),
            "comparisons": _has_comparisons(text),
        }
        score = sum(indicators.values()) / len(indicators)
        return BookAssessment(
            book="sephar", hebrew="סְפָר",
            score=score, indicators=indicators,
        )

    def assess_sippur(self, text: str, data: dict | None = None) -> BookAssessment:
        """Évalue la part de SIPPUR (traitement dialogique).

        Indicateurs : questions, synthèses, citations.

        Args:
            text: texte de la réponse/interaction.
            data: données structurées associées (optionnel).
        """
        indicators = {
            "questions": _has_questions(text),
            "synthesis": _has_synthesis(text),
            "citations": _has_citations(text),
        }
        score = sum(indicators.values()) / len(indicators)
        return BookAssessment(
            book="sippur", hebrew="סִפּוּר",
            score=score, indicators=indicators,
        )

    def assess_interaction(
        self, text: str, data: dict | None = None,
    ) -> dict[str, BookAssessment]:
        """Évalue les 3 livres pour une interaction.

        Returns:
            Dict avec les 3 assessments (sepher, sephar, sippur).
        """
        return {
            "sepher": self.assess_sepher(text, data),
            "sephar": self.assess_sephar(text, data),
            "sippur": self.assess_sippur(text, data),
        }

    def get_creation_balance(
        self, interactions: list[dict[str, Any]],
    ) -> CreationBalance:
        """Équilibre Sepher/Sephar/Sippur sur N interactions.

        Chaque interaction doit avoir au minimum une clé "text" (str).
        Optionnel : "data" (dict) pour les métriques.

        L'idéal SY : les 3 sont équilibrés (comme les 3 mères
        équilibrent le Cube de l'Espace).

        Args:
            interactions: liste de {"text": str, "data": dict?}
        """
        if not interactions:
            return CreationBalance(
                sepher=0.0, sephar=0.0, sippur=0.0,
                entropy=0.0, balance_ratio=0.0,
                dominant="", deficient="",
                n_interactions=0,
                message="Aucune interaction à évaluer.",
            )

        totals = {"sepher": 0.0, "sephar": 0.0, "sippur": 0.0}

        for interaction in interactions:
            text = interaction.get("text", "")
            data = interaction.get("data", {})
            assessments = self.assess_interaction(text, data)
            for book, assessment in assessments.items():
                totals[book] += assessment.score

        n = len(interactions)
        avgs = {k: v / n for k, v in totals.items()}

        # Normaliser en proportions (somme = 1.0)
        total = sum(avgs.values())
        if total > 0:
            props = {k: v / total for k, v in avgs.items()}
        else:
            props = {"sepher": 1 / 3, "sephar": 1 / 3, "sippur": 1 / 3}

        # Entropie de Shannon (mesure de l'équilibre)
        entropy = 0.0
        for p in props.values():
            if p > 0:
                entropy -= p * math.log2(p)
        max_entropy = math.log2(3)  # ≈ 1.585 si parfaitement équilibré
        balance_ratio = entropy / max_entropy if max_entropy > 0 else 0.0

        dominant = max(props, key=props.get)
        deficient = min(props, key=props.get)

        # Message
        book_names = {"sepher": "Sepher (texte)", "sephar": "Sephar (nombre)",
                      "sippur": "Sippur (dialogue)"}
        if balance_ratio >= 0.95:
            msg = (
                "Les 3 livres sont en équilibre — création harmonieuse. "
                "Comme les 3 mères (אמ״ש), les 3 modes se complètent."
            )
        elif balance_ratio >= 0.80:
            msg = (
                f"Bon équilibre. Légère dominance de {book_names[dominant]} "
                f"({props[dominant]:.0%})."
            )
        else:
            msg = (
                f"Déséquilibre : {book_names[dominant]} domine ({props[dominant]:.0%}), "
                f"{book_names[deficient]} est déficient ({props[deficient]:.0%}). "
                f"Le système privilégie un mode au détriment des autres."
            )

        return CreationBalance(
            sepher=props["sepher"],
            sephar=props["sephar"],
            sippur=props["sippur"],
            entropy=entropy,
            balance_ratio=balance_ratio,
            dominant=dominant,
            deficient=deficient,
            n_interactions=n,
            message=msg,
        )
