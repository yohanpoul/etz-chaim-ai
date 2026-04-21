"""daemon_tasks/daat.py — Da'at tasks: predict, verify, correct biases, maintenance, snapshot.

Extracted from daemon.py for modularity.
"""
from __future__ import annotations

import logging
import os

DB_URL = (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim"))
log = logging.getLogger("etz-daemon")

# Seuils pour la génération de prédictions et biais
_DAAT_WEAK_THRESHOLD = 0.50  # avg_score < 0.50 → domaine faible
_DAAT_STRONG_THRESHOLD = 0.65  # avg_score >= 0.65 → domaine fort
_DAAT_HIGH_VARIANCE_THRESHOLD = 0.10  # std > 0.10 → variance élevée
_DAAT_DECLINE_THRESHOLD = -0.05  # delta < -0.05 → déclin
_DAAT_MIN_QUESTIONS = 10  # minimum de questions pour statistiques fiables


def _query_hitbonenut_domain_stats(db_url: str) -> list[dict]:
    """Requête directe des stats Hitbonenut par domaine.

    Retourne: [{'domain', 'n', 'avg_score', 'stddev', 'recent_avg', 'older_avg'}]
    """
    import psycopg2.extras
    from pool import get_conn

    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                WITH base AS (
                    SELECT domain, score,
                           ROW_NUMBER() OVER (
                               PARTITION BY domain ORDER BY created_at DESC
                           ) AS rn,
                           COUNT(*) OVER (PARTITION BY domain) AS total
                    FROM hitbonenut_questions
                    WHERE score IS NOT NULL
                ),
                stats AS (
                    SELECT domain,
                           total AS n,
                           AVG(score) AS avg_score,
                           STDDEV(score) AS stddev,
                           AVG(score) FILTER (WHERE rn <= 10) AS recent_avg,
                           AVG(score) FILTER (WHERE rn > total - 10) AS older_avg
                    FROM base
                    GROUP BY domain, total
                )
                SELECT domain, n,
                       COALESCE(avg_score, 0) AS avg_score,
                       COALESCE(stddev, 0) AS stddev,
                       COALESCE(recent_avg, avg_score, 0) AS recent_avg,
                       COALESCE(older_avg, avg_score, 0) AS older_avg
                FROM stats
                WHERE n >= %s
                ORDER BY avg_score ASC
            """, (_DAAT_MIN_QUESTIONS,))
            return [dict(r) for r in cur.fetchall()]


def task_snapshot(tree: dict) -> dict:
    """Da'at — Snapshot SelfModel de l'état du système."""
    report = {"task": "snapshot", "health": "unknown", "biases": 0}
    daat = tree.get("daat")
    if not daat:
        report["error"] = "SelfModel non disponible"
        return report

    try:
        state = daat.capture_state()
        report["captured_at"] = str(state.captured_at)
        report["model_confidence"] = round(state.model_confidence, 2)

        biases = daat.detect_biases(state)
        report["biases"] = len(biases)
        if biases:
            report["bias_types"] = list({b.bias_type for b in biases})

        evolution = daat.track_evolution()
        report["health"] = round(evolution.overall_health, 2)
        report["trend"] = evolution.trend

        diag = daat.self_diagnose()
        report["diagnosis"] = diag.get("level", "unknown")
        if diag.get("issues"):
            report["issues"] = diag["issues"]

        log.info(
            "Da'at snapshot: health=%.2f, trend=%s, biases=%d, diag=%s",
            evolution.overall_health, evolution.trend,
            len(biases), diag.get("level"),
        )
    except Exception as e:
        report["error"] = str(e)
        log.error("Snapshot error: %s", e)

    return report


def task_daat_predict(tree: dict) -> dict:
    """Da'at — Prédictions d'erreurs et détection de biais depuis les données.

    Analyse les 416+ questions Hitbonenut pour :
    1. Prédire les échecs dans les domaines faibles (Samael)
    2. Détecter la sur-confiance dans les domaines à haute variance (Samael)
    3. Détecter les blind spots dans les domaines stagnants (Satariel)
    4. Détecter les déclins (Thagirion)
    5. Générer des prédictions pour les intentions actives (Netzach)
    """
    report = {
        "task": "daat_predict",
        "state_captured": False,
        "predictions_generated": 0,
        "biases_detected": 0,
        "domains_analyzed": 0,
    }
    daat = tree.get("daat")
    if not daat:
        report["error"] = "SelfModel non disponible"
        return report

    # ── Rate limiter : cap à 50K prédictions/jour ──
    # Sans ce garde, le système produit jusqu'à 1.5M predictions/jour
    # (rumination cognitive — penser sans jamais vérifier).
    _DAILY_PREDICTION_CAP = 50_000
    try:
        from pool import get_conn

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM selfmodel_predictions "
                    "WHERE predicted_at >= CURRENT_DATE"
                )
                count_today = cur.fetchone()[0]
        if count_today >= _DAILY_PREDICTION_CAP:
            report["skipped"] = True
            report["reason"] = (
                f"Rate limit: {count_today} predictions today "
                f"(cap={_DAILY_PREDICTION_CAP})"
            )
            log.warning(
                "Da'at predict: RATE LIMITED — %d predictions today (cap=%d)",
                count_today, _DAILY_PREDICTION_CAP,
            )
            return report
    except Exception as e:
        log.debug("Da'at predict rate limit check: %s", e)

    # ── Snapshot SelfModel : capturer l'état complet du système ──
    try:
        state = daat.capture_state()
        report["state_captured"] = True
        log.info("SelfModel: état capturé (confiance=%.2f)", state.model_confidence)
    except Exception as e:
        log.warning("SelfModel capture_state failed: %s", e)

    try:
        from selfmodel.models import BiasEntry, Prediction

        # 1. Récupérer les stats Hitbonenut directement
        stats = _query_hitbonenut_domain_stats(DB_URL)
        report["domains_analyzed"] = len(stats)

        predictions = []
        biases = []

        for ds in stats:
            domain = ds["domain"]
            avg = float(ds["avg_score"])
            std = float(ds["stddev"])
            recent = float(ds["recent_avg"])
            older = float(ds["older_avg"])
            n = int(ds["n"])
            delta = recent - older

            # ── Domaine faible → prédiction Samael ──
            if avg < _DAAT_WEAK_THRESHOLD:
                severity = round(1.0 - avg, 2)  # Plus c'est bas, plus c'est sévère
                predictions.append(Prediction(
                    prediction=(
                        f"Domaine faible: {domain} (avg={avg:.3f}, n={n}). "
                        f"Risque d'échec élevé sur les prochaines questions."
                    ),
                    domain=domain,
                    predicted_error_type="samael",
                    predicted_confidence=round(min(0.9, severity), 2),
                ))

            # ── Haute variance + score moyen → sur-confiance (Samael) ──
            if std > _DAAT_HIGH_VARIANCE_THRESHOLD and avg > _DAAT_WEAK_THRESHOLD:
                predictions.append(Prediction(
                    prediction=(
                        f"Haute variance: {domain} (std={std:.3f}, avg={avg:.3f}). "
                        f"Performance instable — risque de sur-estimation."
                    ),
                    domain=domain,
                    predicted_error_type="samael",
                    predicted_confidence=round(min(0.8, std * 3), 2),
                ))
                biases.append(BiasEntry(
                    bias_type="overconfidence",
                    description=(
                        f"Variance élevée en {domain}: std={std:.3f} sur {n} questions. "
                        f"Score moyen {avg:.3f} masque des oscillations."
                    ),
                    evidence={"domain": domain, "avg": avg, "std": std, "n": n},
                    severity=round(min(0.8, std * 4), 2),
                    domain=domain,
                    mitigation=f"Cibler les sous-thèmes faibles de {domain}",
                ))

            # ── Déclin récent → Thagirion ──
            if delta < _DAAT_DECLINE_THRESHOLD and n >= 15:
                predictions.append(Prediction(
                    prediction=(
                        f"Déclin détecté: {domain} (recent={recent:.3f} vs "
                        f"older={older:.3f}, delta={delta:+.3f}). "
                        f"Régression en cours."
                    ),
                    domain=domain,
                    predicted_error_type="thagirion",
                    predicted_confidence=round(min(0.8, abs(delta) * 5), 2),
                ))
                biases.append(BiasEntry(
                    bias_type="recency_bias",
                    description=(
                        f"Déclin en {domain}: les 10 dernières questions "
                        f"({recent:.3f}) sous les 10 premières ({older:.3f})."
                    ),
                    evidence={
                        "domain": domain, "recent_avg": recent,
                        "older_avg": older, "delta": delta,
                    },
                    severity=round(min(0.7, abs(delta) * 4), 2),
                    domain=domain,
                    mitigation=f"Réviser les fondamentaux de {domain}",
                ))

            # ── Stagnation → blind spot (Satariel) ──
            if (abs(delta) < 0.02 and avg < _DAAT_STRONG_THRESHOLD
                    and n >= 20):
                biases.append(BiasEntry(
                    bias_type="domain_blind_spot",
                    description=(
                        f"Stagnation en {domain}: delta={delta:+.3f} sur {n} questions, "
                        f"avg={avg:.3f}. Pas de progression détectable."
                    ),
                    evidence={"domain": domain, "avg": avg, "delta": delta, "n": n},
                    severity=round(0.3 + (1.0 - avg) * 0.5, 2),
                    domain=domain,
                    mitigation=f"Explorer de nouvelles approches pour {domain}",
                ))
                predictions.append(Prediction(
                    prediction=(
                        f"Stagnation: {domain} (avg={avg:.3f}, delta={delta:+.3f}). "
                        f"Domaine en plateau — possible blind spot."
                    ),
                    domain=domain,
                    predicted_error_type="satariel",
                    predicted_confidence=round(0.4 + (1.0 - avg) * 0.3, 2),
                ))

        # ── Biais global : domaines faibles multiples ──
        weak_domains = [ds for ds in stats if float(ds["avg_score"]) < _DAAT_WEAK_THRESHOLD]
        if len(weak_domains) >= 3:
            biases.append(BiasEntry(
                bias_type="underconfidence",
                description=(
                    f"{len(weak_domains)} domaines sous {_DAAT_WEAK_THRESHOLD}: "
                    f"{', '.join(d['domain'] for d in weak_domains)}. "
                    f"Possible sous-performance systémique."
                ),
                evidence={"weak_domains": [d["domain"] for d in weak_domains]},
                severity=round(min(0.8, len(weak_domains) * 0.2), 2),
                mitigation="Renforcer les bases kabbalistiques communes",
            ))

        # ── Prédictions pour les intentions actives ──
        netzach = tree.get("netzach")
        if netzach:
            try:
                active = netzach.get_active_intentions() if hasattr(netzach, 'get_active_intentions') else []
                for intent in active[:5]:
                    desc = getattr(intent, 'description', str(intent))
                    name = getattr(intent, 'name', 'intention')
                    # Chercher les domaines pertinents
                    matching = [
                        ds for ds in stats
                        if ds["domain"] in desc.lower()
                        or desc.lower() in ds["domain"]
                    ]
                    if matching:
                        weakest = min(matching, key=lambda d: float(d["avg_score"]))
                        predictions.append(Prediction(
                            prediction=(
                                f"Intention '{name}' touche le domaine "
                                f"{weakest['domain']} (avg={float(weakest['avg_score']):.3f}). "
                                f"Risque de blocage."
                            ),
                            domain=weakest["domain"],
                            predicted_error_type="gamchicoth",
                            predicted_confidence=round(
                                1.0 - float(weakest["avg_score"]), 2
                            ),
                        ))
            except Exception as e:
                log.warning("Da'at predict: intentions error: %s", e)

        # ── Persister ──
        saved_preds = 0
        for pred in predictions:
            try:
                daat.db.save_prediction(pred)
                saved_preds += 1
            except Exception as e:
                log.warning("Da'at predict: save prediction error: %s", e)

        saved_biases = 0
        for bias in biases:
            try:
                daat.db.save_bias(bias)
                saved_biases += 1
            except Exception as e:
                log.warning("Da'at predict: save bias error: %s", e)

        report["predictions_generated"] = saved_preds
        report["biases_detected"] = saved_biases
        report["weak_domains"] = [d["domain"] for d in weak_domains]
        report["strong_domains"] = [
            ds["domain"] for ds in stats
            if float(ds["avg_score"]) >= _DAAT_STRONG_THRESHOLD
        ]

        log.info(
            "Da'at predict: %d predictions, %d biases from %d domains",
            saved_preds, saved_biases, len(stats),
        )

    except Exception as e:
        report["error"] = str(e)
        log.error("Da'at predict error: %s", e)

    return report


def task_daat_verify(tree: dict) -> dict:
    """Da'at — Vérifier les prédictions passées contre la réalité.

    אוֹר חוֹזֵר — La lumière qui remonte. Sans vérification, Da'at est
    aveugle — il prédit sans jamais savoir s'il avait raison.

    Pour chaque prédiction non vérifiée :
    - Compare le domain de la prédiction aux scores Hitbonenut récents
    - Si le domaine s'est amélioré → prédiction d'échec était fausse
    - Si le domaine a stagné/décliné → prédiction correcte
    """
    report = {
        "task": "daat_verify",
        "checked": 0,
        "verified_correct": 0,
        "verified_incorrect": 0,
    }
    daat = tree.get("daat")
    if not daat:
        report["error"] = "SelfModel non disponible"
        return report

    try:
        import psycopg2.extras
        from pool import get_conn

        # 1. Récupérer les prédictions non vérifiées (max 1000, les plus anciennes)
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, domain, predicted_error_type, predicted_confidence,
                           predicted_at
                    FROM selfmodel_predictions
                    WHERE was_correct IS NULL
                      AND predicted_at < NOW() - INTERVAL '24 hours'
                    ORDER BY predicted_at ASC
                    LIMIT 1000
                """)
                unverified = cur.fetchall()

        if not unverified:
            report["status"] = "no_unverified"
            return report

        # 2. Récupérer les stats récentes par domaine pour comparaison
        current_stats = {}
        stats_raw = _query_hitbonenut_domain_stats(DB_URL)
        for ds in stats_raw:
            current_stats[ds["domain"]] = {
                "avg": float(ds["avg_score"]),
                "recent": float(ds["recent_avg"]),
                "delta": float(ds["recent_avg"]) - float(ds["older_avg"]),
            }

        # 3. Vérifier chaque prédiction
        for pred in unverified:
            domain = pred["domain"]
            error_type = pred["predicted_error_type"]

            if domain not in current_stats:
                continue

            stats = current_stats[domain]
            was_correct = False
            outcome = ""

            if error_type in ("samael", "satariel"):
                # Prédiction de faiblesse/stagnation — correcte si avg toujours bas
                was_correct = stats["avg"] < _DAAT_WEAK_THRESHOLD
                outcome = f"avg={stats['avg']:.3f}, {'toujours faible' if was_correct else 'amélioré'}"
            elif error_type == "thagirion":
                # Prédiction de déclin — correcte si delta toujours négatif
                was_correct = stats["delta"] < -0.02
                outcome = f"delta={stats['delta']:+.3f}, {'déclin confirmé' if was_correct else 'stabilisé'}"
            elif error_type == "gamchicoth":
                # Prédiction de blocage d'intention — correcte si domaine toujours faible
                was_correct = stats["avg"] < 0.5
                outcome = f"avg={stats['avg']:.3f}, {'bloqué' if was_correct else 'débloqué'}"

            try:
                daat.verify_prediction(pred["id"], was_correct, outcome)
                report["checked"] += 1
                if was_correct:
                    report["verified_correct"] += 1
                else:
                    report["verified_incorrect"] += 1
            except Exception as e:
                log.warning("Da'at verify %s: %s", pred["id"], e)

        correct_count = report["verified_correct"]
        incorrect_count = report["verified_incorrect"]
        accuracy = correct_count / max(1, correct_count + incorrect_count)
        report["accuracy"] = accuracy
        log.info(
            "Da'at verify: %d checked, %d correct, %d incorrect (accuracy=%.1f%%)",
            report["checked"], correct_count,
            incorrect_count, accuracy * 100,
        )

    except Exception as e:
        report["error"] = str(e)
        log.error("Da'at verify error: %s", e)

    return report


def task_daat_correct_biases(tree: dict) -> dict:
    """Da'at — Corriger les biais détectés à haute sévérité.

    תִּיקוּן הַדַּעַת — Le Tikkun de Da'at : passer de la détection
    à l'action. Un biais détecté mais non corrigé est pire qu'un biais
    ignoré — il crée l'illusion de la conscience de soi sans la correction.

    Pour chaque biais haute sévérité (>0.6) :
    - overconfidence sur un domaine → réduire le score SelfMap
    - underconfidence → augmenter le score SelfMap
    - domain_blind_spot → flaguer pour exploration prioritaire
    """
    report = {
        "task": "daat_correct_biases",
        "biases_checked": 0,
        "corrections_applied": 0,
        "deactivated": 0,
    }
    daat = tree.get("daat")
    hod = tree.get("hod")
    if not daat:
        report["error"] = "SelfModel non disponible"
        return report

    try:
        # Récupérer les biais actifs haute sévérité
        active_biases = daat.db.get_active_biases()
        high_severity = [b for b in active_biases if b.severity >= 0.6]
        report["biases_checked"] = len(high_severity)

        for bias in high_severity:
            try:
                domain = bias.domain
                if not domain:
                    continue

                if bias.bias_type == "overconfidence" and hod:
                    # Réduire le score SelfMap pour ce domaine
                    if hasattr(hod, "adjust_domain_score"):
                        hod.adjust_domain_score(domain, delta=-0.1)
                        report["corrections_applied"] += 1
                        log.info(
                            "Da'at correction: overconfidence %s → score -0.1",
                            domain,
                        )
                    # Désactiver le biais après correction
                    daat.db.deactivate_bias(bias.id)
                    report["deactivated"] += 1

                elif bias.bias_type == "underconfidence" and hod:
                    if hasattr(hod, "adjust_domain_score"):
                        hod.adjust_domain_score(domain, delta=+0.05)
                        report["corrections_applied"] += 1
                        log.info(
                            "Da'at correction: underconfidence %s → score +0.05",
                            domain,
                        )
                    daat.db.deactivate_bias(bias.id)
                    report["deactivated"] += 1

                elif bias.bias_type == "domain_blind_spot":
                    # Persister dans Yesod pour que l'exploration le voie
                    yesod = tree.get("yesod")
                    if yesod:
                        yesod.remember(
                            content=(
                                f"[Biais Da'at] Blind spot détecté: {domain}. "
                                f"{bias.mitigation or 'Explorer ce domaine en priorité.'}"
                            ),
                            source_sephirah="daat",
                            confidence=0.8,
                            domain=domain,
                            tags=["bias", "blind_spot", "daat_correction"],
                        )
                        report["corrections_applied"] += 1
                    daat.db.deactivate_bias(bias.id)
                    report["deactivated"] += 1

                elif bias.bias_type == "recency_bias":
                    # Vieux biais de déclin — vérifier si toujours d'actualité
                    if hasattr(bias, "detected_at") and bias.detected_at:
                        import datetime

                        age = datetime.datetime.now(datetime.timezone.utc) - bias.detected_at
                        if age.days > 7:
                            daat.db.deactivate_bias(bias.id)
                            report["deactivated"] += 1

            except Exception as e:
                log.warning("Da'at correct bias %s: %s", bias.id, e)

        log.info(
            "Da'at correct: %d checked, %d corrections, %d deactivated",
            report["biases_checked"], report["corrections_applied"],
            report["deactivated"],
        )

    except Exception as e:
        report["error"] = str(e)
        log.error("Da'at correct biases error: %s", e)

    return report


def task_selfmodel_maintenance(tree: dict) -> dict:
    """Da'at Maintenance — nettoyage des predictions non verifiees.

    Audit F01/R6 : selfmodel_predictions avait 5.2M rows (1578 MB = 74% DB)
    mais seulement 215 (0.004%) verifiees. Ce nettoyage :
    1. Verifie un batch de 100 predictions stale (>7 jours)
    2. Archive (supprime) les predictions non verifiees >30 jours

    Le hitkalelut : l'archivage PRESERVE les predictions verifiees.
    """
    report = {
        "task": "selfmodel_maintenance",
        "verify_result": {},
        "archive_result": {},
    }

    try:
        from pool import get_conn, try_advisory_lock, LOCK_SELFMODEL_MAINTENANCE
        from selfmodel.maintenance import archive_old_predictions, verify_stale_predictions

        # 1. Recuperer les domain stats pour la verification
        domain_stats = {}
        try:
            stats_raw = _query_hitbonenut_domain_stats(DB_URL)
            for ds in stats_raw:
                domain_stats[ds["domain"]] = {
                    "avg": float(ds["avg_score"]),
                    "recent": float(ds["recent_avg"]),
                    "delta": float(ds["recent_avg"]) - float(ds["older_avg"]),
                }
        except Exception as e:
            log.warning("Maintenance: cannot load domain stats: %s", e)

        # 2. Verifier les predictions stale (UPDATEs only — no lock needed)
        with get_conn() as conn:
            verify_result = verify_stale_predictions(
                conn, domain_stats=domain_stats or None, batch_size=100,
            )
            report["verify_result"] = verify_result

        # 3. Archiver les vieilles predictions non verifiees (DELETE — lock)
        with get_conn() as conn:
            with try_advisory_lock(conn, LOCK_SELFMODEL_MAINTENANCE) as acquired:
                if not acquired:
                    log.info("SelfModel maintenance: advisory lock déjà tenu, skip archive")
                    report["archive_result"] = {"deleted": 0, "skipped": "lock held"}
                else:
                    archive_result = archive_old_predictions(conn, retention_days=30)
                    report["archive_result"] = archive_result

        total_verified = verify_result.get("verified", 0)
        total_deleted = report["archive_result"].get("deleted", 0)
        if total_verified > 0 or total_deleted > 0:
            log.warning(
                "SelfModel maintenance: %d predictions verified, %d archived (deleted)",
                total_verified, total_deleted,
            )
        else:
            log.info("SelfModel maintenance: nothing to do")

    except Exception as e:
        report["error"] = str(e)
        log.error("SelfModel maintenance error: %s", e)

    return report
