"""daemon_tasks/netzach.py — Netzach task: intention monitoring.

Extracted from daemon.py for modularity.
"""
from __future__ import annotations

import logging
import os

DB_URL = (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim"))
log = logging.getLogger("etz-daemon")


def task_netzach(tree: dict) -> dict:
    """Netzach — Vérifier les intentions actives et diagnostiquer.

    Ne fait PAS avancer automatiquement les sous-tâches
    (ça nécessiterait un LLM pour décider quoi faire),
    mais détecte les intentions stagnantes et zombie.
    """
    report = {"task": "netzach", "intentions": 0, "warnings": []}

    # Garde Tzimtzum : Netzach peut être mis en dormance
    from daemon import _is_tzimtzum_module_active

    if not _is_tzimtzum_module_active("netzach"):
        report["skipped"] = "Netzach dormant (Tzimtzum actif)"
        log.info("Netzach: SKIP — module dormant par Tzimtzum")
        return report

    netzach = tree.get("netzach")
    if not netzach:
        report["error"] = "IntentKeeper non disponible"
        return report

    try:
        active = netzach.db.get_active_intentions()

        # Si aucune intention active, seed automatiquement depuis l'état système
        if not active:
            log.info("Netzach: aucune intention — seed depuis état système")
            try:
                seeded = netzach.seed_system_intentions(DB_URL)
                report["seeded"] = len(seeded)
                log.info("Netzach: %d intentions créées automatiquement", len(seeded))
                active = netzach.db.get_active_intentions()
            except Exception as e:
                log.error("Netzach seed error: %s", e)
                report["seed_error"] = str(e)

        # Mettre à jour le progrès depuis les métriques système (KavanahPlanner)
        try:
            netzach.refresh_progress_from_state(DB_URL)
        except Exception as e:
            log.warning("Netzach refresh error: %s", e)

        # KavanahPlanner pour les suggestions d'action
        try:
            from intentkeeper.kavanah_planner import KavanahPlanner
            kavanah = KavanahPlanner(DB_URL)
        except Exception as e:
            log.warning("KavanahPlanner init failed: %s", e)
            kavanah = None

        report["intentions"] = len(active)

        for intention in active:
            progress = netzach.check_progress(intention.id)
            abandon = netzach.should_abandon(intention.id)

            entry = {
                "goal": intention.goal[:80],
                "progress": f"{progress.progress:.0%}",
                "on_track": progress.is_on_track,
                "days_inactive": round(progress.days_since_activity, 1),
            }

            # KavanahPlanner — suggestion d'action concrète
            if kavanah:
                try:
                    subtasks = netzach.db.get_subtasks(intention.id)
                    descs = [st.description for st in subtasks]
                    action = kavanah.suggest_next_action(intention.goal, descs)
                    entry["suggested_action"] = action
                except Exception as e:
                    log.warning("Kavanah suggest_next_action failed: %s", e)

            if abandon.should_abandon:
                entry["abandon_level"] = abandon.level
                entry["abandon_reason"] = abandon.reason
                report["warnings"].append(
                    f"[{abandon.level}] '{intention.goal[:50]}' — {abandon.reason}"
                )
                log.warning(
                    "Intention à risque [%s]: %s — %s",
                    abandon.level, intention.goal[:50], abandon.reason,
                )
            elif not progress.is_on_track:
                entry["warning"] = progress.warning
                if progress.warning:
                    report["warnings"].append(
                        f"[slow] '{intention.goal[:50]}' — {progress.warning}"
                    )

        log.info(
            "Netzach: %d intentions actives, %d warnings",
            report["intentions"], len(report["warnings"]),
        )
    except Exception as e:
        report["error"] = str(e)
        log.error("Netzach error: %s", e)

    return report
