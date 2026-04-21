"""Tests de l'embedder Sifrei Yesod."""

import pytest
import psycopg2
import psycopg2.extras

from .conftest import TEST_DB_URL


def test_embed_assertions(seeded_db):
    """Les embeddings sont générés pour les assertions sans embedding."""
    from sifrei_yesod.pipeline.embedder import Embedder
    embedder = Embedder(db_url=TEST_DB_URL)

    try:
        count = embedder.embed_assertions()
        assert count == 2  # 2 assertions in fixture

        # Verify embeddings exist
        conn = psycopg2.connect(TEST_DB_URL)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM sifrei_yesod_assertions "
            "WHERE embedding IS NOT NULL AND assertion_id LIKE 'EC-K99-%'"
        )
        assert cur.fetchone()[0] == 2
        cur.close()
        conn.close()
    finally:
        embedder.close()


def test_skip_existing_embeddings(seeded_db):
    """Les embeddings déjà générés ne sont pas recalculés."""
    from sifrei_yesod.pipeline.embedder import Embedder
    embedder = Embedder(db_url=TEST_DB_URL)

    try:
        # First pass
        count1 = embedder.embed_assertions()
        assert count1 == 2

        # Second pass — should skip all
        count2 = embedder.embed_assertions()
        assert count2 == 0
    finally:
        embedder.close()
