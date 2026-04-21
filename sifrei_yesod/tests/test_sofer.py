"""Tests du pipeline Sofer (ingestion YAML → PostgreSQL)."""

import yaml
import pytest
import psycopg2.extras

from .conftest import TEST_DB_URL, FIXTURE_PEREK_YAML


def test_ingest_perek(seeded_db):
    """L'ingestion d'un perek crée les entrées dans toutes les tables."""
    report = seeded_db
    assert not report.errors, f"Erreurs: {report.errors}"
    assert report.assertions_upserted == 2
    assert report.relations_upserted == 1
    assert report.principes_upserted == 1
    assert report.concepts_created >= 2  # test_concept_a, test_concept_b (+ c)


def test_idempotence(sofer, fixture_yaml, seeded_db):
    """Ingérer 2 fois le même fichier ne crée pas de doublons."""
    # First ingestion happened in seeded_db
    # Second ingestion — should be skipped (same hash)
    report2 = sofer.ingest_perek(fixture_yaml)
    assert report2.skipped

    # Verify counts are still the same
    conn = psycopg2.connect(TEST_DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM sifrei_yesod_assertions WHERE assertion_id LIKE 'EC-K99-%'")
    assert cur.fetchone()[0] == 2
    cur.close()
    conn.close()


def test_change_detection(sofer, fixture_yaml, seeded_db):
    """Modifier le YAML déclenche une ré-ingestion."""
    # Modify the file
    data = yaml.safe_load(FIXTURE_PEREK_YAML)
    data["assertions"][0]["assertion"] = "Assertion modifiée pour test."
    fixture_yaml.write_text(yaml.dump(data, allow_unicode=True))

    report = sofer.ingest_perek(fixture_yaml)
    assert not report.skipped
    assert report.assertions_upserted == 2

    # Check updated content
    conn = psycopg2.connect(TEST_DB_URL)
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT assertion FROM sifrei_yesod_assertions WHERE assertion_id = 'EC-K99-001'")
    row = cur.fetchone()
    assert "modifiée" in row["assertion"]
    cur.close()
    conn.close()


def test_concept_auto_creation(seeded_db):
    """Les concepts sont auto-créés lors de l'ingestion."""
    conn = psycopg2.connect(TEST_DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT concept_id FROM sifrei_yesod_concepts ORDER BY concept_id")
    concepts = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()

    assert "test_concept_a" in concepts
    assert "test_concept_b" in concepts
    assert "test_concept_c" in concepts
