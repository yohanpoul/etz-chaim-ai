"""ExplorationEngine — Le cœur de Chesed.

Abraham ouvre la porte à tout — mais sait quand fermer.
Exploration inter-domaines avec sérendipité structurée.

Le cycle Chesed↔Gevurah via Tiferet :
  ExplorationEngine génère des hypothèses
  → AutoJudge les évalue et rejette les mauvaises
  → FailureToInsight apprend des échecs
  → ExplorationEngine utilise cet apprentissage pour mieux explorer

Connexions sephirothiques :
  - Chesed → Gevurah (Teth) : connexions évaluées par AutoJudge
  - Chesed → Tiferet (Vav) : contradictions → DissensuEngine
  - Chesed → Yesod (via Tiferet) : connexions validées → EpisteMemory
  - Chesed ← Hod (SelfMap) : domaines de compétence
  - Chesed ← Lamed (graphe d'échecs) : directions non explorées
"""

from __future__ import annotations

import logging
import time

log = logging.getLogger("etz-daemon")

from explorationengine.analogy_engine import AnalogyEngine
from explorationengine.cross_domain import CrossDomainConnector
from explorationengine.db import ExplorationEngineDB
from explorationengine.models import Connection, ExplorationResult
from explorationengine.novelty_scorer import NoveltyScorer
from explorationengine.serendipity import SerendipityWalker
from omer import get_param

# Omer de Chesed — 7 paramètres de calibration (hardcoded defaults as fallback)
DEFAULT_EXPLORE_BREADTH = 10            # Chesed-dans-Chesed
DEFAULT_NOVELTY_THRESHOLD = 0.3         # Gevurah-dans-Chesed
DEFAULT_BALANCE_BREADTH_DEPTH = 0.5     # Tiferet-dans-Chesed
DEFAULT_MAX_DURATION_SECONDS = 600      # Netzach-dans-Chesed
DEFAULT_EXPLAIN_CONNECTIONS = True       # Hod-dans-Chesed
DEFAULT_PERSIST_ALL_CONNECTIONS = True   # Yesod-dans-Chesed
DEFAULT_OUTPUT_FORMAT = "graph"          # Malkuth-dans-Chesed

_MODULE = "explorationengine"


_UNSET = object()


class ExplorationEngine:
    """Abraham ouvre la porte à tout — mais sait quand fermer.

    Orchestre l'exploration inter-domaines :
    - CrossDomainConnector : trouver des ponts
    - AnalogyEngine : analogies structurelles
    - SerendipityWalker : marche de sérendipité
    - NoveltyScorer : anti-Gamchicoth
    """

    def __init__(
        self,
        db_url: str,
        memory=None,
        selfmap=None,
        autojudge=None,
        domain_knowledge: dict[str, str] | None = None,
        explore_breadth: int = _UNSET,
        novelty_threshold: float = _UNSET,
        balance_breadth_depth: float = _UNSET,
        max_duration_seconds: int = _UNSET,
        explain_connections: bool = _UNSET,
        persist_all_connections: bool = _UNSET,
        output_format: str = _UNSET,
    ):
        self.db = ExplorationEngineDB(db_url)
        self.memory = memory
        self.selfmap = selfmap
        self.autojudge = autojudge
        self.dissensus = None           # Tiferet (injection tardive)
        self.failuretoinsight = None    # Lamed (injection tardive)

        # Omer — DB overrides when caller uses default, explicit values preserved.
        self.explore_breadth = explore_breadth if explore_breadth is not _UNSET else get_param(_MODULE, "explore_breadth", DEFAULT_EXPLORE_BREADTH)
        self.novelty_threshold = novelty_threshold if novelty_threshold is not _UNSET else get_param(_MODULE, "novelty_threshold", DEFAULT_NOVELTY_THRESHOLD)
        self.balance_breadth_depth = balance_breadth_depth if balance_breadth_depth is not _UNSET else get_param(_MODULE, "balance_breadth_depth", DEFAULT_BALANCE_BREADTH_DEPTH)
        self.max_duration_seconds = max_duration_seconds if max_duration_seconds is not _UNSET else get_param(_MODULE, "max_duration_seconds", DEFAULT_MAX_DURATION_SECONDS)
        self.explain_connections = explain_connections if explain_connections is not _UNSET else get_param(_MODULE, "explain_connections", DEFAULT_EXPLAIN_CONNECTIONS)
        self.persist_all_connections = persist_all_connections if persist_all_connections is not _UNSET else get_param(_MODULE, "persist_all_connections", DEFAULT_PERSIST_ALL_CONNECTIONS)
        self.output_format = output_format if output_format is not _UNSET else get_param(_MODULE, "output_format", DEFAULT_OUTPUT_FORMAT)

        # Composants
        self.connector = CrossDomainConnector(domain_knowledge)
        self.analogies = AnalogyEngine()
        self.novelty = NoveltyScorer()
        self.serendipity = SerendipityWalker(self.connector, self.analogies)

    def explore(
        self,
        query: str,
        seed_domain: str,
        target_domains: list[str] | None = None,
        max_connections: int = 50,
        context: dict[str, str] | None = None,
    ) -> ExplorationResult:
        """Exploration inter-domaines à partir d'une question.

        Le cœur de Chesed : trouver des connexions non évidentes
        entre le domaine source et les domaines cibles.

        Args:
            query: question de départ
            seed_domain: domaine de départ
            target_domains: domaines à explorer (auto-détectés si None)
            max_connections: limite de connexions (anti-Gamchicoth)
            context: contexte textuel par domaine

        Returns:
            ExplorationResult avec toutes les connexions trouvées.
        """
        # Garde Tzimtzum — Chesed dormant pendant la contraction
        try:
            from tzimtzum import is_module_active
            if not is_module_active("chesed"):
                log.info("Chesed dormant (Tzimtzum contraction) — explore() skipped")
                return ExplorationResult(
                    connections=[], status="dormant", domains_explored=[]
                )
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)  # Tzimtzum unavailable = module active

        # Identifier les domaines cibles
        domains = target_domains or self._identify_target_domains(query, seed_domain)
        domains = domains[:self.explore_breadth]

        # Créer l'exploration en DB
        exploration = self.db.create_exploration(
            seed_query=query,
            seed_domain=seed_domain,
            target_domains=domains,
            max_connections=max_connections,
            max_duration_seconds=self.max_duration_seconds,
            novelty_threshold=self.novelty_threshold,
        )

        start_time = time.time()
        connections: list[Connection] = []
        status = "completed"

        for domain in domains:
            if domain == seed_domain:
                continue

            # Budget check (anti-Gamchicoth Mamash)
            elapsed = time.time() - start_time
            if elapsed >= self.max_duration_seconds:
                status = "stopped_budget"
                break

            if len(connections) >= max_connections:
                status = "stopped_budget"
                break

            # Trouver des connexions cross-domain
            new_conns = self.connector.find_connections(
                query=query,
                domain_a=seed_domain,
                domain_b=domain,
                context_a=(context or {}).get(seed_domain, ""),
                context_b=(context or {}).get(domain, ""),
            )

            # Aussi chercher des analogies
            analogy_conns = self.analogies.find_analogies(
                concept=query,
                source_domain=seed_domain,
                target_domains=[domain],
            )
            new_conns.extend(analogy_conns)

            # Connexions cachées du Cube de l'Espace
            try:
                from kabbalah.hybrid_retrieval import HybridRetrieval
                retrieval = HybridRetrieval()
                hidden = retrieval.query(query, mode="hidden", top_k=5)
                for h in hidden:
                    cube_conn = Connection(
                        concept_a=query,
                        domain_a=seed_domain,
                        concept_b=h.concept,
                        domain_b=domain,
                        connection_type="cube_hidden",
                        description=(
                            f"Cube de l'Espace : {h.concept} est structurellement "
                            f"lié (kab={h.kab_sim:.3f}) mais sémantiquement distant "
                            f"(ml={h.ml_sim:.3f}). Gap={h.gap:.3f}."
                        ),
                        confidence=min(h.kab_sim, 0.8),
                    )
                    new_conns.append(cube_conn)
            except Exception as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)  # Graceful degradation

            for conn in new_conns:
                # Anti-Gamchicoth Mamash : hard limit par connexion
                if len(connections) >= max_connections:
                    status = "stopped_budget"
                    break

                # Score de nouveauté (anti-Gamchicoth)
                conn.novelty_score = self.novelty.score(conn, connections)

                # Gevurah-dans-Chesed : arrêt si plus rien de nouveau
                if self.novelty.detect_decay(
                    connections + [conn], self.novelty_threshold
                ):
                    status = "stopped_novelty"
                    break

                # Score de pertinence
                conn.relevance_score = self._compute_relevance(conn, query)

                connections.append(conn)

                # Persister dans EpisteMemory
                if self.persist_all_connections and self.memory:
                    try:
                        mem_id = self.memory.remember(
                            content=conn.description,
                            source_sephirah="chesed",
                            confidence=conn.confidence,
                            domain=f"{conn.domain_a}+{conn.domain_b}",
                            tags=["exploration", conn.connection_type],
                            ttl_days=365,
                        )
                        conn.epistememory_id = mem_id
                    except Exception as _exc:

                        import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

                # Persister la connexion en DB
                if self.persist_all_connections:
                    self.db.create_connection(
                        exploration_id=exploration.id,
                        concept_a=conn.concept_a,
                        domain_a=conn.domain_a,
                        concept_b=conn.concept_b,
                        domain_b=conn.domain_b,
                        connection_type=conn.connection_type,
                        description=conn.description,
                        novelty_score=conn.novelty_score,
                        relevance_score=conn.relevance_score,
                        confidence=conn.confidence,
                        epistememory_id=conn.epistememory_id,
                    )

            if status != "completed":
                break

        # Finaliser l'exploration
        novel_count = sum(1 for c in connections if c.novelty_score >= self.novelty_threshold)
        self.db.complete_exploration(
            exploration_id=exploration.id,
            status=status,
            connections_found=len(connections),
            novel_connections=novel_count,
        )

        return ExplorationResult(
            exploration_id=exploration.id,
            connections=connections,
            status=status,
            domains_explored=domains,
        )

    def find_analogies(
        self,
        concept: str,
        source_domain: str,
        target_domains: list[str] | None = None,
    ) -> list[Connection]:
        """Trouver des analogies structurelles dans d'autres domaines."""
        # Garde Tzimtzum — Chesed dormant pendant la contraction
        try:
            from tzimtzum import is_module_active
            if not is_module_active("chesed"):
                log.info("Chesed dormant (Tzimtzum contraction) — find_analogies() skipped")
                return []
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)  # Tzimtzum unavailable = module active

        return self.analogies.find_analogies(
            concept=concept,
            source_domain=source_domain,
            target_domains=target_domains,
        )

    def spatial_route(
        self,
        from_domain: str,
        to_domain: str,
    ) -> list[dict] | None:
        """Route spatiale entre 2 domaines via le Cube de l'Espace.

        Utilise TzerufSpatial pour calculer le chemin optimal
        dans le Cube du Sefer Yetzirah. Les lettres intermédiaires
        indiquent quels modes cognitifs traverser.

        Returns:
            Liste de steps ou None si les domaines ne mappent pas.
        """
        # Garde Tzimtzum — Chesed dormant pendant la contraction
        try:
            from tzimtzum import is_module_active
            if not is_module_active("chesed"):
                log.info("Chesed dormant (Tzimtzum contraction) — spatial_route() skipped")
                return None
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)  # Tzimtzum unavailable = module active

        try:
            from kabbalah.tzeruf_spatial import TzerufSpatial
            ts = TzerufSpatial()
            route = ts.suggest_exploration_route(from_domain, to_domain)
            return route if route else None
        except Exception:
            return None

    def serendipity_walk(
        self,
        start: str,
        start_domain: str,
        n_steps: int = 5,
    ) -> list[Connection]:
        """Marche de sérendipité : chaque pas ouvre un domaine inattendu."""
        # Garde Tzimtzum — Chesed dormant pendant la contraction
        try:
            from tzimtzum import is_module_active
            if not is_module_active("chesed"):
                log.info("Chesed dormant (Tzimtzum contraction) — serendipity_walk() skipped")
                return []
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)  # Tzimtzum unavailable = module active

        return self.serendipity.walk(
            start_concept=start,
            start_domain=start_domain,
            n_steps=n_steps,
        )

    def explore_open_questions(self, max_questions: int = 5) -> list[dict]:
        """Explorer les questions ouvertes de Tiferet (DissensuEngine).

        Chesed → Tiferet (Vav) : les open_questions sont des graines
        d'exploration. Pour chaque question, on cherche des connexions
        inter-domaines qui pourraient apporter l'évidence manquante.

        Si l'exploration trouve une résolution (connexion à haute confiance
        dans le domaine de la question), on marque la question résolue.

        Args:
            max_questions: nombre max de questions à explorer par appel.

        Returns:
            Liste de dicts {question, domain, explored, connections_found,
            resolved, error}.
        """
        # Garde Tzimtzum — Chesed dormant pendant la contraction
        try:
            from tzimtzum import is_module_active
            if not is_module_active("chesed"):
                log.info("Chesed dormant (Tzimtzum contraction) — explore_open_questions() skipped")
                return []
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)  # Tzimtzum unavailable = module active

        if not self.dissensus:
            log.warning("explore_open_questions: dissensus (Tiferet) non connecté")
            return []

        # Récupérer les questions ouvertes triées par priorité
        try:
            open_qs = self.dissensus.db.get_open_questions(unresolved_only=True)
        except Exception as e:
            log.error("explore_open_questions: impossible de lire les open_questions: %s", e)
            return []

        if not open_qs:
            log.info("explore_open_questions: aucune question ouverte")
            return []

        results: list[dict] = []

        for oq in open_qs[:max_questions]:
            entry: dict = {
                "question_id": str(oq.id),
                "question": oq.question[:200],
                "domain": oq.domain,
                "missing_evidence": oq.missing_evidence,
                "explored": False,
                "connections_found": 0,
                "resolved": False,
                "error": None,
            }

            try:
                # Explorer la question dans son domaine
                seed_domain = oq.domain or "general"
                exploration_result = self.explore(
                    query=oq.question,
                    seed_domain=seed_domain,
                    max_connections=10,
                )

                entry["explored"] = True
                entry["connections_found"] = exploration_result.total_connections

                # Si on trouve des connexions à haute confiance et pertinence,
                # considérer la question comme résolue
                strong_connections = [
                    c for c in exploration_result.connections
                    if c.confidence >= 0.7 and c.relevance_score >= 0.5
                ]

                if strong_connections:
                    try:
                        self.dissensus.db.resolve_question(oq.id)
                        entry["resolved"] = True
                        log.info(
                            "explore_open_questions: question résolue — '%s' "
                            "(%d connexions fortes)",
                            oq.question[:60], len(strong_connections),
                        )
                    except Exception as e:
                        log.warning(
                            "explore_open_questions: resolve_question failed: %s", e
                        )

            except Exception as e:
                entry["error"] = str(e)
                log.warning(
                    "explore_open_questions: exploration failed for '%s': %s",
                    oq.question[:60], e,
                )

            results.append(entry)

        log.info(
            "explore_open_questions: %d/%d explorées, %d résolues",
            sum(1 for r in results if r["explored"]),
            len(results),
            sum(1 for r in results if r["resolved"]),
        )

        return results

    def self_diagnose(self) -> dict:
        """Auto-diagnostic de Chesed — les 4 niveaux de Gamchicoth."""
        recent = self.db.get_explorations(limit=10)
        if not recent:
            return {"level": "healthy", "issues": []}

        diagnostics = {"level": "healthy", "issues": []}

        for exp in recent:
            if exp.status == "running":
                continue

            # Vérifier les connexions de cette exploration
            conns = self.db.get_connections(exploration_id=exp.id)

            diag = self.novelty.diagnose(
                connections=[
                    Connection(
                        concept_a=c.concept_a, domain_a=c.domain_a,
                        concept_b=c.concept_b, domain_b=c.domain_b,
                        connection_type=c.connection_type,
                        description=c.description,
                        novelty_score=c.novelty_score or 0,
                    )
                    for c in conns
                ],
                budget_seconds=exp.max_duration_seconds,
                max_connections=exp.max_connections,
                novelty_threshold=exp.novelty_threshold,
            )

            if diag["level"] != "healthy":
                diagnostics = diag
                break

        return diagnostics

    def report(self, exploration_id=None) -> str:
        """Rapport lisible — Malkuth de Chesed."""
        if exploration_id:
            exp = self.db.get_exploration(exploration_id)
            if not exp:
                return "Exploration not found."
            conns = self.db.get_connections(exploration_id=exploration_id)
            return self._format_exploration_report(exp, conns)

        recent = self.db.get_explorations(limit=5)
        diag = self.self_diagnose()

        lines = [
            "=== ExplorationEngine Report (Chesed) ===",
            f"Recent explorations: {len(recent)}",
        ]

        for exp in recent:
            lines.append(
                f"  [{exp.status}] '{exp.seed_query}' from {exp.seed_domain} "
                f"→ {exp.connections_found} connections ({exp.novel_connections} novel)"
            )

        lines.append(f"\nSelf-diagnosis: {diag['level']}")
        if diag["issues"]:
            lines.append("Issues:")
            for issue in diag["issues"]:
                lines.append(f"  - {issue}")

        return "\n".join(lines)

    def _format_exploration_report(self, exp, conns) -> str:
        lines = [
            f"=== Exploration: '{exp.seed_query}' ===",
            f"Seed domain: {exp.seed_domain}",
            f"Target domains: {', '.join(exp.target_domains)}",
            f"Status: {exp.status}",
            f"Connections: {len(conns)} ({exp.novel_connections} novel)",
            "",
        ]
        for c in conns:
            novelty = f" [novelty={c.novelty_score:.2f}]" if c.novelty_score else ""
            lines.append(
                f"  [{c.connection_type}] {c.domain_a}::{c.concept_a} "
                f"↔ {c.domain_b}::{c.concept_b}{novelty}"
            )
            if self.explain_connections:
                lines.append(f"    {c.description}")
        return "\n".join(lines)

    def run_analogy_detection(self, limit: int = 100, skip_llm: bool = False) -> dict:
        """Analyser les connexions récentes et détecter des analogies cross-domain.

        Lit les connexions existantes, détecte des patterns récurrents
        heuristiquement, puis utilise Ollama pour générer des analogies
        structurelles profondes.

        Returns:
            dict avec les résultats de la détection.
        """
        # Garde Tzimtzum — Chesed dormant pendant la contraction
        try:
            from tzimtzum import is_module_active
            if not is_module_active("chesed"):
                log.info("Chesed dormant (Tzimtzum contraction) — run_analogy_detection() skipped")
                return {
                    "heuristic_found": 0, "llm_found": 0,
                    "duplicates_skipped": 0, "stored": 0,
                    "errors": [], "skipped": "dormant",
                }
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)  # Tzimtzum unavailable = module active

        report = {
            "heuristic_found": 0,
            "llm_found": 0,
            "duplicates_skipped": 0,
            "stored": 0,
            "errors": [],
        }

        # 1. Récupérer les connexions récentes
        connections = self.db.get_connections(limit=limit)

        # 1b. Fetch fresh concepts from Yesod-Pipeline for new material
        try:
            from pool import get_conn, init_pool
            _url = self.db.db_url if hasattr(self.db, 'db_url') else "postgresql://localhost/etz_chaim"
            init_pool(_url)  # idempotent
            with get_conn() as _conn:
                with _conn.cursor() as _cur:
                    _cur.execute("""
                        SELECT concept, hebrew_word FROM hybrid_embeddings
                        WHERE harvested_at > NOW() - INTERVAL '7 days'
                          AND status != 'deprecated'
                        ORDER BY harvested_at DESC LIMIT 50
                    """)
                    fresh_concepts = _cur.fetchall()
            report["fresh_concepts"] = len(fresh_concepts)
        except Exception:
            fresh_concepts = []
            report["fresh_concepts"] = 0

        if len(connections) < 2:
            report["errors"].append("Pas assez de connexions pour détecter des analogies")
            return report

        # 2. Détection heuristique
        heuristic_analogies = self.analogies.detect_cross_domain_analogies(connections)
        report["heuristic_found"] = len(heuristic_analogies)

        # 3. Stocker les analogies heuristiques (sans doublon)
        for a in heuristic_analogies:
            if self.db.analogy_exists(a["domain_a"], a["domain_b"], a["pattern"]):
                report["duplicates_skipped"] += 1
                continue
            self.db.create_analogy(
                domain_a=a["domain_a"],
                domain_b=a["domain_b"],
                pattern=a["pattern"],
                explanation=a["explanation"],
                strength=a["strength"],
                source_connection_ids=a.get("source_ids"),
                generated_by="heuristic",
            )
            report["stored"] += 1

        # 4. Générer des analogies LLM pour les paires les plus riches
        if skip_llm:
            return report
        domain_pairs = self._get_rich_domain_pairs(connections, min_conns=2)
        for (da, db), pair_conns in domain_pairs[:5]:  # Top 5 paires
            try:
                llm_analogies = self._llm_analogy(da, db, pair_conns)
                report["llm_found"] += len(llm_analogies)
                for a in llm_analogies:
                    if self.db.analogy_exists(a["domain_a"], a["domain_b"], a["pattern"]):
                        report["duplicates_skipped"] += 1
                        continue
                    self.db.create_analogy(**a)
                    report["stored"] += 1
            except Exception as e:
                report["errors"].append(f"LLM analogy {da}↔{db}: {e}")

        return report

    def _get_rich_domain_pairs(
        self, connections: list[Connection], min_conns: int = 2
    ) -> list[tuple[tuple[str, str], list[Connection]]]:
        """Paires de domaines avec le plus de connexions."""
        pairs: dict[tuple[str, str], list[Connection]] = {}
        for c in connections:
            pair = tuple(sorted([c.domain_a, c.domain_b]))
            pairs.setdefault(pair, []).append(c)
        rich = [(pair, conns) for pair, conns in pairs.items() if len(conns) >= min_conns]
        rich.sort(key=lambda x: len(x[1]), reverse=True)
        return rich

    def _llm_analogy(
        self, domain_a: str, domain_b: str, connections: list[Connection],
    ) -> list[dict]:
        """Utiliser Ollama pour générer des analogies structurelles profondes."""
        try:
            from olamot import ollama_generate
        except ImportError:
            return []

        conn_descriptions = "\n".join(
            f"- [{c.connection_type}] {c.concept_a} ↔ {c.concept_b}: {c.description[:150]}"
            for c in connections[:10]
        )

        prompt = (
            f"Analyse ces connexions entre les domaines '{domain_a}' et '{domain_b}':\n\n"
            f"{conn_descriptions}\n\n"
            f"Identifie 1 à 3 analogies structurelles profondes (pas de simples synonymes).\n"
            f"Pour chaque analogie, donne:\n"
            f"PATTERN: <nom court du pattern>\n"
            f"FORCE: <0.0-1.0>\n"
            f"EXPLICATION: <pourquoi c'est une analogie structurelle, pas superficielle>\n"
        )

        try:
            response, _ = ollama_generate(
                "yetzirah", prompt, timeout=30,
                kavvanah={
                    "intention": f"Trouver des analogies structurelles profondes entre {domain_a} et {domain_b}",
                    "critere_succes": "Analogies qui révèlent une structure commune, pas des synonymes",
                    "anti_pattern": "Ne pas produire d'analogies superficielles ou de simples métaphores",
                },
                domain=f"{domain_a}/{domain_b}",
                context_items=[
                    f"Domaine A: {domain_a}",
                    f"Domaine B: {domain_b}",
                    f"Connexions existantes: {len(connections)}",
                ],
                principles=["Analogie structurelle = bijection préservant les relations, pas simple ressemblance"],
            )
        except Exception as e:
            log.warning("Chesed LLM analogy failed for %s <-> %s: %s", domain_a, domain_b, e)
            if not hasattr(self, "_llm_failures"):
                self._llm_failures = 0
            self._llm_failures += 1
            return []

        return self._parse_llm_analogies(response, domain_a, domain_b)

    @staticmethod
    def _parse_llm_analogies(
        response: str, domain_a: str, domain_b: str,
    ) -> list[dict]:
        """Parser la réponse LLM en analogies structurées."""
        import re
        analogies: list[dict] = []

        blocks = re.split(r'PATTERN:\s*', response)
        for block in blocks[1:]:  # Skip preamble
            pattern_match = re.match(r'(.+?)(?:\n|$)', block.strip())
            if not pattern_match:
                continue
            pattern = pattern_match.group(1).strip()

            force_match = re.search(r'FORCE:\s*([\d.]+)', block)
            strength = float(force_match.group(1)) if force_match else 0.5
            strength = max(0.0, min(1.0, strength))

            expl_match = re.search(r'EXPLICATION:\s*(.+?)(?:\nPATTERN:|\Z)', block, re.DOTALL)
            explanation = expl_match.group(1).strip() if expl_match else pattern

            analogies.append({
                "domain_a": domain_a,
                "domain_b": domain_b,
                "pattern": pattern[:200],
                "explanation": explanation[:500],
                "strength": strength,
                "source_connection_ids": [],
                "generated_by": "llm",
            })

        return analogies

    def _identify_target_domains(self, query: str, seed_domain: str) -> list[str]:
        """Identifier les domaines cibles pour l'exploration.

        Si SelfMap est connecté, utiliser ses compétences.
        Sinon, retourner tous les domaines connus de l'AnalogyEngine.
        """
        known = self.analogies.get_known_domains()
        return [d for d in known if d != seed_domain]

    def _compute_relevance(self, conn: Connection, query: str) -> float:
        """Calculer la pertinence d'une connexion par rapport à la query."""
        import re
        query_words = {w for w in re.findall(r'\b[a-zA-ZÀ-ÿ]{3,}\b', query.lower())}
        desc_words = {w for w in re.findall(r'\b[a-zA-ZÀ-ÿ]{3,}\b', conn.description.lower())}

        if not query_words or not desc_words:
            return 0.5

        overlap = len(query_words & desc_words)
        return min(overlap / max(len(query_words), 1), 1.0)
