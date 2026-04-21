"""MazalEngine Phase 3 — rectification active (Sprint 10 Phase C).

3 modes :
    - ``observe`` : detect + signal uniquement (comportement Sprint 9, défaut).
    - ``suggest`` : observe + émet un event ``mazal_action_proposed`` décrivant
      l'action concrète proposée — SANS l'appliquer.
    - ``act`` : suggest + applique effectivement l'action (Omer adjust,
      UPDATE causal_claims.abandoned).

**Opt-in** : le mode ``act`` doit être explicitement activé (env var
``MAZAL_RECTIFICATION_MODE=act`` ou ``config.yaml/mazalengine.rectification_mode: act``).
Par défaut ``observe`` pour respecter le prérequis doctrinal "observer 2-4 semaines
avant d'appliquer des actions automatiques" (HANDOFF §C.3).

**Hitlabshut (EC-K5-008)** : aucune écriture sur ``partzufim_state``. Les
rectifications agissent sur ``omer_history`` (paramètres de calibration) et
``causal_claims`` (flag ``abandoned``) — orthogonales aux Kelim des Partzufim.
"""

from __future__ import annotations

import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

log = logging.getLogger("etz-mazalengine")


class RectificationMode:
    OBSERVE = "observe"
    SUGGEST = "suggest"
    ACT = "act"

    ALL = (OBSERVE, SUGGEST, ACT)


def load_mode(explicit: str | None = None) -> str:
    """Résout le mode: explicit arg > env var > config.yaml > default `observe`."""
    if explicit and explicit in RectificationMode.ALL:
        return explicit
    env = os.environ.get("MAZAL_RECTIFICATION_MODE")
    if env and env in RectificationMode.ALL:
        return env
    try:
        cfg_path = Path(__file__).resolve().parent.parent / "config.yaml"
        if cfg_path.exists():
            cfg = yaml.safe_load(cfg_path.read_text()) or {}
            mode = (cfg.get("mazalengine") or {}).get("rectification_mode")
            if mode in RectificationMode.ALL:
                return mode
    except (OSError, yaml.YAMLError):
        pass
    return RectificationMode.OBSERVE


@dataclass
class ProposedAction:
    """Action concrète proposée par un Mazal (sans encore être appliquée)."""

    mazal: str  # "elyon" | "tahton"
    tikkun: str  # "notzer_chesed" | "ve_nakeh"
    action_type: str  # "omer_adjust" | "claim_abandon"
    target: str  # module ou table cible
    params: dict = field(default_factory=dict)
    reason: str = ""
    doctrine_ref: str = "EC-K5-001"


# ══════════════════════════════════════════════════════════════════
#  NOTZER CHESED — rectification Omer ExplorationEngine
# ══════════════════════════════════════════════════════════════════


class NotzerChesedRectifier:
    """En cas de Chesed starvation, ajuste l'Omer pour relancer le flux.

    Action : `explore_breadth += BREADTH_BOOST` et `novelty_threshold += NOVELTY_RELAX`
    via ``OmerManager.apply``, qui persiste l'override dans ``omer_history`` et
    invalide le cache module.
    """

    MODULE: str = "explorationengine"
    BREADTH_BOOST: int = 5
    NOVELTY_RELAX: float = -0.1

    def propose(self, deviation: dict) -> ProposedAction:
        return ProposedAction(
            mazal="elyon",
            tikkun="notzer_chesed",
            action_type="omer_adjust",
            target=self.MODULE,
            params={
                "explore_breadth_delta": self.BREADTH_BOOST,
                "novelty_threshold_delta": self.NOVELTY_RELAX,
            },
            reason=(f"chesed starvation on {deviation.get('window_hours', 24)}h window"),
        )

    def apply(self, action: ProposedAction, db_url: str | None = None) -> dict:
        """Applique l'ajustement via OmerManager.apply. Retourne event."""
        try:
            from omer import get_param
            from omer.core import OmerManager, Suggestion
        except ImportError as exc:
            log.debug("NotzerChesed: omer unavailable (%s)", exc)
            return self._failure_event("omer_unavailable")

        url = db_url or os.environ.get(
            "ETZ_CHAIM_DB_URL",
            "postgresql://postgres@localhost:5432/etz_chaim",
        )

        current_breadth = get_param(self.MODULE, "explore_breadth", 10)
        current_novelty = get_param(self.MODULE, "novelty_threshold", 0.3)
        new_breadth = int(current_breadth) + int(action.params["explore_breadth_delta"])
        new_novelty = max(
            0.0,
            min(1.0, float(current_novelty) + float(action.params["novelty_threshold_delta"])),
        )

        suggestions = [
            Suggestion(
                key="chesed_dans_chesed",
                param="explore_breadth",
                sephirah="chesed",
                inner="chesed",
                module=self.MODULE,
                old_value=current_breadth,
                new_value=new_breadth,
                reason=f"MazalEngine Notzer Chesed — {action.reason}",
                severity="info",
            ),
            Suggestion(
                key="gevurah_dans_chesed",
                param="novelty_threshold",
                sephirah="chesed",
                inner="gevurah",
                module=self.MODULE,
                old_value=current_novelty,
                new_value=new_novelty,
                reason=f"MazalEngine Notzer Chesed — {action.reason}",
                severity="info",
            ),
        ]

        try:
            mgr = OmerManager(url)
            n = mgr.apply(suggestions)
        except Exception as exc:
            log.debug("NotzerChesed apply failed: %s", exc)
            return self._failure_event(f"omer_apply_failed: {exc}")

        return {
            "mazal": "elyon",
            "tikkun": "notzer_chesed",
            "action": "omer_adjusted",
            "doctrine_ref": action.doctrine_ref,
            "applied": n,
            "adjustments": [
                {
                    "param": s.param,
                    "old": s.old_value,
                    "new": s.new_value,
                }
                for s in suggestions
            ],
        }

    def _failure_event(self, reason: str) -> dict:
        return {
            "mazal": "elyon",
            "tikkun": "notzer_chesed",
            "action": "omer_adjust_skipped",
            "doctrine_ref": "EC-K5-001",
            "reason": reason,
        }


# ══════════════════════════════════════════════════════════════════
#  VE-NAKEH — rectification causal_claims.abandoned
# ══════════════════════════════════════════════════════════════════


class VeNakehRectifier:
    """Marque les causal_claims stales comme ``abandoned`` après N cycles répétés.

    Le compteur de cycles est porté dans ``self._cycle_count`` — incrémenté
    à chaque ``propose()`` appelé avec une starvation active. L'abandon n'est
    appliqué que si ``_cycle_count >= STALE_CYCLES_BEFORE_ABANDON``.

    Aucune suppression — respecte le Reshimu (trace préservée). Le flag
    ``abandoned=TRUE`` signale simplement "hors cycle actif" pour les
    requêtes courantes.
    """

    STALE_CYCLES_BEFORE_ABANDON: int = 3

    def __init__(self) -> None:
        self._cycle_count: int = 0

    def propose(self, deviation: dict) -> ProposedAction:
        self._cycle_count += 1
        return ProposedAction(
            mazal="tahton",
            tikkun="ve_nakeh",
            action_type="claim_abandon",
            target="causal_claims",
            params={
                "stale_days": deviation.get("threshold_days", 30),
                "stale_cycles": self._cycle_count,
                "min_cycles_before_abandon": self.STALE_CYCLES_BEFORE_ABANDON,
            },
            reason=(
                f"{deviation.get('metrics', {}).get('stale_count', 0)} "
                f"stale claims, cycle {self._cycle_count}"
                f"/{self.STALE_CYCLES_BEFORE_ABANDON}"
            ),
        )

    def reset_cycle_count(self) -> None:
        """Réinitialise le compteur (appelé quand starvation se résout)."""
        self._cycle_count = 0

    def apply(self, action: ProposedAction, db_url: str | None = None) -> dict:
        """Applique ``UPDATE causal_claims SET abandoned=TRUE`` si seuil atteint."""
        if action.params["stale_cycles"] < action.params["min_cycles_before_abandon"]:
            return {
                "mazal": "tahton",
                "tikkun": "ve_nakeh",
                "action": "abandon_deferred",
                "doctrine_ref": action.doctrine_ref,
                "reason": (
                    f"cycle {action.params['stale_cycles']} < "
                    f"{action.params['min_cycles_before_abandon']}"
                ),
            }

        try:
            from pool import get_conn
        except ImportError:
            return self._failure_event("pool_unavailable")

        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "ALTER TABLE causal_claims ADD COLUMN IF NOT EXISTS "
                        "abandoned BOOLEAN DEFAULT FALSE"
                    )
                    cur.execute(
                        "UPDATE causal_claims SET abandoned = TRUE "
                        "WHERE confounders_controlled = FALSE "
                        "AND created_at < NOW() - make_interval(days => %s) "
                        "AND COALESCE(abandoned, FALSE) = FALSE",
                        (int(action.params["stale_days"]),),
                    )
                    abandoned_count = cur.rowcount
        except Exception as exc:
            log.debug("VeNakeh apply failed: %s", exc)
            return self._failure_event(f"update_failed: {exc}")

        self._cycle_count = 0
        return {
            "mazal": "tahton",
            "tikkun": "ve_nakeh",
            "action": "claims_abandoned",
            "doctrine_ref": action.doctrine_ref,
            "abandoned_count": int(abandoned_count or 0),
        }

    def _failure_event(self, reason: str) -> dict:
        return {
            "mazal": "tahton",
            "tikkun": "ve_nakeh",
            "action": "abandon_skipped",
            "doctrine_ref": "EC-K5-001",
            "reason": reason,
        }


def action_to_event(action: ProposedAction) -> dict:
    """Convertit ProposedAction en event structuré pour daemon_events.jsonl."""
    d = asdict(action)
    d["event_type"] = "mazal_action_proposed"
    return d
