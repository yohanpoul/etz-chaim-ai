#!/usr/bin/env python3
"""daemon.py — Keter-de-Malkuth : le battement de coeur de l'Arbre.

כֶּתֶר שֶׁבְּמַלְכוּת — La couronne dans le royaume.
Un processus léger qui veille sur l'Arbre en permanence :
- Hitbonenut   (continu) : auto-apprentissage, tourne dès le démarrage
- Netzach      (1h)      : vérifie les intentions actives, détecte stagnation
- Gevurah      (24h)     : GC de Yesod, supprime les entrées périmées
- Da'at        (24h)     : snapshot SelfModel + prédictions depuis Hitbonenut
- Tiferet      (24h)     : détecte les contradictions dans EpisteMemory
- Binah        (24h)     : enrichit les claims causaux avec confounders LLM
- Karpathy     (23h-0h30): Karpathy Loop — explore et enrichit EpisteMemory
- Rapport      (24h)     : écrit un résumé quotidien lisible

Le Hitbonenut tourne en continu sans schedule horaire.
Seule exception : pause pendant le Karpathy Loop (23h-0h30).
Consolidation automatique toutes les 100 questions.
Le daemon ne charge les modèles Ollama QUE quand il a une tâche,
puis libère tout. Empreinte mémoire au repos : ~30 Mo.

Usage:
    python daemon.py                     # Lancer en foreground (debug)
    python daemon.py --once              # Exécuter un cycle unique puis quitter
    python daemon.py --task gc           # Exécuter une tâche spécifique
    python daemon.py --task auto-improve # Lancer le Karpathy Loop manuellement
"""

from __future__ import annotations

import json
import logging
import os
import signal
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timedelta
from pathlib import Path

# ─── Paths ──────────────────────────────────────────────────

ETZ_HOME = Path.home() / ".etz-chaim"
ETZ_HOME.mkdir(exist_ok=True)

LOG_FILE = ETZ_HOME / "daemon.log"
PID_FILE = ETZ_HOME / "daemon.pid"
STATE_FILE = ETZ_HOME / "daemon_state.json"
REPORT_DIR = ETZ_HOME / "reports"
REPORT_DIR.mkdir(exist_ok=True)

DB_URL = (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim"))
CONFIG_PATH = Path(__file__).parent / "config.yaml"

# ─── Intervals ──────────────────────────────────────────────

INTERVAL_NETZACH = 3600       # 1 heure
INTERVAL_PARTZUF_REG = 3600   # 1 heure — régulation Partzufim (transitions katnut↔gadlut)
INTERVAL_DAILY = 86400        # 24 heures
INTERVAL_OMER = 604800        # 7 jours — Sefirat haOmer hebdomadaire
INTERVAL_SOFER = 300          # 5 minutes — SoferWatcher (Sifrei Yesod)
INTERVAL_DIN_MONITOR = 1800   # 30 minutes — Tamid : surveillance Gevurah interne (Tanya ch. 27)
INTERVAL_EXTERNAL_SCAN = 604800  # 7 jours — Scans Promptfoo + Garak hebdomadaires
INTERVAL_VALIDATE_ORPHAN = 21600  # 6 heures — Sprint 5.6 : validation des pending hitbonenut orphelins
SLEEP_TICK = 60               # Vérifier toutes les 60 secondes
SENTIER_TIMEOUT = 120         # Timeout par sentier (secondes)
FULL_TREE_TIMEOUT = 900       # Timeout global exploration arbre (15 min)

# Karpathy nocturne : plage horaire
# PROVISOIRE avril-juin 2026 — Mac principal eteint la nuit, Karpathy
# decale en soiree 21h-23h. A restaurer a 23h/0h (regime doctrinal
# Tikkun Chatzot) quand le Mac mini dedie sera en place.
# Voir audits/mode_nuit_provisoire_avril_juin_2026.md.
KARPATHY_START_HOUR = 21      # Provisoire : 21h (doctrinal : 23h)
KARPATHY_END_HOUR = 23        # Provisoire : 23h exclusif (doctrinal : 0h wrap)


def _in_karpathy_window(hour: int, minute: int) -> bool:
    """Retourne True si (hour, minute) est dans la fenêtre Karpathy.

    Deux régimes :
      - END > START (ex. 21→23) : fenêtre simple, START <= hour < END.
      - END <= START (ex. 23→0) : wrap autour de minuit, conserve le
        comportement historique « hour == START OR (hour == 0 AND
        minute <= 30) » — Karpathy démarre dans l'heure pleine START,
        tourne jusqu'à ~0h30 inclus.

    Le régime wrap est le régime doctrinal originel (Tikkun Chatzot,
    chatzot halayla). Le régime simple est utilisé en mode « provisoire »
    quand la machine hôte ne peut pas rester allumée la nuit — voir
    audits/mode_nuit_provisoire_avril_juin_2026.md.
    """
    if KARPATHY_END_HOUR > KARPATHY_START_HOUR:
        return KARPATHY_START_HOUR <= hour < KARPATHY_END_HOUR
    return hour == KARPATHY_START_HOUR or (hour == 0 and minute <= 30)

# ─── Full Tree Scope ──────────────────────────────────────

# Les 22 sentiers dans l'ordre initiatique (32→11)
ALL_SENTIER_NAMES = [
    # Moitié basse (sentiers 32-23)
    "tav", "shin", "resh", "qoph", "tsadi",
    "ayin", "peh", "samekh", "nun", "lamed",
    # Moitié haute (sentiers 22-11)
    "kaph", "yod", "teth", "cheth", "zayin",
    "vav", "heh", "daleth", "gimel", "beth",
    "aleph", "mem",
]

LOWER_SENTIERS = set(ALL_SENTIER_NAMES[:10])   # Sentiers 32-23
UPPER_SENTIERS = set(ALL_SENTIER_NAMES[10:])   # Sentiers 22-11

# Paires de Zivug entre Partzufim
ZIVUG_PAIRS = [
    ("abba", "imma"),               # Chokmah × Binah → Mochin de Zeir Anpin
    ("zeir_anpin", "nukva"),        # Tiferet × Malkuth → manifestation
    ("arikh_anpin", "atik_yomin"),  # Keter interne → volonté primordiale
]

# ─── Config ────────────────────────────────────────────────

def load_daemon_config() -> dict:
    """Charger la section daemon: du config.yaml."""
    defaults = {
        "auto_improve_hour": 21,
        "auto_improve_max_cycles": 10,
        "auto_improve_timeout": 300,
        "novelty_threshold": 0.15,
        "sentier_exploration": True,
        "zivug_testing": True,
        "convergence_tracking": True,
    }
    try:
        import yaml
        with open(CONFIG_PATH) as f:
            cfg = yaml.safe_load(f)
        return {**defaults, **cfg.get("daemon", {})}
    except Exception:
        return defaults

# ─── Logging ────────────────────────────────────────────────

def setup_logging() -> logging.Logger:
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Configurer le root logger — tous les modules (hitbonenut, olamot, etc.)
    # héritent automatiquement sans duplication
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Audit cycle 4, N2 : RotatingFileHandler pour éviter le disque
    # plein. 10 MB par fichier × 5 backups = 60 MB max au total.
    from logging.handlers import RotatingFileHandler
    fh = RotatingFileHandler(
        LOG_FILE, maxBytes=10_000_000, backupCount=5, encoding="utf-8",
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # Console (si foreground)
    if sys.stdout.isatty():
        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        root.addHandler(ch)

    return logging.getLogger("etz-daemon")


# Sprint 8 D-log1 : module-level getter sans side-effect. setup_logging()
# n'ajoute les handlers RotatingFileHandler/StreamHandler qu'une fois
# appelée explicitement depuis __main__. Évite la pollution de
# daemon.log par les tests pytest qui importent daemon.
log = logging.getLogger("etz-daemon")


# ─── PID lock ──────────────────────────────────────────────


def _is_pid_alive(pid: int) -> bool:
    """Vérifier si un processus est vivant (signal 0 = test existence)."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def acquire_pid_lock() -> None:
    """Acquérir le PID lock. Refuse de démarrer si un daemon tourne déjà.

    כְּלִי — Le Keli (récipient) ne peut contenir qu'une seule lumière.
    Deux daemons sur la même DB = corruption silencieuse.
    """
    if PID_FILE.exists():
        try:
            old_pid = int(PID_FILE.read_text().strip())
            if _is_pid_alive(old_pid):
                log.error(
                    "Daemon déjà actif (PID %d). Refus de démarrer. "
                    "Si le processus est mort, supprimer %s",
                    old_pid, PID_FILE,
                )
                sys.exit(1)
            else:
                log.warning(
                    "PID stale détecté (%d, processus mort). Nettoyage.",
                    old_pid,
                )
                PID_FILE.unlink()
        except (ValueError, OSError):
            log.warning("PID file corrompu. Nettoyage.")
            PID_FILE.unlink(missing_ok=True)

    PID_FILE.write_text(str(os.getpid()))
    log.info("PID lock acquis (PID %d)", os.getpid())


def release_pid_lock() -> None:
    """Libérer le PID lock. Vérifie que c'est bien notre PID."""
    if PID_FILE.exists():
        try:
            stored_pid = int(PID_FILE.read_text().strip())
            if stored_pid == os.getpid():
                PID_FILE.unlink()
                log.info("PID lock libéré")
            else:
                log.warning(
                    "PID file contient %d, nous sommes %d — pas notre lock",
                    stored_pid, os.getpid(),
                )
        except (ValueError, OSError):
            PID_FILE.unlink(missing_ok=True)


# ─── State persistence ──────────────────────────────────────

def load_state() -> dict:
    """Charger l'état du daemon (dernières exécutions)."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
    return {
        "last_netzach": 0,
        "last_gc": 0,
        "last_snapshot": 0,
        "last_contradictions": 0,
        "last_report": 0,
        "last_auto_improve": 0,
        "last_hitbonenut": 0,
        "last_insightforge": 0,
        "last_tiferet_synthesize": 0,
        "last_binah_confounders": 0,
        "last_omer": 0,
        "last_clustering": 0,
        "last_partzuf_reg": 0,
        "last_din_monitor": 0,
        "last_external_scan": 0,
        "last_orphan_validation": 0,
    }


def save_state(state: dict) -> None:
    """Sauvegarder l'état du daemon — écriture atomique (write+rename).

    Crash pendant save_state() ne corrompt plus daemon_state.json.
    Le rename est atomique sur les systèmes POSIX (même filesystem).
    """
    state["hitbonenut_running"] = _hitbonenut_runner.is_running
    state["_daemon_pid"] = os.getpid()
    state["_last_save"] = time.time()

    tmp_path = STATE_FILE.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(state, indent=2))
    os.replace(str(tmp_path), str(STATE_FILE))  # atomique POSIX


# ─── Tree lifecycle (léger) ─────────────────────────────────

def _init_tree():
    """Initialiser l'Arbre — appelé uniquement quand nécessaire."""
    # Import local pour ne pas charger au démarrage
    sys.path.insert(0, str(Path(__file__).parent))
    from main import init_tree
    return init_tree(DB_URL)


def _close_tree(tree: dict):
    """Fermer proprement."""
    from main import close_tree
    close_tree(tree)


# ─── Tzimtzum dormancy guard ────────────────────────────────


def _is_tzimtzum_module_active(module_name: str) -> bool:
    """Vérifier si un module est actif (non-dormant par Tzimtzum).

    Le Tsimtsum peut mettre Chesed et Netzach en dormance.
    Cette fonction vérifie l'état persisté en DB.
    """
    try:
        from tzimtzum import TzimtzumEngine
        tz_state = _load_tzimtzum_state_from_db()
        engine = TzimtzumEngine(tz_state)
        return engine.is_module_active(module_name)
    except Exception as e:
        log.warning("tzimtzum is_module_active check failed: %s", e)
        return True  # En cas d'erreur, pas de blocage


# ─── Tasks (extracted to daemon_tasks/ package) ─────────────
from daemon_tasks import (  # noqa: E402
    EtzDomainJudge,
    _collect_pressure_metrics,
    _ensure_tzimtzum_table,
    _find_busiest_domain,
    _find_weakest_domain,
    _generate_forge_questions,
    _load_tzimtzum_state_from_db,
    _query_hitbonenut_domain_stats,
    _recycle_candidate_rejections_to_fti,
    _recycle_rejections_to_fti,
    _save_tzimtzum_state_to_db,
    task_auto_improve,
    task_autojudge_to_partzuf,
    task_beinoni_check,
    task_beinoni_to_selfmap,
    task_binah_causal_graphs,
    task_binah_confounders,
    task_binah_evidence_elevator,
    task_binah_to_yesod,
    task_chesed_analogies,
    task_clustering,
    task_concept_harvest,
    task_contradictions,
    task_cube_insights,
    task_daat_correct_biases,
    task_daat_predict,
    task_daat_verify,
    task_dira_birur_stats,
    task_explore_full_tree,
    task_explore_open_questions,
    task_gc,
    task_gevurah_eval,
    task_hitbonenut,
    task_insightforge,
    task_insightforge_to_selfmodel,
    task_log_retention,
    task_masakh_health,
    task_memory_stats,
    task_netzach,
    task_omer_calibrate,
    task_partzuf_regulation,
    task_selfmodel_maintenance,
    task_sifrei_to_yesod,
    task_snapshot,
    task_sofer_watcher,
    task_tiferet_synthesize,
    task_tzeruf_spatial,
    task_tzimtzum_detect,
    task_validate_orphan_candidates,
    task_yesod_mature,
)

# Re-export threshold constants used by run_cycle indirectly
from daemon_tasks.daat import (  # noqa: E402, F811
    _DAAT_DECLINE_THRESHOLD,
    _DAAT_HIGH_VARIANCE_THRESHOLD,
    _DAAT_MIN_QUESTIONS,
    _DAAT_STRONG_THRESHOLD,
    _DAAT_WEAK_THRESHOLD,
)


# ─── Zivvug → Partzufim propagation ────────────────────────
# Sprint 8 D1 — _apply_zivvug_to_partzufim SUPPRIMÉ.
# Doctrine EC-K5-008 (Sha'ar HaKlalim 5:2, Etz Chaim) : l'Ohr Zivvug doit
# transiter par les Kelim (facultés), jamais direct sur overall_score.
# Les boosts persistent dans zivvug_state (couche Mem du Tzelem) et sont
# consommés par update_all_partzufim Phase 2 (Hitlabshut, couche Lamed).


# ─── Hitbonenut helpers (kept in daemon.py — used by HitbonenutDaemonRunner) ──

_DIFFICULTY_TO_COMPLEXITY = {
    "progressive": 0.3, "intermediaire": 0.5, "avancee": 0.8,
}


def _record_hitbonenut_to_beinoni(session) -> None:
    """Enregistre chaque Q/A hitbonenut comme interaction BeinoniTracker.

    Le Hitbonenut est toujours contemplation (NefeshHaElokit dominante).
    Chaque question répondue = une interaction enregistrée.
    """
    try:
        from tanya.beinoni_tracker import BeinoniTracker
        tracker = BeinoniTracker(db_url=DB_URL)
        for r in session.results:
            tracker.record_interaction(
                dominant_soul="elokit",
                response_score=r.score,
                olam_used="briah",
                complexity_score=_DIFFICULTY_TO_COMPLEXITY.get(r.difficulty, 0.5),
                domain=r.domain,
                query_snippet=r.question[:100],
            )
        log.debug("BeinoniTracker: %d interactions hitbonenut enregistrées", len(session.results))
    except Exception as e:
        log.warning("BeinoniTracker record_hitbonenut: %s", e)


def _daemon_emit_hitbonenut(event: str, **data):
    """SSE helper pour Hitbonenut."""
    try:
        from web.events import emit as _emit
        _emit(f"hitbonenut_{event}", **data)
    except Exception as e:
        log.warning("SSE emit hitbonenut failed: %s", e)


_STUB_REMOVED = True  # marker: task functions moved to daemon_tasks/

# (Old task function bodies removed — now in daemon_tasks/*.py)
# The following line prevents accidental re-inclusion:
# END_OF_EXTRACTED_TASKS

# ─── Hitbonenut (helpers kept for HitbonenutDaemonRunner) ─────
# _DIFFICULTY_TO_COMPLEXITY, _record_hitbonenut_to_beinoni, _daemon_emit_hitbonenut
# are imported above in the extracted-tasks import block.
# They were KEPT in daemon.py because HitbonenutDaemonRunner needs them directly.
_END_MARKER = True  # noqa: F841

# ─── Hitbonenut Continuous Runner ─────────────────────────

class HitbonenutDaemonRunner:
    """Gère le Hitbonenut en mode continu dans un thread dédié.

    Le Hitbonenut tourne en continu dès le démarrage du daemon.
    Seule exception : pause pendant le Karpathy Loop (23h-0h30).
    Après le Karpathy, le Hitbonenut reprend immédiatement.
    Si le Mac est éteint puis rallumé : launchd relance le daemon,
    le Hitbonenut reprend en continu. Rien n'est perdu (scores en PG).
    """

    def __init__(self):
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_session: "SessionResult | None" = None
        self._running = False
        self._started_at: float | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, tree: dict) -> None:
        """Démarrer le Hitbonenut continu dans un thread."""
        if self.is_running:
            log.info("Hitbonenut continu déjà en cours")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            args=(tree,),
            name="hitbonenut-continuous",
            daemon=True,
        )
        self._thread.start()
        self._running = True
        self._started_at = time.time()
        log.info("Hitbonenut continu démarré (thread=%s)", self._thread.name)

    def stop(self, timeout: float = 30.0) -> None:
        """Arrêter proprement le Hitbonenut continu."""
        if not self.is_running:
            return
        log.info("Arrêt du Hitbonenut continu...")
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                log.warning("Hitbonenut continu: thread n'a pas terminé dans le délai")
        self._running = False
        log.info("Hitbonenut continu arrêté")

    def get_status(self) -> dict:
        """État courant du runner."""
        uptime = None
        if self._started_at and self.is_running:
            uptime = round(time.time() - self._started_at, 1)
        return {
            "running": self.is_running,
            "started_at": self._started_at,
            "uptime_seconds": uptime,
            "last_session_id": str(self._last_session.session_id) if self._last_session else None,
            "last_questions": self._last_session.n_questions if self._last_session else 0,
            "last_avg_score": self._last_session.avg_score if self._last_session else 0.0,
        }

    def _run_loop(self, tree: dict) -> None:
        """Thread principal : lance run_research_loop (Hitbonenut-2).

        Hitbonenut-2 = Karpathy AutoResearch + Or Chozer + Da'at.
        Boucle de recherche réflexive autonome qui modifie les paramètres
        du système, mesure l'impact, extrait des principes, et vérifie
        la transformation opérationnelle.

        Fallback sur run_continuous() si run_research_loop échoue.
        """
        try:
            from hitbonenut import HitbonenutEngine

            engine = HitbonenutEngine(
                tree=tree,
                db_url=DB_URL,
                corpus_path=Path(__file__).parent / "hitbonenut_corpus.yaml",
            )

            _daemon_emit_hitbonenut("research_start")

            # ── Hitbonenut-2 : boucle de recherche réflexive ──
            experiments = engine.run_research_loop(stop_event=self._stop_event)

            keeps = [e for e in experiments if e.status == "keep"]
            discards = [e for e in experiments if e.status == "discard"]
            principles = [e for e in experiments if e.principle]

            _daemon_emit_hitbonenut(
                "research_end",
                experiments=len(experiments),
                keeps=len(keeps),
                discards=len(discards),
                principles=len(principles),
            )

            log.info(
                "Hitbonenut-2 thread terminé: %d exp, %d keep, %d discard, %d principes",
                len(experiments), len(keeps), len(discards), len(principles),
            )

        except Exception as e:
            log.error("Hitbonenut-2 thread error: %s\n%s", e, traceback.format_exc())
        finally:
            self._running = False


# Instance globale du runner (utilisée par le daemon et la CLI)
_hitbonenut_runner = HitbonenutDaemonRunner()


# ─── Daily Report ───────────────────────────────────────────

def write_daily_report(results: dict) -> str:
    """Écrire le rapport quotidien lisible."""
    today = datetime.now().strftime("%Y-%m-%d")
    report_path = REPORT_DIR / f"{today}.txt"

    lines = []
    lines.append("=" * 60)
    lines.append(f"  Etz Chaim — Rapport Quotidien — {today}")
    lines.append("=" * 60)
    lines.append("")

    # Mémoire
    mem = results.get("memory_stats", {})
    lines.append("  YESOD (Mémoire)")
    lines.append(f"    Entrées actives  : {mem.get('active_entries', '?')}")
    lines.append(f"    Confiance moy.   : {mem.get('avg_confidence', '?')}")
    lines.append(f"    Domaines         : {mem.get('domains', '?')}")
    lines.append(f"    Avec embeddings  : {mem.get('with_embeddings', '?')}")
    lines.append(f"    Contradictions   : {mem.get('open_contradictions', '?')}")
    lines.append(f"    Expirent bientot : {mem.get('near_expiration', '?')}")
    lines.append("")

    # GC
    gc = results.get("gc", {})
    if "error" in gc:
        lines.append(f"  GEVURAH-DE-YESOD (GC) — ERREUR: {gc['error']}")
    else:
        lines.append("  GEVURAH-DE-YESOD (GC)")
        lines.append(f"    Expirées nettoyées : {gc.get('expired', 0)}")
        lines.append(f"    Total deprecated   : {gc.get('deprecated', 0)}")
    lines.append("")

    # Intentions
    netzach = results.get("netzach", {})
    if "error" in netzach:
        lines.append(f"  NETZACH (Intentions) — ERREUR: {netzach['error']}")
    else:
        lines.append("  NETZACH (Intentions)")
        lines.append(f"    Actives   : {netzach.get('intentions', 0)}")
        warnings = netzach.get("warnings", [])
        if warnings:
            lines.append(f"    Alertes   :")
            for w in warnings:
                lines.append(f"      ! {w}")
        else:
            lines.append(f"    Alertes   : aucune")
    lines.append("")

    # Snapshot
    snap = results.get("snapshot", {})
    if "error" in snap:
        lines.append(f"  DA'AT (SelfModel) — ERREUR: {snap['error']}")
    else:
        lines.append("  DA'AT (SelfModel)")
        lines.append(f"    Santé globale  : {snap.get('health', '?')}")
        lines.append(f"    Tendance       : {snap.get('trend', '?')}")
        lines.append(f"    Confiance      : {snap.get('model_confidence', '?')}")
        lines.append(f"    Biais détectés : {snap.get('biases', 0)}")
        lines.append(f"    Diagnostic     : {snap.get('diagnosis', '?')}")
        if snap.get("issues"):
            for issue in snap["issues"]:
                lines.append(f"      ! {issue}")
    lines.append("")

    # Da'at Predictions
    dp = results.get("daat_predict", {})
    if dp and dp.get("predictions_generated", 0) > 0:
        lines.append("  DA'AT PREDICTIONS")
        lines.append(f"    Domaines analysés : {dp.get('domains_analyzed', 0)}")
        lines.append(f"    Prédictions       : {dp.get('predictions_generated', 0)}")
        lines.append(f"    Biais détectés    : {dp.get('biases_detected', 0)}")
        weak = dp.get("weak_domains", [])
        if weak:
            lines.append(f"    Domaines faibles  : {', '.join(weak)}")
        strong = dp.get("strong_domains", [])
        if strong:
            lines.append(f"    Domaines forts    : {', '.join(strong)}")
        lines.append("")

    # Contradictions
    contra = results.get("contradictions", {})
    if "error" in contra:
        lines.append(f"  TIFERET (Contradictions) — ERREUR: {contra['error']}")
    else:
        lines.append("  TIFERET (Contradictions)")
        lines.append(f"    Conclusions      : {contra.get('total_conclusions', 0)}")
        lines.append(f"    Tensions         : {contra.get('tensions', 0)}")
        lines.append(f"    Santé            : {contra.get('health', '?')}")
        lines.append(f"    Divergence moy.  : {contra.get('avg_divergence', '?')}")
        lines.append(f"    Questions ouvertes: {contra.get('open_questions', 0)}")
        lines.append(f"    Diagnostic       : {contra.get('diagnosis', '?')}")
    lines.append("")

    # Tiferet Synthesize
    tifs = results.get("tiferet_synthesize", {})
    if tifs and not tifs.get("error"):
        lines.append("  TIFERET (Synthèses)")
        lines.append(f"    Conclusions récoltées : {tifs.get('harvested', 0)}")
        lines.append(f"    Total conclusions     : {tifs.get('total_conclusions', 0)}")
        lines.append(f"    Domaines traités      : {tifs.get('domains_processed', 0)}")
        lines.append(f"    Synthèses produites   : {tifs.get('syntheses', 0)}")
        lines.append(f"    Dissensus             : {tifs.get('dissensus', 0)}")
        lines.append("")
    elif tifs and tifs.get("error"):
        lines.append(f"  TIFERET (Synthèses) — ERREUR: {tifs['error']}")
        lines.append("")

    # Full Tree exploration
    ft = results.get("full_tree", {})
    if ft:
        sentiers = ft.get("sentiers", {})
        lines.append("  ETZ CHAIM (Arbre Complet — 22 Sentiers)")
        lines.append(f"    Total            : {sentiers.get('total', 22)}")
        lines.append(f"    Succès           : {sentiers.get('successes', 0)}")
        lines.append(f"    Échecs           : {sentiers.get('failures', 0)}")
        lines.append(f"    Erreurs          : {sentiers.get('errors', 0)}")
        failed = ft.get("failed_sentiers", [])
        if failed:
            lines.append(f"    Sentiers en échec: {', '.join(failed[:10])}")
        cross = ft.get("cross_insights", [])
        if cross:
            lines.append(f"    Cross-insights   : {len(cross)}")
            for c in cross[:5]:
                lines.append(f"      · {c}")
            if len(cross) > 5:
                lines.append(f"      ... et {len(cross) - 5} de plus")
        lines.append("")

        # Zivugim
        ziv = ft.get("zivugim", {})
        lines.append("  ZIVUGIM (Couplages entre Partzufim)")
        lines.append(f"    Paires testées   : {ziv.get('pairs_tested', 0)}")
        for zr in ziv.get("results", []):
            if "error" in zr:
                lines.append(f"    {zr['pair']}: ERREUR — {zr['error'][:80]}")
            else:
                status = "✓" if zr.get("success") else "✗"
                lines.append(
                    f"    {status} {zr['pair']}: "
                    f"resonance={zr.get('resonance', '?')}, "
                    f"{zr.get('orientation', '?')}"
                )
        lines.append("")

        # Convergence
        conv = ft.get("convergence", {})
        lines.append("  CONVERGENCE (Métriques Adam Kadmon)")
        ohr = conv.get("ohr_ratio", {})
        lines.append(f"    Ohr Pnimi        : {ohr.get('pnimi', '?')}")
        lines.append(f"    Ohr Makif        : {ohr.get('makif', '?')}")
        lines.append(f"    Ratio P/M        : {ohr.get('ratio', '?')}")
        lines.append(f"    Taux intégration : {ohr.get('integration_rate', '?')}")
        nitz = conv.get("nitzotzot", {})
        lines.append(f"    Nitzotzot total  : {nitz.get('total', '?')}")
        lines.append(f"    Nitzotzot cycle  : {nitz.get('count', '?')}/288")
        lines.append(f"    Cycles Tikkun    : {nitz.get('cycle', '?')}")
        lines.append(f"    Adam Kadmon      : {conv.get('adam_kadmon_score', '?')}")
        soul = conv.get("soul_level", {})
        lines.append(f"    Niveau d'âme     : {soul.get('level', '?')}")
        if soul.get("details"):
            lines.append(f"    Détails          : {soul['details']}")
        lines.append("")

    # Hitbonenut
    hb = results.get("hitbonenut", {})
    if hb:
        lines.append("  HITBONENUT (Auto-Exercice Contemplatif)")
        if "error" in hb:
            lines.append(f"    ERREUR: {hb['error']}")
        else:
            sess = hb.get("session", {})
            prog = hb.get("progress", {})
            if sess:
                lines.append(f"    Questions posées  : {sess.get('questions_asked', 0)}")
                lines.append(f"    Réponses          : {sess.get('questions_answered', 0)}")
                lines.append(f"    Score moyen       : {sess.get('avg_score', '?')}")
                lines.append(f"    Durée             : {sess.get('duration', '?')}s")
                domains = sess.get("domains_covered", [])
                if domains:
                    lines.append(f"    Domaines couverts : {', '.join(domains[:8])}")
            if hb.get("targeted_domain"):
                lines.append(f"    Domaine ciblé     : {hb['targeted_domain']}")
            if hb.get("difficulty_scaled"):
                lines.append(f"    Difficulté scalée : oui")
            novel = hb.get("novel_question")
            if novel:
                lines.append(f"    Question novel    : {novel.get('question', '?')[:80]}")
                lines.append(f"    Novelty score     : {novel.get('novelty', '?')}")
            if prog:
                lines.append(f"    Compétence globale: {prog.get('overall_score', '?')}")
                lines.append(f"    Sessions totales  : {prog.get('sessions_total', '?')}")
                stag = prog.get("stagnant", [])
                if stag:
                    lines.append(f"    Domaines stagnants: {', '.join(stag[:5])}")
                impr = prog.get("improving", [])
                if impr:
                    lines.append(f"    En progression    : {', '.join(impr[:5])}")
        lines.append("")

    # Auto-improve
    ai = results.get("auto_improve", {})
    if ai:
        lines.append("  CHESED-DE-GEVURAH (Auto-Improve Nocturne)")
        if "error" in ai:
            lines.append(f"    ERREUR: {ai['error']}")
        elif ai.get("early_stop") and ai.get("cycles_run", 0) == 0:
            lines.append(f"    Skip: {ai.get('early_stop_reason', '?')}")
        else:
            lines.append(f"    Intention       : {ai.get('intention', '?')}")
            lines.append(f"    Cycles exécutés : {ai.get('cycles_run', 0)}")
            lines.append(f"    Acceptés        : {ai.get('accepted', 0)}")
            lines.append(f"    Rejetés         : {ai.get('rejected', 0)}")
            lines.append(f"    Nitzotzot       : {ai.get('nitzotzot', 0)}")
            lines.append(f"    Novelty moy.    : {ai.get('avg_novelty', 0)}")
            lines.append(f"    Sentiers        : {ai.get('sentiers_success', '?')}/{ai.get('sentiers_explored', '?')}")
            lines.append(f"    Soul level      : {ai.get('soul_level', '?')}")
            lines.append(f"    Adam Kadmon     : {ai.get('adam_kadmon_score', '?')}")
            stored = ai.get("stored_ids", [])
            if stored:
                lines.append(f"    Stockés dans EpisteMemory: {len(stored)}")
            if ai.get("early_stop"):
                lines.append(f"    Arrêt anticipé  : {ai.get('early_stop_reason')}")
        lines.append("")

    # InsightForge (Chokmah)
    iforge = results.get("insightforge", {})
    if iforge:
        lines.append("  CHOKMAH (InsightForge)")
        if "error" in iforge:
            lines.append(f"    ERREUR: {iforge['error']}")
        elif iforge.get("early_stop"):
            lines.append(f"    Skip: {iforge.get('early_stop_reason', '?')}")
        else:
            lines.append(f"    Questions générées : {iforge.get('questions_generated', 0)}")
            lines.append(f"    Sessions complétées: {iforge.get('sessions_completed', 0)}")
            lines.append(f"    Candidats totaux   : {iforge.get('total_candidates', 0)}")
            lines.append(f"    Insights validés   : {iforge.get('total_insights', 0)}")
            lines.append(f"    Rejetés            : {iforge.get('total_rejected', 0)}")
            lines.append(f"    Signaux émergence  : {iforge.get('emergence_signals', 0)}")
            diag = iforge.get("diagnosis", {})
            if diag:
                lines.append(f"    Diagnostic Ghagiel : {diag.get('level', '?')}")
                for issue in diag.get("issues", []):
                    lines.append(f"      ! {issue}")
            for sess in iforge.get("sessions", []):
                src = sess.get("source", "?")
                ins = sess.get("insights_found", 0)
                cand = sess.get("total_candidates", 0)
                pearl = sess.get("pearl_level", "?")
                lines.append(f"    [{src}] {ins} insights / {cand} candidats (pearl={pearl})")
                for insight in sess.get("insights", []):
                    desc = insight.get("description", "?")[:80]
                    nov = insight.get("novelty", "?")
                    lines.append(f"      * {desc} (novelty={nov})")
        lines.append("")

    # Chesed Analogies
    ca = results.get("chesed_analogies", {})
    if ca:
        lines.append("  CHESED (Analogies Cross-Domain)")
        if "error" in ca:
            lines.append(f"    ERREUR: {ca['error']}")
        else:
            lines.append(f"    Heuristiques     : {ca.get('heuristic_found', 0)}")
            lines.append(f"    LLM              : {ca.get('llm_found', 0)}")
            lines.append(f"    Stockées         : {ca.get('stored', 0)}")
            lines.append(f"    Doublons skippés : {ca.get('duplicates_skipped', 0)}")
            errs = ca.get("errors", [])
            if errs:
                for err in errs[:3]:
                    lines.append(f"    ! {err}")
        lines.append("")

    # Chesed → Tiferet : Open Questions (R2.7)
    eoq = results.get("explore_open_questions", {})
    if eoq:
        lines.append("  CHESED → TIFERET (Open Questions)")
        if "error" in eoq:
            lines.append(f"    ERREUR: {eoq['error']}")
        elif eoq.get("skipped"):
            lines.append(f"    SKIP: {eoq['skipped']}")
        else:
            lines.append(f"    Explorées        : {eoq.get('explored', 0)}")
            lines.append(f"    Résolues         : {eoq.get('resolved', 0)}")
            lines.append(f"    Connexions       : {eoq.get('connections_found', 0)}")
        lines.append("")

    # Binah Confounders
    bc = results.get("binah_confounders", {})
    if bc:
        lines.append("  BINAH (Confounders Contextuels)")
        if "error" in bc:
            lines.append(f"    ERREUR: {bc['error']}")
        else:
            lines.append(f"    Claims traités       : {bc.get('claims_processed', 0)}")
            lines.append(f"    Nouveaux confounders  : {bc.get('total_new_confounders', 0)}")
            lines.append(f"    Evidence élevée      : {bc.get('evidence_elevated', 0)}")
            if bc.get("errors", 0) > 0:
                lines.append(f"    Erreurs              : {bc['errors']}")
        lines.append("")

    be = results.get("binah_elevator", {})
    if be:
        lines.append("  BINAH (Evidence Elevator)")
        if "error" in be:
            lines.append(f"    ERREUR: {be['error']}")
        else:
            lines.append(f"    → observed_association   : {be.get('elevated_to_observed', 0)}")
            lines.append(f"    → probable_causation     : {be.get('elevated_to_probable', 0)}")
            lines.append(f"    → demonstrated_causation : {be.get('elevated_to_demonstrated', 0)}")
            after = be.get("after", {})
            if after:
                total = sum(after.values())
                elevated = total - after.get("correlation_only", 0)
                pct = elevated / total * 100 if total else 0
                lines.append(f"    Total élevé : {elevated}/{total} ({pct:.1f}%)")
            if be.get("errors", 0) > 0:
                lines.append(f"    Erreurs              : {be['errors']}")
        lines.append("")

    lines.append("=" * 60)
    ts = datetime.now().strftime("%H:%M:%S")
    lines.append(f"  Généré à {ts}")
    lines.append("=" * 60)

    text = "\n".join(lines)
    report_path.write_text(text, encoding="utf-8")
    log.info("Rapport quotidien écrit: %s", report_path)
    return str(report_path)


# ─── Omer Calibration ───────────────────────────────────────


def task_sofer_watcher() -> dict:
    """SoferWatcher — scanner les Sifrei Yesod pour YAML nouveaux ou modifiés.

    Toutes les 5 minutes, vérifie si des fichiers perek ont changé (via hash SHA256).
    Si oui, lance le pipeline sofer + embedder.
    """
    report = {"task": "sofer_watcher", "ingested": 0, "embedded": 0, "errors": 0}

    try:
        from sifrei_yesod.pipeline.sofer import Sofer
        sofer = Sofer(DB_URL)
        try:
            results = sofer.scan_and_ingest()
            report["ingested"] = sum(
                r.assertions_upserted for r in results if not r.skipped
            )
            report["errors"] = sum(1 for r in results if r.errors)

            # Generate ML embeddings for new content
            if report["ingested"] > 0:
                from sifrei_yesod.pipeline.embedder import Embedder
                embedder = Embedder(DB_URL)
                try:
                    counts = embedder.embed_all()
                    report["embedded"] = sum(counts.values())
                finally:
                    embedder.close()

            # Generate hybrid embeddings for any missing concepts
            try:
                from kabbalah.embed_sifrei import SifreiYesodEmbedder
                hybrid_embedder = SifreiYesodEmbedder(db_url=DB_URL)
                try:
                    hybrid_stats = hybrid_embedder.embed_new_concepts()
                    report["hybrid_embedded"] = hybrid_stats["embedded"]
                    report["hybrid_errors"] = hybrid_stats["errors"]
                finally:
                    hybrid_embedder.close()
            except Exception as e:
                log.warning("SoferWatcher hybrid embedding: %s", e)
                report["hybrid_error"] = str(e)
        finally:
            sofer.close()
    except Exception as e:
        log.warning("SoferWatcher: %s", e)
        report["error"] = str(e)

    return report


def task_concept_harvest(tree: dict) -> dict:
    """ConceptHarvester — Yesod-Pipeline pour concepts vivants.

    Extrait des concepts depuis 9 sources, filtre (Masakh),
    embed (ML+Kab+Gematria), stocke dans hybrid_embeddings.
    """
    report = {"task": "concept_harvest"}
    try:
        from kabbalah.concept_harvester import ConceptHarvester
        ch = ConceptHarvester(db_url=DB_URL)
        state = load_state()
        last_harvest = state.get("last_concept_harvest")
        if isinstance(last_harvest, (int, float)):
            from datetime import datetime, timezone
            last_harvest = datetime.fromtimestamp(last_harvest, tz=timezone.utc)
        result = ch.harvest(last_harvest=last_harvest)
        report.update(result)
        ch.close()
        log.info(
            "ConceptHarvester: %d harvested, %d deduped, %d pruned",
            result.get("harvested", 0),
            result.get("deduped", 0),
            result.get("pruned", 0),
        )
    except Exception as e:
        report["error"] = str(e)
        log.error("ConceptHarvester error: %s", e)
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
        # Le conflit en temps réel (elokit vs behamit) nourrit le diagnostic.
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


# ─── Main Loop ──────────────────────────────────────────────

_running = True


def _signal_handler(signum, frame):
    global _running
    log.info("Signal %d recu — arrêt propre...", signum)
    _running = False


def _record_task_to_beinoni(task_name: str, result: dict) -> None:
    """Enregistre chaque tâche daemon comme interaction BeinoniTracker.

    Chaque tâche daemon qui produit un résultat = une interaction de l'IA.
    Le Tanya distingue NefeshHaElokit (réflexion profonde) et NefeshHaBehamit
    (réaction rapide). Les tâches d'analyse et synthèse = elokit, les tâches
    de détection rapide = behamit.
    """
    # Skip si erreur ou aucun résultat utile
    if result.get("error"):
        return

    # Mapping : task → (dominant_soul, olam, complexity)
    TASK_MAP = {
        "insightforge":       ("elokit",  "briah",    0.7),
        "binah_confounders":  ("elokit",  "briah",    0.6),
        "binah_causal_graphs":("elokit",  "briah",    0.5),
        "binah_elevator":     ("elokit",  "briah",    0.6),
        "tiferet_synthesize": ("elokit",  "briah",    0.7),
        "gevurah_eval":       ("elokit",  "yetzirah", 0.5),
        "contradictions":     ("behamit", "yetzirah", 0.4),
        "chesed_analogies":   ("elokit",  "briah",    0.6),
    }

    mapping = TASK_MAP.get(task_name)
    if not mapping:
        return

    soul, olam, complexity = mapping

    # Compute response_score from task results
    score = 0.5
    if task_name == "insightforge":
        gen = result.get("questions_generated", 0)
        score = result.get("total_insights", 0) / max(gen, 1)
    elif task_name == "binah_confounders":
        proc = result.get("claims_processed", 0)
        score = result.get("total_new_confounders", 0) / max(proc, 1)
    elif task_name == "binah_elevator":
        score = min((
            result.get("elevated_to_observed", 0)
            + result.get("elevated_to_probable", 0)
            + result.get("elevated_to_demonstrated", 0)
        ) * 0.2, 1.0)
    elif task_name == "tiferet_synthesize":
        dom = result.get("domains_processed", 0)
        score = (result.get("syntheses", 0) + result.get("dissensus", 0)) / max(dom, 1)
    elif task_name == "gevurah_eval":
        score = result.get("avg_quality", 0.5)
    elif task_name == "contradictions":
        h = result.get("health", "unknown")
        score = {"consistent": 0.8, "tensions_detected": 0.5, "highly_divergent": 0.2}.get(h, 0.4)
    elif task_name == "chesed_analogies":
        score = min(result.get("analogies_found", 0) * 0.15, 1.0)

    score = max(0.0, min(1.0, score))

    try:
        from tanya.beinoni_tracker import BeinoniTracker
        tracker = BeinoniTracker(db_url=DB_URL)
        tracker.record_interaction(
            dominant_soul=soul,
            response_score=score,
            olam_used=olam,
            complexity_score=complexity,
            domain=task_name,
            query_snippet=f"daemon:{task_name}",
        )
    except Exception as e:
        log.debug("BeinoniTracker record %s: %s", task_name, e)


# ─── Helpers for daemon_tasks/exploration.py (full_tree convergence) ─────
# Restored after refactor Cycle 4 (15ec2aa) dropped them. Imported by
# daemon_tasks.exploration.task_explore_full_tree via `from daemon import ...`.


def _init_partzufim(tree: dict) -> dict:
    """Initialiser les 6 Partzufim depuis l'Arbre."""
    try:
        from main import init_partzufim_from_tree
        return init_partzufim_from_tree(tree)
    except Exception as e:
        log.warning("Partzufim init failed: %s", e)
        return {}


def _get_nitzotzot_state() -> dict:
    """Récupérer l'état des Nitzotzot depuis la DB."""
    from pool import get_conn
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM failuretoinsight_insights")
                total = cur.fetchone()[0]
        return {"count": total % 288, "cycle": total // 288, "total": total}
    except Exception as e:
        log.warning("Nitzotzot query failed: %s", e)
        return {"count": 0, "cycle": 0, "total": 0}


def _compute_ohr_ratio() -> dict:
    """Ratio Ohr Pnimi / Ohr Makif.

    Pnimi = insights intégrés (haute confiance, actifs)
    Makif = signaux périphériques (basse confiance ou non traités)
    """
    from pool import get_conn
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        COUNT(*) FILTER (
                            WHERE confidence >= 0.6
                              AND epistemic_status = 'active'
                        ) AS pnimi,
                        COUNT(*) FILTER (
                            WHERE confidence < 0.6
                               OR epistemic_status != 'active'
                        ) AS makif,
                        COUNT(*) AS total
                    FROM epistememory
                """)
                pnimi, makif, total = cur.fetchone()
        ratio = pnimi / makif if makif > 0 else (float("inf") if pnimi > 0 else 0.0)
        return {
            "pnimi": pnimi,
            "makif": makif,
            "total": total,
            "ratio": round(ratio, 3),
            "integration_rate": round(pnimi / total, 3) if total > 0 else 0.0,
        }
    except Exception as e:
        log.warning("Ohr ratio failed: %s", e)
        return {"pnimi": 0, "makif": 0, "ratio": 0.0, "error": str(e)}


def _compute_adam_kadmon_score(
    tree: dict,
    partzufim: dict,
    sentier_results: dict,
) -> float:
    """Score de fidélité Adam Kadmon — proximité au blueprint idéal.

    Pondération : 40% sentiers, 30% modules, 20% Partzufim, 10% Zivugim.
    """
    score = 0.0

    total = sentier_results.get("total", 22)
    successes = sentier_results.get("successes", 0)
    score += 0.4 * (successes / total if total > 0 else 0.0)

    healthy = 0
    module_count = 0
    for name, mod in tree.items():
        if mod is None:
            continue
        module_count += 1
        try:
            if hasattr(mod, "self_diagnose"):
                try:
                    diag = mod.self_diagnose(quick=True)
                except TypeError:
                    diag = mod.self_diagnose()
                lvl = diag.get("level", "") if isinstance(diag, dict) else ""
                if lvl in ("healthy", "ok", "active", "nogah"):
                    healthy += 1
        except Exception as e:
            log.warning("Module self_diagnose failed: %s", e)
    score += 0.3 * (healthy / module_count if module_count > 0 else 0.0)

    if partzufim:
        panim_count = 0
        overall_sum = 0.0
        n = 0
        for p in partzufim.values():
            try:
                state = p.assess()
                overall_sum += state.overall
                if p.orientation == "panim":
                    panim_count += 1
                n += 1
            except Exception as e:
                log.warning("Partzuf assess failed: %s", e)
        if n > 0:
            score += 0.2 * (0.5 * (overall_sum / n) + 0.5 * (panim_count / n))

    return round(score, 3)


def _assess_soul(tree: dict, partzufim: dict) -> dict:
    """Évaluer le niveau d'âme du système via NeshamotEngine."""
    try:
        from soul_levels import NeshamotEngine
        engine = NeshamotEngine()
        nitzotzot = _get_nitzotzot_state()
        assessment = engine.assess_soul_level(tree, nitzotzot, partzufim or None)
        return assessment.to_dict()
    except Exception as e:
        log.warning("Soul assessment failed: %s", e)
        return {"level": "nefesh", "error": str(e)}


def _filter_reserved_kwargs(data: dict, reserved: tuple[str, ...]) -> dict:
    """Retirer les clés réservées d'un dict de données.

    Utilisé par `_daemon_emit` pour dédupliquer les kwargs avant expansion
    via `**data` quand le call site a déjà un kwarg explicite du même nom
    (ex. `emit("daemon_task", task=task_name, **data)` où `data` peut
    contenir `task`). Retourne une copie — n'altère pas `data`.
    """
    return {k: v for k, v in data.items() if k not in reserved}


def run_cycle(state: dict, force_daily: bool = False) -> dict:
    """Exécuter un cycle du daemon. Retourne les résultats."""
    now = time.time()
    results = {}
    tree = None

    # ── SSE + JSONL helper ──
    def _daemon_emit(task_name, **data):
        try:
            from web.events import emit as _emit
            safe = _filter_reserved_kwargs(data, ("task",))
            _emit("daemon_task", task=task_name, **safe)
        except Exception as e:
            log.warning("SSE emit failed: %s", e)

    def _safe_emit_data(result: dict) -> dict:
        """Extraire les champs serialisables d'un resultat de tache."""
        safe = {}
        for k, v in result.items():
            if isinstance(v, (str, int, float, bool, type(None))):
                safe[k] = v
            elif isinstance(v, list) and len(v) <= 10:
                safe[k] = v
        return safe

    # ── Governance Assessment (F405d, R2.9) ───────────────
    # Les 3 Gouverneurs (Teli/Galgal/Lev) évaluent la santé du système
    # et produisent des HINTS qui modulent les décisions du daemon.
    # Ce ne sont pas des hard overrides — ils influencent fréquence/priorité.
    gov_hints: dict = {
        "increase_karpathy": False,     # Teli < 0.4 → structure faible
        "prioritize_unexplored": False, # Galgal < 0.4 → déséquilibre temporel
        "conserve_resources": False,    # Lev < 0.4 → vitalité faible
        "harmony": 0.5,                # Score harmonique global
    }
    try:
        from kabbalah.governors import ThreeGovernors
        _gov = ThreeGovernors(tree=tree, db_url=DB_URL)
        _gov_state = _gov.assess_governance()

        gov_hints["harmony"] = _gov_state.harmony

        log.info(
            "Gouverneurs — Teli=%.2f Galgal=%.2f Lev=%.2f harmony=%.2f [%s]",
            _gov_state.teli.score,
            _gov_state.galgal.score,
            _gov_state.lev.score,
            _gov_state.harmony,
            _gov_state.message,
        )

        # Teli (structure) faible → augmenter fréquence Karpathy
        if _gov_state.teli.score < 0.4:
            gov_hints["increase_karpathy"] = True
            log.info(
                "Gov hint: Teli=%.2f < 0.4 — structure faible, "
                "Karpathy loop frequency increased",
                _gov_state.teli.score,
            )

        # Galgal (temps) faible → prioriser domaines sous-explorés
        if _gov_state.galgal.score < 0.4:
            gov_hints["prioritize_unexplored"] = True
            log.warning(
                "Gov hint: Galgal=%.2f < 0.4 — déséquilibre temporel, "
                "priorité aux domaines sous-explorés",
                _gov_state.galgal.score,
            )

        # Lev (vitalité) faible → réduire la charge, conserver les ressources
        if _gov_state.lev.score < 0.4:
            gov_hints["conserve_resources"] = True
            log.warning(
                "Gov hint: Lev=%.2f < 0.4 — vitalité faible, "
                "tâches optionnelles réduites pour conserver les ressources",
                _gov_state.lev.score,
            )

        if _gov_state.harmony > 0.7:
            log.info("Gov: harmonie > 0.7 — opération normale")

        _daemon_emit("governance", **_gov_state.to_dict())

    except Exception as _gov_err:
        # Governor failure must NOT break the daemon
        log.debug("Governance assessment failed (non-fatal): %s", _gov_err)

    try:
        # ── SoferWatcher (toutes les 5 minutes) ─────────────
        if now - state.get("last_sofer", 0) >= INTERVAL_SOFER:
            log.info("--- Cycle SoferWatcher ---")
            _daemon_emit("sofer_watcher", status="running")
            results["sofer_watcher"] = task_sofer_watcher()
            _daemon_emit("sofer_watcher_done", **_safe_emit_data(results["sofer_watcher"]))
            state["last_sofer"] = now
            if results["sofer_watcher"].get("ingested", 0) > 0:
                log.info("SoferWatcher: %d assertions ingérées, %d embeddings",
                         results["sofer_watcher"]["ingested"],
                         results["sofer_watcher"]["embedded"])

        # ── ConceptHarvester — Yesod-Pipeline ─────────────
        _daemon_emit("concept_harvest", status="running")
        results["concept_harvest"] = task_concept_harvest(tree)
        _daemon_emit("concept_harvest_done", **_safe_emit_data(results["concept_harvest"]))
        _record_task_to_beinoni("concept_harvest", results["concept_harvest"])
        state["last_concept_harvest"] = now

        # ── Din Monitor / Sitra Achra (toutes les 30 min) ────
        # Tamid (Tanya ch. 27) : surveillance DEFENSIVE permanente
        # de la rigueur interne de chaque module. Si défaillance
        # détectée → instanciation réactive du Sitra Achra.
        if now - state.get("last_din_monitor", 0) >= INTERVAL_DIN_MONITOR:
            log.info("--- Cycle Din Monitor (tamid) ---")
            _daemon_emit("din_monitor", status="running")
            try:
                from sitra_achra.din_monitor import task_din_monitor
                din_result = task_din_monitor(DB_URL)
                results["din_monitor"] = din_result.to_dict()
                _daemon_emit("din_monitor_done", **_safe_emit_data(din_result.to_dict()))

                if din_result.sitra_achra_triggered:
                    log.warning(
                        "Din Monitor → Sitra Achra RÉACTIF sur : %s",
                        ", ".join(din_result.targets),
                    )
                    _daemon_emit("sitra_achra_triggered", targets=din_result.targets)

                    # Instancier le Sitra Achra réactif
                    from sitra_achra.samael_coordinator import SamaelCoordinator
                    from sitra_achra.itaruta import Itaruta

                    samael = SamaelCoordinator(DB_URL)
                    itaruta = Itaruta(DB_URL)
                    from sitra_achra.budget_parasitaire import BudgetParasitaire
                    bp = BudgetParasitaire()

                    for target in din_result.targets:
                        if not bp.can_run():
                            log.info("Sitra Achra: budget épuisé, arrêt")
                            break

                        # Extraire les anomalies du rapport pour ce module
                        target_report = next(
                            (r for r in din_result.reports if r.module == target),
                            None,
                        )
                        if not target_report:
                            continue

                        anomalies = [a.to_dict() if hasattr(a, 'to_dict') else {
                            "qliphah": a.qliphah, "description": a.description,
                            "severity": a.severity, "metric_name": a.metric_name,
                            "metric_value": a.metric_value, "threshold": a.threshold,
                        } for a in target_report.anomalies]

                        # Round complet : plan → execute → report
                        sa_report = samael.run_full_round(target, anomalies)
                        results[f"sitra_achra_{target}"] = sa_report.to_dict()

                        # Itaruta : auto-diagnostic ascendant
                        if itaruta.should_trigger(sa_report.results):
                            itaruta_report = itaruta.auto_diagnostic(target, sa_report.results)
                            log.info(
                                "Itaruta [%s]: %d failles reconnues → %s",
                                target, itaruta_report.flaw_count,
                                itaruta_report.help_request[:80],
                            )
                            _daemon_emit("itaruta", module=target,
                                         flaw_count=itaruta_report.flaw_count)

                            # Teshuvah : convertir les failles en tests de régression
                            if itaruta_report.teshuvah_records:
                                try:
                                    from sitra_achra.teshuvah_writer import (
                                        process_teshuvah_records,
                                        store_teshuvah_in_db,
                                    )
                                    tw_results = process_teshuvah_records(
                                        itaruta_report.teshuvah_records,
                                    )
                                    written = sum(1 for r in tw_results if r.written)
                                    if written > 0:
                                        store_teshuvah_in_db(tw_results, DB_URL)
                                        log.info(
                                            "Teshuvah [%s]: %d faille(s) → tests de régression",
                                            target, written,
                                        )
                                        _daemon_emit("teshuvah", module=target,
                                                     tests_written=written)
                                except Exception as te:
                                    log.warning("Teshuvah writer error: %s", te)

                        # Budget : nourrir le SA avec les failles trouvées
                        bp.consume(sa_report.budget_consumed)
                        if sa_report.critical_flaws > 0:
                            bp.register_flaw(sa_report.critical_flaws)

                else:
                    log.info("Din Monitor: tous les modules sains — Sa'ir la-Azazel")

            except Exception as e:
                log.error("Din Monitor error: %s", e)
                results["din_monitor"] = {"error": str(e)}

            state["last_din_monitor"] = now

        # ── Netzach (toutes les heures) ──────────────────────
        if now - state["last_netzach"] >= INTERVAL_NETZACH:
            log.info("--- Cycle Netzach (horaire) ---")
            _daemon_emit("netzach", status="running")
            tree = tree or _init_tree()
            results["netzach"] = task_netzach(tree)
            _daemon_emit("netzach_done", **_safe_emit_data(results["netzach"]))
            state["last_netzach"] = now

            # ── BeinoniTracker — surveillance du profil temporel ──
            try:
                results["beinoni"] = task_beinoni_check()
                beinoni_r = results["beinoni"]
                if beinoni_r.get("regression"):
                    _daemon_emit("beinoni_regression",
                                 **_safe_emit_data(beinoni_r))
                    log.warning("RÉGRESSION BEINONI: Δ=%s — %s",
                                beinoni_r["regression"]["delta"],
                                beinoni_r.get("teshuvah", "")[:80])
                elif beinoni_r.get("elevation"):
                    _daemon_emit("beinoni_elevation",
                                 **_safe_emit_data(beinoni_r))
                    log.info("ÉLÉVATION BEINONI: Δ=%s",
                             beinoni_r["elevation"]["delta"])
            except Exception as e:
                log.debug("BeinoniTracker: %s", e)

            # ── Tzimtzum detection (avec Netzach) ──
            results["tzimtzum"] = task_tzimtzum_detect(tree)
            if results["tzimtzum"].get("triggered"):
                _daemon_emit("tzimtzum", **_safe_emit_data(results["tzimtzum"]))

        # ── Partzufim regulation (horaire) ───────────────────
        # Deuxième étage au-dessus du Tzimtzum : variateur analogique.
        # Vérifie les transitions katnut↔gadlut avec hystérésis.
        if now - state.get("last_partzuf_reg", 0) >= INTERVAL_PARTZUF_REG:
            log.info("--- Cycle Partzufim Regulation (horaire) ---")
            _daemon_emit("partzuf_regulation", status="running")
            tree = tree or _init_tree()

            # Bridge I2 : AutoJudge → Partzufim (push récent sur Zeir Anpin)
            # Précède la régulation pour qu'elle voie l'état à jour.
            try:
                results["autojudge_to_partzuf"] = task_autojudge_to_partzuf(tree)
                if results["autojudge_to_partzuf"].get("transition"):
                    _daemon_emit("autojudge_to_partzuf",
                                 **_safe_emit_data(results["autojudge_to_partzuf"]))
            except Exception as e:
                log.debug("autojudge_to_partzuf: %s", e)

            # Bridge I2 : BeinoniTracker → SelfMap (signal par domaine)
            try:
                results["beinoni_to_selfmap"] = task_beinoni_to_selfmap(tree)
                if results["beinoni_to_selfmap"].get("domains_updated"):
                    _daemon_emit("beinoni_to_selfmap",
                                 **_safe_emit_data(results["beinoni_to_selfmap"]))
            except Exception as e:
                log.debug("beinoni_to_selfmap: %s", e)

            results["partzuf_regulation"] = task_partzuf_regulation(tree)
            _daemon_emit("partzuf_regulation_done",
                         **_safe_emit_data(results["partzuf_regulation"]))
            state["last_partzuf_reg"] = now
            if results["partzuf_regulation"].get("transitions"):
                for t in results["partzuf_regulation"]["transitions"]:
                    log.info("  Partzuf %s: %s → %s", t["partzuf"], t["from"], t["to"])

            # ── MazalEngine — Auto-rectification doctrinale (Sprint 9) ─
            # 2 Mazalot pilot (Notzer Chesed + Ve-Nakeh) surveillent les
            # écarts doctrinaux et émettent des Tikkunim observables.
            # Doctrine : EC-K5-001 (Sha'ar HaKlalim 5:1). Ne modifie
            # JAMAIS partzufim_state (Hitlabshut EC-K5-008).
            try:
                from mazalengine import MazalEngine
                _mazal_events = MazalEngine().run(tree)
                for _ev in _mazal_events:
                    _daemon_emit("mazal_tikkun", **_ev)
                if _mazal_events:
                    log.info("MazalEngine: %d tikkun(im) émis", len(_mazal_events))
            except Exception as _exc_mazal:
                log.debug("MazalEngine: %s", _exc_mazal)

        # ── Orphan validation (6h) — Sprint 5.6 ──────────────
        # Ferme la boucle Chokmah → Binah → Da'at : retro-patche
        # connects_domains et valide les pending hitbonenut créés
        # avant Sprint 5.3/5.5 (format Q/A + connects_domains).
        if now - state.get("last_orphan_validation", 0) >= INTERVAL_VALIDATE_ORPHAN:
            log.info("--- Cycle Orphan Validation (6h, Sprint 5.6) ---")
            _daemon_emit("orphan_validation", status="running")
            try:
                results["orphan_validation"] = task_validate_orphan_candidates(tree)
                _daemon_emit(
                    "orphan_validation_done",
                    **_safe_emit_data(results["orphan_validation"]),
                )
            except Exception as e:
                log.warning("orphan_validation error: %s", e)
                results["orphan_validation"] = {"error": str(e)}
            state["last_orphan_validation"] = now

        # ── Hitbonenut continu : démarrage PRÉCOCE ──────────
        # Lancé AVANT les tâches quotidiennes pour ne pas être bloqué
        # par des tâches longues (binah confounders, etc.)
        _hitb_hour = datetime.now().hour
        _hitb_minute = datetime.now().minute
        _hitb_in_karpathy = _in_karpathy_window(_hitb_hour, _hitb_minute)
        from pause_state import is_paused as _is_paused
        _hitb_paused = _is_paused("hitbonenut")

        log.info(
            "Hitbonenut check: runner.is_running=%s, in_karpathy=%s, paused=%s, "
            "thread=%s, hour=%d:%02d",
            _hitbonenut_runner.is_running, _hitb_in_karpathy, _hitb_paused,
            _hitbonenut_runner._thread, _hitb_hour, _hitb_minute,
        )

        if _hitb_paused and _hitbonenut_runner.is_running:
            log.info("Hitbonenut PAUSED — stopping runner")
            _hitbonenut_runner.stop()
            _daemon_emit("hitbonenut_paused")

        if not _hitbonenut_runner.is_running and not _hitb_in_karpathy and not _hitb_paused:
            log.info("--- Hitbonenut continu: démarrage (heure=%d:%02d) ---",
                     _hitb_hour, _hitb_minute)
            tree = tree or _init_tree()
            _daemon_emit("hitbonenut_continuous_start")
            _hitbonenut_runner.start(tree)
            state["last_hitbonenut"] = now
            # Sauver immédiatement pour que le web voie hitbonenut_running=True
            save_state(state)

        # ── Karpathy / Auto-improve (PRIORITAIRE, fenêtre 23h-0h30) ──
        # Placé AVANT le cycle quotidien pour ne pas être bloqué par
        # les tâches lourdes (InsightForge, ConfounderDetector ~10min).
        _karp_hour = datetime.now().hour
        _karp_minute = datetime.now().minute
        _in_karpathy_window_now = _in_karpathy_window(_karp_hour, _karp_minute)
        from pause_state import is_paused as _is_paused
        _karpathy_paused = _is_paused("karpathy")
        _hitbonenut_paused = _is_paused("hitbonenut")

        if _karpathy_paused:
            log.info("Karpathy PAUSED — skipping")

        _last_improve = state.get("last_auto_improve", 0)
        _improve_age = now - _last_improve if _last_improve else float("inf")
        # Gov hint: Teli faible → Karpathy plus fréquent (12h au lieu de 24h)
        _karpathy_interval = INTERVAL_DAILY // 2 if gov_hints["increase_karpathy"] else INTERVAL_DAILY
        _improve_due = (
            _in_karpathy_window_now
            and _improve_age >= _karpathy_interval
            and not _karpathy_paused
        )

        log.info(
            "Karpathy check: window=%s, age=%.0fs (need %ds%s), paused=%s → due=%s",
            _in_karpathy_window_now, _improve_age, _karpathy_interval,
            " [gov:boosted]" if gov_hints["increase_karpathy"] else "",
            _karpathy_paused, _improve_due,
        )

        if _improve_due or (force_daily and not _karpathy_paused):
            # Pause Hitbonenut pour le Karpathy Loop
            if _hitbonenut_runner.is_running:
                log.info("Pause Hitbonenut continu pour Karpathy Loop (heure=%d:%02d)",
                         _karp_hour, _karp_minute)
                _hitbonenut_runner.stop()
                _daemon_emit("hitbonenut_continuous_pause")

            log.info("--- Auto-improve nocturne (Karpathy, heure=%d:%02d) ---",
                     _karp_hour, _karp_minute)
            state["karpathy_running"] = True
            save_state(state)
            tree = tree or _init_tree()

            # Full Tree exploration AVANT auto-improve
            _daemon_emit("full_tree", detail="Exploration 22 sentiers + Zivugim")
            log.info("--- Exploration Arbre Complet (22 sentiers) ---")
            results["full_tree"] = task_explore_full_tree(tree)

            ft = results["full_tree"]
            _daemon_emit("full_tree_done",
                         successes=ft.get("sentiers", {}).get("successes", 0),
                         failures=ft.get("sentiers", {}).get("failures", 0),
                         zivugim=ft.get("zivugim", {}).get("pairs_tested", 0))

            # Auto-improve avec contexte Full Tree
            _daemon_emit("auto_improve", detail="Karpathy Loop démarré",
                         status="running")
            cfg = load_daemon_config()
            results["auto_improve"] = task_auto_improve(
                tree, full_tree_context=results["full_tree"],
            )
            state["last_auto_improve"] = now

            ai = results["auto_improve"]
            _daemon_emit("auto_improve_done",
                         cycles=ai.get("cycles_run", 0),
                         accepted=ai.get("accepted", 0),
                         rejected=ai.get("rejected", 0),
                         nitzotzot=ai.get("nitzotzot", 0),
                         avg_novelty=ai.get("avg_novelty", 0.0))

            # Après Karpathy : reprendre le Hitbonenut (sauf si pausé)
            state["karpathy_running"] = False
            log.info("Karpathy terminé — reprise du Hitbonenut continu")
            _daemon_emit("karpathy_done", detail="Exploration nocturne terminée")
            if not _hitbonenut_paused:
                _daemon_emit("hitbonenut_continuous_resume")
                _hitbonenut_runner.start(tree)
                state["last_hitbonenut"] = now
            else:
                log.info("Hitbonenut PAUSED — skipping post-Karpathy resume")

            save_state(state)

        # En fenêtre Karpathy sans auto-improve : pause Hitbonenut
        elif _in_karpathy_window_now and _hitbonenut_runner.is_running:
            log.info("Fenêtre Karpathy active — pause Hitbonenut (heure=%d:%02d)",
                     _karp_hour, _karp_minute)
            _hitbonenut_runner.stop()
            _daemon_emit("hitbonenut_continuous_pause")

        # ── Tâches quotidiennes ──────────────────────────────
        daily_due = (now - state["last_gc"] >= INTERVAL_DAILY) or force_daily

        if daily_due:
            log.info("--- Cycle quotidien ---")
            tree = tree or _init_tree()

            # ── Omer Daily Influence — moduler les seuils du jour ──
            try:
                from omer.daily_influence import OmerDailyInfluence
                _omer_daily = OmerDailyInfluence()
                _omer_influence = _omer_daily.get_today_influence()
                if _omer_influence:
                    omer_changes = _omer_daily.apply_to_modules(tree, _omer_influence)
                    log.info("Omer jour %d/49 — %s — %d module(s) modulé(s)",
                             _omer_influence.day, _omer_influence.combination,
                             len(omer_changes))
                    _daemon_emit("omer_daily",
                                 day=_omer_influence.day,
                                 combination=_omer_influence.combination,
                                 combination_hebrew=_omer_influence.combination_hebrew,
                                 primary=_omer_influence.primary_sefirah,
                                 secondary=_omer_influence.secondary_sefirah,
                                 kavvanah=_omer_influence.kavvanah,
                                 changes={k: v for k, v in omer_changes.items()})
                else:
                    log.debug("Omer: hors période de l'Omer")
            except Exception as e:
                log.debug("Omer daily influence: %s", e)

            # Atzvut — Entrer en mode Vidouï (rapport quotidien)
            # Le Tanya (ch. 26) : les diagnostics complets sont bienvenus
            # uniquement pendant le Vidouï, pas pendant le travail.
            try:
                from tanya.atzvut import AtzvutManager as _AM
                _atzvut_mgr = _AM()
                _atzvut_mgr.enter_vidui()
            except Exception as e:
                log.warning("AtzvutManager enter_vidui failed: %s", e)
                _atzvut_mgr = None

            # GC Yesod
            _daemon_emit("gc", status="running")
            results["gc"] = task_gc(tree)
            _daemon_emit("gc_done", **_safe_emit_data(results["gc"]))
            state["last_gc"] = now

            # Log retention — purge des tables à croissance non bornée
            _daemon_emit("log_retention", status="running")
            results["log_retention"] = task_log_retention(tree)
            _daemon_emit("log_retention_done",
                         **_safe_emit_data(results["log_retention"]))

            # Snapshot Da'at
            _daemon_emit("snapshot", status="running")
            results["snapshot"] = task_snapshot(tree)
            _daemon_emit("snapshot_done", **_safe_emit_data(results["snapshot"]))
            state["last_snapshot"] = now

            # Da'at Predict (après snapshot)
            _daemon_emit("daat_predict", status="running")
            results["daat_predict"] = task_daat_predict(tree)
            _daemon_emit("daat_predict_done", **_safe_emit_data(results["daat_predict"]))
            state["last_daat_predict"] = now

            # Da'at Verify — Or Chozer : vérifier les prédictions passées
            _daemon_emit("daat_verify", status="running")
            results["daat_verify"] = task_daat_verify(tree)
            _daemon_emit("daat_verify_done", **_safe_emit_data(results["daat_verify"]))

            # Da'at Correct — Tikkun : corriger les biais haute sévérité
            _daemon_emit("daat_correct", status="running")
            results["daat_correct"] = task_daat_correct_biases(tree)
            _daemon_emit("daat_correct_done", **_safe_emit_data(results["daat_correct"]))

            # Da'at Maintenance — nettoyage predictions stale (audit F01/R6)
            _daemon_emit("selfmodel_maintenance", status="running")
            results["selfmodel_maintenance"] = task_selfmodel_maintenance(tree)
            _daemon_emit("selfmodel_maintenance_done",
                         **_safe_emit_data(results["selfmodel_maintenance"]))

            # Contradictions Tiferet
            _daemon_emit("contradictions", status="running")
            results["contradictions"] = task_contradictions(tree)
            _daemon_emit("contradictions_done", **_safe_emit_data(results["contradictions"]))
            _record_task_to_beinoni("contradictions", results["contradictions"])
            state["last_contradictions"] = now

            # Tiferet Synthesize — récolte + synthèse/dissensus
            _daemon_emit("tiferet_synthesize", status="running")
            results["tiferet_synthesize"] = task_tiferet_synthesize(tree)
            _daemon_emit("tiferet_synthesize_done",
                         **_safe_emit_data(results["tiferet_synthesize"]))
            _record_task_to_beinoni("tiferet_synthesize", results["tiferet_synthesize"])
            state["last_tiferet_synthesize"] = now

            # Gevurah Eval — évaluation des réponses Hitbonenut
            _daemon_emit("gevurah_eval", status="running")
            results["gevurah_eval"] = task_gevurah_eval(tree)
            _daemon_emit("gevurah_eval_done",
                         **_safe_emit_data(results["gevurah_eval"]))
            _record_task_to_beinoni("gevurah_eval", results["gevurah_eval"])

            # ── Chaîne : Gevurah rejets → FailureToInsight ──
            # Les réponses rejetées par Gevurah nourrissent le Birur :
            # le Lamed (FailureToInsight) extrait les Nitzotzot des Qliphoth.
            # Les insights extraits alimenteront InsightForge via _generate_forge_questions.
            gevurah_rejected = results["gevurah_eval"].get("rejected", 0)
            if gevurah_rejected > 0 and not results["gevurah_eval"].get("error"):
                try:
                    _recycle_rejections_to_fti(tree, batch_limit=10)
                except Exception as e:
                    log.warning("Rejection→FTI recycling failed: %s", e)

            # InsightForge (Chokmah) — forge d'insights quotidienne
            # Nourri en amont par FailureToInsight (via _generate_forge_questions)
            _daemon_emit("insightforge", status="running")
            results["insightforge"] = task_insightforge(tree)
            _daemon_emit("insightforge_done", **_safe_emit_data(results["insightforge"]))
            _record_task_to_beinoni("insightforge", results["insightforge"])
            state["last_insightforge"] = now

            # ── Chaîne : InsightForge rejets (Triple Validation) → FailureToInsight ──
            # Les candidate_insights.status='rejected' (Binah/Gevurah/Da'at) passent
            # aussi par Lamed pour Birur. Batch limité à 20 par cycle (rate limit).
            # Idempotence : (source_type='hypothesis', source_id=ci.id).
            try:
                recycled = _recycle_candidate_rejections_to_fti(
                    tree, batch_limit=20,
                )
                if recycled:
                    _daemon_emit(
                        "candidate_rejections_to_fti",
                        recycled=recycled,
                    )
            except Exception as e:
                log.warning("Candidate rejection→FTI recycling failed: %s", e)

            # Bridge I2 : InsightForge → SelfModel (ingestion des insights validés)
            try:
                results["insightforge_to_selfmodel"] = (
                    task_insightforge_to_selfmodel(tree)
                )
                if results["insightforge_to_selfmodel"].get("fed"):
                    _daemon_emit(
                        "insightforge_to_selfmodel",
                        **_safe_emit_data(results["insightforge_to_selfmodel"]),
                    )
            except Exception as e:
                log.debug("insightforge_to_selfmodel: %s", e)

            # ── Gov hint: Lev faible → skip optional exploration tasks ──
            if gov_hints["conserve_resources"]:
                log.info("Gov: Lev faible — skip chesed_analogies, cube_insights, "
                         "tzeruf_spatial (conservation des ressources)")
                _daemon_emit("governance_skip",
                             tasks="chesed_analogies,cube_insights,tzeruf_spatial",
                             reason="lev_low")
            else:
                # Chesed Analogies — détection de patterns cross-domain
                _daemon_emit("chesed_analogies", status="running")
                results["chesed_analogies"] = task_chesed_analogies(tree)
                _daemon_emit("chesed_analogies_done",
                             **_safe_emit_data(results["chesed_analogies"]))
                _record_task_to_beinoni("chesed_analogies", results["chesed_analogies"])

                # Chesed → Tiferet : explorer les open_questions (R2.7)
                _daemon_emit("explore_open_questions", status="running")
                results["explore_open_questions"] = task_explore_open_questions(tree)
                _daemon_emit("explore_open_questions_done",
                             **_safe_emit_data(results["explore_open_questions"]))
                _record_task_to_beinoni("explore_open_questions",
                                       results["explore_open_questions"])

                # Cube Insights — connexions cachées du Cube de l'Espace
                _daemon_emit("cube_insights", status="running")
                results["cube_insights"] = task_cube_insights(tree)
                _daemon_emit("cube_insights_done",
                             **_safe_emit_data(results["cube_insights"]))

                # Tzeruf Spatial 3D — géométrie des mots dans le Cube
                _daemon_emit("tzeruf_spatial", status="running")
                results["tzeruf_spatial"] = task_tzeruf_spatial(tree)
                _daemon_emit("tzeruf_spatial_done",
                             **_safe_emit_data(results["tzeruf_spatial"]))
                _record_task_to_beinoni("tzeruf_spatial", results["tzeruf_spatial"])

            # Clustering dual Kab vs ML — désaccords tradition/statistique
            _daemon_emit("clustering", status="running")
            results["clustering"] = task_clustering(tree)
            _daemon_emit("clustering_done",
                         **_safe_emit_data(results["clustering"]))
            state["last_clustering"] = now

            # Binah Confounders — enrichissement contextuel LLM
            _daemon_emit("binah_confounders", status="running")
            results["binah_confounders"] = task_binah_confounders(tree)
            _daemon_emit("binah_confounders_done",
                         **_safe_emit_data(results["binah_confounders"]))
            _record_task_to_beinoni("binah_confounders", results["binah_confounders"])
            state["last_binah_confounders"] = now

            # Binah Causal Graphs — construction du graphe global
            _daemon_emit("binah_causal_graphs", status="running")
            results["binah_causal_graphs"] = task_binah_causal_graphs(tree)
            _daemon_emit("binah_causal_graphs_done",
                         **_safe_emit_data(results["binah_causal_graphs"]))
            _record_task_to_beinoni("binah_causal_graphs", results["binah_causal_graphs"])

            # Binah Evidence Elevator — cristallisation des claims
            _daemon_emit("binah_elevator", status="running")
            results["binah_elevator"] = task_binah_evidence_elevator(tree)
            _daemon_emit("binah_elevator_done",
                         **_safe_emit_data(results["binah_elevator"]))
            _record_task_to_beinoni("binah_elevator", results["binah_elevator"])

            # Binah → Yesod — réinjection des claims causaux
            _daemon_emit("binah_to_yesod", status="running")
            results["binah_to_yesod"] = task_binah_to_yesod(tree)
            _daemon_emit("binah_to_yesod_done",
                         **_safe_emit_data(results["binah_to_yesod"]))

            # Masakh Health — surveillance du pipeline Sod HaKli
            _daemon_emit("masakh_health", status="running")
            results["masakh_health"] = task_masakh_health()
            _daemon_emit("masakh_health_done",
                         **_safe_emit_data(results["masakh_health"]))

            # ── Zivvug Abba v'Imma — renforcement mutuel ──
            try:
                from partzufim.zivvug import load_or_create_zivvug
                # Sprint 10 Phase E : factory canonique (Refactor L).
                zivvug = load_or_create_zivvug()

                # InsightForge a produit des insights → boost Imma
                insightforge_insights = results.get("insightforge", {}).get("total_insights", 0)
                if insightforge_insights > 0:
                    zivvug.mutual_reinforcement(insight_produced=True)
                    log.info("Zivvug: %d insights → Imma boosted", insightforge_insights)

                # Binah a enrichi des claims → boost Abba
                binah_elevated = results.get("binah_confounders", {}).get("evidence_elevated", 0)
                binah_confounders = results.get("binah_confounders", {}).get("total_new_confounders", 0)
                elevator_elevated = (
                    results.get("binah_elevator", {}).get("elevated_to_observed", 0)
                    + results.get("binah_elevator", {}).get("elevated_to_probable", 0)
                    + results.get("binah_elevator", {}).get("elevated_to_demonstrated", 0)
                )
                if binah_elevated > 0 or binah_confounders > 0 or elevator_elevated > 0:
                    zivvug.mutual_reinforcement(causal_validated=True)
                    log.info("Zivvug: %d elevated + %d confounders + %d crystallized → Abba boosted",
                             binah_elevated, binah_confounders, elevator_elevated)

                # ── Chaîne : Zivvug → zivvug_state persist ──
                # Sprint 8 D1 (EC-K5-008) : les boosts ne sont plus appliqués
                # directement sur partzufim_state.overall_score (viole Hitlabshut).
                # Ils sont persistés dans zivvug_state (couche Mem du Tzelem) et
                # consommés au prochain update_all_partzufim via cmd_ask/ohr_yashar
                # (Hitlabshut via facultés, couche Lamed, ΔOverall ≈ 0.02).

                # Persist Zivvug state + assessment
                try:
                    from partzufim.zivvug import save_zivvug_state
                    from partzufim.regulator import PartzufimRegulator
                    reg = PartzufimRegulator()
                    pstate = reg.load_state()
                    abba_s = pstate.get("abba", {}).get("overall", 0.5)
                    imma_s = pstate.get("imma", {}).get("overall", 0.5)
                    assessment = zivvug.assess_zivvug_state(abba_s, imma_s)
                    save_zivvug_state(zivvug, assessment)
                    log.info("Zivvug state saved: %s (mochin=%.3f)",
                             assessment.state.value, assessment.mochin_quality)
                except Exception as e_zs:
                    log.debug("Zivvug state save: %s", e_zs)

                # NB: ne PAS stocker l'objet zivvug dans state (non JSON-serialisable)
                # Sprint 8 D1 : emit les boosts courants (non-reset, persistés via
                # save_zivvug_state) pour traçage daemon_events.jsonl.
                _daemon_emit("zivvug", status="updated",
                             abba_boost=zivvug.abba_boost,
                             imma_boost=zivvug.imma_boost)
            except Exception as e:
                log.debug("Zivvug update: %s", e)

            # Stats mémoire (léger, pas besoin de l'Arbre)
            _daemon_emit("memory_stats", status="running")
            results["memory_stats"] = task_memory_stats()
            _daemon_emit("memory_stats_done", **_safe_emit_data(results["memory_stats"]))

            # Yesod maturation — promotion automatique des mémoires mûres
            _daemon_emit("yesod_mature", status="running")
            results["yesod_mature"] = task_yesod_mature(tree)
            _daemon_emit("yesod_mature_done", **_safe_emit_data(results["yesod_mature"]))

            # Sifrei Yesod → EpisteMemory — injection des concepts
            _daemon_emit("sifrei_to_yesod", status="running")
            results["sifrei_to_yesod"] = task_sifrei_to_yesod(tree)
            _daemon_emit("sifrei_to_yesod_done", **_safe_emit_data(results["sifrei_to_yesod"]))

            # Dira BeTachtonim + Birur Nogah — stats quotidiennes
            _daemon_emit("dira_birur", status="running")
            results["dira_birur"] = task_dira_birur_stats(tree)
            _daemon_emit("dira_birur_done", **_safe_emit_data(results["dira_birur"]))

            # ── Omer Calibration (hebdomadaire, vérifié dans le cycle quotidien) ──
            # Garde DB : vérifier la fraîcheur de l'Omer indépendamment
            # de l'état in-memory (qui se perd au redémarrage du daemon).
            omer_stale_days = 0.0
            try:
                from pool import get_conn, init_pool
                init_pool(DB_URL)  # idempotent
                with get_conn() as _omer_conn:
                    with _omer_conn.cursor() as _omer_cur:
                        _omer_cur.execute(
                            "SELECT EXTRACT(EPOCH FROM NOW() - max(applied_at)) / 86400.0 "
                            "FROM omer_history"
                        )
                        row = _omer_cur.fetchone()
                        omer_stale_days = row[0] if row and row[0] else 999.0
            except Exception as e_omer_check:
                log.debug("Omer staleness check: %s", e_omer_check)
                omer_stale_days = 999.0

            if omer_stale_days > 7.0:
                log.warning(
                    "OMER STALE — dernière calibration il y a %.1f jours "
                    "(seuil: 7j). Forçage de la calibration.",
                    omer_stale_days,
                )

            omer_due = (
                (now - state.get("last_omer", 0) >= INTERVAL_OMER)
                or force_daily
                or omer_stale_days > 7.0
            )
            if omer_due:
                log.info("--- Sefirat haOmer (hebdomadaire) ---")
                _daemon_emit("omer", status="running")
                results["omer"] = task_omer_calibrate()
                _daemon_emit("omer_done", **_safe_emit_data(results["omer"]))
                state["last_omer"] = now

            # ── External Scan (hebdomadaire — Promptfoo + Garak) ──
            scan_due = (now - state.get("last_external_scan", 0) >= INTERVAL_EXTERNAL_SCAN)
            if scan_due:
                log.info("--- Scan externe hebdomadaire (Promptfoo + Garak) ---")
                _daemon_emit("external_scan", status="running")
                try:
                    from sitra_achra.external_scanner import task_external_scan
                    scan_results = task_external_scan(DB_URL)
                    results["external_scan"] = scan_results

                    # Alerter sur les regressions
                    for scanner in ("promptfoo", "garak"):
                        reg_key = f"{scanner}_regression"
                        if reg_key in scan_results:
                            reg = scan_results[reg_key]
                            log.warning(
                                "REGRESSION %s: %d → %d failles (+%d)",
                                scanner, reg["prev_flaws"],
                                reg["curr_flaws"], reg["delta_flaws"],
                            )
                            _daemon_emit("external_scan_regression",
                                         scanner=scanner, **reg)

                    _daemon_emit("external_scan_done",
                                 **_safe_emit_data(scan_results))
                except Exception as e:
                    log.error("External scan error: %s", e)
                    results["external_scan"] = {"error": str(e)}

                state["last_external_scan"] = now

            # Atzvut — Sortir du mode Vidouï
            if _atzvut_mgr:
                _atzvut_mgr.exit_vidui()

            # Rapport (sera réécrit après auto-improve si lancé)
            write_daily_report(results)
            _daemon_emit("report_written")
            state["last_report"] = now

        # (Karpathy check already done above, before daily tasks)

    except Exception as e:
        log.error("Erreur cycle: %s\n%s", e, traceback.format_exc())
        results["cycle_error"] = str(e)
    finally:
        # Ne PAS libérer l'arbre si le Hitbonenut continu tourne (il en a besoin)
        if tree and not _hitbonenut_runner.is_running:
            try:
                _close_tree(tree)
            except Exception as e:
                log.warning("_close_tree failed: %s", e)
            log.info("Arbre libéré.")
        elif tree and _hitbonenut_runner.is_running:
            log.debug("Arbre conservé (Hitbonenut continu actif)")

    # Persist governance hints in state for dashboard visibility
    state["gov_hints"] = gov_hints
    save_state(state)
    return results


def run_single_task(task_name: str) -> None:
    """Exécuter une tâche unique."""
    tree = _init_tree()
    try:
        if task_name == "netzach":
            r = task_netzach(tree)
        elif task_name == "gc":
            r = task_gc(tree)
        elif task_name == "log-retention":
            r = task_log_retention(tree)
        elif task_name == "snapshot":
            r = task_snapshot(tree)
        elif task_name == "daat-predict":
            r = task_daat_predict(tree)
        elif task_name == "contradictions":
            r = task_contradictions(tree)
        elif task_name == "tiferet-synthesize":
            r = task_tiferet_synthesize(tree)
        elif task_name == "hitbonenut":
            r = task_hitbonenut(tree)
        elif task_name == "full-tree":
            r = task_explore_full_tree(tree)
        elif task_name == "auto-improve":
            ft = task_explore_full_tree(tree)
            r = task_auto_improve(tree, full_tree_context=ft)
        elif task_name == "insightforge":
            r = task_insightforge(tree)
        elif task_name == "binah-confounders":
            r = task_binah_confounders(tree)
        elif task_name == "binah-graphs":
            r = task_binah_causal_graphs(tree)
        elif task_name == "binah-elevator":
            r = task_binah_evidence_elevator(tree)
        elif task_name == "gevurah-eval":
            r = task_gevurah_eval(tree)
        elif task_name == "omer":
            r = task_omer_calibrate()
        elif task_name == "clustering":
            r = task_clustering(tree)
        elif task_name == "selfmodel-maintenance":
            r = task_selfmodel_maintenance(tree)
        elif task_name == "sofer":
            r = task_sofer_watcher()
        elif task_name == "report":
            ft = task_explore_full_tree(tree)
            results = {
                "netzach": task_netzach(tree),
                "gc": task_gc(tree),
                "log_retention": task_log_retention(tree),
                "snapshot": task_snapshot(tree),
                "daat_predict": task_daat_predict(tree),
                "contradictions": task_contradictions(tree),
                "tiferet_synthesize": task_tiferet_synthesize(tree),
                "memory_stats": task_memory_stats(),
                "yesod_mature": task_yesod_mature(tree),
                "hitbonenut": task_hitbonenut(tree),
                "full_tree": ft,
                "auto_improve": task_auto_improve(tree, full_tree_context=ft),
                "insightforge": task_insightforge(tree),
                "binah_confounders": task_binah_confounders(tree),
                "binah_causal_graphs": task_binah_causal_graphs(tree),
                "binah_elevator": task_binah_evidence_elevator(tree),
                "gevurah_eval": task_gevurah_eval(tree),
                "omer": task_omer_calibrate(),
            }
            path = write_daily_report(results)
            print(f"Rapport: {path}")
            return
        else:
            print(f"Tâche inconnue: {task_name}")
            print("Disponibles: netzach, gc, log-retention, snapshot, "
                  "daat-predict, contradictions, tiferet-synthesize, "
                  "hitbonenut, full-tree, auto-improve, insightforge, "
                  "binah-confounders, binah-graphs, binah-elevator, "
                  "gevurah-eval, sofer, omer, report")
            return
        print(json.dumps(r, indent=2, default=str))
    finally:
        _close_tree(tree)


HEARTBEAT_INTERVAL = 10  # secondes entre heartbeats

# Auto-restart : backoff exponentiel après crash
MAX_CONSECUTIVE_CRASHES = 5
CRASH_BACKOFF_BASE = 10  # secondes — 10, 20, 40, 80, 160


def _emit_heartbeat():
    """Emettre un heartbeat JSONL pour que le dashboard sache que le daemon vit."""
    try:
        from web.events import emit as _emit
        _emit("daemon_heartbeat",
              pid=os.getpid(),
              hitbonenut_running=_hitbonenut_runner.is_running,
              uptime_s=int(time.time() - _daemon_start_time))
    except Exception as e:
        log.warning("SSE heartbeat failed: %s", e)


_daemon_start_time = time.time()


def run_daemon() -> None:
    """Boucle principale du daemon — avec PID lock et auto-restart.

    כֶּתֶר שֶׁבְּמַלְכוּת — La couronne dans le royaume doit survivre
    à ses propres ténèbres. Un crash de run_cycle() ne tue pas le daemon.
    """
    global _running, _daemon_start_time

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    # ── PID lock : un seul daemon à la fois ──
    acquire_pid_lock()

    _daemon_start_time = time.time()
    log.info("Daemon démarré (PID %d)", os.getpid())

    state = load_state()

    # ── Fix zombie flag : au démarrage, hitbonenut ne tourne PAS ──
    # L'ancien daemon a peut-être crashé avec hitbonenut_running: true.
    # On reset à la réalité : le thread n'existe pas encore.
    state["hitbonenut_running"] = False
    save_state(state)

    # Init Tzimtzum table
    _ensure_tzimtzum_table()

    # Heartbeat initial
    _emit_heartbeat()

    # Premier cycle immédiat
    try:
        run_cycle(state, force_daily=False)
    except Exception as e:
        log.error("Premier cycle échoué: %s\n%s", e, traceback.format_exc())

    last_heartbeat = time.time()
    consecutive_crashes = 0

    while _running:
        time.sleep(HEARTBEAT_INTERVAL)
        if not _running:
            break

        # Heartbeat toutes les 10 secondes
        now = time.time()
        if now - last_heartbeat >= HEARTBEAT_INTERVAL:
            _emit_heartbeat()
            last_heartbeat = now

        # Cycle principal toutes les SLEEP_TICK secondes
        if now - state.get("_last_cycle_time", 0) >= SLEEP_TICK:
            try:
                run_cycle(state)
                state["_last_cycle_time"] = now
                consecutive_crashes = 0  # reset sur succès
            except Exception as e:
                consecutive_crashes += 1
                backoff = min(
                    CRASH_BACKOFF_BASE * (2 ** (consecutive_crashes - 1)),
                    300,  # max 5 minutes
                )
                log.error(
                    "run_cycle crash #%d: %s — backoff %ds\n%s",
                    consecutive_crashes, e, backoff,
                    traceback.format_exc(),
                )
                if consecutive_crashes >= MAX_CONSECUTIVE_CRASHES:
                    log.critical(
                        "SHEVIRAH — %d crashes consécutifs. "
                        "Daemon en mode survie (heartbeat seul, pas de cycles).",
                        consecutive_crashes,
                    )
                    # Attente longue avant de réessayer
                    for _ in range(int(300 / HEARTBEAT_INTERVAL)):
                        if not _running:
                            break
                        time.sleep(HEARTBEAT_INTERVAL)
                        _emit_heartbeat()
                    consecutive_crashes = 0  # réessayer après 5 min
                else:
                    # Backoff court avant le prochain cycle
                    for _ in range(int(backoff / HEARTBEAT_INTERVAL)):
                        if not _running:
                            break
                        time.sleep(HEARTBEAT_INTERVAL)
                        _emit_heartbeat()

    # ── Nettoyage propre ──
    log.info("Arrêt en cours...")
    if _hitbonenut_runner.is_running:
        log.info("Arrêt du Hitbonenut continu...")
        _hitbonenut_runner.stop()
    # Sauvegarder l'état final avec le vrai statut
    state["hitbonenut_running"] = False
    save_state(state)
    from pool import close_pool
    close_pool()
    release_pid_lock()
    log.info("Daemon arrêté proprement.")


# ─── CLI ────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    # Sprint 8 D-log1 : configuration logging uniquement au démarrage CLI.
    # L'import du module (pytest, autres modules) ne touche plus au root logger.
    log = setup_logging()

    parser = argparse.ArgumentParser(
        prog="etz-daemon",
        description="Keter-de-Malkuth — Le battement de coeur de l'Arbre",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Un seul cycle complet puis quitter",
    )
    parser.add_argument(
        "--task",
        choices=["netzach", "gc", "snapshot", "daat-predict", "contradictions", "tiferet-synthesize", "hitbonenut", "full-tree", "auto-improve", "insightforge", "binah-confounders", "binah-graphs", "omer", "report"],
        help="Exécuter une seule tâche",
    )
    args = parser.parse_args()

    # Init connection pool pour tous les modes
    from pool import init_pool
    init_pool(DB_URL)

    if args.task:
        run_single_task(args.task)
    elif args.once:
        state = load_state()
        run_cycle(state, force_daily=True)
        print("Cycle complet terminé.")
    else:
        run_daemon()
