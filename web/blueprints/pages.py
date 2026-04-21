"""pages_bp — pages HTML + /health.

Audit cycle 4, N1 phase 3 — extraction des 15 routes "pages" depuis
web/app.py (templates HTML, redirects, /health).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from flask import Blueprint, redirect, render_template

from web.app import _json_response

pages_bp = Blueprint("pages", __name__)

_FRONTEND_AVATAR = Path(__file__).resolve().parent.parent.parent / "frontend-avatar"
_FRONTEND_SYSTEME = Path(__file__).resolve().parent.parent.parent / "frontend-systeme"


def _load_json(path: Path) -> dict | list:
    """Charger un JSON, retourner {} si introuvable / corrompu."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


# ─── Pages templates ────────────────────────────────────────


@pages_bp.route("/")
def page_home():
    return render_template("home.html")


@pages_bp.route("/dashboard")
def page_dashboard():
    return render_template("dashboard.html")


@pages_bp.route("/chat")
def page_chat():
    return render_template("chat.html")


@pages_bp.route("/explore")
def page_explore():
    return render_template("explore.html")


@pages_bp.route("/intentions")
def page_intentions():
    return render_template("intentions.html")


@pages_bp.route("/memory")
def page_memory():
    return render_template("memory.html")


@pages_bp.route("/import")
def page_import():
    return render_template("import.html")


@pages_bp.route("/world")
def page_world():
    return render_template("world.html")


@pages_bp.route("/avatars")
def page_avatars():
    return redirect("/systeme/personnages", code=301)


@pages_bp.route("/systeme")
def page_systeme():
    return render_template("systeme/index.html")


@pages_bp.route("/systeme/personnages")
def page_systeme_personnages():
    data = _load_json(_FRONTEND_AVATAR / "personnages.json")
    actes = data.get("actes", []) if isinstance(data, dict) else []
    return render_template("systeme/personnages.html", actes=actes)


@pages_bp.route("/systeme/arbre")
def page_systeme_arbre():
    data = _load_json(_FRONTEND_SYSTEME / "arbre.json")
    return render_template("systeme/arbre.html", data=data)


@pages_bp.route("/systeme/mondes")
def page_systeme_mondes():
    data = _load_json(_FRONTEND_SYSTEME / "mondes.json")
    return render_template("systeme/mondes.html", data=data)


@pages_bp.route("/systeme/erreurs")
def page_systeme_erreurs():
    data = _load_json(_FRONTEND_SYSTEME / "erreurs.json")
    return render_template("systeme/erreurs.html", data=data)


# ─── Health ─────────────────────────────────────────────────


@pages_bp.route("/health")
def health_check():
    """Endpoint de santé système — vérifie daemon, DB, hitbonenut.

    Retourne 200 (ok), 200 (degraded), ou 503 (down).
    Conçu pour monitoring externe (curl, uptime checks, launchd).
    """
    status = "ok"
    checks: dict = {}

    # 1. DB connectée
    try:
        from pool import get_conn
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        checks["db"] = {"status": "ok"}
    except Exception as e:
        checks["db"] = {"status": "down", "error": str(e)}
        status = "down"

    # 2. Daemon vivant (PID + heartbeat récent)
    try:
        pid_file = Path.home() / ".etz-chaim" / "daemon.pid"
        state_file = Path.home() / ".etz-chaim" / "daemon_state.json"

        if not pid_file.exists():
            checks["daemon"] = {"status": "down", "reason": "no_pid_file"}
            if status != "down":
                status = "degraded"
        else:
            pid = int(pid_file.read_text().strip())
            try:
                os.kill(pid, 0)
                alive = True
            except (OSError, ProcessLookupError):
                alive = False

            if not alive:
                checks["daemon"] = {
                    "status": "down",
                    "reason": "pid_stale",
                    "pid": pid,
                }
                if status != "down":
                    status = "degraded"
            else:
                daemon_info: dict = {"status": "ok", "pid": pid}
                if state_file.exists():
                    try:
                        st = json.loads(state_file.read_text())
                        last_save = st.get("_last_save", 0)
                        age = time.time() - last_save
                        daemon_info["state_age_s"] = round(age, 1)
                        daemon_info["hitbonenut_running"] = st.get(
                            "hitbonenut_running", False
                        )
                        if age > 120:
                            daemon_info["status"] = "stale"
                            if status == "ok":
                                status = "degraded"
                    except Exception as _exc:

                        import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
                checks["daemon"] = daemon_info
    except Exception as e:
        checks["daemon"] = {"status": "error", "error": str(e)}
        if status != "down":
            status = "degraded"

    http_code = 503 if status == "down" else 200
    return _json_response({
        "status": status,
        "timestamp": time.time(),
        "checks": checks,
    }, status=http_code)
