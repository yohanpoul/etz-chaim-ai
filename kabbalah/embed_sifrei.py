"""kabbalah/embed_sifrei.py — Embedding hybride pour les concepts Sifrei Yesod.

שִׁלּוּב ספרי יסוד — Intégration des textes fondateurs

Peuple hybrid_embeddings avec tous les concepts de sifrei_yesod_concepts
qui n'y figurent pas encore. Suit le même pattern que embed_initial.py
et embed_gates.py.

Deux cas :
  - Concepts avec nom_fr : utilisent nom_fr comme label (déjà couverts par embed_initial)
  - Concepts sans nom_fr : utilisent concept_id comme label, nom_he comme hebrew_word

Usage:
    python -m kabbalah.embed_sifrei [--batch-size 50] [--db-url URL] [--dry-run]
"""

from __future__ import annotations

import argparse
import logging
import os
import time
from datetime import datetime

import psycopg2
import psycopg2.extras

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DB_URL = (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim"))


class SifreiYesodEmbedder:
    """Embedding hybride pour les concepts Sifrei Yesod."""

    def __init__(self, db_url: str = DB_URL, batch_size: int = 50) -> None:
        self.db_url = db_url
        self.batch_size = batch_size
        self._conn: psycopg2.extensions.connection | None = None
        self._he = None  # lazy HybridEmbedding

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
        return self._conn

    @property
    def he(self):
        if self._he is None:
            from kabbalah.hybrid_embedding import HybridEmbedding
            self._he = HybridEmbedding(db_url=self.db_url)
        return self._he

    def close(self) -> None:
        if self._conn and not self._conn.closed:
            self._conn.close()

    def find_unembedded(self) -> list[dict]:
        """Trouve les concepts sifrei_yesod sans entrée dans hybrid_embeddings.

        Retourne une liste de dicts avec id, concept_id, nom_he, nom_fr, description.
        """
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT sy.id, sy.concept_id, sy.nom_he, sy.nom_fr, sy.description
            FROM sifrei_yesod_concepts sy
            WHERE NOT EXISTS (
                SELECT 1 FROM hybrid_embeddings he
                WHERE he.concept = COALESCE(sy.nom_fr, sy.concept_id)
            )
            ORDER BY sy.id
        """)
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]

    def _build_embed_text(self, concept: dict) -> str:
        """Construit le texte à passer au ML embedding.

        Priorité : description > nom_fr > concept_id enrichi.
        """
        if concept.get("description"):
            return concept["description"]
        if concept.get("nom_fr"):
            nom_he = concept.get("nom_he") or ""
            return f"{concept['nom_fr']} ({nom_he}) — concept kabbalistique du Etz Chaim"
        nom_he = concept.get("nom_he") or ""
        cid = concept.get("concept_id", "")
        label = cid.replace("_", " ")
        return f"{label} ({nom_he}) — concept kabbalistique du Etz Chaim"

    def _concept_label(self, concept: dict) -> str:
        """Le label utilisé comme clé dans hybrid_embeddings.concept."""
        return concept.get("nom_fr") or concept.get("concept_id", "")

    def embed_concept(self, concept: dict, max_retries: int = 3) -> bool:
        """Embed un seul concept Sifrei Yesod dans hybrid_embeddings.

        Args:
            concept: dict avec concept_id, nom_he, nom_fr, description
            max_retries: nombre de tentatives si Ollama est down

        Returns:
            True si embeddé avec succès.
        """
        label = self._concept_label(concept)
        hebrew = concept.get("nom_he")
        embed_text = self._build_embed_text(concept)

        for attempt in range(max_retries):
            try:
                vec = self.he.embed(embed_text, hebrew_word=hebrew)
                # Override concept name to the label (embed_text was for ML quality)
                vec.concept = label
                vec.hebrew_word = hebrew
                self.he.save_to_db(vec)
                return True
            except Exception as e:
                if "connection" in str(e).lower() or "ollama" in str(e).lower():
                    wait = 2 ** attempt
                    logger.warning(
                        "Ollama/connection error for %s, retry %d/%d in %ds: %s",
                        label, attempt + 1, max_retries, wait, e,
                    )
                    time.sleep(wait)
                else:
                    logger.error("Failed to embed %s: %s", label, e)
                    return False

        logger.error("All retries exhausted for %s", label)
        return False

    def embed_all_missing(self, dry_run: bool = False) -> dict:
        """Embed tous les concepts manquants par batch.

        Args:
            dry_run: si True, ne fait que compter sans embedder.

        Returns:
            {"found": int, "embedded": int, "errors": int, "skipped": int}
        """
        unembedded = self.find_unembedded()
        stats = {"found": len(unembedded), "embedded": 0, "errors": 0, "skipped": 0}

        if dry_run:
            logger.info("DRY RUN: %d concepts à embedder", len(unembedded))
            return stats

        logger.info("Embedding %d concepts Sifrei Yesod manquants...", len(unembedded))

        for i, concept in enumerate(unembedded):
            label = self._concept_label(concept)
            if not label:
                stats["skipped"] += 1
                continue

            ok = self.embed_concept(concept)
            if ok:
                stats["embedded"] += 1
            else:
                stats["errors"] += 1

            if (i + 1) % self.batch_size == 0:
                logger.info(
                    "  Batch %d: %d/%d embeddés, %d erreurs",
                    (i + 1) // self.batch_size,
                    stats["embedded"], stats["found"], stats["errors"],
                )

        logger.info(
            "Terminé: %d embeddés, %d erreurs, %d skippés sur %d",
            stats["embedded"], stats["errors"], stats["skipped"], stats["found"],
        )
        return stats

    def embed_new_since(self, since: datetime) -> dict:
        """Embed les concepts ajoutés depuis une date donnée.

        Args:
            since: datetime UTC, embed uniquement les concepts créés après.

        Returns:
            {"found": int, "embedded": int, "errors": int}
        """
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT sy.id, sy.concept_id, sy.nom_he, sy.nom_fr, sy.description
            FROM sifrei_yesod_concepts sy
            WHERE sy.created_at >= %s
              AND NOT EXISTS (
                  SELECT 1 FROM hybrid_embeddings he
                  WHERE he.concept = COALESCE(sy.nom_fr, sy.concept_id)
              )
            ORDER BY sy.id
        """, (since,))
        rows = cur.fetchall()
        cur.close()

        stats = {"found": len(rows), "embedded": 0, "errors": 0}

        for concept in rows:
            ok = self.embed_concept(dict(concept))
            if ok:
                stats["embedded"] += 1
            else:
                stats["errors"] += 1

        if stats["found"] > 0:
            logger.info(
                "embed_new_since(%s): %d embeddés, %d erreurs sur %d",
                since.isoformat(), stats["embedded"], stats["errors"], stats["found"],
            )
        return stats

    def embed_new_concepts(self) -> dict:
        """Détecte et embed tous les concepts non encore dans hybrid_embeddings.

        Couvre TOUTES les sources : sifrei_yesod + tout concept orphelin.
        Point d'entrée pour le pipeline incrémental / daemon.

        Returns:
            {"embedded": int, "errors": int, "sources": {"sifrei_yesod": int}}
        """
        stats = {"embedded": 0, "errors": 0, "sources": {"sifrei_yesod": 0}}

        unembedded = self.find_unembedded()
        if not unembedded:
            return stats

        logger.info("Pipeline incrémental: %d concepts à embedder", len(unembedded))

        for concept in unembedded:
            label = self._concept_label(concept)
            if not label:
                continue
            ok = self.embed_concept(concept)
            if ok:
                stats["embedded"] += 1
                stats["sources"]["sifrei_yesod"] += 1
            else:
                stats["errors"] += 1

        logger.info(
            "Pipeline incrémental terminé: %d embeddés, %d erreurs",
            stats["embedded"], stats["errors"],
        )
        return stats


def main():
    parser = argparse.ArgumentParser(
        prog="kabbalah.embed_sifrei",
        description="Embed les concepts Sifrei Yesod dans hybrid_embeddings",
    )
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--db-url", default=None)
    parser.add_argument("--dry-run", action="store_true",
                        help="Compter seulement, ne pas embedder")
    args = parser.parse_args()

    embedder = SifreiYesodEmbedder(
        db_url=args.db_url or DB_URL,
        batch_size=args.batch_size,
    )
    try:
        stats = embedder.embed_all_missing(dry_run=args.dry_run)
        print(f"\nRésultat:")
        print(f"  Trouvés  : {stats['found']}")
        print(f"  Embeddés : {stats['embedded']}")
        print(f"  Erreurs  : {stats['errors']}")
        print(f"  Skippés  : {stats['skipped']}")
    finally:
        embedder.close()


if __name__ == "__main__":
    main()
