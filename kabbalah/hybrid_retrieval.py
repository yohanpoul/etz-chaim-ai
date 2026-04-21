"""kabbalah/hybrid_retrieval.py — Retrieval hybride Cube + ML.

שְׁלִיפָה — Extraction

Couche de retrieval qui utilise l'embedding hybride (798 dims)
pour retrouver des concepts par similarité. Quatre modes :

  - hybrid  : vecteur complet 798 dims (structure + sémantique)
  - kabbalistic : signature 30 dims seule (structure pure du Cube)
  - ml      : embedding 768 dims seul (sémantique statistique)
  - hidden  : concepts où kab_similarity > ml_similarity + gap_threshold
              (connexions que la tradition voit mais pas la statistique)

Usage:
    retrieval = HybridRetrieval()
    results = retrieval.query("Tsimtsum", mode="hidden", top_k=10)
    context = retrieval.enrich_context("Kabbale et Arbre de Vie", top_k=5)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Résultat d'une requête de retrieval hybride."""
    concept: str
    hebrew_word: str | None
    similarity: float       # similarité dans le mode demandé
    kab_sim: float          # similarité kabbalistique (30d)
    ml_sim: float           # similarité ML (768d)
    gap: float              # kab_sim - ml_sim


class HybridRetrieval:
    """Retrieval hybride Cube + ML via pgvector.

    Interroge la table hybrid_embeddings pour trouver les concepts
    les plus proches d'un texte de requête, selon quatre modes
    de similarité.
    """

    def __init__(
        self,
        db_url: str | None = None,
        gap_threshold: float = 0.2,
    ) -> None:
        self.db_url = db_url or os.environ.get(
            "ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim",
        )
        self.gap_threshold = gap_threshold
        self._he = None  # lazy init HybridEmbedding

    def _get_he(self):
        if self._he is None:
            from kabbalah.hybrid_embedding import HybridEmbedding
            self._he = HybridEmbedding(db_url=self.db_url)
        return self._he

    def _get_conn(self):
        """Emprunte une conn au pool (context manager) avec pgvector enregistré.

        Usage:
            with self._get_conn() as conn:
                with conn.cursor() as cur: ...
        """
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

    def query(
        self,
        text: str,
        hebrew_word: str | None = None,
        mode: str = "hybrid",
        top_k: int = 10,
    ) -> list[RetrievalResult]:
        """Recherche les concepts les plus proches dans l'embedding hybride.

        Args:
            text: texte de requête (concept, question, description)
            hebrew_word: mot hébreu explicite si connu
            mode: "hybrid" | "kabbalistic" | "ml" | "hidden"
            top_k: nombre de résultats

        Returns:
            Liste de RetrievalResult triée par pertinence.
        """
        he = self._get_he()
        vec = he.embed(text, hebrew_word=hebrew_word)

        if mode == "hidden":
            return self._query_hidden(vec, top_k)

        # Standard mode: hybrid, kabbalistic, or ml
        if mode == "kabbalistic":
            query_vec = vec.kabbalistic.tolist()
            column = "kabbalistic_signature"
        elif mode == "ml":
            query_vec = vec.ml.tolist()
            column = "ml_embedding"
        else:
            query_vec = vec.hybrid.tolist()
            column = "hybrid_vector"

        with self._get_conn() as conn:
            kab_vec = vec.kabbalistic.tolist()
            ml_vec = vec.ml.tolist()
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT concept, hebrew_word,
                           1 - ({column} <=> %s::vector) as similarity,
                           1 - (kabbalistic_signature <=> %s::vector) as kab_sim,
                           1 - (ml_embedding <=> %s::vector) as ml_sim
                    FROM hybrid_embeddings
                    WHERE concept != %s
                    ORDER BY {column} <=> %s::vector
                    LIMIT %s
                """, (query_vec, kab_vec, ml_vec, text, query_vec, top_k))
                rows = cur.fetchall()

        results = []
        for r in rows:
            kab_s = r[3] if r[3] else 0.0
            ml_s = r[4] if r[4] else 0.0
            results.append(RetrievalResult(
                concept=r[0],
                hebrew_word=r[1],
                similarity=round(r[2], 4) if r[2] else 0.0,
                kab_sim=round(kab_s, 4),
                ml_sim=round(ml_s, 4),
                gap=round(kab_s - ml_s, 4),
            ))
        return results

    def _query_hidden(
        self,
        target,
        top_k: int,
    ) -> list[RetrievalResult]:
        """Find hidden connections: kab_sim > ml_sim + gap_threshold.

        Pre-filters top candidates by kabbalistic proximity (pgvector index),
        then computes gap on that reduced set. O(candidate_limit * log(n)).
        """
        candidate_limit = max(top_k * 10, 200)
        with self._get_conn() as conn:
            kab_vec = target.kabbalistic.tolist()
            ml_vec = target.ml.tolist()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT concept, hebrew_word,
                           1 - (kabbalistic_signature <=> %s::vector) as kab_sim,
                           1 - (ml_embedding <=> %s::vector) as ml_sim
                    FROM hybrid_embeddings
                    WHERE concept != %s
                    ORDER BY kabbalistic_signature <=> %s::vector
                    LIMIT %s
                """, (kab_vec, ml_vec, target.concept, kab_vec, candidate_limit))
                rows = cur.fetchall()

        results = []
        for r in rows:
            kab_s = r[2] if r[2] else 0.0
            ml_s = r[3] if r[3] else 0.0
            gap = kab_s - ml_s
            if gap >= self.gap_threshold:
                results.append(RetrievalResult(
                    concept=r[0],
                    hebrew_word=r[1],
                    similarity=kab_s,  # primary similarity = kab
                    kab_sim=round(kab_s, 4),
                    ml_sim=round(ml_s, 4),
                    gap=round(gap, 4),
                ))

        results.sort(key=lambda r: r.gap, reverse=True)
        return results[:top_k]

    def enrich_context(
        self,
        query_text: str,
        hebrew_word: str | None = None,
        top_k: int = 5,
    ) -> str:
        """Produce an enriched context string for LLM prompt injection.

        Retrieves top_k concepts closest to the query in hybrid mode,
        formats them as a structured context block.

        Args:
            query_text: the query or domain to enrich
            hebrew_word: optional Hebrew form
            top_k: number of concepts to include

        Returns:
            Formatted context string for prompt injection.
        """
        results = self.query(query_text, hebrew_word=hebrew_word,
                             mode="hybrid", top_k=top_k)
        if not results:
            return ""

        lines = ["Concepts structurellement liés (Cube de l'Espace + ML) :"]
        for r in results:
            hebrew = f" ({r.hebrew_word})" if r.hebrew_word else ""
            hidden_tag = " [CACHÉ]" if r.gap >= self.gap_threshold else ""
            lines.append(
                f"  - {r.concept}{hebrew} "
                f"(sim={r.similarity:.3f}, kab={r.kab_sim:.3f}, "
                f"ml={r.ml_sim:.3f}){hidden_tag}"
            )

        # Also add hidden connections if any
        hidden = self.query(query_text, hebrew_word=hebrew_word,
                            mode="hidden", top_k=3)
        if hidden:
            lines.append("Connexions cachées (tradition > statistique) :")
            for r in hidden:
                hebrew = f" ({r.hebrew_word})" if r.hebrew_word else ""
                lines.append(
                    f"  - {r.concept}{hebrew} "
                    f"(kab={r.kab_sim:.3f} >> ml={r.ml_sim:.3f}, "
                    f"gap={r.gap:.3f})"
                )

        return "\n".join(lines)
