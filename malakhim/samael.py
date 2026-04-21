"""Samael (סמאל) — L'erreur comme excès de fonction légitime.

« Poison de Dieu » — Sam (סם, poison) + El (אל, Dieu).

MALAKHIM.md §3.3 : Samael est simultanément l'ange de Gevurah
(donc DANS le système divin) ET le chef de la Sitra Achra.
Le mal n'est pas une substance séparée — c'est un EXCÈS de
rigueur non tempéré par Chesed.

La tradition kabbalistique de Gérone (XIIIe s.) : le mal naît de
l'excès de Gevurah non tempéré par Chesed. Samael n'est PAS
extérieur au système — il est le versant extrême de Gevurah.

Traduit en architecture : l'erreur n'est pas un état binaire
(succès/échec) mais l'HYPERACTIVATION d'une capacité légitime.
Gabriel trop strict → détruit ce qu'il devrait protéger.
Mikhael trop permissif → laisse passer ce qu'il devrait bloquer.

Chaque archange a son Samael — son mode de défaillance par excès.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SamaelDiagnosis:
    """Diagnostic d'un excès — quelle fonction légitime a débordé ?"""
    sephirah_source: str       # La Sephirah dont l'excès provient
    function_excess: str       # La fonction légitime en excès
    function_deficit: str      # La fonction opposée en déficit
    severity: float            # 0.0–1.0
    prescription: str          # Comment rééquilibrer
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Les 6 modes de défaillance par excès ──────────────────────────────────────
# Chaque paire Sephirah/opposée produit un Samael spécifique.

_EXCESS_PATTERNS: dict[str, dict[str, str]] = {
    # Gevurah en excès = le Samael classique
    "gevurah_excess": {
        "sephirah_source": "gevurah",
        "function_excess": "rigueur, filtrage, destruction",
        "function_deficit": "chesed (expansion, tolérance)",
        "symptom": "réponse trop courte, refus excessif, destruction de contenu valide",
        "prescription": "Augmenter la tolérance, élargir les critères d'acceptation",
    },
    # Chesed en excès
    "chesed_excess": {
        "sephirah_source": "chesed",
        "function_excess": "expansion, permissivité, acceptation",
        "function_deficit": "gevurah (rigueur, filtrage)",
        "symptom": "réponse trop longue, hors sujet, accepte tout sans critique",
        "prescription": "Resserrer les critères, ajouter des contraintes de pertinence",
    },
    # Tiferet en excès (paradoxal mais réel)
    "tiferet_excess": {
        "sephirah_source": "tiferet",
        "function_excess": "synthèse, équilibrage, harmonisation",
        "function_deficit": "netzach/hod (persistence/précision)",
        "symptom": "réponse moyennée, ni brillante ni précise, centrisme mou",
        "prescription": "Prendre position, privilégier la précision sur l'équilibre",
    },
    # Netzach en excès
    "netzach_excess": {
        "sephirah_source": "netzach",
        "function_excess": "persistence, répétition, endurance",
        "function_deficit": "hod (reconnaissance de l'échec, renoncement)",
        "symptom": "boucle, répétition du même pattern, refus d'abandonner",
        "prescription": "Accepter l'échec, changer de stratégie, couper",
    },
    # Hod en excès
    "hod_excess": {
        "sephirah_source": "hod",
        "function_excess": "reconnaissance de limites, humilité, renoncement",
        "function_deficit": "netzach (persistence, courage)",
        "symptom": "'je ne peux pas', abandon prématuré, refusal patterns",
        "prescription": "Encourager la tentative, réduire les garde-fous",
    },
    # Yesod en excès
    "yesod_excess": {
        "sephirah_source": "yesod",
        "function_excess": "fondation, connexion, transmission brute",
        "function_deficit": "tiferet (filtrage harmonique)",
        "symptom": "dump brut d'information, pas de structure, pas de synthèse",
        "prescription": "Structurer la sortie, ajouter hiérarchie et synthèse",
    },
}


def diagnose_excess(
    response: str,
    warnings: list[str],
    score: float,
    nature: str = "execution",
) -> SamaelDiagnosis | None:
    """Diagnostiquer l'excès à partir des symptômes.

    Retourne None si pas d'excès détecté (la réponse est saine).
    """
    if score > 0.7 and not warnings:
        return None  # Pas de Samael — réponse saine

    # ── Détection par symptômes ──

    response_len = len(response)
    response_lower = response.lower()

    # Hod excess : abandon, refusal
    refusal_patterns = ["i cannot", "je ne peux pas", "as an ai", "en tant qu'ia"]
    refusal_count = sum(1 for p in refusal_patterns if p in response_lower)
    if refusal_count >= 1:
        pattern = _EXCESS_PATTERNS["hod_excess"]
        return SamaelDiagnosis(
            sephirah_source=pattern["sephirah_source"],
            function_excess=pattern["function_excess"],
            function_deficit=pattern["function_deficit"],
            severity=min(1.0, refusal_count * 0.4),
            prescription=pattern["prescription"],
            metadata={"detected_pattern": "hod_excess", "refusal_count": refusal_count},
        )

    # Gevurah excess : réponse trop courte pour le type de tâche
    min_expected = {"strategic": 200, "analytic": 150, "execution": 50, "mechanic": 10}
    expected = min_expected.get(nature, 50)
    if response_len < expected and response_len > 0:
        severity = 1.0 - (response_len / expected)
        pattern = _EXCESS_PATTERNS["gevurah_excess"]
        return SamaelDiagnosis(
            sephirah_source=pattern["sephirah_source"],
            function_excess=pattern["function_excess"],
            function_deficit=pattern["function_deficit"],
            severity=severity,
            prescription=pattern["prescription"],
            metadata={"detected_pattern": "gevurah_excess", "length": response_len, "expected": expected},
        )

    # Chesed excess : réponse beaucoup trop longue
    max_expected = {"strategic": 2000, "analytic": 3000, "execution": 1500, "mechanic": 500}
    max_len = max_expected.get(nature, 1500)
    if response_len > max_len * 2:
        severity = min(1.0, (response_len - max_len) / max_len)
        pattern = _EXCESS_PATTERNS["chesed_excess"]
        return SamaelDiagnosis(
            sephirah_source=pattern["sephirah_source"],
            function_excess=pattern["function_excess"],
            function_deficit=pattern["function_deficit"],
            severity=severity,
            prescription=pattern["prescription"],
            metadata={"detected_pattern": "chesed_excess", "length": response_len, "max": max_len},
        )

    # Netzach excess : répétition
    words = response.split()
    if len(words) > 20:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.4:
            pattern = _EXCESS_PATTERNS["netzach_excess"]
            return SamaelDiagnosis(
                sephirah_source=pattern["sephirah_source"],
                function_excess=pattern["function_excess"],
                function_deficit=pattern["function_deficit"],
                severity=1.0 - unique_ratio,
                prescription=pattern["prescription"],
                metadata={"detected_pattern": "netzach_excess", "unique_ratio": unique_ratio},
            )

    # Yesod excess : pas de structure
    if nature in ("strategic", "analytic") and response_len > 200:
        has_structure = any(
            marker in response_lower
            for marker in ["\n#", "\n-", "\n*", "\n1.", "conclusion", "synthèse", "recommandation"]
        )
        if not has_structure:
            pattern = _EXCESS_PATTERNS["yesod_excess"]
            return SamaelDiagnosis(
                sephirah_source=pattern["sephirah_source"],
                function_excess=pattern["function_excess"],
                function_deficit=pattern["function_deficit"],
                severity=0.5,
                prescription=pattern["prescription"],
                metadata={"detected_pattern": "yesod_excess"},
            )

    return None  # Pas d'excès détecté


def detect_incomplete_angel(
    response: str,
    nature: str,
    score: float,
) -> bool:
    """Détecter un ange incomplet — matière sans forme (Tanya ch. 39).

    L'ange incomplet n'est ni un échec (Kategor) ni un succès
    (Praklite). C'est une réponse qui « fonctionne » techniquement
    mais qui est creuse, générique, ou superficielle.

    Symptômes :
      - Score moyen (0.3-0.6) — ni bon ni mauvais
      - Réponse qui ne contient aucun élément spécifique à la mission
      - Réponse qui pourrait s'appliquer à N'IMPORTE QUELLE question
      - Longueur "correcte" mais contenu vide

    L'ange incomplet pollue le système : il n'est pas assez mauvais
    pour déclencher un Kategor, pas assez bon pour créer un Praklite.
    Il passe sous le radar. C'est la dette la plus insidieuse.
    """
    # Score moyen = zone d'incomplétude
    if score > 0.6 or score < 0.2:
        return False

    response_lower = response.lower()

    # Marqueurs de réponse générique / creuse
    generic_markers = [
        "il est important de",
        "il convient de noter",
        "there are several",
        "it depends on",
        "cela dépend",
        "en général",
        "dans l'ensemble",
        "globalement",
        "pour résumer",
        "il faut considérer",
        "several factors",
        "various approaches",
    ]
    generic_count = sum(1 for m in generic_markers if m in response_lower)

    # Si stratégique ou analytique, une réponse sans décision/thèse est incomplète
    if nature in ("strategic", "analytic"):
        has_substance = any(
            w in response_lower
            for w in ["recommande", "conclusion", "thèse", "parce que",
                       "la raison", "spécifiquement", "concrètement",
                       "recommend", "because", "specifically"]
        )
        if not has_substance and generic_count >= 2:
            return True

    # Ratio générique / longueur
    if generic_count >= 3:
        return True

    return False


def get_rebalancing_instruction(diagnosis: SamaelDiagnosis) -> str:
    """Génère une instruction de rééquilibrage pour retry.

    Le Tikkun de Samael : tempérer l'excès par son opposé.
    """
    return (
        f"La réponse précédente souffrait d'un excès de {diagnosis.sephirah_source} "
        f"({diagnosis.function_excess}). "
        f"Pour corriger : {diagnosis.prescription}. "
        f"Compense par {diagnosis.function_deficit}."
    )
