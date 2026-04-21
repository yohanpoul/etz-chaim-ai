"""generate_cross_refs.py — Génération automatique des cross-références inter-shaarim.

Utilise la similarité cosinus sur les embeddings 768d (nomic-embed-text) déjà
stockés dans PostgreSQL/pgvector pour identifier les assertions sémantiquement
proches entre différents sha'arim.

Usage:
    python -m sifrei_yesod.pipeline.generate_cross_refs
    python -m sifrei_yesod.pipeline.generate_cross_refs --dry-run
    python -m sifrei_yesod.pipeline.generate_cross_refs --threshold 0.80 --top-k 5
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass

import psycopg2
import psycopg2.extras

DB_URL = (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim"))

DEFAULT_THRESHOLD = 0.75
DEFAULT_TOP_K = 3


@dataclass
class CrossRefCandidate:
    """A candidate cross-reference between two assertions."""

    source_assertion_id: str
    target_assertion_id: str
    target_sefer: str
    target_ref: str
    similarity: float


class CrossRefGenerator:
    """Generate cross-references between assertions of different sha'arim.

    Algorithm:
        For each assertion with an embedding, use pgvector's cosine distance
        operator (<=>) to find the top-k most similar assertions from a
        DIFFERENT sha'ar (identified by the (sefer_id, heikhal_number,
        shaar_number) tuple via the perakim join). Only pairs above the
        similarity threshold are kept.
    """

    def __init__(
        self,
        db_url: str = DB_URL,
        threshold: float = DEFAULT_THRESHOLD,
        top_k: int = DEFAULT_TOP_K,
    ) -> None:
        self.db_url = db_url
        self.threshold = threshold
        self.top_k = top_k
        self._conn: psycopg2.extensions.connection | None = None

    @property
    def conn(self) -> psycopg2.extensions.connection:
        if self._conn is None or self._conn.closed:
            # Pipeline batch standalone — connexion DIRECTE volontaire
            # (audit cycle 4, C5). Long-lived avec contrôle transactionnel
            # manuel (commit/rollback explicite). Le pool est pour le code
            # daemon-actif ; ces scripts sont CLI/pipelines one-shot.

            self._conn = psycopg2.connect(self.db_url)
            try:
                from pgvector.psycopg2 import register_vector

                register_vector(self._conn)
            except ImportError as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
            self._conn.commit()
            self._conn.autocommit = False
        return self._conn

    def close(self) -> None:
        if self._conn and not self._conn.closed:
            self._conn.close()

    def _count_existing(self) -> int:
        """Count existing cross-references."""
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM sifrei_yesod_cross_refs")
        return cur.fetchone()[0]

    def _count_assertions_with_embeddings(self) -> int:
        """Count assertions that have embeddings."""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM sifrei_yesod_assertions WHERE embedding IS NOT NULL"
        )
        return cur.fetchone()[0]

    def generate(self) -> list[CrossRefCandidate]:
        """Find cross-shaar similar assertion pairs via pgvector.

        Uses a single SQL query per source assertion to find the top-k
        neighbors from different sha'arim. The cosine similarity is
        computed as ``1 - (embedding <=> target.embedding)``.

        Returns:
            List of CrossRefCandidate with similarity >= threshold.
        """
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Fetch all assertions with their shaar coordinates
        cur.execute(
            """
            SELECT
                a.assertion_id,
                a.source_ref,
                a.embedding,
                p.sefer_id,
                p.heikhal_number,
                p.shaar_number
            FROM sifrei_yesod_assertions a
            JOIN sifrei_yesod_perakim p ON a.perek_id = p.id
            WHERE a.embedding IS NOT NULL
            ORDER BY a.assertion_id
            """
        )
        assertions = cur.fetchall()

        if not assertions:
            print("  Aucune assertion avec embedding trouvée.")
            return []

        print(f"  {len(assertions)} assertions avec embeddings")

        candidates: list[CrossRefCandidate] = []
        seen_pairs: set[tuple[str, str]] = set()

        for i, src in enumerate(assertions):
            # Use pgvector to find top-k neighbors from different shaarim
            cur.execute(
                """
                SELECT
                    a2.assertion_id,
                    a2.source_ref,
                    p2.sefer_id,
                    1 - (a2.embedding <=> %s::vector) AS similarity
                FROM sifrei_yesod_assertions a2
                JOIN sifrei_yesod_perakim p2 ON a2.perek_id = p2.id
                WHERE a2.embedding IS NOT NULL
                  AND a2.assertion_id != %s
                  AND (p2.sefer_id, p2.heikhal_number, p2.shaar_number)
                      != (%s, %s, %s)
                ORDER BY a2.embedding <=> %s::vector
                LIMIT %s
                """,
                (
                    src["embedding"],
                    src["assertion_id"],
                    src["sefer_id"],
                    src["heikhal_number"],
                    src["shaar_number"],
                    src["embedding"],
                    self.top_k,
                ),
            )
            neighbors = cur.fetchall()

            for nb in neighbors:
                if nb["similarity"] < self.threshold:
                    continue

                # Deduplicate: keep only one direction (A->B, not also B->A)
                pair = tuple(sorted([src["assertion_id"], nb["assertion_id"]]))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                candidates.append(
                    CrossRefCandidate(
                        source_assertion_id=src["assertion_id"],
                        target_assertion_id=nb["assertion_id"],
                        target_sefer=nb["sefer_id"],
                        target_ref=nb["source_ref"],
                        similarity=round(float(nb["similarity"]), 4),
                    )
                )

            if (i + 1) % 100 == 0:
                print(f"  ... {i + 1}/{len(assertions)} assertions traitées")

        # Sort by similarity descending
        candidates.sort(key=lambda c: c.similarity, reverse=True)
        print(f"  {len(candidates)} cross-références trouvées (seuil={self.threshold})")
        return candidates

    def insert(self, candidates: list[CrossRefCandidate]) -> int:
        """Insert cross-reference candidates into sifrei_yesod_cross_refs.

        Returns:
            Number of rows inserted.
        """
        if not candidates:
            return 0

        cur = self.conn.cursor()

        # Clear existing auto-generated cross-refs (relation_type = 'embedding_similarity')
        cur.execute(
            "DELETE FROM sifrei_yesod_cross_refs WHERE relation_type = 'embedding_similarity'"
        )
        deleted = cur.rowcount
        if deleted > 0:
            print(f"  {deleted} anciennes cross-refs (embedding_similarity) supprimées")

        inserted = 0
        for c in candidates:
            cur.execute(
                """
                INSERT INTO sifrei_yesod_cross_refs
                    (source_assertion_id, target_assertion_id, target_sefer,
                     target_ref, relation_type, description)
                VALUES (%s, %s, %s, %s, 'embedding_similarity', %s)
                """,
                (
                    c.source_assertion_id,
                    c.target_assertion_id,
                    c.target_sefer,
                    c.target_ref,
                    f"Cosine similarity: {c.similarity}",
                ),
            )
            inserted += 1

        self.conn.commit()
        return inserted


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="sifrei_yesod.pipeline.generate_cross_refs",
        description=(
            "Génération automatique des cross-références inter-shaarim "
            "par similarité d'embedding (pgvector cosine)"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Afficher les cross-refs sans les insérer",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Seuil de similarité minimum (défaut: {DEFAULT_THRESHOLD})",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help=f"Nombre de voisins par assertion (défaut: {DEFAULT_TOP_K})",
    )
    parser.add_argument("--db", default=DB_URL, help="URL PostgreSQL")
    args = parser.parse_args()

    gen = CrossRefGenerator(
        db_url=args.db,
        threshold=args.threshold,
        top_k=args.top_k,
    )

    try:
        print(f"Cross-Refs Generator — seuil={args.threshold}, top-k={args.top_k}")
        print(f"  Cross-refs existantes: {gen._count_existing()}")
        print(f"  Assertions avec embeddings: {gen._count_assertions_with_embeddings()}")
        print()

        candidates = gen.generate()

        if not candidates:
            print("\n  Aucune cross-référence au-dessus du seuil.")
            return

        # Show top results
        print(f"\n  Top 20 cross-références (sur {len(candidates)}):")
        for c in candidates[:20]:
            print(
                f"    {c.source_assertion_id} <-> {c.target_assertion_id}"
                f"  sim={c.similarity}  ref={c.target_ref}"
            )

        if args.dry_run:
            print(f"\n  [DRY RUN] {len(candidates)} cross-refs non insérées.")
        else:
            inserted = gen.insert(candidates)
            print(f"\n  {inserted} cross-références insérées dans sifrei_yesod_cross_refs.")
    finally:
        gen.close()


if __name__ == "__main__":
    main()
