"""LanguageEnforcer — forcer le langage causal approprié.

Anti-Satariel Ruach : ne JAMAIS dire "cause" quand on a
seulement une corrélation. Le langage doit MÉRITER ses verbes.

Niveaux de langage :
  correlation_only → "est associé à", "est corrélé avec", "co-occur avec"
  probable_causation → "contribue probablement à", "semble causer"
  demonstrated_causation → "cause", "provoque", "entraîne"

Strictness (Malkuth-dans-Binah) :
  "strict" : correction systématique
  "moderate" : correction + explication
  "permissive" : suggestion seulement
"""

from __future__ import annotations

import re

from causalengine.models import LanguageCorrection


# Patterns de langage causal injustifié
CAUSAL_PATTERNS = [
    # Verbes causaux forts
    (r"\b(causes?|provoque[sn]?t?|entraîne[sn]?t?|produi[ts]?|génère[sn]?t?)\b", "strong_causal"),
    # Verbes causaux modérés
    (r"\b(contribue[sn]?t?\s+à|mène\s+à|condui[ts]?\s+à|résulte\s+en)\b", "moderate_causal"),
    # Formulations causales implicites
    (r"\b(grâce\s+à|à\s+cause\s+de|en\s+raison\s+de|du\s+fait\s+de)\b", "implicit_causal"),
    # Anglais — verbes causaux forts
    (r"\b(leads?\s+to|results?\s+in|brings?\s+about|triggers?)\b", "strong_causal"),
    # "X improves Y" — causal implicite
    (r"\b(improves?|increases?|decreases?|reduces?|enhances?|boosts?)\b", "implicit_causal"),
    # "X améliore Y"
    (r"\b(améliore[sn]?t?|augmente[sn]?t?|diminue[sn]?t?|rédui[ts]?|renforce[sn]?t?)\b", "implicit_causal"),
]

# Remplacements par niveau
REPLACEMENTS = {
    "correlation_only": {
        "strong_causal": "is associated with",
        "moderate_causal": "is correlated with",
        "implicit_causal": "co-occurs with",
    },
    "probable_causation": {
        "strong_causal": "likely contributes to",
        "moderate_causal": "probably influences",
        "implicit_causal": "may be linked to",
    },
    "demonstrated_causation": {
        # À ce niveau, le langage causal est justifié
        "strong_causal": None,  # pas de correction
        "moderate_causal": None,
        "implicit_causal": None,
    },
}


class LanguageEnforcer:
    """Force le langage approprié au niveau de preuve.

    Le gardien de Malkuth-dans-Binah : les mots doivent
    correspondre à ce qui a été démontré, pas à ce qu'on
    voudrait croire.
    """

    def __init__(self, strictness: str = "strict"):
        """
        Args:
            strictness: "strict", "moderate", ou "permissive"
        """
        if strictness not in ("strict", "moderate", "permissive"):
            raise ValueError(f"Invalid strictness: {strictness}")
        self.strictness = strictness

    def check(
        self,
        text: str,
        evidence_level: str = "correlation_only",
    ) -> list[LanguageCorrection]:
        """Vérifier le langage d'un texte par rapport au niveau de preuve.

        Returns:
            Liste de corrections nécessaires (vide si tout est OK).
        """
        corrections: list[LanguageCorrection] = []

        if evidence_level == "demonstrated_causation":
            # À ce niveau, tout langage causal est justifié
            return corrections

        for pattern, category in CAUSAL_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                original = match.group(0)
                replacement = REPLACEMENTS.get(evidence_level, {}).get(category)

                if replacement is not None:
                    reason = self._format_reason(
                        original, evidence_level, category,
                    )
                    corrections.append(LanguageCorrection(
                        original=original,
                        corrected=replacement,
                        evidence_level=evidence_level,
                        reason=reason,
                    ))

        return corrections

    def enforce(
        self,
        text: str,
        evidence_level: str = "correlation_only",
    ) -> tuple[str, list[LanguageCorrection]]:
        """Corriger le texte — appliquer les corrections.

        Returns:
            (corrected_text, list of corrections applied)
        """
        corrections = self.check(text, evidence_level)

        if not corrections:
            return text, []

        if self.strictness == "permissive":
            # En mode permissive, on ne modifie pas le texte
            return text, corrections

        corrected = text
        applied: list[LanguageCorrection] = []

        for correction in corrections:
            if correction.original in corrected:
                corrected = corrected.replace(
                    correction.original, correction.corrected, 1,
                )
                applied.append(correction)

        return corrected, applied

    def appropriate_language(self, evidence_level: str) -> list[str]:
        """Renvoyer les formulations appropriées pour un niveau de preuve.

        Returns:
            Liste de formulations acceptables.
        """
        if evidence_level == "correlation_only":
            return [
                "is associated with",
                "is correlated with",
                "co-occurs with",
                "tends to co-occur with",
                "shows a statistical relationship with",
            ]
        elif evidence_level == "observed_association":
            return [
                "is observed alongside",
                "has been noted in association with",
                "recurrently co-appears with",
                "is documented in multiple contexts with",
            ]
        elif evidence_level == "probable_causation":
            return [
                "likely contributes to",
                "probably influences",
                "may be linked to",
                "appears to affect",
                "is a probable contributor to",
            ]
        elif evidence_level == "demonstrated_causation":
            return [
                "causes",
                "leads to",
                "produces",
                "triggers",
                "results in",
                "brings about",
            ]
        return []

    def suggest_rewrite(
        self,
        text: str,
        evidence_level: str = "correlation_only",
    ) -> str:
        """Suggérer une réécriture complète du texte.

        Plus agressif que enforce() — reformule la phrase entière
        si nécessaire.
        """
        corrected, corrections = self.enforce(text, evidence_level)

        if not corrections:
            return text

        if self.strictness == "strict":
            return corrected

        # En mode moderate, ajouter une note explicative
        if self.strictness == "moderate" and corrections:
            note = (
                f" [Note: evidence level is '{evidence_level}' — "
                f"causal language adjusted to match]"
            )
            return corrected + note

        return corrected

    def _format_reason(
        self,
        original: str,
        evidence_level: str,
        category: str,
    ) -> str:
        """Formater la raison d'une correction."""
        level_descriptions = {
            "correlation_only": "only correlation observed",
            "observed_association": "observed association, not yet causal",
            "probable_causation": "probable causation, not demonstrated",
        }
        category_descriptions = {
            "strong_causal": "strong causal verb",
            "moderate_causal": "moderate causal expression",
            "implicit_causal": "implicit causal framing",
        }

        level_desc = level_descriptions.get(evidence_level, evidence_level)
        cat_desc = category_descriptions.get(category, category)

        return (
            f"'{original}' is a {cat_desc} but evidence level is "
            f"'{evidence_level}' ({level_desc})"
        )
