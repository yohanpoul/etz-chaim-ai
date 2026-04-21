"""Metatron (מטטרון) — Médiateur vertical adaptatif.

MALAKHIM.md §3.3 : « Metatron a sa tête dans Briah, son corps
éthérique dans Yetzirah, et ses pieds dans Assiah » — il traverse
les trois mondes inférieurs.

3 Hénoch 12:5 : YHVH HaQatan (« le moindre YHVH »).
Titres : Na'ar (jeune serviteur), Sar HaPanim (Prince de la Face),
Sar HaOlam (Prince du Monde).

Gematria : מטטרון = 314 = שדי (Shaddai).

Rôle computationnel : Metatron n'est pas un routeur — c'est un
TRADUCTEUR ONTOLOGIQUE qui reformule la même intention à chaque
niveau du système. La même requête se manifeste différemment
selon le monde :

  Briah   → intention stratégique, abstraite, conceptuelle
  Yetzirah → plan d'exécution structuré, étapes concrètes
  Assiah  → commandes spécifiques, format exact

Combiné avec le modèle Levush de Cordovero (§5.2) :
la Sephirah se « revêt » (mitlabbeshet) d'une forme adaptée
au monde. La même capacité se manifeste différemment à chaque
niveau. Chesed en Atziluth = attribut pur → en Briah = Mikhael →
en Yetzirah = prince des armées → en Assiah = force d'expansion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LevushAdaptation:
    """Une adaptation de la même intention pour un monde donné.

    Levush (לבוש) = vêtement. La Sephirah revêt une forme
    adaptée au monde. L'intention reste la même, la forme change.
    """
    olam: str
    adapted_prompt: str
    adapted_system_prompt: str
    emphasis: str  # ce que ce niveau priorise
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Levush : adaptation par monde ─────────────────────────────────────────────
# La même intention revêt une forme différente à chaque olam.

_LEVUSH_TEMPLATES: dict[str, dict[str, str]] = {
    "atziluth": {
        "emphasis": "vision, intention pure, principes directeurs",
        "frame": (
            "Au niveau le plus élevé de l'abstraction. "
            "Concentre-toi sur l'INTENTION profonde, les PRINCIPES "
            "directeurs, et la VISION d'ensemble. Pas de détails "
            "d'implémentation — seulement la direction."
        ),
    },
    "briah": {
        "emphasis": "architecture, structure, raisonnement",
        "frame": (
            "Au niveau de la création intellectuelle. "
            "Concentre-toi sur l'ARCHITECTURE, la STRUCTURE "
            "logique, et le RAISONNEMENT. Définis les composants "
            "et leurs relations, sans descendre dans le code."
        ),
    },
    "yetzirah": {
        "emphasis": "plan d'exécution, étapes concrètes, processus",
        "frame": (
            "Au niveau de la formation. "
            "Concentre-toi sur le PLAN D'EXÉCUTION : étapes "
            "concrètes, ordre des opérations, inputs/outputs "
            "de chaque étape. Sois spécifique et actionnable."
        ),
    },
    "assiah": {
        "emphasis": "implémentation directe, commandes, format exact",
        "frame": (
            "Au niveau de l'action. "
            "Concentre-toi sur l'EXÉCUTION DIRECTE : code exact, "
            "commandes spécifiques, format de sortie précis. "
            "Pas d'explication — juste le résultat."
        ),
    },
}


def adapt_to_olam(
    prompt: str,
    system_prompt: str,
    olam: str,
    nature: str = "execution",
) -> LevushAdaptation:
    """Adapter l'intention au monde cible (Levush).

    Metatron traverse les mondes et reformule la même
    intention dans la langue de chaque monde.

    Args:
        prompt: le prompt original
        system_prompt: le system prompt existant (du Heikhalot)
        olam: le monde cible (atziluth/briah/yetzirah/assiah)
        nature: la nature ontologique de la tâche

    Returns:
        LevushAdaptation avec le prompt et system prompt adaptés
    """
    template = _LEVUSH_TEMPLATES.get(olam, _LEVUSH_TEMPLATES["yetzirah"])

    # Le system prompt est enrichi avec le cadre du monde
    adapted_system = f"{system_prompt}\n\n[Olam {olam.upper()}] {template['frame']}"

    # Le prompt reste le même — c'est le cadre qui change
    # (l'intention est invariante, le vêtement change)
    adapted_prompt = prompt

    return LevushAdaptation(
        olam=olam,
        adapted_prompt=adapted_prompt,
        adapted_system_prompt=adapted_system,
        emphasis=template["emphasis"],
        metadata={"nature": nature},
    )


def translate_across_worlds(
    prompt: str,
    system_prompt: str,
    source_olam: str,
    target_olam: str,
    nature: str = "execution",
) -> LevushAdaptation:
    """Metatron traduit une intention d'un monde à un autre.

    Quand une requête haute (Briah) doit être exécutée en bas
    (Assiah), Metatron reformule l'intention dans la langue
    du monde cible.

    Symétrie Metatron-Sandalphon (MALAKHIM.md §3.3) :
      Metatron descend (transmission de la lumière divine)
      Sandalphon monte (transmission des prières humaines)

    Ici : Metatron opère la descente adaptative.
    """
    return adapt_to_olam(prompt, system_prompt, target_olam, nature)


def jurisdictional_check(
    agent_domains: list[str],
    target_domain: str,
) -> tuple[bool, str]:
    """Vérifie la juridiction territoriale (Échelle de Jacob).

    Gen 28:12, Rashi (Bereshit Rabbah 68:12) : les anges d'Eretz
    Israël montent, ceux de l'exil descendent. La juridiction
    angélique est TERRITORIALEMENT LIMITÉE.

    Un agent qui a compétence en 'code' ne devrait pas opérer
    en 'poetry' sans autorisation explicite.

    Returns:
        (allowed: bool, reason: str)
    """
    if not agent_domains:
        # Pas de domaines définis → universel (Ishim, le rang le plus bas)
        return True, "Agent sans domaine — juridiction universelle (Ishim)"

    if target_domain in agent_domains:
        return True, f"Domaine {target_domain} dans la juridiction"

    if "general" in agent_domains:
        return True, "Agent à juridiction générale"

    return False, (
        f"Domaine {target_domain} HORS juridiction. "
        f"Domaines autorisés : {', '.join(agent_domains)}. "
        f"(Bereshit Rabbah 68:12 : juridiction territorialement limitée)"
    )
