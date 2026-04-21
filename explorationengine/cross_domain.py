"""CrossDomainConnector — Le cœur de Chesed.

Trouver des ponts entre domaines par analyse heuristique.
Pas de LLM — détection de patterns partagés par analyse textuelle :
- Vocabulaire commun entre domaines
- Structures parallèles (listes, hiérarchies, cycles)
- Relations causales implicites (mots-clés d'influence)
- Contradictions (négations, oppositions)

"Abraham ne pré-juge pas. Il ouvre la porte à TOUT."
"""

from __future__ import annotations

import re
from collections import Counter

from explorationengine.models import Connection


# Marqueurs de type de connexion
CAUSAL_MARKERS = {
    "causes", "leads", "produces", "results", "triggers", "enables",
    "prevents", "blocks", "inhibits", "drives", "influences",
    "cause", "produit", "entraîne", "déclenche", "permet",
    "empêche", "bloque", "inhibe", "influence",
}

CONTRADICTION_MARKERS = {
    "but", "however", "contrary", "opposite", "unlike", "versus",
    "conflicts", "contradicts", "opposes", "refutes", "denies",
    "mais", "cependant", "contraire", "opposé", "contrairement",
    "contredit", "réfute", "nie", "inverse",
}

COMPLEMENT_MARKERS = {
    "also", "additionally", "extends", "complements", "supports",
    "enhances", "reinforces", "builds", "augments", "supplements",
    "aussi", "complète", "renforce", "étend", "soutient",
    "enrichit", "augmente", "ajoute",
}

# Patterns structurels détectables
HIERARCHY_MARKERS = {"levels", "layers", "stages", "phases", "tiers", "hierarchy",
                     "niveaux", "couches", "étapes", "phases", "hiérarchie"}
CYCLE_MARKERS = {"cycle", "loop", "feedback", "iteration", "recursive", "oscillation",
                 "boucle", "itération", "récursif", "oscillation"}
FLOW_MARKERS = {"flow", "pipeline", "sequence", "chain", "stream", "cascade",
                "flux", "séquence", "chaîne", "cascade"}


def _extract_words(text: str) -> list[str]:
    """Extract significant words (3+ chars)."""
    return [w for w in re.findall(r'\b[a-zA-ZÀ-ÿ]{3,}\b', text.lower())]


def _word_set(text: str) -> set[str]:
    return set(_extract_words(text))


def _detect_structural_pattern(words: set[str]) -> str | None:
    """Detect if text describes a hierarchy, cycle, or flow."""
    if words & HIERARCHY_MARKERS:
        return "hierarchy"
    if words & CYCLE_MARKERS:
        return "cycle"
    if words & FLOW_MARKERS:
        return "flow"
    return None


class CrossDomainConnector:
    """Le cœur de Chesed : trouver des ponts entre domaines.

    Analyse heuristique de connexions inter-domaines :
    1. Vocabulaire partagé → pattern_shared
    2. Patterns structurels communs → analogy
    3. Marqueurs causaux → causal
    4. Marqueurs de contradiction → contradicts
    5. Marqueurs de complémentarité → complements
    """

    def __init__(self, domain_knowledge: dict[str, str] | None = None):
        """
        domain_knowledge : dict mapping domain_id → description textuelle du domaine.
        Si fourni, enrichit la détection de connexions.
        """
        self.domain_knowledge = domain_knowledge or {}

    def find_connections(
        self,
        query: str,
        domain_a: str,
        domain_b: str,
        context_a: str = "",
        context_b: str = "",
    ) -> list[Connection]:
        """Trouver des connexions entre deux domaines pour une query.

        Args:
            query: la question de départ
            domain_a: domaine source
            domain_b: domaine cible
            context_a: texte de contexte du domaine A (optionnel)
            context_b: texte de contexte du domaine B (optionnel)

        Returns:
            Liste de connexions trouvées (peut être vide).
        """
        connections: list[Connection] = []

        # Enrichir le contexte avec domain_knowledge
        text_a = f"{query} {context_a} {self.domain_knowledge.get(domain_a, '')}".strip()
        text_b = f"{context_b} {self.domain_knowledge.get(domain_b, '')}".strip()

        words_a = _word_set(text_a)
        words_b = _word_set(text_b)

        if not words_a or not words_b:
            return connections

        # 1. Vocabulaire partagé → pattern_shared
        shared = words_a & words_b
        # Exclure les stop words trop communs
        stopwords = {"the", "and", "for", "that", "this", "with", "from", "are",
                      "les", "des", "une", "par", "pour", "dans", "qui", "que"}
        shared -= stopwords

        if len(shared) >= 2:
            shared_significant = sorted(shared, key=lambda w: len(w), reverse=True)[:5]
            connections.append(Connection(
                concept_a=query,
                domain_a=domain_a,
                concept_b=", ".join(shared_significant),
                domain_b=domain_b,
                connection_type="pattern_shared",
                description=(
                    f"Shared vocabulary between {domain_a} and {domain_b}: "
                    f"{', '.join(shared_significant)}. "
                    f"These concepts bridge both domains."
                ),
                confidence=min(len(shared) / 10, 0.9),
            ))

        # 2. Patterns structurels communs → analogy
        pattern_a = _detect_structural_pattern(words_a)
        pattern_b = _detect_structural_pattern(words_b)
        if pattern_a and pattern_b and pattern_a == pattern_b:
            connections.append(Connection(
                concept_a=f"{pattern_a} in {domain_a}",
                domain_a=domain_a,
                concept_b=f"{pattern_b} in {domain_b}",
                domain_b=domain_b,
                connection_type="analogy",
                description=(
                    f"Both {domain_a} and {domain_b} exhibit a {pattern_a} structure. "
                    f"This structural analogy suggests deeper parallels."
                ),
                confidence=0.6,
            ))
        elif pattern_a and not pattern_b:
            # A has a structure that B might also have
            connections.append(Connection(
                concept_a=f"{pattern_a} in {domain_a}",
                domain_a=domain_a,
                concept_b=f"potential {pattern_a} in {domain_b}",
                domain_b=domain_b,
                connection_type="analogy",
                description=(
                    f"{domain_a} has a {pattern_a} structure. "
                    f"Does {domain_b} have an analogous structure?"
                ),
                confidence=0.3,
            ))

        # 3. Marqueurs causaux
        all_words = words_a | words_b
        causal_found = all_words & CAUSAL_MARKERS
        if causal_found:
            connections.append(Connection(
                concept_a=query,
                domain_a=domain_a,
                concept_b=f"influence on {domain_b}",
                domain_b=domain_b,
                connection_type="causal",
                description=(
                    f"Causal relationship detected between {domain_a} and {domain_b} "
                    f"(markers: {', '.join(sorted(causal_found)[:3])}). "
                    f"Changes in {domain_a} may influence {domain_b}."
                ),
                confidence=0.4,
            ))

        # 4. Contradiction
        contradiction_found = all_words & CONTRADICTION_MARKERS
        if contradiction_found:
            connections.append(Connection(
                concept_a=query,
                domain_a=domain_a,
                concept_b=f"tension with {domain_b}",
                domain_b=domain_b,
                connection_type="contradicts",
                description=(
                    f"Potential tension between {domain_a} and {domain_b} "
                    f"(markers: {', '.join(sorted(contradiction_found)[:3])}). "
                    f"This contradiction may be productive."
                ),
                confidence=0.35,
            ))

        # 5. Complémentarité
        complement_found = all_words & COMPLEMENT_MARKERS
        if complement_found and not contradiction_found:
            connections.append(Connection(
                concept_a=query,
                domain_a=domain_a,
                concept_b=f"extension in {domain_b}",
                domain_b=domain_b,
                connection_type="complements",
                description=(
                    f"{domain_a} and {domain_b} appear complementary "
                    f"(markers: {', '.join(sorted(complement_found)[:3])}). "
                    f"Combining insights from both domains may yield synthesis."
                ),
                confidence=0.45,
            ))

        return connections

    def find_connections_multi(
        self,
        query: str,
        seed_domain: str,
        target_domains: list[str],
        context: dict[str, str] | None = None,
    ) -> list[Connection]:
        """Trouver des connexions entre un domaine et plusieurs cibles."""
        ctx = context or {}
        all_connections: list[Connection] = []
        for target in target_domains:
            if target == seed_domain:
                continue
            conns = self.find_connections(
                query=query,
                domain_a=seed_domain,
                domain_b=target,
                context_a=ctx.get(seed_domain, ""),
                context_b=ctx.get(target, ""),
            )
            all_connections.extend(conns)
        return all_connections
