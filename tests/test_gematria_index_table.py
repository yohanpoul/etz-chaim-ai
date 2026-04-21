"""Régression F-S1-003 — gematria_index table accessibilité.

Bug : `gematria` absent de init_db.py SCHEMA_ORDER → table jamais créée →
étape ↑⑥½ Gématria Or Chozer dégradée par "relation does not exist".
"""

from __future__ import annotations

from pathlib import Path

import psycopg2
import pytest


PROJECT_ROOT = Path(__file__).parent.parent


def test_gematria_in_schema_order():
    """init_db.py SCHEMA_ORDER doit inclure 'gematria' pour créer gematria_index."""
    import init_db
    assert "gematria" in init_db.SCHEMA_ORDER, (
        "gematria absent de SCHEMA_ORDER — gematria_index ne sera pas créée"
    )


def test_gematria_schema_file_exists():
    schema = PROJECT_ROOT / "gematria" / "schema.sql"
    assert schema.exists(), f"gematria/schema.sql introuvable ({schema})"
    content = schema.read_text()
    assert "CREATE TABLE IF NOT EXISTS gematria_index" in content


@pytest.fixture(scope="module")
def gematria_db():
    """Applique le schéma gematria sur la DB de test et renvoie l'URL."""
    TEST_DB = "postgresql://localhost/etz_chaim_test"
    conn = psycopg2.connect("postgresql://localhost/postgres")
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'etz_chaim_test'")
    if not cur.fetchone():
        cur.execute("CREATE DATABASE etz_chaim_test")
    cur.close()
    conn.close()

    conn = psycopg2.connect(TEST_DB)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    schema_sql = (PROJECT_ROOT / "gematria" / "schema.sql").read_text()
    cur.execute(schema_sql)
    cur.close()
    conn.close()

    yield TEST_DB


def test_gematria_index_table_exists_after_schema(gematria_db):
    """Après application de gematria/schema.sql, la table gematria_index existe."""
    conn = psycopg2.connect(gematria_db)
    cur = conn.cursor()
    cur.execute("SELECT to_regclass('gematria_index')")
    result = cur.fetchone()[0]
    cur.close()
    conn.close()
    assert result == "gematria_index", (
        f"Table gematria_index inaccessible: to_regclass={result}"
    )


def test_find_equivalences_no_relation_error(gematria_db):
    """find_equivalences ne doit plus échouer par 'relation does not exist'."""
    from gematria.engine import GematriaEngine

    engine = GematriaEngine(db_url=gematria_db)
    # Terme absent → liste vide, mais pas de ProgrammingError
    equivs = engine.find_equivalences("חסד", method="standard")
    assert equivs == []
