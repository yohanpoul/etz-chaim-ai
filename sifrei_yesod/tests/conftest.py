"""Fixtures de test pour Sifrei Yesod."""

import subprocess
from pathlib import Path

import psycopg2
import pytest

from tests._psql import require_psql

TEST_DB_URL = "postgresql://localhost/etz_chaim_test"
PROJECT_ROOT = Path(__file__).parent.parent.parent

FIXTURE_PEREK_YAML = """
meta:
  sefer: etz_chaim
  shaar: 1
  shaar_name_he: "שער הכללים"
  perek: 99
  source_edition: "TEST"
  transposed_by: "TEST"
  version: 1
  strates: ["base"]

assertions:
  - id: "EC-K99-001"
    source_he: "טקסט לבדיקה"
    source_ref: "Test 1:1"
    assertion: "Assertion de test pour validation du pipeline."
    type: axiome_explicite
    concepts:
      - {id: test_concept_a, role: test}
      - {id: test_concept_b, role: test}
    mapping:
      modules: []
      tables: []
      partzufim: []
      relevance: "Test uniquement"

  - id: "EC-K99-002"
    source_he: "טקסט שני"
    source_ref: "Test 1:2"
    assertion: "Deuxieme assertion pour tester les relations."
    type: déduction_logique
    concepts:
      - {id: test_concept_a, role: source}
      - {id: test_concept_c, role: résultat}

relations:
  - id: "REL-K99-001"
    type: causal
    from: test_concept_a
    to: test_concept_b
    nature: "Relation de test"
    assertions_source: ["EC-K99-001"]

principes_generatifs:
  - id: "PG-K99-001"
    nom: "Principe de test"
    source_assertions: ["EC-K99-001"]
    formalisation: "Si A alors B — principe de test."
    applications_ia: ["Test d'application"]
    questions_ouvertes: ["Question de test ?"]
"""


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create test database and apply sifrei_yesod schema."""
    conn = psycopg2.connect("postgresql://localhost/postgres")
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'etz_chaim_test'")
    if not cur.fetchone():
        cur.execute("CREATE DATABASE etz_chaim_test")
    cur.close()
    conn.close()

    # Setup extensions and drop old tables for schema refresh
    conn = psycopg2.connect(TEST_DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    except Exception:
        conn.rollback()
    # Drop existing sifrei_yesod tables to apply fresh schema
    cur.execute("""
        DROP TABLE IF EXISTS
            sifrei_yesod_cross_refs,
            sifrei_yesod_principes,
            sifrei_yesod_relations,
            sifrei_yesod_assertions,
            sifrei_yesod_perakim,
            sifrei_yesod_shaarim,
            sifrei_yesod_heikhalot,
            sifrei_yesod_concepts,
            sifrei_yesod_sefarim
        CASCADE
    """)
    cur.close()
    conn.close()

    # Apply schema
    subprocess.run(
        [require_psql(), "-d", "etz_chaim_test",
         "-f", "sifrei_yesod/schema.sql"],
        cwd=str(PROJECT_ROOT),
        check=True,
        capture_output=True,
    )


@pytest.fixture
def db_conn():
    """Fresh PostgreSQL connection, cleaned between tests."""
    conn = psycopg2.connect(TEST_DB_URL)
    conn.autocommit = False
    yield conn

    # Truncate all sifrei_yesod tables
    conn.rollback()
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("""
        TRUNCATE sifrei_yesod_cross_refs,
                 sifrei_yesod_principes,
                 sifrei_yesod_relations,
                 sifrei_yesod_assertions,
                 sifrei_yesod_perakim,
                 sifrei_yesod_shaarim,
                 sifrei_yesod_heikhalot,
                 sifrei_yesod_concepts,
                 sifrei_yesod_sefarim
        CASCADE
    """)
    cur.close()
    conn.close()


@pytest.fixture
def sofer(db_conn):
    """Sofer instance pointed at test DB."""
    from sifrei_yesod.pipeline.sofer import Sofer
    s = Sofer(db_url=TEST_DB_URL)
    yield s
    s.close()


@pytest.fixture
def query(db_conn):
    """SifreiYesodQuery instance pointed at test DB."""
    from sifrei_yesod.api.query import SifreiYesodQuery
    q = SifreiYesodQuery(db_url=TEST_DB_URL)
    yield q
    q.close()


@pytest.fixture
def fixture_yaml(tmp_path) -> Path:
    """Write the fixture perek YAML to a temp file."""
    f = tmp_path / "perek_99.yaml"
    f.write_text(FIXTURE_PEREK_YAML)
    return f


@pytest.fixture
def seeded_db(sofer, fixture_yaml):
    """Seed the test DB with meta + fixture perek."""
    # Ensure sefer exists
    sofer.ensure_sefer({
        "sefer_id": "etz_chaim",
        "titre_he": "עץ חיים",
        "titre_fr": "L'Arbre de Vie",
        "auteur": "Rabbi Haim Vital",
        "edition_base": "TEST",
        "structure": {"type": "shaarim_perakim", "nombre_shaarim": 50},
        "description": "Test",
    })
    # Ensure sha'ar exists
    sofer.ensure_shaar({
        "sefer_id": "etz_chaim",
        "shaar_number": 1,
        "shaar_name_he": "שער הכללים",
        "shaar_name_fr": "La Porte des Principes Généraux",
        "nombre_perakim": 1,
    })
    # Ingest fixture perek
    report = sofer.ingest_perek(fixture_yaml)
    return report
