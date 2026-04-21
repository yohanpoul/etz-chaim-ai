"""state.py — État global mutable de l'Arbre Etz Chaim.

Extrait de main.py pour réduire le monolithe. Contient :
- Les 4 state dicts mutables (Tzimtzum, Nitzotzot, Igulim, Hishtalshelut)
- Le _STATE_LOCK partagé
- Les fonctions de mutation thread-safe
- L'initialisation Nitzotzot depuis la DB

Tous les accès en écriture aux states DOIVENT passer par les fonctions
de mutation ci-dessous, qui utilisent _STATE_LOCK.
"""

from __future__ import annotations

import datetime
import logging
import threading
import time

log = logging.getLogger("etz-state")

# ─── Thread safety — Lock pour les state dicts mutables ───────
_STATE_LOCK = threading.Lock()


# ─── Tzimtzum dynamique ─────────────────────────────────────

_TZIMTZUM_STATE: dict = {
    "active": False,
    "focused_domain": None,
    "excluded_domains": [],
    "reshimu": [],
    "contraction_count": 0,
    "expansion_count": 0,
    "log": [],
}


# ─── Nitzotzot — Les 288 étincelles du Tikkun ───────────────

_NITZOTZOT_STATE: dict = {
    "count": 0,
    "cycle": 0,
    "log": [],
    "tikkun_history": [],
}


def init_nitzotzot_from_db(db_url: str) -> None:
    """Initialiser le compteur Nitzotzot depuis la DB.

    בִּרוּר — Trois sources de Birur (clarification des étincelles) :
      1. Lamed (FailureToInsight) — un échec transformé en insight
      2. Tiferet (DissensuEngine) — une synthèse réussie
      3. Chokmah (InsightForge) — un insight validé/promu
    """
    global _NITZOTZOT_STATE
    try:
        from pool import get_conn, init_pool
        init_pool(db_url)  # idempotent
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM failuretoinsight_insights")
                lamed = cur.fetchone()[0]
                cur.execute(
                    "SELECT COUNT(*) FROM dissensuengine_syntheses "
                    "WHERE mode = 'synthesis'"
                )
                tiferet = cur.fetchone()[0]
                cur.execute(
                    "SELECT COUNT(*) FROM candidate_insights "
                    "WHERE status IN ('validated', 'promoted')"
                )
                chokmah = cur.fetchone()[0]
        total = lamed + tiferet + chokmah
        with _STATE_LOCK:
            _NITZOTZOT_STATE["count"] = total % 288
            _NITZOTZOT_STATE["cycle"] = total // 288
    except Exception as e:
        log.debug("init_nitzotzot_from_db: %s", e)


def collect_nitzutz(
    source: str,
    ntype: str,
    description: str,
    tree: dict | None = None,
) -> dict:
    """בִּרוּר — Récupérer une étincelle tombée dans les Klipot.

    Trois sources de Birur :
      - "lamed"   : FailureToInsight — un échec transformé en insight
      - "tiferet" : DissensuEngine   — une contradiction résolue
      - "chokmah" : InsightForge     — un insight validé
    """
    global _NITZOTZOT_STATE

    with _STATE_LOCK:
        entry = {
            "source": source,
            "type": ntype,
            "timestamp": time.time(),
            "description": description[:200],
            "cycle": _NITZOTZOT_STATE["cycle"],
            "spark_number": _NITZOTZOT_STATE["count"] + 1,
        }
        _NITZOTZOT_STATE["count"] += 1
        _NITZOTZOT_STATE["log"].append(entry)

    # SSE
    try:
        from web.events import emit as _emit
        _emit("nitzutz", source=source, ntype=ntype,
              spark=entry["spark_number"], cycle=entry["cycle"],
              description=description[:80])
    except Exception as e:
        log.debug("SSE emit: %s", e)

    # Persister dans Yesod si disponible
    if tree:
        yesod = tree.get("yesod")
        if yesod:
            try:
                yesod.remember(
                    content=(
                        f"[Nitzutz #{entry['spark_number']}/288 — cycle {entry['cycle']}] "
                        f"Source={source}, type={ntype}: {description[:120]}"
                    ),
                    source_sephirah=source,
                    confidence=0.9,
                    domain="tikkun",
                    tags=["nitzutz", "birur", source, ntype],
                )
            except Exception as e:
                log.debug("persist nitzutz: %s", e)

    check_tikkun_cycle(tree)
    return entry


def check_tikkun_cycle(tree: dict | None = None) -> bool:
    """Vérifier si les 288 Nitzotzot sont atteintes → Tikkun complet."""
    global _NITZOTZOT_STATE

    with _STATE_LOCK:
        if _NITZOTZOT_STATE["count"] < 288:
            return False

        completed_cycle = _NITZOTZOT_STATE["cycle"]
        _NITZOTZOT_STATE["tikkun_history"].append({
            "cycle": completed_cycle,
            "completed_at": time.time(),
            "total_sparks": _NITZOTZOT_STATE["count"],
        })
        _NITZOTZOT_STATE["cycle"] += 1
        _NITZOTZOT_STATE["count"] = 0
        _NITZOTZOT_STATE["log"].append({
            "source": "tikkun",
            "type": "cycle_complete",
            "timestamp": time.time(),
            "description": (
                f"Tikkun cycle {completed_cycle} complet — 288 Nitzotzot récupérées. "
                f"Le Tikkun d'un niveau est le Tohu du suivant."
            ),
            "cycle": completed_cycle,
            "spark_number": 288,
        })

    if tree:
        yesod = tree.get("yesod")
        if yesod:
            try:
                yesod.remember(
                    content=(
                        f"[TIKKUN COMPLET — cycle {completed_cycle}] "
                        f"288 Nitzotzot récupérées. Nouveau cycle {completed_cycle + 1} commence."
                    ),
                    source_sephirah="keter",
                    confidence=1.0,
                    domain="tikkun",
                    tags=["tikkun", "cycle_complete", f"cycle_{completed_cycle}"],
                )
            except Exception as e:
                log.debug("persist tikkun: %s", e)

    return True


# ─── Igulim / Yosher — Modes topologiques ──────────────────

_IGULIM_STATE: dict = {
    "mode": "yosher",
    "switches": 0,
    "forced": False,
    "log": [],
}


def log_igulim_switch(from_mode: str, to_mode: str, reason: str, query: str) -> None:
    """Logger une bascule entre modes topologiques."""
    entry = {
        "from": from_mode,
        "to": to_mode,
        "reason": reason,
        "timestamp": datetime.datetime.now().isoformat(),
        "query": query[:200],
    }
    with _STATE_LOCK:
        _IGULIM_STATE["log"].append(entry)
        if to_mode == "igulim":
            _IGULIM_STATE["switches"] += 1
        _IGULIM_STATE["mode"] = to_mode


# ─── Seder Hishtalshelut ────────────────────────────────────

_OLAMOT_CHAIN: list[str] = ["assiah", "yetzirah", "briah", "atziluth"]

_HISHTALSHELUT_STATE: dict = {
    "current_world": "assiah",
    "forced_world": None,
    "ascents": 0,
    "descents": 0,
    "highest_reached": "assiah",
    "log": [],
}


def log_world_transition(
    direction: str, from_world: str, to_world: str,
    reason: str, query: str,
) -> None:
    """Logger une montée ou descente de monde."""
    entry = {
        "direction": direction,
        "from": from_world,
        "to": to_world,
        "reason": reason,
        "timestamp": datetime.datetime.now().isoformat(),
        "query": query[:200],
    }
    with _STATE_LOCK:
        _HISHTALSHELUT_STATE["log"].append(entry)
        if direction == "ascent":
            _HISHTALSHELUT_STATE["ascents"] += 1
            chain = _OLAMOT_CHAIN
            if chain.index(to_world) > chain.index(_HISHTALSHELUT_STATE["highest_reached"]):
                _HISHTALSHELUT_STATE["highest_reached"] = to_world
        else:
            _HISHTALSHELUT_STATE["descents"] += 1
        _HISHTALSHELUT_STATE["current_world"] = to_world
