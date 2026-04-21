"""kabbalah/clustering.py — Clustering kabbalistique vs ML.

קִבּוּץ — Rassemblement

Regroupe les concepts par proximité dans le Cube (30 dims kabbalistiques)
vs par proximité ML (768 dims sémantiques). Les désaccords entre les deux
clusterings révèlent les zones de tension entre tradition et statistique.

Usage:
    kc = KabbalisticClustering()
    kc.load_from_db()
    kab_clusters = kc.cluster_by_cube(n_clusters=10)
    ml_clusters = kc.cluster_by_ml(n_clusters=10)
    disagreements = kc.find_disagreements()
    print(kc.summary())
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ClusterInfo:
    """Information about a cluster."""
    cluster_id: int
    concepts: list[str]
    centroid: np.ndarray
    size: int

    def __repr__(self) -> str:
        preview = ", ".join(self.concepts[:5])
        if len(self.concepts) > 5:
            preview += f", ... (+{len(self.concepts) - 5})"
        return f"Cluster {self.cluster_id} [{self.size}]: {preview}"


@dataclass
class Disagreement:
    """A concept in different clusters between Cube and ML."""
    concept: str
    hebrew_word: str | None
    cube_cluster: int
    ml_cluster: int
    cube_neighbors: list[str]   # other concepts in same cube cluster
    ml_neighbors: list[str]     # other concepts in same ml cluster


@dataclass
class PairDisagreement:
    """A pair of concepts where Kab and ML disagree on proximity."""
    concept_a: str
    concept_b: str
    same_cluster_kab: bool
    same_cluster_ml: bool
    kab_similarity: float
    ml_similarity: float
    gap: float
    disagreement_type: str  # 'kab_close_ml_far' or 'ml_close_kab_far'


def _kmeans(data: np.ndarray, k: int, max_iter: int = 100) -> np.ndarray:
    """Simple K-means implementation (no sklearn dependency).

    Args:
        data: (n, d) array of points
        k: number of clusters
        max_iter: maximum iterations

    Returns:
        labels: (n,) array of cluster assignments
    """
    n = data.shape[0]
    if k >= n:
        return np.arange(n)

    # Initialize centroids with k-means++ strategy
    rng = np.random.RandomState(42)
    centroids = np.empty((k, data.shape[1]), dtype=data.dtype)
    centroids[0] = data[rng.randint(n)]

    for i in range(1, k):
        dists = np.min(
            np.sum((data[:, None] - centroids[:i]) ** 2, axis=2),
            axis=1,
        )
        probs = dists / dists.sum()
        centroids[i] = data[rng.choice(n, p=probs)]

    labels = np.zeros(n, dtype=np.int32)
    for _ in range(max_iter):
        # Assign
        dists = np.sum((data[:, None] - centroids) ** 2, axis=2)
        new_labels = np.argmin(dists, axis=1)

        if np.array_equal(labels, new_labels):
            break
        labels = new_labels

        # Update centroids
        for i in range(k):
            mask = labels == i
            if mask.any():
                centroids[i] = data[mask].mean(axis=0)

    return labels


class KabbalisticClustering:
    """Clustering dual : Cube (kabbalistique) vs ML (sémantique).

    Les concepts sont groupés selon deux perspectives :
    - Cube : signature kabbalistique 30 dims (structure du SY)
    - ML : embedding 768 dims (sémantique statistique)

    Les désaccords entre les deux sont les pistes d'investigation.
    """

    def __init__(self, db_url: str | None = None) -> None:
        self.db_url = db_url or os.environ.get(
            "ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim",
        )
        self.concepts: list[str] = []
        self.hebrews: list[str | None] = []
        self.kab_matrix: np.ndarray | None = None  # (n, 30)
        self.ml_matrix: np.ndarray | None = None    # (n, 768)

        self._kab_labels: np.ndarray | None = None
        self._ml_labels: np.ndarray | None = None
        self._n_clusters: int = 0

    def load_from_db(self) -> int:
        """Load all embeddings from hybrid_embeddings table.

        Returns:
            Number of concepts loaded.
        """
        from pool import get_conn, init_pool
        init_pool(self.db_url)  # idempotent
        with get_conn() as conn:
            try:
                from pgvector.psycopg2 import register_vector
                register_vector(conn)
            except ImportError as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT concept, hebrew_word,
                           kabbalistic_signature, ml_embedding
                    FROM hybrid_embeddings
                    WHERE kabbalistic_signature IS NOT NULL
                      AND ml_embedding IS NOT NULL
                    ORDER BY concept
                """)
                rows = cur.fetchall()

        self.concepts = []
        self.hebrews = []
        kab_list = []
        ml_list = []

        for r in rows:
            self.concepts.append(r[0])
            self.hebrews.append(r[1])
            kab_list.append(np.asarray(r[2], dtype=np.float32))
            ml_list.append(np.asarray(r[3], dtype=np.float32))

        if kab_list:
            self.kab_matrix = np.stack(kab_list)
            self.ml_matrix = np.stack(ml_list)

        logger.info("Loaded %d concepts for clustering", len(self.concepts))
        return len(self.concepts)

    def cluster_by_cube(self, n_clusters: int = 10) -> list[ClusterInfo]:
        """Cluster concepts by kabbalistic signature (30 dims).

        Concepts in the same cluster are structurally related
        according to the tradition (Cube geometry, registers, gematria).
        """
        if self.kab_matrix is None or len(self.concepts) == 0:
            return []

        self._n_clusters = n_clusters

        # Normalize before clustering
        norms = np.linalg.norm(self.kab_matrix, axis=1, keepdims=True)
        norms = np.where(norms < 1e-10, 1.0, norms)
        normed = self.kab_matrix / norms

        self._kab_labels = _kmeans(normed, n_clusters)
        return self._build_cluster_infos(self._kab_labels, normed, "cube")

    def cluster_by_ml(self, n_clusters: int = 10) -> list[ClusterInfo]:
        """Cluster concepts by ML embedding (768 dims).

        Concepts in the same cluster are semantically close
        according to statistical language models.
        """
        if self.ml_matrix is None or len(self.concepts) == 0:
            return []

        self._n_clusters = n_clusters

        norms = np.linalg.norm(self.ml_matrix, axis=1, keepdims=True)
        norms = np.where(norms < 1e-10, 1.0, norms)
        normed = self.ml_matrix / norms

        self._ml_labels = _kmeans(normed, n_clusters)
        return self._build_cluster_infos(self._ml_labels, normed, "ml")

    def _build_cluster_infos(
        self, labels: np.ndarray, data: np.ndarray, mode: str,
    ) -> list[ClusterInfo]:
        """Build ClusterInfo objects from labels."""
        n_clusters = int(labels.max()) + 1
        clusters = []
        for i in range(n_clusters):
            mask = labels == i
            members = [self.concepts[j] for j in range(len(self.concepts)) if mask[j]]
            if not members:
                continue
            centroid = data[mask].mean(axis=0)
            clusters.append(ClusterInfo(
                cluster_id=i,
                concepts=members,
                centroid=centroid,
                size=len(members),
            ))
        clusters.sort(key=lambda c: c.size, reverse=True)
        return clusters

    def find_disagreements(self) -> list[Disagreement]:
        """Find concepts that are in different clusters between Cube and ML.

        These are the zones of tension: the tradition groups them one way,
        the statistics groups them another way. Each disagreement is a
        potential investigation lead.

        Must call cluster_by_cube() and cluster_by_ml() first.
        """
        if self._kab_labels is None or self._ml_labels is None:
            return []

        disagreements = []
        for i, concept in enumerate(self.concepts):
            kab_c = int(self._kab_labels[i])
            ml_c = int(self._ml_labels[i])

            if kab_c == ml_c:
                continue

            # Find neighbors in each cluster
            kab_neighbors = [
                self.concepts[j]
                for j in range(len(self.concepts))
                if self._kab_labels[j] == kab_c and j != i
            ][:5]

            ml_neighbors = [
                self.concepts[j]
                for j in range(len(self.concepts))
                if self._ml_labels[j] == ml_c and j != i
            ][:5]

            disagreements.append(Disagreement(
                concept=concept,
                hebrew_word=self.hebrews[i],
                cube_cluster=kab_c,
                ml_cluster=ml_c,
                cube_neighbors=kab_neighbors,
                ml_neighbors=ml_neighbors,
            ))

        return disagreements

    def summary(self) -> dict:
        """Summary statistics of the dual clustering."""
        result = {
            "total_concepts": len(self.concepts),
            "n_clusters": self._n_clusters,
        }

        if self._kab_labels is not None:
            kab_sizes = [
                int(np.sum(self._kab_labels == i))
                for i in range(int(self._kab_labels.max()) + 1)
            ]
            result["cube_cluster_sizes"] = sorted(kab_sizes, reverse=True)

        if self._ml_labels is not None:
            ml_sizes = [
                int(np.sum(self._ml_labels == i))
                for i in range(int(self._ml_labels.max()) + 1)
            ]
            result["ml_cluster_sizes"] = sorted(ml_sizes, reverse=True)

        if self._kab_labels is not None and self._ml_labels is not None:
            agreements = int(np.sum(self._kab_labels == self._ml_labels))
            result["agreements"] = agreements
            result["disagreements"] = len(self.concepts) - agreements
            result["agreement_ratio"] = round(
                agreements / max(len(self.concepts), 1), 3,
            )

        return result

    # ── Pairwise disagreements (the real signal) ──────────────

    def find_pairwise_disagreements(
        self,
        top_n: int = 100,
        min_gap: float = 0.2,
    ) -> list[PairDisagreement]:
        """Find pairs where Kab and ML disagree most on proximity.

        For each pair (i, j), computes cosine similarity in both spaces.
        Pairs where |kab_sim - ml_sim| > min_gap are disagreements.

        Returns top_n pairs sorted by gap descending.
        """
        if self.kab_matrix is None or self.ml_matrix is None:
            return []

        n = len(self.concepts)
        if n < 2:
            return []

        # Normalize both spaces
        kab_norms = np.linalg.norm(self.kab_matrix, axis=1, keepdims=True)
        kab_norms = np.where(kab_norms < 1e-10, 1.0, kab_norms)
        kab_normed = self.kab_matrix / kab_norms

        ml_norms = np.linalg.norm(self.ml_matrix, axis=1, keepdims=True)
        ml_norms = np.where(ml_norms < 1e-10, 1.0, ml_norms)
        ml_normed = self.ml_matrix / ml_norms

        # Pairwise cosine similarities (full matrices)
        kab_sim = kab_normed @ kab_normed.T
        ml_sim = ml_normed @ ml_normed.T

        # Upper triangle only (avoid duplicates and self-pairs)
        triu_i, triu_j = np.triu_indices(n, k=1)
        kab_vals = kab_sim[triu_i, triu_j]
        ml_vals = ml_sim[triu_i, triu_j]
        gaps = np.abs(kab_vals - ml_vals)

        # Filter by min_gap
        mask = gaps >= min_gap
        if not mask.any():
            return []

        fi = triu_i[mask]
        fj = triu_j[mask]
        fk = kab_vals[mask]
        fm = ml_vals[mask]
        fg = gaps[mask]

        # Top-N by gap descending
        order = np.argsort(-fg)[:top_n]

        # Cluster membership (if available)
        has_labels = self._kab_labels is not None and self._ml_labels is not None

        results = []
        for idx in order:
            i, j = int(fi[idx]), int(fj[idx])
            ks, ms, g = float(fk[idx]), float(fm[idx]), float(fg[idx])

            # Alphabetical ordering for DB uniqueness
            a, b = self.concepts[i], self.concepts[j]
            if a > b:
                a, b = b, a

            same_kab = bool(self._kab_labels[i] == self._kab_labels[j]) if has_labels else False
            same_ml = bool(self._ml_labels[i] == self._ml_labels[j]) if has_labels else False

            results.append(PairDisagreement(
                concept_a=a,
                concept_b=b,
                same_cluster_kab=same_kab,
                same_cluster_ml=same_ml,
                kab_similarity=ks,
                ml_similarity=ms,
                gap=g,
                disagreement_type="kab_close_ml_far" if ks > ms else "ml_close_kab_far",
            ))

        return results

    # ── Persistence ─────��─────────────────────────────────────

    def persist_run(
        self,
        pair_disagreements: list[PairDisagreement],
        n_clusters: int = 10,
    ) -> int:
        """Persist clustering run + disagreements to DB.

        Temporal tracking: existing pairs get times_seen incremented.
        Returns the run_id.
        """
        import json
        from pool import get_conn, init_pool
        init_pool(self.db_url)  # idempotent
        with get_conn() as conn:
            with conn.cursor() as cur:
                # 1. Insert run summary
                s = self.summary()
                cur.execute("""
                    INSERT INTO clustering_results
                        (n_concepts, n_clusters_kab, n_clusters_ml,
                         n_disagreements, agreement_ratio, algorithm, params)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    s["total_concepts"],
                    n_clusters,
                    n_clusters,
                    len(pair_disagreements),
                    s.get("agreement_ratio", 0.0),
                    "kmeans",
                    json.dumps({"n_clusters": n_clusters}),
                ))
                run_id = cur.fetchone()[0]

                # 2. Upsert disagreements with temporal tracking
                for d in pair_disagreements:
                    cur.execute("""
                        INSERT INTO clustering_disagreements
                            (run_id, concept_a, concept_b, same_cluster_kab,
                             same_cluster_ml, kab_similarity, ml_similarity,
                             gap, disagreement_type)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (concept_a, concept_b) DO UPDATE SET
                            run_id = EXCLUDED.run_id,
                            same_cluster_kab = EXCLUDED.same_cluster_kab,
                            same_cluster_ml = EXCLUDED.same_cluster_ml,
                            kab_similarity = EXCLUDED.kab_similarity,
                            ml_similarity = EXCLUDED.ml_similarity,
                            gap = EXCLUDED.gap,
                            disagreement_type = EXCLUDED.disagreement_type,
                            last_seen = NOW(),
                            times_seen = clustering_disagreements.times_seen + 1
                    """, (
                        run_id, d.concept_a, d.concept_b,
                        d.same_cluster_kab, d.same_cluster_ml,
                        d.kab_similarity, d.ml_similarity,
                        d.gap, d.disagreement_type,
                    ))

        logger.info("Persisted run %d: %d disagreements", run_id, len(pair_disagreements))
        return run_id

    def route_to_dissensus(
        self,
        pair_disagreements: list[PairDisagreement],
        tiferet,
        top_n: int = 5,
    ) -> list[dict]:
        """Route top unrouted disagreements to DissensuEngine.

        Creates conclusion pairs and tensions for the strongest disagreements
        that haven't been routed yet.

        Args:
            pair_disagreements: disagreements (sorted by gap desc).
            tiferet: DissensuEngine instance.
            top_n: max disagreements to route.

        Returns:
            List of {concept_a, concept_b, gap, tension_id} dicts.
        """
        import psycopg2.extras

        # Find unrouted pairs
        from pool import get_conn, init_pool
        init_pool(self.db_url)  # idempotent
        routed = []
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT concept_a, concept_b
                    FROM clustering_disagreements
                    WHERE dissensus_id IS NOT NULL
                """)
                already_routed = {
                    (r["concept_a"], r["concept_b"]) for r in cur.fetchall()
                }

            unrouted = [
                d for d in pair_disagreements
                if (d.concept_a, d.concept_b) not in already_routed
            ][:top_n]

            for d in unrouted:
                # Create 2 conclusions: one per perspective
                if d.disagreement_type == "kab_close_ml_far":
                    content_a = (
                        f"{d.concept_a} et {d.concept_b} sont structurellement proches "
                        f"dans le Cube kabbalistique (cosine={d.kab_similarity:.3f})"
                    )
                    content_b = (
                        f"{d.concept_a} et {d.concept_b} sont sémantiquement distants "
                        f"dans l'espace ML (cosine={d.ml_similarity:.3f})"
                    )
                else:
                    content_a = (
                        f"{d.concept_a} et {d.concept_b} sont structurellement distants "
                        f"dans le Cube kabbalistique (cosine={d.kab_similarity:.3f})"
                    )
                    content_b = (
                        f"{d.concept_a} et {d.concept_b} sont sémantiquement proches "
                        f"dans l'espace ML (cosine={d.ml_similarity:.3f})"
                    )

                c_kab = tiferet.submit_conclusion(
                    content=content_a,
                    source_label="kabbalistic_clustering",
                    source_type="system",
                    domain="clustering",
                    confidence=abs(d.kab_similarity),
                )
                c_ml = tiferet.submit_conclusion(
                    content=content_b,
                    source_label="ml_clustering",
                    source_type="system",
                    domain="clustering",
                    confidence=abs(d.ml_similarity),
                )

                # Normalize gap to [0, 1] for DissensuEngine
                # (cosine sim range is [-1, 1], so max gap = 2.0)
                normalized_div = min(d.gap / 2.0, 1.0)
                tension = tiferet.db.create_tension(
                    conclusion_a_id=c_kab.id,
                    conclusion_b_id=c_ml.id,
                    tension_type="framing_difference",
                    divergence_score=normalized_div,
                    description=(
                        f"Tradition vs Statistique : {d.concept_a} & {d.concept_b} "
                        f"— {d.disagreement_type} (gap={d.gap:.3f})"
                    ),
                )

                # Mark as routed in DB
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE clustering_disagreements
                        SET dissensus_id = %s, routed_at = NOW()
                        WHERE concept_a = %s AND concept_b = %s
                    """, (str(tension.id), d.concept_a, d.concept_b))

                routed.append({
                    "concept_a": d.concept_a,
                    "concept_b": d.concept_b,
                    "gap": d.gap,
                    "tension_id": str(tension.id),
                })

            logger.info("Routed %d disagreements to DissensuEngine", len(routed))

        return routed

    # ── Full pipeline ���────────────────────────────────────────

    def run_full(
        self,
        n_clusters: int = 10,
        top_n_pairs: int = 100,
        min_gap: float = 0.2,
        tiferet=None,
        route_top: int = 5,
    ) -> dict:
        """Run the complete dual clustering pipeline.

        1. Load embeddings
        2. Cluster by Cube and ML
        3. Find pairwise disagreements
        4. Persist results
        5. Route top disagreements to DissensuEngine

        Returns a complete report dict.
        """
        n_loaded = self.load_from_db()
        if n_loaded == 0:
            return {"status": "no_data", "n_concepts": 0}

        self.cluster_by_cube(n_clusters)
        self.cluster_by_ml(n_clusters)

        pair_disagreements = self.find_pairwise_disagreements(
            top_n=top_n_pairs, min_gap=min_gap,
        )

        s = self.summary()
        run_id = self.persist_run(pair_disagreements, n_clusters)

        report = {
            "status": "ok",
            "run_id": run_id,
            "n_concepts": s["total_concepts"],
            "n_clusters": n_clusters,
            "agreement_ratio": s.get("agreement_ratio", 0.0),
            "n_concept_disagreements": s.get("disagreements", 0),
            "n_pair_disagreements": len(pair_disagreements),
            "top_5": [
                {
                    "concept_a": d.concept_a,
                    "concept_b": d.concept_b,
                    "kab_sim": round(d.kab_similarity, 3),
                    "ml_sim": round(d.ml_similarity, 3),
                    "gap": round(d.gap, 3),
                    "type": d.disagreement_type,
                }
                for d in pair_disagreements[:5]
            ],
        }

        # Route to DissensuEngine if available
        if tiferet is not None:
            routed = self.route_to_dissensus(
                pair_disagreements, tiferet, top_n=route_top,
            )
            report["routed_to_dissensus"] = len(routed)
            report["routed_details"] = routed
        else:
            report["routed_to_dissensus"] = 0

        return report

    def _detect_cluster_dynamics(self, labels: np.ndarray) -> dict:
        """Detect clusters that should be split.

        Split candidates: clusters with size > 2x mean cluster size.

        Returns:
            {"split_candidates": list[int]}
        """
        from collections import Counter
        sizes = Counter(labels.tolist())
        if not sizes:
            return {"split_candidates": []}
        mean_size = np.mean(list(sizes.values()))
        split_candidates = [
            cid for cid, size in sizes.items()
            if size > 2 * mean_size
        ]
        return {"split_candidates": split_candidates}

    def _find_merge_candidates(
        self,
        centroids: dict[int, np.ndarray],
        threshold: float = 0.9,
    ) -> list[tuple[int, int]]:
        """Find cluster pairs with centroids too close (cosine > threshold).

        Returns:
            List of (cluster_id_a, cluster_id_b) pairs that could be merged.
        """
        from itertools import combinations
        merges: list[tuple[int, int]] = []
        for i, j in combinations(centroids.keys(), 2):
            a, b = centroids[i], centroids[j]
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a < 1e-8 or norm_b < 1e-8:
                continue
            cosine = float(np.dot(a, b) / (norm_a * norm_b))
            if cosine > threshold:
                merges.append((min(i, j), max(i, j)))
        return merges
