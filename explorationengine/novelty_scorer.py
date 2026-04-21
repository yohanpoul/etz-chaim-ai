"""NoveltyScorer — Anti-Gamchicoth.

Mesure la nouveauté de chaque découverte par rapport aux connexions existantes.
Si les N dernières découvertes sont trop similaires → signal d'arrêt.

Gamchicoth (les Dévoreurs) : Chesed sans Gevurah = exploration infinie.
Le NoveltyScorer est le Gevurah-dans-Chesed : il sait quand s'arrêter.

4 niveaux de Gamchicoth :
- Nogah : exploration dépasse le budget de 20%
- Ruach : connexions redondantes (>50% similaires)
- Anan : score de nouveauté en déclin continu
- Mamash : exploration infinie (hard limits dépassés)
"""

from __future__ import annotations

import re

from explorationengine.models import Connection


def _word_set(text: str) -> set[str]:
    """Extract significant words as a set."""
    return {w for w in re.findall(r'\b[a-zA-ZÀ-ÿ]{3,}\b', text.lower())}


def _jaccard(a: set, b: set) -> float:
    """Jaccard similarity between two sets."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class NoveltyScorer:
    """Anti-Gamchicoth : mesure la nouveauté de chaque découverte.

    Score de nouveauté : 0 = déjà vu, 1 = totalement nouveau.
    Basé sur la similarité Jaccard entre la description de la nouvelle
    connexion et celles des connexions existantes.
    """

    def __init__(self, decay_window: int = 10):
        """
        decay_window: nombre de connexions récentes à examiner
                      pour détecter le déclin de nouveauté.
        """
        self.decay_window = decay_window

    def score(
        self,
        new_connection: Connection,
        existing_connections: list[Connection],
    ) -> float:
        """Score de nouveauté d'une connexion.

        0 = identique à une connexion existante
        1 = aucune similarité avec aucune connexion existante
        """
        if not existing_connections:
            return 1.0

        new_words = _word_set(new_connection.description)
        new_domains = {new_connection.domain_a, new_connection.domain_b}

        if not new_words:
            return 0.5

        max_similarity = 0.0

        for existing in existing_connections:
            # Similarité textuelle (description)
            existing_words = _word_set(existing.description)
            text_sim = _jaccard(new_words, existing_words)

            # Bonus de similarité si mêmes domaines
            existing_domains = {existing.domain_a, existing.domain_b}
            domain_sim = 1.0 if new_domains == existing_domains else 0.0

            # Bonus si même type de connexion
            type_sim = 1.0 if (
                new_connection.connection_type == existing.connection_type
            ) else 0.0

            # Score combiné de similarité
            similarity = text_sim * 0.6 + domain_sim * 0.25 + type_sim * 0.15

            max_similarity = max(max_similarity, similarity)

        # Novelty = 1 - max_similarity
        return round(max(0.0, min(1.0, 1.0 - max_similarity)), 4)

    def detect_decay(
        self,
        connections: list[Connection],
        threshold: float = 0.3,
    ) -> bool:
        """Détecter si la nouveauté décline (anti-Gamchicoth Anan).

        Retourne True si les `decay_window` dernières connexions
        ont toutes un novelty_score < threshold.
        """
        if len(connections) < self.decay_window:
            return False

        recent = connections[-self.decay_window:]
        return all(c.novelty_score < threshold for c in recent)

    def detect_redundancy(
        self,
        connections: list[Connection],
        redundancy_ceiling: float = 0.5,
    ) -> bool:
        """Détecter les connexions redondantes (anti-Gamchicoth Ruach).

        Retourne True si plus de `redundancy_ceiling` des connexions
        sont similaires entre elles.
        """
        if len(connections) < 2:
            return False

        n = len(connections)
        similar_pairs = 0
        total_pairs = 0

        for i in range(n):
            for j in range(i + 1, n):
                total_pairs += 1
                words_i = _word_set(connections[i].description)
                words_j = _word_set(connections[j].description)
                sim = _jaccard(words_i, words_j)
                if sim > 0.6:
                    similar_pairs += 1

        if total_pairs == 0:
            return False

        return (similar_pairs / total_pairs) > redundancy_ceiling

    def diagnose(
        self,
        connections: list[Connection],
        elapsed_seconds: float = 0.0,
        budget_seconds: float = 600.0,
        max_connections: int = 50,
        novelty_threshold: float = 0.3,
    ) -> dict:
        """Diagnostic anti-Gamchicoth — 4 niveaux.

        Returns:
            dict with 'level' (healthy/nogah/ruach/anan/mamash) and 'issues'.
        """
        diagnostics = {"level": "healthy", "issues": []}

        if not connections:
            return diagnostics

        # Mamash : hard limits dépassés
        if len(connections) > max_connections:
            diagnostics["level"] = "mamash"
            diagnostics["issues"].append(
                f"Mamash: {len(connections)} connections exceeds hard limit "
                f"of {max_connections}"
            )
            return diagnostics

        # Anan : score de nouveauté en déclin continu
        if self.detect_decay(connections, novelty_threshold):
            diagnostics["level"] = "anan"
            diagnostics["issues"].append(
                f"Anan: novelty score declining — last {self.decay_window} "
                f"connections all below {novelty_threshold}"
            )

        # Ruach : connexions redondantes
        if self.detect_redundancy(connections):
            if diagnostics["level"] == "healthy":
                diagnostics["level"] = "ruach"
            diagnostics["issues"].append(
                "Ruach: >50% of connections are redundant"
            )

        # Nogah : budget temps dépassé de 20%
        if elapsed_seconds > budget_seconds * 1.2:
            if diagnostics["level"] == "healthy":
                diagnostics["level"] = "nogah"
            diagnostics["issues"].append(
                f"Nogah: exploration exceeded time budget by "
                f"{((elapsed_seconds / budget_seconds) - 1) * 100:.0f}%"
            )

        return diagnostics
