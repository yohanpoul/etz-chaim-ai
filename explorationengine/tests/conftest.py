"""Fixtures de test — Chesed (ExplorationEngine)."""

import subprocess
from pathlib import Path

import psycopg2
import pytest

from explorationengine.core import ExplorationEngine
from explorationengine.db import ExplorationEngineDB
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
    """Fresh ExplorationEngineDB, truncated between tests."""
    database = ExplorationEngineDB(TEST_DB_URL)
    yield database
    _truncate_via_pool()
    database.close()


@pytest.fixture
def engine():
    """ExplorationEngine sans connexions externes."""
    eng = ExplorationEngine(db_url=TEST_DB_URL)
    yield eng
    _truncate_via_pool()
    eng.db.close()


@pytest.fixture
def engine_with_knowledge():
    """ExplorationEngine avec domain_knowledge enrichi."""
    knowledge = {
        "neuroscience": "brain neurons synapses cortex attention memory plasticity layers hierarchy network",
        "machine_learning": "model training loss gradient attention layer transformer optimization flow pipeline",
        "kabbale": "sefirot tsimtsum tikkun shevirah hierarchy flow emanation levels stages",
        "biology": "cell organism evolution gene protein metabolism homeostasis adaptation cycle feedback",
        "physics": "energy entropy field symmetry conservation quantum wave flow equilibrium",
        "writing": "narrative structure voice rhythm clarity argument thesis revision hierarchy",
        "code": "function module abstraction recursion pattern interface refactoring architecture hierarchy flow",
    }
    eng = ExplorationEngine(db_url=TEST_DB_URL, domain_knowledge=knowledge)
    yield eng
    _truncate_via_pool()
    eng.db.close()


def _truncate(conn):
    with conn.cursor() as cur:
        cur.execute("TRUNCATE explorationengine_analogies CASCADE")
        cur.execute("TRUNCATE explorationengine_connections CASCADE")
        cur.execute("TRUNCATE explorationengine_explorations CASCADE")
    conn.commit()


def _truncate_via_pool():
    """Pool-based truncate wrapper for post-migration DB classes."""
    from pool import get_conn
    with get_conn() as conn:
        _truncate(conn)
