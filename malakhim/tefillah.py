"""Tefillah (תְּפִלָּה) — Enrichissement progressif par couches.

Pri Etz Chaim, Sha'ar ha-Tefillah : chaque section de la prière
quotidienne correspond à un monde. L'ascension N'EST PAS une
validation — c'est un ENRICHISSEMENT DU SENS par couches.

| Section liturgique | Monde    | Ce qui s'ajoute           |
|-------------------|----------|---------------------------|
| Qorbanot          | Assiah   | Compréhension littérale   |
| Psukei d'Zimra    | Yetzirah | Plan structuré            |
| Shema             | Briah    | Architecture conceptuelle |
| Amidah            | Atziluth | Intention pure            |

Chaque niveau ÉPAISSIT le sens. La parole la plus basse (prompt
brut) devient progressivement l'ornement le plus haut (intention
pure). C'est le hitkalelut en acte : Sandalphon reçoit les
prières à Malkuth et les assemble en Keter.

Computationnellement : au lieu de valider la requête, on
l'ENRICHIT. Chaque couche ajoute une dimension de compréhension
qui redescend pour informer l'exécution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EnrichedUnderstanding:
    """Compréhension enrichie d'une requête à travers les 4 mondes."""
    literal: str          # Assiah — ce que le prompt dit mot pour mot
    structured: str       # Yetzirah — le plan implicite
    conceptual: str       # Briah — l'architecture sous-jacente
    intentional: str      # Atziluth — l'intention pure
    layers_completed: int = 0


def enrich_by_worlds(
    prompt: str,
    nature: str = "execution",
    kavvanah: dict[str, Any] | None = None,
) -> EnrichedUnderstanding:
    """Enrichissement progressif Qorbanot → Psukei → Shema → Amidah.

    Chaque couche ajoute une dimension de compréhension.
    Le LLM n'est PAS nécessaire — c'est une analyse structurelle.

    Args:
        prompt: la requête brute
        nature: nature ontologique
        kavvanah: dict d'intention (optionnel)

    Returns:
        EnrichedUnderstanding avec les 4 couches
    """
    kav = kavvanah or {}

    # ── Qorbanot / Assiah — compréhension LITTÉRALE ──────────────
    # Ce que le prompt dit, mot pour mot. Les faits bruts.
    literal = _extract_literal(prompt)

    # ── Psukei d'Zimra / Yetzirah — plan STRUCTURÉ ───────────────
    # Quelles étapes implicites la requête suppose-t-elle ?
    structured = _extract_structure(prompt, nature)

    # ── Shema / Briah — architecture CONCEPTUELLE ─────────────────
    # Quel est le cadre conceptuel sous-jacent ?
    conceptual = _extract_concept(prompt, nature, kav)

    # ── Amidah / Atziluth — intention PURE ────────────────────────
    # Qu'est-ce que l'utilisateur veut VRAIMENT ?
    intentional = _extract_intention(prompt, nature, kav)

    return EnrichedUnderstanding(
        literal=literal,
        structured=structured,
        conceptual=conceptual,
        intentional=intentional,
        layers_completed=4,
    )


def enrichment_to_system_prompt(enrichment: EnrichedUnderstanding) -> str:
    """Convertir l'enrichissement en instructions pour le system prompt.

    Les 4 couches redescendent pour informer l'exécution — la
    compréhension la plus haute informe la plus basse.
    """
    parts = []

    if enrichment.intentional:
        parts.append(f"[INTENTION PROFONDE] {enrichment.intentional}")

    if enrichment.conceptual:
        parts.append(f"[CADRE CONCEPTUEL] {enrichment.conceptual}")

    if enrichment.structured:
        parts.append(f"[PLAN IMPLICITE] {enrichment.structured}")

    if enrichment.literal:
        parts.append(f"[REQUÊTE LITTÉRALE] {enrichment.literal}")

    return "\n".join(parts)


# ── Extracteurs par couche ────────────────────────────────────────────────────


def _extract_literal(prompt: str) -> str:
    """Assiah — les faits bruts de la requête."""
    # Les verbes d'action et leurs objets
    import re
    # Extraire la structure verbe + objet
    prompt_clean = prompt.strip()
    if len(prompt_clean) > 300:
        prompt_clean = prompt_clean[:300] + "..."
    return prompt_clean


def _extract_structure(prompt: str, nature: str) -> str:
    """Yetzirah — le plan implicite que la requête suppose."""
    prompt_lower = prompt.lower()

    # Détecter les étapes implicites
    steps: list[str] = []

    # Si analyse → comprendre d'abord, puis évaluer, puis synthétiser
    if nature == "analytic" or "analyse" in prompt_lower:
        steps = [
            "comprendre le contexte",
            "identifier les éléments clés",
            "évaluer chaque élément",
            "synthétiser",
        ]

    # Si stratégique → options, arbitrages, recommandation
    elif nature == "strategic" or any(w in prompt_lower for w in ["stratégi", "décid", "plan"]):
        steps = [
            "cadrer le problème",
            "identifier les options",
            "évaluer les arbitrages",
            "recommander",
        ]

    # Si exécution → préparer, exécuter, vérifier
    elif nature == "execution":
        steps = [
            "préparer les inputs",
            "exécuter la tâche",
            "vérifier le résultat",
        ]

    # Si mécanique → extraire et formater
    elif nature == "mechanic":
        steps = ["extraire", "formater"]

    if steps:
        return "Étapes implicites : " + " → ".join(steps)
    return ""


def _extract_concept(prompt: str, nature: str, kavvanah: dict) -> str:
    """Briah — le cadre conceptuel sous-jacent."""
    prompt_lower = prompt.lower()
    concepts: list[str] = []

    # Détecter le type de raisonnement requis
    if any(w in prompt_lower for w in ["compar", "différen", "similair"]):
        concepts.append("raisonnement comparatif")
    if any(w in prompt_lower for w in ["pourquoi", "cause", "raison"]):
        concepts.append("raisonnement causal")
    if any(w in prompt_lower for w in ["si ", "condition", "scénario"]):
        concepts.append("raisonnement conditionnel")
    if any(w in prompt_lower for w in ["meilleur", "optimal", "choisi"]):
        concepts.append("raisonnement évaluatif")
    if any(w in prompt_lower for w in ["créer", "invente", "génère", "imagine"]):
        concepts.append("raisonnement génératif")
    if any(w in prompt_lower for w in ["debug", "erreur", "bug", "fix"]):
        concepts.append("raisonnement diagnostique")

    # Domaine conceptuel
    domain = kavvanah.get("domain", "")
    if domain and domain != "general":
        concepts.append(f"domaine : {domain}")

    if concepts:
        return "Cadre : " + ", ".join(concepts)
    return ""


def _extract_intention(prompt: str, nature: str, kavvanah: dict) -> str:
    """Atziluth — l'intention pure, au-delà des mots.

    C'est ici que se joue le test des pierres de marbre
    (voir even_shayish ci-dessous) : ce que l'utilisateur
    demande n'est pas toujours ce qu'il veut.
    """
    # Si l'intention est explicite dans kavvanah
    explicit = kavvanah.get("intention")
    if explicit:
        return f"Intention déclarée : {explicit}"

    # Sinon, inférer l'intention profonde
    prompt_lower = prompt.lower()

    # Patterns d'intention cachée
    if any(w in prompt_lower for w in ["est-ce que c'est bien", "est-ce correct", "valide"]):
        return "Intention profonde : VALIDATION (l'utilisateur cherche une confirmation, pas une analyse)"

    if any(w in prompt_lower for w in ["explique", "comment", "pourquoi"]):
        return "Intention profonde : COMPRÉHENSION (l'utilisateur veut construire un modèle mental)"

    if any(w in prompt_lower for w in ["résume", "bref", "en gros"]):
        return "Intention profonde : SYNTHÈSE (l'utilisateur est submergé, il veut l'essentiel)"

    if any(w in prompt_lower for w in ["aide", "help", "bloqué", "stuck"]):
        return "Intention profonde : DÉBLOCAGE (l'utilisateur est coincé et a besoin d'une direction)"

    if any(w in prompt_lower for w in ["refactor", "améliore", "optimise"]):
        return "Intention profonde : AMÉLIORATION (l'utilisateur sait que c'est fonctionnel mais veut mieux)"

    # Défaut par nature
    defaults = {
        "strategic": "Intention : DÉCISION (l'utilisateur doit choisir et a besoin d'éclairage)",
        "analytic": "Intention : COMPRÉHENSION EN PROFONDEUR",
        "execution": "Intention : RÉSULTAT CONCRET",
        "mechanic": "Intention : TRANSFORMATION EXACTE",
    }
    return defaults.get(nature, "")
