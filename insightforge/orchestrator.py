"""Orchestrator — mobilise tous les modules pour une question.

Le chef d'orchestre de Chokmah : chaque module joue sa partie,
l'orchestrator assemble et observe si quelque chose d'inattendu émerge.

7 phases d'orchestration :
  1. Chesed  — Explorer largement (connexions inter-domaines)
  1b. Data-mining — Candidats à partir des données DB existantes
  2. Binah   — Analyser la causalité dans les connexions trouvées
  3. Tiferet — Détecter les tensions entre les claims
  4. Gevurah — Juger la qualité de chaque candidat
  5. Da'at   — Le système se connaît-il assez ?
  6. Yesod   — Qu'est-ce qui est déjà connu ?
  7. Émergence — Y a-t-il quelque chose de NOUVEAU ?
"""

from __future__ import annotations

import logging

from insightforge.models import CandidateInsight, InsightSession

log = logging.getLogger(__name__)


class Orchestrator:
    """Mobilise les 8 modules en séquence autour d'une question.

    Chaque phase consulte un module et enrichit la session.
    L'orchestrator ne décide pas ce qui est un insight —
    il collecte les candidats. Novelty + Validation décident.
    """

    def __init__(
        self,
        epistememory=None,  # Yesod
        selfmap=None,       # Hod
        intentkeeper=None,  # Netzach
        dissensus=None,     # Tiferet
        autojudge=None,     # Gevurah
        exploration=None,   # Chesed
        selfmodel=None,     # Da'at
        causal=None,        # Binah
        db_url: str = "postgresql://localhost/etz_chaim",
    ):
        self.yesod = epistememory
        self.hod = selfmap
        self.netzach = intentkeeper
        self.tiferet = dissensus
        self.gevurah = autojudge
        self.chesed = exploration
        self.daat = selfmodel
        self.binah = causal
        self.db_url = db_url

    def orchestrate(
        self,
        session: InsightSession,
        max_explore: int = 10,
        shov_context: str = "",
    ) -> InsightSession:
        """Exécuter les 7 phases d'orchestration.

        Chaque phase est optionnelle — si le module n'est pas
        disponible, la phase est sautée. Cela permet de tester
        InsightForge avec un sous-ensemble de modules.

        Args:
            shov_context: Contexte Ratzo v'Shov — guidance issue
                des rejets des cycles précédents. Injecté dans
                la session pour que les phases de génération
                évitent les patterns d'échec récurrents.
        """
        if shov_context:
            session.shov_context = shov_context
            session.modules_consulted.append("shov")
        # Phase 1 : Chesed — Explorer largement
        self._phase_explore(session, max_explore)

        # Phase 1b : Data-mining — candidats à partir des données existantes
        self._phase_data_mine(session)

        # Phase 2 : Binah — Analyser la causalité
        self._phase_causal(session)

        # Phase 3 : Tiferet — Détecter les tensions
        self._phase_tensions(session)

        # Phase 4 : Gevurah — Juger la qualité
        self._phase_judge(session)

        # Phase 5 : Da'at — Auto-évaluation
        self._phase_self_assess(session)

        # Phase 6 : Yesod — Connaissances existantes
        self._phase_recall(session)

        return session

    def _phase_explore(self, session: InsightSession, max_explore: int) -> None:
        """Phase 1 : Chesed explore largement."""
        if not self.chesed:
            return
        session.modules_consulted.append("chesed")

        result = self.chesed.explore(
            query=session.question,
            seed_domain=session.domain or "general",
            max_connections=max_explore,
        )

        # Chaque connexion explorée devient un candidat
        if hasattr(result, "connections"):
            for conn in result.connections:
                domain_a = getattr(conn, "domain_a", "")
                domain_b = getattr(conn, "domain_b", "")
                candidate = CandidateInsight(
                    description=getattr(conn, "description", str(conn)),
                    source_module="chesed",
                    domain=domain_b or domain_a or session.domain,
                    confidence=getattr(conn, "novelty_score", 0.5),
                    connects_domains=[domain_a, domain_b],
                )
                session.add_candidate(candidate)

    def _phase_data_mine(self, session: InsightSession) -> None:
        """Phase 1b : Data-mining — candidats à partir des données DB.

        Chesed seul ne génère que des connexions par overlap de vocabulaire.
        Cette phase enrichit la session avec des candidats issus de 3 sources :
          1. Hitbonenut — questions contemplatives diversifiées
          2. FailureToInsight — patterns d'échec, opportunités
          3. EpisteMemory — entrées cross-domain pertinentes

        Si un contexte Shov est présent, les paires de domaines récurrentes
        sont évitées pour réduire le taux de doublons.
        """
        from pool import get_conn

        session.modules_consulted.append("data_mine")
        question_words = set(session.question.lower().split())

        # Shov : extraire les paires de domaines ET les sources à éviter.
        # Le Shov context produit plusieurs lignes de guidance ; ne pas se
        # limiter aux paires de domaines — une source à 190/360 rejets
        # (ex. hitbonenut en Mamash) doit aussi être skippée au niveau
        # data-mine, sinon le prochain cycle re-génère les mêmes rejets.
        shov = getattr(session, "shov_context", "")
        avoided_pairs: set[str] = set()
        avoided_sources: set[str] = set()
        if shov:
            for line in shov.split("\n"):
                if "ÉVITER ces paires" in line:
                    parts = line.split(":")[-1].strip().rstrip(".")
                    for pair in parts.split(","):
                        avoided_pairs.add(pair.strip())
                elif "ÉVITER ou diversifier cette source" in line:
                    # Parse "Source 'hitbonenut' : 190 rejets — ÉVITER ..."
                    try:
                        src = line.split("'")[1]
                        avoided_sources.add(src)
                    except IndexError as _exc:

                        import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
        if avoided_sources:
            log.info("Shov: sources évitées ce cycle: %s", sorted(avoided_sources))

        try:
          with get_conn() as conn:
            cur = conn.cursor()

            # --- 1. Hitbonenut : questions proches de la question posée ---
            if "hitbonenut" in avoided_sources:
                log.debug("Shov: skip hitbonenut source this cycle")
                cur.execute("SELECT NULL WHERE FALSE")
            else:
                cur.execute("""
                SELECT question, response, domain
                FROM hitbonenut_questions
                WHERE response IS NOT NULL AND length(response) > 50
                ORDER BY created_at DESC
                LIMIT 50
            """)
            for q, response, domain in cur.fetchall():
                # Pertinence : overlap de mots entre la question forge et la Q hitbonenut
                q_words = set(q.lower().split())
                overlap = question_words & q_words
                if len(overlap) >= 2 or (domain and domain in session.question.lower()):
                    desc = f"Hitbonenut insight: {q} — {response[:200]}"
                    candidate = CandidateInsight(
                        description=desc,
                        source_module="hitbonenut",
                        domain=domain or "contemplation",
                        confidence=0.5,
                        connects_domains=[domain or "contemplation", session.domain or "general"],
                    )
                    session.add_candidate(candidate)

            # --- 2. FTI : patterns d'échec et opportunités ---
            if "failuretoinsight" in avoided_sources:
                log.debug("Shov: skip failuretoinsight source this cycle")
                cur.execute("SELECT NULL WHERE FALSE")
            else:
                cur.execute("""
                SELECT content, insight_type, domain, confidence
                FROM failuretoinsight_insights
                WHERE insight_type IN ('opportunity', 'pattern', 'warning')
                ORDER BY created_at DESC
                LIMIT 20
            """)
            for content, itype, domain, conf in cur.fetchall():
                content_words = set(content.lower().split())
                overlap = question_words & content_words
                # Les FTI sont toujours pertinents — c'est de l'apprentissage par échec
                if len(overlap) >= 1 or itype == "opportunity":
                    desc = f"FTI {itype}: {content[:300]}"
                    candidate = CandidateInsight(
                        description=desc,
                        source_module="failuretoinsight",
                        domain=domain or "failure_analysis",
                        confidence=conf or 0.4,
                        connects_domains=[domain or "failure_analysis", session.domain or "general"],
                    )
                    session.add_candidate(candidate)

            # --- 3. EpisteMemory : entrées cross-domain ---
            # Trouver les domaines les plus actifs
            if "data_mine" in avoided_sources:
                log.debug("Shov: skip data_mine cross-domain this cycle")
                top_domains = []
            else:
                cur.execute("""
                SELECT domain, COUNT(*) as cnt
                FROM epistememory
                WHERE domain IS NOT NULL AND domain <> ''
                  AND epistemic_status <> 'deprecated'
                GROUP BY domain
                HAVING COUNT(*) >= 3
                ORDER BY cnt DESC
                LIMIT 5
            """)
                top_domains = [r[0] for r in cur.fetchall()]

            # Chercher des entrées à haute confiance dans des domaines différents
            # qui partagent des mots-clés avec la question
            if top_domains:
                placeholders = ",".join(["%s"] * len(top_domains))
                cur.execute(f"""
                    SELECT content, domain, confidence, source_sephirah
                    FROM epistememory
                    WHERE domain IN ({placeholders})
                      AND confidence >= 0.5
                      AND epistemic_status <> 'deprecated'
                    ORDER BY confidence DESC
                    LIMIT 100
                """, top_domains)

                # Grouper par domaine pour détecter les croisements
                by_domain: dict[str, list[tuple]] = {}
                for content, domain, conf, source in cur.fetchall():
                    by_domain.setdefault(domain, []).append((content, conf, source))

                # Générer des candidats cross-domain
                domain_list = list(by_domain.keys())
                for i, d1 in enumerate(domain_list):
                    for d2 in domain_list[i + 1:]:
                        # Shov : skip les paires de domaines récurrentes rejetées
                        pair_key = f"{d1}↔{d2}"
                        pair_key_rev = f"{d2}↔{d1}"
                        if pair_key in avoided_pairs or pair_key_rev in avoided_pairs:
                            continue
                        # Prendre la meilleure entrée de chaque domaine
                        e1 = by_domain[d1][0]
                        e2 = by_domain[d2][0]
                        desc = (
                            f"Cross-domain ({d1} × {d2}): "
                            f"[{d1}] {e1[0][:150]} ↔ "
                            f"[{d2}] {e2[0][:150]}"
                        )
                        avg_conf = (e1[1] + e2[1]) / 2
                        candidate = CandidateInsight(
                            description=desc,
                            source_module="data_mine",
                            domain=f"{d1}+{d2}",
                            confidence=avg_conf * 0.8,  # Discount car connexion heuristique
                            connects_domains=[d1, d2],
                        )
                        session.add_candidate(candidate)

            cur.close()

        except Exception as e:
            log.warning("Data-mining phase failed: %s", e)

    def _phase_causal(self, session: InsightSession) -> None:
        """Phase 2 : Binah vérifie la causalité des candidats."""
        if not self.binah:
            return
        session.modules_consulted.append("binah")

        for candidate in session.surviving_candidates():
            # Tenter une analyse causale si le candidat décrit une relation
            assessment = self.binah.check_claim(
                cause=session.question,
                effect=candidate.description,
                domain=session.domain,
            )
            # Le claim passe la vérification causale ?
            if assessment.claim.evidence_level != "correlation_only":
                candidate.binah_validated = True
            else:
                # Pas rejeté — juste non validé par Binah
                candidate.binah_validated = False

    def _phase_tensions(self, session: InsightSession) -> None:
        """Phase 3 : Tiferet cherche les tensions entre les candidats."""
        if not self.tiferet:
            return
        session.modules_consulted.append("tiferet")
        # Les tensions entre candidats peuvent révéler de nouveaux insights

    def _phase_judge(self, session: InsightSession) -> None:
        """Phase 4 : Gevurah juge la qualité."""
        if not self.gevurah:
            return
        session.modules_consulted.append("gevurah")
        # AutoJudge évalue chaque candidat survivant

    def _phase_self_assess(self, session: InsightSession) -> None:
        """Phase 5 : Da'at — le système est-il compétent ici ?

        Sprint 8b fix 3 : ne pose PLUS `daat_validated` ici. Ce flag
        doit refléter le résultat de la triple validation exécutée plus
        tard (core.py:_persist_candidates). Poser le flag ici produisait
        une asymétrie en DB (237 rows avec daat_validated=True mais
        0 rows binah_validated/gevurah_validated=True) — la requête
        triple-AND du daemon ne matchait donc jamais rien.
        La phase reste utile pour `modules_consulted` et pour alimenter
        `session.question` côté Da'at.
        """
        if not self.daat:
            return
        session.modules_consulted.append("daat")
        # Appel signalant à Da'at qu'il est consulté (predict_error peut
        # logger / compter ces sessions côté SelfModel).
        self.daat.predict_error(session.question)

    def _phase_recall(self, session: InsightSession) -> None:
        """Phase 6 : Yesod — qu'est-ce qui est déjà connu ?"""
        if not self.yesod:
            return
        session.modules_consulted.append("yesod")

    def modules_available(self) -> list[str]:
        """Liste des modules disponibles."""
        available = []
        if self.yesod:
            available.append("yesod")
        if self.hod:
            available.append("hod")
        if self.netzach:
            available.append("netzach")
        if self.tiferet:
            available.append("tiferet")
        if self.gevurah:
            available.append("gevurah")
        if self.chesed:
            available.append("chesed")
        if self.daat:
            available.append("daat")
        if self.binah:
            available.append("binah")
        return available
