"""daemon_tasks/exploration.py — Exploration tasks: auto_improve, full_tree, hitbonenut, gevurah, etc.

Extracted from daemon.py for modularity.
"""
from __future__ import annotations

import logging
import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path

DB_URL = (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim"))
log = logging.getLogger("etz-daemon")


# ─── EtzDomainJudge (used by task_auto_improve) ─────────────

class EtzDomainJudge:
    """DomainJudge pour le loop nocturne — explore EpisteMemory.

    Chesed (ExplorationEngine) génère les hypothèses,
    Gevurah (AutoJudge) évalue via ce judge.
    Le contenu est l'intention active de Netzach.
    """

    def __init__(self, chesed, yesod, lamed, intention_goal: str,
                 sentier_context: dict | None = None):
        self.chesed = chesed
        self.yesod = yesod
        self.lamed = lamed
        self.intention = intention_goal
        self.sentier_context = sentier_context or {}
        self._last_exploration = None
        self._iteration_count = 0
        # Domaines faibles pour rotation — chaque itération explore un domaine différent
        self._weak_domains = list(self.sentier_context.get("weak_domains") or [])
        # Seed domains variés pour diversifier les explorations
        self._seed_domains = [
            "auto_improve", "kabbale", "hitbonenut", "epistememory",
            "sentiers", "partzufim", "olamot", "tzeruf",
        ]
        # Track seen connections to exclude duplicates across iterations
        self._seen_connection_keys: set[str] = set()

    def generate_hypothesis(self, current_state: str) -> str:
        """Chokmah — explorer l'Arbre complet pour trouver des connexions."""
        self._iteration_count += 1

        # Guidance de Lamed : éviter les chemins déjà empruntés
        guidance = None
        try:
            guidance = self.lamed.guide_next_hypothesis(domain="auto_improve")
        except Exception as e:
            log.warning("Lamed guidance failed: %s", e)

        # Chesed explore — contexte enrichi par l'Arbre complet
        context = {"intention": self.intention}
        if guidance and guidance.promising_directions:
            context["directions"] = ", ".join(guidance.promising_directions[:3])
        if guidance and guidance.avoid_patterns:
            context["avoid"] = ", ".join(guidance.avoid_patterns[:3])

        # Sentiers échoués = directions prometteuses d'exploration
        if self.sentier_context.get("failed_sentiers"):
            context["failed_sentiers"] = ", ".join(
                self.sentier_context["failed_sentiers"][:5]
            )
        # Interactions cross-sentiers haut/bas
        if self.sentier_context.get("cross_insights"):
            context["cross_insights"] = "; ".join(
                self.sentier_context["cross_insights"][:3]
            )
        # Zivugim entre Partzufim
        if self.sentier_context.get("zivugim_insights"):
            context["zivugim"] = "; ".join(
                self.sentier_context["zivugim_insights"][:3]
            )

        # ── DIVERSIFICATION : query aléatoire depuis EpisteMemory ──
        random_seed_text = None
        try:
            from pool import get_conn

            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT content, domain FROM epistememory "
                        "WHERE confidence >= 0.5 AND epistemic_status != 'deprecated' "
                        "ORDER BY RANDOM() LIMIT 1"
                    )
                    row = cur.fetchone()
                    if row:
                        random_seed_text = row[0][:200]
        except Exception as e:
            log.warning("Random seed text DB fetch failed: %s", e)

        # Rotation des domaines faibles
        if self._weak_domains:
            focus_domain = self._weak_domains[
                (self._iteration_count - 1) % len(self._weak_domains)
            ]
            context["target_focus"] = f"Focus sur: {focus_domain}"
            target = [focus_domain]
        else:
            if self.sentier_context.get("target_focus"):
                context["target_focus"] = self.sentier_context["target_focus"]
            target = None

        # Query = souvenir aléatoire OU intention avec variation
        if random_seed_text:
            query = random_seed_text
        else:
            query = f"{self.intention} (iter {self._iteration_count})"

        # Rotation du seed_domain
        seed = self._seed_domains[
            (self._iteration_count - 1) % len(self._seed_domains)
        ]

        result = self.chesed.explore(
            query=query,
            seed_domain=seed,
            target_domains=target,
            max_connections=20,  # Fetch more to compensate for filtering
            context=context,
        )
        self._last_exploration = result

        # Filter out already-seen connections
        novel = []
        for c in (result.connections or []):
            key = f"{c.domain_a}|{c.domain_b}|{(c.description or '')[:80]}"
            if key not in self._seen_connection_keys:
                novel.append(c)
                self._seen_connection_keys.add(key)

        if not novel:
            return f"Aucune nouvelle connexion pour '{query[:60]}' (seed={seed}, iter={self._iteration_count})"

        # Update result connections for evaluate() downstream
        result.connections = novel

        # Synthétiser les meilleures nouvelles connexions
        best = sorted(novel,
                      key=lambda c: c.novelty_score * c.relevance_score,
                      reverse=True)[:3]

        parts = []
        for c in best:
            parts.append(
                f"[{c.domain_a}\u2192{c.domain_b}] {c.description} "
                f"(novelty={c.novelty_score:.2f}, relevance={c.relevance_score:.2f})"
            )

        focus_label = target[0] if target else seed
        return (
            f"Exploration '{focus_label}':\n"
            + "\n".join(parts)
        )

    def apply_modification(self, content: str, hypothesis: str) -> str:
        """Yetzirah — enrichir le contenu avec l'hypothèse."""
        return f"{content}\n\n--- Exploration nocturne ---\n{hypothesis}"

    def evaluate(self, original: str, modified: str) -> "DomainScore":
        """Gevurah — évaluer la qualité de l'exploration."""
        from autojudge.models import DomainScore

        if not self._last_exploration or not self._last_exploration.connections:
            return DomainScore(
                quality=0.1,
                metrics={"novelty": 0.0, "relevance": 0.0, "connections": 0},
                explanation="Pas de connexions trouvées",
            )

        avg_nov = self._last_exploration.avg_novelty
        avg_rel = self._last_exploration.avg_relevance
        n_conns = self._last_exploration.total_connections
        n_novel = self._last_exploration.novel_connections

        # Quality = combinaison novelty x relevance
        quality = (avg_nov * 0.6 + avg_rel * 0.4) if n_conns > 0 else 0.0

        return DomainScore(
            quality=quality,
            metrics={
                "novelty": round(avg_nov, 3),
                "relevance": round(avg_rel, 3),
                "connections": n_conns,
                "novel_connections": n_novel,
            },
            explanation=(
                f"{n_conns} connexions ({n_novel} nouvelles), "
                f"novelty={avg_nov:.2f}, relevance={avg_rel:.2f}"
            ),
        )

    def get_loss_description(self) -> str:
        return "Novelty x Relevance des connexions inter-domaines dans EpisteMemory"


# ─── task_auto_improve ─────────────────────────────────────────


def task_auto_improve(tree: dict, full_tree_context: dict | None = None) -> dict:
    """Auto-improve nocturne — Karpathy Loop sur l'Arbre complet.

    Pipeline :
    1. Netzach → intention active
    2. Full Tree (22 sentiers + Zivugim) → contexte enrichi
    3. Chesed (ExplorationEngine) → connexions dans EpisteMemory
    4. Gevurah (AutoJudge) → évalue et filtre via le Karpathy Loop
    5. Lamed (FailureToInsight) → extrait Nitzotzot des rejets
    6. Yesod (EpisteMemory) → stocke les résultats acceptés
    """
    from daemon import load_daemon_config

    cfg = load_daemon_config()
    max_cycles = cfg["auto_improve_max_cycles"]
    timeout = cfg["auto_improve_timeout"]
    novelty_threshold = cfg["novelty_threshold"]

    report = {
        "task": "auto_improve",
        "intention": None,
        "cycles_run": 0,
        "accepted": 0,
        "rejected": 0,
        "nitzotzot": 0,
        "avg_novelty": 0.0,
        "stored_ids": [],
        "early_stop": False,
        "early_stop_reason": None,
        # Métriques Full Tree
        "sentiers_explored": 0,
        "sentiers_success": 0,
        "zivugim_tested": 0,
        "ohr_ratio": None,
        "adam_kadmon_score": None,
        "soul_level": None,
        "nitzotzot_per_cycle": 0,
    }

    netzach = tree.get("netzach")
    chesed = tree.get("chesed")
    gevurah = tree.get("gevurah")
    lamed = tree.get("lamed")
    yesod = tree.get("yesod")

    # Vérifier que tout est disponible
    missing = []
    if not netzach:  missing.append("netzach")
    if not chesed:   missing.append("chesed")
    if not gevurah:  missing.append("gevurah")
    if not lamed:    missing.append("lamed")
    if not yesod:    missing.append("yesod")
    if missing:
        report["error"] = f"Modules manquants: {', '.join(missing)}"
        return report

    # 1. Prendre une intention active
    try:
        active = netzach.db.get_active_intentions()
    except Exception as e:
        report["error"] = f"Impossible de récupérer les intentions: {e}"
        return report

    if not active:
        report["early_stop"] = True
        report["early_stop_reason"] = "Aucune intention active"
        log.info("Auto-improve: aucune intention active, skip")
        return report

    intention = active[0]  # La plus ancienne
    report["intention"] = intention.goal[:100]
    log.info("Auto-improve: intention sélectionnée — '%s'", intention.goal[:80])

    # 1b. Récupérer les 5 domaines les plus faibles de SelfMap → ciblage
    weak_domains = []
    hod = tree.get("hod")
    if hod:
        try:
            # Use whatever model_id exists in the DB
            from selfmap.core import _get_default_model

            all_comp = hod.db.get_all_competences(model_id=_get_default_model())
            # Trier par score croissant, garder ceux avec assez d'évaluations
            evaluated = [c for c in all_comp if c.n_evals > 0]
            evaluated.sort(key=lambda c: c.score)
            weak_domains = [c.domain for c in evaluated[:5]]
            report["weak_domains"] = weak_domains
            log.info("Auto-improve: domaines faibles ciblés — %s", weak_domains)
        except Exception as e:
            log.warning("Auto-improve: impossible de lire SelfMap: %s", e)

    # Enrichir le contexte avec les domaines faibles
    enriched_context = dict(full_tree_context or {})
    if weak_domains:
        enriched_context["weak_domains"] = weak_domains
        enriched_context["target_focus"] = (
            f"Focus sur les domaines faibles: {', '.join(weak_domains)}"
        )

    # 2. Créer le DomainJudge — enrichi par le contexte Full Tree
    judge = EtzDomainJudge(
        chesed=chesed,
        yesod=yesod,
        lamed=lamed,
        intention_goal=intention.goal,
        sentier_context=enriched_context,
    )

    # 3. Lancer le Karpathy Loop via AutoJudge
    def _on_karpathy_iteration(it):
        """Émettre un SSE pour chaque hypothèse testée en temps réel."""
        try:
            from web.events import emit as _emit

            _emit(
                "karpathy_hypothesis",
                iteration=it.iteration,
                hypothesis=it.hypothesis[:200],
                decision=it.decision,
                score=it.domain_score.quality,
                novelty=it.domain_score.metrics.get("novelty", 0.0),
                explanation=it.explanation[:200],
            )
        except Exception as e:
            log.warning("SSE emit AutoJudge failed: %s", e)

    try:
        loop_result = gevurah.run_loop(
            domain_judge=judge,
            content=intention.goal,
            domain_id="auto_improve",
            n_iterations=max_cycles,
            budget_seconds=timeout,
            on_iteration=_on_karpathy_iteration,
        )
    except Exception as e:
        report["error"] = f"Erreur AutoJudge loop: {e}"
        log.error("Auto-improve loop error: %s", e)
        return report

    report["cycles_run"] = loop_result.total
    report["accepted"] = loop_result.accepted
    report["rejected"] = loop_result.rejected

    # 4. Compter les Nitzotzot extraits par LamedBridge (rejets + quarantaines)
    nitzotzot_total = 0
    for it in loop_result.iterations:
        if it.failure_analysis_id and it.decision in ("rejected", "quarantined"):
            try:
                existing = lamed.db.get_insights(it.failure_analysis_id)
                nitzotzot_total += len(existing)
            except Exception as e:
                log.warning("Nitzotzot count failed for %s: %s",
                            it.failure_analysis_id, e)

    report["nitzotzot"] = nitzotzot_total

    # 5. Calculer la novelty moyenne
    novelties = []
    for it in loop_result.iterations:
        nov = it.domain_score.metrics.get("novelty", 0.0)
        novelties.append(nov)

    avg_novelty = sum(novelties) / len(novelties) if novelties else 0.0
    report["avg_novelty"] = round(avg_novelty, 3)

    if avg_novelty < novelty_threshold:
        report["early_stop"] = True
        report["early_stop_reason"] = (
            f"Novelty moyenne ({avg_novelty:.2f}) < seuil ({novelty_threshold})"
        )

    # 6. Stocker les résultats acceptés dans EpisteMemory
    for it in loop_result.iterations:
        if it.decision == "accepted":
            try:
                mem_id = yesod.remember(
                    content=(
                        f"[Auto-improve nocturne] Intention: {intention.goal[:80]}\n"
                        f"Hypothèse: {it.hypothesis}\n"
                        f"Score: {it.domain_score.quality:.2f} — "
                        f"{it.domain_score.explanation}"
                    ),
                    source_sephirah="chesed",
                    confidence=0.5,
                    domain="auto_improve",
                    tags=["auto_improve", "nocturne", "karpathy_loop"],
                    ttl_days=90,
                    source_detail={
                        "source_type": "auto_improve",
                        "intention_id": str(intention.id),
                        "intention_goal": intention.goal[:200],
                        "iteration": it.iteration,
                        "quality": it.domain_score.quality,
                        "metrics": it.domain_score.metrics,
                    },
                )
                report["stored_ids"].append(str(mem_id))
            except Exception as e:
                log.warning("Stockage EpisteMemory échoué: %s", e)

    # 7. Injecter les métriques Full Tree dans le rapport
    if full_tree_context:
        sentiers = full_tree_context.get("sentiers", {})
        report["sentiers_explored"] = sentiers.get("total", 0)
        report["sentiers_success"] = sentiers.get("successes", 0)
        report["zivugim_tested"] = full_tree_context.get(
            "zivugim", {},
        ).get("pairs_tested", 0)
        conv = full_tree_context.get("convergence", {})
        ohr = conv.get("ohr_ratio", {})
        report["ohr_ratio"] = ohr.get("ratio") if isinstance(ohr, dict) else None
        report["adam_kadmon_score"] = conv.get("adam_kadmon_score")
        soul = conv.get("soul_level", {})
        report["soul_level"] = soul.get("level") if isinstance(soul, dict) else None
        report["nitzotzot_per_cycle"] = (
            report["nitzotzot"] / report["cycles_run"]
            if report["cycles_run"] > 0 else 0
        )

    log.info(
        "Auto-improve terminé: %d cycles, %d acceptés, %d rejetés, "
        "%d nitzotzot, novelty=%.2f, sentiers=%d/%d, soul=%s, AK=%.3f",
        report["cycles_run"], report["accepted"], report["rejected"],
        report["nitzotzot"], report["avg_novelty"],
        report["sentiers_success"], report["sentiers_explored"],
        report.get("soul_level", "?"),
        report.get("adam_kadmon_score") or 0.0,
    )

    return report


# ─── task_explore_full_tree ─────────────────────────────────────


def task_explore_full_tree(tree: dict) -> dict:
    """Explorer l'Arbre complet — 22 sentiers, Zivugim, métriques.

    Étape 1 : Exécuter les 22 sentiers (haut ET bas)
    Étape 2 : Tester les Zivugim entre Partzufim
    Étape 3 : Calculer les métriques de convergence

    Retourne un dict utilisable comme context pour le Karpathy Loop.
    """
    from daemon import (
        ALL_SENTIER_NAMES,
        FULL_TREE_TIMEOUT,
        LOWER_SENTIERS,
        SENTIER_TIMEOUT,
        UPPER_SENTIERS,
        ZIVUG_PAIRS,
        _assess_soul,
        _compute_adam_kadmon_score,
        _compute_ohr_ratio,
        _get_nitzotzot_state,
        _init_partzufim,
        load_daemon_config,
    )

    cfg = load_daemon_config()
    report = {
        "task": "full_tree_exploration",
        "sentiers": {
            "total": 22, "successes": 0, "failures": 0, "errors": 0,
            "details": {},
        },
        "zivugim": {"pairs_tested": 0, "results": []},
        "convergence": {},
        # Digest pour le Karpathy Loop
        "failed_sentiers": [],
        "cross_insights": [],
        "zivugim_insights": [],
    }

    partzufim = {}

    # ── Étape 1 : Les 22 sentiers ────────────────────────────
    if cfg.get("sentier_exploration", True):
        try:
            from sentiers import run_sentier, REGISTRY

            tree_start = time.time()
            for name in ALL_SENTIER_NAMES:
                # Timeout global : arrêter si l'exploration dure trop
                if time.time() - tree_start > FULL_TREE_TIMEOUT:
                    log.warning("Full tree timeout (%ds) — %d/%d sentiers",
                                FULL_TREE_TIMEOUT, len(report["sentiers"]["details"]),
                                len(ALL_SENTIER_NAMES))
                    break

                try:
                    entry = REGISTRY[name]
                    # Émettre événement SSE avant chaque sentier
                    try:
                        from web.events import emit as _emit

                        _emit("sentier_traverse", sentier=name, letter=entry["letter"],
                              source=entry["source"], target=entry["target"],
                              status="start")
                        _emit("module_active", module=entry["source"],
                              action=f"sentier_{name}")
                        _emit("module_active", module=entry["target"],
                              action=f"sentier_{name}")
                    except Exception as e:
                        log.warning("SSE emit failed (sentier start): %s", e)

                    # Timeout par sentier pour éviter les blocages LLM
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(run_sentier, name, tree)
                        try:
                            result = future.result(timeout=SENTIER_TIMEOUT)
                        except FuturesTimeoutError:
                            log.warning("Sentier %s TIMEOUT (%ds)", name, SENTIER_TIMEOUT)
                            report["sentiers"]["details"][name] = {
                                "error": f"timeout ({SENTIER_TIMEOUT}s)",
                            }
                            report["sentiers"]["errors"] += 1
                            report["failed_sentiers"].append(name)
                            continue

                    report["sentiers"]["details"][name] = {
                        "letter": entry["letter"],
                        "number": entry["number"],
                        "source": entry["source"],
                        "target": entry["target"],
                        "success": result.success,
                        "mode": result.mode,
                        "message": (result.message or "")[:200],
                    }

                    # Émettre résultat du sentier
                    try:
                        from web.events import emit as _emit

                        _emit("sentier_traverse", sentier=name, letter=entry["letter"],
                              source=entry["source"], target=entry["target"],
                              status="done", success=result.success)
                    except Exception as e:
                        log.warning("SSE emit failed (sentier done): %s", e)

                    if result.success:
                        report["sentiers"]["successes"] += 1
                    else:
                        report["sentiers"]["failures"] += 1
                        report["failed_sentiers"].append(name)
                except Exception as e:
                    report["sentiers"]["details"][name] = {
                        "error": str(e)[:200],
                    }
                    report["sentiers"]["errors"] += 1
                    report["failed_sentiers"].append(name)

            # Cross-sentier : interactions haut/bas via Sephiroth partagées
            from sentiers import REGISTRY as _REG

            upper_ok = {
                n for n in UPPER_SENTIERS
                if report["sentiers"]["details"].get(n, {}).get("success")
            }
            lower_ok = {
                n for n in LOWER_SENTIERS
                if report["sentiers"]["details"].get(n, {}).get("success")
            }
            for u_name in sorted(upper_ok):
                u = _REG[u_name]
                for l_name in sorted(lower_ok):
                    l_entry = _REG[l_name]
                    shared = set()
                    if u["source"] in (l_entry["source"], l_entry["target"]):
                        shared.add(u["source"])
                    if u["target"] in (l_entry["source"], l_entry["target"]):
                        shared.add(u["target"])
                    if shared:
                        report["cross_insights"].append(
                            f"{u_name}({u['letter']})\u2194{l_name}({l_entry['letter']}) "
                            f"via {','.join(sorted(shared))}"
                        )

            log.info(
                "Sentiers: %d/%d OK, %d échecs, %d erreurs, %d cross-insights",
                report["sentiers"]["successes"], report["sentiers"]["total"],
                report["sentiers"]["failures"], report["sentiers"]["errors"],
                len(report["cross_insights"]),
            )
        except Exception as e:
            report["sentiers"]["error"] = str(e)
            log.error("Sentier exploration error: %s", e)

    # ── Étape 2 : Zivugim entre Partzufim ────────────────────
    if cfg.get("zivug_testing", True):
        try:
            partzufim = _init_partzufim(tree)

            for a_name, b_name in ZIVUG_PAIRS:
                a = partzufim.get(a_name)
                b = partzufim.get(b_name)
                if not a or not b:
                    continue

                try:
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(a.interact, b)
                        try:
                            zivug = future.result(timeout=SENTIER_TIMEOUT)
                        except FuturesTimeoutError:
                            log.warning("Zivug %s\u00d7%s TIMEOUT (%ds)",
                                        a_name, b_name, SENTIER_TIMEOUT)
                            report["zivugim"]["results"].append({
                                "pair": f"{a_name}\u00d7{b_name}",
                                "error": f"timeout ({SENTIER_TIMEOUT}s)",
                            })
                            continue

                    zivug_data = {
                        "pair": f"{a_name}\u00d7{b_name}",
                        "success": zivug.success,
                        "orientation": zivug.orientation,
                        "resonance": round(zivug.resonance, 3),
                        "message": (zivug.message or "")[:200],
                    }
                    report["zivugim"]["results"].append(zivug_data)
                    report["zivugim"]["pairs_tested"] += 1

                    if zivug.success:
                        report["zivugim_insights"].append(
                            f"{a_name}\u00d7{b_name}: "
                            f"resonance={zivug.resonance:.2f}, "
                            f"{zivug.orientation}"
                        )
                    else:
                        report["zivugim_insights"].append(
                            f"{a_name}\u00d7{b_name}: "
                            f"FAILED ({zivug.orientation})"
                        )
                except Exception as e:
                    report["zivugim"]["results"].append({
                        "pair": f"{a_name}\u00d7{b_name}",
                        "error": str(e)[:200],
                    })

            log.info(
                "Zivugim: %d paires testées",
                report["zivugim"]["pairs_tested"],
            )
        except Exception as e:
            report["zivugim"]["error"] = str(e)
            log.error("Zivugim error: %s", e)

    # ── Étape 3 : Métriques de convergence ────────────────────
    if cfg.get("convergence_tracking", True):
        try:
            convergence = {}

            # Ohr Pnimi / Ohr Makif
            convergence["ohr_ratio"] = _compute_ohr_ratio()

            # Nitzotzot
            convergence["nitzotzot"] = _get_nitzotzot_state()

            # Adam Kadmon score
            if not partzufim:
                partzufim = _init_partzufim(tree)
            convergence["adam_kadmon_score"] = _compute_adam_kadmon_score(
                tree, partzufim, report["sentiers"],
            )

            # Soul level
            convergence["soul_level"] = _assess_soul(tree, partzufim)

            report["convergence"] = convergence

            log.info(
                "Convergence: ohr=%.3f, nitzotzot=%d (cycle %d), "
                "AK=%.3f, soul=%s",
                convergence.get("ohr_ratio", {}).get("ratio", 0.0),
                convergence.get("nitzotzot", {}).get("total", 0),
                convergence.get("nitzotzot", {}).get("cycle", 0),
                convergence.get("adam_kadmon_score", 0.0),
                convergence.get("soul_level", {}).get("level", "?"),
            )
        except Exception as e:
            report["convergence"]["error"] = str(e)
            log.error("Convergence metrics error: %s", e)

    return report


# ─── task_hitbonenut ─────────────────────────────────────────


def task_hitbonenut(tree: dict) -> dict:
    """Hitbonenut — Session ponctuelle (5 questions).

    Utilisé par `--task hitbonenut` et par le rapport quotidien.
    Le mode continu est géré par HitbonenutDaemonRunner.
    """
    from daemon import _daemon_emit_hitbonenut, _record_hitbonenut_to_beinoni

    report = {
        "task": "hitbonenut",
        "session": None,
        "progress": None,
        "targeted_domain": None,
        "difficulty_scaled": False,
        "novel_question": None,
    }

    try:
        from hitbonenut import HitbonenutEngine

        engine = HitbonenutEngine(
            tree=tree,
            db_url=DB_URL,
            corpus_path=Path(__file__).parent.parent / "hitbonenut_corpus.yaml",
        )

        progress = engine.assess_progress()
        report["progress"] = {
            "overall_score": progress.overall_competence,
            "sessions_total": progress.sessions_count,
            "domains_assessed": len(progress.current_scores),
            "stagnant": progress.stagnant_domains,
            "improving": progress.improving_domains,
        }

        stagnant = progress.stagnant_domains
        difficulty = "progressive"

        if progress.overall_competence > 0.3:
            difficulty = "intermediaire"
            report["difficulty_scaled"] = True
        if progress.overall_competence > 0.6:
            difficulty = "avancee"
            report["difficulty_scaled"] = True

        targeted = None
        if progress.sessions_count >= 3 and stagnant:
            targeted = stagnant[0]
            report["targeted_domain"] = targeted

        try:
            novel_q = engine.generate_novel_question()
            if novel_q:
                report["novel_question"] = {"question": novel_q[:200]}
        except Exception as e:
            log.warning("Hitbonenut: génération novel échouée: %s", e)

        _daemon_emit_hitbonenut("session_start")

        if targeted:
            session = engine.run_targeted(domain=targeted, n=5, budget_seconds=120)
        else:
            session = engine.run_session(n_questions=5, difficulty=difficulty, budget_seconds=120)

        report["session"] = {
            "session_id": str(session.session_id),
            "questions_asked": session.n_questions,
            "questions_answered": len(session.results),
            "avg_score": round(session.avg_score, 3),
            "duration": round(session.duration, 1),
            "domains_covered": session.domains,
        }

        _daemon_emit_hitbonenut("session_end",
                                avg_score=session.avg_score,
                                questions=session.n_questions)

        log.info(
            "Hitbonenut: %d/%d questions, score=%.2f, durée=%.0fs, domaines=%s, ciblé=%s",
            len(session.results), session.n_questions,
            session.avg_score, session.duration,
            ", ".join(session.domains[:5]), targeted or "aucun",
        )

        # ── BeinoniTracker : enregistrer chaque Q/A comme interaction ──
        _record_hitbonenut_to_beinoni(session)

    except ImportError:
        report["error"] = "Module hitbonenut non disponible"
        log.error("Hitbonenut: module non trouvé")
    except Exception as e:
        report["error"] = str(e)
        log.error("Hitbonenut error: %s\n%s", e, traceback.format_exc())

    return report


# ─── task_gevurah_eval ─────────────────────────────────────────


def task_gevurah_eval(tree: dict, batch_size: int = 30) -> dict:
    """Gevurah évalue les réponses Hitbonenut — le jugement de l'Arbre.

    Tire un échantillon de réponses (les plus faibles d'abord),
    les passe au HitbonenutJudge, persiste comme expériences AutoJudge.
    """
    report = {
        "task": "gevurah_eval",
        "evaluated": 0,
        "accepted": 0,
        "rejected": 0,
        "quarantined": 0,
        "avg_quality": 0.0,
        "weakest_domains": [],
    }

    gevurah = tree.get("gevurah")
    if not gevurah:
        report["error"] = "Module gevurah non disponible"
        return report

    try:
        import psycopg2.extras
        from autojudge.domains.hitbonenut import HitbonenutJudge
        from pool import get_conn, init_pool

        # Enregistrer le domaine
        gevurah.register_domain(
            "hitbonenut_eval",
            "Hitbonenut Response Quality",
            "kabbalistic_depth + domain_keywords + structure",
            {"source": "hitbonenut_questions", "batch_size": batch_size},
        )

        init_pool(DB_URL)  # idempotent
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Réponses non encore évaluées par Gevurah
                cur.execute("""
                    SELECT hq.id, hq.question, hq.domain, hq.response, hq.score, hq.kw_score
                    FROM hitbonenut_questions hq
                    WHERE hq.response IS NOT NULL AND hq.response != ''
                    AND NOT EXISTS (
                        SELECT 1 FROM autojudge_experiments ae
                        WHERE ae.original_content = LEFT(hq.question, 500)
                        AND ae.domain_id = 'hitbonenut_eval'
                    )
                    ORDER BY hq.score ASC
                    LIMIT %s
                """, (batch_size,))
                rows = cur.fetchall()

        if not rows:
            report["note"] = "Toutes les questions ont déjà été évaluées"
            return report

        hitbonenut_judge = HitbonenutJudge()
        total_quality = 0.0
        domain_scores: dict[str, list[float]] = {}

        for row in rows:
            question = row["question"]
            response = row["response"] or ""
            domain = row["domain"] or "general"

            hitbonenut_judge.set_context(question, domain)
            metrics = hitbonenut_judge.compute_metrics(response)
            quality = hitbonenut_judge.compute_quality(metrics)

            decision = ("accepted" if quality >= 0.6
                        else "quarantined" if quality >= 0.4
                        else "rejected")

            gevurah.db.create_experiment(
                domain_id="hitbonenut_eval",
                hypothesis=hitbonenut_judge.generate_hypothesis(response),
                original_content=question[:500],
                modified_content=response[:1000],
                score_gevurah=quality,
                score_chesed=metrics["diversity"],
                score_tiferet=metrics["relevance"],
                score_hod=metrics["structure"],
                score_yesod=metrics["kabbalistic_depth"],
                score_overall=quality,
                decision=decision,
                loop_iteration=0,
            )

            total_quality += quality
            domain_scores.setdefault(domain, []).append(quality)

            if decision == "accepted":
                report["accepted"] += 1
            elif decision == "rejected":
                report["rejected"] += 1
            else:
                report["quarantined"] += 1

        report["evaluated"] = len(rows)
        report["avg_quality"] = round(total_quality / len(rows), 3)

        # Domaines les plus faibles
        domain_avgs = {
            d: round(sum(s) / len(s), 3)
            for d, s in domain_scores.items()
        }
        report["weakest_domains"] = sorted(
            domain_avgs.items(), key=lambda x: x[1]
        )[:5]

        log.info(
            "Gevurah eval: %d questions, avg=%.2f, %d accepted, "
            "%d rejected, %d quarantined",
            len(rows), report["avg_quality"],
            report["accepted"], report["rejected"], report["quarantined"],
        )

    except Exception as e:
        report["error"] = str(e)
        log.error("Gevurah eval error: %s", e)

    return report


# ─── Misc exploration tasks ─────────────────────────────────────


def task_dira_birur_stats(tree: dict) -> dict:
    """Dira BeTachtonim + Birur Nogah — stats quotidiennes."""
    report = {
        "task": "dira_birur",
        "dira_count": 0,
        "dira_penetration": 0.0,
        "birur_rate": 0.0,
        "total_birurims": 0,
    }

    yesod = tree.get("yesod")

    # Dira stats
    try:
        from tanya.dira_betachtonim import DiraEngine

        dira = DiraEngine(yesod=yesod)
        stats = dira.assess_dira_state()
        report["dira_count"] = stats.dira_count
        report["dira_penetration"] = round(stats.penetration, 4)
        report["dira_by_source"] = stats.by_source
        report["dira_by_domain"] = stats.by_domain
        log.info("Dira: %d mémoires, pénétration=%.1f%%",
                 stats.dira_count, stats.penetration * 100)
    except Exception as e:
        log.warning("Dira stats failed: %s", e)

    # Birur stats
    try:
        if yesod:
            dira_memories = yesod.recall(
                query="birur nogah nitzutz étincelle",
                limit=200,
                min_confidence=0.0,
            )
            birur_count = sum(
                1 for m in dira_memories
                if hasattr(m, "tags") and m.tags and "birur_nogah" in m.tags
            )
            nitz_memories = yesod.recall(
                query="nitzutz birur_nogah",
                limit=200,
                min_confidence=0.0,
            )
            nitz_birur = sum(
                1 for m in nitz_memories
                if hasattr(m, "tags") and m.tags and "birur_nogah" in m.tags
            )
            report["total_birurims"] = max(birur_count, nitz_birur)
            log.info("Birur: %d birurims historiques", report["total_birurims"])
    except Exception as e:
        log.warning("Birur stats failed: %s", e)

    return report


def task_tzeruf_spatial(tree: dict) -> dict:
    """Tzeruf Spatial — relations geometriques entre mots hebreux."""
    report = {"task": "tzeruf_spatial", "comparisons": 0,
              "parallels": 0, "oppositions": 0, "perpendiculars": 0}
    try:
        from kabbalah.tzeruf_db import get_hebrew_concepts, store_relationship, tzeruf_exists
        from kabbalah.tzeruf_spatial import TzerufSpatial

        ts = TzerufSpatial()
        hebrew_concepts = get_hebrew_concepts(DB_URL, limit=30)

        if len(hebrew_concepts) < 2:
            report["status"] = "not_enough_hebrew_concepts"
            return report

        for i, (c1, w1) in enumerate(hebrew_concepts):
            for c2, w2 in hebrew_concepts[i + 1:]:
                if tzeruf_exists(DB_URL, w1, w2):
                    continue
                try:
                    comparison = ts.compare_words(w1, w2)
                except Exception as e:
                    log.warning("Tzeruf compare_words(%s, %s) failed: %s", w1, w2, e)
                    continue
                if not comparison:
                    continue

                rel = getattr(comparison, "relationship", "similar")
                store_relationship(DB_URL, {
                    "word_a": w1,
                    "word_b": w2,
                    "relationship": rel,
                    "angle": getattr(comparison, "angle", 0.0),
                    "geometric_similarity": getattr(comparison, "geometric_similarity", None),
                    "dominant_direction_a": getattr(comparison, "dominant_direction_a", None),
                    "dominant_direction_b": getattr(comparison, "dominant_direction_b", None),
                })
                report["comparisons"] += 1
                if rel == "parallel":
                    report["parallels"] += 1
                elif rel == "opposed":
                    report["oppositions"] += 1
                elif rel == "perpendicular":
                    report["perpendiculars"] += 1

        log.info(
            "TzerufSpatial: %d comparisons, %d parallels, %d oppositions, %d perpendiculars",
            report["comparisons"], report["parallels"],
            report["oppositions"], report["perpendiculars"],
        )
    except Exception as e:
        report["error"] = str(e)
        log.error("TzerufSpatial error: %s", e)
    return report


def task_masakh_health() -> dict:
    """Masakh — surveillance quotidienne de l'activité de filtrage."""
    report = {
        "task": "masakh_health",
        "masakh_entries_today": 0,
        "avg_tokens_rejected": 0,
        "context_monitor_avg_score": 0,
    }

    try:
        from pool import get_conn

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*), COALESCE(AVG(tokens_rejected), 0),
                           COALESCE(AVG(tokens_before), 0)
                    FROM masakh_log
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                """)
                row = cur.fetchone()
                report["masakh_entries_today"] = row[0]
                report["avg_tokens_rejected"] = round(float(row[1]), 1)
                avg_before = float(row[2])

                if avg_before > 0:
                    report["avg_rejection_ratio"] = round(
                        float(row[1]) / avg_before, 3
                    )

                cur.execute("""
                    SELECT COALESCE(AVG(score_global), 0), COUNT(*)
                    FROM context_monitor_log
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                """)
                mon_row = cur.fetchone()
                report["context_monitor_avg_score"] = round(float(mon_row[0]), 3)
                report["context_monitor_entries"] = mon_row[1]

                cur.execute("""
                    SELECT COUNT(*) FROM reshimot
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                """)
                report["reshimot_today"] = cur.fetchone()[0]

        log.info(
            "Masakh health: %d filtres, avg rejet=%.0f tokens, "
            "monitor score=%.3f, %d reshimot",
            report["masakh_entries_today"],
            report["avg_tokens_rejected"],
            report["context_monitor_avg_score"],
            report.get("reshimot_today", 0),
        )

    except Exception as e:
        report["error"] = str(e)
        log.debug("Masakh health: %s", e)

    return report


def task_sofer_watcher() -> dict:
    """SoferWatcher — scanner les Sifrei Yesod pour YAML nouveaux ou modifiés."""
    report = {"task": "sofer_watcher", "ingested": 0, "embedded": 0, "errors": 0}

    try:
        from sifrei_yesod.pipeline.sofer import Sofer

        sofer = Sofer(DB_URL)
        try:
            results = sofer.scan_and_ingest()
            report["ingested"] = sum(
                r.assertions_upserted for r in results if not r.skipped
            )
            report["errors"] = sum(1 for r in results if r.errors)

            # Generate ML embeddings for new content
            if report["ingested"] > 0:
                from sifrei_yesod.pipeline.embedder import Embedder

                embedder = Embedder(DB_URL)
                try:
                    counts = embedder.embed_all()
                    report["embedded"] = sum(counts.values())
                finally:
                    embedder.close()

            # Generate hybrid embeddings for any missing concepts
            try:
                from kabbalah.embed_sifrei import SifreiYesodEmbedder

                hybrid_embedder = SifreiYesodEmbedder(db_url=DB_URL)
                try:
                    hybrid_stats = hybrid_embedder.embed_new_concepts()
                    report["hybrid_embedded"] = hybrid_stats["embedded"]
                    report["hybrid_errors"] = hybrid_stats["errors"]
                finally:
                    hybrid_embedder.close()
            except Exception as e:
                log.warning("SoferWatcher hybrid embedding: %s", e)
                report["hybrid_error"] = str(e)
        finally:
            sofer.close()
    except Exception as e:
        log.warning("SoferWatcher: %s", e)
        report["error"] = str(e)

    return report


def task_concept_harvest(tree: dict) -> dict:
    """ConceptHarvester — Yesod-Pipeline pour concepts vivants."""
    report = {"task": "concept_harvest"}
    try:
        from daemon import load_state

        from kabbalah.concept_harvester import ConceptHarvester

        ch = ConceptHarvester(db_url=DB_URL)
        state = load_state()
        last_harvest = state.get("last_concept_harvest")
        if isinstance(last_harvest, (int, float)):
            from datetime import datetime, timezone

            last_harvest = datetime.fromtimestamp(last_harvest, tz=timezone.utc)
        result = ch.harvest(last_harvest=last_harvest)
        report.update(result)
        ch.close()
        log.info(
            "ConceptHarvester: %d harvested, %d deduped, %d pruned",
            result.get("harvested", 0),
            result.get("deduped", 0),
            result.get("pruned", 0),
        )
    except Exception as e:
        report["error"] = str(e)
        log.error("ConceptHarvester error: %s", e)
    return report
