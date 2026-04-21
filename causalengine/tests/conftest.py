"""Fixtures de test — Binah (CausalEngine)."""

import subprocess
from pathlib import Path

import psycopg2
import pytest

from causalengine.core import CausalEngine
from causalengine.db import CausalDB
from tests._psql import require_psql

TEST_DB_URL = "postgresql://localhost/etz_chaim_test"
PROJECT_ROOT = str(Path(__file__).resolve().parents[2])


@pytest.fixture(scope="session", autouse=True)
def apply_schemas():
    """Apply all schemas once."""
    conn = psycopg2.connect("postgresql://localhost/postgres")
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'etz_chaim_test'")
    if not cur.fetchone():
        cur.execute("CREATE DATABASE etz_chaim_test")
    cur.close()
    conn.close()

    conn = psycopg2.connect(TEST_DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    cur.close()
    conn.close()

    for schema in [
        "epistememory/schema.sql",
        "selfmap/schema.sql",
        "intentkeeper/schema.sql",
        "failuretoinsight/schema.sql",
        "dissensuengine/schema.sql",
        "autojudge/schema.sql",
        "explorationengine/schema.sql",
        "selfmodel/schema.sql",
        "causalengine/schema.sql",
        "masakh/schema.sql",
    ]:
        subprocess.run(
            [require_psql(), "-d", "etz_chaim_test",
             "-f", schema],
            cwd=PROJECT_ROOT, check=True, capture_output=True,
        )

    # Pool init for modules that borrow from the shared pool
    from pool import init_pool
    init_pool(TEST_DB_URL)


@pytest.fixture
def db():
    """Fresh CausalDB, truncated between tests."""
    database = CausalDB(TEST_DB_URL)
    yield database
    _truncate_via_pool()
    database.close()


@pytest.fixture
def engine():
    """CausalEngine sans connexions externes — Binah nue."""
    eng = CausalEngine(db_url=TEST_DB_URL)
    yield eng
    _truncate_via_pool()
    eng.db.close()


@pytest.fixture
def engine_strict():
    """CausalEngine en mode strict."""
    eng = CausalEngine(db_url=TEST_DB_URL, language_strictness="strict")
    yield eng
    _truncate_via_pool()
    eng.db.close()


@pytest.fixture
def engine_permissive():
    """CausalEngine en mode permissif."""
    eng = CausalEngine(
        db_url=TEST_DB_URL,
        language_strictness="permissive",
        persist_all_dags=False,
    )
    yield eng
    _truncate_via_pool()
    eng.db.close()


def _truncate(conn):
    with conn.cursor() as cur:
        cur.execute("TRUNCATE causal_confounders CASCADE")
        cur.execute("TRUNCATE causal_claims CASCADE")
        cur.execute("TRUNCATE causal_graphs CASCADE")
    conn.commit()


def _truncate_via_pool():
    """Pool-based truncate wrapper for post-migration DB classes."""
    from pool import get_conn
    with get_conn() as conn:
        _truncate(conn)
