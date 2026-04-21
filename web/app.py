"""web/app.py — Malkuth-de-Malkuth : l'interface web de l'Arbre.

Flask léger, SSE pour le chat, API JSON pour les modules.
"""

from __future__ import annotations

import hmac
import json
import logging
import mimetypes
import os
import time
import traceback
import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Any, Generator

# Register .glb MIME type for Three.js GLTF binary assets
mimetypes.add_type('model/gltf-binary', '.glb')

from flask import (
    Flask, Response, jsonify, redirect, render_template, request, stream_with_context,
)

# ─── JSON encoder pour dataclasses, UUID, datetime ──────────

class TreeEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if is_dataclass(o) and not isinstance(o, type):
            return asdict(o)
        if isinstance(o, uuid.UUID):
            return str(o)
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        # numpy arrays (embeddings) — skip them in JSON output
        try:
            import numpy as np
            if isinstance(o, np.ndarray):
                return None
        except ImportError as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
        return super().default(o)


# ─── Globals ────────────────────────────────────────────────

_tree: dict | None = None
_db_url: str = ""


def _get_tree() -> dict:
    global _tree
    if _tree is None:
        from main import init_tree
        print("  Initialisation de l'Arbre pour le web...")
        _tree = init_tree(_db_url)
        active = sum(1 for v in _tree.values() if v is not None)
        print(f"  {active}/10 modules initialisés")
    return _tree


def _get_db_url() -> str:
    """Accesseur module-level pour _db_url, utilisable par les blueprints."""
    return _db_url


def _db_query(sql: str, params=None) -> list[tuple]:
    """Requête directe PostgreSQL via pool."""
    from pool import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def _json_response(data: Any, status: int = 200) -> Response:
    """Réponse JSON unifiée — encoder dataclasses/UUID/datetime.

    Niveau module : utilisable par les blueprints (web/blueprints/*).
    """
    return Response(
        json.dumps(data, cls=TreeEncoder, ensure_ascii=False),
        status=status,
        mimetype="application/json",
    )


# ─── Flask App ──────────────────────────────────────────────

def create_app(db_url: str | None = None) -> Flask:
    global _db_url
    _db_url = db_url or os.environ.get(
        "ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim"
    )

    # Init connection pool
    from pool import init_pool
    init_pool(_db_url)

    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / "templates"),
        static_folder=str(Path(__file__).parent / "static"),
    )
    app.config["SECRET_KEY"] = os.environ.get("ETZ_CHAIM_SECRET_KEY", "etz-chaim-local-dev")
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0  # No cache for static files

    # ── API Key Authentication (fail-closed) ────────────────
    # Auth OBLIGATOIRE sur /api/* par défaut.
    # Comparaison via hmac.compare_digest (constant-time, anti timing attack).
    # Transport :
    #   - header Authorization: Bearer <key>  (cas général)
    #   - query param ?key=<key>              (UNIQUEMENT SSE : EventSource
    #                                          ne supporte pas les headers custom)
    # Configuration :
    #   - ETZ_CHAIM_API_KEY=<key>    → auth active
    #   - ETZ_CHAIM_ALLOW_ANON=1     → auth désactivée EXPLICITEMENT (dev local)
    #   - ni l'un ni l'autre         → 503 sur /api/* (fail-closed)
    _api_key = os.environ.get("ETZ_CHAIM_API_KEY", "")
    _allow_anon = os.environ.get("ETZ_CHAIM_ALLOW_ANON", "") == "1"
    _sse_paths = frozenset({
        "/api/chat/stream",
        "/api/world/events",
        "/api/dashboard/stream",
    })

    if not _api_key:
        if _allow_anon:
            logging.getLogger(__name__).warning(
                "ETZ_CHAIM_ALLOW_ANON=1 — auth /api/* DÉSACTIVÉE (dev uniquement)."
            )
        else:
            logging.getLogger(__name__).warning(
                "ETZ_CHAIM_API_KEY absente et ETZ_CHAIM_ALLOW_ANON != 1 — "
                "/api/* renverra 503 jusqu'à configuration."
            )

    @app.before_request
    def _check_api_auth() -> Response | None:
        if not request.path.startswith("/api/"):
            return None  # Pages HTML, assets statiques — pas d'auth
        if not _api_key:
            if _allow_anon:
                return None
            return Response(
                json.dumps({
                    "error": "Auth non configurée",
                    "hint": "Définir ETZ_CHAIM_API_KEY, ou ETZ_CHAIM_ALLOW_ANON=1 pour accès anonyme explicite (dev).",
                }),
                status=503,
                mimetype="application/json",
            )
        key_bytes = _api_key.encode()
        # Header Authorization: Bearer <key>
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            provided = auth_header[7:].encode()
            if hmac.compare_digest(provided, key_bytes):
                return None
        # Query param ?key=<key> — SSE endpoints UNIQUEMENT
        if request.path in _sse_paths:
            qkey = request.args.get("key", "").encode()
            if hmac.compare_digest(qkey, key_bytes):
                return None
        return Response(
            json.dumps({
                "error": "Unauthorized",
                "hint": "Authorization: Bearer <key> (?key= autorisé uniquement sur endpoints SSE)",
            }),
            status=401,
            mimetype="application/json",
        )

    # Cache-busting: changes on each server restart
    import hashlib
    _cache_bust = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]

    @app.context_processor
    def inject_cache_bust():
        return {"cache_bust": _cache_bust, "api_key": _api_key}

    # Pages + /health : voir web/blueprints/pages.py (N1).

    # API routes : voir web/blueprints/api.py (N1).

    # Chat CRUD routes : voir web/blueprints/chat.py (N1).

    # ── Enregistrement des blueprints (audit cycle 4, N1) ────
    # Import à l'intérieur de create_app pour éviter le cycle
    # web.app ↔ web.blueprints.chat (chat.py importe depuis web.app).
    from web.blueprints.api import api_bp
    from web.blueprints.chat import chat_bp
    from web.blueprints.pages import pages_bp
    from web.blueprints.sifrei import sifrei_bp
    app.register_blueprint(api_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(sifrei_bp)

    return app
