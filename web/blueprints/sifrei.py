"""sifrei_bp — pages + API /sifrei-yesod/* et /api/sifrei-yesod/*.

Audit cycle 4, N1 phase 2 — extraction des 7 routes Sifrei Yesod
depuis web/app.py. Toutes les requêtes passent par SifreiYesodQuery
(qui utilise db_url direct car standalone API CLI).
"""

from __future__ import annotations

import json

from flask import Blueprint, jsonify, render_template, request

from web.app import TreeEncoder, _get_db_url

sifrei_bp = Blueprint("sifrei", __name__)


# ─── Pages HTML ─────────────────────────────────────────────


@sifrei_bp.route("/sifrei-yesod")
def page_sifrei_yesod():
    return render_template("sifrei_yesod.html", active="sifrei-yesod")


@sifrei_bp.route("/sifrei-yesod/<sefer_id>")
def page_sifrei_yesod_sefer(sefer_id):
    return render_template(
        "sifrei_yesod_sefer.html", active="sifrei-yesod", sefer_id=sefer_id
    )


@sifrei_bp.route("/sifrei-yesod/concept/<concept_id>")
def page_sifrei_yesod_concept(concept_id):
    return render_template(
        "sifrei_yesod_concept.html", active="sifrei-yesod", concept_id=concept_id
    )


# ─── API JSON ───────────────────────────────────────────────


@sifrei_bp.route("/api/sifrei-yesod/stats")
def api_sifrei_yesod_stats():
    try:
        from sifrei_yesod.api.query import SifreiYesodQuery
        q = SifreiYesodQuery(db_url=_get_db_url())
        return jsonify(q.stats())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@sifrei_bp.route("/api/sifrei-yesod/sefer/<sefer_id>")
def api_sifrei_yesod_sefer(sefer_id):
    try:
        from sifrei_yesod.api.query import SifreiYesodQuery
        q = SifreiYesodQuery(db_url=_get_db_url())
        sefer = q.get_sefer(sefer_id)
        shaarim = q.get_shaarim(sefer_id)
        return json.dumps(
            {"sefer": sefer, "shaarim": shaarim},
            cls=TreeEncoder, ensure_ascii=False,
        ), 200, {"Content-Type": "application/json"}
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@sifrei_bp.route("/api/sifrei-yesod/concept/<concept_id>")
def api_sifrei_yesod_concept(concept_id):
    try:
        from sifrei_yesod.api.query import SifreiYesodQuery
        q = SifreiYesodQuery(db_url=_get_db_url())
        result = q.get_concept(concept_id)
        if not result:
            return jsonify({"error": "Concept introuvable"}), 404
        return json.dumps(
            result, cls=TreeEncoder, ensure_ascii=False,
        ), 200, {"Content-Type": "application/json"}
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@sifrei_bp.route("/api/sifrei-yesod/search")
def api_sifrei_yesod_search():
    query = request.args.get("q", "")
    layer = request.args.get("layer", "all")
    limit = int(request.args.get("limit", 10))
    if not query:
        return jsonify({"error": "Paramètre 'q' requis"}), 400
    try:
        from sifrei_yesod.api.query import SifreiYesodQuery
        q = SifreiYesodQuery(db_url=_get_db_url())
        results = {}
        if layer in ("assertions", "all"):
            results["assertions"] = q.search_assertions(query, limit=limit)
        if layer in ("principes", "all"):
            results["principes"] = q.search_principes(query, limit=limit)
        # Strip embeddings from search results (large vectors, not needed in API)
        for key in ("assertions", "principes"):
            for item in results.get(key, []):
                item.pop("embedding", None)
        return json.dumps(
            results, cls=TreeEncoder, ensure_ascii=False,
        ), 200, {"Content-Type": "application/json"}
    except Exception as e:
        return jsonify({"error": str(e)}), 500
