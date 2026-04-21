"""Fixtures de test — Sefirat haOmer (calibration)."""

import subprocess
from pathlib import Path

import psycopg2
import pytest

from omer.core import OmerManager
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
        "omer/schema.sql",
    ]:
        subprocess.run(
            [require_psql(), "-d", "etz_chaim_test",
             "-f", schema],
            cwd=PROJECT_ROOT, check=True, capture_output=True,
        )


@pytest.fixture
def omer():
    """Fresh OmerManager, truncated between tests."""
    om = OmerManager(db_url=TEST_DB_URL)
    yield om
    _truncate_all(TEST_DB_URL)


def _truncate_all(db_url: str):
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("TRUNCATE failuretoinsight_insights CASCADE")
        cur.execute("TRUNCATE failuretoinsight_analyses CASCADE")
        cur.execute("TRUNCATE omer_history CASCADE")
    conn.close()
