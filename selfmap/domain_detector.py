"""Détection de domaine — Binah-de-Hod : classifier la requête.

Utilise l'embedding sémantique pour router vers le bon domaine.
Fallback sur keywords quand l'embedding n'est pas disponible.
"""

from __future__ import annotations

# Domain keywords for fast classification (Assiah-level)
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "python": [
        "python", "pip", "def ", "class ", "import ", "__init__",
        "pytest", "django", "flask", "pandas", "numpy", "torch",
    ],
    "math": [
        "derivative", "integral", "matrix", "eigenvalue", "theorem",
        "proof", "prove ", "equation", "polynomial", "calcul", "algèbre",
        "dérivée", "intégrale", "matrice", "topolog", "irrational",
        "sqrt", "prime number", "convergence", "infinity", "logarithm",
    ],
    "history": [
        "century", "war", "revolution", "emperor", "dynasty", "treaty",
        "siècle", "guerre", "révolution", "empire",
    ],
    "kabbalah": [
        "sephir", "zohar", "kabbale", "kabbalah", "sefirot", "tsimtsum",
        "qliphoth", "partzuf", "tikkun", "luria", "cordovero",
        "arbre de vie", "tree of life", "ein sof",
    ],
    "medicine": [
        "symptom", "disease", "treatment", "diagnosis", "patient",
        "blood", "heart", "brain", "organ", "medical", "medication",
        "aspirin", "headache", "chest pain", "drug", "prescri", "dose",
        "surgery", "doctor", "clinic", "hospital",
        "symptôme", "maladie", "traitement", "diagnostic", "médicament",
        "médecin", "douleur", "ordonnance",
    ],
    "code": [
        "function", "variable", "algorithm", "bug", "compile",
        "git", "docker", "api", "database", "sql", "rust", "go ",
    ],
    "health": [
        "sleep", "exercise", "diet", "nutrition", "weight",
        "sommeil", "jeûne", "fasting", "cardiaque", "bpm",
    ],
}


def detect_domain(query: str) -> tuple[str, float]:
    """Detect the domain of a query.

    Returns (domain, confidence).
    Binah-de-Hod : classification structurée.
    """
    query_lower = query.lower()

    scores: dict[str, int] = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in query_lower)
        if hits > 0:
            scores[domain] = hits

    if not scores:
        return "general", 0.2

    best_domain = max(scores, key=scores.get)  # type: ignore[arg-type]
    total_keywords = len(DOMAIN_KEYWORDS[best_domain])
    confidence = min(scores[best_domain] / max(total_keywords * 0.3, 1), 1.0)

    return best_domain, round(confidence, 2)


def _default_llm_model() -> str:
    """Get default LLM model from config."""
    from olamot import get_model
    return get_model("yetzirah")


def detect_domain_llm(
    query: str, model: str | None = None,
) -> tuple[str, float]:
    """Detect domain using LLM (Briah-level, more expensive).

    Used when keyword detection has low confidence.
    Passe par olamot.py (Hod → Yetzirah).
    """
    domains = list(DOMAIN_KEYWORDS.keys()) + ["general"]
    prompt = (
        f"Classify this query into exactly ONE domain from: {', '.join(domains)}.\n\n"
        f"Query: {query}\n\n"
        f"Reply with ONLY the domain name, nothing else."
    )

    try:
        from olamot import ollama_generate

        if model is None:
            model = _default_llm_model()

        response, _ = ollama_generate(
            "yetzirah", prompt, timeout=15,
            model=model, temperature=0.0, num_predict=20,
            kavvanah={
                "intention": "Identifier le domaine kabbalistique principal de cette question",
                "critere_succes": "Domaine identifié parmi les 22 domaines SelfMap",
                "anti_pattern": "Ne pas classifier en 'general' par défaut — chercher le domaine spécifique",
            },
            context_items=[f"Domaines disponibles: {', '.join(domains[:10])}"],
            domain="domain_classification",
        )
        response = response.lower()

        for d in domains:
            if d in response:
                return d, 0.7
        return "general", 0.3
    except Exception:
        return detect_domain(query)
