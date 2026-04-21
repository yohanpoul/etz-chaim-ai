"""Classificateur Qliphoth — Gevurah du sentier Lamed.

Chaque Qliphah est le mode de défaillance SPÉCIFIQUE d'une Sephirah.
Le classificateur identifie QUEL type d'échec s'est produit.
"""

from __future__ import annotations

# Mots-clés par Qliphah — le vocabulaire de chaque mode de défaillance
QLIPHAH_KEYWORDS: dict[str, list[str]] = {
    "gamaliel": [
        "memory", "mémoire", "storage", "stockage", "data loss", "perte de données",
        "corruption", "corrompu", "persist", "recall", "rappel", "embedding",
        "expir", "ttl", "cache", "stale data", "donnée périmée",
    ],
    "samael": [
        "confidence", "confiance", "routing", "routage", "wrong model", "mauvais modèle",
        "overconfident", "surconfian", "calibration", "incompétent", "domaine inconnu",
        "self-knowledge", "hod", "misroute",
    ],
    "aarab_zaraq": [
        "retry", "timeout", "zombie", "infinite loop", "boucle infinie", "stuck",
        "bloqué", "hang", "suspend", "freeze", "gelé", "resource leak",
        "fuite de ressource", "circuit breaker", "dead letter",
    ],
    "thagirion": [
        "contradiction", "conflict", "conflit", "inconsistent", "incohérent",
        "synthesis fail", "synthèse échouée", "merge", "fusion",
        "false harmony", "fausse harmonie", "forced consensus",
    ],
    "golachab": [
        "reject", "rejet", "filter", "filtr", "too strict", "trop strict",
        "empty result", "résultat vide", "nothing found", "rien trouvé",
        "false negative", "faux négatif", "over-filter", "sur-filtr",
    ],
    "gamchicoth": [
        "scope creep", "scope", "resource exhaust", "épuisement",
        "too many", "trop de", "overflow", "débordement", "bloat",
        "memory limit", "limite mémoire", "accumulation", "infini",
    ],
    "hatehom": [
        "self-model", "disconnect", "déconnexion", "misalign", "désaligné",
        "wrong capability", "mauvaise capacité", "intent vs execution",
        "intention vs exécution", "daat", "abyss", "abîme",
    ],
    "satariel": [
        "false pattern", "faux pattern", "correlation", "corrélation",
        "causation", "causalité", "spurious", "fallacieux", "noise", "bruit",
        "apopheni", "false positive", "faux positif",
    ],
    "ghagiel": [
        "hypothesis", "hypothèse", "diverge", "no convergence",
        "blocked", "bloqué créatif", "no ideas", "pas d'idée",
        "loop", "reformulat", "novelty", "nouveauté",
    ],
    "thaumiel": [
        "contradictory goal", "but contradictoire", "dual intent",
        "double intention", "fork", "split", "conflit d'intention",
        "two plans", "deux plans", "incompatible",
    ],
}

# Mots-clés de sévérité
SEVERITY_KEYWORDS: dict[str, list[str]] = {
    "mamash": [
        "crash", "fatal", "total failure", "échec total", "data loss",
        "perte de données", "unrecoverable", "irrécupérable", "destroyed",
        "détruit", "corrupt", "irréparable", "no output", "aucun résultat",
    ],
    "anan": [
        "silent", "silencieux", "seems ok", "semble correct", "false positive",
        "faux positif", "wrong but confident", "faux mais confiant",
        "undetected", "non détecté", "hidden", "caché", "masqué",
    ],
    "ruach": [
        "propagat", "spread", "cascade", "neighbor", "voisin", "leak",
        "fuite", "resource", "affect", "downstream", "en aval",
        "side effect", "effet de bord",
    ],
    "nogah": [
        "minor", "mineur", "warning", "recoverable", "récupérable",
        "slow", "lent", "degraded", "dégradé", "partial", "partiel",
    ],
}


def classify_qliphah(description: str, context: dict | None = None) -> str:
    """Classifier un échec par sa Qliphah.

    Retourne la Qliphah avec le meilleur score de correspondance.
    """
    desc_lower = description.lower()
    ctx_text = ""
    if context:
        ctx_text = " ".join(str(v) for v in context.values()).lower()
    combined = desc_lower + " " + ctx_text

    scores: dict[str, int] = {}
    for qliphah, keywords in QLIPHAH_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score > 0:
            scores[qliphah] = score

    if not scores:
        return "unknown"

    return max(scores, key=scores.get)


def classify_severity(description: str, context: dict | None = None) -> str:
    """Déterminer la sévérité d'un échec.

    Vérifie du plus grave (mamash) au moins grave (nogah).
    """
    desc_lower = description.lower()
    ctx_text = ""
    if context:
        ctx_text = " ".join(str(v) for v in context.values()).lower()
    combined = desc_lower + " " + ctx_text

    # Check from most severe to least
    for severity in ["mamash", "anan", "ruach", "nogah"]:
        keywords = SEVERITY_KEYWORDS[severity]
        if any(kw in combined for kw in keywords):
            return severity

    return "nogah"  # default = le moins grave
