"""Tzelem — Le moule archetypal qui pre-forme la reponse.

צֶלֶם — Le Tzelem est le "moule" ou "image" (cf. Genese 1:27
"betselem Elohim") qui pre-structure la forme de la reponse
AVANT que le contenu ne la remplisse.

EC-SHK-079, PG-SHK-024 — Dimension 21 du Kli.

Comme le Tzelem pre-forme le corps de l'ame avant la naissance,
le template cognitif pre-forme la reponse avant la generation.
L'ame (contenu) remplit le Tzelem (forme), mais le Tzelem
contraint aussi ce que l'ame peut exprimer.

v1 : detection par templates (heuristique, pas LLM).
Les 5 templates correspondent a 5 modalites cognitives fondamentales.

Usage:
    from masakh.tzelem import Tzelem

    tz = Tzelem()
    name = tz.detect({"intention": "analyser le code"}, "yetzirah")
    instruction = tz.apply(name)
    # → "Structure ta reponse comme : Instructions sequentielles..."
"""

from __future__ import annotations


# Les 5 templates cognitifs
TEMPLATES: dict[str, str] = {
    "analyse_technique": (
        "Analyse structuree avec diagnostic, causes, "
        "recommandations, et risques"
    ),
    "dialogue_erudit": (
        "Echange entre pairs avec sources, "
        "nuances, et questions ouvertes"
    ),
    "implementation": (
        "Instructions sequentielles avec code, "
        "tests, et validation"
    ),
    "exploration": (
        "Brainstorming ouvert avec hypotheses, "
        "analogies, et directions"
    ),
    "audit": (
        "Verification systematique avec metriques, gaps, "
        "et plan d'action"
    ),
}

# Mots-cles pour la detection par intention
_INTENTION_KEYWORDS: dict[str, list[str]] = {
    "exploration": ["explorer", "brainstorm", "imaginer", "hypothese", "possibilite"],
    "audit": ["audit", "verifier", "valider", "checker", "conformite"],
    "analyse_technique": ["analyser", "comprendre", "diagnostiquer", "expliquer", "cause"],
    "implementation": ["implementer", "coder", "ecrire", "creer", "construire", "deployer"],
    "dialogue_erudit": ["discuter", "comparer", "debattre", "nuancer", "architectur"],
}

# Mapping Olam → template par defaut (si l'intention ne matche pas)
_OLAM_DEFAULT: dict[str, str] = {
    "atziluth": "analyse_technique",
    "atzilut": "analyse_technique",
    "briah": "dialogue_erudit",
    "yetzirah": "implementation",
    "assiah": "implementation",
}


class Tzelem:
    """צֶלֶם — Detecteur et applicateur du moule archetypal."""

    def detect(self, kavvanah: dict | None, olam: str) -> str:
        """Determiner le Tzelem approprie.

        Detection en deux passes :
          1. Par mots-cles dans l'intention de la Kavvanah
          2. Par defaut selon l'Olam

        Args:
            kavvanah: Intention dirigee (dict avec 'intention').
            olam: L'Olam de la tache.

        Returns:
            Nom du template : "analyse_technique", "dialogue_erudit",
            "implementation", "exploration", ou "audit".
        """
        # Passe 1 : detection par intention
        if kavvanah and kavvanah.get("intention"):
            intention = kavvanah["intention"].lower()
            for template_name, keywords in _INTENTION_KEYWORDS.items():
                for kw in keywords:
                    if kw in intention:
                        return template_name

        # Passe 2 : defaut par Olam
        return _OLAM_DEFAULT.get(olam, "implementation")

    def apply(self, tzelem_name: str) -> str:
        """Retourner l'instruction de Tzelem a injecter dans le prompt.

        Args:
            tzelem_name: Nom du template.

        Returns:
            Instruction formatee.

        Raises:
            ValueError: Si le template n'existe pas.
        """
        template = TEMPLATES.get(tzelem_name)
        if template is None:
            raise ValueError(
                f"Tzelem inconnu : {tzelem_name!r}. "
                f"Attendu : {', '.join(TEMPLATES)}"
            )
        return f"[TZELEM] Structure ta reponse comme : {template} [/TZELEM]"
