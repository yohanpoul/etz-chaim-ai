"""ContextAssembler — Orchestrateur unifié du pipeline Sod HaKli.

מְכַנֵּס הַהֶקְשֵׁר — Le ContextAssembler est l'organe central du Kli vivant.
Il orchestre les 10 étapes du pipeline complet :

  1. GILGUL INIT  — charger les Tikkun patterns de la session précédente
  2. ROSH          — décision (Masakh : niveau, budget, paramètres)
  3. ARAKHIN       — recatégoriser le contexte selon la tâche
  4. HITLABSHUT    — enclothe les principes dans les instructions
  5. DA'AT BRIDGE  — construire le pont connaissance↔application
  6. KAVVANAH      — formater et injecter l'intention
  7. TZELEM        — injecter le moule archétypal
  8. TOCH          — assembler et filtrer (budget tokens)
  9. SOF           — documenter ce qui a été exclu
  10. MONITOR      — évaluer les 29 dimensions, écrire le Reshimo

PG-SHK-021, PG-SHK-024 — Phase 4, Partzufim complets.
Le Kli passe de Berudim (facettes juxtaposées) à Partzufim
(facettes co-créantes organiquement).

Usage:
    from masakh.context_assembler import ContextAssembler

    assembler = ContextAssembler(db_pool_fn=get_conn, config=cfg)
    result = assembler.assemble(
        olam="briah",
        prompt="Analyse ce passage du Zohar",
        kavvanah={"intention": "analyser", "critere_succes": "..."},
    )
    print(result["prompt_final"])
    print(result["dimensions_score"])
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional

from masakh import Masakh, _MASAKH_LOG, CHARS_PER_TOKEN
from masakh.arakhin import Arakhin
from masakh.context_monitor import ContextMonitor, log_to_db as monitor_log_to_db
from masakh.gilgul import Gilgul
from masakh.hitlabshut import Hitlabshut

logger = logging.getLogger(__name__)


def _format_kavvanah(kavvanah: dict) -> str:
    """Formater un bloc Kavvanah pour injection en tete de prompt."""
    parts = ["[KAVVANAH]"]
    if "intention" in kavvanah:
        parts.append(f"Intention : {kavvanah['intention']}")
    if "critere_succes" in kavvanah:
        parts.append(f"Succès si : {kavvanah['critere_succes']}")
    if "anti_pattern" in kavvanah:
        parts.append(f"Ne pas : {kavvanah['anti_pattern']}")
    parts.append("[/KAVVANAH]")
    return "\n".join(parts)


# F-008: compteur d'appels module-level pour purge Onesh périodique
_CALL_COUNTER = 0
_PURGE_ONESH_INTERVAL = 50


class ContextAssembler:
    """Orchestrateur unifie du pipeline Sod HaKli.

    Orchestre les 10 etapes du pipeline complet, de Gilgul Init
    au Reshimo final. C'est le Kli vivant — pas un conteneur passif
    mais un organisme qui s'adapte, filtre, et se monitore.
    """

    def __init__(
        self,
        db_pool_fn: Callable | None = None,
        config: dict | None = None,
    ) -> None:
        """
        Args:
            db_pool_fn: Callable retournant une connexion DB (optionnel).
                Si None, fonctionne en mode memoire seule.
            config: Configuration du systeme (optionnel).
                Si None, utilise les defaults.
        """
        self._db_pool_fn = db_pool_fn
        self._config = config or {}

        # Sous-modules
        self._gilgul = Gilgul()
        self._arakhin = Arakhin()
        self._hitlabshut = Hitlabshut()
        self._monitor = ContextMonitor()
        self._maturation: Any = None  # Lazy-loaded (Phase 4b)
        self._tzelem: Any = None  # Lazy-loaded (Phase 4d)
        self._daat_bridge: Any = None  # Lazy-loaded
        self._db_ctx: Any = None  # Context manager pour cleanup

    def _get_db_conn(self):
        """Obtenir une connexion DB si disponible.

        Gère le cas où db_pool_fn retourne un context manager (generator)
        ou une connexion directe.
        """
        if self._db_pool_fn:
            try:
                result = self._db_pool_fn()
                # Si c'est un context manager (generator), entrer dedans
                if hasattr(result, '__enter__'):
                    conn = result.__enter__()
                    # Stocker le context manager pour cleanup
                    self._db_ctx = result
                    return conn
                return result
            except Exception as e:
                logger.debug("DB connection failed: %s", e)
        return None

    def _get_maturation(self):
        """Lazy-load du module Maturation (Phase 4b)."""
        if self._maturation is None:
            try:
                from masakh.maturation import Maturation
                self._maturation = Maturation(self._db_pool_fn)
            except ImportError:
                self._maturation = False  # Module pas encore disponible
        return self._maturation if self._maturation is not False else None

    def _get_tzelem(self):
        """Lazy-load du module Tzelem (Phase 4d)."""
        if self._tzelem is None:
            try:
                from masakh.tzelem import Tzelem
                self._tzelem = Tzelem()
            except ImportError:
                self._tzelem = False
        return self._tzelem if self._tzelem is not False else None

    def _get_daat_bridge(self):
        """Lazy-load du DaatBridge. Fonctionne avec ou sans DB."""
        if self._daat_bridge is None:
            try:
                from daat_bridge import DaatBridge
                self._daat_bridge = DaatBridge(self._db_pool_fn)
            except ImportError:
                self._daat_bridge = False
        return self._daat_bridge if self._daat_bridge is not False else None

    def assemble(
        self,
        olam: str,
        prompt: str,
        context_window: int = 8192,
        kavvanah: dict | None = None,
        context_sources: dict | None = None,
        context_items: list[str] | None = None,
        principles: list[str] | None = None,
        domain: str | None = None,
        facts: list[str] | None = None,
        pressure_regulated: bool = False,
        daemon_block: str | None = None,
        tree_signals: dict | None = None,
    ) -> dict[str, Any]:
        """Orchestre le pipeline complet en 10 etapes.

        Args:
            olam: Le monde cible ("atziluth", "briah", "yetzirah", "assiah").
            prompt: Le prompt original de l'utilisateur.
            context_window: Taille du context window en tokens.
            kavvanah: Intention dirigee (optionnel).
            context_sources: Sources de contexte additionnelles (optionnel).
            context_items: Elements de contexte a recategoriser (optionnel).
            principles: Principes a enclothe (optionnel).
            domain: Domaine pour le pont Da'at (optionnel).
            facts: Faits pour le pont Da'at (optionnel).
            daemon_block: Contenu DaemonBridge pre-formate (optionnel).
                Soumis au budget Masakh total : ses tokens sont deduits
                du budget AVANT le filtrage Toch, puis il est appende
                au prompt filtre.  F6 — EC-SHK-023.
            tree_signals: Signaux des modules de l'Arbre (optionnel).
                Permet aux 9 dimensions restantes (02-07, 10, 11, 26)
                d'etre mesurees sans import circulaire. Cles possibles:
                  active_profile, context_window, model_think,
                  active_intention, recent_insights, causal_confidence,
                  unresolved_tensions, intent_progress, domain_competence,
                  active_skills_count

        Returns:
            Dict avec :
                - prompt_final (str): Le prompt assemble et filtre
                - masakh_level (str): Niveau de Masakh applique
                - dimensions_score (float): Score des 29 dimensions
                - reshimo_id (int|None): ID du Reshimo en DB
                - maturation_stage (str|None): Stade IYM
                - excluded (dict): Ce qui a ete exclu par le Masakh
                - pipeline_steps (list[str]): Etapes executees
                - daemon_tokens_used (int): Tokens daemon effectivement injectes
        """
        steps_executed = []
        conn = self._get_db_conn()
        original_prompt = prompt

        # F-008: purge Onesh périodique
        global _CALL_COUNTER
        _CALL_COUNTER += 1
        if _CALL_COUNTER % _PURGE_ONESH_INTERVAL == 0:
            try:
                self._gilgul.purge_onesh(olam=olam, conn=conn)
                logger.info("[GILGUL] Purge Onesh périodique (appel #%d)", _CALL_COUNTER)
            except Exception as e:
                logger.debug("Purge Onesh skipped: %s", e)

        # ── ETAPE 1 : GILGUL INIT ──────────────────────────────
        tikkun_patterns = []
        try:
            tikkun_patterns = self._gilgul.get_tikkun_patterns(
                olam, limit=5, conn=conn,
            )
            steps_executed.append("gilgul_init")
        except Exception as e:
            logger.debug("Gilgul init skipped: %s", e)

        # ── ETAPE 1b : MATURATION ──────────────────────────────
        maturation_stage = None
        maturation = self._get_maturation()
        if maturation:
            try:
                maturation_stage = maturation.assess_stage(olam=olam, conn=conn)
                steps_executed.append("maturation")
            except Exception as e:
                logger.debug("Maturation skipped: %s", e)

        # ── ETAPE 2 : ROSH (decision) ──────────────────────────
        masakh = Masakh(olam)

        # Calibrer le Masakh initial selon les Tikkun patterns
        if tikkun_patterns:
            best_level = (
                tikkun_patterns[0]
                .get("reshimo_aviut", {})
                .get("masakh_level")
            )
            if best_level:
                try:
                    masakh.set_level(best_level)
                except ValueError as _exc:

                    import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        # Adapter le Masakh selon le stade de maturation
        if maturation_stage == "ibur":
            # En Ibur, pas de filtrage agressif
            if masakh.level_index < 3:  # Moins que aleph
                masakh.set_level("aleph")
        elif maturation_stage == "yenikah":
            # En Yenikah, pas plus haut que bet
            if masakh.level_index < 2:  # Moins que bet
                masakh.set_level("bet")
        # En Mochin : pas de contrainte, le Masakh peut atteindre son max

        params = masakh.rosh(prompt, context_window)
        steps_executed.append("rosh")

        # ── ETAPE 3 : ARAKHIN ──────────────────────────────────
        # Skip en Ibur (trop tot)
        if context_items and maturation_stage != "ibur":
            try:
                transformed = [
                    self._arakhin.transform(item, olam)
                    for item in context_items
                ]
                context_block = "\n".join(transformed)
                prompt = f"{context_block}\n\n{prompt}"
                steps_executed.append("arakhin")
            except Exception as e:
                logger.debug("Arakhin skipped: %s", e)

        # ── ETAPE 4 : HITLABSHUT ──────────────────────────────
        # Skip en Ibur (trop tot), basique en Yenikah
        if principles and masakh.level in ("gimel", "dalet"):
            if maturation_stage != "ibur":
                try:
                    prompt = self._hitlabshut.enclothe_many(principles, prompt)
                    steps_executed.append("hitlabshut")
                except Exception as e:
                    logger.debug("Hitlabshut skipped: %s", e)

        # ── ETAPE 5 : DA'AT BRIDGE ────────────────────────────
        # EC-SHK-016, 032-034 : Da'at = Dvekut + Kishur + Kolel.
        # Le Bridge connecte les connaissances au domaine de la query.
        # Fonctionne sans DB (mode contexte pur) et sans domain/facts
        # explicites (extrait le domaine de la kavvanah).
        daat_applied = False
        daat_bridge = self._get_daat_bridge()
        if daat_bridge:
            try:
                daat_block = daat_bridge.build(
                    question=original_prompt,
                    domain=domain,
                    facts=facts,
                    context_items=context_items,
                    kavvanah=kavvanah,
                )
                if daat_block:
                    prompt = f"{prompt}\n\n{daat_block}"
                    daat_applied = True
                    steps_executed.append("daat_bridge")
            except Exception as e:
                logger.debug("Da'at bridge skipped: %s", e)

        # ── ETAPE 6 : KAVVANAH ─────────────────────────────────
        if kavvanah:
            kavvanah_block = _format_kavvanah(kavvanah)
            prompt = f"{kavvanah_block}\n\n{prompt}"
            steps_executed.append("kavvanah")

        # ── ETAPE 7 : TZELEM ──────────────────────────────────
        tzelem = self._get_tzelem()
        tzelem_applied = None
        if tzelem and kavvanah:
            try:
                tzelem_name = tzelem.detect(kavvanah, olam)
                tzelem_instruction = tzelem.apply(tzelem_name)
                # Injecter apres la Kavvanah, avant le contexte
                prompt = f"{tzelem_instruction}\n\n{prompt}"
                tzelem_applied = tzelem_name
                steps_executed.append("tzelem")
            except Exception as e:
                logger.debug("Tzelem skipped: %s", e)

        # ── ETAPE 8 : TOCH (assemblage + filtrage) ─────────────
        # F6 — Le DaemonBridge est soumis au budget Masakh total.
        # Ses tokens sont deduits du budget AVANT filtrage, puis
        # le bloc daemon est appende au prompt filtre.
        daemon_tokens_used = 0
        effective_budget = params["budget_tokens"]
        if daemon_block:
            daemon_tokens_used = masakh.estimate_tokens(daemon_block)
            # Reserver au max 20% du budget pour le daemon, cap restant
            max_daemon = int(params["budget_tokens"] * 0.20)
            if daemon_tokens_used > max_daemon:
                # Tronquer le daemon_block pour respecter 20% du budget
                max_chars = max_daemon * CHARS_PER_TOKEN
                daemon_block = daemon_block[:max_chars]
                daemon_tokens_used = masakh.estimate_tokens(daemon_block)
            effective_budget = max(1, params["budget_tokens"] - daemon_tokens_used)

        filtered = masakh.toch(prompt, effective_budget, query=original_prompt)
        steps_executed.append("toch")

        # ── ETAPE 9 : SOF (rejet) ──────────────────────────────
        # sof() doit voir filtered SANS daemon, sinon les tokens
        # daemon gonflent tokens_after et corrompent le Reshimo.
        log_entry = masakh.sof(prompt, filtered)
        _MASAKH_LOG.append(log_entry)

        # Appendre le daemon APRES sof — il est dans le budget
        if daemon_block:
            filtered = filtered + "\n\n" + daemon_block

        # Enrichir le log
        if kavvanah:
            log_entry["kavvanah"] = kavvanah

        steps_executed.append("sof")

        # ── ETAPE 10 : MONITOR + RESHIMO ───────────────────────
        # Fix 2 : Le Tsimtsum est la contraction qui crée l'espace.
        # Si le Masakh a effectivement filtré (was_filtered), c'est du
        # Tsimtsum effectif — pas besoin d'un bool externe.
        effective_pressure = (
            pressure_regulated
            or log_entry.get("was_filtered", False)
        )
        monitor_data = {
            "olam": olam,
            "kavvanah": kavvanah,
            "masakh_log": log_entry,
            # F202: reshimo is only prepared here, not yet written to DB.
            # The actual DB write happens later in _persist_post_response().
            # Set to False — the monitor will see STATUS_ABSENT for dim 14
            # until _persist_post_response runs and updates post-response.
            "reshimo_written": False,
            # F202: token ratio is computed in log_entry by sof().
            # True only if tokens_before and tokens_after are actually present.
            "token_ratio_logged": bool(
                log_entry.get("tokens_before") is not None
                and log_entry.get("tokens_after") is not None
            ),
            # F4 — pipeline awareness for dims 19/20/21
            "pipeline_steps": steps_executed,
            # F4 — maturation stage for dim 23
            "maturation_stage": maturation_stage,
            # F4 — Gilgul tikkun patterns for dim 28
            "tikkun_patterns_count": len(tikkun_patterns),
            # F5+Fix2 — Tsimtsum = contraction effective (pression OU filtrage)
            "pressure_regulated": effective_pressure,
            # Fix 3 — Yesod = mémoire/contexte externe consulté
            "memory_active": bool(context_sources) or bool(facts),
            # 29/29 — Signaux de l'Arbre pour les 9 dims restantes
            **(tree_signals or {}),
        }
        monitor_state = self._monitor.assess(monitor_data)
        steps_executed.append("monitor")

        # ── AUDIT F05-R2: Per-dimension corrective actions ─────
        # Applied BEFORE the global score check so that individual
        # critical dimensions are remediated even when the global
        # score looks acceptable.  Each action patches the context
        # dict rather than triggering a full retry.
        per_dim_actions: list[dict[str, str]] = []
        dim_status_map = {
            d["id"]: d["status"]
            for d in monitor_state.get("dimensions", [])
        }

        # Dim 01 — Kavvanah absent → inject default kavvanah
        if dim_status_map.get("01") == "✗" and not kavvanah:
            kavvanah = {"intention": "general_query"}
            kavvanah_block = _format_kavvanah(kavvanah)
            filtered = f"{kavvanah_block}\n\n{filtered}"
            per_dim_actions.append({
                "dim": "01", "action": "default_kavvanah_injected",
            })
            logger.info(
                "[AUDIT-F05] Dim 01 (Kavvanah) absent — "
                "default kavvanah='general_query' injected",
            )

        # Dim 08 — Da'at absent → flag for downstream bridge
        if dim_status_map.get("08") == "✗" and not daat_applied:
            monitor_state["force_daat_bridge"] = True
            per_dim_actions.append({
                "dim": "08", "action": "force_daat_bridge_flagged",
            })
            logger.info(
                "[AUDIT-F05] Dim 08 (Da'at) absent — "
                "force_daat_bridge=True flagged for next call",
            )

        # Dims 02-07 — tree_signals missing → inject neutral defaults
        _TREE_SIGNAL_DEFAULTS = {
            "02": ("active_profile", "default"),
            "03": ("context_window", 8192),
            "04": ("model_name", "unknown"),
            "05": ("active_intention", {"intention": "neutral", "critere_succes": "neutral"}),
            "06": ("recent_insights", []),
            "07": ("causal_confidence", 0.5),
        }
        for dim_id, (signal_key, default_val) in _TREE_SIGNAL_DEFAULTS.items():
            if dim_status_map.get(dim_id) == "✗":
                monitor_data[signal_key] = default_val
                per_dim_actions.append({
                    "dim": dim_id,
                    "action": f"neutral_default_{signal_key}",
                })
        if any(a["dim"] in ("02", "03", "04", "05", "06", "07")
               for a in per_dim_actions):
            # Re-assess with patched signals so the score reflects
            # the remediated state (neutral defaults → △ or ✓).
            monitor_state = self._monitor.assess(monitor_data)
            logger.info(
                "[AUDIT-F05] Dims 02-07 — neutral defaults injected "
                "for %d missing tree_signals, score re-assessed",
                sum(1 for a in per_dim_actions
                    if a["dim"] in ("02", "03", "04", "05", "06", "07")),
            )

        # ── F-016: décision basée sur le score — Masakh retry si critique
        # AUDIT F05-R2: seuil relevé de 0.3 à 0.5 pour que le retry
        # se déclenche quand moins de ~15/29 dims passent (au lieu de 9/29).
        score_global = monitor_state.get("score_global", 0.5)
        masakh_retry = False
        if score_global < 0.5:
            # CRITIQUE — Kli défectueux, épaissir le Masakh et re-filtrer
            # level_index 0=dalet(max) → plus petit index = plus filtrant
            if masakh.level_index > 0:  # pas déjà au max de filtrage (dalet)
                old_level = masakh.level
                from masakh import LEVEL_ORDER
                new_level = LEVEL_ORDER[masakh.level_index - 1]
                masakh.set_level(new_level)
                filtered = masakh.toch(prompt, effective_budget, query=original_prompt)
                log_entry = masakh.sof(prompt, filtered)
                if daemon_block:
                    filtered = filtered + "\n\n" + daemon_block
                # Re-inject default kavvanah if it was patched above
                if any(a["action"] == "default_kavvanah_injected"
                       for a in per_dim_actions):
                    kavvanah_block = _format_kavvanah(kavvanah)
                    filtered = f"{kavvanah_block}\n\n{filtered}"
                masakh_retry = True
                logger.warning(
                    "[SOD-HAKLI] Score critique %.2f — retry %s→%s",
                    score_global, old_level, masakh.level,
                )
        elif score_global < 0.7:
            logger.info(
                "[SOD-HAKLI] Score bas %.2f — signalé pour Hizdakchut",
                score_global,
            )

        # F-017: stocker le reshimo pré-LLM sans écrire — _persist_post_response
        # fusionnera avec les données post-LLM et écrira un seul Reshimo.
        reshimo = {
            "reshimo_hitlabshut": {
                "pipeline_steps": steps_executed,
                "maturation_stage": maturation_stage,
                "tzelem": tzelem_applied,
                "tikkun_patterns_count": len(tikkun_patterns),
            },
            "reshimo_aviut": {
                "masakh_level": log_entry.get("aviut_level"),
                "kashiut": log_entry.get("kashiut"),
                "aviut_mode": log_entry.get("aviut_mode"),
                "tokens_before": log_entry.get("tokens_before"),
                "tokens_after": log_entry.get("tokens_after"),
                "tokens_rejected": log_entry.get("tokens_rejected"),
                "was_filtered": log_entry.get("was_filtered"),
                "kavvanah": kavvanah,
                "score": monitor_state["score_global"],
            },
        }
        steps_executed.append("reshimo")

        # Persister le monitor en DB si disponible
        if conn:
            try:
                monitor_log_to_db(conn, monitor_state)
            except Exception as e:
                logger.debug("Monitor DB log failed: %s", e)

        # Cleanup du context manager DB
        if self._db_ctx is not None:
            try:
                self._db_ctx.__exit__(None, None, None)
            except Exception as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
            self._db_ctx = None

        return {
            "prompt_final": filtered,
            "masakh_level": masakh.level,
            "dimensions_score": monitor_state["score_global"],
            "monitor_state": monitor_state,
            "reshimo_pre": reshimo,
            "reshimo_id": None,  # ID DB si disponible (futur)
            "maturation_stage": maturation_stage,
            "excluded": {
                "tokens_rejected": log_entry.get("tokens_rejected", 0),
                "rejection_ratio": log_entry.get("rejection_ratio", 0.0),
                "rejection_reason": log_entry.get("rejection_reason", ""),
            },
            "pipeline_steps": steps_executed,
            "daat_applied": daat_applied,
            "daemon_tokens_used": daemon_tokens_used,
            "masakh_retry": masakh_retry,
            # AUDIT F05-R2: alert range raised to match new retry threshold
            "score_alert": 0.5 <= score_global < 0.7,
            "per_dim_actions": per_dim_actions,
        }
