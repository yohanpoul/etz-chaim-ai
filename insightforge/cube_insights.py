"""insightforge/cube_insights.py — Insights générés par le Cube de l'Espace.

גִּלּוּי — Révélation

Les connexions cachées (gap > seuil entre kab_similarity et ml_similarity)
sont des candidats d'insights automatiques. Le Cube génère des hypothèses
que la statistique seule ne voit pas.

Usage:
    gen = CubeInsightGenerator()
    hidden = gen.discover_hidden_connections(min_gap=0.2, top_k=20)
    candidates = gen.format_as_insight_candidates(hidden)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HiddenConnection:
    """Une connexion cachée entre deux concepts."""
    concept_a: str
    concept_b: str
    hebrew_a: str | None
    hebrew_b: str | None
    kab_similarity: float
    ml_similarity: float
    gap: float  # kab_sim - ml_sim


class CubeInsightGenerator:
    """Génère des insights à partir des connexions cachées du Cube.

    Scanne les hybrid_embeddings pour trouver des paires de concepts
    qui sont proches dans le Cube (tradition) mais éloignés en ML
    (statistique). Chaque telle paire est un candidat d'insight :
    la tradition perçoit un lien que les données ne montrent pas.
    """

    def __init__(
        self,
        db_url: str | None = None,
        default_min_gap: float = 0.2,
    ) -> None:
        self.db_url = db_url or os.environ.get(
            "ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim",
        )
        self.default_min_gap = default_min_gap

    def _get_conn(self):
        """Emprunte une conn au pool (context manager) avec pgvector."""
        from contextlib import contextmanager

        from pool import get_conn as _pool_get, init_pool

        @contextmanager
        def _borrow():
            init_pool(self.db_url)  # idempotent
            with _pool_get() as conn:
                try:
                    from pgvector.psycopg2 import register_vector
                    register_vector(conn)
                except ImportError as _exc:

                    import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
                yield conn

        return _borrow()

    def discover_hidden_connections(
        self,
        min_gap: float | None = None,
        top_k: int = 20,
    ) -> list[HiddenConnection]:
        """Scan all pairs to find hidden connections.

        For efficiency, we compare each concept's kab and ML neighbors
        rather than doing an O(n²) full scan. Strategy:
        - For each concept, find its top kab neighbors
        - For those neighbors, compute ml_similarity
        - If kab_sim - ml_sim > min_gap → hidden connection

        Args:
            min_gap: minimum gap threshold (default: self.default_min_gap)
            top_k: number of hidden connections to return

        Returns:
            List of HiddenConnection sorted by gap descending.
        """
        min_gap = min_gap if min_gap is not None else self.default_min_gap

        with self._get_conn() as conn:
            # Load all concept vectors
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT concept, hebrew_word,
                           kabbalistic_signature, ml_embedding
                    FROM hybrid_embeddings
                    WHERE kabbalistic_signature IS NOT NULL
                      AND ml_embedding IS NOT NULL
                """)
                rows = cur.fetchall()

        if len(rows) < 2:
            return []

        import numpy as np

        # Build numpy arrays for vectorized comparison
        concepts = []
        hebrews = []
        kab_vecs = []
        ml_vecs = []

        for r in rows:
            concepts.append(r[0])
            hebrews.append(r[1])
            kab_vecs.append(np.asarray(r[2], dtype=np.float32))
            ml_vecs.append(np.asarray(r[3], dtype=np.float32))

        kab_mat = np.stack(kab_vecs)
        ml_mat = np.stack(ml_vecs)

        # Normalize for cosine similarity
        kab_norms = np.linalg.norm(kab_mat, axis=1, keepdims=True)
        kab_norms = np.where(kab_norms < 1e-10, 1.0, kab_norms)
        kab_normed = kab_mat / kab_norms

        ml_norms = np.linalg.norm(ml_mat, axis=1, keepdims=True)
        ml_norms = np.where(ml_norms < 1e-10, 1.0, ml_norms)
        ml_normed = ml_mat / ml_norms

        # Compute full similarity matrices
        n = len(concepts)
        # For large n, process in batches to avoid memory issues
        batch_size = min(n, 200)
        all_hidden: list[HiddenConnection] = []
        seen_pairs: set[tuple[str, str]] = set()

        for i in range(0, n, batch_size):
            end = min(i + batch_size, n)
            kab_sims = kab_normed[i:end] @ kab_normed.T  # (batch, n)
            ml_sims = ml_normed[i:end] @ ml_normed.T      # (batch, n)
            gaps = kab_sims - ml_sims

            # Find pairs with gap > min_gap
            for bi, gi in enumerate(range(i, end)):
                for j in range(n):
                    if gi == j:
                        continue
                    g = gaps[bi, j]
                    if g >= min_gap:
                        pair_key = tuple(sorted([concepts[gi], concepts[j]]))
                        if pair_key not in seen_pairs:
                            seen_pairs.add(pair_key)
                            all_hidden.append(HiddenConnection(
                                concept_a=concepts[gi],
                                concept_b=concepts[j],
                                hebrew_a=hebrews[gi],
                                hebrew_b=hebrews[j],
                                kab_similarity=round(float(kab_sims[bi, j]), 4),
                                ml_similarity=round(float(ml_sims[bi, j]), 4),
                                gap=round(float(g), 4),
                            ))

        all_hidden.sort(key=lambda h: h.gap, reverse=True)
        logger.info(
            "Discovered %d hidden connections (min_gap=%.2f), returning top %d",
            len(all_hidden), min_gap, top_k,
        )
        return all_hidden[:top_k]

    def format_as_insight_candidates(
        self,
        connections: list[HiddenConnection],
    ) -> list[dict]:
        """Format hidden connections as InsightForge candidate dicts.

        Each candidate has the shape expected by InsightForge's pipeline:
        domain_a, domain_b, hypothesis, source.
        """
        candidates = []
        for conn in connections:
            # Determine domains from concept names
            domain_a = self._infer_domain(conn.concept_a)
            domain_b = self._infer_domain(conn.concept_b)

            hebrew_a = f" ({conn.hebrew_a})" if conn.hebrew_a else ""
            hebrew_b = f" ({conn.hebrew_b})" if conn.hebrew_b else ""

            hypothesis = (
                f"Le Cube de l'Espace révèle que {conn.concept_a}{hebrew_a} "
                f"et {conn.concept_b}{hebrew_b} sont structurellement liés "
                f"(kab={conn.kab_similarity:.3f}) bien que sémantiquement "
                f"distants (ml={conn.ml_similarity:.3f}). "
                f"Gap={conn.gap:.3f}. "
                f"La tradition perçoit une connexion que la statistique ne voit pas."
            )

            candidates.append({
                "description": hypothesis,
                "source_module": "cube_insights",
                "domain": f"{domain_a}+{domain_b}",
                "confidence": min(conn.kab_similarity, 0.9),
                "connects_domains": [domain_a, domain_b],
                "source": "cube_hidden",
                "kab_sim": conn.kab_similarity,
                "ml_sim": conn.ml_similarity,
                "gap": conn.gap,
            })

        return candidates

    @staticmethod
    def _infer_domain(concept: str) -> str:
        """Infer domain from concept name."""
        concept_lower = concept.lower()
        if concept_lower.startswith("gate_"):
            return "gates"
        if concept_lower.startswith("letter "):
            return "letters"
        if concept_lower.startswith("sephirah "):
            return "sephiroth"
        if concept_lower.startswith("partzuf "):
            return "partzufim"
        if concept_lower.startswith("domain "):
            return concept_lower.replace("domain ", "")
        return "kabbale"
