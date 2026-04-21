"""daemon_tasks/tzimtzum.py — Tzimtzum tasks: detect, helpers, partzuf regulation.

Extracted from daemon.py for modularity.
"""
from __future__ import annotations

import json
import logging
import os

DB_URL = (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim"))
log = logging.getLogger("etz-daemon")


def _ensure_tzimtzum_table() -> None:
    """Créer la table tzimtzum_state si elle n'existe pas."""
    from pool import get_conn

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS tzimtzum_state (
                        id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
                        is_contracted BOOLEAN DEFAULT FALSE,
                        focused_domain TEXT,
                        contraction_count INTEGER DEFAULT 0,
                        expansion_count INTEGER DEFAULT 0,
                        dormant_modules TEXT[] DEFAULT '{}',
                        reshimot_count INTEGER DEFAULT 0,
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """)
                cur.execute("""
                    INSERT INTO tzimtzum_state (id) VALUES (1)
                    ON CONFLICT (id) DO NOTHING
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS tzimtzum_events (
                        id SERIAL PRIMARY KEY,
                        event_type TEXT NOT NULL,
                        domain TEXT,
                        reason TEXT,
                        excluded_domains TEXT[],
                        dormant_modules TEXT[],
                        insights TEXT[],
                        metadata JSONB DEFAULT '{}',
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS tzimtzum_reshimot (
                        id SERIAL PRIMARY KEY,
                        focused_domain TEXT NOT NULL,
                        excluded_domains TEXT[],
                        excluded_modules TEXT[],
                        pre_contraction_state JSONB DEFAULT '{}',
                        reason TEXT,
                        insights TEXT[] DEFAULT '{}',
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """)
    except Exception as e:
        log.warning("Tzimtzum table init failed: %s", e)


def _load_tzimtzum_state_from_db() -> dict:
    """Charger l'état Tzimtzum depuis la DB."""
    from pool import get_conn

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT is_contracted, focused_domain, contraction_count,
                           expansion_count, dormant_modules, reshimot_count
                    FROM tzimtzum_state WHERE id = 1
                """)
                row = cur.fetchone()
                if row:
                    return {
                        "active": row[0],
                        "focused_domain": row[1],
                        "contraction_count": row[2],
                        "expansion_count": row[3],
                        "excluded_domains": [],
                        "dormant_modules": row[4] or [],
                        "reshimot_count": row[5],
                        "reshimu": [],
                        "log": [],
                    }
    except Exception as e:
        log.warning("Tzimtzum load failed: %s", e)
    return {
        "active": False, "focused_domain": None,
        "contraction_count": 0, "expansion_count": 0,
        "excluded_domains": [], "dormant_modules": [], "reshimot_count": 0,
        "reshimu": [], "log": [],
    }


def _find_busiest_domain() -> str | None:
    """Trouver le domaine avec le plus de connexions récentes."""
    from pool import get_conn

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT seed_domain, count(*) as cnt
                    FROM explorationengine_explorations
                    GROUP BY seed_domain
                    ORDER BY cnt DESC
                    LIMIT 1
                """)
                row = cur.fetchone()
                return row[0] if row else None
    except Exception as e:
        log.warning("_find_busiest_domain DB query failed: %s", e)
        return None


def _save_tzimtzum_state_to_db(
    engine, triggered: str | None = None, pressure=None,
) -> None:
    """Persister l'état Tzimtzum en DB + événements/reshimot."""
    from pool import get_conn

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE tzimtzum_state SET
                        is_contracted = %s,
                        focused_domain = %s,
                        contraction_count = %s,
                        expansion_count = %s,
                        dormant_modules = %s,
                        reshimot_count = %s,
                        pressure = %s,
                        pressure_state = %s,
                        kav_domain = %s,
                        updated_at = NOW()
                    WHERE id = 1
                """, (
                    engine.is_contracted,
                    engine.focused_domain,
                    engine.contraction_count,
                    engine.expansion_count,
                    list(engine.get_dormant_modules()),
                    len(engine.get_reshimot()),
                    pressure.global_pressure if pressure else 0.0,
                    pressure.phase.value if pressure else "stable",
                    engine.get_kav_focus(),
                ))
                # Persister l'événement
                if triggered == "contraction":
                    reshimot = engine.get_reshimot()
                    last = reshimot[-1] if reshimot else {}
                    cur.execute("""
                        INSERT INTO tzimtzum_events
                            (event_type, domain, reason, excluded_domains,
                             dormant_modules, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        "contraction",
                        engine.focused_domain,
                        last.get("reason", "auto"),
                        last.get("excluded_domains", []),
                        last.get("excluded_modules", []),
                        json.dumps({"contraction_count": engine.contraction_count}),
                    ))
                    # Persister le reshimu
                    cur.execute("""
                        INSERT INTO tzimtzum_reshimot
                            (focused_domain, excluded_domains, excluded_modules,
                             pre_contraction_state, reason)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        last.get("focused_domain", "general"),
                        last.get("excluded_domains", []),
                        last.get("excluded_modules", []),
                        json.dumps(last.get("pre_contraction_state", {})),
                        last.get("reason", "auto"),
                    ))
                elif triggered == "expansion":
                    cur.execute("""
                        INSERT INTO tzimtzum_events
                            (event_type, domain, reason, metadata)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        "expansion",
                        engine._state.get("focused_domain"),
                        "auto-detect: mastery reached",
                        json.dumps({"expansion_count": engine.expansion_count}),
                    ))
                    # Mettre à jour le reshimu avec les insights
                    reshimot = engine.get_reshimot()
                    if reshimot:
                        last = reshimot[-1]
                        insights = last.get("insights_during_contraction", [])
                        if insights:
                            cur.execute("""
                                UPDATE tzimtzum_reshimot
                                SET insights = %s
                                WHERE id = (
                                    SELECT id FROM tzimtzum_reshimot
                                    ORDER BY created_at DESC LIMIT 1
                                )
                            """, (insights,))
    except Exception as e:
        log.warning("Tzimtzum save failed: %s", e)


def _collect_pressure_metrics() -> dict:
    """Collecter les métriques de pression depuis la DB."""
    from pool import get_conn

    metrics = {}
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                # Tensions (Tiferet)
                cur.execute("""
                    SELECT
                        count(*) FILTER (WHERE resolution_status = 'open') as open_t,
                        count(*) FILTER (WHERE resolution_status != 'open') as resolved_t
                    FROM dissensuengine_tensions
                """)
                row = cur.fetchone()
                metrics["open_tensions"] = row[0] or 0
                metrics["resolved_tensions"] = row[1] or 0

                # Mémoire épistémique (Yesod)
                cur.execute("""
                    SELECT
                        count(*) FILTER (WHERE epistemic_status = 'hypothesis') as hyp,
                        count(*) FILTER (WHERE epistemic_status IN ('fact', 'validated')) as fact
                    FROM epistememory
                """)
                row = cur.fetchone()
                metrics["hypotheses"] = row[0] or 0
                metrics["facts"] = row[1] or 0

                # Insights (Chokmah/Binah)
                cur.execute("""
                    SELECT
                        count(*) FILTER (WHERE status = 'rejected') as rej,
                        count(*) FILTER (WHERE status = 'accepted') as acc,
                        count(*) FILTER (WHERE status = 'pending') as pend
                    FROM candidate_insights
                """)
                row = cur.fetchone()
                metrics["insights_rejected"] = row[0] or 0
                metrics["insights_accepted"] = row[1] or 0
                metrics["insights_pending"] = row[2] or 0

                # Claims causaux (Gevurah)
                cur.execute("""
                    SELECT
                        count(*) as total,
                        count(*) FILTER (WHERE confidence < 0.5) as weak
                    FROM causal_claims
                """)
                row = cur.fetchone()
                metrics["causal_claims_total"] = row[0] or 0
                metrics["causal_claims_weak"] = row[1] or 0

                # Domaines explorés pour chesed_diag (gardé pour compatibilité)
                cur.execute("""
                    SELECT DISTINCT seed_domain
                    FROM explorationengine_explorations
                """)
                metrics["domains_explored"] = [r[0] for r in cur.fetchall()]

    except Exception as e:
        log.warning("Pressure metrics collection error: %s", e)
    return metrics


def _find_weakest_domain() -> str | None:
    """Trouver le domaine avec le score de compétence le plus bas."""
    from pool import get_conn

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT domain FROM selfmap_competence
                    WHERE n_evals > 0
                    ORDER BY score ASC
                    LIMIT 1
                """)
                row = cur.fetchone()
                return row[0] if row else None
    except Exception as e:
        log.warning("_find_weakest_domain DB query failed: %s", e)
        return None


def task_tzimtzum_detect(tree: dict) -> dict:
    """Détecter contraction/expansion via pression système et persister en DB."""
    report = {"task": "tzimtzum", "triggered": None}

    try:
        from pool import get_conn
        from tzimtzum import TzimtzumEngine

        tz_state = _load_tzimtzum_state_from_db()
        engine = TzimtzumEngine(tz_state)
        ctx = {}

        # Chesed diag (gardé pour compatibilité avec contract/expand)
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT count(*) FROM explorationengine_connections")
                    total_connections = cur.fetchone()[0]
                    cur.execute("SELECT count(*) FROM explorationengine_explorations")
                    total_explorations = cur.fetchone()[0]
            ctx["chesed_diag"] = {
                "total_connections": total_connections,
                "total_explorations": total_explorations,
                "domains_explored": [],
            }
        except Exception as e:
            log.warning("Chesed diag DB query failed: %s", e)
            ctx["chesed_diag"] = {
                "total_connections": 0,
                "total_explorations": 0,
                "domains_explored": [],
            }

        # ── Régulation par pression ──
        metrics = _collect_pressure_metrics()
        if metrics.get("domains_explored"):
            ctx["chesed_diag"]["domains_explored"] = metrics["domains_explored"]

        pressure = engine.assess_system_pressure(**{
            k: v for k, v in metrics.items()
            if k != "domains_explored"
        })
        report["pressure"] = pressure.to_dict()

        weakest = _find_weakest_domain() or _find_busiest_domain() or "general"
        action = engine.regulate(pressure, tree, ctx, weakest_domain=weakest)
        report["action"] = {
            "phase": action.phase.value,
            "kav_domain": action.kav_domain,
            "reason": action.reason,
        }

        if action.phase.value == "contraction" and not (
            engine.is_contracted and action.reason.startswith("déjà")
        ):
            report["triggered"] = "contraction"
            # Auto-action : EXÉCUTER la contraction (pas seulement détecter)
            try:
                contract_result = engine.contract(
                    weakest, tree, ctx,
                    reason=f"Auto-contraction daemon: pression={pressure.global_pressure:.2f}",
                )
                report["contract_result"] = {
                    "action": contract_result.get("action"),
                    "domain": contract_result.get("domain"),
                    "dormant_modules": contract_result.get("dormant_modules", []),
                }
                log.info(
                    "Tzimtzum: CONTRACTION EXÉCUTÉE sur '%s' (pression=%.2f, "
                    "%d modules dormants)",
                    action.kav_domain, pressure.global_pressure,
                    len(contract_result.get("dormant_modules", [])),
                )
            except Exception as e_contract:
                report["contract_error"] = str(e_contract)
                log.warning("Tzimtzum: contraction échouée: %s", e_contract)
        elif action.phase.value == "expansion" and action.adjustments:
            report["triggered"] = "expansion"
            # Auto-action : EXÉCUTER l'expansion
            try:
                expand_result = engine.expand(tree, ctx)
                report["expand_result"] = {
                    "action": expand_result.get("action"),
                    "recovered_domains": expand_result.get("recovered_domains", []),
                }
                log.info(
                    "Tzimtzum: EXPANSION EXÉCUTÉE (pression=%.2f, "
                    "%d domaines récupérés)",
                    pressure.global_pressure,
                    len(expand_result.get("recovered_domains", [])),
                )
            except Exception as e_expand:
                report["expand_error"] = str(e_expand)
                log.warning("Tzimtzum: expansion échouée: %s", e_expand)

        _save_tzimtzum_state_to_db(
            engine,
            triggered=report.get("triggered"),
            pressure=pressure,
        )
        report["state"] = {
            "is_contracted": engine.is_contracted,
            "contraction_count": engine.contraction_count,
            "expansion_count": engine.expansion_count,
            "pressure": pressure.global_pressure,
            "phase": pressure.phase.value,
        }

    except Exception as e:
        report["error"] = str(e)
        log.warning("Tzimtzum detect error: %s", e)

    return report


def task_autojudge_to_partzuf(tree: dict) -> dict:
    """AutoJudge → PartzufimRegulator — bridge I2 (audit Cycle 4).

    גְּבוּרָה → פַּרְצוּפִים — les verdicts récents de Gevurah (AutoJudge)
    doivent pousser Zeir Anpin (les 6 midot = actions) vers katnut/gadlut
    sans attendre le polling 24h de `_dynamic_za`.

    Complément de `task_partzuf_regulation` : ce dernier moyenne sur
    DYNAMIC_WINDOW_HOURS (24h) ; ici on réagit sur la dernière heure.

    Seuils :
        ratio_accepted < 0.4 OR avg_score < 0.4 → katnut (Zeir Anpin)
        ratio_accepted > 0.7 AND avg_score > 0.6 → gadlut (Zeir Anpin)
    """
    report = {
        "task": "autojudge_to_partzuf",
        "experiments_scanned": 0,
        "accepted": 0,
        "rejected": 0,
        "avg_score": None,
        "transition": None,
    }

    try:
        from pool import get_conn

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        COUNT(*) FILTER (WHERE decision = 'accepted'),
                        COUNT(*) FILTER (WHERE decision = 'rejected'),
                        COUNT(*),
                        COALESCE(AVG(score_overall), 0.0)
                    FROM autojudge_experiments
                    WHERE created_at > NOW() - INTERVAL '1 hour'
                """)
                accepted, rejected, total, avg_score = cur.fetchone()

        report["accepted"] = int(accepted or 0)
        report["rejected"] = int(rejected or 0)
        report["experiments_scanned"] = int(total or 0)
        report["avg_score"] = round(float(avg_score or 0.0), 3)

        # Pas assez de données → pas de décision (évite les faux-positifs).
        if report["experiments_scanned"] < 3:
            return report

        ratio_accepted = accepted / total if total else 0.0
        from partzufim.regulator import PartzufimRegulator
        reg = PartzufimRegulator()

        if ratio_accepted < 0.4 or report["avg_score"] < 0.4:
            reason = (
                f"autojudge recent: accepted={accepted}/{total} "
                f"(ratio={ratio_accepted:.2f}), avg={report['avg_score']:.2f}"
            )
            if reg.trigger_katnut("zeir_anpin", reason):
                report["transition"] = "katnut"
                log.info("AJ→Partzuf: Zeir Anpin → katnut (%s)", reason)
        elif ratio_accepted > 0.7 and report["avg_score"] > 0.6:
            reason = (
                f"autojudge recent: accepted={accepted}/{total} "
                f"(ratio={ratio_accepted:.2f}), avg={report['avg_score']:.2f}"
            )
            if reg.trigger_gadlut("zeir_anpin", reason):
                report["transition"] = "gadlut"
                log.info("AJ→Partzuf: Zeir Anpin → gadlut (%s)", reason)

    except Exception as e:
        report["error"] = str(e)
        log.warning("AJ→Partzuf error: %s", e)

    return report


def task_partzuf_regulation(tree: dict) -> dict:
    """Régulation horaire des Partzufim — transitions katnut<->gadlut.

    Vérifie les conditions de transition pour chaque Partzuf :
      - Score < 0.4 → katnut (avec hystérésis : retour à 0.6)
      - Cascade Atik Yomin → tous dégradés
      - Cascade Imma katnut → ZA katnut

    Ceci permet aux Partzufim de changer d'état même en dehors
    de cmd_ask (ex: Hitbonenut fait baisser les scores la nuit).
    """
    report = {
        "task": "partzuf_regulation",
        "transitions": [],
        "states": {},
    }

    try:
        from partzufim.regulator import PartzufimRegulator

        reg = PartzufimRegulator()
        state = reg.load_state()

        # Snapshot des états pour le rapport
        for name, ps in state.items():
            report["states"][name] = {
                "score": ps.get("overall", 0),
                "mochin": ps.get("mochin_state", "?"),
                "orientation": ps.get("orientation", "?"),
            }

        # Vérifier les transitions
        transitions = reg.check_transitions(state)
        report["transitions"] = transitions

        if transitions:
            for t in transitions:
                log.info("Partzuf %s: %s → %s (%s)",
                         t["partzuf"], t["from"], t["to"], t["reason"])
        else:
            log.debug("Partzuf regulation: aucune transition")

    except Exception as e:
        report["error"] = str(e)
        log.warning("Partzuf regulation error: %s", e)

    return report
