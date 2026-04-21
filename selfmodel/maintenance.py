"""Maintenance des predictions SelfModel — nettoyage de Da'at.

Audit F01/R6 : selfmodel_predictions a 5.2M rows (1578 MB = 74% de la DB),
mais seulement 215 (0.004%) ont ete verifiees. C'est du bruit qui noie
le signal. Ce module fournit deux operations :

1. verify_stale_predictions : verifier un batch de predictions anciennes
   en comparant le domain predit aux stats Hitbonenut actuelles.
2. archive_old_predictions : supprimer les predictions non verifiees
   au-dela d'une retention (30j par defaut).

Le hitkalelut est present : l'archivage PRESERVE les predictions verifiees
(correctes ou non) — seul le bruit non verifie est supprime.
Le signal (meme incorrect) reste pour la calibration.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import psycopg2.extras

if TYPE_CHECKING:
    import psycopg2.extensions

log = logging.getLogger("etz-daat-maintenance")


def verify_stale_predictions(
    conn: psycopg2.extensions.connection,
    domain_stats: dict[str, dict] | None = None,
    batch_size: int = 100,
) -> dict:
    """Verifier un batch de predictions non verifiees de plus de 7 jours.

    Compare chaque prediction au stats actuelles du domaine :
    - samael/satariel (faiblesse) : correct si avg toujours < 0.50
    - thagirion (declin) : correct si delta toujours < -0.02
    - gamchicoth (blocage) : correct si avg toujours < 0.50

    Args:
        conn: connexion psycopg2 (autocommit=True attendu).
        domain_stats: dict domain -> {"avg": float, "recent": float, "delta": float}.
                      Si None, les predictions sont retournees sans verification.
        batch_size: nombre max de predictions a traiter.

    Returns:
        dict avec verified, correct, incorrect, skipped (domain inconnu).
    """
    result = {
        "verified": 0,
        "correct": 0,
        "incorrect": 0,
        "skipped": 0,
    }

    # 1. Recuperer les predictions stale
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT id, domain, predicted_error_type, predicted_confidence
            FROM selfmodel_predictions
            WHERE was_correct IS NULL
              AND predicted_at < NOW() - INTERVAL '7 days'
            ORDER BY predicted_at ASC
            LIMIT %s
        """, (batch_size,))
        stale = cur.fetchall()

    if not stale:
        log.info("Maintenance: aucune prediction stale a verifier")
        return result

    if domain_stats is None:
        log.warning("Maintenance: pas de domain_stats — skip verification")
        result["skipped"] = len(stale)
        return result

    # Seuils alignes sur daemon.py _DAAT_WEAK_THRESHOLD
    weak_threshold = 0.50

    # 2. Verifier chaque prediction
    for pred in stale:
        domain = pred["domain"]
        error_type = pred["predicted_error_type"]

        if domain not in domain_stats:
            result["skipped"] += 1
            continue

        stats = domain_stats[domain]
        was_correct = False
        outcome = ""

        if error_type in ("samael", "satariel"):
            was_correct = stats["avg"] < weak_threshold
            outcome = (
                f"avg={stats['avg']:.3f}, "
                f"{'toujours faible' if was_correct else 'ameliore'}"
            )
        elif error_type == "thagirion":
            was_correct = stats["delta"] < -0.02
            outcome = (
                f"delta={stats['delta']:+.3f}, "
                f"{'declin confirme' if was_correct else 'stabilise'}"
            )
        elif error_type == "gamchicoth":
            was_correct = stats["avg"] < weak_threshold
            outcome = (
                f"avg={stats['avg']:.3f}, "
                f"{'bloque' if was_correct else 'debloque'}"
            )
        else:
            # Type inconnu — marquer comme incorrect par defaut
            was_correct = False
            outcome = f"type inconnu: {error_type}"

        with conn.cursor() as cur:
            cur.execute("""
                UPDATE selfmodel_predictions
                SET verified_at = NOW(), was_correct = %s, actual_outcome = %s
                WHERE id = %s
            """, (was_correct, outcome, pred["id"]))

        result["verified"] += 1
        if was_correct:
            result["correct"] += 1
        else:
            result["incorrect"] += 1

    log.info(
        "Maintenance verify: %d verified (%d correct, %d incorrect, %d skipped)",
        result["verified"], result["correct"], result["incorrect"], result["skipped"],
    )
    return result


def archive_old_predictions(
    conn: psycopg2.extensions.connection,
    retention_days: int = 30,
) -> dict:
    """Supprimer les predictions non verifiees au-dela de la retention.

    PRESERVE les predictions verifiees (was_correct IS NOT NULL) —
    elles servent a la calibration de Da'at. Seul le bruit non verifie
    est supprime.

    Args:
        conn: connexion psycopg2 (autocommit=True attendu).
        retention_days: nombre de jours avant archivage (defaut 30).

    Returns:
        dict avec deleted (nombre de rows supprimees).
    """
    with conn.cursor() as cur:
        cur.execute("""
            DELETE FROM selfmodel_predictions
            WHERE was_correct IS NULL
              AND predicted_at < NOW() - make_interval(days => %s)
        """, (retention_days,))
        deleted = cur.rowcount

    if deleted > 0:
        log.warning(
            "Maintenance archive: %d predictions non verifiees supprimees "
            "(retention=%d jours)",
            deleted, retention_days,
        )
    else:
        log.info("Maintenance archive: rien a supprimer (retention=%d jours)", retention_days)

    return {"deleted": deleted}
