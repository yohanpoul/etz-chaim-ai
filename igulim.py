"""igulim.py — עִגּוּלִים : mode cercles concentriques."""

from __future__ import annotations

import logging
import os
import time

log = logging.getLogger("etz-malkuth")
DB_URL = (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim"))

from state import (  # noqa: E402
    _IGULIM_STATE,
    log_igulim_switch as _log_igulim_switch,
)


def _consult_igulim(tree: dict, query: str) -> dict:
    """עִגּוּלִים — Consulter TOUS les modules en cercles concentriques.

    Avant le Tikkun, les Sephiroth n'ont pas de hiérarchie.
    Chaque module est un cercle au même niveau — il contribue
    ce qu'il peut, indépendamment des autres.

    Retourne un dict de contributions, chacune avec un poids.
    """
    contributions = {}  # {module_name: {data: ..., weight: float, status: str}}

    # ── Yesod (EpisteMemory) — rappel mémoire ──
    yesod = tree.get("yesod")
    if yesod:
        try:
            memories = yesod.recall(query, limit=10)
            weight = min(1.0, len(memories) / 10) * 0.8 if memories else 0.0
            contributions["yesod"] = {
                "data": {"memories": memories, "count": len(memories)},
                "weight": weight,
                "status": "ok",
                "label": "Mémoire",
            }
        except Exception as e:
            contributions["yesod"] = {
                "data": {}, "weight": 0.0, "status": f"error: {e}", "label": "Mémoire",
            }

    # ── Sifrei Yesod — doctrine EC-* ──
    try:
        from sifrei_yesod.api.query import SifreiYesodQuery
        _sy = SifreiYesodQuery(db_url=DB_URL)
        sy_assertions = _sy.search_assertions(query, limit=5)
        _sy.close()
        weight = min(1.0, len(sy_assertions) * 0.25) if sy_assertions else 0.0
        contributions["sifrei_yesod"] = {
            "data": {"assertions": sy_assertions, "count": len(sy_assertions)},
            "weight": weight,
            "status": "ok",
            "label": "Doctrine EC-*",
        }
    except Exception as e:
        contributions["sifrei_yesod"] = {
            "data": {}, "weight": 0.0, "status": f"error: {e}", "label": "Doctrine EC-*",
        }

    # ── Hod (SelfMap) — compétence / domaine ──
    hod = tree.get("hod")
    if hod:
        try:
            route_decision = hod.route(query)
            if route_decision.did_decline:
                weight = 0.1
            else:
                weight = route_decision.competence_score
            contributions["hod"] = {
                "data": {"route": route_decision, "declined": route_decision.did_decline},
                "weight": weight,
                "status": "ok",
                "label": "Compétence",
            }
        except Exception as e:
            contributions["hod"] = {
                "data": {}, "weight": 0.0, "status": f"error: {e}", "label": "Compétence",
            }

    # ── Netzach (IntentKeeper) — intentions actives ──
    netzach = tree.get("netzach")
    if netzach:
        try:
            active = netzach.db.get_active_intentions()
            # Filtrer les intentions liées à la query
            q_lower = query.lower()
            related = []
            for intent_obj in active:
                goal_lower = intent_obj.goal.lower() if hasattr(intent_obj, "goal") else ""
                q_words = set(q_lower.split())
                g_words = set(goal_lower.split())
                overlap = q_words & g_words - {"le", "la", "les", "de", "du", "des", "un", "une"}
                if len(overlap) >= 2:
                    related.append(intent_obj)
            weight = min(1.0, len(related) * 0.3) if related else 0.0
            contributions["netzach"] = {
                "data": {"intentions": related, "total_active": len(active)},
                "weight": weight,
                "status": "ok",
                "label": "Intentions",
            }
        except Exception as e:
            contributions["netzach"] = {
                "data": {}, "weight": 0.0, "status": f"error: {e}", "label": "Intentions",
            }

    # ── Tiferet (DissensuEngine) — tensions / cohérence ──
    tiferet = tree.get("tiferet")
    if tiferet:
        try:
            diag = tiferet.self_diagnose()
            n_tensions = diag.get("open_tensions", 0)
            weight = min(1.0, n_tensions * 0.2) if n_tensions > 0 else 0.1
            contributions["tiferet"] = {
                "data": diag,
                "weight": weight,
                "status": "ok",
                "label": "Tensions",
            }
        except Exception as e:
            contributions["tiferet"] = {
                "data": {}, "weight": 0.0, "status": f"error: {e}", "label": "Tensions",
            }

    # ── Gevurah (AutoJudge) — jugement ──
    gevurah = tree.get("gevurah")
    if gevurah:
        try:
            diag = gevurah.self_diagnose()
            n_exp = diag.get("total_experiments", 0)
            weight = min(1.0, n_exp * 0.1) if n_exp > 0 else 0.1
            contributions["gevurah"] = {
                "data": diag,
                "weight": weight,
                "status": "ok",
                "label": "Jugement",
            }
        except Exception as e:
            contributions["gevurah"] = {
                "data": {}, "weight": 0.0, "status": f"error: {e}", "label": "Jugement",
            }

    # ── Chesed (ExplorationEngine) — connexions ──
    chesed = tree.get("chesed")
    if chesed:
        try:
            domain = "general"
            hod_data = contributions.get("hod", {}).get("data", {})
            route = hod_data.get("route")
            if route and not hod_data.get("declined"):
                domain = route.detected_domain or "general"
            result = chesed.explore(query, seed_domain=domain, max_connections=5)
            n_novel = (len(result.novel_connections)
                       if hasattr(result, "novel_connections") and result.novel_connections
                       else 0)
            weight = min(1.0, n_novel * 0.3) if n_novel > 0 else 0.1
            contributions["chesed"] = {
                "data": {"exploration": result, "n_novel": n_novel, "domain": domain},
                "weight": weight,
                "status": "ok",
                "label": "Exploration",
            }
        except Exception as e:
            contributions["chesed"] = {
                "data": {}, "weight": 0.0, "status": f"error: {e}", "label": "Exploration",
            }

    # ── Binah (CausalEngine) — causalité ──
    binah = tree.get("binah")
    if binah:
        try:
            diag = binah.self_diagnose()
            n_graphs = diag.get("total_graphs", 0)
            weight = min(1.0, n_graphs * 0.2) if n_graphs > 0 else 0.1
            contributions["binah"] = {
                "data": diag,
                "weight": weight,
                "status": "ok",
                "label": "Causalité",
            }
        except Exception as e:
            contributions["binah"] = {
                "data": {}, "weight": 0.0, "status": f"error: {e}", "label": "Causalité",
            }

    # ── Chokmah (InsightForge) — insights ──
    chokmah = tree.get("chokmah")
    if chokmah:
        try:
            session = chokmah.forge(query, domain="", max_explore=3)
            validated = session.validated_insights or []
            weight = min(1.0, len(validated) * 0.4) if validated else 0.1
            contributions["chokmah"] = {
                "data": {"session": session, "validated": validated},
                "weight": weight,
                "status": "ok",
                "label": "Insights",
            }
        except Exception as e:
            contributions["chokmah"] = {
                "data": {}, "weight": 0.0, "status": f"error: {e}", "label": "Insights",
            }

    # ── Da'at (SelfModel) — self-model ──
    daat = tree.get("daat")
    if daat:
        try:
            state = daat.capture_state()
            weight = state.model_confidence * 0.5
            contributions["daat"] = {
                "data": {"state": state},
                "weight": weight,
                "status": "ok",
                "label": "Self-model",
            }
        except Exception as e:
            contributions["daat"] = {
                "data": {}, "weight": 0.0, "status": f"error: {e}", "label": "Self-model",
            }

    # ── Gématria (transversal) ──
    gematria = tree.get("gematria")
    if gematria:
        try:
            from gematria import extract_hebrew_terms
            terms = extract_hebrew_terms(query)
            all_equivs = []
            for hebrew, translit in terms:
                equivs = gematria.find_equivalences(hebrew, method="standard")
                all_equivs.extend(equivs)
            weight = min(1.0, len(all_equivs) * 0.3) if all_equivs else 0.0
            contributions["gematria"] = {
                "data": {"terms": terms, "equivalences": all_equivs},
                "weight": weight,
                "status": "ok",
                "label": "Gématria",
            }
        except Exception as e:
            contributions["gematria"] = {
                "data": {}, "weight": 0.0, "status": f"error: {e}", "label": "Gématria",
            }

    return contributions


def _synthesize_igulim(
    tree: dict, query: str, contributions: dict, intent: dict,
) -> tuple[str, dict]:
    """Synthèse Igulim — vote pondéré de toutes les contributions.

    Au lieu du flux hiérarchique Yosher (Keter->Malkuth), les cercles
    concentriques assemblent toutes les contributions au même niveau.
    Le poids de chaque module détermine son influence sur la réponse.

    Retourne (response, ctx) comme cmd_ask en mode Yosher.
    """
    from olamot import ollama_generate

    ctx = {"intent": intent, "mode": "igulim"}

    # ── Assembler le contexte depuis les contributions ──
    parts = []
    parts.append(f"[MODE: IGULIM — cercles concentriques, pas de hiérarchie]")
    parts.append(f"[Intent: type={intent.get('type', '?')}, depth={intent.get('depth', '?')}]")

    total_weight = 0.0
    active_modules = 0

    for name, contrib in sorted(contributions.items(),
                                 key=lambda x: x[1]["weight"], reverse=True):
        if contrib["status"] != "ok" or contrib["weight"] <= 0.0:
            continue
        active_modules += 1
        total_weight += contrib["weight"]

        label = contrib["label"]
        w = contrib["weight"]

        if name == "yesod":
            memories = contrib["data"].get("memories", [])
            if memories:
                parts.append(f"[{label} (poids={w:.2f}):]")
                for m in memories[:5]:
                    content = m.content[:200] if hasattr(m, "content") else str(m)[:200]
                    conf = m.confidence if hasattr(m, "confidence") else 0.0
                    parts.append(f"  - [{conf:.1f}] {content}")

        elif name == "hod":
            route = contrib["data"].get("route")
            if route and not contrib["data"].get("declined"):
                parts.append(f"[{label} (poids={w:.2f}): "
                             f"domaine={route.detected_domain}, "
                             f"score={route.competence_score:.2f}]")
                ctx["route_decision"] = route

        elif name == "netzach":
            intentions = contrib["data"].get("intentions", [])
            if intentions:
                parts.append(f"[{label} (poids={w:.2f}):]")
                for i in intentions[:3]:
                    parts.append(f"  - {i.goal} ({i.progress:.0%})")

        elif name == "tiferet":
            n_t = contrib["data"].get("open_tensions", 0)
            if n_t > 0:
                parts.append(f"[{label} (poids={w:.2f}): "
                             f"{n_t} tension(s) ouverte(s)]")

        elif name == "gevurah":
            n_exp = contrib["data"].get("total_experiments", 0)
            rej = contrib["data"].get("rejection_rate", 0)
            parts.append(f"[{label} (poids={w:.2f}): "
                         f"{n_exp} exp., rejet={rej:.0%}]")

        elif name == "chesed":
            n_novel = contrib["data"].get("n_novel", 0)
            domain = contrib["data"].get("domain", "?")
            parts.append(f"[{label} (poids={w:.2f}): "
                         f"{n_novel} connexion(s) nouvelle(s), domaine={domain}]")

        elif name == "binah":
            n_g = contrib["data"].get("total_graphs", 0)
            n_c = contrib["data"].get("total_claims", 0)
            parts.append(f"[{label} (poids={w:.2f}): "
                         f"{n_g} graphe(s), {n_c} claim(s)]")

        elif name == "chokmah":
            validated = contrib["data"].get("validated", [])
            if validated:
                parts.append(f"[{label} (poids={w:.2f}):]")
                for ins in validated:
                    parts.append(f"  - [{ins.confidence:.2f}] {ins.description}")
            ctx["forge_session"] = contrib["data"].get("session")

        elif name == "daat":
            state = contrib["data"].get("state")
            if state:
                parts.append(f"[{label} (poids={w:.2f}): "
                             f"confiance={state.model_confidence:.2f}]")

        elif name == "sifrei_yesod":
            assertions = contrib["data"].get("assertions", [])
            if assertions:
                parts.append(f"[{label} (poids={w:.2f}):]")
                for sa in assertions[:5]:
                    aid = sa.get("assertion_id", "?")
                    text = sa.get("assertion", "")[:200]
                    sim = sa.get("similarity", 0.0)
                    parts.append(f"  - [{aid}] (sim={sim:.2f}) {text}")

        elif name == "gematria":
            equivs = contrib["data"].get("equivalences", [])
            if equivs:
                parts.append(f"[{label} (poids={w:.2f}):]")
                seen = set()
                for eq in equivs[:5]:
                    pair = (eq.term_a, eq.term_b)
                    if pair in seen:
                        continue
                    seen.add(pair)
                    parts.append(f"  - {eq.term_a} = {eq.term_b} [{eq.method}={eq.shared_value}]")

    # Confiance globale = moyenne pondérée
    if total_weight > 0:
        avg_weight = total_weight / active_modules
    else:
        avg_weight = 0.0
    ctx["response_confidence"] = avg_weight
    ctx["igulim_active_modules"] = active_modules
    ctx["igulim_total_weight"] = total_weight

    parts.append(f"[Confiance agrégée (vote pondéré): {avg_weight:.2f}, "
                 f"{active_modules} module(s) actif(s)]")

    igulim_context = "\n".join(parts)
    olam = intent.get("depth", "yetzirah")

    prompt = f"""You are Etz Chaim, a cognitive architecture modeled on the kabbalistic Tree of Life.
You are operating in IGULIM mode — concentric circles, no hierarchy.
All modules have contributed equally. Synthesize their contributions.
Answer in French, with depth and precision. Be direct.

Context gathered from the circles (Igulim):
{igulim_context}

User question: {query}
Response:"""

    igulim_kavvanah = {
        "intention": f"synthèse Igulim — {intent.get('type', 'question')}, profondeur {olam}",
        "critere_succes": f"intégrer les {active_modules} contributions en réponse cohérente, confiance > {avg_weight:.2f}",
        "anti_pattern": "ne pas ignorer les contributions à faible poids, ne pas fabriquer de consensus artificiel",
    }

    try:
        response, latency = ollama_generate(olam, prompt, timeout=300, kavvanah=igulim_kavvanah)
        ctx["generation_olam"] = olam
        ctx["generation_latency"] = latency
    except Exception as e:
        response = f"[Erreur génération — Igulim/{olam}] {e}"
        ctx["generation_olam"] = olam
        ctx["generation_latency"] = 0.0

    ctx["response"] = response
    return response, ctx


def _cmd_ask_igulim(tree: dict, query: str) -> None:
    """Mode Igulim — cercles concentriques, pas de hiérarchie."""
    from main import _classify_intent  # lazy import — function lives in main.py

    print("═══════════════════════════════════════════════════════════")
    print("  Etz Chaim — Ask Mode — עִגּוּלִים IGULIM (Cercles)")
    print(f"  Question : {query}")
    print("═══════════════════════════════════════════════════════════")
    print()

    t0 = time.monotonic()

    # 1. Keter — classification (même en Igulim, l'intention pré-existe)
    print("  ⟐ ① Keter — classification de l'intention...")
    intent = _classify_intent(query)
    print(f"    type={intent['type']}, depth={intent['depth']}")

    # 2. Consultation parallèle de tous les modules
    print()
    print("╔═══════════════════════════════════════════════════════╗")
    print("║  עִגּוּלִים — Consultation en cercles concentriques    ║")
    print("╚═══════════════════════════════════════════════════════╝")
    print()

    print("  ⟐ Consultation parallèle de tous les modules...")
    contributions = _consult_igulim(tree, query)

    # Afficher chaque contribution
    igulim_report = []
    for name, contrib in sorted(contributions.items(),
                                 key=lambda x: x[1]["weight"], reverse=True):
        label = contrib["label"]
        w = contrib["weight"]
        status = contrib["status"]
        marker = "●" if status == "ok" and w > 0 else "○"
        print(f"    {marker} {label:<14} poids={w:.2f}  [{status}]")
        igulim_report.append(f"  {marker} {label:<14} poids={w:.2f}  [{status}]")

    active = sum(1 for c in contributions.values() if c["status"] == "ok" and c["weight"] > 0)
    print(f"    → {active} module(s) actif(s)")

    # 3. Synthèse par vote pondéré
    print()
    print("  ⟐ Synthèse par vote pondéré...")
    response, ctx = _synthesize_igulim(tree, query, contributions, intent)
    # Audit cycle 4, N3 : generation_latency est stockée en MILLISECONDES
    # (cf. ollama_generate qui retourne latency_ms et ohr_yashar:2614 qui
    # somme des latency_ms). Le bug "22040.9s" venait de l'affichage brut.
    t_gen_ms = ctx.get("generation_latency", 0.0)
    print(f"    Généré en {t_gen_ms/1000:.1f}s via {ctx.get('generation_olam', '?')}")

    # 4. Or Chozer minimal — stockage en mémoire
    print()
    print("  ⟐ ↑ Stockage en mémoire (Yesod)...")
    yesod = tree.get("yesod")
    if yesod:
        try:
            route = contributions.get("hod", {}).get("data", {}).get("route")
            domain = (route.detected_domain
                      if route and not contributions.get("hod", {}).get("data", {}).get("declined")
                      else "general")
            yesod.remember(
                content=f"Q: {query[:100]} → R: {response[:200]}",
                source_sephirah="malkuth",
                confidence=ctx.get("response_confidence", 0.3),
                domain=domain,
                tags=["ask-mode", "igulim", "response"],
            )
            print(f"    Persisté (domaine={domain})")
        except Exception as e:
            print(f"    ⚠ {e}")

    # ═══════════════════════════════════════════════════════════
    #   RAPPORT FINAL — Igulim
    # ═══════════════════════════════════════════════════════════
    elapsed = time.monotonic() - t0
    print()
    print("═══════════════════════════════════════════════════════════")
    print("  RAPPORT — Etz Chaim Ask (Igulim)")
    print("═══════════════════════════════════════════════════════════")

    # Cercles
    print()
    print("┌─── עִגּוּלִים (cercles) ──────────────────────────────────┐")
    for line in igulim_report:
        print(f"│ {line}")
    print("└──────────────────────────────────────────────────────────┘")

    # Réponse
    print()
    print("┌─── מַלְכוּת (réponse) ──────────────────────────────────┐")
    for resp_line in response.split("\n"):
        print(f"│ {resp_line}")
    print("└──────────────────────────────────────────────────────────┘")

    # Méta
    print()
    print("── Méta ──")
    print(f"  Mode               : עִגּוּלִים IGULIM (cercles concentriques)")
    reason = "forcé par CLI" if _IGULIM_STATE["forced"] else "bascule auto (confiance < 0.2)"
    print(f"  Raison             : {reason}")
    print(f"  Modules actifs     : {active}/{len(contributions)}")
    print(f"  Confiance agrégée  : {ctx.get('response_confidence', 0):.2f}")
    print(f"  Temps total        : {elapsed:.1f}s")
    print(f"  Génération         : {t_gen_ms/1000:.1f}s ({ctx.get('generation_olam', '?')})")
    print(f"  Bascules Y→I total : {_IGULIM_STATE['switches']}")
    print()
