"""embedder.py — Génération des embeddings vectoriels pour Sifrei Yesod.

Utilise le même modèle Ollama que le reste du projet (nomic-embed-text, 768 dims).

Usage:
    python -m sifrei_yesod.pipeline.embedder --all
    python -m sifrei_yesod.pipeline.embedder --assertions-only
    python -m sifrei_yesod.pipeline.embedder --concepts-only
    python -m sifrei_yesod.pipeline.embedder --principes-only
"""

from __future__ import annotations

import argparse
import os
import sys

import psycopg2
import psycopg2.extras

from epistememory.embedding import embed

DB_URL = (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim"))

BATCH_SIZE = 20


class Embedder:
    """Generate embeddings for Sifrei Yesod entries missing them."""

    def __init__(self, db_url: str = DB_URL) -> None:
        self.db_url = db_url
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

    def embed_assertions(self) -> int:
        """Generate embeddings for assertions where embedding IS NULL."""
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id, assertion FROM sifrei_yesod_assertions WHERE embedding IS NULL"
        )
        rows = cur.fetchall()
        if not rows:
            return 0

        count = 0
        for row in rows:
            try:
                vec = embed(row["assertion"])
                cur.execute(
                    "UPDATE sifrei_yesod_assertions SET embedding = %s WHERE id = %s",
                    (vec, row["id"]),
                )
                count += 1
                if count % BATCH_SIZE == 0:
                    self.conn.commit()
            except Exception as e:
                print(f"  ⚠ Assertion {row['id']}: {e}")
                self.conn.rollback()

        self.conn.commit()
        return count

    def embed_concepts(self) -> int:
        """Generate embeddings for concepts where embedding IS NULL."""
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """SELECT id, concept_id, description, nom_fr
               FROM sifrei_yesod_concepts WHERE embedding IS NULL"""
        )
        rows = cur.fetchall()
        if not rows:
            return 0

        count = 0
        for row in rows:
            text = row["description"] or row["nom_fr"] or row["concept_id"]
            try:
                vec = embed(text)
                cur.execute(
                    "UPDATE sifrei_yesod_concepts SET embedding = %s WHERE id = %s",
                    (vec, row["id"]),
                )
                count += 1
                if count % BATCH_SIZE == 0:
                    self.conn.commit()
            except Exception as e:
                print(f"  ⚠ Concept {row['concept_id']}: {e}")
                self.conn.rollback()

        self.conn.commit()
        return count

    def embed_principes(self) -> int:
        """Generate embeddings for principes where embedding IS NULL."""
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id, formalisation FROM sifrei_yesod_principes WHERE embedding IS NULL"
        )
        rows = cur.fetchall()
        if not rows:
            return 0

        count = 0
        for row in rows:
            try:
                vec = embed(row["formalisation"])
                cur.execute(
                    "UPDATE sifrei_yesod_principes SET embedding = %s WHERE id = %s",
                    (vec, row["id"]),
                )
                count += 1
                if count % BATCH_SIZE == 0:
                    self.conn.commit()
            except Exception as e:
                print(f"  ⚠ Principe {row['id']}: {e}")
                self.conn.rollback()

        self.conn.commit()
        return count

    def embed_all(self) -> dict[str, int]:
        """Generate all missing embeddings."""
        return {
            "assertions": self.embed_assertions(),
            "concepts": self.embed_concepts(),
            "principes": self.embed_principes(),
        }


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="sifrei_yesod.pipeline.embedder",
        description="Embedder — Générer les embeddings vectoriels Sifrei Yesod",
    )
    parser.add_argument("--all", action="store_true", help="Tous les embeddings manquants")
    parser.add_argument("--assertions-only", action="store_true")
    parser.add_argument("--concepts-only", action="store_true")
    parser.add_argument("--principes-only", action="store_true")
    parser.add_argument("--db", default=DB_URL, help="URL PostgreSQL")
    args = parser.parse_args()

    if not any([args.all, args.assertions_only, args.concepts_only, args.principes_only]):
        parser.error("--all ou --assertions-only/--concepts-only/--principes-only requis")

    embedder = Embedder(db_url=args.db)

    try:
        if args.all:
            results = embedder.embed_all()
            print(f"  Assertions: {results['assertions']} embeddings générés")
            print(f"  Concepts:   {results['concepts']} embeddings générés")
            print(f"  Principes:  {results['principes']} embeddings générés")
        elif args.assertions_only:
            n = embedder.embed_assertions()
            print(f"  {n} embeddings d'assertions générés")
        elif args.concepts_only:
            n = embedder.embed_concepts()
            print(f"  {n} embeddings de concepts générés")
        elif args.principes_only:
            n = embedder.embed_principes()
            print(f"  {n} embeddings de principes générés")
    finally:
        embedder.close()


if __name__ == "__main__":
    main()
