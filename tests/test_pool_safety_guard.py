"""Garde anti-destruction du pool — tests régression.

Suite à un incident où des TRUNCATE de tests sont tombés sur la DB PROD
(causal_claims vidée à cause d'init_pool idempotent), pool.init_pool
refuse maintenant toute URL non-test pendant un run pytest.

Ces tests vérifient que :
  - init_pool sous pytest avec URL prod → RuntimeError
  - init_pool sous pytest avec URL '_test' → autorisé
  - init_pool en mode override (ETZ_CHAIM_TEST_DB_OVERRIDE=1) → autorisé
  - reset_pool() ferme proprement le pool
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def reset_pool_state():
    """Reset le pool global avant et après chaque test pour isolation."""
    import pool
    pool.reset_pool()
    # Le test fixture pytest définit PYTEST_CURRENT_TEST automatiquement.
    yield
    pool.reset_pool()
    os.environ.pop("ETZ_CHAIM_TEST_DB_OVERRIDE", None)


class TestPoolGuard:
    def test_refuses_prod_url_under_pytest(self):
        """init_pool('postgresql:///etz_chaim') sous pytest → RuntimeError."""
        from pool import init_pool

        with pytest.raises(RuntimeError, match="ne pointe pas sur une DB de test"):
            init_pool("postgresql://localhost/etz_chaim")

    def test_refuses_prod_when_default_url(self):
        """init_pool() sans arg sous pytest, sans ETZ_CHAIM_DB pointant vers _test, → RuntimeError."""
        from pool import init_pool

        # Cleanup env to ensure we hit the default
        old = os.environ.pop("ETZ_CHAIM_DB", None)
        try:
            with pytest.raises(RuntimeError, match="ne pointe pas sur une DB de test"):
                init_pool()
        finally:
            if old is not None:
                os.environ["ETZ_CHAIM_DB"] = old

    def test_accepts_test_url(self):
        """init_pool('postgresql:///etz_chaim_test') → autorisé."""
        from pool import init_pool

        # Note : ce test essaie de se connecter à etz_chaim_test ; si
        # la DB n'existe pas, on accepte la psycopg2.OperationalError.
        try:
            init_pool("postgresql://localhost/etz_chaim_test")
        except RuntimeError as e:
            if "ne pointe pas sur une DB de test" in str(e):
                pytest.fail(f"Garde a refusé URL test : {e}")
            # Autre RuntimeError (connexion impossible, etc.) → on accepte
        except Exception:
            pass

    def test_accepts_arbitrary_url_with_override(self):
        """ETZ_CHAIM_TEST_DB_OVERRIDE=1 → garde désactivée."""
        from pool import init_pool

        os.environ["ETZ_CHAIM_TEST_DB_OVERRIDE"] = "1"
        # Avec override, l'URL prod n'est plus refusée par la garde
        # (peut quand même échouer à se connecter — mais pas via la garde).
        try:
            init_pool("postgresql://localhost/etz_chaim")
        except RuntimeError as e:
            if "ne pointe pas sur une DB de test" in str(e):
                pytest.fail("Override n'a pas désactivé la garde")
        except Exception:
            pass

    def test_reset_pool_closes_existing(self):
        """reset_pool() ferme et oublie le pool global."""
        import pool
        from pool import init_pool, reset_pool

        # Init test DB (peut échouer si DB absente, c'est OK)
        try:
            init_pool("postgresql://localhost/etz_chaim_test")
        except Exception:
            return  # DB test absente, on skip

        assert pool._pool is not None
        reset_pool()
        assert pool._pool is None
