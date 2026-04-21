"""Fixtures de test — Da'at (SelfModel)."""

import subprocess
from pathlib import Path

import psycopg2
import pytest

from selfmodel.core import SelfModel
from selfmodel.db import SelfModelDB
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
        "masakh/schema.sql",
    ]:
        subprocess.run(
            [require_psql(), "-d", "etz_chaim_test",
             "-f", schema],
            cwd=PROJECT_ROOT, check=True, capture_output=True,
        )

    # Pool-backed modules (SelfModelDB etc.) require init on the test DB.
    from pool import init_pool
    init_pool(TEST_DB_URL)


@pytest.fixture
def db():
    """Fresh SelfModelDB, truncated between tests."""
    database = SelfModelDB(TEST_DB_URL)
    yield database
    _truncate_via_pool()
    database.close()


@pytest.fixture
def model():
    """SelfModel sans connexions externes — Da'at nu."""
    m = SelfModel(db_url=TEST_DB_URL)
    yield m
    _truncate_via_pool()
    m.db.close()


@pytest.fixture
def model_with_state(model):
    """SelfModel with a pre-captured state."""
    model.capture_state()
    return model


def _truncate_via_pool():
    """Clean state between tests via the shared pool (post-migration)."""
    from pool import get_conn
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("TRUNCATE selfmodel_evolution CASCADE")
        cur.execute("TRUNCATE selfmodel_biases CASCADE")
        cur.execute("TRUNCATE selfmodel_predictions CASCADE")
        cur.execute("TRUNCATE selfmodel_states CASCADE")
