"""chat_bp — endpoints /api/chat/* (audit cycle 4, N1 phase 1).

Extraction de 10 routes depuis web/app.py :
  - GET  /api/chat/stream                    (SSE streaming réponse LLM)
  - GET  /api/chat/projects                  (liste projets)
  - POST /api/chat/projects                  (création)
  - PUT  /api/chat/projects/<id>             (update)
  - DEL  /api/chat/projects/<id>             (delete)
  - GET  /api/chat/conversations             (liste, par projet ou orphans)
  - POST /api/chat/conversations             (création)
  - PUT  /api/chat/conversations/<id>        (rename / move)
  - DEL  /api/chat/conversations/<id>        (delete)
  - GET  /api/chat/conversations/<id>/messages (historique)
"""

from __future__ import annotations

import json
from typing import Generator

from flask import (
    Blueprint, Response, request, stream_with_context,
)

from web.app import TreeEncoder, _get_tree, _json_response

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")


# ─── SSE streaming chat ─────────────────────────────────────


@chat_bp.route("/stream")
def api_chat_stream():
    message = request.args.get("message", "").strip()
    mode = request.args.get("mode", "auto").strip()
    world = request.args.get("world", "auto").strip()
    conversation_id = request.args.get("conversation_id", "").strip()
    if not message:
        return _json_response({"error": "No message"}, 400)

    # Anti-prompt-injection : neutraliser les patterns dangereux AVANT
    # toute concaténation dans un prompt LLM ou persistance qui sera
    # ensuite rappelée via yesod.recall (vecteur d'empoisonnement).
    from malakhim.adversarial.prompt_guard import guard_user_input
    message = guard_user_input(message)

    # Persister le message user
    if conversation_id:
        try:
            from chat.db import add_message, auto_title, list_messages
            add_message(conversation_id, "user", message, {"mode": mode, "world": world})
            # Auto-titre apres le premier message
            msgs = list_messages(conversation_id, limit=2)
            if len(msgs) <= 1:
                auto_title(conversation_id)
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

    def generate() -> Generator[str, None, None]:
        tree = _get_tree()

        # Phase 1 : Routage (Hod) — détection du domaine
        hod = tree.get("hod")
        domain = "general"
        if hod:
            try:
                route = hod.route(message)
                domain = route.detected_domain or "general"
                yield f"data: {json.dumps({'type': 'route', 'domain': domain, 'score': route.competence_score, 'declined': route.did_decline}, cls=TreeEncoder)}\n\n"
            except Exception as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        # Phase 2 : Rappel mémoire (Yesod) — filtré par domaine
        yesod = tree.get("yesod")
        memories = []
        recall_domain = domain if domain != "general" else None
        if yesod:
            try:
                memories = yesod.recall(message, limit=3, min_confidence=0.3,
                                        domain=recall_domain)
                if memories:
                    mem_lines = []
                    for m in memories:
                        content = m.content[:200] if hasattr(m, "content") else str(m)[:200]
                        conf = m.confidence if hasattr(m, "confidence") else 0.0
                        mem_lines.append({"content": content, "confidence": conf})
                    yield f"data: {json.dumps({'type': 'memory', 'memories': mem_lines}, cls=TreeEncoder, ensure_ascii=False)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'module': 'yesod', 'error': str(e)})}\n\n"

        # Phase 3 : Malakhim — préparation via Heikhalot
        try:
            from malakhim.memuneh.router import Memuneh
            from malakhim.pekidah.registry import PekidahRegistry

            _malakhim_reg = PekidahRegistry()
            _malakhim_memuneh = Memuneh(registry=_malakhim_reg)

            kav = {
                "intention": f"Répondre à : {message[:100]}",
                "critere_succes": "Réponse directe, claire et utile en français",
                "anti_pattern": "Ne pas ignorer la question. Ne pas répondre à autre chose.",
                "domain": domain,
            }
            if world != "auto":
                kav["nature"] = {
                    "atziluth": "strategic", "briah": "analytic",
                    "yetzirah": "execution", "assiah": "mechanic",
                }.get(world, "execution")

            preparation = _malakhim_memuneh.prepare_for_stream(
                prompt=message,
                kavvanah=kav,
            )

            olam = preparation.get("olam", "yetzirah")
            enriched_prompt = preparation.get("enriched_prompt", message)
            malakhim_tier = preparation.get("tier", "medium")
            malakhim_stages = preparation.get("heikhalot_stages", [])
            malakhim_shem = preparation.get("shem_index")
            malakhim_warnings = preparation.get("warnings", [])

        except Exception:
            # Fallback : sélection d'olam originale si malakhim échoue
            if world != "auto":
                olam = world
            elif len(message) > 200 or any(w in message.lower() for w in [
                "pourquoi", "explique", "analyse", "compare",
                "raisonne", "prouve", "causalité", "profond",
            ]):
                olam = "briah"
            else:
                olam = "yetzirah"
            enriched_prompt = f"Réponds en français, de manière claire et structurée.\n\nQuestion : {message}\nRéponse :"
            malakhim_tier = "fallback"
            malakhim_stages = []
            malakhim_shem = None
            malakhim_warnings = []
            preparation = {}

        yield f"data: {json.dumps({'type': 'model', 'olam': olam, 'mode': mode, 'malakhim_tier': malakhim_tier, 'heikhalot_stages': len(malakhim_stages), 'shem': malakhim_shem})}\n\n"

        # Phase 4 : Streaming LLM avec le prompt enrichi par Heikhalot
        prompt = enriched_prompt if enriched_prompt != message else f"Réponds en français, de manière claire et structurée.\n\nQuestion : {message}\nRéponse :"

        try:
            from olamot import ollama_generate_stream

            _facts = None
            if memories:
                from malakhim.adversarial.prompt_guard import guard_memory
                _facts = []
                for m in memories[:3]:
                    raw = m.content if hasattr(m, "content") else str(m)
                    clean, _ = guard_memory(raw, max_len=200)
                    _facts.append(clean)

            full_response = []
            for chunk in ollama_generate_stream(
                olam, prompt,
                kavvanah={
                    "intention": f"Répondre à : {message[:100]}",
                    "critere_succes": "Réponse directe, claire et utile en français",
                    "anti_pattern": "Ne pas ignorer la question.",
                },
                domain=domain,
                facts=_facts,
            ):
                token = chunk.get("response", "")
                if token:
                    full_response.append(token)
                    yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"
                if chunk.get("done"):
                    break

            # Phase 4b : Post-stream — Samael + Reshimo (cycle fermé)
            resp_text = "".join(full_response)
            try:
                post_check = _malakhim_memuneh.post_stream_check(
                    response=resp_text,
                    preparation=preparation,
                    prompt=message,
                    kavvanah=kav,
                )
                samael = post_check.get("samael")
                if samael:
                    yield f"data: {json.dumps({'type': 'samael', 'sephirah': samael['sephirah_source'], 'prescription': samael['prescription'], 'severity': samael['severity']})}\n\n"
            except Exception as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

            # Persister en Yesod (recall sémantique)
            if yesod and full_response:
                try:
                    yesod.remember(
                        content=f"Q: {message[:100]} -> R: {resp_text[:200]}",
                        source_sephirah="malkuth",
                        confidence=0.5,
                        domain=domain,
                        tags=["chat", "web", olam, f"tier:{malakhim_tier}"],
                        ttl_days=30,
                    )
                except Exception as _exc:

                    import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

            # Persister la réponse dans chat_messages
            if conversation_id and resp_text:
                try:
                    from chat.db import add_message as _chat_add
                    _chat_add(conversation_id, "etz", resp_text, {
                        "domain": domain, "olam": olam,
                        "tier": malakhim_tier,
                    })
                except Exception as _exc:

                    import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'module': olam, 'error': str(e)})}\n\n"

        # Envoyer l'état des 29 dimensions après la réponse
        try:
            from masakh.context_monitor import get_last_assessment
            _last = get_last_assessment()
            if _last:
                dims = _last.get("dimensions", [])
                score = _last.get("score_global", 0)
                ok = sum(1 for d in dims if d.get("status") == "\u2713")
                partial = sum(1 for d in dims if d.get("status") == "\u25b3")
                absent = sum(1 for d in dims if d.get("status") == "\u2717")
                na = sum(1 for d in dims if d.get("status") == "\u2014")
                yield f"data: {json.dumps({'type': 'kli', 'score': score, 'ok': ok, 'partial': partial, 'absent': absent, 'na': na, 'total': len(dims)})}\n\n"
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ─── Projets ────────────────────────────────────────────────


@chat_bp.route("/projects")
def api_chat_projects():
    from chat.db import list_projects
    return _json_response(list_projects())


@chat_bp.route("/projects", methods=["POST"])
def api_chat_projects_create():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    if not name:
        return _json_response({"error": "name required"}, 400)
    from chat.db import create_project
    return _json_response(create_project(name, data.get("description")))


@chat_bp.route("/projects/<project_id>", methods=["PUT"])
def api_chat_projects_update(project_id):
    data = request.get_json() or {}
    from chat.db import update_project
    result = update_project(project_id, data.get("name"), data.get("description"))
    if not result:
        return _json_response({"error": "not found"}, 404)
    return _json_response(result)


@chat_bp.route("/projects/<project_id>", methods=["DELETE"])
def api_chat_projects_delete(project_id):
    from chat.db import delete_project
    if delete_project(project_id):
        return _json_response({"ok": True})
    return _json_response({"error": "not found"}, 404)


# ─── Conversations ──────────────────────────────────────────


@chat_bp.route("/conversations")
def api_chat_conversations():
    project_id = request.args.get("project_id")
    orphans = request.args.get("orphans") == "1"
    from chat.db import list_conversations
    return _json_response(list_conversations(project_id=project_id, orphans_only=orphans))


@chat_bp.route("/conversations", methods=["POST"])
def api_chat_conversations_create():
    data = request.get_json() or {}
    from chat.db import create_conversation
    return _json_response(create_conversation(
        title=data.get("title", "Nouvelle conversation"),
        project_id=data.get("project_id"),
    ))


@chat_bp.route("/conversations/<conv_id>", methods=["PUT"])
def api_chat_conversations_update(conv_id):
    data = request.get_json() or {}
    from chat.db import update_conversation
    project_id = data.get("project_id", "UNSET")
    result = update_conversation(conv_id, data.get("title"), project_id)
    if not result:
        return _json_response({"error": "not found"}, 404)
    return _json_response(result)


@chat_bp.route("/conversations/<conv_id>", methods=["DELETE"])
def api_chat_conversations_delete(conv_id):
    from chat.db import delete_conversation
    if delete_conversation(conv_id):
        return _json_response({"ok": True})
    return _json_response({"error": "not found"}, 404)


@chat_bp.route("/conversations/<conv_id>/messages")
def api_chat_messages(conv_id):
    limit = int(request.args.get("limit", 200))
    offset = int(request.args.get("offset", 0))
    from chat.db import list_messages
    return _json_response(list_messages(conv_id, limit=limit, offset=offset))
