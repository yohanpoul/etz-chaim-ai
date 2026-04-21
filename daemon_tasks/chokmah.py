"""daemon_tasks/chokmah.py — Chokmah tasks: insightforge, analogies, open questions, cube, clustering.

Extracted from daemon.py for modularity.
"""
from __future__ import annotations

import logging
import os

DB_URL = (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim"))
log = logging.getLogger("etz-daemon")


def _generate_forge_questions(tree: dict, max_questions: int = 3) -> list[dict]:
    """Générer des questions pour InsightForge à partir des données existantes.

    Sources :
      1. Hitbonenut — questions récentes diversifiées
      2. FailureToInsight — patterns d'échec à explorer
      3. EpisteMemory — croisements inter-domaines
    """
    from pool import get_conn

    questions: list[dict] = []

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                # 1. Hitbonenut — question récente la plus riche (pas de doublon)
                cur.execute("""
                    SELECT DISTINCT ON (question) question
                    FROM hitbonenut_questions
                    WHERE length(question) > 30
                    ORDER BY question, created_at DESC
                    LIMIT 20
                """)
                hitbo_qs = [r[0] for r in cur.fetchall()]
                if hitbo_qs:
                    best = max(hitbo_qs, key=len)
                    questions.append({
                        "question": best,
                        "domain": "hitbonenut",
                        "source": "hitbonenut",
                    })

                # 2. FTI — patterns d'échec récents (opportunités et warnings)
                cur.execute("""
                    SELECT content, domain, insight_type
                    FROM failuretoinsight_insights
                    WHERE insight_type IN ('opportunity', 'pattern', 'warning')
                    ORDER BY created_at DESC
                    LIMIT 10
                """)
                fti_rows = cur.fetchall()
                if fti_rows:
                    unique_contents = list({r[0] for r in fti_rows})
                    if unique_contents:
                        q = (
                            "Quels patterns émergent des échecs récents ? "
                            + "; ".join(unique_contents[:3])
                        )
                        questions.append({
                            "question": q[:500],
                            "domain": "failure_analysis",
                            "source": "failuretoinsight",
                        })

                # 3. Cross-domain — domaines les plus actifs en EpisteMemory
                cur.execute("""
                    SELECT domain, COUNT(*) as cnt
                    FROM epistememory
                    WHERE domain IS NOT NULL AND domain <> ''
                      AND epistemic_status <> 'deprecated'
                    GROUP BY domain
                    HAVING COUNT(*) >= 3
                    ORDER BY cnt DESC
                    LIMIT 10
                """)
                domains = [r[0] for r in cur.fetchall()]
                if len(domains) >= 2:
                    d1, d2 = domains[0], domains[1]
                    questions.append({
                        "question": (
                            f"Quelles connexions non-évidentes existent entre "
                            f"'{d1}' et '{d2}' dans la base de connaissances ?"
                        ),
                        "domain": f"{d1}+{d2}",
                        "source": "cross_domain",
                    })
    except Exception as e:
        log.warning("Génération questions InsightForge échouée: %s", e)

    return questions[:max_questions]


def _resolve_fti(tree: dict):
    """Résoudre l'instance FailureToInsight depuis l'arbre.

    Priorité : tree["lamed"] (main.py standard) puis alias, puis via gevurah.
    """
    fti = tree.get("lamed") or tree.get("failuretoinsight")
    if fti is None:
        gevurah = tree.get("gevurah")
        if gevurah:
            fti = (
                getattr(gevurah, "fti", None)
                or getattr(gevurah, "failure_to_insight", None)
            )
            # AutoJudge stocke FTI dans self.lamed.fti (LamedBridge)
            if fti is None:
                bridge = getattr(gevurah, "lamed", None)
                if bridge is not None:
                    fti = getattr(bridge, "fti", None)
    return fti


def _recycle_rejections_to_fti(tree: dict, batch_limit: int = 10) -> int:
    """Chaîne Gevurah → Lamed : recycler les rejets AutoJudge via FailureToInsight.

    Le Birur des Qliphoth : les réponses rejetées par Gevurah contiennent
    des Nitzotzot (étincelles) que le Lamed peut extraire.
    Les insights résultants nourrissent InsightForge via _generate_forge_questions.

    Idempotence : matching exact via (source_type='experiment', source_id=ae.id).
    source_type 'experiment' satisfait la CHECK constraint
    failuretoinsight_analyses_source_type_check.

    Returns:
        Nombre de rejets recyclés.
    """
    from pool import get_conn

    recycled = 0
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ae.id, ae.original_content, ae.modified_content,
                           ae.domain_id, ae.score_overall
                    FROM autojudge_experiments ae
                    WHERE ae.decision = 'rejected'
                      AND ae.domain_id = 'hitbonenut_eval'
                      AND NOT EXISTS (
                          SELECT 1 FROM failuretoinsight_analyses fa
                          WHERE fa.source_type = 'experiment'
                            AND fa.source_id = ae.id
                      )
                    ORDER BY ae.created_at DESC
                    LIMIT %s
                """, (batch_limit,))
                rejections = cur.fetchall()

        if not rejections:
            return 0

        fti = _resolve_fti(tree)
        if fti is None:
            log.debug("FailureToInsight non disponible pour recyclage autojudge")
            return 0

        for row in rejections:
            ae_id, question, response, domain_id, score = row
            description = (
                f"Rejet Gevurah (score={(score or 0.0):.3f}) sur '{(question or '')[:100]}' "
                f"— réponse: {(response or '')[:200]}"
            )
            try:
                analysis = fti.analyze_failure(
                    description=description,
                    source_type="experiment",
                    source_id=ae_id,
                    domain=domain_id or "general",
                )
                fti.extract_nitzotzot(analysis_id=analysis.id)
                recycled += 1
            except Exception as e:
                log.warning("FTI recycle error for %s: %s", ae_id, e)

        if recycled > 0:
            log.info("Rejection→FTI: %d/%d rejets AutoJudge recyclés en insights",
                     recycled, len(rejections))

    except Exception as e:
        log.warning("Rejection→FTI query failed: %s", e)

    return recycled


def _recycle_candidate_rejections_to_fti(
    tree: dict, batch_limit: int = 20,
) -> int:
    """Chaîne InsightForge → Lamed : recycler les candidate_insights rejetés.

    Complète _recycle_rejections_to_fti : ce dernier ne couvre que les rejets
    AutoJudge (autojudge_experiments). Cette fonction traite les rejets de
    Triple Validation (insightforge.core — 'Triple validation failed: ...')
    qui sont stockés dans candidate_insights avec status='rejected'.

    Chaque candidat rejeté produit :
      - 1 failuretoinsight_analysis (source_type='hypothesis', source_id=ci.id)
      - ≥ 1 failuretoinsight_insight (anti_pattern + classifiés)
      - 1 entrée EpisteMemory (via fti.memory.remember si connecté)

    Idempotence : (source_type='hypothesis', source_id=ci.id) —
    un candidat rejeté est élevé exactement une fois.

    Rate limit : batch_limit (défaut 20) rejets par cycle daemon.

    Args:
        tree: arbre des modules (lookup de l'instance FailureToInsight)
        batch_limit: nombre max de rejets élevés par cycle

    Returns:
        Nombre de rejets recyclés en analyses FTI.
    """
    from pool import get_conn

    recycled = 0
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ci.id, ci.description, ci.domain, ci.confidence,
                           ci.novelty_score, ci.rejection_reason
                    FROM candidate_insights ci
                    WHERE ci.status = 'rejected'
                      AND NOT EXISTS (
                          SELECT 1 FROM failuretoinsight_analyses fa
                          WHERE fa.source_type = 'hypothesis'
                            AND fa.source_id = ci.id
                      )
                    ORDER BY ci.created_at DESC
                    LIMIT %s
                """, (batch_limit,))
                rejections = cur.fetchall()

        if not rejections:
            return 0

        fti = _resolve_fti(tree)
        if fti is None:
            log.debug("FailureToInsight non disponible pour recyclage candidate_insights")
            return 0

        for row in rejections:
            ci_id, desc, domain, conf, novelty, reason = row
            description = (
                f"Candidat InsightForge rejeté "
                f"(conf={(conf or 0.0):.2f}, novelty={(novelty or 0.0):.2f}) "
                f"sur domaine '{domain or 'general'}': "
                f"{(desc or '')[:200]}"
            )
            if reason:
                description += f" — reason: {reason[:200]}"

            context = {
                "candidate_id": str(ci_id),
                "domain": domain or "",
                "confidence": float(conf or 0.0),
                "novelty_score": float(novelty or 0.0),
                "rejection_reason": reason or "",
            }

            try:
                analysis = fti.analyze_failure(
                    description=description,
                    source_type="hypothesis",
                    source_id=ci_id,
                    context=context,
                    domain=domain or "general",
                )
                fti.extract_nitzotzot(analysis_id=analysis.id)
                recycled += 1
            except Exception as e:
                log.warning("FTI candidate recycle error for %s: %s", ci_id, e)

        if recycled > 0:
            log.info(
                "CandidateRejection→FTI: %d/%d rejets InsightForge recyclés en insights",
                recycled, len(rejections),
            )

    except Exception as e:
        log.warning("CandidateRejection→FTI query failed: %s", e)

    return recycled


def task_insightforge_to_selfmodel(tree: dict) -> dict:
    """InsightForge → SelfModel — bridge I2 (audit Cycle 4).

    חָכְמָה → דַּעַת — les insights triple-validés (Binah + Gevurah + Da'at)
    produits par InsightForge doivent être ingérés dans Da'at pour enrichir
    sa connaissance de soi. Sans cette boucle, Da'at agrège passivement les
    stats des 6 Sephiroth mais ignore les insights émergents.

    Idempotent : utilise la clé UNIQUE (source_module, source_id) de
    `selfmodel_external_insights`.
    """
    report = {
        "task": "insightforge_to_selfmodel",
        "candidates_read": 0,
        "fed": 0,
        "duplicates": 0,
    }

    daat = tree.get("daat")
    if daat is None:
        report["error"] = "SelfModel (Da'at) non disponible"
        return report

    try:
        import psycopg2.extras
        from pool import get_conn

        # Triple validés ET pas encore ingérés dans selfmodel_external_insights
        with get_conn() as conn:
            with conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            ) as cur:
                cur.execute("""
                    SELECT ci.id, ci.description, ci.confidence, ci.domain,
                           ci.novelty_score
                    FROM candidate_insights ci
                    WHERE ci.status = 'insight'
                      AND ci.binah_validated = TRUE
                      AND ci.gevurah_validated = TRUE
                      AND ci.daat_validated = TRUE
                      AND NOT EXISTS (
                          SELECT 1 FROM selfmodel_external_insights sei
                          WHERE sei.source_module = 'insightforge'
                            AND sei.source_id = ci.id
                      )
                    ORDER BY ci.created_at DESC
                    LIMIT 200
                """)
                rows = cur.fetchall()

        report["candidates_read"] = len(rows)

        for row in rows:
            try:
                inserted = daat.feed_insight(
                    source_module="insightforge",
                    source_id=row["id"],
                    description=row["description"],
                    confidence=float(row.get("confidence") or 0.5),
                    domain=row.get("domain") or None,
                    novelty_score=(
                        float(row["novelty_score"])
                        if row.get("novelty_score") is not None else None
                    ),
                )
                if inserted:
                    report["fed"] += 1
                else:
                    report["duplicates"] += 1
            except Exception as e:
                log.warning("IF→SM feed %s: %s", row.get("id"), e)

        if report["fed"]:
            log.info(
                "IF→SM: %d insights ingérés (lus=%d, doublons=%d)",
                report["fed"], report["candidates_read"], report["duplicates"],
            )

    except Exception as e:
        report["error"] = str(e)
        log.error("IF→SM error: %s", e)

    return report


def task_insightforge(tree: dict) -> dict:
    """Chokmah — Forge d'insights à partir des données accumulées.

    חָכְמָה — Le flash du Yod. Mobilise tous les modules
    autour de questions générées automatiquement à partir de :
    - Hitbonenut (questions contemplatives)
    - FailureToInsight (patterns d'échec)
    - EpisteMemory (croisements inter-domaines)

    Chaque question passe par le pipeline complet :
    Orchestration → Novelty → Triple Validation → Émergence.
    """
    report = {
        "task": "insightforge",
        "questions_generated": 0,
        "sessions_completed": 0,
        "total_candidates": 0,
        "total_insights": 0,
        "total_rejected": 0,
        "emergence_signals": 0,
        "ratzo_v_shov": {},
        "sessions": [],
    }

    chokmah = tree.get("chokmah")
    if not chokmah:
        report["error"] = "InsightForge (Chokmah) non disponible"
        return report

    # Ratzo v'Shov : construire le contexte Shov à partir des rejets précédents
    shov_context = ""
    try:
        shov_context = chokmah.ratzo_v_shov.get_shov_context_for_next_cycle()
        if shov_context:
            log.info("InsightForge Shov: contexte injecté (%d lignes)",
                     shov_context.count("\n") + 1)
    except Exception as e:
        log.warning("InsightForge Shov context failed: %s", e)

    # Générer les questions
    questions = _generate_forge_questions(tree)
    report["questions_generated"] = len(questions)

    if not questions:
        report["early_stop"] = True
        report["early_stop_reason"] = "Aucune question générée (pas assez de données)"
        log.info("InsightForge: aucune question, skip")
        return report

    log.info("InsightForge: %d questions générées", len(questions))

    for q_info in questions:
        question = q_info["question"]
        domain = q_info["domain"]
        source = q_info["source"]

        log.info(
            "InsightForge: forge [%s] '%s'",
            source, question[:80],
        )

        try:
            session = chokmah.forge(
                question=question,
                domain=domain,
                max_explore=10,
                shov_context=shov_context,
            )

            session_report = {
                "question": question[:200],
                "domain": domain,
                "source": source,
                "status": session.status,
                "total_candidates": session.total_candidates,
                "insights_found": session.insights_found,
                "rejected_count": session.rejected_count,
                "pearl_level": session.pearl_level,
                "modules_consulted": session.modules_consulted,
                "emergence_count": len(session.emergence_signals),
            }

            # Insights validés
            if session.validated_insights:
                session_report["insights"] = [
                    {
                        "description": i.description[:200],
                        "novelty": i.novelty_score,
                        "confidence": i.confidence,
                        "triple_validated": (
                            i.binah_validated
                            and i.gevurah_validated
                            and i.daat_validated
                        ),
                    }
                    for i in session.validated_insights[:5]
                ]

            report["sessions"].append(session_report)
            report["sessions_completed"] += 1
            report["total_candidates"] += session.total_candidates
            report["total_insights"] += session.insights_found
            report["total_rejected"] += session.rejected_count
            report["emergence_signals"] += len(session.emergence_signals)

            log.info(
                "InsightForge [%s]: %d candidats, %d insights, %d rejetés, "
                "pearl=%s, émergence=%d",
                source, session.total_candidates, session.insights_found,
                session.rejected_count, session.pearl_level,
                len(session.emergence_signals),
            )

        except Exception as e:
            log.error("InsightForge error [%s]: %s", source, e)
            report["sessions"].append({
                "question": question[:200],
                "source": source,
                "error": str(e),
            })

    # Auto-diagnostic Ghagiel
    try:
        diag = chokmah.self_diagnose()
        report["diagnosis"] = diag
    except Exception as e:
        log.warning("InsightForge self_diagnose failed: %s", e)

    # Ratzo v'Shov : tracking d'amélioration
    try:
        improvement = chokmah.ratzo_v_shov.track_improvement()
        report["ratzo_v_shov"] = improvement
        log.info(
            "Ratzo v'Shov: trend=%s, delta=%.3f (early=%.3f → recent=%.3f)",
            improvement.get("trend", "?"),
            improvement.get("delta", 0),
            improvement.get("avg_rejection_rate_early", 0),
            improvement.get("avg_rejection_rate_recent", 0),
        )
    except Exception as e:
        log.warning("InsightForge Ratzo v'Shov tracking failed: %s", e)

    # Ratzo v'Shov : accumuler les patterns pour feedback cross-module
    try:
        accumulated = chokmah.ratzo_v_shov.accumulate_patterns(n_sessions=10)
        report["ratzo_accumulated"] = accumulated.get("accumulated", False)

        # Si dégradation, enregistrer un warning Beinoni
        trend = report.get("ratzo_v_shov", {}).get("trend")
        if trend == "degrading":
            log.warning(
                "RATZO V'SHOV DÉGRADATION: le taux de rejet augmente — "
                "le Shov ne corrige plus efficacement"
            )
            report["ratzo_degrading"] = True
    except Exception as e:
        log.debug("InsightForge Ratzo accumulate: %s", e)

    log.info(
        "InsightForge terminé: %d sessions, %d insights / %d candidats, "
        "%d émergences",
        report["sessions_completed"], report["total_insights"],
        report["total_candidates"], report["emergence_signals"],
    )

    return report


def task_chesed_analogies(tree: dict) -> dict:
    """Chesed détecte les analogies cross-domain dans les connexions récentes.

    Analyse les connexions existantes pour trouver :
    - Patterns récurrents entre paires de domaines (heuristique)
    - Analogies structurelles profondes (LLM via Ollama, think:false)
    - Concepts qui traversent 3+ domaines

    Stocke dans explorationengine_analogies.
    """
    from daemon import _is_tzimtzum_module_active

    report = {
        "task": "chesed_analogies",
        "heuristic_found": 0,
        "llm_found": 0,
        "stored": 0,
        "errors": [],
    }

    # Garde Tzimtzum : Chesed peut être mis en dormance
    if not _is_tzimtzum_module_active("chesed"):
        report["skipped"] = "Chesed dormant (Tzimtzum actif)"
        log.info("Chesed: SKIP — module dormant par Tzimtzum")
        return report

    chesed = tree.get("chesed")
    if not chesed:
        report["error"] = "Module chesed non disponible"
        return report

    # Ratzo v'Shov feedback : réduire les paires stériles
    avoid_pairs: list[str] = []
    try:
        chokmah = tree.get("chokmah")
        if chokmah and hasattr(chokmah, "ratzo_v_shov"):
            avoid_pairs = chokmah.ratzo_v_shov.get_high_rejection_domains(threshold=0.5)
            if avoid_pairs:
                report["ratzo_avoid_pairs"] = avoid_pairs
                log.info("Chesed: %d paires à éviter (Ratzo feedback)", len(avoid_pairs))
    except Exception as e:
        log.warning("Ratzo v'Shov feedback failed: %s", e)

    try:
        result = chesed.run_analogy_detection(limit=100)
        report.update(result)
        log.info(
            "Chesed analogies: %d heuristiques, %d LLM, %d stockées, %d doublons",
            result["heuristic_found"], result["llm_found"],
            result["stored"], result["duplicates_skipped"],
        )
    except Exception as e:
        report["error"] = str(e)
        log.error("Chesed analogies error: %s", e)

    return report


def task_explore_open_questions(tree: dict) -> dict:
    """Chesed explore les open_questions de Tiferet (R2.7).

    Les open_questions sont des tensions escaladées qui attendent
    de l'évidence supplémentaire. Chesed les utilise comme graines
    d'exploration inter-domaines. Si l'exploration trouve des
    connexions fortes, la question est marquée résolue.

    Léger : max 5 questions par cycle.
    """
    from daemon import _is_tzimtzum_module_active

    report: dict = {
        "task": "explore_open_questions",
        "explored": 0,
        "resolved": 0,
        "connections_found": 0,
        "questions": [],
    }

    # Garde Tzimtzum : Chesed peut être mis en dormance
    if not _is_tzimtzum_module_active("chesed"):
        report["skipped"] = "Chesed dormant (Tzimtzum actif)"
        log.info("explore_open_questions: SKIP — Chesed dormant par Tzimtzum")
        return report

    chesed = tree.get("chesed")
    if not chesed:
        report["error"] = "Module chesed non disponible"
        return report

    if not chesed.dissensus:
        report["error"] = "Tiferet (dissensus) non connecté à Chesed"
        return report

    try:
        results = chesed.explore_open_questions(max_questions=5)
        report["questions"] = results
        report["explored"] = sum(1 for r in results if r.get("explored"))
        report["resolved"] = sum(1 for r in results if r.get("resolved"))
        report["connections_found"] = sum(
            r.get("connections_found", 0) for r in results
        )
        log.info(
            "explore_open_questions: %d explorées, %d résolues, %d connexions",
            report["explored"], report["resolved"], report["connections_found"],
        )
    except Exception as e:
        report["error"] = str(e)
        log.error("explore_open_questions error: %s", e)

    return report


def task_cube_insights(tree: dict) -> dict:
    """Cube de l'Espace — découverte de connexions cachées.

    Scanne les embeddings hybrides pour trouver des paires de concepts
    proches dans le Cube (structure kabbalistique) mais éloignés en ML
    (sémantique statistique). Chaque paire est un candidat d'insight.

    Les candidats sont injectés dans InsightForge pour validation
    par le pipeline standard (Binah/Gevurah/Da'at).
    """
    report = {
        "task": "cube_insights",
        "hidden_found": 0,
        "candidates_generated": 0,
        "injected": 0,
        "errors": [],
    }

    try:
        from insightforge.cube_insights import CubeInsightGenerator

        gen = CubeInsightGenerator(db_url=DB_URL)
        hidden = gen.discover_hidden_connections(min_gap=0.2, top_k=20)
        report["hidden_found"] = len(hidden)

        if hidden:
            candidates = gen.format_as_insight_candidates(hidden)
            report["candidates_generated"] = len(candidates)

            # Inject into InsightForge if available
            insightforge = tree.get("chokmah")
            if insightforge and hasattr(insightforge, "db"):
                from insightforge.models import CandidateInsight

                for cand in candidates:
                    try:
                        ci = CandidateInsight(
                            description=cand["description"],
                            source_module="cube_insights",
                            domain=cand["domain"],
                            confidence=cand["confidence"],
                            connects_domains=cand["connects_domains"],
                        )
                        insightforge.db.save_candidate(ci)
                        report["injected"] += 1
                    except Exception as e:
                        report["errors"].append(f"inject: {e}")

        log.info(
            "CubeInsights: %d hidden, %d candidates, %d injected",
            report["hidden_found"], report["candidates_generated"],
            report["injected"],
        )
    except Exception as e:
        report["error"] = str(e)
        log.error("CubeInsights error: %s", e)

    return report


def task_clustering(tree: dict) -> dict:
    """Clustering dual Kab vs ML — Kibboutz.

    Compare les regroupements kabbalistiques (30D Cube) vs ML (768D sémantique).
    Persiste les résultats, route les top désaccords vers DissensuEngine.
    """
    report = {"task": "clustering"}

    try:
        from kabbalah.clustering import KabbalisticClustering

        kc = KabbalisticClustering(db_url=DB_URL)

        tiferet = tree.get("tiferet")
        result = kc.run_full(
            n_clusters=10,
            top_n_pairs=100,
            min_gap=0.2,
            tiferet=tiferet,
            route_top=5,
        )
        report.update(result)

        log.info(
            "Clustering: %d concepts, ratio=%.3f, %d pair disagreements, %d routed",
            result.get("n_concepts", 0),
            result.get("agreement_ratio", 0.0),
            result.get("n_pair_disagreements", 0),
            result.get("routed_to_dissensus", 0),
        )
    except Exception as e:
        report["error"] = str(e)
        log.error("Clustering error: %s", e)

    return report
