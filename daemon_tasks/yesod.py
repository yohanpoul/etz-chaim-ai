"""daemon_tasks/yesod.py — Yesod tasks: memory stats, maturation, GC, retention, sifrei.

Extracted from daemon.py for modularity.
"""
from __future__ import annotations

import logging
import os

DB_URL = (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim"))
log = logging.getLogger("etz-daemon")


def task_memory_stats() -> dict:
    """Stats mémoire rapides (pas besoin de l'Arbre complet)."""
    from pool import get_conn

    report = {"task": "memory_stats"}
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        COUNT(*) AS total,
                        COUNT(*) FILTER (WHERE epistemic_status != 'deprecated') AS active,
                        AVG(confidence) AS avg_conf,
                        COUNT(DISTINCT domain) AS domains,
                        COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS with_emb
                    FROM epistememory
                """)
                total, active, avg_conf, domains, with_emb = cur.fetchone()
                report.update({
                    "total_entries": total,
                    "active_entries": active,
                    "avg_confidence": round(avg_conf, 2) if avg_conf else 0,
                    "domains": domains,
                    "with_embeddings": with_emb,
                })

                cur.execute("SELECT COUNT(*) FROM open_contradictions")
                report["open_contradictions"] = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM near_expiration")
                report["near_expiration"] = cur.fetchone()[0]
    except Exception as e:
        report["error"] = str(e)

    return report


def task_yesod_mature(tree: dict) -> dict:
    """Yesod maturation — promotion automatique des mémoires mûres.

    Critères :
      hypothesis → verified_once : confiance >= 0.6 ET access_count >= 2
      verified_once → fact : confiance >= 0.8 ET ancienneté > 24h ET non contradictée
    Max 20 promotions par niveau par cycle.
    """
    report: dict = {"task": "yesod_mature"}
    yesod = tree.get("yesod")
    if not yesod:
        report["error"] = "EpisteMemory non disponible"
        return report

    try:
        promoted = yesod.mature(max_per_level=50)
        report["to_verified_once"] = len(promoted["to_verified_once"])
        report["to_fact"] = len(promoted["to_fact"])
        report["total_promoted"] = report["to_verified_once"] + report["to_fact"]
        log.info(
            "Yesod mature: %d→verified_once, %d→fact",
            report["to_verified_once"], report["to_fact"],
        )
    except Exception as e:
        log.error("Yesod mature error: %s", e)
        report["error"] = str(e)

    return report


def task_log_retention(tree: dict) -> dict:
    """Gevurah — Purge des logs anciens pour éviter la croissance sans limite.

    גְּבוּרָה — La rigueur qui émonde.
    Trois tables à INSERT sans DELETE grandissent de ~525K rows/an chacune.
    Politique de rétention :
      - context_monitor_log : 30 jours
      - masakh_log          : 30 jours
      - hitbonenut_questions : 90 jours (plus précieuses pour l'analyse)
    """
    from pool import get_conn, try_advisory_lock, LOCK_LOG_RETENTION

    retention: dict[str, tuple[str, int]] = {
        "context_monitor_log": ("created_at", 30),
        "masakh_log": ("created_at", 30),
        "hitbonenut_questions": ("created_at", 90),
    }
    total_deleted = 0
    report: dict = {"task": "log_retention", "purged": 0, "details": {}}
    try:
        with get_conn() as conn:
            with try_advisory_lock(conn, LOCK_LOG_RETENTION) as acquired:
                if not acquired:
                    log.info("Log retention: advisory lock déjà tenu, skip")
                    return report
                for table, (col, days) in retention.items():
                    with conn.cursor() as cur:
                        cur.execute(
                            f"DELETE FROM {table} WHERE {col} < NOW() - make_interval(days => %s)",
                            (days,),
                        )
                        count = cur.rowcount
                        if count > 0:
                            log.warning(
                                "Retention: purged %d rows from %s (>%d days)",
                                count, table, days,
                            )
                        report["details"][table] = count
                        total_deleted += count
                    conn.commit()

                # ── Purge agressive : selfmodel_predictions non vérifiées > 7j ──
                # Ancienne rétention : 30j implicite (jamais purgé).
                # Les prédictions non vérifiées au bout de 7j n'ont plus de valeur :
                # le contexte a changé, les vérifier serait anachronique.
                # Les prédictions VÉRIFIÉES sont conservées (valeur analytique).
                with conn.cursor() as cur:
                    cur.execute("""
                        DELETE FROM selfmodel_predictions
                        WHERE was_correct IS NULL
                          AND predicted_at < NOW() - INTERVAL '7 days'
                    """)
                    pred_purged = cur.rowcount
                    if pred_purged > 0:
                        log.warning(
                            "Retention: purged %d unverified predictions "
                            "from selfmodel_predictions (>7 days)",
                            pred_purged,
                        )
                    report["details"]["selfmodel_predictions_unverified"] = pred_purged
                    total_deleted += pred_purged
                conn.commit()

                # ── TTL sur candidate_insights rejetés > 30j ──
                # 80% des entrées sont rejected — les garder indéfiniment
                # fait grossir la table sans valeur. Les acceptés restent.
                with conn.cursor() as cur:
                    cur.execute("""
                        DELETE FROM candidate_insights
                        WHERE status = 'rejected'
                          AND created_at < NOW() - INTERVAL '30 days'
                    """)
                    ci_purged = cur.rowcount
                    if ci_purged > 0:
                        log.warning(
                            "Retention: purged %d rejected insights "
                            "from candidate_insights (>30 days)",
                            ci_purged,
                        )
                    report["details"]["candidate_insights_rejected"] = ci_purged
                    total_deleted += ci_purged
                conn.commit()
    except Exception as e:
        report["error"] = str(e)
        log.error("Log retention error: %s", e)
    report["purged"] = total_deleted
    return report


def task_gc(tree: dict) -> dict:
    """Gevurah-de-Yesod — Garbage collection des entrées périmées + données mortes.

    גְּבוּרָה שֶׁבְּיְסוֹד — La rigueur dans la fondation.
    Trois niveaux de nettoyage :
    1. Entries expirées (TTL dépassé)
    2. Entries mortes (access_count=0, >30 jours, pas des faits)
    3. Prédictions orphelines (was_correct=NULL, >30 jours)
    """
    report = {"task": "gc", "expired": 0, "deprecated": 0, "dead_entries": 0, "dead_predictions": 0}
    yesod = tree.get("yesod")
    if not yesod:
        report["error"] = "EpisteMemory non disponible"
        return report

    try:
        gc_result = yesod.gc()
        report["expired"] = gc_result.expired_count
        report["deprecated"] = gc_result.deprecated_count
        log.info(
            "GC Yesod: %d expirées, %d deprecated total",
            gc_result.expired_count, gc_result.deprecated_count,
        )
    except Exception as e:
        report["error"] = str(e)
        log.error("GC error: %s", e)

    # ── Données mortes : entries jamais consultées >30j ──
    try:
        from pool import get_conn, try_advisory_lock, LOCK_GC_YESOD

        with get_conn() as conn:
            with try_advisory_lock(conn, LOCK_GC_YESOD) as acquired:
                if not acquired:
                    log.info("GC: advisory lock déjà tenu, skip dead data cleanup")
                    return report
                with conn.cursor() as cur:
                    # Marquer deprecated les entries jamais consultées, >30j,
                    # sauf les 'fact' (trop précieuses même si non consultées)
                    cur.execute("""
                        UPDATE epistememory
                        SET epistemic_status = 'deprecated'
                        WHERE access_count = 0
                          AND created_at < NOW() - INTERVAL '30 days'
                          AND epistemic_status NOT IN ('deprecated', 'fact')
                        RETURNING id
                    """)
                    dead = cur.fetchall()
                    report["dead_entries"] = len(dead)
                    if dead:
                        log.info("GC: %d entries mortes marquées deprecated", len(dead))

                    # Purger les prédictions orphelines (>30j, non vérifiées)
                    cur.execute("""
                        DELETE FROM selfmodel_predictions
                        WHERE was_correct IS NULL
                          AND created_at < NOW() - INTERVAL '30 days'
                        RETURNING id
                    """)
                    dead_preds = cur.fetchall()
                    report["dead_predictions"] = len(dead_preds)
                    if dead_preds:
                        log.info("GC: %d prédictions orphelines supprimées", len(dead_preds))

    except Exception as e:
        log.warning("GC dead data: %s", e)

    return report


def task_sifrei_to_yesod(tree: dict) -> dict:
    """Injecter les concepts Sifrei Yesod dans EpisteMemory.

    2 732 concepts kabbalistiques structurés avec embeddings sont en DB
    mais jamais accessibles au rappel mémoire. Cette tâche les y injecte
    avec source='sifrei_yesod' pour qu'ils soient consultables par recall().
    Fréquence : quotidienne. Ne traite que les concepts non encore injectés.
    """
    report: dict = {"task": "sifrei_to_yesod", "injected": 0, "skipped": 0}
    yesod = tree.get("yesod")
    if not yesod:
        report["error"] = "EpisteMemory non disponible"
        return report

    try:
        import psycopg2.extras
        from pool import get_conn

        # Trouver les concepts non encore injectés dans epistememory
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT c.concept_id, c.nom_he, c.nom_fr, c.description, c.domaine
                    FROM sifrei_yesod_concepts c
                    WHERE c.description IS NOT NULL
                      AND NOT EXISTS (
                          SELECT 1 FROM epistememory e
                          WHERE e.content LIKE '%%' || c.concept_id || '%%'
                            AND e.source_sephirah = 'sifrei_yesod'
                      )
                    LIMIT 100
                """)
                new_concepts = cur.fetchall()

        for concept in new_concepts:
            try:
                content = (
                    f"[{concept['concept_id']}] "
                    f"{concept['nom_he'] or ''} / {concept['nom_fr'] or ''} — "
                    f"{concept['description'][:500]}"
                )
                yesod.remember(
                    content=content,
                    source_sephirah="sifrei_yesod",
                    confidence=0.9,
                    domain=concept["domaine"] or "kabbale",
                    tags=["sifrei_yesod", "concept", concept["concept_id"]],
                )
                report["injected"] += 1
            except Exception as e:
                report["skipped"] += 1
                log.debug("Sifrei→Yesod inject %s: %s", concept["concept_id"], e)

        log.info(
            "Sifrei→Yesod: %d injected, %d skipped, %d new concepts found",
            report["injected"], report["skipped"], len(new_concepts),
        )
    except Exception as e:
        report["error"] = str(e)
        log.error("Sifrei→Yesod error: %s", e)

    return report
