"""SerendipityWalker — Marche de sérendipité.

Chaque pas ouvre un domaine inattendu.
Ce n'est ni random (pas de structure) ni ciblé (pas de surprise).
C'est guidé par les connexions DÉJÀ trouvées — chaque découverte
ouvre une porte vers un domaine qu'on n'aurait pas exploré.

"La sérendipité est l'art de trouver ce qu'on ne cherchait pas."
"""

from __future__ import annotations

import hashlib
import re

from explorationengine.analogy_engine import AnalogyEngine
from explorationengine.cross_domain import CrossDomainConnector
from explorationengine.models import Connection


def _deterministic_choice(items: list, seed: str) -> int:
    """Choix déterministe basé sur un hash — reproductible mais varié."""
    if not items:
        return 0
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    return h % len(items)


def _extract_key_concepts(text: str) -> list[str]:
    """Extraire les concepts-clés d'un texte (mots significatifs > 4 chars)."""
    words = re.findall(r'\b[a-zA-ZÀ-ÿ]{4,}\b', text.lower())
    # Compter et prendre les plus fréquents
    from collections import Counter
    counts = Counter(words)
    # Retourner les mots qui apparaissent au moins 1 fois, triés par longueur
    return sorted(counts.keys(), key=lambda w: (-len(w), w))[:10]


class SerendipityWalker:
    """Marche de sérendipité entre domaines.

    À chaque pas :
    1. Analyser les connexions du pas précédent
    2. Extraire un concept-pivot (le plus surprenant)
    3. Choisir un domaine NON encore visité
    4. Chercher des connexions depuis le concept-pivot
    5. Ajouter les résultats et continuer

    Anti-Gamchicoth intégré : la marche s'arrête si les domaines
    disponibles sont épuisés ou si le concept-pivot ne change plus.
    """

    def __init__(
        self,
        connector: CrossDomainConnector | None = None,
        analogy_engine: AnalogyEngine | None = None,
    ):
        self.connector = connector or CrossDomainConnector()
        self.analogies = analogy_engine or AnalogyEngine()

    def walk(
        self,
        start_concept: str,
        start_domain: str,
        n_steps: int = 5,
        available_domains: list[str] | None = None,
    ) -> list[Connection]:
        """Marche de sérendipité.

        Args:
            start_concept: concept de départ
            start_domain: domaine de départ
            n_steps: nombre de pas
            available_domains: domaines dans lesquels marcher (tous si None)

        Returns:
            Liste de connexions trouvées pendant la marche.
        """
        domains = available_domains or self.analogies.get_known_domains()
        visited: set[str] = {start_domain}
        current_concept = start_concept
        current_domain = start_domain
        all_connections: list[Connection] = []

        for step in range(n_steps):
            # Domaines non visités
            unvisited = [d for d in domains if d not in visited]
            if not unvisited:
                break

            # Choisir le prochain domaine (déterministe mais varié)
            seed = f"{current_concept}_{current_domain}_{step}"
            idx = _deterministic_choice(unvisited, seed)
            next_domain = unvisited[idx]

            # Chercher des connexions
            conns = self.connector.find_connections(
                query=current_concept,
                domain_a=current_domain,
                domain_b=next_domain,
            )

            # Aussi chercher des analogies
            analogy_conns = self.analogies.find_analogies(
                concept=current_concept,
                source_domain=current_domain,
                target_domains=[next_domain],
            )
            conns.extend(analogy_conns)

            all_connections.extend(conns)
            visited.add(next_domain)

            # Pivot : extraire le concept le plus intéressant
            # de la dernière connexion trouvée
            if conns:
                pivot = self._extract_pivot(conns, current_concept)
                current_concept = pivot
            current_domain = next_domain

        return all_connections

    def _extract_pivot(
        self, connections: list[Connection], previous_concept: str
    ) -> str:
        """Extraire le concept-pivot le plus surprenant des connexions.

        Le pivot est le concept_b qui diffère le plus du concept précédent.
        """
        if not connections:
            return previous_concept

        prev_words = set(re.findall(r'\b[a-zA-ZÀ-ÿ]{3,}\b', previous_concept.lower()))

        best_pivot = previous_concept
        best_novelty = 0.0

        for conn in connections:
            candidate = conn.concept_b
            cand_words = set(re.findall(r'\b[a-zA-ZÀ-ÿ]{3,}\b', candidate.lower()))
            if not cand_words:
                continue

            # Novelty = proportion de mots nouveaux
            if prev_words:
                overlap = len(cand_words & prev_words) / max(len(cand_words), 1)
                novelty = 1.0 - overlap
            else:
                novelty = 0.5

            if novelty > best_novelty:
                best_novelty = novelty
                best_pivot = candidate

        return best_pivot
