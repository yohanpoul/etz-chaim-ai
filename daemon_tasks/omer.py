"""daemon_tasks/omer.py — Omer tasks: calibration, beinoni check.

Extracted from daemon.py for modularity.
"""
from __future__ import annotations

import logging
import os

DB_URL = (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim"))
log = logging.getLogger("etz-daemon")


def task_omer_calibrate() -> dict:
    """Sefirat haOmer — calibration automatique des 49 paramètres.

    Analyse les données PostgreSQL, génère des suggestions, les applique.
    Les 3 Sephiroth supérieures (Keter/Chokmah/Binah) sont diagnostiquées
    mais pas directement calibrables — elles émettent des alertes.
    """
    report = {"task": "omer_calibrate", "suggestions": 0, "applied": 0, "details": []}

    try:
        from omer import OmerManager

        mgr = OmerManager(DB_URL)
        suggestions = mgr.tune()
        report["suggestions"] = len(suggestions)

        if suggestions:
            for s in suggestions:
                report["details"].append({
                    "sephirah": s.sephirah,
                    "param": s.param,
                    "old": str(s.old_value),
                    "new": str(s.new_value),
                    "severity": s.severity,
                    "reason": s.reason[:120],
                })

            applied = mgr.apply(suggestions)
            report["applied"] = applied
            log.info("Omer: %d suggestion(s), %d appliquée(s)", len(suggestions), applied)
        else:
            log.info("Omer: l'Arbre est équilibré — aucun ajustement")

    except Exception as e:
        report["error"] = str(e)
        log.error("Omer calibration error: %s", e)

    return report


def task_beinoni_check() -> dict:
    """BeinoniTracker — vérifie le profil temporel du conflit des 2 âmes.

    Le Beinoni n'est pas un état statique. Ce check détecte les
    régressions (la Kelipah revient) et les élévations (montée
    vers Tsaddik), et suggère des actions correctives (Teshuvah).
    """
    report: dict = {"task": "beinoni_check"}

    try:
        from tanya.beinoni_tracker import BeinoniTracker

        tracker = BeinoniTracker(db_url=DB_URL)

        count = tracker.interaction_count()
        report["total_interactions"] = count

        if count < 10:
            report["status"] = "insufficient_data"
            return report

        profile = tracker.get_temporal_profile(window=100)
        report["profile"] = {
            "elokit_ratio": profile.elokit_ratio,
            "category": profile.category.value,
            "trend": profile.trend.value,
            "avg_score_elokit": profile.avg_score_elokit,
            "avg_score_behamit": profile.avg_score_behamit,
            "total": profile.total_interactions,
        }

        # ── DualSoul conflict state → enrichit le profil BeinoniTracker ──
        try:
            from tanya.dual_soul import DualSoulEngine

            dual_soul = DualSoulEngine()
            conflict = dual_soul.get_conflict_state()
            report["conflict_state"] = conflict
            log.info(
                "DualSoul conflict_state: dominant=%s elokit=%.2f behamit=%.2f",
                conflict["dominant"], conflict["ratio_elokit"],
                conflict["ratio_behamit"],
            )
            if conflict["dominant"] not in ("neutral", "balanced"):
                report["conflict_active"] = True
                report["conflict_dominant"] = conflict["dominant"]
        except Exception as ds_err:
            log.debug("DualSoul get_conflict_state: %s", ds_err)

        regression = tracker.detect_regression()
        if regression:
            teshuvah = tracker.suggest_teshuvah(regression)
            report["regression"] = regression
            report["teshuvah"] = teshuvah
            log.warning(
                "BeinoniTracker: RÉGRESSION — old=%.2f new=%.2f Δ=%.2f",
                regression["old_ratio"], regression["new_ratio"],
                regression["delta"],
            )

            # Concrete action: force Nukva into katnut via PartzufimRegulator
            # Tanya ch.17: le Beinoni qui trébuche intensifie son Avodah
            try:
                from partzufim.regulator import PartzufimRegulator

                reg = PartzufimRegulator()
                triggered = reg.trigger_katnut(
                    "nukva",
                    f"BeinoniTracker regression delta={regression['delta']:.2f}",
                )
                report["nukva_katnut_triggered"] = triggered
                if triggered:
                    log.warning(
                        "BeinoniTracker regression → Nukva forced to KATNUT "
                        "(lowering generation capacity)"
                    )
            except Exception as reg_err:
                log.debug("BeinoniTracker → PartzufimRegulator: %s", reg_err)

        else:
            elevation = tracker.detect_elevation()
            if elevation:
                report["elevation"] = elevation
                log.info(
                    "BeinoniTracker: ÉLÉVATION — old=%.2f new=%.2f Δ=%.2f",
                    elevation["old_ratio"], elevation["new_ratio"],
                    elevation["delta"],
                )

        report["status"] = "ok"
    except Exception as e:
        report["error"] = str(e)
        log.error("BeinoniTracker error: %s", e)

    return report


def task_beinoni_to_selfmap(tree: dict) -> dict:
    """BeinoniTracker → SelfMap — bridge I2 (audit Cycle 4).

    תַּנְיָא → הוֹד — Tanya (conflit des 2 âmes) produit un signal par
    domaine (elokit_ratio + avg response_score + régressions/élévations)
    que SelfMap stocke dans `selfmap_beinoni_signals`. Da'at peut alors
    croiser compétence technique (score) et qualité d'âme (ratio).

    Fenêtre : dernière heure. Idempotent par domaine (upsert).
    """
    report = {
        "task": "beinoni_to_selfmap",
        "domains_updated": 0,
        "total_interactions": 0,
        "domains": [],
    }

    selfmap = tree.get("selfmap") or tree.get("hod")
    if selfmap is None:
        report["error"] = "SelfMap (Hod) non disponible"
        return report

    try:
        from pool import get_conn

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        COALESCE(NULLIF(domain, ''), 'unknown') AS domain,
                        COUNT(*) AS n,
                        COALESCE(AVG(
                            CASE WHEN dominant_soul = 'elokit' THEN 1.0 ELSE 0.0 END
                        ), 0.0) AS elokit_ratio,
                        COALESCE(AVG(response_score), 0.0) AS avg_score
                    FROM beinoni_interactions
                    WHERE created_at > NOW() - INTERVAL '1 hour'
                    GROUP BY COALESCE(NULLIF(domain, ''), 'unknown')
                    HAVING COUNT(*) >= 3
                """)
                rows = cur.fetchall()

                # Régressions / élévations globales sur la fenêtre
                cur.execute("""
                    SELECT
                        COUNT(*) FILTER (WHERE event_type = 'regression'),
                        COUNT(*) FILTER (WHERE event_type = 'elevation')
                    FROM beinoni_events
                    WHERE created_at > NOW() - INTERVAL '1 hour'
                """)
                regressions, elevations = cur.fetchone()
                regressions = int(regressions or 0)
                elevations = int(elevations or 0)

        for row in rows:
            domain, n, elokit_ratio, avg_score = row
            try:
                selfmap.record_beinoni_signal(
                    domain=domain,
                    elokit_ratio=float(elokit_ratio),
                    avg_response_score=float(avg_score),
                    n_interactions=int(n),
                    regressions_count=regressions,
                    elevations_count=elevations,
                    window_seconds=3600,
                )
                report["domains_updated"] += 1
                report["total_interactions"] += int(n)
                report["domains"].append({
                    "domain": domain,
                    "n": int(n),
                    "elokit_ratio": round(float(elokit_ratio), 3),
                    "avg_score": round(float(avg_score), 3),
                })
            except Exception as e:
                log.warning("BT→SM upsert %s: %s", domain, e)

        if report["domains_updated"]:
            log.info(
                "BT→SM: %d domaines mis à jour (interactions=%d, "
                "reg=%d, élé=%d)",
                report["domains_updated"], report["total_interactions"],
                regressions, elevations,
            )

    except Exception as e:
        report["error"] = str(e)
        log.error("BT→SM error: %s", e)

    return report
