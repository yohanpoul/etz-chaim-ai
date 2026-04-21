"""partzufim/regulator.py — Régulateur analogique des Partzufim.

Les Partzufim sont les configurations matures des Sefirot. Chaque Partzuf
"habille" (malbish) une ou plusieurs Sefirot et contrôle leur capacité
opérationnelle.

Contrairement au Tzimtzum (binaire : actif/dormant), le régulateur
Partzufim est ANALOGIQUE : il module les seuils et budgets des modules
en fonction de l'état de leur Partzuf parent.

Hiérarchie de régulation (du plus grossier au plus fin) :
  1. Tzimtzum — circuit-breaker (si dormant, rien ne passe)
  2. Partzufim — variateur (si katnut, capacité réduite)
  3. Omer — calibration quotidienne fine

Doctrine :
  - Atik Yomin (עַתִּיק יוֹמִין) = méta-régulateur, supervise tout
  - Arikh Anpin → Keter (routing initial)
  - Abba → Chokmah (InsightForge, ExplorationEngine)
  - Imma → Binah (CausalEngine)
  - Zeir Anpin → 6 Midot (Chesed→Yesod)
  - Nukva → Malkuth (génération finale)

  Cascade : Atik dégradé → TOUS dégradés ; Imma katnut → ZA katnut
  Hystérésis : katnut à score < 0.4, gadlut à score > 0.6
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ── Seuils de transition (hystérésis) ───────────────────────
KATNUT_THRESHOLD = 0.4      # En dessous → force katnut
GADLUT_THRESHOLD = 0.6      # Au dessus → autorise retour gadlut
HIGH_SCORE_BONUS = 0.85     # Au dessus → bonus +10%
ATIK_CASCADE_THRESHOLD = 0.5  # Atik sous ce seuil → tout dégradé
LOAD_STATE_TIMEOUT_MS = 100   # Timeout DB en ms

# ── Scores dynamiques ──────────────────────────────────────
DYNAMIC_WEIGHT_RECENT = 0.4   # Poids activité récente (24h)
DYNAMIC_WEIGHT_CUMUL = 0.6    # Poids score cumulatif existant
DYNAMIC_WINDOW_HOURS = 24     # Fenêtre temporelle pour le récent
INACTIVITY_SCORE = 0.5        # Score plancher si 0 activité récente

# ── Conditions achor ───────────────────────────────────────
ACHOR_INACTIVITY_HOURS = 24   # Inactivité > 24h → achor
ACHOR_CONSECUTIVE_ERRORS = 3  # 3+ erreurs consécutives → achor
ACHOR_CAPACITY_PENALTY = 0.8  # En achor : capacity × 0.8

# ── Tiferet guard pour Zeir Anpin ──────────────────────────
# Doctrine : Tiferet est la Midah de l'équilibre/compassion au cœur
# de ZA. Quand l'équilibre interne est élevé (tiferet > seuil),
# un taux de rejet AutoJudge élevé seul ne suffit pas à "tourner
# le dos" (akhor). L'équilibre interne modère le rejet externe —
# une forme de khesed qui tempère gevurah avant l'akhor.
# Sans ce garde, ZA bascule akhor systématiquement dès que
# AutoJudge atteint son régime nominal de rejet ~70-89% (Nitzotzot),
# même quand les 6 Midot sont internes équilibrées.
ZA_TIFERET_AKHOR_GUARD = 0.8  # Si ZA.tiferet > 0.8, tiferet préserve panim


# ── Mapping Partzuf → Modules régulés ───────────────────────
# Doctrine : chaque Partzuf "habille" certaines Sefirot de l'Arbre.
# L'attribut 'source' dans le REGISTRY donne la Sephirah source,
# mais un Partzuf peut réguler PLUSIEURS modules (Abba régule
# le pilier droit : Chokmah + Chesed via influence descendante).

PARTZUF_TO_MODULES: dict[str, list[str]] = {
    "abba": ["chokmah"],              # InsightForge
    "imma": ["binah"],                # CausalEngine
    "zeir_anpin": [
        "chesed",                     # ExplorationEngine
        "gevurah",                    # AutoJudge
        "tiferet",                    # DissensuEngine
        "netzach",                    # IntentKeeper
        "hod",                        # SelfMap
        "yesod",                      # EpisteMemory
    ],
    "nukva": ["malkuth"],             # Génération finale
    "arikh_anpin": ["keter"],         # Routing initial
    "atik_yomin": [],                 # Méta — régule les Partzufim eux-mêmes
}


# ── Profils de modulation par état ──────────────────────────
# Chaque combinaison (mochin_state × orientation) produit un
# profil de modulation spécifique.

@dataclass
class ModifierProfile:
    """Profil de modulation pour un module."""
    capacity_factor: float = 1.0     # 1.0 = plein, 0.5 = réduit
    threshold_modifier: float = 0.0  # ajouté aux seuils (+ = plus strict)
    budget_factor: float = 1.0       # multiplicateur budget tokens
    feedback_enabled: bool = True    # False si akhor
    reason: str = ""


_PROFILES: dict[tuple[str, str], dict] = {
    # GADLUT + PANIM — état optimal
    ("gadlut", "panim"): {
        "capacity_factor": 1.0,
        "threshold_modifier": 0.0,
        "budget_factor": 1.0,
        "feedback_enabled": True,
    },
    # GADLUT + AKHOR — puissant mais aveugle
    ("gadlut", "akhor"): {
        "capacity_factor": 0.8,
        "threshold_modifier": 0.05,
        "budget_factor": 0.8,
        "feedback_enabled": False,
    },
    # KATNUT + PANIM — limité mais conscient
    ("katnut", "panim"): {
        "capacity_factor": 0.5,
        "threshold_modifier": 0.1,
        "budget_factor": 0.5,
        "feedback_enabled": True,
    },
    # KATNUT + AKHOR — état minimal
    ("katnut", "akhor"): {
        "capacity_factor": 0.3,
        "threshold_modifier": 0.15,
        "budget_factor": 0.3,
        "feedback_enabled": False,
    },
    # TRANSITIONAL + PANIM — intermédiaire
    ("transitional", "panim"): {
        "capacity_factor": 0.75,
        "threshold_modifier": 0.03,
        "budget_factor": 0.75,
        "feedback_enabled": True,
    },
    # TRANSITIONAL + AKHOR — intermédiaire aveugle
    ("transitional", "akhor"): {
        "capacity_factor": 0.6,
        "threshold_modifier": 0.08,
        "budget_factor": 0.6,
        "feedback_enabled": False,
    },
}


# ── Mapping module key → attributs modulables ──────────────
# Pour chaque module de l'arbre, quels attributs le Regulator peut toucher.
# capacity_factor → max_insights_per_session, explore_breadth, max_iterations, etc.
# threshold_modifier → min_novelty_score, quality_threshold, min_evidence, etc.
# budget_factor → max_duration_seconds, max_open_questions, etc.

MODULE_TUNABLE_ATTRS: dict[str, dict[str, list[str]]] = {
    "chokmah": {
        "capacity": ["max_insights_per_session"],
        "threshold": ["min_novelty_score"],
        "budget": [],
    },
    "binah": {
        "capacity": ["max_confounders"],
        "threshold": [],
        "budget": [],
    },
    "chesed": {
        "capacity": ["explore_breadth"],
        "threshold": ["novelty_threshold"],
        "budget": ["max_duration_seconds"],
    },
    "gevurah": {
        "capacity": ["max_iterations"],
        "threshold": ["quality_threshold", "quarantine_threshold"],
        "budget": [],
    },
    "tiferet": {
        "capacity": ["max_open_questions"],
        "threshold": ["dissensus_threshold", "confidence_floor"],
        "budget": [],
    },
    "netzach": {
        # IntentKeeper instance attrs (intentkeeper/core.py)
        "capacity": [],
        "threshold": ["min_progress_at_quarter", "max_failed_ratio"],
        "budget": ["stale_days", "zombie_days"],
    },
    "hod": {
        # SelfMap instance attrs (selfmap/core.py)
        "capacity": [],
        "threshold": ["decline_threshold"],
        "budget": [],
    },
    "yesod": {
        # EpisteMemory (epistememory/core.py) — intentionally empty.
        # EpisteMemory.__init__ has no numeric tunable instance vars:
        #   self.db = Database(...)       → object
        #   self.gematria = None          → object (injected later)
        #   self.embedding_model = "..."  → string
        # Tunable params (max_per_level, remove_expired) are method args,
        # not instance vars. Nothing for the regulator to modulate.
        "capacity": [],
        "threshold": [],
        "budget": [],
    },
    "keter": {
        # DaatBridge (daat_bridge.py) — intentionally empty.
        # DaatBridge.__init__ has no numeric tunable instance vars:
        #   self._db = db_pool_fn  → callable or None
        # Keter/routing operates as a pure transformer (context in → context out)
        # with no adjustable numeric knobs.
        "capacity": [],
        "threshold": [],
        "budget": [],
    },
    "malkuth": {
        # BeinoniTracker (tanya/beinoni_tracker.py) — intentionally empty.
        # BeinoniTracker.__init__ has no numeric tunable instance vars:
        #   self._db_url = db_url   → string or None
        #   self._memory = []       → list (in-memory buffer)
        # Thresholds (_REGRESSION_THRESHOLD, _TSADDIK_THRESHOLD, etc.) are
        # module-level constants, not instance vars the regulator can touch.
        "capacity": [],
        "threshold": [],
        "budget": [],
    },
}


# ── Mapping noms d'affichage → clés snake_case ─────────────
# En DB, les Partzufim sont stockés avec leur nom d'affichage
# (partzuf.name = "Atik Yomin"), mais le regulator utilise
# des clés snake_case ("atik_yomin") conformes à PARTZUF_TO_MODULES.

_DISPLAY_TO_KEY: dict[str, str] = {
    "Atik Yomin": "atik_yomin",
    "Arikh Anpin": "arikh_anpin",
    "Abba": "abba",
    "Imma": "imma",
    "Zeir Anpin": "zeir_anpin",
    "Nukva": "nukva",
}


class PartzufimRegulator:
    """Régulateur analogique basé sur l'état des Partzufim.

    Usage dans le pipeline :

        reg = PartzufimRegulator()
        state = reg.load_state()
        modifiers = reg.compute_modifiers(state)
        reg.apply_to_tree(tree, modifiers)
        ctx['partzuf_state'] = state
        ctx['partzuf_modifiers'] = modifiers
    """

    def __init__(self) -> None:
        self._last_state: dict[str, dict] | None = None
        self._partzuf_to_modules = PARTZUF_TO_MODULES

    # ── Chargement d'état ────────────────────────────────────

    def load_state(self) -> dict[str, dict]:
        """Charge l'état actuel des 6 Partzufim depuis la DB.

        Les noms en DB sont des noms d'affichage ("Atik Yomin"),
        convertis ici en clés snake_case ("atik_yomin") pour
        correspondre à PARTZUF_TO_MODULES.

        Timeout 100ms — si DB lente, retourne les dernières valeurs connues.

        Returns:
            {partzuf_key: {overall, mochin_state, orientation, faculties, updated_at}}
        """
        t0 = time.monotonic()
        try:
            from partzufim.db import load_all_partzufim
            raw = load_all_partzufim()
            elapsed_ms = (time.monotonic() - t0) * 1000
            if elapsed_ms > LOAD_STATE_TIMEOUT_MS:
                logger.warning(
                    "load_state took %.0fms (timeout=%dms), using result anyway",
                    elapsed_ms, LOAD_STATE_TIMEOUT_MS,
                )
            if raw:
                # Normaliser les clés : nom d'affichage → snake_case
                state = {}
                for db_name, data in raw.items():
                    key = _DISPLAY_TO_KEY.get(db_name, db_name.lower().replace(" ", "_"))
                    state[key] = data
                self._last_state = state
                return state
        except Exception as e:
            logger.debug("load_state failed: %s — using fallback", e)

        # Fallback : dernières valeurs connues
        if self._last_state:
            return self._last_state
        return {}

    # ── Calcul des modificateurs ─────────────────────────────

    def compute_modifiers(self, state: dict[str, dict] | None = None) -> dict[str, ModifierProfile]:
        """Calcule les modificateurs pour chaque module basé sur l'état des Partzufim.

        Returns:
            {module_key: ModifierProfile}
            module_key = clé dans le tree dict (chokmah, binah, chesed, etc.)
        """
        if state is None:
            state = self.load_state()

        modifiers: dict[str, ModifierProfile] = {}

        # Vérifier cascade Atik Yomin → tous
        atik_degraded = self._is_atik_degraded(state)

        # Pour chaque Partzuf, calculer le profil de ses modules
        for partzuf_name, module_keys in self._partzuf_to_modules.items():
            ps = state.get(partzuf_name, {})
            if not ps:
                # Partzuf absent de la DB — état neutre (pas de modulation)
                for mk in module_keys:
                    modifiers[mk] = ModifierProfile(reason=f"{partzuf_name} absent de DB")
                continue

            score = ps.get("overall", 0.5)
            mochin = ps.get("mochin_state", "transitional")
            orientation = ps.get("orientation", "panim")

            # Force katnut si score < seuil ou cascade Atik
            effective_mochin = mochin
            if self.should_force_katnut(partzuf_name, state):
                effective_mochin = "katnut"

            # Profil de base
            profile_key = (effective_mochin, orientation)
            base = _PROFILES.get(profile_key, _PROFILES[("transitional", "panim")])

            capacity = base["capacity_factor"]
            threshold = base["threshold_modifier"]
            budget = base["budget_factor"]
            feedback = base["feedback_enabled"]

            # Bonus score élevé
            if score > HIGH_SCORE_BONUS and effective_mochin == "gadlut":
                capacity = min(1.1, capacity * 1.1)
                budget = min(1.1, budget * 1.1)

            # Cascade Atik : dégradation supplémentaire
            if atik_degraded and partzuf_name != "atik_yomin":
                capacity *= 0.7
                threshold += 0.05
                budget *= 0.7

            for mk in module_keys:
                modifiers[mk] = ModifierProfile(
                    capacity_factor=round(capacity, 3),
                    threshold_modifier=round(threshold, 3),
                    budget_factor=round(budget, 3),
                    feedback_enabled=feedback,
                    reason=self._format_reason(partzuf_name, score, effective_mochin, orientation, atik_degraded),
                )

        return modifiers

    # ── Application aux modules ──────────────────────────────

    def apply_to_tree(self, tree: dict, modifiers: dict[str, ModifierProfile] | None = None) -> dict[str, ModifierProfile]:
        """Applique les modificateurs aux instances des modules dans le tree.

        Les Partzufim s'appliquent EN PLUS de l'Omer :
          - Multiplicatif pour capacity et budget (× factor)
          - Additif pour les seuils (+ modifier)

        Ne modifie PAS les modules si le Tzimtzum les a mis en dormance
        (le Tzimtzum reste le premier étage de régulation).

        Returns:
            Les modifiers appliqués (pour logging/ctx).
        """
        if modifiers is None:
            modifiers = self.compute_modifiers()

        for module_key, profile in modifiers.items():
            module = tree.get(module_key)
            if module is None:
                continue

            # Pas de modulation neutre (capacity=1.0, threshold=0.0)
            if (profile.capacity_factor == 1.0
                    and profile.threshold_modifier == 0.0
                    and profile.budget_factor == 1.0
                    and profile.feedback_enabled):
                continue

            tunable = MODULE_TUNABLE_ATTRS.get(module_key, {})

            # Capacity : multiplicatif
            for attr in tunable.get("capacity", []):
                current = getattr(module, attr, None)
                if current is not None and isinstance(current, (int, float)):
                    new_val = current * profile.capacity_factor
                    if isinstance(current, int):
                        new_val = max(1, int(round(new_val)))
                    else:
                        new_val = round(new_val, 4)
                    setattr(module, attr, new_val)

            # Threshold : additif (+ = plus strict)
            for attr in tunable.get("threshold", []):
                current = getattr(module, attr, None)
                if current is not None and isinstance(current, (int, float)):
                    new_val = current + profile.threshold_modifier
                    new_val = min(1.0, round(new_val, 4))
                    setattr(module, attr, new_val)

            # Budget : multiplicatif
            for attr in tunable.get("budget", []):
                current = getattr(module, attr, None)
                if current is not None and isinstance(current, (int, float)):
                    new_val = current * profile.budget_factor
                    if isinstance(current, int):
                        new_val = max(1, int(round(new_val)))
                    else:
                        new_val = round(new_val, 4)
                    setattr(module, attr, new_val)

        return modifiers

    # ── Détection de transitions ─────────────────────────────

    def should_force_katnut(self, partzuf_name: str, state: dict[str, dict]) -> bool:
        """Détermine si un Partzuf devrait être forcé en katnut.

        Conditions :
          - Score < KATNUT_THRESHOLD (0.4)
          - Atik Yomin dégradé (score < 0.5) → TOUT le monde en katnut
          - Imma en katnut → ZA forcé en katnut (Imma nourrit les Mochin de ZA)
        """
        ps = state.get(partzuf_name, {})
        score = ps.get("overall", 0.5)

        # Score sous le seuil
        if score < KATNUT_THRESHOLD:
            return True

        # Cascade Atik → tous
        if self._is_atik_degraded(state) and partzuf_name != "atik_yomin":
            return True

        # Cascade Imma → ZA
        if partzuf_name == "zeir_anpin":
            imma = state.get("imma", {})
            imma_mochin = imma.get("mochin_state", "transitional")
            imma_score = imma.get("overall", 0.5)
            if imma_mochin == "katnut" or imma_score < KATNUT_THRESHOLD:
                return True

        return False

    def can_return_to_gadlut(self, partzuf_name: str, state: dict[str, dict]) -> bool:
        """Détermine si un Partzuf peut revenir en gadlut.

        Hystérésis : le seuil de retour (0.6) est SUPÉRIEUR au seuil
        de chute (0.4). Ceci évite le flip-flop.

        Conditions supplémentaires :
          - Atik ne doit PAS être dégradé
          - Si ZA, Imma ne doit PAS être en katnut
        """
        ps = state.get(partzuf_name, {})
        score = ps.get("overall", 0.5)
        mochin = ps.get("mochin_state", "transitional")

        # Déjà en gadlut — rien à faire
        if mochin == "gadlut":
            return False

        # Score doit dépasser le seuil de retour
        if score < GADLUT_THRESHOLD:
            return False

        # Atik dégradé bloque le retour de tous
        if self._is_atik_degraded(state) and partzuf_name != "atik_yomin":
            return False

        # ZA ne peut pas revenir si Imma est en katnut
        if partzuf_name == "zeir_anpin":
            imma = state.get("imma", {})
            if imma.get("mochin_state", "transitional") == "katnut":
                return False
            if imma.get("overall", 0.5) < KATNUT_THRESHOLD:
                return False

        return True

    def trigger_katnut(self, partzuf_name: str, reason: str) -> bool:
        """Force un Partzuf en katnut. Enregistre en DB.

        Returns:
            True si la transition a été effectuée.
        """
        db_name = self._to_db_name(partzuf_name)
        try:
            from pool import get_conn
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE partzufim_state
                        SET mochin_state = 'katnut', updated_at = NOW()
                        WHERE name = %s AND mochin_state != 'katnut'
                    """, (db_name,))
                    changed = cur.rowcount > 0
            if changed:
                logger.info("Partzuf %s → KATNUT: %s", partzuf_name, reason)
            return changed
        except Exception as e:
            logger.error("trigger_katnut(%s) failed: %s", partzuf_name, e)
            return False

    def trigger_gadlut(self, partzuf_name: str, reason: str) -> bool:
        """Restaure un Partzuf en gadlut. Enregistre en DB.

        Returns:
            True si la transition a été effectuée.
        """
        db_name = self._to_db_name(partzuf_name)
        try:
            from pool import get_conn
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE partzufim_state
                        SET mochin_state = 'gadlut', updated_at = NOW()
                        WHERE name = %s AND mochin_state != 'gadlut'
                    """, (db_name,))
                    changed = cur.rowcount > 0
            if changed:
                logger.info("Partzuf %s → GADLUT: %s", partzuf_name, reason)
            return changed
        except Exception as e:
            logger.error("trigger_gadlut(%s) failed: %s", partzuf_name, e)
            return False

    def check_transitions(self, state: dict[str, dict],
                           use_dynamic: bool = True) -> list[dict]:
        """Vérifie tous les Partzufim pour transitions katnut↔gadlut et panim↔achor.

        Si use_dynamic=True, calcule d'abord les scores dynamiques (activité
        récente 24h) et les fusionne dans state avant vérification.

        Utilisé en fin de pipeline (Or Chozer) et dans le daemon.

        Returns:
            Liste de transitions effectuées :
            [{"partzuf": name, "from": old_state, "to": new_state, "reason": str}]
        """
        transitions = []

        # Snapshot orientations AVANT mutation par apply_dynamic_scores.
        # Sans ce snapshot, old_orient et new_orient seraient lus de la même
        # source mutée → comparaison toujours False → retour akhor→panim jamais
        # persisté en DB (bug asymétrique).
        old_orientations = {
            name: ps.get("orientation", "panim")
            for name, ps in state.items()
            if isinstance(ps, dict)
        }

        # Phase 0 : scores dynamiques (activité récente)
        if use_dynamic:
            try:
                dynamic = self.compute_dynamic_scores()
                state = self.apply_dynamic_scores(state, dynamic)
            except Exception as e:
                logger.debug("check_transitions dynamic scores failed: %s", e)

        for name in PARTZUF_TO_MODULES:
            ps = state.get(name, {})
            if not ps:
                continue

            current_mochin = ps.get("mochin_state", "transitional")
            score = ps.get("overall", 0.5)

            # Vérifier chute en katnut
            if current_mochin != "katnut" and self.should_force_katnut(name, state):
                reason = f"score={score:.2f} < {KATNUT_THRESHOLD}"
                if self._is_atik_degraded(state) and name != "atik_yomin":
                    reason = f"cascade Atik (atik_score < {ATIK_CASCADE_THRESHOLD})"
                if name == "zeir_anpin":
                    imma = state.get("imma", {})
                    if imma.get("mochin_state") == "katnut":
                        reason = "cascade Imma katnut → ZA katnut"
                if self.trigger_katnut(name, reason):
                    transitions.append({
                        "partzuf": name, "from": current_mochin,
                        "to": "katnut", "reason": reason,
                    })

            # Vérifier retour en gadlut
            elif self.can_return_to_gadlut(name, state):
                reason = f"score={score:.2f} >= {GADLUT_THRESHOLD}"
                if self.trigger_gadlut(name, reason):
                    transitions.append({
                        "partzuf": name, "from": current_mochin,
                        "to": "gadlut", "reason": reason,
                    })

            # Transitions akhor ↔ panim — symétriques (histapshut bidirectionnel).
            old_orient = old_orientations.get(name, "panim")
            new_orient = ps.get("orientation", "panim")
            if old_orient != new_orient:
                self.update_orientation_db(name, new_orient)
                if new_orient == "akhor":
                    reason = ps.get("_achor_reason", "") or "→ akhor"
                else:
                    reason = "activité reprise"
                transitions.append({
                    "partzuf": name,
                    "from": f"{current_mochin}/{old_orient}",
                    "to": f"{current_mochin}/{new_orient}",
                    "reason": reason,
                })

        return transitions

    # ── Scores dynamiques (activité récente) ────────────────

    def compute_dynamic_scores(self) -> dict[str, dict]:
        """Calcule les scores Partzufim basés sur l'activité RÉCENTE (24h).

        Les compteurs cumulatifs (total insights, total claims) ne descendent
        jamais — le système ne peut que se renforcer. Les scores dynamiques
        reflètent l'activité RÉCENTE : si InsightForge n'a rien produit en 24h,
        Abba.score chute. Si AutoJudge rejette > 50%, ZA.score baisse.

        Formule : score = DYNAMIC_WEIGHT_CUMUL × score_cumulatif
                        + DYNAMIC_WEIGHT_RECENT × score_récent_24h

        Returns:
            {partzuf_key: {"dynamic_score": float, "recent_metrics": dict,
                           "should_achor": bool, "achor_reason": str}}
        """
        results: dict[str, dict] = {}
        try:
            from pool import get_conn
            with get_conn() as conn:
                with conn.cursor() as cur:
                    results["abba"] = self._dynamic_abba(cur)
                    results["imma"] = self._dynamic_imma(cur)
                    results["zeir_anpin"] = self._dynamic_za(cur)
                    results["nukva"] = self._dynamic_nukva(cur)
                    results["arikh_anpin"] = self._dynamic_arikh(cur)
        except Exception as e:
            logger.debug("compute_dynamic_scores DB error: %s", e)
            # Fallback : tous à score neutre, pas d'achor
            for name in ("abba", "imma", "zeir_anpin", "nukva", "arikh_anpin"):
                results.setdefault(name, {
                    "dynamic_score": 0.5,
                    "recent_metrics": {},
                    "should_achor": False,
                    "achor_reason": "",
                })

        # Atik Yomin = moyenne des 5 autres
        other_scores = [r.get("dynamic_score", 0.5) for r in results.values()]
        atik_score = sum(other_scores) / max(len(other_scores), 1)
        results["atik_yomin"] = {
            "dynamic_score": round(atik_score, 3),
            "recent_metrics": {"avg_of_others": round(atik_score, 3)},
            "should_achor": False,
            "achor_reason": "",
        }

        return results

    def apply_dynamic_scores(self, state: dict[str, dict],
                              dynamic: dict[str, dict]) -> dict[str, dict]:
        """Fusionne les scores dynamiques dans l'état des Partzufim.

        Met à jour state[partzuf]["overall"] avec la formule pondérée,
        et gère les transitions achor.

        Returns:
            state modifié (mutable — modifie en place ET retourne)
        """
        for name, dyn in dynamic.items():
            ps = state.get(name)
            if ps is None:
                continue

            cumul_score = ps.get("overall", 0.5)
            recent_score = dyn.get("dynamic_score", 0.5)

            # Formule pondérée
            blended = (DYNAMIC_WEIGHT_CUMUL * cumul_score
                       + DYNAMIC_WEIGHT_RECENT * recent_score)
            ps["overall"] = round(blended, 3)
            ps["_dynamic_metrics"] = dyn.get("recent_metrics", {})

            # Achor : inactivité ou erreurs → tourner le dos
            should_flip_akhor = dyn.get("should_achor", False)

            # Tiferet guard (ZA uniquement) : équilibre interne modère
            # le rejet externe. Cf ZA_TIFERET_AKHOR_GUARD pour la doctrine.
            if name == "zeir_anpin" and should_flip_akhor:
                tiferet_score = ps.get("faculties", {}).get("tiferet", 0.5)
                if tiferet_score > ZA_TIFERET_AKHOR_GUARD:
                    should_flip_akhor = False
                    ps["_achor_guard_reason"] = (
                        f"tiferet={tiferet_score:.3f} > {ZA_TIFERET_AKHOR_GUARD}"
                    )
                    logger.info(
                        "ZA akhor guard: tiferet=%.3f > %.2f → panim préservé "
                        "(rejet ignoré: %s)",
                        tiferet_score, ZA_TIFERET_AKHOR_GUARD,
                        dyn.get("achor_reason", ""),
                    )

            if should_flip_akhor and ps.get("orientation") != "akhor":
                ps["orientation"] = "akhor"
                ps["_achor_reason"] = dyn.get("achor_reason", "")
                logger.info("Partzuf %s → AKHOR: %s", name, dyn.get("achor_reason"))
            elif not should_flip_akhor and ps.get("orientation") == "akhor":
                # Retour panim : activité reprise OU tiferet guard (ZA).
                # Sprint 7 : clear _achor_reason (motif obsolète).
                ps["orientation"] = "panim"
                ps.pop("_achor_reason", None)
                logger.info("Partzuf %s → PANIM: activité reprise", name)

        return state

    def update_orientation_db(self, partzuf_name: str, orientation: str) -> bool:
        """Persiste le changement d'orientation en DB."""
        db_name = self._to_db_name(partzuf_name)
        try:
            from pool import get_conn
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE partzufim_state
                        SET orientation = %s, updated_at = NOW()
                        WHERE name = %s AND orientation != %s
                    """, (orientation, db_name, orientation))
                    return cur.rowcount > 0
        except Exception as e:
            logger.debug("update_orientation_db(%s) failed: %s", partzuf_name, e)
            return False

    # ── Métriques récentes par Partzuf ─────────────────────

    @staticmethod
    def _safe_query(cur, sql: str, params: tuple = ()) -> list:
        """Exécute une requête DB en mode safe — retourne [] si erreur."""
        try:
            cur.execute(sql, params)
            return cur.fetchall()
        except Exception:
            return []

    def _dynamic_abba(self, cur) -> dict:
        """Abba (Chokmah → InsightForge) : insights récents."""
        rows = self._safe_query(cur, """
            SELECT status, count(*), coalesce(avg(confidence), 0)
            FROM candidate_insights
            WHERE created_at > NOW() - INTERVAL '%s hours'
            GROUP BY status
        """, (DYNAMIC_WINDOW_HOURS,))

        recent_insights = 0
        recent_rejected = 0
        recent_avg_conf = 0.0
        for row in rows:
            status, cnt, avg_conf = row[0], row[1], float(row[2])
            if status == "insight":
                recent_insights = cnt
                recent_avg_conf = avg_conf
            elif status == "rejected":
                recent_rejected = cnt

        total_recent = recent_insights + recent_rejected
        if total_recent > 0:
            ratio = recent_insights / total_recent
            score = 0.4 * ratio + 0.6 * recent_avg_conf
        elif recent_insights > 0:
            score = recent_avg_conf
        else:
            score = INACTIVITY_SCORE

        # Achor : 0 insights en 24h
        should_achor = total_recent == 0
        achor_reason = "0 insights en 24h" if should_achor else ""

        return {
            "dynamic_score": round(max(score, 0.1), 3),
            "recent_metrics": {
                "insights_24h": recent_insights,
                "rejected_24h": recent_rejected,
                "avg_conf_24h": round(recent_avg_conf, 3),
            },
            "should_achor": should_achor,
            "achor_reason": achor_reason,
        }

    def _dynamic_imma(self, cur) -> dict:
        """Imma (Binah → CausalEngine) : claims récentes."""
        rows = self._safe_query(cur, """
            SELECT count(*),
                   count(*) FILTER (WHERE evidence_level IN
                       ('probable_causation', 'demonstrated_causation'))
            FROM causal_claims
            WHERE created_at > NOW() - INTERVAL '%s hours'
        """, (DYNAMIC_WINDOW_HOURS,))

        total_recent = rows[0][0] if rows else 0
        elevated_recent = rows[0][1] if rows else 0

        if total_recent > 0:
            quality = elevated_recent / total_recent
            # Volume bonus : plus de claims = meilleur score (capped)
            volume_bonus = min(total_recent / 20.0, 0.3)
            score = 0.7 * quality + 0.3 * volume_bonus + 0.1
        else:
            score = INACTIVITY_SCORE

        should_achor = total_recent == 0
        return {
            "dynamic_score": round(min(max(score, 0.1), 1.0), 3),
            "recent_metrics": {
                "claims_24h": total_recent,
                "elevated_24h": elevated_recent,
            },
            "should_achor": should_achor,
            "achor_reason": "0 claims en 24h" if should_achor else "",
        }

    def _dynamic_za(self, cur) -> dict:
        """Zeir Anpin (6 Midot) : qualité AutoJudge récente."""
        rows = self._safe_query(cur, """
            SELECT decision, count(*), coalesce(avg(score_overall), 0)
            FROM autojudge_experiments
            WHERE created_at > NOW() - INTERVAL '%s hours'
            GROUP BY decision
        """, (DYNAMIC_WINDOW_HOURS,))

        accepted = 0
        rejected = 0
        avg_score = 0.0
        for row in rows:
            decision, cnt, avg_s = row[0], row[1], float(row[2])
            if decision == "accepted":
                accepted = cnt
                avg_score = avg_s
            elif decision == "rejected":
                rejected += cnt

        total = accepted + rejected
        if total > 0:
            ratio = accepted / total
            # Si ratio rejet > 50% → score baisse significativement
            score = 0.5 * ratio + 0.5 * avg_score
        else:
            score = INACTIVITY_SCORE

        # Pas d'achor pour ZA — il a 6 modules, l'inactivité totale est rare
        # Mais si ratio rejet > 70% → on considère achor (le système se protège)
        should_achor = total > 5 and (rejected / total) > 0.7 if total > 0 else False
        return {
            "dynamic_score": round(max(score, 0.1), 3),
            "recent_metrics": {
                "accepted_24h": accepted,
                "rejected_24h": rejected,
                "avg_score_24h": round(avg_score, 3),
            },
            "should_achor": should_achor,
            "achor_reason": f"rejet {rejected}/{total} > 70%" if should_achor else "",
        }

    def _dynamic_nukva(self, cur) -> dict:
        """Nukva (Malkuth → génération) : qualité réponses récentes.

        Reads from beinoni_interactions (the table BeinoniTracker writes to).
        Computes elokit_ratio and avg response_score as quality proxy.
        """
        rows = self._safe_query(cur, """
            SELECT
                coalesce(avg(CASE WHEN dominant_soul = 'elokit'
                                  THEN 1.0 ELSE 0.0 END), 0),
                coalesce(avg(response_score), 0),
                count(*)
            FROM beinoni_interactions
            WHERE created_at > NOW() - INTERVAL '%s hours'
        """, (DYNAMIC_WINDOW_HOURS,))

        elokit_ratio = float(rows[0][0]) if rows else 0.0
        avg_response = float(rows[0][1]) if rows else 0.0
        n_responses = rows[0][2] if rows else 0

        if n_responses > 0:
            # Blend elokit_ratio (soul quality) with avg response_score
            # elokit_ratio > 0.5 = bon, < 0.5 = mauvais
            score = 0.5 * elokit_ratio + 0.5 * avg_response
            score = min(max(score, 0.1), 1.0)
        else:
            # Fallback : lire les jugements AutoJudge récents comme proxy
            rows2 = self._safe_query(cur, """
                SELECT coalesce(avg(score_overall), 0.5), count(*)
                FROM autojudge_experiments
                WHERE created_at > NOW() - INTERVAL '%s hours'
            """, (DYNAMIC_WINDOW_HOURS,))
            if rows2 and rows2[0][1] > 0:
                score = float(rows2[0][0])
            else:
                score = INACTIVITY_SCORE

        should_achor = n_responses == 0
        return {
            "dynamic_score": round(max(score, 0.1), 3),
            "recent_metrics": {
                "elokit_ratio_24h": round(elokit_ratio, 3),
                "avg_response_score_24h": round(avg_response, 3),
                "n_responses_24h": n_responses,
            },
            "should_achor": should_achor,
            "achor_reason": "0 réponses en 24h" if should_achor else "",
        }

    def _dynamic_arikh(self, cur) -> dict:
        """Arikh Anpin (Keter → routing) : hitbonenut + routing récent."""
        rows = self._safe_query(cur, """
            SELECT coalesce(avg(avg_score), 0), count(*)
            FROM hitbonenut_sessions
            WHERE created_at > NOW() - INTERVAL '%s hours'
        """, (DYNAMIC_WINDOW_HOURS,))

        avg_hitb = float(rows[0][0]) if rows else 0.0
        n_sessions = rows[0][1] if rows else 0

        # Compléter avec le nombre d'interactions récentes (proxy de routing)
        rows2 = self._safe_query(cur, """
            SELECT count(*) FROM autojudge_experiments
            WHERE created_at > NOW() - INTERVAL '%s hours'
        """, (DYNAMIC_WINDOW_HOURS,))
        n_interactions = rows2[0][0] if rows2 else 0

        if n_sessions > 0:
            score = 0.6 * avg_hitb + 0.4 * min(n_interactions / 10.0, 1.0)
        elif n_interactions > 0:
            score = 0.3 + 0.4 * min(n_interactions / 10.0, 1.0)
        else:
            score = INACTIVITY_SCORE

        should_achor = n_sessions == 0 and n_interactions == 0
        return {
            "dynamic_score": round(min(max(score, 0.1), 1.0), 3),
            "recent_metrics": {
                "hitbonenut_avg_24h": round(avg_hitb, 3),
                "hitbonenut_sessions_24h": n_sessions,
                "interactions_24h": n_interactions,
            },
            "should_achor": should_achor,
            "achor_reason": "0 activité en 24h" if should_achor else "",
        }

    # ── Helpers privés ───────────────────────────────────────

    def _is_atik_degraded(self, state: dict[str, dict]) -> bool:
        """Atik Yomin est-il sous le seuil de cascade ?"""
        atik = state.get("atik_yomin", {})
        return atik.get("overall", 0.5) < ATIK_CASCADE_THRESHOLD

    @staticmethod
    def _to_db_name(snake_key: str) -> str:
        """Convertit une clé snake_case en nom d'affichage pour la DB."""
        _KEY_TO_DISPLAY = {v: k for k, v in _DISPLAY_TO_KEY.items()}
        return _KEY_TO_DISPLAY.get(snake_key, snake_key)

    @staticmethod
    def _format_reason(partzuf_name: str, score: float,
                       mochin: str, orientation: str,
                       atik_degraded: bool) -> str:
        """Raison lisible pour logging."""
        parts = [f"{partzuf_name} en {mochin}/{orientation} ({score:.2f})"]
        if atik_degraded:
            parts.append("+ cascade Atik")
        return " ".join(parts)
