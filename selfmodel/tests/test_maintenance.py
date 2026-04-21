"""Tests maintenance predictions — audit F01/R6."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import psycopg2
import psycopg2.extras
import pytest

from selfmodel.maintenance import archive_old_predictions, verify_stale_predictions

TEST_DB_URL = "postgresql://localhost/etz_chaim_test"


@pytest.fixture
def conn():
    """Connexion de test avec autocommit."""
    c = psycopg2.connect(TEST_DB_URL)
    c.autocommit = True
    yield c
    # Cleanup
    with c.cursor() as cur:
        cur.execute("TRUNCATE selfmodel_predictions CASCADE")
    c.close()


def _insert_prediction(
    conn,
    domain: str = "test",
    error_type: str = "samael",
    days_ago: int = 10,
    was_correct: bool | None = None,
) -> UUID:
    """Helper : inserer une prediction avec un age specifique."""
    predicted_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            INSERT INTO selfmodel_predictions
            (prediction, domain, predicted_error_type, predicted_confidence,
             predicted_at, was_correct)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            f"Test prediction for {domain}",
            domain,
            error_type,
            0.7,
            predicted_at,
            was_correct,
        ))
        return cur.fetchone()["id"]


class TestVerifyStale:
    """verify_stale_predictions — verification batch des predictions anciennes."""

    def test_verify_correct_prediction(self, conn):
        """Prediction samael pour domaine faible → was_correct=True."""
        pred_id = _insert_prediction(conn, domain="chimie", error_type="samael", days_ago=10)
        domain_stats = {"chimie": {"avg": 0.35, "recent": 0.30, "delta": -0.05}}

        result = verify_stale_predictions(conn, domain_stats=domain_stats, batch_size=10)

        assert result["verified"] == 1
        assert result["correct"] == 1
        assert result["incorrect"] == 0

        # Verifier en DB
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT was_correct, verified_at FROM selfmodel_predictions WHERE id = %s", (pred_id,))
            row = cur.fetchone()
            assert row["was_correct"] is True
            assert row["verified_at"] is not None

    def test_verify_incorrect_prediction(self, conn):
        """Prediction samael pour domaine ameliore → was_correct=False."""
        _insert_prediction(conn, domain="physique", error_type="samael", days_ago=10)
        domain_stats = {"physique": {"avg": 0.75, "recent": 0.80, "delta": 0.10}}

        result = verify_stale_predictions(conn, domain_stats=domain_stats, batch_size=10)

        assert result["verified"] == 1
        assert result["correct"] == 0
        assert result["incorrect"] == 1

    def test_verify_thagirion_correct(self, conn):
        """Prediction thagirion (declin) pour domaine en declin → correct."""
        _insert_prediction(conn, domain="math", error_type="thagirion", days_ago=10)
        domain_stats = {"math": {"avg": 0.60, "recent": 0.50, "delta": -0.10}}

        result = verify_stale_predictions(conn, domain_stats=domain_stats, batch_size=10)

        assert result["verified"] == 1
        assert result["correct"] == 1

    def test_verify_thagirion_incorrect(self, conn):
        """Prediction thagirion pour domaine stabilise → incorrect."""
        _insert_prediction(conn, domain="math", error_type="thagirion", days_ago=10)
        domain_stats = {"math": {"avg": 0.60, "recent": 0.60, "delta": 0.00}}

        result = verify_stale_predictions(conn, domain_stats=domain_stats, batch_size=10)

        assert result["verified"] == 1
        assert result["incorrect"] == 1

    def test_skip_unknown_domain(self, conn):
        """Domaine absent des stats → skip."""
        _insert_prediction(conn, domain="inconnu", error_type="samael", days_ago=10)
        domain_stats = {"chimie": {"avg": 0.35, "recent": 0.30, "delta": -0.05}}

        result = verify_stale_predictions(conn, domain_stats=domain_stats, batch_size=10)

        assert result["verified"] == 0
        assert result["skipped"] == 1

    def test_skip_recent_predictions(self, conn):
        """Predictions de moins de 7 jours ne sont pas touchees."""
        _insert_prediction(conn, domain="chimie", error_type="samael", days_ago=3)
        domain_stats = {"chimie": {"avg": 0.35, "recent": 0.30, "delta": -0.05}}

        result = verify_stale_predictions(conn, domain_stats=domain_stats, batch_size=10)

        assert result["verified"] == 0
        assert result["skipped"] == 0

    def test_skip_already_verified(self, conn):
        """Predictions deja verifiees ne sont pas re-verifiees."""
        _insert_prediction(conn, domain="chimie", error_type="samael", days_ago=10, was_correct=True)
        domain_stats = {"chimie": {"avg": 0.35, "recent": 0.30, "delta": -0.05}}

        result = verify_stale_predictions(conn, domain_stats=domain_stats, batch_size=10)

        assert result["verified"] == 0

    def test_no_domain_stats_skips_all(self, conn):
        """Sans domain_stats, tout est skip."""
        _insert_prediction(conn, domain="chimie", error_type="samael", days_ago=10)

        result = verify_stale_predictions(conn, domain_stats=None, batch_size=10)

        assert result["skipped"] == 1

    def test_batch_size_respected(self, conn):
        """Le batch_size limite le nombre de predictions traitees."""
        for i in range(5):
            _insert_prediction(conn, domain="chimie", error_type="samael", days_ago=10 + i)
        domain_stats = {"chimie": {"avg": 0.35, "recent": 0.30, "delta": -0.05}}

        result = verify_stale_predictions(conn, domain_stats=domain_stats, batch_size=2)

        assert result["verified"] == 2

    def test_empty_table(self, conn):
        """Table vide → rien a faire."""
        result = verify_stale_predictions(conn, domain_stats={"x": {"avg": 0.5, "recent": 0.5, "delta": 0.0}})

        assert result["verified"] == 0
        assert result["skipped"] == 0


class TestArchiveOld:
    """archive_old_predictions — suppression des predictions non verifiees."""

    def test_archive_old_unverified(self, conn):
        """Predictions non verifiees >30j sont supprimees."""
        _insert_prediction(conn, domain="chimie", days_ago=45)

        result = archive_old_predictions(conn, retention_days=30)

        assert result["deleted"] == 1
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM selfmodel_predictions")
            assert cur.fetchone()[0] == 0

    def test_preserve_verified(self, conn):
        """Predictions verifiees NE SONT PAS supprimees, meme anciennes."""
        _insert_prediction(conn, domain="chimie", days_ago=45, was_correct=True)
        _insert_prediction(conn, domain="chimie", days_ago=45, was_correct=False)

        result = archive_old_predictions(conn, retention_days=30)

        assert result["deleted"] == 0
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM selfmodel_predictions")
            assert cur.fetchone()[0] == 2

    def test_preserve_recent_unverified(self, conn):
        """Predictions non verifiees recentes ne sont pas supprimees."""
        _insert_prediction(conn, domain="chimie", days_ago=10)

        result = archive_old_predictions(conn, retention_days=30)

        assert result["deleted"] == 0

    def test_mixed_scenario(self, conn):
        """Mix de vieilles/recentes, verifiees/non verifiees."""
        # Vieux non verifie → supprime
        _insert_prediction(conn, domain="a", days_ago=45)
        # Vieux verifie → garde
        _insert_prediction(conn, domain="b", days_ago=45, was_correct=True)
        # Recent non verifie → garde
        _insert_prediction(conn, domain="c", days_ago=10)
        # Recent verifie → garde
        _insert_prediction(conn, domain="d", days_ago=10, was_correct=False)

        result = archive_old_predictions(conn, retention_days=30)

        assert result["deleted"] == 1
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM selfmodel_predictions")
            assert cur.fetchone()[0] == 3

    def test_custom_retention(self, conn):
        """retention_days personnalise."""
        _insert_prediction(conn, domain="chimie", days_ago=10)

        result = archive_old_predictions(conn, retention_days=7)

        assert result["deleted"] == 1

    def test_nothing_to_delete(self, conn):
        """Table vide → 0 deleted."""
        result = archive_old_predictions(conn, retention_days=30)

        assert result["deleted"] == 0
