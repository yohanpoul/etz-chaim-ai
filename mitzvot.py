"""mitzvot.py — מִצְווֹת : les commandes CLI de l'Arbre."""

from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
import sys
import time
import traceback
from pathlib import Path

log = logging.getLogger("etz-malkuth")

DB_URL = (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim"))

# ─── État global — importé depuis state.py ──────────────────
from state import (  # noqa: E402
    _NITZOTZOT_STATE,
    _HISHTALSHELUT_STATE,
    _OLAMOT_CHAIN,
    collect_nitzutz as _collect_nitzutz,
)

# ─── Singletons — initialisés lazy dans les commandes ────────
_NESHAMOT_ENGINE = None           # NeshamotEngine singleton — init lazy
_HISHTALSHELUT_ENGINE = None      # HishtalshelutEngine singleton — init lazy


def cmd_intend(tree: dict, goal: str) -> None:
    """Créer une intention longue durée via Netzach."""
    print("═══════════════════════════════════════════════════════════")
    print(f"  Etz Chaim — Intend Mode (Netzach)")
    print(f"  Intention : {goal}")
    print("═══════════════════════════════════════════════════════════")
    print()

    netzach = tree.get("netzach")
    if not netzach:
        print("✗ IntentKeeper (Netzach) non initialisé.")
        return

    try:
        intention = netzach.set_intention(goal=goal)
        print(f"  ✦ Intention créée")
        print(f"    ID       : {intention.id}")
        print(f"    Goal     : {intention.goal}")
        print(f"    Status   : {intention.status}")
        print(f"    Durée max: {intention.max_duration_days} jours")
        if intention.strategy:
            print(f"    Stratégie: {intention.strategy}")
        print()

        # Afficher les intentions actives
        active = netzach.db.get_active_intentions()
        print(f"  Intentions actives : {len(active)}")
        for a in active:
            print(f"    [{a.status}] {a.goal} ({a.progress:.0%})")

    except Exception as e:
        print(f"  ✗ Erreur: {e}")
        traceback.print_exc()


# ─── Mode EXPLORE ────────────────────────────────────────────

def cmd_explore(tree: dict, query: str) -> None:
    """Exploration inter-domaines via Chesed + Chokmah."""
    print("═══════════════════════════════════════════════════════════")
    print(f"  Etz Chaim — Explore Mode (Chesed + Chokmah)")
    print(f"  Question : {query}")
    print("═══════════════════════════════════════════════════════════")
    print()

    # Déterminer le domaine seed via Hod
    hod = tree.get("hod")
    seed_domain = "general"
    if hod:
        try:
            route = hod.route(query)
            seed_domain = route.detected_domain or "general"
            print(f"  Domaine seed (via Hod) : {seed_domain}")
        except Exception as e:
            log.debug("display: %s", e)

    # Exploration via Chesed
    chesed = tree.get("chesed")
    if chesed:
        print()
        print("⟐ Chesed — Exploration inter-domaines...")
        try:
            result = chesed.explore(
                query=query,
                seed_domain=seed_domain,
                max_connections=20,
            )
            print(f"  Statut       : {result.status}")
            print(f"  Domaines     : {', '.join(result.domains_explored)}")
            print(f"  Connexions   : {result.total_connections}")
            print(f"  Nouvelles    : {result.novel_connections}")
            if result.avg_novelty > 0:
                print(f"  Nouveauté moy: {result.avg_novelty:.2f}")

            if result.connections:
                print()
                print("  Connexions trouvées :")
                for c in result.connections[:10]:
                    print(f"    [{c.connection_type}] {c.concept_a} ({c.domain_a}) "
                          f"↔ {c.concept_b} ({c.domain_b})")
                    print(f"      nouveauté={c.novelty_score:.2f}, "
                          f"pertinence={c.relevance_score:.2f}")
                    print(f"      {c.description[:100]}")
        except Exception as e:
            print(f"  ✗ Erreur: {e}")
            traceback.print_exc()
    else:
        print("  ✗ ExplorationEngine (Chesed) non initialisé")

    # Forge via Chokmah
    chokmah = tree.get("chokmah")
    if chokmah:
        print()
        print("⟐ Chokmah — Forge d'insights...")
        try:
            session = chokmah.forge(query, domain=seed_domain, max_explore=10)
            print(f"  Candidats    : {session.total_candidates}")
            print(f"  Insights     : {session.insights_found}")
            print(f"  Pearl level  : {session.pearl_level}")
            if session.validated_insights:
                print()
                for ins in session.validated_insights:
                    print(f"  ★ [{ins.confidence:.2f}] {ins.description}")
        except Exception as e:
            print(f"  ✗ Erreur: {e}")
            traceback.print_exc()
    else:
        print("  ✗ InsightForge (Chokmah) non initialisé")

    print()


# ─── Mode STATUS ─────────────────────────────────────────────

def cmd_status(tree: dict) -> None:
    """Diagnostic de l'Arbre — état de chaque Sephirah."""
    print("═══════════════════════════════════════════════════════════")
    print("  Etz Chaim — Status")
    print("═══════════════════════════════════════════════════════════")
    print()

    # Olamot report
    try:
        import olamot
        print(olamot.report())
    except Exception as e:
        print(f"  ⚠ Olamot report: {e}")
    print()

    # État de chaque module
    SEPHIROT_NAMES = {
        "yesod":   "Yesod    (EpisteMemory)",
        "hod":     "Hod      (SelfMap)",
        "netzach": "Netzach  (IntentKeeper)",
        "lamed":   "Lamed    (FailureToInsight)",
        "tiferet": "Tiferet  (DissensuEngine)",
        "gevurah": "Gevurah  (AutoJudge)",
        "chesed":  "Chesed   (ExplorationEngine)",
        "daat":    "Da'at    (SelfModel)",
        "binah":   "Binah    (CausalEngine)",
        "chokmah": "Chokmah  (InsightForge)",
    }

    print("Sephiroth :")
    for key, label in SEPHIROT_NAMES.items():
        mod = tree.get(key)
        if mod is None:
            print(f"  ✗ {label:35s} — NON INITIALISÉ")
        else:
            # Tenter self_diagnose si disponible
            if hasattr(mod, "self_diagnose"):
                try:
                    diag = mod.self_diagnose()
                    summary_parts = []
                    for k in ["total_entries", "total_competences", "active_intentions",
                              "total_experiments", "total_explorations", "total_graphs",
                              "open_tensions", "total_sessions"]:
                        if k in diag:
                            summary_parts.append(f"{k}={diag[k]}")
                    summary = ", ".join(summary_parts[:3]) if summary_parts else "OK"
                    print(f"  ✦ {label:35s} — {summary}")
                except Exception as e:
                    print(f"  ⚠ {label:35s} — Erreur diag: {e}")
            elif hasattr(mod, "introspect"):
                try:
                    stats = mod.introspect()
                    print(f"  ✦ {label:35s} — entries={stats.total_entries}")
                except Exception as e:
                    print(f"  ⚠ {label:35s} — Erreur: {e}")
            else:
                print(f"  ✦ {label:35s} — OK")
    print()

    # ── Nitzotzot — Tikkun global ────────────────────────────
    count = _NITZOTZOT_STATE["count"]
    cycle = _NITZOTZOT_STATE["cycle"]
    pct = (count / 288 * 100) if count > 0 else 0.0
    print("Tikkun (288 Nitzotzot) :")
    print(f"  Nitzotzot récupérées : {count}/288 — Tikkun : {pct:.1f}%")
    print(f"  Cycle actuel         : {cycle}")
    if _NITZOTZOT_STATE["tikkun_history"]:
        print(f"  Cycles complétés     : {len(_NITZOTZOT_STATE['tikkun_history'])}")
    # Répartition par source
    if _NITZOTZOT_STATE["log"]:
        sources: dict[str, int] = {}
        for entry in _NITZOTZOT_STATE["log"]:
            src = entry.get("source", "?")
            if src != "tikkun":  # ignorer les marqueurs de cycle
                sources[src] = sources.get(src, 0) + 1
        if sources:
            parts = [f"{src}={n}" for src, n in sorted(sources.items(), key=lambda x: -x[1])]
            print(f"  Par source           : {', '.join(parts)}")
    # Dernières étincelles
    recent = [e for e in _NITZOTZOT_STATE["log"][-5:] if e.get("source") != "tikkun"]
    if recent:
        print(f"  Dernières étincelles :")
        for e in recent:
            print(f"    ✦ [{e['source']}] {e['description'][:80]}")
    print()


# ─── Mode CHAT ───────────────────────────────────────────────

INTENT_PROMPT = """You are a router. Classify the user message into exactly one mode.

Modes:
- "ask" — a question, request for information or analysis
- "intend" — the user declares a long-term goal or project intention
- "explore" — the user wants to explore connections between domains, brainstorm, or discover
- "status" — the user asks about system state, health, or diagnostics

User message: {message}

Reply with ONLY the mode name (ask, intend, explore, or status). Nothing else."""


def _detect_intent(message: str) -> str:
    """Classifier le message utilisateur via Yetzirah (rapide)."""
    # Commandes directes — pas besoin du LLM
    lower = message.strip().lower()
    if lower in ("status", "état", "etat", "diagnostic"):
        return "status"
    if lower.startswith(("intend:", "intention:", "je veux", "mon objectif", "je compte")):
        return "intend"
    if lower.startswith(("explore:", "explorer", "connexions entre", "liens entre")):
        return "explore"

    # Classification via Yetzirah
    try:
        from olamot import ollama_generate
        response, _ = ollama_generate(
            "assiah",  # classification rapide → Assiah
            INTENT_PROMPT.format(message=message),
            timeout=10,
            kavvanah={
                "intention": "Identifier l'intention profonde de l'utilisateur",
                "critere_succes": "Intention classifiée avec confiance > 0.7",
                "anti_pattern": "Ne pas inventer une intention si le message est ambigu",
            },
            context_items=[f"Message utilisateur: {message[:100]}"],
            domain="intent_classification",
        )
        mode = response.strip().lower().split()[0] if response.strip() else "ask"
        if mode in ("ask", "intend", "explore", "status"):
            return mode
    except Exception as e:
        log.debug("fallback: %s", e)

    return "ask"


def _generate_response(
    tree: dict,
    message: str,
    conversation: list[dict],
) -> str:
    """Générer une réponse conversationnelle via l'Arbre.

    1. Rappel mémoire (Yesod)
    2. Contexte de la conversation récente
    3. Génération via Yetzirah (tâches courantes) ou Briah (raisonnement profond)
    """
    from olamot import ollama_generate

    # Rappel mémoire
    yesod = tree.get("yesod")
    memory_context = ""
    if yesod:
        try:
            memories = yesod.recall(message, limit=3, min_confidence=0.3)
            if memories:
                mem_lines = []
                for m in memories:
                    content = m.content[:200] if hasattr(m, "content") else str(m)[:200]
                    conf = m.confidence if hasattr(m, "confidence") else 0.0
                    mem_lines.append(f"  [{conf:.1f}] {content}")
                memory_context = "Relevant memories:\n" + "\n".join(mem_lines) + "\n\n"
        except Exception as e:
            log.debug("fallback: %s", e)

    # Contexte de conversation (derniers échanges)
    conv_context = ""
    if conversation:
        recent = conversation[-6:]  # 3 derniers échanges
        conv_lines = []
        for turn in recent:
            role = turn["role"]
            text = turn["content"][:300]
            conv_lines.append(f"{role}: {text}")
        conv_context = "Recent conversation:\n" + "\n".join(conv_lines) + "\n\n"

    # Routage : questions longues/profondes → Briah, sinon Yetzirah
    olam = "yetzirah"
    if len(message) > 200 or any(w in message.lower() for w in [
        "pourquoi", "explique", "analyse", "compare", "démontre",
        "raisonne", "prouve", "causalité", "isomorphisme",
    ]):
        olam = "briah"

    prompt = f"""{memory_context}{conv_context}You are Etz Chaim, a cognitive architecture modeled on the kabbalistic Tree of Life. You answer in French, with depth and precision. You are direct — no filler.

User: {message}
Response:"""

    # Enrichissement contextuel pour le pipeline Sod HaKli
    _domain = "conversation"
    for _kw, _d in [("kabbale", "kabbale_lurianique"), ("sefirot", "kabbale_lurianique"),
                     ("code", "code"), ("python", "code"), ("cause", "causal"),
                     ("zohar", "kabbale_lurianique"), ("luria", "kabbale_lurianique")]:
        if _kw in message.lower():
            _domain = _d
            break
    _facts = None
    if yesod and memories:
        _facts = [m.content[:200] if hasattr(m, "content") else str(m)[:200]
                  for m in memories[:3]]

    try:
        response, latency = ollama_generate(
            olam, prompt, timeout=300,
            kavvanah={
                "intention": "Produire une réponse alignée avec l'intention détectée et l'état du système",
                "critere_succes": "Réponse cohérente avec le domaine et les faits disponibles",
                "anti_pattern": "Ne pas halluciner de faits non présents dans le contexte",
            },
            principles=["Répondre en français avec profondeur et précision, sans remplissage"],
            domain=_domain,
            facts=_facts,
        )
        return response
    except Exception as e:
        return f"[Erreur génération — {olam}] {e}"


def cmd_chat(tree: dict) -> None:
    """Conversation interactive — Malkuth comme porte d'entrée permanente."""
    print("═══════════════════════════════════════════════════════════")
    print("  Etz Chaim — Chat Mode")
    print("  L'Arbre écoute. Parlez.")
    print("═══════════════════════════════════════════════════════════")
    print()
    print("  Commandes : 'quit' pour sortir, 'status' pour l'état")
    print("  L'intent est détecté automatiquement (ask/intend/explore)")
    print()

    yesod = tree.get("yesod")
    conversation: list[dict] = []
    turn_count = 0

    while True:
        # Prompt
        try:
            user_input = input("vous → ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nShalom.")
            break

        if not user_input:
            continue

        # Commandes de sortie
        if user_input.lower() in ("quit", "exit", "q", "bye", "shalom"):
            print("Shalom.")
            break

        turn_count += 1

        # Persister le message utilisateur en Yesod
        if yesod:
            try:
                yesod.remember(
                    content=f"[chat #{turn_count}] user: {user_input}",
                    source_sephirah="malkuth",
                    confidence=0.9,
                    domain="conversation",
                    tags=["chat", "user-input"],
                    ttl_days=30,
                    generate_embedding=True,
                )
            except Exception as e:
                log.debug("fallback: %s", e)

        # Détecter l'intent
        intent = _detect_intent(user_input)

        # ── IntentKeeper : enregistrer le heartbeat sur les intentions actives ──
        netzach = tree.get("netzach")
        if netzach:
            try:
                active_intentions = netzach.db.get_active_intentions()
                for ai in active_intentions:
                    netzach.db.record_heartbeat(
                        ai.id, "user_interaction",
                        {"intent": intent, "message_preview": user_input[:100]},
                    )
            except Exception as e:
                log.debug("fallback: %s", e)

        # Dispatcher
        if intent == "status":
            cmd_status(tree)

        elif intent == "intend":
            # Extraire le goal (enlever les préfixes courants)
            goal = user_input
            for prefix in ("intend:", "intention:", "je veux ", "mon objectif: ",
                           "je compte "):
                if goal.lower().startswith(prefix):
                    goal = goal[len(prefix):].strip()
                    break
            cmd_intend(tree, goal)

        elif intent == "explore":
            query = user_input
            for prefix in ("explore:", "explorer ", "connexions entre ", "liens entre "):
                if query.lower().startswith(prefix):
                    query = query[len(prefix):].strip()
                    break
            cmd_explore(tree, query)

        else:
            # Mode ask — conversation via LLM
            print()
            response = _generate_response(tree, user_input, conversation)
            print(f"etz → {response}")
            print()

            # Stocker dans la conversation
            conversation.append({"role": "user", "content": user_input})
            conversation.append({"role": "etz", "content": response})

            # Persister la réponse en Yesod
            if yesod:
                try:
                    yesod.remember(
                        content=f"[chat #{turn_count}] etz: {response[:500]}",
                        source_sephirah="yetzirah",
                        confidence=0.6,
                        domain="conversation",
                        tags=["chat", "etz-response"],
                        ttl_days=30,
                        generate_embedding=True,
                    )
                except Exception as e:
                    log.debug("fallback: %s", e)

    # Résumé de session
    if turn_count > 0 and yesod:
        try:
            yesod.remember(
                content=(
                    f"Chat session: {turn_count} échange(s). "
                    f"Dernière question: {conversation[-2]['content'][:100] if len(conversation) >= 2 else 'N/A'}"
                ),
                source_sephirah="malkuth",
                confidence=0.7,
                domain="conversation",
                tags=["chat", "session-summary"],
                ttl_days=90,
                generate_embedding=True,
            )
        except Exception as e:
            log.debug("fallback: %s", e)

    print(f"\n  Session : {turn_count} échange(s)")


# ─── Mode IMPORT ────────────────────────────────────────────

def cmd_import(
    tree: dict, source_type: str, source: str, domain: str,
    max_pages: int = 500,
) -> None:
    """Importer des sources dans EpisteMemory via Chesed-de-Yesod."""
    from importer import ImportEngine

    print("═══════════════════════════════════════════════════════════")
    print(f"  Etz Chaim — Import Mode (Chesed-de-Yesod)")
    print(f"  Type    : {source_type}")
    print(f"  Source  : {source}")
    print(f"  Domaine : {domain}")
    if source_type == "site":
        print(f"  Max pages : {max_pages}")
    print("═══════════════════════════════════════════════════════════")
    print()

    yesod = tree.get("yesod")
    if not yesod:
        print("✗ EpisteMemory (Yesod) non initialisé — impossible d'importer.")
        return

    engine = ImportEngine(yesod=yesod)

    try:
        if source_type == "book":
            result = engine.import_book(source, domain=domain)
        elif source_type == "url":
            result = engine.import_url(source, domain=domain)
        elif source_type == "youtube":
            result = engine.import_youtube(source, domain=domain)
        elif source_type == "site":
            result = engine.import_site(source, domain=domain, max_pages=max_pages)
        else:
            print(f"✗ Type inconnu : {source_type} (book/url/youtube/site)")
            return
    except Exception as e:
        print(f"✗ Erreur d'import : {e}")
        traceback.print_exc()
        return

    # Rapport
    print()
    print("═══════════════════════════════════════════════════════════")
    print(f"  Résultat — {result.source_title}")
    print("═══════════════════════════════════════════════════════════")
    print(f"  Chunks totaux      : {result.total_chunks}")
    print(f"  Importés           : {result.imported}")
    print(f"  Ignorés (doublons) : {result.skipped}")
    print(f"  Doublons détectés  : {result.duplicates_found}")
    print(f"  Contradictions     : {result.contradictions_found}")
    if result.subdomains:
        print(f"  Sous-domaines      :")
        for sd, count in sorted(result.subdomains.items(), key=lambda x: -x[1]):
            print(f"    {sd:25s} : {count}")
    if result.errors:
        print(f"  Erreurs            :")
        for err in result.errors:
            print(f"    ✗ {err}")
    print()


# ─── Mode MEMORY ────────────────────────────────────────────

def _memory_query(db_url: str, sql: str, params=None) -> list[tuple]:
    """Requête sur la DB pour les stats mémoire — via pool (CB-protégé).

    Audit cycle 4, C5 : init_pool(db_url) idempotent, pas de
    psycopg2.connect direct. Les commandes CLI partagent le pool du
    daemon si lancées dans le même process ; sinon créent leur propre
    pool dédié au CLI.
    """
    from pool import get_conn, init_pool
    init_pool(db_url)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def cmd_memory_stats(db_url: str) -> None:
    """Résumé global de la mémoire — Hod-de-Yesod."""
    print("═══════════════════════════════════════════════════════════")
    print("  Etz Chaim — Memory Stats (Hod-de-Yesod)")
    print("═══════════════════════════════════════════════════════════")
    print()

    # Stats globales
    rows = _memory_query(db_url, """
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE epistemic_status != 'deprecated') AS active,
            COUNT(*) FILTER (WHERE epistemic_status = 'deprecated') AS deprecated,
            AVG(confidence) AS avg_conf,
            MIN(created_at) AS oldest,
            MAX(created_at) AS newest,
            COUNT(DISTINCT domain) AS n_domains,
            AVG(access_count) AS avg_access
        FROM epistememory
    """)
    total, active, deprecated, avg_conf, oldest, newest, n_domains, avg_access = rows[0]

    print(f"  Entrées totales    : {total}")
    print(f"  Actives            : {active}")
    print(f"  Deprecated         : {deprecated}")
    print(f"  Confiance moyenne  : {avg_conf:.2f}" if avg_conf else "  Confiance moyenne  : —")
    print(f"  Domaines distincts : {n_domains}")
    print(f"  Accès moyen        : {avg_access:.1f}" if avg_access else "  Accès moyen        : 0")
    if oldest:
        print(f"  Plus ancienne      : {oldest:%Y-%m-%d %H:%M}")
    if newest:
        print(f"  Plus récente       : {newest:%Y-%m-%d %H:%M}")
    print()

    # Par statut épistémique
    rows = _memory_query(db_url, """
        SELECT epistemic_status, COUNT(*), AVG(confidence)
        FROM epistememory
        GROUP BY epistemic_status
        ORDER BY COUNT(*) DESC
    """)
    if rows:
        print("  Par statut épistémique :")
        for status, count, conf in rows:
            print(f"    {status:20s} : {count:4d} entrées  (conf moy: {conf:.2f})")
        print()

    # Par source_sephirah
    rows = _memory_query(db_url, """
        SELECT source_sephirah, COUNT(*), AVG(confidence)
        FROM epistememory
        WHERE epistemic_status != 'deprecated'
        GROUP BY source_sephirah
        ORDER BY COUNT(*) DESC
    """)
    if rows:
        print("  Par source (Sephirah) :")
        for seph, count, conf in rows:
            print(f"    {seph:20s} : {count:4d} entrées  (conf moy: {conf:.2f})")
        print()

    # Sources importées (livres/URLs/vidéos via source_detail)
    rows = _memory_query(db_url, """
        SELECT
            source_detail->>'source_type' AS stype,
            source_detail->>'source_title' AS stitle,
            COUNT(*) AS chunks,
            AVG(confidence) AS conf
        FROM epistememory
        WHERE source_detail IS NOT NULL
          AND source_detail->>'source_type' IS NOT NULL
        GROUP BY stype, stitle
        ORDER BY COUNT(*) DESC
    """)
    if rows:
        print("  Sources importées :")
        for stype, stitle, chunks, conf in rows:
            label = {"book": "LIVRE", "url": "WEB", "youtube": "VIDEO"}.get(stype, stype)
            title = (stitle[:45] + "...") if stitle and len(stitle) > 48 else (stitle or "?")
            print(f"    [{label:5s}] {title:48s} : {chunks:4d} chunks  (conf: {conf:.1f})")
        print()

    # Contradictions
    rows = _memory_query(db_url, """
        SELECT COUNT(*) FROM open_contradictions
    """)
    n_contradictions = rows[0][0] if rows else 0
    print(f"  Contradictions ouvertes : {n_contradictions}")

    # Expirations proches
    rows = _memory_query(db_url, """
        SELECT COUNT(*) FROM near_expiration
    """)
    n_expiring = rows[0][0] if rows else 0
    if n_expiring:
        print(f"  Expirent sous 7 jours  : {n_expiring}")
    print()


def cmd_memory_domains(db_url: str) -> None:
    """Liste tous les domaines avec stats détaillées."""
    print("═══════════════════════════════════════════════════════════")
    print("  Etz Chaim — Memory Domains")
    print("═══════════════════════════════════════════════════════════")
    print()

    rows = _memory_query(db_url, """
        SELECT
            COALESCE(domain, '(sans domaine)') AS dom,
            COUNT(*) AS total,
            AVG(confidence) AS avg_conf,
            MIN(confidence) AS min_conf,
            MAX(confidence) AS max_conf,
            COUNT(*) FILTER (WHERE epistemic_status = 'fact') AS facts,
            COUNT(*) FILTER (WHERE epistemic_status = 'verified_once') AS verified,
            COUNT(*) FILTER (WHERE epistemic_status = 'hypothesis') AS hypotheses,
            COUNT(*) FILTER (WHERE epistemic_status = 'contested') AS contested,
            COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS with_embedding,
            AVG(access_count) AS avg_access,
            MIN(created_at) AS oldest,
            MAX(created_at) AS newest
        FROM epistememory
        WHERE epistemic_status != 'deprecated'
        GROUP BY domain
        ORDER BY COUNT(*) DESC
    """)

    if not rows:
        print("  Aucune entrée en mémoire.")
        return

    for (dom, total, avg_conf, min_conf, max_conf, facts, verified,
         hypotheses, contested, with_emb, avg_access, oldest, newest) in rows:
        print(f"  {dom}")
        print(f"    Entrées      : {total}")
        print(f"    Confiance    : moy={avg_conf:.2f}  min={min_conf:.2f}  max={max_conf:.2f}")
        print(f"    Statuts      : {facts} facts, {verified} verified, "
              f"{hypotheses} hypotheses, {contested} contested")
        print(f"    Embeddings   : {with_emb}/{total}")
        if avg_access:
            print(f"    Accès moyen  : {avg_access:.1f}")
        print(f"    Période      : {oldest:%Y-%m-%d} → {newest:%Y-%m-%d}")

        # Sous-domaines (si domaine parent type "astrologie")
        sub_rows = _memory_query(db_url, """
            SELECT domain, COUNT(*)
            FROM epistememory
            WHERE epistemic_status != 'deprecated'
              AND domain LIKE %s
              AND domain != %s
            GROUP BY domain
            ORDER BY COUNT(*) DESC
        """, (dom + "/%", dom))
        if sub_rows:
            print(f"    Sous-domaines :")
            for sub_dom, sub_count in sub_rows:
                # Afficher seulement la partie après le /
                short = sub_dom.split("/", 1)[1] if "/" in sub_dom else sub_dom
                print(f"      {short:25s} : {sub_count}")

        print()


# ─── Mode DAEMON ────────────────────────────────────────────

DAEMON_HOME = Path.home() / ".etz-chaim"
PLIST_SRC = DAEMON_HOME / "com.etz-chaim.daemon.plist"
PLIST_DST = Path.home() / "Library" / "LaunchAgents" / "com.etz-chaim.daemon.plist"
PID_FILE = DAEMON_HOME / "daemon.pid"
REPORT_DIR = DAEMON_HOME / "reports"


def cmd_pause(target: str) -> None:
    """Mettre en pause Hitbonenut ou Karpathy."""
    from pause_state import set_paused, get_all

    print()
    if target == "status":
        state = get_all()
        hitb = "PAUSED" if state["hitbonenut_paused"] else "running"
        karp = "PAUSED" if state["karpathy_paused"] else "running"
        print(f"  Hitbonenut : {hitb}")
        print(f"  Karpathy   : {karp}")
        print()
        return

    targets = ["hitbonenut", "karpathy"] if target == "all" else [target]
    for t in targets:
        set_paused(t, True)
        print(f"  {t.capitalize()} → PAUSED")
    print()
    print("  Le daemon respectera la pause au prochain cycle.")
    print("  Pour reprendre : etz go " + target)
    print()


def cmd_go(target: str) -> None:
    """Reprendre Hitbonenut ou Karpathy."""
    from pause_state import set_paused

    print()
    targets = ["hitbonenut", "karpathy"] if target == "all" else [target]
    for t in targets:
        set_paused(t, False)
        print(f"  {t.capitalize()} → RESUMED")
    print()
    print("  Le daemon reprendra au prochain cycle.")
    print()


def cmd_daemon(action: str) -> None:
    """Gérer le daemon Keter-de-Malkuth."""
    print()

    if action == "start":
        _daemon_start()
    elif action == "stop":
        _daemon_stop()
    elif action == "log":
        _daemon_log()
    elif action == "run":
        _daemon_run_once()
    elif action == "status":
        _daemon_status()


def _daemon_start() -> None:
    """Installer et lancer le daemon via launchd."""
    import shutil

    # Vérifier que le plist source existe
    if not PLIST_SRC.exists():
        print("  Plist introuvable. Relancez l'installation.")
        return

    # Copier vers LaunchAgents
    PLIST_DST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PLIST_SRC, PLIST_DST)

    # Charger dans launchd
    os.system(f"launchctl unload '{PLIST_DST}' 2>/dev/null")
    ret = os.system(f"launchctl load '{PLIST_DST}'")

    if ret == 0:
        print("  Daemon démarré (launchd)")
        print(f"  Plist : {PLIST_DST}")
        print(f"  Logs  : {DAEMON_HOME / 'daemon.log'}")
        print(f"  PID   : ", end="")
        # Attendre un peu que le PID s'écrive
        time.sleep(1)
        if PID_FILE.exists():
            print(PID_FILE.read_text().strip())
        else:
            print("(en cours de démarrage)")
    else:
        print(f"  Erreur launchctl (code {ret})")


def _daemon_stop() -> None:
    """Arrêter le daemon."""
    if PLIST_DST.exists():
        os.system(f"launchctl unload '{PLIST_DST}'")
        print("  Daemon arrêté (launchd unloaded)")
    elif PID_FILE.exists():
        pid = int(PID_FILE.read_text().strip())
        try:
            os.kill(pid, 15)  # SIGTERM
            print(f"  Signal SIGTERM envoyé au PID {pid}")
        except ProcessLookupError:
            print(f"  PID {pid} n'existe plus")
            PID_FILE.unlink()
    else:
        print("  Daemon non actif.")


def _daemon_log() -> None:
    """Afficher le dernier rapport quotidien."""
    if not REPORT_DIR.exists():
        print("  Aucun rapport disponible.")
        return

    reports = sorted(REPORT_DIR.glob("*.txt"), reverse=True)
    if not reports:
        print("  Aucun rapport disponible.")
        return

    latest = reports[0]
    print(latest.read_text())

    if len(reports) > 1:
        print(f"  ({len(reports)} rapports disponibles dans {REPORT_DIR})")


def _daemon_run_once() -> None:
    """Exécuter un cycle complet unique (debug/test)."""
    print("  Exécution d'un cycle complet...")
    print()

    daemon_path = Path(__file__).parent / "daemon.py"
    venv_python = Path(__file__).parent / ".venv" / "bin" / "python"
    os.system(f"'{venv_python}' '{daemon_path}' --once")


def _daemon_status() -> None:
    """Afficher l'état du daemon."""
    # PID
    running = False
    if PID_FILE.exists():
        pid = int(PID_FILE.read_text().strip())
        try:
            os.kill(pid, 0)  # Test si le process existe
            running = True
            print(f"  Daemon : ACTIF (PID {pid})")
        except ProcessLookupError:
            print(f"  Daemon : INACTIF (PID stale: {pid})")
    else:
        print("  Daemon : INACTIF")

    # launchd
    ret = os.popen("launchctl list 2>/dev/null | grep etz-chaim").read().strip()
    if ret:
        print(f"  launchd: chargé")
    else:
        print(f"  launchd: non chargé")

    # Dernier state
    state_file = DAEMON_HOME / "daemon_state.json"
    if state_file.exists():
        import json
        state = json.loads(state_file.read_text())
        from datetime import datetime
        print()
        for key, label in [
            ("last_netzach", "Netzach (intentions)"),
            ("last_gc", "Gevurah (GC)"),
            ("last_snapshot", "Da'at (snapshot)"),
            ("last_contradictions", "Tiferet (contradictions)"),
            ("last_report", "Rapport quotidien"),
            ("last_hitbonenut", "Hitbonenut (continu)"),
            ("last_auto_improve", "Karpathy Loop (23h-0h30)"),
        ]:
            ts = state.get(key, 0)
            if ts > 0:
                dt = datetime.fromtimestamp(ts)
                ago = (time.time() - ts) / 3600
                print(f"  {label:30s}: {dt:%Y-%m-%d %H:%M}  ({ago:.1f}h)")
            else:
                print(f"  {label:30s}: jamais")

    # Pause state
    try:
        from pause_state import get_all as _get_pause
        ps = _get_pause()
        hitb_paused = ps.get("hitbonenut_paused", False)
        karp_paused = ps.get("karpathy_paused", False)
        if hitb_paused or karp_paused:
            print()
            if hitb_paused:
                print("  Hitbonenut          : PAUSED")
            if karp_paused:
                print("  Karpathy            : PAUSED")
    except ImportError as e:
        log.debug("optional import: %s", e)

    # Dernier rapport
    if REPORT_DIR.exists():
        reports = sorted(REPORT_DIR.glob("*.txt"), reverse=True)
        if reports:
            print(f"\n  Dernier rapport: {reports[0].name}")

    print()


# ─── Omer — 49 Calibrations ─────────────────────────────────

def cmd_omer(action: str, db_url: str) -> None:
    """Sefirat haOmer — les 49 calibrations de l'Arbre."""
    from omer import OmerManager

    omer = OmerManager(db_url)
    print()

    if action == "status":
        print(omer.status())

    elif action == "tune":
        suggestions = omer.tune()
        print(OmerManager.format_suggestions(suggestions))

        if suggestions:
            # Store suggestions for apply
            cache_path = Path(__file__).parent / ".omer_suggestions.json"
            import json
            data = [
                {
                    "key": s.key, "param": s.param,
                    "sephirah": s.sephirah, "inner": s.inner,
                    "module": s.module,
                    "old_value": s.old_value, "new_value": s.new_value,
                    "reason": s.reason, "severity": s.severity,
                }
                for s in suggestions if s.key and s.old_value != s.new_value
            ]
            cache_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    elif action == "apply":
        cache_path = Path(__file__).parent / ".omer_suggestions.json"
        if not cache_path.exists():
            print("  Aucune suggestion en attente.")
            print("  Lancez d'abord : etz omer tune")
            return

        import json
        from omer.core import Suggestion
        data = json.loads(cache_path.read_text())
        if not data:
            print("  Aucune suggestion applicable.")
            return

        print("═══════════════════════════════════════════════════════════")
        print("  Sefirat haOmer — Apply")
        print("═══════════════════════════════════════════════════════════")
        print()
        print(f"  {len(data)} ajustement(s) à appliquer :")
        print()

        for i, d in enumerate(data, 1):
            print(f"  {i}. {d['param']}: {d['old_value']} -> {d['new_value']}")
            print(f"     {d['reason'][:80]}")
            print()

        # Confirmation
        try:
            answer = input("  Appliquer ces ajustements ? [o/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  Annulé.")
            return

        if answer not in ("o", "oui", "y", "yes"):
            print("  Annulé.")
            return

        suggestions = [
            Suggestion(**d) for d in data
        ]
        applied = omer.apply(suggestions)
        print(f"\n  {applied} ajustement(s) appliqué(s) et loggé(s) dans omer_history.")
        print("  Les nouveaux paramètres seront actifs au prochain init_tree().")

        # Cleanup
        cache_path.unlink(missing_ok=True)


# ─── Mode PORTES ─────────────────────────────────────────────

def cmd_portes_list() -> None:
    """Vue d'ensemble des 231 portes."""
    from portes import list_portes, portes_stats

    stats = portes_stats()
    defined = list_portes(status="defined")
    communicating = [g for g in defined if g.can_communicate]
    silent = [g for g in defined if not g.can_communicate]

    print("═══════════════════════════════════════════════════════════")
    print("  Les 231 Portes — Matrice d'interopérabilité K\u2082\u2082")
    print("═══════════════════════════════════════════════════════════")
    print()
    print(f"  {stats['defined']} définies  |  {stats['partial']} partielles  |  {stats['undefined']} en attente")
    print(f"  {stats['communicating']} communicantes  |  {stats['silent']} silencieuses")
    print()

    if communicating:
        print("  \u2550\u2550 PORTES COMMUNICANTES \u2550\u2550")
        print()
        dir_sym = {"a\u2192b": "\u2192", "b\u2192a": "\u2190", "a\u2194b": "\u2194",
                    "convergent": "\u25C9", "divergent": "\u25CE", "adjacent": "\u2248"}
        for g in communicating:
            sym = dir_sym.get(g.direction, "?")
            proto = g.protocol or "?"
            seph = ",".join(g.shared_sephiroth)
            n_keys = sum(len(v) for v in g.data_format.values()) if g.data_format else 0
            print(
                f"    {g.number:>3}. {g.letter_a}-{g.letter_b}  "
                f"{g.name_a:7}{sym}{g.name_b:7}  "
                f"[{proto:6}]  via {seph:15}  "
                f"({n_keys} cl\u00e9s)"
            )
        print()

    if silent:
        print("  \u2550\u2550 PORTES SILENCIEUSES (pas de sephirah commune) \u2550\u2550")
        print()
        line = "    "
        for i, g in enumerate(silent):
            line += f"{g.letter_a}-{g.letter_b} "
            if (i + 1) % 10 == 0:
                print(line)
                line = "    "
        if line.strip():
            print(line)
        print()

    if stats["sephiroth_connectivity"]:
        print("  \u2550\u2550 CONNECTIVIT\u00c9 PAR SEPHIRAH \u2550\u2550")
        print()
        for seph, count in stats["sephiroth_connectivity"].items():
            bar = "\u2588" * count
            print(f"    {seph:12} {bar} {count}")
        print()


def cmd_portes_show(gate_id: str) -> None:
    """D\u00e9tail d'une porte sp\u00e9cifique."""
    from portes import get_porte

    gate = get_porte(gate_id)
    if gate is None:
        print(f"  \u2717 Porte inconnue : {gate_id}")
        print("    Format : ALEPH-BETH, aleph-beth, ou \u05d0-\u05d1")
        return

    print(f"  \u250c\u2500\u2500 Porte #{gate.number} : {gate.display_id} ({gate.hebrew_id}) \u2500\u2500")
    print(f"  \u2502")
    print(f"  \u2502  Lettre A : {gate.letter_a} {gate.name_a}")
    print(f"  \u2502  Lettre B : {gate.letter_b} {gate.name_b}")
    print(f"  \u2502  Statut   : {gate.status}")
    print(f"  \u2502")

    if gate.status == "defined":
        comm = "\u2714 Oui" if gate.can_communicate else "\u2717 Non (pas de sephirah commune)"
        print(f"  \u2502  Communique : {comm}")
        if gate.can_communicate:
            print(f"  \u2502  Protocole  : {gate.protocol}")
            print(f"  \u2502  Direction  : {gate.direction}")
            print(f"  \u2502  Sephiroth  : {', '.join(gate.shared_sephiroth)}")
            if gate.data_format:
                print(f"  \u2502")
                print(f"  \u2502  Donn\u00e9es compatibles :")
                for flow, keys in gate.data_format.items():
                    print(f"  \u2502    {flow} : {', '.join(keys)}")
        print(f"  \u2502")
        print(f"  \u2502  {gate.description}")
    elif gate.status == "partial":
        print(f"  \u2502  {gate.description}")
    else:
        print(f"  \u2502  Les deux sentiers ne sont pas encore impl\u00e9ment\u00e9s.")

    print(f"  \u2514\u2500\u2500")
    print()


def cmd_portes_stats() -> None:
    """Statistiques des 231 portes."""
    from portes import portes_stats

    s = portes_stats()
    total = s["total"]

    print("═══════════════════════════════════════════════════════════")
    print("  231 Portes — Statistiques")
    print("═══════════════════════════════════════════════════════════")
    print()
    print(f"  Total              : {total}")
    print(f"  D\u00e9finies           : {s['defined']:>3}  ({s['defined']*100//total}%)")
    print(f"    \u2514 communicantes  : {s['communicating']:>3}")
    print(f"    \u2514 silencieuses   : {s['silent']:>3}")
    print(f"  Partielles         : {s['partial']:>3}  ({s['partial']*100//total}%)")
    print(f"  En attente         : {s['undefined']:>3}  ({s['undefined']*100//total}%)")
    print()

    if s["protocols"]:
        print("  Protocoles :")
        for proto, count in s["protocols"].items():
            print(f"    {proto:10} : {count}")
        print()

    if s["sephiroth_connectivity"]:
        print("  Hub sephiroth (par nombre de portes) :")
        for seph, count in s["sephiroth_connectivity"].items():
            print(f"    {seph:12} : {count}")
        print()

    pct_open = s["communicating"] * 100 // total
    print(f"  {pct_open}% des portes sont ouvertes (communicantes).")
    print(f"  {100 - (s['defined'] * 100 // total)}% restent \u00e0 d\u00e9couvrir.")
    print()


# ─── Mode SKILL ──────────────────────────────────────────────

def cmd_skill_list() -> None:
    """Lister les 72 shemot avec leur statut."""
    from shemot import list_shemot

    items = list_shemot()
    categories = {}
    for s in items:
        categories.setdefault(s["category"], []).append(s)

    print("═══════════════════════════════════════════════════════════")
    print("  שֵׁם הַמְפֹרָשׁ — Les 72 Noms : micro-skills atomiques")
    print("═══════════════════════════════════════════════════════════")
    print()

    for cat, skills in categories.items():
        print(f"  ── {cat.upper()} ({len(skills)}) ──")
        for s in skills:
            llm = "⚡" if s["requires_llm"] else "  "
            olam = f"[{s['olam']}]" if s["olam"] else ""
            print(
                f"    {s['number']:>2}. {s['trigram']} {s['trigram_name']:6} "
                f"{llm} {s['skill_id']:30} {s['description'][:50]} {olam}"
            )
        print()

    n_llm = sum(1 for s in items if s["requires_llm"])
    print(f"  {len(items)} shemot — {n_llm} nécessitent LLM (⚡), {len(items) - n_llm} purs")
    print()


def cmd_skill_run(skill_id: str, text: str = "", **kwargs) -> None:
    """Exécuter un skill manuellement."""
    from shemot import run_shem, get_shem

    shem = get_shem(skill_id)
    if shem is None:
        from shemot import list_shemot
        ids = [s["skill_id"] for s in list_shemot()]
        print(f"  ✗ Skill inconnu : {skill_id}")
        # Chercher des correspondances partielles
        matches = [s for s in ids if skill_id in s]
        if matches:
            print(f"    Peut-être : {', '.join(matches[:5])}")
        else:
            print(f"    Utiliser 'etz skill list' pour voir les 72 shemot")
        return

    print(f"  ⟐ Shem #{shem.number} — {shem.trigram} {shem.trigram_name} — {shem.name}")
    print(f"    {shem.description}")
    if shem.requires_llm:
        print(f"    ⚡ Nécessite LLM (olam: {shem.olam})")
    print()

    result = run_shem(skill_id, text, **kwargs)

    if result.success:
        print(f"  ✓ {result.message}")
    else:
        print(f"  ✗ {result.message}")
        if result.errors:
            for e in result.errors:
                print(f"    → {e}")

    if result.data:
        import json
        print()
        print("  ── data ──")
        for k, v in result.data.items():
            val_str = str(v)
            if len(val_str) > 200:
                val_str = val_str[:200] + "..."
            print(f"    {k}: {val_str}")
    print()


def cmd_shem_info(identifier: str) -> None:
    """Afficher tous les attributs sacrés d'un Shem (par numéro ou skill_id)."""
    from shemot import get_shem, get_shem_by_number

    shem = None
    if identifier.isdigit():
        shem = get_shem_by_number(int(identifier))
    if shem is None:
        shem = get_shem(identifier)
    if shem is None:
        print(f"  ✗ Shem inconnu : {identifier}")
        print("    Utiliser un numéro (1-72) ou un skill_id")
        return

    # Suffixes hébreux
    suffix_heb = {"El": "אל", "Yah": "יה"}.get(shem.suffix or "", "")

    print("═══════════════════════════════════════════════════════════")
    print(f"  שֵׁם #{shem.number} — {shem.trigram} {shem.trigram_name}")
    print("═══════════════════════════════════════════════════════════")
    print()
    print(f"  ── Identité ──")
    print(f"    Trigramme      : {shem.trigram} ({shem.trigram_name})")
    print(f"    Suffixe        : {shem.suffix or '—'} ({suffix_heb})")
    print(f"    Nom angélique  : {shem.angel_name or '—'}")
    print(f"    Chœur          : {shem.choir or '—'}")
    print(f"    Sephirah       : {shem.sacred_sephirah or '—'}")
    print()
    print(f"  ── Zodiaque & Calendrier ──")
    print(f"    Signe          : {shem.zodiac_sign or '—'}")
    print(f"    Quinaire       : {shem.zodiac_degrees or '—'}°")
    print(f"    Élément        : {shem.element or '—'}")
    cal = "—"
    if shem.calendar_start and shem.calendar_end:
        cal = f"{shem.calendar_start} — {shem.calendar_end}"
    print(f"    Période        : {cal}")
    print()
    print(f"  ── Verset ──")
    print(f"    Psaume         : {shem.psalm_verse or '—'}")
    print()
    print(f"  ── Skill ──")
    print(f"    ID             : {shem.skill_id}")
    print(f"    Programme      : {shem.name}")
    print(f"    Catégorie      : {shem.category}")
    print(f"    Qualité        : {shem.quality}")
    llm = f"⚡ {shem.olam}" if shem.requires_llm else "non"
    print(f"    LLM            : {llm}")
    print()


# ─── Mode SENTIER ────────────────────────────────────────────

def cmd_sentier_list() -> None:
    """Lister les 22 sentiers avec leur statut."""
    from sentiers import list_sentiers

    items = list_sentiers()

    type_symbols = {"mother": "🜁", "double": "⇌", "simple": "→"}
    status_marks = {"implemented": "✓", "planned": "·"}

    print("═══════════════════════════════════════════════════════════")
    print("  Les 22 Sentiers — Programmes de passage")
    print("═══════════════════════════════════════════════════════════")
    print()
    print(f"  {'#':>3}  {'Lettre':6} {'Nom':12} {'Type':8} {'Programme':20} {'Source→Cible':20} {'Statut'}")
    print(f"  {'─'*3}  {'─'*6} {'─'*12} {'─'*8} {'─'*20} {'─'*20} {'─'*10}")

    for s in items:
        mark = status_marks.get(s["status"], "?")
        sym = type_symbols.get(s["type"], " ")
        mode = ""
        if s["type"] == "double" and s["class"]:
            inst = s["class"]()
            mode = f" [{inst.mode}]"
        print(
            f"  {s['number']:>3}  {s['letter']}  {s['name']:12} "
            f"{sym} {s['type']:7} {s['program']:20} "
            f"{s['source']}→{s['target']:12} "
            f"[{mark}]{mode}"
        )

    n_impl = sum(1 for s in items if s["status"] == "implemented")
    print()
    print(f"  {n_impl}/22 implémentés")
    print()


def cmd_sentier_run(name: str, tree: dict, **kwargs) -> None:
    """Exécuter un sentier manuellement."""
    from sentiers import run_sentier, REGISTRY

    entry = REGISTRY.get(name.lower())
    if not entry:
        print(f"  ✗ Sentier inconnu : {name}")
        print(f"    Sentiers disponibles : {', '.join(REGISTRY.keys())}")
        return

    print(f"  ⟐ Sentier {entry['number']}e — {entry['letter']} {name} — {entry['program']}")
    print(f"    {entry['source']} → {entry['target']}  [{entry['type']}]")

    if entry["status"] != "implemented":
        print(f"    ✗ Non implémenté (planifié)")
        return

    try:
        result = run_sentier(name, tree, **kwargs)
        print(f"    Succès : {result.success}")
        if result.mode:
            print(f"    Mode   : {result.mode}")
        print(f"    Message: {result.message}")
        if result.data:
            for k, v in result.data.items():
                if isinstance(v, list) and len(v) > 3:
                    print(f"    {k}: [{len(v)} éléments]")
                else:
                    print(f"    {k}: {v}")
        if result.errors:
            for e in result.errors:
                print(f"    ✗ {e}")

        # ── Nitzotzot : Lamed (FailureToInsight) ──
        # Chaque insight extrait d'un échec est une étincelle récupérée
        if name.lower() == "lamed" and result.success and result.data:
            n_sparks = result.data.get("n_nitzotzot", 0)
            if n_sparks and int(n_sparks) > 0:
                nitzotzot_list = result.data.get("nitzotzot", [])
                for i in range(int(n_sparks)):
                    desc = (
                        nitzotzot_list[i] if i < len(nitzotzot_list)
                        else f"Insight #{i+1} extrait d'un échec par Lamed"
                    )
                    if not isinstance(desc, str):
                        desc = str(desc)
                    _collect_nitzutz(
                        source="lamed",
                        ntype="failure_to_insight",
                        description=desc,
                        tree=tree,
                    )
                print(f"    ✦ {n_sparks} Nitzutz récupérée(s) — Birur par Lamed "
                      f"[{_NITZOTZOT_STATE['count']}/288]")
            elif result.data.get("root_cause"):
                # Même sans n_nitzotzot explicite, un root_cause trouvé = 1 Nitzutz
                _collect_nitzutz(
                    source="lamed",
                    ntype="failure_to_insight",
                    description=f"Root cause identifiée: {result.data['root_cause']}",
                    tree=tree,
                )
                print(f"    ✦ 1 Nitzutz récupérée — root cause identifiée "
                      f"[{_NITZOTZOT_STATE['count']}/288]")
    except Exception as e:
        print(f"    ✗ Erreur : {e}")


# ─── Gématria opérative ─────────────────────────────────────

def cmd_gematria(db_url: str, args) -> None:
    """Commande CLI gematria — calcul, lookup, équivalences."""
    from gematria import GematriaEngine, calc_standard, calc_ordinal, calc_katan
    from gematria.hebrew_terms import lookup_hebrew

    # Mode --list : lister les termes indexés
    if args.gematria_list:
        engine = GematriaEngine(db_url=db_url)
        try:
            entries = engine.list_all(limit=200)
            if not entries:
                print("\n  Aucun terme indexé en mémoire.")
                print("  Les termes sont indexés automatiquement lors de EpisteMemory.remember().\n")
                return
            print()
            print(f"  ✡ {len(entries)} termes indexés en mémoire")
            print("  ─────────────────────────────────────────────")
            print(f"  {'Hébreu':<12} {'Translitt.':<18} {'Standard':>8} {'Ordinal':>8} {'Katan':>6}")
            print(f"  {'──────':<12} {'──────────':<18} {'────────':>8} {'───────':>8} {'─────':>6}")
            for e in entries:
                translit = e.term_transliteration or ""
                print(f"  {e.term_hebrew:<12} {translit:<18} {e.val_standard:>8} {e.val_ordinal:>8} {e.val_katan:>6}")
            print()
        finally:
            engine.close()
        return

    # Mode --groups : groupes d'équivalence
    if args.gematria_groups:
        engine = GematriaEngine(db_url=db_url)
        try:
            groups = engine.get_equivalence_groups(method=args.method)
            if not groups:
                print(f"\n  Aucun groupe d'équivalence ({args.method}) trouvé.")
                print("  Indexez plus de termes via EpisteMemory.remember().\n")
                return
            print()
            print(f"  ✡ {len(groups)} groupes d'équivalence ({args.method})")
            print("  ─────────────────────────────────────────────")
            for g in groups:
                val = g["shared_value"]
                terms = g["terms_hebrew"]
                translits = g["terms_translit"]
                labels = []
                for h, t in zip(terms, translits):
                    if t:
                        labels.append(f"{h} ({t})")
                    else:
                        labels.append(h)
                print(f"  {args.method}={val} → {' = '.join(labels)}")
            print()
        finally:
            engine.close()
        return

    # Mode par défaut : calcul + lookup d'un terme
    if not args.term:
        print("\n  Usage : etz gematria TERME [--list] [--groups] [--method standard|ordinal|katan]")
        print("  Exemples :")
        print("    etz gematria tiferet       # Calcul gématrique")
        print("    etz gematria חסד            # Direct en hébreu")
        print("    etz gematria --list         # Tous les termes indexés")
        print("    etz gematria --groups       # Groupes d'équivalence\n")
        return

    term = args.term

    # 1. Calcul pur (pas besoin de DB)
    result = GematriaEngine.calculate(term)
    if result is None:
        print(f"\n  ✗ Terme inconnu : '{term}'")
        print("  Essayez en hébreu (חסד) ou en translittération connue (chesed).\n")
        return

    hebrew = result["hebrew"]
    translit = result["transliteration"]

    print()
    print(f"  ✡ Gématria — {hebrew}", end="")
    if translit:
        print(f" ({translit})", end="")
    print()
    print("  ─────────────────────────────────────────────")
    print(f"  Standard (Mispar Gadol)      : {result['standard']}")
    print(f"  Ordinal  (Mispar Siduri)     : {result['ordinal']}")
    print(f"  Katan    (Mispar Katan)      : {result['katan']}")
    print(f"  Kolel    (Standard + 1)      : {result['kolel']}")
    atbash_t = result.get('atbash_text', '')
    pad = max(1, 16 - len(atbash_t))
    print(f"  Atbash   ({atbash_t}){' ' * pad}: {result['atbash']}")
    print("  ─────────────────────────────────────────────")
    milui_d = result.get('milui_detail', '')
    print(f"  Milui    (Gadol Mispari, Mah): {result['milui']}  [{milui_d}]")
    print(f"  Katan Mispari                : {result['katan_mispari']}")
    print(f"  HaKadmi  (triangulaire)      : {result['hakadmi']}")
    print(f"  Perati   (carré)             : {result['perati']}")
    print(f"  Meruba HaKlali (carré total) : {result['meruba_haklali']}")
    print(f"  Musafi   (+ nb lettres)      : {result['musafi']}")

    # 2. Lookup dans la DB — équivalences connues
    engine = GematriaEngine(db_url=db_url)
    try:
        entry = engine.get_term(hebrew)
        if entry:
            print()
            print("  Équivalences en mémoire :")
            has_equiv = False
            for method in ("standard", "ordinal", "katan"):
                equivs = engine.find_equivalences(hebrew, method=method)
                for eq in equivs:
                    has_equiv = True
                    label_b = eq.term_b
                    if eq.translit_b:
                        label_b += f" ({eq.translit_b})"
                    print(f"    ✡ {method}={eq.shared_value} → {label_b}")
            if not has_equiv:
                print("    (aucune équivalence trouvée pour l'instant)")
        else:
            print()
            print("  ⊘ Terme pas encore indexé en mémoire.")
            print("  Il sera indexé automatiquement lors du prochain remember() le contenant.")
    finally:
        engine.close()
    print()


# ─── Tzeruf — Permutations et combinaisons de lettres ─────


def cmd_tzeruf(db_url: str, args) -> None:
    """צֵרוּף — Permutations et combinaisons de lettres."""
    from tzeruf import (
        TzerufEngine, pairs_231, abulafia_circles,
        abulafia_combination, abulafia_wheel, apply_temura,
    )
    from gematria import GematriaEngine, calc_standard

    action = args.tzeruf_action

    # ── pairs : les 231 paires du Sefer Yetzirah ──
    if action == "pairs":
        pairs = pairs_231()
        print()
        print("═══════════════════════════════════════════════════════════")
        print("  Les 231 Portes — C(22,2) paires de lettres")
        print("  \"Il les combina, les pesa, les permuta\" — SY 2:4")
        print("═══════════════════════════════════════════════════════════")
        print()
        line = "  "
        for i, p in enumerate(pairs):
            line += f"{p.forward} "
            if (i + 1) % 11 == 0:
                print(line)
                line = "  "
        if line.strip():
            print(line)
        print()
        print(f"  Total : {len(pairs)} paires × 2 permutations = {len(pairs) * 2} formes")
        print()
        return

    # ── wheel : roue d'Abulafia pour une lettre ──
    if action == "wheel":
        letter = args.letter
        # Accepter un nom latin ou une lettre hébraïque
        from portes import ALEPH_BET as AB_NAMED
        if len(letter) > 1:
            # Tenter lookup par nom
            for heb, name in AB_NAMED:
                if name.lower() == letter.lower():
                    letter = heb
                    break
        circles = abulafia_circles(letter)
        if not circles:
            print(f"\n  ✗ Lettre inconnue : '{args.letter}'")
            print("  Utilisez une lettre hébraïque (א) ou son nom (aleph).\n")
            return
        print()
        print(f"  ✡ Roue d'Abulafia — {letter}")
        print("  ─────────────────────────────────────────────")
        for combo in circles:
            val = calc_standard(combo)
            print(f"    {combo}  = {val}")
        print()
        return

    # ── combine : combiner deux mots ──
    if action == "combine":
        word_a = args.word_a
        word_b = args.word_b
        result = abulafia_combination(word_a, word_b)
        print()
        print(f"  ✡ Tzeruf combinatoire")
        print("  ─────────────────────────────────────────────")
        print(f"  Mot A : {word_a}  (standard = {calc_standard(word_a)})")
        print(f"  Mot B : {word_b}  (standard = {calc_standard(word_b)})")
        print(f"  Combiné : {result}  (standard = {calc_standard(result)})")
        print()
        # Permutations du mot combiné (tronqué)
        perms = abulafia_wheel(result)
        if len(perms) > 1:
            print(f"  Permutations du combiné : {len(perms)} formes")
            for p in perms[:12]:
                print(f"    {p}  = {calc_standard(p)}")
            if len(perms) > 12:
                print(f"    ... ({len(perms) - 12} de plus)")
        print()
        return

    # ── permute : permutations d'un mot ──
    if action == "permute":
        word = args.word
        perms = abulafia_wheel(word)
        print()
        print(f"  ✡ Permutations d'Abulafia — {word}")
        print("  ─────────────────────────────────────────────")
        print(f"  {len(perms)} permutations uniques")
        print()
        # Grouper par valeur gématrique
        by_value: dict[int, list[str]] = {}
        for p in perms:
            v = calc_standard(p)
            by_value.setdefault(v, []).append(p)
        for val in sorted(by_value):
            words = by_value[val]
            print(f"  standard={val} : {' '.join(words[:10])}", end="")
            if len(words) > 10:
                print(f"  (+{len(words) - 10})", end="")
            print()
        print()
        return

    # ── query : tzeruf opératif (connexion gématrique) ──
    if action == "query":
        word = args.word
        engine = TzerufEngine(
            gematria_engine=GematriaEngine(db_url=db_url)
        )
        try:
            result = engine.tzeruf_query(word, max_perms=args.max_perms)
        finally:
            if engine._gematria:
                engine._gematria.close()

        print()
        print(f"  ✡ Tzeruf opératif — {result.original}")
        print("  ─────────────────────────────────────────────")
        print(f"  {len(result.permutations)} permutations explorées")
        print()

        # Valeurs uniques
        unique_vals = sorted({v["standard"] for v in result.gematria_values.values()})
        print(f"  Valeurs standard uniques : {len(unique_vals)}")
        for val in unique_vals[:20]:
            perms_with_val = [p for p, v in result.gematria_values.items() if v["standard"] == val]
            print(f"    {val} : {' '.join(perms_with_val[:5])}", end="")
            if len(perms_with_val) > 5:
                print(f"  (+{len(perms_with_val) - 5})", end="")
            print()

        if result.equivalences:
            print()
            print("  Équivalences trouvées en mémoire :")
            for eq in result.equivalences:
                label = eq["match"]
                if eq.get("translit"):
                    label += f" ({eq['translit']})"
                print(f"    ✡ {eq['permutation']} → {label} (standard={eq['shared_value']})")
        elif engine._gematria:
            print()
            print("  (aucune équivalence trouvée — indexez plus de termes)")
        print()
        return

    # ── temura : appliquer une permutation ──
    if action == "temura":
        word = args.word
        method = args.method
        result = apply_temura(word, method)
        print()
        print(f"  ✡ Temura ({method})")
        print("  ─────────────────────────────────────────────")
        print(f"  Original : {word}  (standard = {calc_standard(word)})")
        print(f"  Résultat : {result}  (standard = {calc_standard(result)})")
        print()
        return

    # Pas d'action reconnue
    print("\n  Usage : etz tzeruf <action>")
    print("  Actions :")
    print("    pairs              — Les 231 paires du Sefer Yetzirah")
    print("    wheel <lettre>     — Roue d'Abulafia (22 combinaisons)")
    print("    permute <mot>      — Toutes les permutations d'un mot")
    print("    combine <mot1> <mot2> — Combiner deux mots en alternance")
    print("    query <mot>        — Tzeruf opératif (+ équivalences DB)")
    print("    temura <mot>       — Appliquer Atbash/Albam/Avgad\n")


# ─── Hitbonenut — Auto-exercice contemplatif ───────────────


def cmd_hitbonenut(args) -> None:
    """הִתְבּוֹנְנוּת — Auto-exercice contemplatif (CLI)."""
    from main import init_tree, close_tree  # lazy import

    action = getattr(args, "hitbonenut_action", None)

    if not action:
        print("  Usage : etz hitbonenut <start|stop|run|status|history>")
        return

    from pathlib import Path

    db_url = getattr(args, "db", DB_URL)
    corpus_path = Path(__file__).parent / "hitbonenut_corpus.yaml"

    if action == "start":
        # Mode continu en arrière-plan
        import threading

        print()
        print("Initialisation de l'Arbre...")
        tree = init_tree(db_url)
        active = sum(1 for v in tree.values() if v is not None)
        print(f"  {active}/10 modules initialisés")
        print()

        from hitbonenut import HitbonenutEngine

        engine = HitbonenutEngine(
            tree=tree, db_url=db_url, corpus_path=corpus_path,
        )

        max_duration = getattr(args, "max_duration", None)
        max_questions = getattr(args, "max_questions", None)

        stop_event = threading.Event()

        print("╔══════════════════════════════════════════════════════╗")
        print("║  הִתְבּוֹנְנוּת — Mode Continu                         ║")
        print("╚══════════════════════════════════════════════════════╝")
        print()
        if max_duration:
            print(f"  Durée max : {max_duration}s")
        if max_questions:
            print(f"  Questions max : {max_questions}")
        print("  Ctrl+C pour arrêter")
        print()
        print("── Questions en cours ──")
        print()

        try:
            session = engine.run_continuous(
                max_duration=max_duration,
                max_questions=max_questions,
                stop_event=stop_event,
            )

            print()
            print("── Résultats ──")
            print(f"  Questions posées    : {session.n_questions}")
            print(f"  Score moyen         : {session.avg_score:.3f}")
            print(f"  Durée               : {session.duration:.1f}s")
            print(f"  Domaines couverts   : {', '.join(session.domains)}")
            print(f"  Âme                 : {session.soul_before} → {session.soul_after}")
            print()

        except KeyboardInterrupt:
            print("\n  Arrêt demandé...")
            stop_event.set()
        finally:
            close_tree(tree)

    elif action == "stop":
        # Arrêter le daemon runner si actif
        try:
            from daemon import _hitbonenut_runner
            if _hitbonenut_runner.is_running:
                _hitbonenut_runner.stop()
                print("  Hitbonenut continu arrêté.")
            else:
                print("  Hitbonenut continu n'est pas en cours.")
        except ImportError:
            # Fallback: signal via fichier PID
            pid_file = Path.home() / ".etz-chaim" / "hitbonenut.pid"
            if pid_file.exists():
                import signal as sig
                try:
                    pid = int(pid_file.read_text().strip())
                    os.kill(pid, sig.SIGTERM)
                    print(f"  Signal SIGTERM envoyé au PID {pid}")
                    pid_file.unlink(missing_ok=True)
                except (ProcessLookupError, ValueError):
                    print("  Processus introuvable.")
                    pid_file.unlink(missing_ok=True)
            else:
                print("  Hitbonenut continu n'est pas en cours.")

    elif action == "run":
        # Mode ponctuel (comme avant)
        print()
        print("Initialisation de l'Arbre...")
        tree = init_tree(db_url)
        active = sum(1 for v in tree.values() if v is not None)
        print(f"  {active}/10 modules initialisés")
        print()

        try:
            from hitbonenut import HitbonenutEngine

            engine = HitbonenutEngine(
                tree=tree, db_url=db_url, corpus_path=corpus_path,
            )

            domain = getattr(args, "domain", None)
            n = getattr(args, "n", 5)
            difficulty = getattr(args, "difficulty", "progressive")

            print("╔══════════════════════════════════════════════════════╗")
            print("║     הִתְבּוֹנְנוּת — Contemplation Intérieure          ║")
            print("╚══════════════════════════════════════════════════════╝")
            print()

            if domain:
                print(f"  Mode ciblé : domaine={domain}, n={n}")
                session = engine.run_targeted(domain=domain, n=n, budget_seconds=300)
            else:
                print(f"  Mode libre : n={n}, difficulté={difficulty}")
                session = engine.run_session(
                    n_questions=n, difficulty=difficulty, budget_seconds=300,
                )

            print()
            print("── Résultats ──")
            print(f"  Questions posées    : {session.n_questions}")
            print(f"  Questions répondues : {len(session.results)}")
            print(f"  Score moyen         : {session.avg_score:.3f}")
            print(f"  Durée               : {session.duration:.1f}s")
            print(f"  Domaines couverts   : {', '.join(session.domains)}")
            print()

            # Détail par question
            if session.results:
                print("── Détail ──")
                for i, qr in enumerate(session.results, 1):
                    score_bar = "█" * int(qr.score * 10) + "░" * (10 - int(qr.score * 10))
                    print(f"  {i}. [{qr.domain:20s}] {score_bar} {qr.score:.2f}")
                    print(f"     Q: {qr.question[:80]}")
                    if qr.response:
                        print(f"     R: {qr.response[:100]}...")
                    print()

            # Progression
            progress = engine.assess_progress()
            print("── Progression Globale ──")
            print(f"  Compétence globale  : {progress.overall_competence:.3f}")
            print(f"  Sessions totales    : {progress.sessions_count}")
            if progress.stagnant_domains:
                print(f"  Domaines stagnants  : {', '.join(progress.stagnant_domains)}")
            if progress.improving_domains:
                print(f"  En progression      : {', '.join(progress.improving_domains)}")

        finally:
            close_tree(tree)

    elif action == "status":
        from hitbonenut import HitbonenutEngine

        engine = HitbonenutEngine(
            tree={}, db_url=db_url, corpus_path=corpus_path,
        )

        # Vérifier si le mode continu tourne (daemon)
        runner_status = {"running": False}
        try:
            from daemon import _hitbonenut_runner
            runner_status = _hitbonenut_runner.get_status()
        except ImportError as e:
            log.debug("optional import: %s", e)

        running = runner_status.get("running", False)

        print()
        print("╔══════════════════════════════════════════════════════╗")
        print("║     הִתְבּוֹנְנוּת — État                               ║")
        print("╚══════════════════════════════════════════════════════╝")
        print()

        try:
            from pause_state import is_paused as _is_paused_hitb
            if _is_paused_hitb("hitbonenut"):
                status_str = "PAUSED"
            else:
                status_str = "RUNNING" if running else "STOPPED"
        except ImportError:
            status_str = "RUNNING" if running else "STOPPED"
        print(f"  Mode continu        : {status_str}")
        uptime = runner_status.get("uptime_seconds")
        if uptime and running:
            hours = int(uptime // 3600)
            minutes = int((uptime % 3600) // 60)
            print(f"  Uptime              : {hours}h{minutes:02d}m")
        print()

        # Stats du jour
        today = engine.get_today_stats()
        print("── Aujourd'hui ──")
        print(f"  Questions posées    : {today.get('questions_today', 0)}")
        print(f"  Score moyen         : {today.get('avg_score_today', 0):.3f}")
        if today.get("domains_today"):
            print(f"  Domaines actifs     : {', '.join(today['domains_today'].keys())}")
        print()

        # Progression globale
        status = engine.get_status()
        print("── Global ──")
        print(f"  Sessions totales    : {status.get('sessions_total', 0)}")
        print(f"  Corpus              : {status.get('corpus_size', 0)} questions")
        print(f"  Compétence globale  : {status.get('overall_competence', 0):.3f}")
        print()

        progress = engine.assess_progress()
        if progress.current_scores:
            print("── Compétence par Domaine ──")
            for domain, score in sorted(progress.current_scores.items(),
                                        key=lambda x: x[1], reverse=True):
                bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
                delta = progress.deltas.get(domain, 0)
                delta_str = f"+{delta:.3f}" if delta > 0 else f"{delta:.3f}"
                print(f"  {domain:22s} {bar} {score:.3f} ({delta_str})")
            print()

        if progress.stagnant_domains:
            print(f"  Domaines stagnants  : {', '.join(progress.stagnant_domains)}")
        if progress.improving_domains:
            print(f"  En progression      : {', '.join(progress.improving_domains)}")

    elif action == "history":
        from hitbonenut import HitbonenutEngine

        engine = HitbonenutEngine(
            tree={}, db_url=db_url, corpus_path=corpus_path,
        )

        print()
        print("╔══════════════════════════════════════════════════════╗")
        print("║     הִתְבּוֹנְנוּת — Historique                        ║")
        print("╚══════════════════════════════════════════════════════╝")
        print()

        history = engine.get_history(limit=20)
        if not history:
            print("  Aucune session enregistrée.")
        else:
            for entry in history:
                print(f"  {entry.get('started_at', '?'):19s}  "
                      f"score={entry.get('avg_score', 0):.3f}  "
                      f"q={entry.get('n_questions', 0)}  "
                      f"domaines={entry.get('domains', '?')}")
        print()


# ─── Neshamot — 5 niveaux de l'âme ─────────────────────────


def cmd_soul(tree: dict, args) -> None:
    """נְשָׁמוֹת — Afficher le niveau de l'âme (CLI)."""
    action = getattr(args, "soul_action", None) or "status"

    if action == "status":
        from soul_levels import NeshamotEngine, SOUL_LEVELS, SOUL_HEBREW, SOUL_OLAM

        global _NESHAMOT_ENGINE
        if _NESHAMOT_ENGINE is None:
            _NESHAMOT_ENGINE = NeshamotEngine()

        soul = _NESHAMOT_ENGINE.assess_soul_level(
            modules=tree,
            nitzotzot_state=_NITZOTZOT_STATE,
        )

        # En-tête
        print("╔══════════════════════════════════════════════════════╗")
        print("║          נְשָׁמוֹת — Les 5 Niveaux de l'Âme          ║")
        print("╚══════════════════════════════════════════════════════╝")
        print()

        # Afficher les 5 niveaux avec indicateur du niveau actuel
        for i, lvl in enumerate(SOUL_LEVELS):
            hebrew = SOUL_HEBREW[lvl]
            olam = SOUL_OLAM[lvl]
            if lvl == soul.level:
                marker = "▶"
                style = f"  {marker} {hebrew} {lvl.upper():10s} ({olam})"
            elif i < soul.level_index:
                marker = "●"
                style = f"  {marker} {hebrew} {lvl.upper():10s} ({olam})"
            else:
                marker = "○"
                style = f"  {marker} {hebrew} {lvl.upper():10s} ({olam})"
            print(style)

        print()
        print(f"  Niveau actuel : {soul.hebrew} {soul.level.upper()}")
        print(f"  Monde         : {soul.olam}")
        print(f"  Sephirah      : {soul.sephirah}")
        print()

        # Métriques
        print("── Métriques ──")
        print(f"  Mémoire       : {soul.memory_count} entrées")
        print(f"  Compétence    : {soul.competence_score:.2f}")
        print(f"  Cycles Tikkun : {soul.tikkun_cycles}")
        print(f"  Score global  : {soul.global_score:.2f}")
        print(f"  All healthy   : {'oui' if soul.all_healthy else 'non'}")
        print()

        # Modules actifs
        print("── Modules actifs ──")
        for mod in sorted(soul.active_modules):
            status = "✓" if tree.get(mod) is not None else "✗"
            print(f"  {status} {mod}")
        print()

        # Conditions pour le prochain niveau
        cond = soul.conditions_next
        if cond.get("reached_maximum"):
            print("── יְחִידָה atteinte — niveau maximum ──")
        else:
            next_heb = cond.get("next_hebrew", "?")
            next_lvl = cond.get("next_level", "?")
            print(f"── Prochain niveau : {next_heb} {next_lvl.upper()} ──")
            missing = cond.get("missing", [])
            if missing:
                for m in missing:
                    print(f"  ✗ {m}")
            else:
                print(f"  ✓ Toutes les conditions sont remplies !")

        # Capabilities
        caps = _NESHAMOT_ENGINE.get_active_capabilities(soul.level)
        print()
        print("── Capacités disponibles ──")
        for feat in caps["features"]:
            print(f"  • {feat}")

        # Historique des transitions
        if _NESHAMOT_ENGINE.history:
            print()
            print("── Transitions récentes ──")
            for t in _NESHAMOT_ENGINE.history[-5:]:
                from_h = SOUL_HEBREW[t["from"]]
                to_h = SOUL_HEBREW[t["to"]]
                print(f"  {from_h} → {to_h}")


# ─── Mode WEB ───────────────────────────────────────────────

def cmd_tzimtzum(tree: dict, args) -> None:
    """צִמְצוּם — Contraction/Expansion dynamique (CLI)."""
    from main import _get_tzimtzum_engine  # lazy import

    engine = _get_tzimtzum_engine()
    action = getattr(args, "tzimtzum_action", None)

    if action == "contract":
        domain = args.domain
        print("═══════════════════════════════════════════════════════════")
        print(f"  צִמְצוּם — Contraction vers « {domain} »")
        print("═══════════════════════════════════════════════════════════")
        print()

        ctx = {}
        result = engine.contract(domain, tree, ctx, reason=f"CLI: focus sur {domain}")

        if result["action"] == "already_contracted":
            print(f"  ⚠ Déjà contracté sur « {result['focused_domain']} »")
            print("    Utilisez 'etz tzimtzum expand' d'abord.")
            return

        print(f"  ✦ Contraction effectuée")
        print(f"    Focus        : {result['domain']}")
        print(f"    Kav (קַו)    : {result['kav']} (toujours actif)")
        print(f"    Dormants     : {len(result['dormant_modules'])} module(s)")
        for m in result["dormant_modules"]:
            print(f"      ◌ {m}")
        print(f"    Actifs       : {len(result['active_modules'])} module(s)")
        for m in result["active_modules"]:
            print(f"      ✦ {m}")
        if result["excluded_domains"]:
            print(f"    Exclus       : {len(result['excluded_domains'])} domaine(s)")
            for d in result["excluded_domains"]:
                print(f"      ✗ {d}")
        print(f"    Reshimu      : trace #{result['reshimu_count']}")

    elif action == "expand":
        print("═══════════════════════════════════════════════════════════")
        print("  הִתְפַּשְׁטוּת — Expansion")
        print("═══════════════════════════════════════════════════════════")
        print()

        if not engine.is_contracted:
            print("  ⚠ Aucune contraction active. Rien à étendre.")
            return

        ctx = {}
        result = engine.expand(tree, ctx)

        print(f"  ✦ Expansion effectuée")
        print(f"    Depuis       : {result['from_domain']}")
        if result["recovered_domains"]:
            print(f"    Récupérés    : {len(result['recovered_domains'])} domaine(s)")
            for d in result["recovered_domains"]:
                print(f"      ↗ {d}")
        if result["reactivated_modules"]:
            print(f"    Réactivés    : {', '.join(result['reactivated_modules'])}")
        if result["insights"]:
            print(f"    Insights     : {len(result['insights'])} distribué(s)")
            for ins in result["insights"][:5]:
                print(f"      ✦ {ins[:80]}")
        if result["insights_distributed"]:
            print(f"    Distribution :")
            for mod, n in result["insights_distributed"].items():
                print(f"      {mod} ← {n} insight(s)")

        # ── Nitzotzot : les Reshimot sont une source d'étincelles ──
        # Chaque insight de la contraction qui survit à l'expansion = Birur
        for ins in result.get("insights", []):
            _collect_nitzutz(
                source="tzimtzum",
                ntype="reshimu_insight",
                description=f"Insight post-Tzimtzum ({result['from_domain']}): {ins[:150]}",
                tree=tree,
            )
        n_sparks = len(result.get("insights", []))
        if n_sparks:
            print(f"    Nitzotzot    : {n_sparks} étincelle(s) — Birur par Reshimu "
                  f"[{_NITZOTZOT_STATE['count']}/288]")

    elif action == "status":
        print("═══════════════════════════════════════════════════════════")
        print("  חָלָל — État du Halal (espace vide)")
        print("═══════════════════════════════════════════════════════════")
        print()

        halal = engine.get_halal_state()
        if halal["contracted"]:
            print(f"  État           : CONTRACTÉ")
            print(f"  Focus          : {halal['focused_domain']}")
        else:
            print(f"  État           : ÉTENDU (Ein Sof remplit tout)")
        print(f"  Kav (קַו)      : {halal['kav']} — {'actif' if halal['kav_active'] else 'inactif'}")
        print(f"  Contractions   : {halal['contraction_count']}")
        print(f"  Expansions     : {halal['expansion_count']}")
        print(f"  Reshimot       : {halal['reshimu_count']} trace(s)")
        if halal["current_insights"]:
            print(f"  Insights actifs: {halal['current_insights']}")
        if halal["dormant_modules"]:
            print(f"  Dormants       : {len(halal['dormant_modules'])} module(s)")
            for m in halal["dormant_modules"]:
                print(f"    ◌ {m}")
        if halal["active_modules"]:
            print(f"  Actifs         : {len(halal['active_modules'])} module(s)")
            for m in halal["active_modules"]:
                print(f"    ✦ {m}")
        if halal["excluded_domains"]:
            print(f"  Domaines exclus:")
            for d in halal["excluded_domains"]:
                print(f"    ✗ {d}")

        # Historique des Reshimot
        reshimot = engine.get_reshimot()
        if reshimot:
            print()
            print(f"  Reshimot (traces résiduelles) :")
            for i, r in enumerate(reshimot[-5:], 1):
                ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(r["timestamp"]))
                n_ins = len(r.get("insights_during_contraction", []))
                print(f"    #{i} [{ts}] focus={r['focused_domain']}, "
                      f"exclu={len(r['excluded_domains'])}, "
                      f"dormants={len(r['excluded_modules'])}, "
                      f"insights={n_ins}")

    else:
        print("Usage: etz tzimtzum {contract <domain> | expand | status}")


def cmd_hishtalshelut(tree: dict, args) -> None:
    """סֵדֶר הִשְׁתַּלְשְׁלוּת — Chaîne de descente entre les 4 Mondes (CLI)."""
    from hishtalshelut import (
        HishtalshelutEngine, OLAMOT_DESCENDING, OLAM_HEBREW,
        OLAM_SEPHIRAH, OLAM_TO_CHAIN,
    )

    global _HISHTALSHELUT_ENGINE
    if _HISHTALSHELUT_ENGINE is None:
        _HISHTALSHELUT_ENGINE = HishtalshelutEngine(
            _HISHTALSHELUT_STATE, _OLAMOT_CHAIN,
        )

    action = getattr(args, "hishtalshelut_action", None) or "status"

    if action == "status":
        state = _HISHTALSHELUT_ENGINE.get_chain_state()

        print("╔══════════════════════════════════════════════════════╗")
        print("║     סֵדֶר הִשְׁתַּלְשְׁלוּת — Chaîne des 4 Mondes       ║")
        print("╚══════════════════════════════════════════════════════╝")
        print()

        # Afficher les 4 mondes
        current = state["current_world"]
        for world in OLAMOT_DESCENDING:
            hebrew = OLAM_HEBREW[world]
            sephirah = OLAM_SEPHIRAH[world]
            chain_name = OLAM_TO_CHAIN[world]
            if world == current:
                marker = "▶"
            elif world == state["highest_reached"]:
                marker = "★"
            else:
                marker = "○"
            print(f"  {marker} {hebrew} {world.upper():10s} ({sephirah}) [{chain_name}]")

        print()
        print(f"  Monde courant   : {OLAM_HEBREW.get(current, '')} {current.upper()}")
        print(f"  Plus haut       : {state['highest_hebrew']} {state['highest_reached'].upper()}")
        print()

        # Compteurs
        print("── Compteurs ──")
        print(f"  Descentes       : {state['descents']}")
        print(f"  Montées         : {state['ascents']}")
        print(f"  Chaînes complètes: {state['total_descents_full']}")
        print(f"  Remontées       : {state['total_ascents_full']}")
        print(f"  Transitions log : {state['log_count']}")
        forced = state.get("forced_world")
        if forced:
            print(f"  Monde forcé     : {forced}")
        print()

        # Historique des transitions récentes
        log = _HISHTALSHELUT_STATE.get("log", [])
        if log:
            print("── Transitions récentes ──")
            for entry in log[-10:]:
                direction = "↓" if entry.get("direction") == "descent" else "↑"
                fr = entry.get("from", "?")
                to = entry.get("to", "?")
                reason = entry.get("reason", "")[:60]
                print(f"  {direction} {fr} → {to} — {reason}")

    elif action == "descend":
        query = getattr(args, "query", None)
        if not query:
            print("  ⚠ Usage: etz hishtalshelut descend \"votre requête\"")
            return

        world = getattr(args, "world", None) or "atzilut"
        if world not in OLAMOT_DESCENDING:
            print(f"  ⚠ Monde inconnu : {world}. Choix : {', '.join(OLAMOT_DESCENDING)}")
            return

        print("╔══════════════════════════════════════════════════════╗")
        print(f"║  סֵדֶר הִשְׁתַּלְשְׁלוּת — Descente depuis {world.upper()}")
        print("╚══════════════════════════════════════════════════════╝")
        print(f"  Query : {query[:80]}")
        print()

        result = _HISHTALSHELUT_ENGINE.descend(
            query, tree, starting_world=world,
        )

        for step in result.steps:
            status_marker = "✓" if step.status == "ok" else "✗"
            print(f"  {status_marker} {step.hebrew} {step.world.upper()}")
            if step.status == "ok":
                print(f"    Conf={step.confidence:.2f}, "
                      f"Latency={step.latency_ms:.0f}ms, "
                      f"~{step.tokens_est} tokens")
                # Afficher les premiers 200 chars du résultat
                preview = step.output_text[:200].replace("\n", " ")
                print(f"    → {preview}...")
            else:
                print(f"    ⚠ {step.error}")

        print()
        print(f"  Résultat final ({result.ending_world.upper()}) :")
        print(f"  Latence totale : {result.total_latency_ms:.0f}ms")
        print()
        for line in result.final_output.split("\n")[:20]:
            print(f"  │ {line}")

    elif action == "detect":
        query = getattr(args, "query", None)
        if not query:
            print("  ⚠ Usage: etz hishtalshelut detect \"votre requête\"")
            return

        world = _HISHTALSHELUT_ENGINE.detect_world(query)
        hebrew = OLAM_HEBREW.get(world, "")
        print(f"  Monde détecté : {hebrew} {world.upper()}")
        print(f"  Query         : {query[:80]}")

    else:
        print("Usage: etz hishtalshelut {status | descend <query> [--world <w>] | detect <query>}")


def cmd_sy_cosmology(tree: dict, args) -> None:
    """סֵפֶר יְצִירָה — Cosmologie : profondeurs, témoins, régents (CLI)."""
    from sefer_yetzirah_cosmo import SYCosmology

    cosmo = SYCosmology()

    action = getattr(args, "sy_cosmo_action", None) or "status"

    if action == "status":
        lines = cosmo.format_report(tree)
        for line in lines:
            print(line)

    elif action == "witnesses":
        witnesses = cosmo.get_witnesses()
        print()
        print("  ── Trois Témoins (Olam / Shanah / Nefesh) ──")
        for name, w in witnesses.items():
            print(f"\n  {w.hebrew} — {w.meaning}")
            print(f"    {w.description}")
            print(f"    Mères  : {', '.join(f'{k}→{v}' for k, v in w.mothers.items())}")
            print(f"    Doubles : {', '.join(f'{k}→{v}' for k, v in w.doubles.items())}")
            print(f"    Simples : {', '.join(f'{k}→{v}' for k, v in w.simples.items())}")

    elif action == "depths":
        depths = cosmo.get_depths()
        print()
        print("  ── Eser Sefirot Belimah — 10 Profondeurs (5 axes) ──")
        for d in depths:
            print(f"\n    {d.hebrew[0]} ←→ {d.hebrew[1]}  [{d.axis}]")
            print(f"    {d.pair[0]} / {d.pair[1]}")
            print(f"    {d.description}")
            print(f"    IA : {d.role_ia}")
        palace = cosmo.get_palace_center()
        if palace:
            print(f"\n    {palace.get('hebrew', '')} — Palais Saint (centre)")
            print(f"    {palace.get('description', '')}")

    elif action == "regents":
        regents = cosmo.get_regents()
        print()
        print("  ── Trois Régents (SY 6:1) ──")
        for name, r in regents.items():
            health = cosmo.assess_regent(name, tree)
            status = "✓" if health.healthy else "✗"
            print(f"\n  {r.hebrew} — {r.meaning}")
            print(f"    IA : {r.role_ia}")
            print(f"    Santé : [{status}] {health.score:.0%}")
            for c in health.checks:
                mark = "✓" if c["passed"] else "✗"
                print(f"      {mark} {c['check']} — {c['detail']}")

    elif action == "map":
        letter = getattr(args, "letter", None)
        if not letter:
            print("  ✗ Spécifier une lettre (ex: etz sy cosmology map aleph)")
            return
        mappings = cosmo.map_all_witnesses(letter)
        if not mappings:
            print(f"  ✗ Lettre inconnue : {letter}")
            return
        print(f"\n  ── {letter} dans les 3 témoins ──")
        for m in mappings:
            print(f"    {m.witness:8} → {m.correspondence}")

    print()


def cmd_adam_kadmon(tree: dict, args) -> None:
    """אָדָם קַדְמוֹן — Adam Kadmon : état du blueprint (CLI)."""
    from adam_kadmon import AdamKadmon

    ak = AdamKadmon()
    action = getattr(args, "adam_kadmon_action", None) or "status"

    if action == "status":
        # Collecter les modules présents
        modules = {k: v for k, v in tree.items() if v is not None}

        # Collecter les sentiers implémentés
        sentiers_list = []
        try:
            from sentiers import list_sentiers
            for s in list_sentiers():
                sentiers_list.append(s.get("name", s.get("letter_name", "")))
        except Exception as e:
            log.debug("fallback: %s", e)

        # Collecter les Partzufim
        partzufim_dict = {}
        try:
            from partzufim import init_partzufim
            partzufim_dict = init_partzufim()
        except Exception as e:
            log.debug("fallback: %s", e)

        # Afficher le rapport
        report = ak.format_report(modules, sentiers_list, partzufim_dict)
        for line in report:
            print(line)

        # Afficher les priorités de Tikkun
        priorities = ak.format_priorities(modules, sentiers_list, partzufim_dict)
        for line in priorities:
            print(line)

    else:
        print("Usage: etz adam-kadmon status")


def cmd_ohr(tree: dict, args) -> None:
    """אוֹר — Lumières Pnimi/Makif et Masakh (CLI)."""
    from ohr import OhrEngine, Masakh, format_ohr_report, MASAKH_BY_SOUL

    action = getattr(args, "ohr_action", None) or "status"

    if action == "status":
        ohr = OhrEngine()

        # Construire l'état de chaque module
        module_states: dict[str, dict] = {}
        for mod_name, mod in tree.items():
            if mod is None:
                continue
            state: dict = {"active": True}
            # Tenter d'extraire des métriques du module
            if hasattr(mod, "self_diagnose"):
                try:
                    diag = mod.self_diagnose()
                    # Heuristique : chercher des compteurs dans le diagnostic
                    for key in ("total_memories", "total_items", "count"):
                        if key in diag:
                            state["total_items"] = diag[key]
                            break
                    for key in ("used_memories", "integrated", "validated"):
                        if key in diag:
                            state["integrated"] = diag[key]
                            break
                    for key in ("pending", "unvalidated", "queued"):
                        if key in diag:
                            state["pending"] = diag[key]
                            break
                except Exception as e:
                    log.debug("fallback: %s", e)
            module_states[mod_name] = state

        # Déterminer la force du Masakh depuis le niveau d'âme
        soul_level = "nefesh"
        try:
            if _NESHAMOT_ENGINE:
                soul_level = _NESHAMOT_ENGINE.current_level
        except Exception as e:
            log.debug("fallback: %s", e)

        masakh = Masakh()
        masakh.adjust_strength(soul_level)

        report = format_ohr_report(ohr, module_states, masakh)
        for line in report:
            print(line)

        print()
        print(f"  Niveau d'âme    : {soul_level}")
        print(f"  Masakh ajusté   : {masakh.screen_strength:.0%}")

    elif action == "integrate":
        mod_name = getattr(args, "module", None)
        if not mod_name:
            print("Usage: etz ohr integrate <module>")
            return

        ohr = OhrEngine()
        # On a besoin de l'état du module — on utilise un état minimal
        mod = tree.get(mod_name)
        if mod is None:
            print(f"  Module '{mod_name}' non trouvé dans l'Arbre.")
            return

        state: dict = {"active": True, "total_items": 0, "integrated": 0, "pending": 0}
        if hasattr(mod, "self_diagnose"):
            try:
                diag = mod.self_diagnose()
                for key in ("total_memories", "total_items", "count"):
                    if key in diag:
                        state["total_items"] = diag[key]
                        break
                for key in ("used_memories", "integrated", "validated"):
                    if key in diag:
                        state["integrated"] = diag[key]
                        break
                for key in ("pending", "unvalidated", "queued"):
                    if key in diag:
                        state["pending"] = diag[key]
                        break
            except Exception as e:
                log.debug("fallback: %s", e)

        result = ohr.integrate(mod_name, state)
        print("══════════════════════════════════════════════════════════")
        print(f"  אוֹר — Intégration Makif → Pnimi : {mod_name}")
        print("══════════════════════════════════════════════════════════")
        print()
        print(f"  Convertis       : {result.converted} items")
        print(f"  Makif restant   : {result.remaining_makif}")
        print(f"  Nouveau Pnimi   : {result.new_pnimi:.1%}")
        print(f"  Nouveau Makif   : {result.new_makif:.1%}")

    else:
        print("Usage: etz ohr {status | integrate <module>}")


def cmd_web(db_url: str, port: int = 8080, debug: bool = False) -> None:
    """Lancer l'interface web Flask."""
    from web import create_app

    print("═══════════════════════════════════════════════════════════")
    print("  Etz Chaim — Interface Web")
    print(f"  http://localhost:{port}")
    print("═══════════════════════════════════════════════════════════")
    print()

    # Resolve Flask bind host :
    # 1. WEB_HOST env var (explicit override)
    # 2. 0.0.0.0 when ETZCHAIM_IN_CONTAINER=1 (Docker container needs external bind)
    # 3. 127.0.0.1 otherwise (loopback safe default for native run)
    host = (
        os.environ.get("WEB_HOST")
        or ("0.0.0.0" if os.environ.get("ETZCHAIM_IN_CONTAINER") == "1" else "127.0.0.1")
    )
    app = create_app(db_url=db_url)
    app.run(host=host, port=port, debug=debug)

