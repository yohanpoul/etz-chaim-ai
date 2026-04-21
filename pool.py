"""pool.py — Connection pool centralisé pour Etz Chaim.

Un seul pool partagé par tout le projet (daemon, web, CLI).
Le pool sert aux connexions ad-hoc (daemon helpers, web queries).

Circuit breaker intégré : après N échecs consécutifs de connexion DB,
les appels sont court-circuités pendant un cooldown (pas de tentatives
inutiles qui cascadent). Retry avec backoff exponentiel sur getconn().
"""

from __future__ import annotations

import logging
import os
import threading
import time
from contextlib import contextmanager
from typing import Generator

import psycopg2
import psycopg2.extensions
from psycopg2.pool import ThreadedConnectionPool

log = logging.getLogger("etz-pool")

_pool: ThreadedConnectionPool | None = None
_lock = threading.Lock()

# ─── DB URL resolution (v0.2+) ───────────────────────────────

_DEFAULT_DB_URL = "postgresql://localhost/etz_chaim"


def _resolve_db_url() -> str:
    """Resolve DB URL from env with priority : ETZ_CHAIM_DB_URL > ETZ_CHAIM_DB > default.

    ETZ_CHAIM_DB is deprecated (v0.2.0) — emits DeprecationWarning if used alone.
    Will be removed in v0.3.0.
    """
    new = os.environ.get("ETZ_CHAIM_DB_URL")
    if new:
        return new
    legacy = os.environ.get("ETZ_CHAIM_DB")
    if legacy:
        import warnings
        warnings.warn(
            "ETZ_CHAIM_DB is deprecated since v0.2.0 ; use ETZ_CHAIM_DB_URL instead. "
            "Legacy name will be removed in v0.3.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return legacy
    return _DEFAULT_DB_URL

# ─── Circuit breaker ─────────────────────────────────────────

_CB_FAILURE_THRESHOLD = 5      # Ouvrir le circuit après N échecs consécutifs
_CB_COOLDOWN_SECONDS = 30      # Durée du circuit ouvert avant retry
_CB_MAX_RETRY = 3              # Tentatives avec backoff avant abandon
_CB_BACKOFF_BASE = 0.5         # Backoff : 0.5s, 1s, 2s

_cb_failures = 0
_cb_open_until = 0.0           # timestamp — circuit ouvert jusqu'à
_cb_lock = threading.Lock()


class CircuitOpenError(RuntimeError):
    """Le circuit breaker DB est ouvert — trop d'échecs consécutifs."""


def _cb_record_success():
    global _cb_failures, _cb_open_until
    with _cb_lock:
        _cb_failures = 0
        _cb_open_until = 0.0


def _cb_record_failure():
    global _cb_failures, _cb_open_until
    with _cb_lock:
        _cb_failures += 1
        if _cb_failures >= _CB_FAILURE_THRESHOLD:
            _cb_open_until = time.time() + _CB_COOLDOWN_SECONDS
            log.warning(
                "Circuit breaker DB OUVERT — %d échecs consécutifs, "
                "cooldown %ds",
                _cb_failures, _CB_COOLDOWN_SECONDS,
            )


def _cb_is_open() -> bool:
    global _cb_failures, _cb_open_until
    with _cb_lock:
        if _cb_open_until <= 0:
            return False
        if time.time() >= _cb_open_until:
            # Cooldown terminé → half-open (laisser passer un essai)
            _cb_open_until = 0.0
            _cb_failures = 0
            log.info("Circuit breaker DB half-open — tentative de reconnexion")
            return False
        return True


# ─── Pool ─────────────────────────────────────────────────────


def init_pool(
    db_url: str | None = None, minconn: int = 2, maxconn: int = 8,
) -> ThreadedConnectionPool:
    """Initialise le pool global. Idempotent — n'appeler qu'une fois.

    Garde anti-destruction (audit cycle 4, post-incident TRUNCATE PROD) :
    sous pytest, REFUSE toute URL qui ne pointe pas explicitement sur
    une DB de test (nom finissant par '_test' ou variable d'env
    ETZ_CHAIM_TEST_DB_OVERRIDE=1).

    Cause de l'incident : init_pool est idempotent. Si la prod l'a
    initialisé en premier, les tests qui appellent init_pool(test_url)
    obtiennent un no-op silencieux. Les TRUNCATE des conftest tombaient
    alors sur la PROD. La garde lève maintenant RuntimeError au lieu
    d'échouer silencieusement.
    """
    global _pool

    # Détection mode test : PYTEST_CURRENT_TEST est défini par pytest.
    in_pytest = "PYTEST_CURRENT_TEST" in os.environ or "pytest" in os.environ.get("_", "")

    with _lock:
        url = db_url or _resolve_db_url()

        # Garde : sous pytest, refuser une URL postgresql qui ne pointe
        # PAS sur une DB de test. Les URLs non-postgresql (mock://, etc.)
        # passent — elles ne peuvent pas TRUNCATE la prod de toute façon.
        if in_pytest and not os.environ.get("ETZ_CHAIM_TEST_DB_OVERRIDE"):
            if url.startswith("postgresql://") or url.startswith("postgres://"):
                db_name = url.rstrip("/").rsplit("/", 1)[-1].split("?")[0]
                if not (db_name.endswith("_test") or db_name == "test"):
                    raise RuntimeError(
                        f"init_pool refusée sous pytest : URL '{url}' ne pointe "
                        f"pas sur une DB de test (nom doit finir par '_test'). "
                        f"Utiliser ETZ_CHAIM_TEST_DB_OVERRIDE=1 pour forcer."
                    )

        # Garde additionnelle : si déjà initialisé sur une DB différente
        # sous pytest, refuser plutôt que retourner silencieusement le pool
        # (qui pointerait sur la mauvaise DB → TRUNCATE sur PROD).
        if _pool is not None:
            if in_pytest and db_url is not None:
                # Vérifier que le pool existant est compatible avec l'URL demandée
                # (en pratique : compare le dbname uniquement).
                existing = _pool._kwargs.get("dsn") if hasattr(_pool, "_kwargs") else None
                req_db = url.rstrip("/").rsplit("/", 1)[-1].split("?")[0]
                if existing and req_db not in existing:
                    raise RuntimeError(
                        f"Pool déjà initialisé avec une DB différente de '{req_db}'. "
                        f"Sous pytest c'est dangereux (risque TRUNCATE PROD). "
                        f"Réinitialiser via reset_pool()."
                    )
            return _pool

        _pool = ThreadedConnectionPool(minconn, maxconn, url)
        return _pool


def reset_pool() -> None:
    """Ferme et réinitialise le pool global (utile pour les tests).

    Sécurité : utilisable hors et dans pytest. Appelle closeall() pour
    fermer les connexions actives avant d'oublier la référence.
    """
    global _pool
    with _lock:
        if _pool is not None:
            try:
                _pool.closeall()
            except Exception:
                pass
            _pool = None


def get_pool() -> ThreadedConnectionPool:
    """Retourne le pool global. Lève RuntimeError si non initialisé."""
    if _pool is None:
        raise RuntimeError("Pool non initialisé — appeler init_pool() d'abord")
    return _pool


@contextmanager
def get_conn(
    autocommit: bool = True,
) -> Generator[psycopg2.extensions.connection, None, None]:
    """Emprunte une connexion au pool, la rend automatiquement.

    Intègre le circuit breaker : si trop d'échecs DB consécutifs,
    lève CircuitOpenError au lieu de tenter une connexion vouée à l'échec.
    Retry avec backoff exponentiel sur les erreurs transitoires.

    Usage:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(...)
    """
    if _cb_is_open():
        raise CircuitOpenError(
            f"Circuit breaker DB ouvert — {_cb_failures} échecs consécutifs, "
            f"réessayer dans {max(0, int(_cb_open_until - time.time()))}s"
        )

    pool = get_pool()
    last_error = None

    for attempt in range(_CB_MAX_RETRY):
        conn = None
        try:
            conn = pool.getconn()
            # Vérifier que la connexion est vivante
            if conn.closed:
                pool.putconn(conn, close=True)
                conn = pool.getconn()
            conn.autocommit = autocommit
            _cb_record_success()
            try:
                yield conn
            finally:
                pool.putconn(conn)
            return
        except psycopg2.OperationalError as e:
            last_error = e
            _cb_record_failure()
            if conn is not None:
                try:
                    pool.putconn(conn, close=True)
                except Exception as _exc:

                    import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
            if attempt < _CB_MAX_RETRY - 1:
                backoff = _CB_BACKOFF_BASE * (2 ** attempt)
                log.warning(
                    "DB connexion échouée (tentative %d/%d): %s — backoff %.1fs",
                    attempt + 1, _CB_MAX_RETRY, e, backoff,
                )
                time.sleep(backoff)

    raise last_error  # type: ignore[misc]


def close_pool() -> None:
    """Ferme toutes les connexions du pool."""
    global _pool
    with _lock:
        if _pool is not None:
            _pool.closeall()
            _pool = None


# ─── Advisory locks ─────────────────────────────────────────
# PostgreSQL advisory locks pour coordonner les threads du daemon.
# Chaque lock_id identifie une ressource partagée.
# Session-level locks : libérés explicitement ou à la déconnexion.

LOCK_SELFMODEL_MAINTENANCE = 1001   # archive/verify selfmodel_predictions
LOCK_GC_YESOD = 1002                # GC epistememory + selfmodel_predictions
LOCK_LOG_RETENTION = 1003            # purge des tables de log


@contextmanager
def advisory_lock(
    conn: psycopg2.extensions.connection, lock_id: int,
) -> Generator[None, None, None]:
    """PostgreSQL advisory lock pour la coordination des tâches du daemon.

    Utilise pg_advisory_lock (bloquant) — le thread attend si un autre
    thread tient déjà le verrou. Libéré dans le finally.

    Args:
        conn: connexion psycopg2 (doit être en autocommit ou hors transaction).
        lock_id: identifiant unique du verrou (voir LOCK_* constants).
    """
    with conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_lock(%s)", (lock_id,))
    try:
        yield
    finally:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_unlock(%s)", (lock_id,))


@contextmanager
def try_advisory_lock(
    conn: psycopg2.extensions.connection, lock_id: int,
) -> Generator[bool, None, None]:
    """PostgreSQL advisory lock non-bloquant (try).

    Utilise pg_try_advisory_lock : retourne immédiatement au lieu de bloquer.
    Yield True si le verrou est acquis, False sinon.
    Le daemon peut ainsi sauter une tâche déjà en cours plutôt que deadlock.

    Usage:
        with try_advisory_lock(conn, LOCK_GC_YESOD) as acquired:
            if not acquired:
                log.info("GC déjà en cours, skip")
                return
            # ... critical section ...

    Args:
        conn: connexion psycopg2 (autocommit attendu).
        lock_id: identifiant unique du verrou (voir LOCK_* constants).
    """
    with conn.cursor() as cur:
        cur.execute("SELECT pg_try_advisory_lock(%s)", (lock_id,))
        acquired = cur.fetchone()[0]
    try:
        yield acquired
    finally:
        if acquired:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_unlock(%s)", (lock_id,))
