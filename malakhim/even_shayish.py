"""Even Shayish (אבני שיש) — Le test des pierres de marbre.

Chagigah 14b / Heikhalot Rabbati : au sixième palais, l'adepte
voit les murs d'albâtre (*even shayish tahor*) comme des vagues
destructrices. Le gardien crie : « Ne dites pas "Eau ! Eau !"
car celui qui ment ne tiendra pas devant Mes yeux. »

Le test est ÉPISTÉMIQUE : confondre l'apparence et la réalité
disqualifie l'ascendant.

Traduit en architecture : détecter quand l'utilisateur confond
ce qu'il DEMANDE avec ce qu'il A BESOIN.

Exemples :
  - "Analyse ce code" → apparence : analyse. Réalité : "rassure-moi"
  - "Fix this bug" → apparence : correction. Réalité : "réécris tout"
  - "Explique X" → apparence : explication. Réalité : "je ne comprends
    rien, commence par les bases"
  - "Résume" → apparence : synthèse. Réalité : "c'est trop long,
    dis-moi juste si c'est important"

Le système qui distingue l'intention APPARENTE de l'intention
RÉELLE donne des réponses radicalement meilleures.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MarbleTestResult:
    """Résultat du test des pierres de marbre."""
    apparent_intent: str       # Ce que le prompt SEMBLE demander
    probable_real_intent: str  # Ce que l'utilisateur VEUT probablement
    divergence: float          # 0.0 = aligné, 1.0 = complètement divergent
    adjustment: str            # Comment ajuster la réponse
    signal: str                # Le signal qui a révélé la divergence


# ── Patterns de divergence intention apparente / réelle ───────────────────────

_DIVERGENCE_PATTERNS: list[dict[str, Any]] = [
    {
        "signals": ["est-ce que c'est bien", "est-ce correct", "c'est bon",
                     "is this ok", "is this correct", "does this look right"],
        "apparent": "demande d'analyse objective",
        "real": "demande de VALIDATION — l'utilisateur veut être rassuré, pas critiqué",
        "adjustment": (
            "L'utilisateur cherche une validation. Commence par confirmer "
            "ce qui fonctionne AVANT de mentionner les problèmes. "
            "Structure : points forts d'abord, puis améliorations possibles."
        ),
        "divergence": 0.6,
    },
    {
        "signals": ["je comprends pas", "je ne comprends pas", "confused",
                     "c'est quoi", "explique", "explain"],
        "apparent": "demande d'explication technique",
        "real": "demande de PÉDAGOGIE — l'utilisateur admet ne pas comprendre",
        "adjustment": (
            "L'utilisateur admet une incompréhension. Ne PAS répondre "
            "au niveau technique demandé — descendre d'un cran. "
            "Utiliser des analogies, partir des bases."
        ),
        "divergence": 0.5,
    },
    {
        "signals": ["résume", "en gros", "tl;dr", "bref", "en résumé"],
        "apparent": "demande de synthèse structurée",
        "real": "demande de TRIAGE — l'utilisateur est submergé et veut savoir si ça vaut le coup de lire",
        "adjustment": (
            "L'utilisateur est submergé. Donner d'abord LE verdict "
            "en une phrase, puis les 3 points clés max. "
            "Pas de structure élaborée — juste l'essentiel."
        ),
        "divergence": 0.4,
    },
    {
        "signals": ["aide", "help", "bloqué", "stuck", "marche pas",
                     "doesn't work", "ne fonctionne pas"],
        "apparent": "demande de solution technique",
        "real": "demande de DÉBLOCAGE — l'utilisateur est frustré et a besoin d'une direction, pas d'une solution complète",
        "adjustment": (
            "L'utilisateur est bloqué et probablement frustré. "
            "Donner d'abord UNE action immédiate à tenter. "
            "Puis expliquer pourquoi. Le déblocage émotionnel "
            "précède le déblocage technique."
        ),
        "divergence": 0.5,
    },
    {
        "signals": ["refactor", "clean up", "améliore", "optimise", "rends plus propre"],
        "apparent": "demande d'optimisation incrémentale",
        "real": "demande de RÉÉCRITURE — l'utilisateur sait que le code est mauvais mais n'ose pas dire 'réécris tout'",
        "adjustment": (
            "L'utilisateur dit 'améliore' mais pense possiblement "
            "'réécris'. Évaluer honnêtement : si >40% doit changer, "
            "proposer une réécriture plutôt qu'un patch."
        ),
        "divergence": 0.4,
    },
    {
        "signals": ["rapide", "vite", "quick", "fast", "just", "juste"],
        "apparent": "demande de réponse concise",
        "real": "signal d'IMPATIENCE — l'utilisateur a déjà cherché et n'a pas trouvé",
        "adjustment": (
            "L'utilisateur signale de l'impatience. Ne PAS faire "
            "de préambule. Réponse directe, code first, explication après."
        ),
        "divergence": 0.3,
    },
]


def marble_test(
    prompt: str,
    nature: str = "execution",
    kavvanah: dict | None = None,
) -> MarbleTestResult | None:
    """Le test des pierres de marbre — distinguer apparence et réalité.

    Retourne None si aucune divergence détectée (le prompt est
    transparent — l'albâtre est bien de l'albâtre, pas des vagues).

    Retourne un MarbleTestResult si une divergence est détectée
    entre ce que le prompt SEMBLE demander et ce que l'utilisateur
    VEUT probablement.
    """
    prompt_lower = prompt.lower()

    # Intention explicite dans kavvanah → l'utilisateur a déjà clarifié
    if kavvanah and kavvanah.get("intention"):
        return None

    best_match: dict | None = None
    best_signal: str = ""

    for pattern in _DIVERGENCE_PATTERNS:
        for signal in pattern["signals"]:
            if signal in prompt_lower:
                if best_match is None or pattern["divergence"] > best_match["divergence"]:
                    best_match = pattern
                    best_signal = signal
                break

    if best_match is None:
        return None

    return MarbleTestResult(
        apparent_intent=best_match["apparent"],
        probable_real_intent=best_match["real"],
        divergence=best_match["divergence"],
        adjustment=best_match["adjustment"],
        signal=best_signal,
    )
