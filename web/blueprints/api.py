"""api_bp — endpoints /api/* (audit cycle 4, N1 phase 4).

Extraction de 26 routes API depuis web/app.py :
  - /api/status, /api/state, /api/explore, /api/import
  - /api/provider/{status,profiles,switch}
  - /api/intentions (list + create), /api/memory/{search,stats,contradictions}
  - /api/omer, /api/omer/today
  - /api/world/{events,test-event,recent}
  - /api/daemon/state, /api/pause/<>, /api/go/<>
  - /api/clustering, /api/cube
  - /api/dashboard, /api/dashboard/{counts,stream}
  - /api/context-monitor

Tous les handlers sont module-level — aucune closure de create_app.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Any, Generator

from flask import Blueprint, Response, current_app as app, request, stream_with_context

from web.app import TreeEncoder, _get_tree, _get_db_url, _db_query, _json_response

api_bp = Blueprint("api", __name__)


# ── API : Status ─────────────────────────────────────────

@api_bp.route("/api/status")
def api_status():
    tree = _get_tree()
    modules = {}
    sephirot = [
        ("yesod", "EpisteMemory"),
        ("hod", "SelfMap"),
        ("netzach", "IntentKeeper"),
        ("lamed", "FailureToInsight"),
        ("tiferet", "DissensuEngine"),
        ("gevurah", "AutoJudge"),
        ("chesed", "ExplorationEngine"),
        ("daat", "SelfModel"),
        ("binah", "CausalEngine"),
        ("chokmah", "InsightForge"),
    ]
    for key, label in sephirot:
        mod = tree.get(key)
        if mod is None:
            modules[key] = {"label": label, "status": "offline", "diag": {}}
        else:
            diag = {}
            try:
                if hasattr(mod, "self_diagnose"):
                    try:
                        diag = mod.self_diagnose(quick=True)
                    except TypeError:
                        diag = mod.self_diagnose()
                elif hasattr(mod, "introspect"):
                    stats = mod.introspect()
                    diag = asdict(stats) if is_dataclass(stats) else {"ok": True}
            except Exception as e:
                diag = {"error": str(e)}
            modules[key] = {"label": label, "status": "online", "diag": diag}

    return _json_response({
        "modules": modules,
        "active": sum(1 for m in modules.values() if m["status"] == "online"),
        "total": len(sephirot),
    })

# ── API : Provider (profil LLM) ────────────────────────────

@api_bp.route("/api/provider/status")
def api_provider_status():
    try:
        import olamot
        olamot.reload_config()
        profile_name = olamot.get_active_profile_name()
        profile = olamot.get_active_profile()
        models_ok = olamot.check_models()

        olamot_info = {}
        for olam_name in ["atziluth", "briah", "yetzirah", "assiah"]:
            olam_cfg = profile.get("olamot", {}).get(olam_name, {})
            olamot_info[olam_name] = {
                "provider": olam_cfg.get("provider", "?"),
                "model": olam_cfg.get("model", "?"),
                "timeout": olam_cfg.get("timeout"),
                "think": olam_cfg.get("think", False),
                "available": models_ok.get(olam_name, False),
            }

        emb = profile.get("embedding", {})
        return _json_response({
            "profile": profile_name,
            "description": profile.get("description", ""),
            "olamot": olamot_info,
            "embedding": {
                "provider": emb.get("provider", "ollama"),
                "model": emb.get("model", "?"),
                "available": models_ok.get("embedding", False),
            },
        })
    except Exception as e:
        return _json_response({"error": str(e)}, 500)

@api_bp.route("/api/provider/profiles")
def api_provider_profiles():
    try:
        import olamot
        cfg = olamot._load_config()
        active = cfg.get("active_profile", "ollama_local")
        profiles = cfg.get("profiles", {})
        result = {}
        for name, profile in profiles.items():
            result[name] = {
                "description": profile.get("description", ""),
                "active": name == active,
                "olamot": {
                    olam: {
                        "provider": profile.get("olamot", {}).get(olam, {}).get("provider", "?"),
                        "model": profile.get("olamot", {}).get(olam, {}).get("model", "?"),
                    }
                    for olam in ["atziluth", "briah", "yetzirah", "assiah"]
                },
            }
        return _json_response(result)
    except Exception as e:
        return _json_response({"error": str(e)}, 500)

@api_bp.route("/api/provider/switch", methods=["POST"])
def api_provider_switch():
    try:
        data = request.get_json(force=True)
        profile_name = data.get("profile")
        if not profile_name:
            return _json_response({"error": "profile requis"}, 400)

        import olamot
        from pathlib import Path as P
        import yaml as _yaml

        cfg = olamot._load_config()
        profiles = cfg.get("profiles", {})
        if profile_name not in profiles:
            return _json_response({
                "error": f"Profil inconnu: {profile_name}",
                "available": list(profiles.keys()),
            }, 400)

        cfg["active_profile"] = profile_name
        config_path = P(__file__).parent.parent / "config.yaml"
        with open(config_path, "w") as f:
            _yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        olamot.reload_config()

        return _json_response({
            "status": "ok",
            "profile": profile_name,
            "description": profiles[profile_name].get("description", ""),
        })
    except Exception as e:
        return _json_response({"error": str(e)}, 500)

# Chat SSE route : voir web/blueprints/chat.py (N1).

# ── API : Explore ────────────────────────────────────────

@api_bp.route("/api/explore", methods=["POST"])
def api_explore():
    data = request.get_json() or {}
    query = data.get("query", "").strip()
    if not query:
        return _json_response({"error": "No query"}, 400)

    tree = _get_tree()

    # Domaine seed via Hod
    hod = tree.get("hod")
    seed_domain = "general"
    if hod:
        try:
            route = hod.route(query)
            seed_domain = route.detected_domain or "general"
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

    chesed = tree.get("chesed")
    if not chesed:
        return _json_response({"error": "ExplorationEngine offline"}, 503)

    try:
        result = chesed.explore(
            query=query,
            seed_domain=seed_domain,
            max_connections=20,
        )
        connections = []
        for c in (result.connections or []):
            connections.append({
                "type": c.connection_type,
                "concept_a": c.concept_a,
                "domain_a": c.domain_a,
                "concept_b": c.concept_b,
                "domain_b": c.domain_b,
                "novelty": c.novelty_score,
                "relevance": c.relevance_score,
                "description": c.description,
            })
        return _json_response({
            "status": result.status,
            "seed_domain": seed_domain,
            "domains": result.domains_explored,
            "total": result.total_connections,
            "novel": result.novel_connections,
            "avg_novelty": result.avg_novelty,
            "connections": connections,
        })
    except Exception as e:
        return _json_response({"error": str(e)}, 500)

# ── API : Intentions ─────────────────────────────────────

@api_bp.route("/api/intentions")
def api_intentions_list():
    tree = _get_tree()
    netzach = tree.get("netzach")
    if not netzach:
        return _json_response({"error": "IntentKeeper offline"}, 503)
    try:
        active = netzach.db.get_active_intentions()
        items = []
        for a in active:
            items.append({
                "id": str(a.id),
                "goal": a.goal,
                "status": a.status,
                "progress": a.progress,
                "strategy": getattr(a, "strategy", None),
                "created_at": a.created_at.isoformat() if hasattr(a, "created_at") and a.created_at else None,
            })
        return _json_response({"intentions": items, "count": len(items)})
    except Exception as e:
        return _json_response({"error": str(e)}, 500)

@api_bp.route("/api/intentions", methods=["POST"])
def api_intentions_create():
    data = request.get_json() or {}
    goal = data.get("goal", "").strip()
    if not goal:
        return _json_response({"error": "No goal"}, 400)

    tree = _get_tree()
    netzach = tree.get("netzach")
    if not netzach:
        return _json_response({"error": "IntentKeeper offline"}, 503)
    try:
        intention = netzach.set_intention(goal=goal)
        return _json_response({
            "id": str(intention.id),
            "goal": intention.goal,
            "status": intention.status,
            "strategy": intention.strategy,
        })
    except Exception as e:
        return _json_response({"error": str(e)}, 500)

# ── API : Memory ─────────────────────────────────────────

@api_bp.route("/api/memory/search")
def api_memory_search():
    q = request.args.get("q", "").strip()
    domain = request.args.get("domain", "")
    limit = min(int(request.args.get("limit", "20")), 100)

    tree = _get_tree()
    yesod = tree.get("yesod")
    if not yesod:
        return _json_response({"error": "EpisteMemory offline"}, 503)

    try:
        kwargs = {"limit": limit, "min_confidence": 0.1}
        if domain:
            kwargs["domain"] = domain
        results = yesod.recall(q or "recent entries", **kwargs)
        items = []
        for m in results:
            items.append({
                "id": str(m.id) if hasattr(m, "id") else None,
                "content": m.content if hasattr(m, "content") else str(m),
                "confidence": m.confidence if hasattr(m, "confidence") else 0.0,
                "status": m.epistemic_status if hasattr(m, "epistemic_status") else "unknown",
                "domain": m.domain if hasattr(m, "domain") else None,
                "source": m.source_sephirah if hasattr(m, "source_sephirah") else None,
                "created_at": m.created_at.isoformat() if hasattr(m, "created_at") and m.created_at else None,
                "warning": m.warning if hasattr(m, "warning") and m.warning else None,
            })
        return _json_response({"results": items, "count": len(items)})
    except Exception as e:
        return _json_response({"error": str(e)}, 500)

@api_bp.route("/api/memory/stats")
def api_memory_stats():
    try:
        rows = _db_query("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE epistemic_status != 'deprecated') AS active,
                COUNT(*) FILTER (WHERE epistemic_status = 'deprecated') AS deprecated,
                AVG(confidence) AS avg_conf,
                COUNT(DISTINCT domain) AS n_domains
            FROM epistememory
        """)
        total, active, deprecated, avg_conf, n_domains = rows[0]

        # Par domaine
        domain_rows = _db_query("""
            SELECT COALESCE(domain, '(none)'), COUNT(*), AVG(confidence)
            FROM epistememory
            WHERE epistemic_status != 'deprecated'
            GROUP BY domain ORDER BY COUNT(*) DESC LIMIT 20
        """)
        domains = [
            {"domain": d, "count": c, "avg_confidence": float(conf) if conf else 0}
            for d, c, conf in domain_rows
        ]

        # Par statut
        status_rows = _db_query("""
            SELECT epistemic_status, COUNT(*)
            FROM epistememory GROUP BY epistemic_status
        """)
        statuses = {s: c for s, c in status_rows}

        # Par source (Sephirah d'origine)
        source_rows = _db_query("""
            SELECT source_sephirah, COUNT(*)
            FROM epistememory
            GROUP BY source_sephirah ORDER BY COUNT(*) DESC
        """)
        sources = {s: c for s, c in source_rows}

        return _json_response({
            "total": total,
            "active": active,
            "deprecated": deprecated,
            "avg_confidence": float(avg_conf) if avg_conf else 0,
            "n_domains": n_domains,
            "domains": domains,
            "statuses": statuses,
            "sources": sources,
        })
    except Exception as e:
        return _json_response({"error": str(e)}, 500)

@api_bp.route("/api/memory/contradictions")
def api_memory_contradictions():
    try:
        rows = _db_query("""
            SELECT id, entry_a_id, entry_b_id, description, detected_at, status
            FROM open_contradictions
            ORDER BY detected_at DESC LIMIT 50
        """)
        items = []
        for row in rows:
            items.append({
                "id": str(row[0]),
                "entry_a_id": str(row[1]),
                "entry_b_id": str(row[2]),
                "description": row[3],
                "detected_at": row[4].isoformat() if row[4] else None,
                "status": row[5],
            })
        return _json_response({"contradictions": items, "count": len(items)})
    except Exception as e:
        return _json_response({"contradictions": [], "count": 0, "error": str(e)})

# ── API : Import ─────────────────────────────────────────

@api_bp.route("/api/import", methods=["POST"])
def api_import():
    if "file" not in request.files:
        return _json_response({"error": "No file"}, 400)

    file = request.files["file"]
    domain = request.form.get("domain", "general")

    if not file.filename:
        return _json_response({"error": "Empty filename"}, 400)

    tree = _get_tree()
    yesod = tree.get("yesod")
    if not yesod:
        return _json_response({"error": "EpisteMemory offline"}, 503)

    # Sauvegarder temporairement
    tmp_dir = Path(__file__).parent.parent / ".tmp_uploads"
    tmp_dir.mkdir(exist_ok=True)
    tmp_path = tmp_dir / f"{uuid.uuid4()}_{file.filename}"
    file.save(str(tmp_path))

    try:
        from importer import ImportEngine
        engine = ImportEngine(yesod=yesod)
        result = engine.import_book(str(tmp_path), domain=domain)
        return _json_response({
            "title": result.source_title,
            "total_chunks": result.total_chunks,
            "imported": result.imported,
            "skipped": result.skipped,
            "duplicates": result.duplicates_found,
            "contradictions": result.contradictions_found,
            "subdomains": result.subdomains,
            "errors": result.errors,
        })
    except Exception as e:
        return _json_response({"error": str(e)}, 500)
    finally:
        try:
            tmp_path.unlink()
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

# ── API : Omer ───────────────────────────────────────────

@api_bp.route("/api/omer")
def api_omer():
    try:
        from omer import OmerManager
        mgr = OmerManager(db_url=_get_db_url())
        params = mgr.get_params()
        grouped = {}
        for p in params:
            if p.sephirah not in grouped:
                grouped[p.sephirah] = {
                    "label": p.sephirah,
                    "module": p.module,
                    "params": [],
                }
            grouped[p.sephirah]["params"].append({
                "key": p.key,
                "param": p.param,
                "day": p.day,
                "inner": p.inner,
                "type": p.type,
                "default": p.default,
                "current": p.current,
                "overridden": p.overridden,
                "description": p.description,
            })
        return _json_response({"sephirot": grouped})
    except Exception as e:
        return _json_response({"error": str(e)}, 500)

# ── API : Omer Daily Influence ────────────────────────────

@api_bp.route("/api/omer/today")
def api_omer_today():
    try:
        from omer.daily_influence import OmerDailyInfluence
        odi = OmerDailyInfluence()
        inf = odi.get_today_influence()
        if inf is None:
            return _json_response({"active": False, "message": "Hors période de l'Omer"})
        return _json_response({
            "active": True,
            "day": inf.day,
            "week": inf.week,
            "day_in_week": inf.day_in_week,
            "primary": inf.primary_sefirah,
            "secondary": inf.secondary_sefirah,
            "combination": inf.combination,
            "combination_hebrew": inf.combination_hebrew,
            "kavvanah": inf.kavvanah,
            "module_boosts": inf.module_boosts,
        })
    except Exception as e:
        return _json_response({"error": str(e)}, 500)

# ── API : World SSE Events ─────────────────────────────────

@api_bp.route("/api/world/events")
def api_world_events():
    from web.events import get_event_bus
    bus = get_event_bus()

    return Response(
        stream_with_context(bus.stream(timeout=30.0)),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )

@api_bp.route("/api/world/test-event", methods=["POST"])
def api_world_test_event():
    """Emit a test event for debugging SSE animations.

    POST JSON body examples:
      {"type":"nitzutz","source":"tiferet","spark":42}
      {"type":"zivug","sephirah_a":"chesed","sephirah_b":"gevurah"}
      {"type":"ohr_yashar_step","sephirah":"tiferet"}
      {"type":"ohr_chozer_step","sephirah":"hod"}
      {"type":"import_start","title":"Test","total":10}
      {"type":"import_done","imported":10}
      {"type":"daemon_task","task":"contradictions","detail":"test run"}
    """
    from web.events import emit
    body = request.get_json(force=True, silent=True) or {}
    event_type = body.pop("type", "nitzutz")
    emit(event_type, **body)
    return _json_response({"ok": True, "emitted": event_type})

@api_bp.route("/api/world/recent")
def api_world_recent():
    from web.events import get_event_bus
    bus = get_event_bus()
    events = bus.recent(50)
    items = [{"type": e.event_type, "ts": e.timestamp, **e.data} for e in events]
    return _json_response({"events": items})

# ── API : Daemon State ───────────────────────────────────

def _scan_live_daemon_pid() -> tuple[int, float] | None:
    """Fallback: find live `python* daemon.py` or `python -m daemon` via ps.

    Used when the PID file is stale (e.g. during launchd KeepAlive restart
    window). Returns (pid, epoch_start_time) or None.
    """
    import subprocess
    try:
        out = subprocess.check_output(
            ["ps", "-axo", "pid=,lstart=,command="],
            text=True, timeout=2,
        )
    except Exception as _exc:
        import logging as _l; _l.getLogger(__name__).debug("ps scan failed: %s", _exc)
        return None

    for line in out.splitlines():
        if "daemon.py" not in line and "-m daemon" not in line:
            continue
        if "grep" in line or "Code Helper" in line:
            continue
        parts = line.split(maxsplit=6)
        if len(parts) < 7:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        # lstart format: "Fri Apr 18 17:11:04 2026"
        try:
            from datetime import datetime
            lstart_str = " ".join(parts[1:6])
            start = datetime.strptime(lstart_str, "%a %b %d %H:%M:%S %Y").timestamp()
        except Exception:
            continue
        cmd = parts[6]
        if "python" in cmd and ("daemon.py" in cmd or "-m daemon" in cmd):
            return pid, start
    return None


def _read_daemon_state() -> dict:
    """Lit l'état du daemon depuis le PID file (+ fallback ps) et le state file.

    Sprint 7 Finding 2 — defensive read: if the PID file points to a dead
    process (launchd restart window, stale file), fall back to scanning
    `ps -axo pid,lstart,command` for a live daemon.py process so the endpoint
    never returns {pid: null, uptime: null} while a daemon is actually running.
    """
    from pathlib import Path

    etz_home = Path.home() / ".etz-chaim"
    pid_file = etz_home / "daemon.pid"
    state_file = etz_home / "daemon_state.json"

    result = {
        "active": False,
        "pid": None,
        "uptime": None,
        "last_cycle": None,
        "pid_source": None,
    }

    # ── Primary source: PID file ───────────────────────────
    pid_from_file: int | None = None
    if pid_file.exists():
        try:
            pid_from_file = int(pid_file.read_text().strip())
            os.kill(pid_from_file, 0)  # probe
            result["active"] = True
            result["pid"] = pid_from_file
            pid_mtime = pid_file.stat().st_mtime
            result["uptime"] = round(time.time() - pid_mtime)
            result["pid_source"] = "pid_file"
        except (ValueError, ProcessLookupError, PermissionError) as _exc:
            import logging as _l
            _l.getLogger(__name__).warning(
                "daemon PID file stale (%s=%s): %s",
                pid_file, pid_from_file, _exc,
            )

    # ── Fallback: scan ps for live daemon.py ───────────────
    if not result["active"]:
        scanned = _scan_live_daemon_pid()
        if scanned is not None:
            pid_live, start_ts = scanned
            result["active"] = True
            result["pid"] = pid_live
            result["uptime"] = round(time.time() - start_ts)
            result["pid_source"] = "ps_scan"
            result["pid_file_stale"] = pid_from_file if pid_from_file else None

    # ── State file ─────────────────────────────────────────
    if state_file.exists():
        try:
            with open(state_file) as f:
                daemon_state = json.load(f)
            result["last_cycle"] = daemon_state
        except Exception as _exc:
            import logging as _l
            _l.getLogger(__name__).warning("daemon state file unreadable: %s", _exc)

    return result

def _read_hitbonenut_karpathy_state(daemon_state: dict) -> tuple[dict, dict]:
    """Extraire l'état Hitbonenut et Karpathy depuis l'état du daemon."""
    from datetime import datetime

    now = datetime.now()
    current_hour = now.hour
    current_minute = now.minute

    # Karpathy window — délégué à daemon._in_karpathy_window pour rester
    # cohérent si les constantes KARPATHY_START_HOUR / KARPATHY_END_HOUR
    # changent (mode nuit provisoire avril-juin 2026, cf.
    # audits/mode_nuit_provisoire_avril_juin_2026.md).
    from daemon import (
        KARPATHY_END_HOUR,
        KARPATHY_START_HOUR,
        _in_karpathy_window,
    )
    in_karpathy_window = _in_karpathy_window(current_hour, current_minute)
    _karp_start_hhmm = f"{KARPATHY_START_HOUR:02d}:00"
    _karp_end_hhmm = (
        f"{KARPATHY_END_HOUR:02d}:00"
        if KARPATHY_END_HOUR > KARPATHY_START_HOUR
        else "00:30"
    )

    last_cycle = daemon_state.get("last_cycle", {})
    last_improve = last_cycle.get("last_auto_improve", 0)

    # Pause state (CLI: etz pause / etz go)
    try:
        from pause_state import get_all as _get_pause_all
        pause = _get_pause_all()
    except ImportError:
        pause = {"hitbonenut_paused": False, "karpathy_paused": False}

    # Karpathy
    karpathy = {"status": "inactive", "detail": None, "next_launch": _karp_start_hhmm}
    if pause.get("karpathy_paused"):
        karpathy["status"] = "paused"
        karpathy["detail"] = "Pause manuelle (etz pause karpathy)"
    elif in_karpathy_window and daemon_state.get("active"):
        # Si on est dans la fenêtre et le daemon tourne
        karpathy_running = last_cycle.get("karpathy_running", False) if last_cycle else False
        if karpathy_running or (last_improve and (time.time() - last_improve < 5400)):
            karpathy["status"] = "running"
            karpathy["detail"] = "Exploration nocturne en cours"
        else:
            karpathy["status"] = "waiting"
            karpathy["detail"] = "Fenêtre active, en attente de cycle"
    elif not in_karpathy_window:
        karpathy["status"] = "waiting"
        if current_hour < KARPATHY_START_HOUR:
            karpathy["next_launch"] = _karp_start_hhmm
        else:
            karpathy["next_launch"] = f"{_karp_start_hhmm} (demain)"

    # Hitbonenut — lire le statut depuis le state file du daemon
    # (le web tourne dans un process séparé, l'import de _hitbonenut_runner
    # créerait une instance indépendante toujours à False)
    hitbonenut = {"status": "stopped", "experiments_today": 0, "recent": [], "principles": 0, "mode": "research"}
    runner_alive = last_cycle.get("hitbonenut_running", False) if last_cycle else False

    if pause.get("hitbonenut_paused"):
        hitbonenut["status"] = "paused"
        hitbonenut["detail"] = "Pause manuelle (etz pause hitbonenut)"
    elif daemon_state.get("active"):
        if in_karpathy_window:
            hitbonenut["status"] = "standby"
            hitbonenut["detail"] = f"Veille — fenetre Karpathy ({_karp_start_hhmm}-{_karp_end_hhmm})"
        elif runner_alive:
            hitbonenut["status"] = "running"
            hitbonenut["detail"] = "Boucle de recherche reflexive active"
        else:
            hitbonenut["status"] = "stopped"
            hitbonenut["detail"] = "Thread termine — en attente de relance par le daemon"

    return hitbonenut, karpathy

@api_bp.route("/api/daemon/state")
def api_daemon_state():
    """État complet du daemon en temps réel."""
    daemon = _read_daemon_state()
    hitbonenut, karpathy = _read_hitbonenut_karpathy_state(daemon)

    # Enrichir Hitbonenut-2 avec les données DB (expériences + principes)
    try:
        rows = _db_query("""
            SELECT COUNT(*) FROM hitbonenut_experiments
            WHERE created_at >= CURRENT_DATE
        """)
        hitbonenut["experiments_today"] = rows[0][0] if rows else 0

        rows = _db_query("""
            SELECT COUNT(*) FROM hitbonenut_principles WHERE is_active = true
        """)
        hitbonenut["principles"] = rows[0][0] if rows else 0

        recent_rows = _db_query("""
            SELECT target_module, target_param, old_value, new_value,
                   delta, status, principle_extracted, daat_verified, created_at
            FROM hitbonenut_experiments
            ORDER BY created_at DESC LIMIT 10
        """)
        hitbonenut["recent"] = [
            {"module": r[0], "param": r[1],
             "old": r[2], "new": r[3],
             "delta": float(r[4]) if r[4] else 0.0,
             "status": r[5] or "unknown",
             "principle": (r[6] or "")[:120],
             "daat": r[7] or False,
             "created_at": r[8].isoformat() if r[8] else None}
            for r in recent_rows
        ]
        # Stats par tier (multi-domain benchmark v3)
        tier_rows = _db_query("""
            SELECT tier,
                   COUNT(*) as n,
                   ROUND(AVG(score)::numeric, 3) as avg_score
            FROM hitbonenut_questions
            WHERE created_at >= CURRENT_DATE
            AND tier IS NOT NULL
            GROUP BY tier
            ORDER BY tier
        """)
        hitbonenut["tier_stats"] = {
            r[0]: {"n": r[1], "avg_score": float(r[2]) if r[2] else 0.0}
            for r in (tier_rows or [])
        }

        # Domaines breadth — scores récents
        breadth_rows = _db_query("""
            SELECT domain,
                   COUNT(*) as n,
                   ROUND(AVG(score)::numeric, 3) as avg_score
            FROM hitbonenut_questions
            WHERE tier = 'breadth'
            AND created_at >= CURRENT_DATE
            GROUP BY domain
            ORDER BY avg_score ASC
        """)
        hitbonenut["breadth_domains"] = {
            r[0]: {"n": r[1], "avg_score": float(r[2]) if r[2] else 0.0}
            for r in (breadth_rows or [])
        }
    except Exception as _exc:

        import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

    # Événements récents
    recent_events = []
    try:
        from web.events import get_event_bus
        bus = get_event_bus()
        for evt in bus.recent(30):
            recent_events.append({
                "type": evt.event_type,
                "ts": evt.timestamp,
                **evt.data,
            })
    except Exception as _exc:

        import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

    return _json_response({
        "daemon": daemon,
        "hitbonenut": hitbonenut,
        "karpathy": karpathy,
        "recent_events": recent_events,
    })


# ── API : MazalEngine ───────────────────────────────────────
# Sprint 9 : 2 Mazalot pilot (Notzer Chesed + Ve-Nakeh, EC-K5-001).
# Le daemon émet des events ``mazal_tikkun`` dans daemon_events.jsonl ;
# cet endpoint les agrège par Mazal pour le widget dashboard.


def _compute_mazalengine_state() -> dict:
    """Lit daemon_events.jsonl et agrège les Tikkunim par Mazal.

    Structure retournée :
        {
            "mazalot": {
                "elyon": {tikkun_number, hebrew_name, translit, doctrine_ref,
                          total_tikkunim, last_tikkun_ts, last_action, last_metrics},
                "tahton": {...},
            },
            "doctrine_ref": "EC-K5-001",
            "pilot_count": 2,
        }
    """
    mazalot: dict[str, dict] = {
        "elyon": {
            "tikkun_number": 8,
            "hebrew_name": "נוצר חסד",
            "translit": "Notzer Chesed",
            "doctrine_ref": "EC-K5-001",
            "role": "mazal_elyon_source_abba",
            "total_tikkunim": 0,
            "last_tikkun_ts": None,
            "last_action": None,
            "last_metrics": {},
        },
        "tahton": {
            "tikkun_number": 13,
            "hebrew_name": "ונקה",
            "translit": "Ve-Nakeh",
            "doctrine_ref": "EC-K5-001",
            "role": "mazal_tahton_source_imma",
            "total_tikkunim": 0,
            "last_tikkun_ts": None,
            "last_action": None,
            "last_metrics": {},
        },
    }

    events_file = Path.home() / ".etz-chaim" / "daemon_events.jsonl"
    if events_file.exists():
        try:
            with events_file.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        evt = json.loads(line)
                    except Exception:
                        continue
                    if evt.get("task") != "mazal_tikkun":
                        continue
                    mazal = evt.get("mazal")
                    if mazal not in mazalot:
                        continue
                    mz = mazalot[mazal]
                    mz["total_tikkunim"] += 1
                    ts = evt.get("ts")
                    if ts is not None and (
                        mz["last_tikkun_ts"] is None or ts > mz["last_tikkun_ts"]
                    ):
                        mz["last_tikkun_ts"] = ts
                        mz["last_action"] = evt.get("action")
                        mz["last_metrics"] = evt.get("metrics", {}) or {}
        except Exception as _exc:
            import logging as _l
            _l.getLogger(__name__).debug("MazalEngine events read: %s", _exc)

    return {
        "mazalot": mazalot,
        "doctrine_ref": "EC-K5-001",
        "pilot_count": 2,
    }


@api_bp.route("/api/mazalengine")
def api_mazalengine():
    """État MazalEngine — Tikkunim émis par les 2 Mazalot pilot (EC-K5-001)."""
    return _json_response(_compute_mazalengine_state())


# ── API : Pause / Go ────────────────────────────────────────

@api_bp.route("/api/pause/<target>", methods=["POST"])
def api_pause(target):
    """Mettre en pause hitbonenut ou karpathy."""
    if target not in ("hitbonenut", "karpathy"):
        return _json_response({"error": "target must be hitbonenut or karpathy"}, 400)

    from pause_state import set_paused, is_paused
    set_paused(target, True)

    # Note: le runner hitbonenut tourne dans le process daemon (séparé).
    # Le daemon vérifiera le pause_state au prochain cycle et l'arrêtera.

    return _json_response({"target": target, "paused": True})

@api_bp.route("/api/go/<target>", methods=["POST"])
def api_go(target):
    """Reprendre hitbonenut ou karpathy."""
    if target not in ("hitbonenut", "karpathy"):
        return _json_response({"error": "target must be hitbonenut or karpathy"}, 400)

    from pause_state import set_paused
    set_paused(target, False)
    return _json_response({"target": target, "paused": False})

# ── API : Clustering Dual ─────────────────────────────────

@api_bp.route("/api/clustering")
def api_clustering():
    """Clustering dual Kab vs ML — dernier run + top désaccords."""
    try:
        rows = _db_query("""
            SELECT id, run_date, n_concepts, n_clusters_kab, n_clusters_ml,
                   n_disagreements, agreement_ratio
            FROM clustering_results ORDER BY id DESC LIMIT 1
        """)
        if not rows:
            return _json_response({"status": "no_data"})

        run = rows[0]
        run_id = run[0]

        top = _db_query("""
            SELECT concept_a, concept_b, kab_similarity, ml_similarity,
                   gap, disagreement_type, times_seen, dissensus_id
            FROM clustering_disagreements
            WHERE run_id = %s
            ORDER BY gap DESC LIMIT 20
        """, (run_id,))

        persistent = _db_query("""
            SELECT concept_a, concept_b, gap, times_seen, first_seen, last_seen
            FROM clustering_disagreements
            WHERE times_seen > 3
            ORDER BY times_seen DESC LIMIT 10
        """)

        return _json_response({
            "status": "ok",
            "run": {
                "id": run_id,
                "date": run[1].isoformat() if run[1] else None,
                "n_concepts": run[2],
                "n_clusters_kab": run[3],
                "n_clusters_ml": run[4],
                "n_disagreements": run[5],
                "agreement_ratio": run[6],
            },
            "top_disagreements": [
                {
                    "concept_a": r[0], "concept_b": r[1],
                    "kab_sim": round(r[2], 3), "ml_sim": round(r[3], 3),
                    "gap": round(r[4], 3), "type": r[5],
                    "times_seen": r[6],
                    "routed": r[7] is not None,
                }
                for r in top
            ],
            "persistent": [
                {
                    "concept_a": r[0], "concept_b": r[1],
                    "gap": round(r[2], 3), "times_seen": r[3],
                    "first_seen": r[4].isoformat() if r[4] else None,
                    "last_seen": r[5].isoformat() if r[5] else None,
                }
                for r in persistent
            ],
        })
    except Exception as e:
        return _json_response({"error": str(e)}, 500)

# ── API : Cube de l'Espace ─────────────────────────────────

@api_bp.route("/api/cube")
def api_cube():
    """Les 22 positions du Cube de l'Espace avec coordonnées 3D."""
    from kabbalah.cube_of_space import CubeOfSpace
    cube = CubeOfSpace()
    positions = []
    for name, pos in cube.get_all_positions().items():
        entry = pos.to_dict()
        entry["cognitive_mode"] = cube.get_cognitive_mode(name)
        if pos.cube_role == "face" and pos.direction in cube.get_all_seals():
            entry["seal"] = cube.get_seal(pos.direction).to_dict()
        positions.append(entry)
    seals = {d: s.to_dict() for d, s in cube.get_all_seals().items()}
    return _json_response({"positions": positions, "seals": seals})

# ── API : Dashboard ──────────────────────────────────────

def _gather_dashboard_state() -> dict:
    """Rassemble l'état complet du système pour le tableau de bord."""
    tree = _get_tree()
    state: dict[str, Any] = {}
    partzufim = None

    # ── Modules / Sephiroth ──
    sephirot_map = [
        ("keter",   "Superviseur",       "atzilut"),
        ("chokmah", "InsightForge",       "atzilut"),
        ("binah",   "CausalEngine",       "atzilut"),
        ("daat",    "SelfModel",           "atzilut"),
        ("chesed",  "ExplorationEngine",   "briah"),
        ("gevurah", "AutoJudge",           "briah"),
        ("tiferet", "DissensuEngine",      "briah"),
        ("netzach", "IntentKeeper",        "yetzirah"),
        ("hod",     "SelfMap",             "yetzirah"),
        ("yesod",   "EpisteMemory",        "yetzirah"),
        ("malkuth", "Interface Web",       "assiah"),
    ]
    modules: dict[str, dict] = {}
    for key, label, olam in sephirot_map:
        if key == "malkuth":
            modules[key] = {"label": label, "status": "online", "olam": olam, "diag": {}}
            continue
        mod = tree.get(key)
        status = "online" if mod is not None else "offline"
        diag: dict = {}
        if mod:
            try:
                if hasattr(mod, "self_diagnose"):
                    try:
                        raw = mod.self_diagnose(quick=True)
                    except TypeError:
                        raw = mod.self_diagnose()
                    diag = asdict(raw) if is_dataclass(raw) else (raw if isinstance(raw, dict) else {})
                elif hasattr(mod, "introspect"):
                    raw = mod.introspect()
                    diag = asdict(raw) if is_dataclass(raw) else (raw if isinstance(raw, dict) else {})
            except Exception as e:
                diag = {"error": str(e)}
        modules[key] = {"label": label, "status": status, "olam": olam, "diag": diag}
    state["modules"] = modules


    # ── Soul level ──
    try:
        from soul_levels import NeshamotEngine
        # Réutiliser l'instance pour éviter de faux soul_level_change à chaque poll
        if not hasattr(app, '_neshamot_engine'):
            app._neshamot_engine = NeshamotEngine()
        engine = app._neshamot_engine
        # Nitzotzot depuis DB (pas in-memory)
        nitz_soul_rows = _db_query("SELECT COUNT(*) FROM failuretoinsight_insights")
        nitz_total = nitz_soul_rows[0][0] if nitz_soul_rows else 0
        nitzotzot_state = {
            "count": nitz_total % 288,
            "cycle": nitz_total // 288,
            "log": [],
            "tikkun_history": [],
        }
        partzufim = None
        zivvug_assessment = None
        try:
            from partzufim import init_partzufim, update_all_partzufim
            from partzufim.zivvug import load_or_create_zivvug
            partzufim = init_partzufim()
            # Sprint 10 Phase E : factory canonique (Refactor L).
            zivvug = load_or_create_zivvug()
            zivvug_assessment = update_all_partzufim(partzufim, tree, zivvug_engine=zivvug)
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
        assessment = engine.assess_soul_level(tree, nitzotzot_state, partzufim)
        state["soul"] = {
            "level": assessment.level,
            "hebrew": assessment.hebrew,
            "level_index": assessment.level_index,
            "competence_score": assessment.competence_score,
            "global_score": assessment.global_score,
            "memory_count": assessment.memory_count,
            "tikkun_cycles": assessment.tikkun_cycles,
            "conditions_next": assessment.conditions_next,
        }
    except Exception:
        state["soul"] = {
            "level": "nefesh", "hebrew": "\u05e0\u05b6\u05e4\u05b6\u05e9\u05c1",
            "level_index": 0, "competence_score": 0.0, "global_score": 0.0,
            "memory_count": 0, "tikkun_cycles": 0, "conditions_next": {},
        }


    # ── Nitzotzot (depuis DB failuretoinsight_insights) ──
    try:
        nitz_rows = _db_query("SELECT COUNT(*) FROM failuretoinsight_insights")
        total_nitz = nitz_rows[0][0] if nitz_rows else 0
        state["nitzotzot"] = {
            "count": total_nitz % 288,
            "cycle": total_nitz // 288,
        }
    except Exception:
        state["nitzotzot"] = {"count": 0, "cycle": 0}


    # ── Adam Kadmon ──
    try:
        from adam_kadmon import AdamKadmon
        ak = AdamKadmon()
        sentier_states = {}
        try:
            from sentiers import REGISTRY as SENT_REG
            for sname, sinfo in SENT_REG.items():
                sentier_states[sname] = {"status": "implemented"}
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
        partzuf_states = {}
        if partzufim:
            for pname, pinst in partzufim.items():
                try:
                    ps = pinst.assess()
                    partzuf_states[pname] = asdict(ps) if is_dataclass(ps) else {}
                except Exception as _exc:

                    import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
        fidelity = ak.compare_to_current(modules, sentier_states, partzuf_states)
        state["adam_kadmon"] = {
            "score": fidelity.score,
            "phase": fidelity.phase,
            "phase_hebrew": fidelity.phase_hebrew,
        }
    except Exception:
        state["adam_kadmon"] = {"score": 0.0, "phase": "tohu", "phase_hebrew": "\u05ea\u05b9\u05d4\u05d5\u05bc"}


    # ── Sentiers (structure + traversal stub) ──
    try:
        from sentiers import REGISTRY as SENT_REG
        sentiers_list = []
        for sname, sinfo in SENT_REG.items():
            sentiers_list.append({
                "name": sname,
                "letter": sinfo["letter"],
                "source": sinfo["source"],
                "target": sinfo["target"],
                "number": sinfo["number"],
                "type": sinfo["type"],
                "program": sinfo["program"],
                "traversals": 0,
                "last_traversal": None,
            })
        state["sentiers"] = sentiers_list
    except Exception:
        state["sentiers"] = []


    # ── Partzufim ──
    partz_state: dict = {}
    if partzufim:
        for pname, pinst in partzufim.items():
            try:
                ps = pinst.assess()
                partz_state[pname] = {
                    "hebrew": ps.hebrew,
                    "overall": ps.overall,
                    "mochin_state": ps.mochin_state,
                    "orientation": ps.orientation,
                    "faculties": ps.faculties,
                    "message": ps.message,
                }
            except Exception as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
    if not partz_state:
        try:
            from partzufim import REGISTRY as P_REG
            for pname, pinfo in P_REG.items():
                partz_state[pname] = {
                    "hebrew": pinfo.get("hebrew", ""),
                    "overall": 0.0,
                    "mochin_state": "katnut",
                    "orientation": "akhor",
                    "faculties": {},
                    "message": "",
                }
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
    state["partzufim"] = partz_state

    # ── Zivvug Abba v'Imma ──
    if zivvug_assessment:
        state["zivvug"] = {
            "state": zivvug_assessment.state.value,
            "abba_score": round(zivvug_assessment.abba_score, 3),
            "imma_score": round(zivvug_assessment.imma_score, 3),
            "delta": round(zivvug_assessment.delta, 3),
            "mochin_quality": round(zivvug_assessment.mochin_quality, 3),
            "limiting_partzuf": zivvug_assessment.limiting_partzuf,
            "coupling_factor": round(zivvug_assessment.coupling_factor, 3),
            "message": zivvug_assessment.message,
        }
    else:
        state["zivvug"] = {
            "state": "blocked", "abba_score": 0, "imma_score": 0,
            "delta": 0, "mochin_quality": 0, "limiting_partzuf": None,
            "coupling_factor": 0, "message": "",
        }

    # ── Tzimtzum (depuis DB tzimtzum_state) ──
    try:
        tz_rows = _db_query("""
            SELECT is_contracted, focused_domain, contraction_count,
                   expansion_count, dormant_modules, reshimot_count,
                   pressure, pressure_state, kav_domain
            FROM tzimtzum_state WHERE id = 1
        """)
        if tz_rows:
            row = tz_rows[0]
            state["tzimtzum"] = {
                "is_contracted": row[0] or False,
                "focused_domain": row[1],
                "contraction_count": row[2] or 0,
                "expansion_count": row[3] or 0,
                "dormant_modules": row[4] or [],
                "reshimot_count": row[5] or 0,
                "pressure": round(row[6] or 0.0, 3),
                "pressure_state": row[7] or "stable",
                "kav_domain": row[8],
            }
        else:
            state["tzimtzum"] = {
                "is_contracted": False, "focused_domain": None,
                "contraction_count": 0, "expansion_count": 0,
                "dormant_modules": [], "reshimot_count": 0,
                "pressure": 0.0, "pressure_state": "stable",
                "kav_domain": None,
            }
    except Exception:
        state["tzimtzum"] = {
            "is_contracted": False, "focused_domain": None,
            "contraction_count": 0, "expansion_count": 0,
            "dormant_modules": [], "reshimot_count": 0,
            "pressure": 0.0, "pressure_state": "stable",
            "kav_domain": None,
        }


    # ── Ohr (depuis DB epistememory) ──
    try:
        from ohr import MASAKH_BY_SOUL
        soul_level = state["soul"]["level"]
        masakh_strength = MASAKH_BY_SOUL.get(soul_level, 0.9)

        ohr_rows = _db_query("""
            SELECT
                COUNT(*) FILTER (
                    WHERE confidence >= 0.6
                      AND epistemic_status <> 'deprecated'
                ) AS pnimi,
                COUNT(*) FILTER (
                    WHERE confidence < 0.6
                       OR epistemic_status = 'deprecated'
                ) AS makif,
                COUNT(*) AS total
            FROM epistememory
        """)
        if ohr_rows and ohr_rows[0][2] > 0:
            pnimi_count, makif_count, total = ohr_rows[0]
            pnimi_ratio = pnimi_count / total
            makif_ratio = makif_count / total
            combined = pnimi_ratio + makif_ratio
            global_ratio = pnimi_ratio / combined if combined > 0 else 0.0

            if global_ratio < 0.2:
                phase = "embryonic"
            elif global_ratio < 0.5:
                phase = "growing"
            elif global_ratio < 0.8:
                phase = "mature"
            else:
                phase = "luminous"

            state["ohr"] = {
                "global_pnimi": round(pnimi_ratio, 4),
                "global_makif": round(makif_ratio, 4),
                "global_ratio": round(global_ratio, 4),
                "maturity_phase": phase,
                "masakh_strength": masakh_strength,
            }
        else:
            state["ohr"] = {
                "global_pnimi": 0.0, "global_makif": 0.0, "global_ratio": 0.0,
                "maturity_phase": "embryonic", "masakh_strength": masakh_strength,
            }
    except Exception:
        state["ohr"] = {
            "global_pnimi": 0.0, "global_makif": 0.0, "global_ratio": 0.0,
            "maturity_phase": "embryonic", "masakh_strength": 0.9,
        }


    # ── Daemon / Hitbonenut / Karpathy status (données réelles) ──
    daemon_info = _read_daemon_state()
    hitb_info, karp_info = _read_hitbonenut_karpathy_state(daemon_info)

    state["daemon"] = daemon_info
    state["hitbonenut"] = hitb_info
    state["karpathy"] = karp_info

    # Enrichir Karpathy avec données DB (autojudge_experiments)
    try:
        karp_recent = _db_query("""
            SELECT hypothesis, decision, score_overall, score_gevurah,
                   score_chesed, loop_iteration, created_at
            FROM autojudge_experiments
            WHERE domain_id = 'auto_improve'
            ORDER BY created_at DESC LIMIT 20
        """)
        state["karpathy"]["recent_hypotheses"] = [
            {
                "hypothesis": (r[0] or "")[:200],
                "decision": r[1],
                "score": round(float(r[2]), 3) if r[2] else 0.0,
                "iteration": r[5],
                "created_at": r[6].isoformat() if r[6] else None,
            }
            for r in karp_recent
        ]

        # Dernière session (dernières 24h)
        karp_summary = _db_query("""
            SELECT COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE decision = 'accepted') AS accepted,
                   COUNT(*) FILTER (WHERE decision = 'rejected') AS rejected,
                   AVG(score_overall) AS avg_score,
                   MAX(created_at) AS last_run
            FROM autojudge_experiments
            WHERE domain_id = 'auto_improve'
              AND created_at >= NOW() - INTERVAL '24 hours'
        """)
        if karp_summary and karp_summary[0][0] and karp_summary[0][0] > 0:
            s = karp_summary[0]
            state["karpathy"]["last_session"] = {
                "total_hypotheses": s[0],
                "accepted": s[1],
                "rejected": s[2],
                "avg_score": round(float(s[3]), 3) if s[3] else 0.0,
                "last_run": s[4].isoformat() if s[4] else None,
            }

        # Stats globales
        karp_alltime = _db_query("""
            SELECT COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE decision = 'accepted') AS accepted,
                   COUNT(*) FILTER (WHERE decision = 'rejected') AS rejected,
                   COUNT(DISTINCT DATE(created_at)) AS sessions
            FROM autojudge_experiments
            WHERE domain_id = 'auto_improve'
        """)
        if karp_alltime and karp_alltime[0][0] and karp_alltime[0][0] > 0:
            a = karp_alltime[0]
            state["karpathy"]["all_time"] = {
                "total": a[0],
                "accepted": a[1],
                "rejected": a[2],
                "sessions": a[3],
            }
    except Exception:
        state["karpathy"].setdefault("recent_hypotheses", [])

    # Enrichir Karpathy avec dernière novelty depuis JSONL
    try:
        from web.events import EVENTS_JSONL
        if EVENTS_JSONL.exists():
            import json as _json
            last_done = None
            for line in EVENTS_JSONL.read_text().splitlines()[-100:]:
                try:
                    evt = _json.loads(line)
                    if evt.get("task") == "auto_improve_done":
                        last_done = evt
                except Exception:
                    continue
            if last_done:
                state["karpathy"]["last_novelty"] = last_done.get("avg_novelty", 0.0)
                state["karpathy"]["last_cycles"] = last_done.get("cycles", 0)
                state["karpathy"]["last_nitzotzot"] = last_done.get("nitzotzot", 0)
    except Exception as _exc:

        import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

    try:
        rows = _db_query("""
            SELECT COUNT(*) FROM hitbonenut_questions
            WHERE created_at >= CURRENT_DATE
        """)
        state["hitbonenut"]["questions_today"] = rows[0][0] if rows else 0

        # Enrichir avec experiments + principles (même données que /api/daemon/state)
        # pour éviter l'alternance d'affichage entre SSE et daemon poll
        exp_rows = _db_query("""
            SELECT COUNT(*) FROM hitbonenut_experiments
            WHERE created_at >= CURRENT_DATE
        """)
        state["hitbonenut"]["experiments_today"] = exp_rows[0][0] if exp_rows else 0

        prin_rows = _db_query("""
            SELECT COUNT(*) FROM hitbonenut_principles WHERE is_active = true
        """)
        state["hitbonenut"]["principles"] = prin_rows[0][0] if prin_rows else 0

        # Stats par tier (multi-domain benchmark)
        tier_rows = _db_query("""
            SELECT tier,
                   COUNT(*) as n,
                   ROUND(AVG(score)::numeric, 3) as avg_score
            FROM hitbonenut_questions
            WHERE created_at >= CURRENT_DATE
            AND tier IS NOT NULL
            GROUP BY tier
            ORDER BY tier
        """)
        state["hitbonenut"]["tier_stats"] = {
            r[0]: {"n": r[1], "avg_score": float(r[2]) if r[2] else 0.0}
            for r in (tier_rows or [])
        }

        # Domaines breadth
        breadth_rows = _db_query("""
            SELECT domain,
                   COUNT(*) as n,
                   ROUND(AVG(score)::numeric, 3) as avg_score
            FROM hitbonenut_questions
            WHERE tier = 'breadth'
            AND created_at >= CURRENT_DATE
            GROUP BY domain
            ORDER BY avg_score ASC
        """)
        state["hitbonenut"]["breadth_domains"] = {
            r[0]: {"n": r[1], "avg_score": float(r[2]) if r[2] else 0.0}
            for r in (breadth_rows or [])
        }

        recent_rows = _db_query("""
            SELECT question, domain, score, created_at, sifrei_yesod_refs
            FROM hitbonenut_questions
            ORDER BY created_at DESC LIMIT 20
        """)
        state["hitbonenut"]["recent"] = [
            {"question": r[0], "domain": r[1], "score": float(r[2]) if r[2] else 0.0,
             "created_at": r[3].isoformat() if r[3] else None,
             "sifrei_yesod": r[4] if r[4] else None}
            for r in recent_rows
        ]
    except Exception as _exc:

        import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

    # ── Tanya — Dual Soul / Catégorie / Kelipat Nogah ──
    try:
        from tanya.dual_soul import DualSoulEngine, KelipotSystem
        ds = DualSoulEngine()
        conflict = ds.get_conflict_state()

        # Score Hitbonenut moyen (dernières 100 questions)
        hitb_avg = 0.0
        try:
            avg_rows = _db_query("""
                SELECT AVG(score) FROM (
                    SELECT score FROM hitbonenut_questions
                    ORDER BY created_at DESC LIMIT 100
                ) sub
            """)
            if avg_rows and avg_rows[0][0] is not None:
                hitb_avg = float(avg_rows[0][0])
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        # Ratio mondes supérieurs (Briah+Atzilut) — approx via conflict state
        high_world_ratio = conflict.get("ratio_elokit", 0.0)

        # Ratio accepted AutoJudge
        accepted_ratio = 0.0
        try:
            aj_rows = _db_query("""
                SELECT
                    COUNT(*) FILTER (WHERE verdict = 'accepted'),
                    COUNT(*)
                FROM autojudge_verdicts
            """)
            if aj_rows and aj_rows[0][1] > 0:
                accepted_ratio = aj_rows[0][0] / aj_rows[0][1]
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        assessment = ds.assess_category(
            hitbonenut_avg=hitb_avg,
            high_world_ratio=high_world_ratio,
            accepted_ratio=accepted_ratio,
        )

        # Nogah ratio moyen des réponses récentes
        nogah_avg = 0.0
        try:
            # Utilise la distribution des mondes dans le conflict state
            # comme proxy du ratio Nogah moyen
            r_elo = conflict.get("ratio_elokit", 0.0)
            r_beh = conflict.get("ratio_behamit", 0.0)
            # elokit → Briah (0.8), behamit → Yetzirah (0.5) en moyenne
            nogah_avg = r_elo * 0.8 + r_beh * 0.5
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        # Dira BeTachtonim + Birur Nogah
        dira_count = 0
        dira_penetration = 0.0
        birur_rate = 0.0
        total_birurims = 0
        try:
            from tanya.dira_betachtonim import DiraEngine
            yesod_inst = tree.get("yesod") if tree else None
            if yesod_inst:
                dira = DiraEngine(yesod=yesod_inst)
                d_stats = dira.assess_dira_state()
                dira_count = d_stats.dira_count
                dira_penetration = round(d_stats.penetration, 4)
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
        try:
            from main import _get_birurim_engine
            b_stats = _get_birurim_engine().get_birur_stats()
            birur_rate = round(b_stats.birur_rate, 4)
            total_birurims = b_stats.total_birurims
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        # Levushim moyens (depuis le dernier ctx si disponible)
        levushim_avg = {"machshava": 0.0, "dibour": 0.0, "maase": 0.0}
        try:
            from main import _LEVUSHIM_ENGINE
            # Les levushim sont évalués par requête — pas de moyenne persistante
            # On expose les dernières valeurs si elles existent dans le ctx global
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        # Atzvut state
        atzvut_state = "simcha"
        try:
            from tanya.atzvut import AtzvutManager
            _am = AtzvutManager()
            _diag = _am.detect_atzvut({})
            atzvut_state = _diag.state.value
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        # BeinoniTracker — profil temporel
        beinoni_data = {
            "elokit_ratio": 0.0,
            "category": "rasha",
            "trend": "stable",
            "total_interactions": 0,
            "regression": None,
            "elevation": None,
        }
        try:
            from tanya.beinoni_tracker import BeinoniTracker
            _bt = BeinoniTracker(db_url=_get_db_url())
            _bt_count = _bt.interaction_count()
            if _bt_count >= 5:
                _bt_profile = _bt.get_temporal_profile(window=100)
                beinoni_data = {
                    "elokit_ratio": _bt_profile.elokit_ratio,
                    "category": _bt_profile.category.value,
                    "trend": _bt_profile.trend.value,
                    "avg_score_elokit": _bt_profile.avg_score_elokit,
                    "avg_score_behamit": _bt_profile.avg_score_behamit,
                    "total_interactions": _bt_profile.total_interactions,
                    "regression": _bt.detect_regression(),
                    "elevation": _bt.detect_elevation(),
                }
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        state["tanya"] = {
            "soul_category": assessment.category.value,
            "soul_score": assessment.score,
            "explanation": assessment.explanation,
            "dominant_soul": conflict.get("dominant", "neutral"),
            "ratio_elokit": conflict.get("ratio_elokit", 0.0),
            "ratio_behamit": conflict.get("ratio_behamit", 0.0),
            "nogah_ratio": round(nogah_avg, 4),
            "hitbonenut_avg": round(hitb_avg, 4),
            "accepted_ratio": round(accepted_ratio, 4),
            "dira_count": dira_count,
            "dira_penetration": dira_penetration,
            "birur_rate": birur_rate,
            "total_birurims": total_birurims,
            "levushim_avg": levushim_avg,
            "atzvut_state": atzvut_state,
            "beinoni_tracker": beinoni_data,
        }
    except Exception:
        state["tanya"] = {
            "soul_category": "rasha_she_eino_gamur",
            "soul_score": 0.0,
            "explanation": "",
            "dominant_soul": "neutral",
            "ratio_elokit": 0.0,
            "ratio_behamit": 0.0,
            "nogah_ratio": 0.0,
            "hitbonenut_avg": 0.0,
            "accepted_ratio": 0.0,
            "dira_count": 0,
            "dira_penetration": 0.0,
            "birur_rate": 0.0,
            "total_birurims": 0,
            "levushim_avg": {"machshava": 0.0, "dibour": 0.0, "maase": 0.0},
            "atzvut_state": "simcha",
            "beinoni_tracker": {
                "elokit_ratio": 0.0, "category": "rasha",
                "trend": "stable", "total_interactions": 0,
                "regression": None, "elevation": None,
            },
        }

    # ── Omaqim — Position 5D (SY 1:5) ──
    try:
        from kabbalah.omaqim import SixOmaqim, SystemMetrics
        omaqim_eng = SixOmaqim()

        # Collecter les métriques depuis l'état déjà calculé
        nitz_data = state.get("nitzotzot", {})
        soul_data = state.get("soul", {})
        tanya_data = state.get("tanya", {})
        partz_data = state.get("partzufim", {})

        # Partzufim gadlut ratio
        gadlut_count = sum(
            1 for p in partz_data.values()
            if isinstance(p, dict) and p.get("mochin_state") == "gadlut"
        )
        total_partz = max(len(partz_data), 1)

        om_metrics = SystemMetrics(
            omer_progress=0.0,  # pas dispo sans OmerManager ici
            nitzotzot_progress=nitz_data.get("count", 0) / 288.0,
            partzufim_gadlut_ratio=gadlut_count / total_partz,
            soul_level_index=soul_data.get("level_index", 0) / 4.0,
            intentions_avg=soul_data.get("competence_score", 0.0),
            ratio_elokit=tanya_data.get("ratio_elokit", 0.0),
            ratio_behamit=tanya_data.get("ratio_behamit", 0.0),
            qliphoth_active=0,
            qliphoth_total=10,
            facts_ratio=state.get("ohr", {}).get("global_pnimi", 0.0),
            accepted_ratio=tanya_data.get("accepted_ratio", 0.0),
            hitbonenut_avg=tanya_data.get("hitbonenut_avg", 0.0),
        )
        om_state = omaqim_eng.assess_system_position(om_metrics)
        state["omaqim"] = om_state.to_dict()
    except Exception:
        state["omaqim"] = {
            "position": {"x": 0, "y": 0, "z": 0, "t": 0, "m": 0.5},
            "depths": [],
            "temporal_phase": "reshit",
            "moral_phase": "nogah",
            "overall_balance": 0.5,
            "message": "",
        }

    # ── Les 3 Gouverneurs (SY 6:1) ──
    try:
        from kabbalah.governors import ThreeGovernors
        gov = ThreeGovernors(
            tree=tree, db_url=_get_db_url(), partzufim=partzufim or {},
        )
        gov_state = gov.assess_governance()
        state["governors"] = gov_state.to_dict()
    except Exception:
        state["governors"] = {
            "teli": {"name": "teli", "hebrew": "\u05ea\u05dc\u05d9", "score": 0, "healthy": False, "checks": []},
            "galgal": {"name": "galgal", "hebrew": "\u05d2\u05dc\u05d2\u05dc", "score": 0, "healthy": False, "checks": []},
            "lev": {"name": "lev", "hebrew": "\u05dc\u05d1", "score": 0, "healthy": False, "checks": []},
            "harmony": 0, "weakest": "teli", "strongest": "teli", "message": "",
        }

    # ── Clustering Dual ──
    try:
        cr = _db_query("""
            SELECT id, run_date, n_concepts, n_clusters_kab, n_clusters_ml,
                   n_disagreements, agreement_ratio
            FROM clustering_results ORDER BY id DESC LIMIT 1
        """)
        if cr:
            run = cr[0]
            top_d = _db_query("""
                SELECT concept_a, concept_b, kab_similarity, ml_similarity,
                       gap, disagreement_type, times_seen
                FROM clustering_disagreements
                WHERE run_id = %s ORDER BY gap DESC LIMIT 10
            """, (run[0],))
            state["clustering"] = {
                "run_date": run[1].isoformat() if run[1] else None,
                "n_concepts": run[2],
                "n_clusters_kab": run[3],
                "n_clusters_ml": run[4],
                "n_disagreements": run[5],
                "agreement_ratio": run[6],
                "top": [
                    {
                        "a": r[0], "b": r[1],
                        "kab": round(r[2], 3), "ml": round(r[3], 3),
                        "gap": round(r[4], 3), "type": r[5], "seen": r[6],
                    }
                    for r in top_d
                ],
            }
        else:
            state["clustering"] = None
    except Exception:
        state["clustering"] = None

    return state

@api_bp.route("/api/dashboard")
def api_dashboard():
    return _json_response(_gather_dashboard_state())

@api_bp.route("/api/dashboard/counts")
def api_dashboard_counts():
    """Counts rapides pour l'inventaire du dashboard."""
    counts: dict[str, int] = {}
    tables = [
        ("causal_claims", "causal_claims"),
        ("tensions", "dissensuengine_tensions"),
        ("novelty_assessments", "novelty_assessments"),
        ("hitbonenut_questions", "hitbonenut_questions"),
        ("hitbonenut_principles", "hitbonenut_principles"),
        ("analogies", "explorationengine_analogies"),
        ("explorations", "explorationengine_explorations"),
        ("selfmodel_states", "selfmodel_states"),
        ("beinoni_interactions", "beinoni_interactions"),
    ]
    for key, table in tables:
        try:
            rows = _db_query(f"SELECT COUNT(*) FROM {table}")  # noqa: S608
            counts[key] = rows[0][0] if rows else 0
        except Exception:
            counts[key] = 0
    return _json_response(counts)

@api_bp.route("/api/dashboard/stream")
def api_dashboard_stream():
    """SSE stream — émet dashboard_update toutes les 5 secondes."""
    def generate() -> Generator[str, None, None]:
        yield ": connected\n\n"
        while True:
            try:
                data = _gather_dashboard_state()
                payload = json.dumps(data, cls=TreeEncoder, ensure_ascii=False)
                yield f"event: dashboard_update\ndata: {payload}\n\n"
            except Exception as e:
                yield f"event: dashboard_error\ndata: {json.dumps({'error': str(e)})}\n\n"
            time.sleep(5)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )

# ── /api/state — état global du système ──────────────────

@api_bp.route("/api/state")
def api_state():
    """État complet du système pour le dashboard."""
    state: dict[str, Any] = {}
    try:
        from pool import get_conn
        with get_conn() as conn:
            with conn.cursor() as cur:
                # Compteurs DB
                for table, label in [
                    ("epistememory", "memories"),
                    ("selfmodel_predictions", "predictions"),
                    ("causal_claims", "claims"),
                    ("candidate_insights", "insights"),
                    ("intentkeeper_intentions", "intentions"),
                    ("sifrei_yesod_assertions", "assertions"),
                    ("omer_history", "omer_entries"),
                ]:
                    try:
                        cur.execute(f"SELECT count(*) FROM {table}")  # noqa: S608
                        state[label] = cur.fetchone()[0]
                    except Exception:
                        conn.rollback()
                        state[label] = None
                # Dernier Omer
                try:
                    cur.execute("SELECT max(applied_at) FROM omer_history")
                    row = cur.fetchone()
                    state["last_omer"] = row[0].isoformat() if row and row[0] else None
                except Exception:
                    conn.rollback()
                    state["last_omer"] = None
                # Hizdakchut transitions per hour (audit cycle 4, I3)
                try:
                    cur.execute(
                        "SELECT count(*) FROM hizdakchut_transitions "
                        "WHERE created_at > NOW() - INTERVAL '1 hour'"
                    )
                    state["hizdakchut_transitions_per_hour"] = cur.fetchone()[0]
                except Exception:
                    conn.rollback()
                    state["hizdakchut_transitions_per_hour"] = None
        # Partzufim / Hizdakchut / Tzimtzum depuis state.py
        from state import _TZIMTZUM_STATE, _NITZOTZOT_STATE, _IGULIM_STATE
        state["nitzotzot"] = _NITZOTZOT_STATE["count"]
        state["nitzotzot_cycle"] = _NITZOTZOT_STATE["cycle"]
        state["tzimtzum_active"] = _TZIMTZUM_STATE.get("active", False)
        state["igulim_forced"] = _IGULIM_STATE.get("forced", False)
        # Governors (Teli, Galgal, Lev)
        try:
            from kabbalah.governors import ThreeGovernors
            gov = ThreeGovernors(db_url=_get_db_url())
            gov_state = gov.assess_governance()
            state["governors"] = {
                "teli": gov_state.teli.score,
                "galgal": gov_state.galgal.score,
                "lev": gov_state.lev.score,
                "harmony": gov_state.harmony,
                "weakest": gov_state.weakest,
                "strongest": gov_state.strongest,
            }
        except Exception:
            state["governors"] = None
        # Circuit breaker Ollama
        try:
            from olamot import (
                _ollama_cb_failures, _ollama_cb_open_until,
                _OLLAMA_CB_THRESHOLD, _OLLAMA_CB_COOLDOWN,
            )
            import time as _t
            state["ollama_circuit_breaker"] = {
                "failures": _ollama_cb_failures,
                "threshold": _OLLAMA_CB_THRESHOLD,
                "is_open": _ollama_cb_failures >= _OLLAMA_CB_THRESHOLD
                           and _t.monotonic() < _ollama_cb_open_until,
                "cooldown_seconds": _OLLAMA_CB_COOLDOWN,
            }
        except Exception:
            state["ollama_circuit_breaker"] = None
    except Exception as e:
        state["error"] = str(e)
    return _json_response(state)

# ── Context Monitor (29 dimensions) ─────────────────────

@api_bp.route("/api/context-monitor")
def api_context_monitor():
    """Dernier état des 29 dimensions du Kli."""
    try:
        rows = _db_query(
            """
            SELECT olam, dimensions, score_global, created_at
            FROM context_monitor_log
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        if not rows:
            # F-014: fallback mémoire avant de créer un assess vide
            from masakh.context_monitor import ContextMonitor, DIMENSIONS, get_last_assessment
            _last = get_last_assessment()
            if _last:
                return _json_response(_last)
            empty = ContextMonitor().assess({"olam": "unknown"})
            return _json_response(empty)
        row = rows[0]
        return _json_response({
            "olam": row[0],
            "dimensions": row[1],
            "score_global": row[2],
            "timestamp": row[3].timestamp() if row[3] else 0,
        })
    except Exception as e:
        from masakh.context_monitor import ContextMonitor
        empty = ContextMonitor().assess({"olam": "unknown"})
        empty["error"] = str(e)
        return _json_response(empty)

# Sifrei Yesod routes : voir web/blueprints/sifrei.py (N1).

