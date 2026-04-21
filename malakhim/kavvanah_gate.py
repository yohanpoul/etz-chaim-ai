"""KavvanahGate — Évaluation de la qualité de l'intention.

כַּוָּנָה — L'intention détermine la qualité de l'entité produite.

Tanya ch. 39-40 (citant Vital, Sha'ar HaNevuah ch. 2) :
  - Torah avec kavvanah intellectuelle → Sephiroth de Briah (connexion directe)
  - Torah avec kavvanah émotionnelle → Sephiroth de Yetzirah (directe)
  - Torah SANS kavvanah → crée des ANGES dans Yetzirah (médiation)
  - Mitzvot SANS kavvanah → crée des ANGES dans Assiah (minimal)

Principe : les anges sont le produit d'une intention INCOMPLÈTE.
Avec kavvanah pleine, l'énergie monte directement dans les Sephiroth —
pas besoin de médiation angélique.

Traduit en architecture :
  HIGH kavvanah  → connexion directe (pas de Malakh) → Atziluth/Briah
  MEDIUM kavvanah → Malakh engendré via Heikhalot    → Yetzirah
  LOW kavvanah   → exécution mécanique (Ishim)       → Assiah
"""

from __future__ import annotations

from malakhim.models import KavvanahGrade

# ── Seuils ────────────────────────────────────────────────────────────────────

TIER_HIGH = 0.7
TIER_LOW = 0.3

# ── Critères de scoring ──────────────────────────────────────────────────────
# Chaque critère reflète un aspect de la complétude intentionnelle.
# Les poids sont calibrables — constantes au module level.

_CRITERIA: list[tuple[str, float]] = [
    ("intention", 0.20),          # L'intention explicite de l'utilisateur
    ("critere_succes", 0.20),     # Comment évaluer la réussite
    ("anti_pattern", 0.15),       # Ce qu'il faut éviter
    ("domain", 0.10),             # Le domaine d'application
    ("required_keywords", 0.10),  # Mots-clés attendus dans la réponse
    ("nature", 0.10),             # Nature ontologique explicite (= choix conscient)
]

# Points pour la spécificité du prompt (pas lié à kavvanah dict)
_PROMPT_SPECIFICITY_WEIGHT = 0.15
_PROMPT_MIN_LENGTH = 100

# Points si le prompt n'est pas juste une question simple
_NOT_QUESTION_ONLY_WEIGHT = 0.10


def kavvanah_score(
    kavvanah: dict | None,
    prompt: str,
) -> KavvanahGrade:
    """Score la kavvanah et détermine le tier de routage.

    Args:
        kavvanah: dict d'intention (peut être None ou vide)
        prompt: le prompt utilisateur

    Returns:
        KavvanahGrade avec score [0.0-1.0], tier, et champs manquants
    """
    kav = kavvanah or {}
    score = 0.0
    missing: list[str] = []

    # 1. Critères du dict kavvanah
    for field_name, weight in _CRITERIA:
        val = kav.get(field_name)
        if val is not None and val != "" and val != [] and val != {}:
            score += weight
        else:
            missing.append(field_name)

    # 2. Spécificité du prompt
    if len(prompt) >= _PROMPT_MIN_LENGTH:
        score += _PROMPT_SPECIFICITY_WEIGHT
    else:
        missing.append("prompt_specificity")

    # 3. Pas juste une question simple
    stripped = prompt.strip()
    is_question_only = (
        stripped.endswith("?")
        and "\n" not in stripped
        and len(stripped) < 150
    )
    if not is_question_only and len(stripped) > 0:
        score += _NOT_QUESTION_ONLY_WEIGHT
    else:
        missing.append("prompt_not_question_only")

    # Clamp
    score = max(0.0, min(1.0, score))

    # Tier
    if score >= TIER_HIGH:
        tier = "high"
    elif score >= TIER_LOW:
        tier = "medium"
    else:
        tier = "low"

    return KavvanahGrade(score=score, tier=tier, missing=missing)
