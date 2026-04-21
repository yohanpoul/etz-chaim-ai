"""InsightForge — le cœur de Chokmah.

חָכְמָה — Le point (nekudah) sans dimension. Le flash du Yod (י).
Chokmah ne se construit pas — elle APPARAÎT.

InsightForge orchestre toutes les composantes :
  - Orchestrator : mobilise les 8 modules en séquence
  - NoveltyAssessor : évalue si un insight est genuinement nouveau
  - InsightValidator : triple validation anti-Ghagiel
  - EmergenceDetector : détecte les propriétés émergentes

Connexions sephirothiques :
  Chokmah ← Tous les 8 modules inférieurs
  Chokmah → Keter (l'horizon — Ratzon, la volonté)

Anti-Ghagiel : 4 niveaux (Nogah, Ruach, Anan, Mamash).
"""

from __future__ import annotations

import logging

from insightforge.db import InsightDB
from insightforge.emergence_detector import EmergenceDetector
from insightforge.insight_validator import InsightValidator
from insightforge.models import (
    CandidateInsight,
    InsightSession,
    InsightValidation,
    NoveltyAssessment,
)
from insightforge.novelty_assessor import NoveltyAssessor
from insightforge.orchestrator import Orchestrator
from insightforge.ratzo_v_shov import RatzoVShov
from omer import get_param

log = logging.getLogger(__name__)

# Omer de Chokmah — 7 paramètres de calibration (hardcoded defaults as fallback)
DEFAULT_MIN_NOVELTY_SCORE = 0.45         # Chesed-dans-Chokmah : seuil nouveauté (abaissé de 0.7 — Tikkun Ghagiel)
DEFAULT_MAX_INSIGHTS_PER_SESSION = 20    # Gevurah-dans-Chokmah : anti-inflation (relevé de 5)
DEFAULT_REQUIRE_CAUSAL = True            # Binah-dans-Chokmah : validation causale
DEFAULT_REQUIRE_SELFMODEL = True         # Da'at-dans-Chokmah : check SelfModel
DEFAULT_MIN_MODULES_CONSULTED = 5        # Tiferet-dans-Chokmah : minimum modules
DEFAULT_HALLUCINATION_TRIPLE = True      # Anti-Ghagiel : TOUJOURS triple validation (binah+gevurah+daat)
DEFAULT_STORE_NON_INSIGHTS = True        # Hod-dans-Chokmah : stocker les rejetés

_MODULE = "insightforge"
_UNSET = object()


class InsightForge:
    """Chokmah — le point d'où tout découle.

    Pas un programme — une expérience. Mobilise les 8 modules
    inférieurs autour d'une question ouverte et observe si
    quelque chose de genuinement NOUVEAU émerge.
    """

    def __init__(
        self,
        db_url: str,
        # Les 8 modules
        epistememory=None,    # Yesod
        selfmap=None,         # Hod
        intentkeeper=None,    # Netzach
        dissensus=None,       # Tiferet
        autojudge=None,       # Gevurah
        exploration=None,     # Chesed
        selfmodel=None,       # Da'at
        causal=None,          # Binah
        # Omer — calibration
        min_novelty_score: float = _UNSET,
        max_insights_per_session: int = _UNSET,
        require_causal_validation: bool = _UNSET,
        require_selfmodel_check: bool = _UNSET,
        min_modules_consulted: int = _UNSET,
        hallucination_triple_check: bool = _UNSET,
        store_non_insights: bool = _UNSET,
    ):
        self.db = InsightDB(db_url)

        # Modules
        self.yesod = epistememory
        self.hod = selfmap
        self.netzach = intentkeeper
        self.tiferet = dissensus
        self.gevurah = autojudge
        self.chesed = exploration
        self.daat = selfmodel
        self.binah = causal

        # Omer — DB overrides when caller uses default, explicit values preserved.
        self.min_novelty_score = min_novelty_score if min_novelty_score is not _UNSET else get_param(_MODULE, "min_novelty_score", DEFAULT_MIN_NOVELTY_SCORE)
        self.max_insights = max_insights_per_session if max_insights_per_session is not _UNSET else get_param(_MODULE, "max_insights_per_session", DEFAULT_MAX_INSIGHTS_PER_SESSION)
        self.require_causal = require_causal_validation if require_causal_validation is not _UNSET else get_param(_MODULE, "require_causal_validation", DEFAULT_REQUIRE_CAUSAL)
        self.require_selfmodel = require_selfmodel_check if require_selfmodel_check is not _UNSET else get_param(_MODULE, "require_selfmodel_check", DEFAULT_REQUIRE_SELFMODEL)
        self.min_modules = min_modules_consulted if min_modules_consulted is not _UNSET else get_param(_MODULE, "min_modules_consulted", DEFAULT_MIN_MODULES_CONSULTED)
        self.hallucination_triple = hallucination_triple_check if hallucination_triple_check is not _UNSET else get_param(_MODULE, "hallucination_triple_check", DEFAULT_HALLUCINATION_TRIPLE)
        self.store_non_insights = store_non_insights if store_non_insights is not _UNSET else get_param(_MODULE, "store_non_insights", DEFAULT_STORE_NON_INSIGHTS)

        # Composants internes
        self.orchestrator = Orchestrator(
            epistememory=epistememory,
            selfmap=selfmap,
            intentkeeper=intentkeeper,
            dissensus=dissensus,
            autojudge=autojudge,
            exploration=exploration,
            selfmodel=selfmodel,
            causal=causal,
            db_url=db_url,
        )

        self.novelty = NoveltyAssessor(
            min_novelty=self.min_novelty_score,
        )

        # Sprint 6.x — BinahGates (Binah haute, 5 Motzaot ha-Peh).
        # Fallback ciblé sur correlation_only faible pour synthèses
        # conceptuelles non-causales (hitbonenut).
        from insightforge.binah_gates import BinahGates

        self.validator = InsightValidator(
            binah=causal,
            binah_gates=BinahGates(),
            gevurah=autojudge,
            daat=selfmodel,
            yesod=epistememory,
            hod=selfmap,
            tiferet=dissensus,
            require_triple=self.hallucination_triple,
        )

        self.emergence = EmergenceDetector()
        self.ratzo_v_shov = RatzoVShov(db_url)

    def forge(
        self,
        question: str,
        domain: str = "",
        max_explore: int = 10,
        shov_context: str = "",
    ) -> InsightSession:
        """Mobiliser tous les degrés autour d'une question ouverte.

        Le processus complet :
          0. Shov — contexte issu des rejets précédents (Ratzo v'Shov)
          1. Orchestration (7 phases via les 8 modules)
          2. Évaluation de la nouveauté
          3. Triple validation
          4. Détection d'émergence
          5. Décision finale
          6. Ratzo — analyse des rejets pour le cycle suivant

        Returns:
            InsightSession avec tous les résultats.
        """
        session = InsightSession(question=question, domain=domain)

        # --- Phase 0 : Shov — injecter le contexte des rejets précédents ---
        if not shov_context:
            try:
                shov_context = self.ratzo_v_shov.get_shov_context_for_next_cycle()
            except Exception as e:
                log.warning("Shov context fetch failed: %s", e, exc_info=True)
                shov_context = ""
        if shov_context:
            log.info(
                "Shov: contexte actif (%d lignes) — appliqué au cycle",
                shov_context.count("\n") + 1,
            )

        # --- Phase 1 : Orchestration ---
        session = self.orchestrator.orchestrate(
            session, max_explore=max_explore, shov_context=shov_context,
        )

        # Vérifier le minimum de modules consultés
        if len(session.modules_consulted) < self.min_modules:
            session.pearl_level = "association"
            # Pas assez de modules — on continue mais on note

        # --- Phase 2 : Évaluation de la nouveauté ---
        existing_knowledge = self._gather_existing_knowledge(question)
        past_insights = self._gather_past_insights()

        self.novelty.existing_knowledge = existing_knowledge
        self.novelty.past_insights = past_insights

        candidates = session.surviving_candidates()
        novelty_assessments = self.novelty.assess_batch(candidates)

        # --- Phase 3 : Triple validation des candidats "nouveaux" ---
        insights_found = 0

        for candidate, novelty_result in zip(candidates, novelty_assessments):
            session.novelty_assessments.append(novelty_result)

            if not novelty_result.is_genuinely_new:
                # Ibur: incubate borderline candidates instead of rejecting
                if 0.35 <= novelty_result.novelty_score < 0.45:
                    candidate.status = "incubating"
                    if not hasattr(session, 'incubating_candidates'):
                        session.incubating_candidates = []
                    session.incubating_candidates.append(candidate)
                    continue
                reason = novelty_result.reasoning
                session.reject_candidate(candidate, f"Not novel: {reason}")
                continue

            # Anti-inflation : limiter le nombre d'insights par session
            if insights_found >= self.max_insights:
                session.defer_candidate(
                    candidate,
                    f"Max insights reached ({self.max_insights})",
                )
                continue

            # Triple validation
            validation = self.validator.validate(candidate, domain)
            session.validations.append(validation)

            # Sprint 8b fix 3 — propager les 3 flags individuels quelle
            # que soit l'issue globale. Sans cela, les candidates
            # rejetés restaient à False même si un des 3 gates était
            # passé, ce qui cassait les diagnostics par gate.
            candidate.binah_validated = validation.binah_ok
            candidate.gevurah_validated = validation.gevurah_ok
            candidate.daat_validated = validation.daat_ok

            if validation.is_valid:
                session.mark_as_insight(candidate, novelty_result, validation)
                insights_found += 1
            else:
                reason_parts = []
                if not validation.binah_ok:
                    reason_parts.append(f"Binah: {validation.binah_detail}")
                if not validation.gevurah_ok:
                    reason_parts.append(f"Gevurah: {validation.gevurah_detail}")
                if not validation.daat_ok:
                    reason_parts.append(f"Da'at: {validation.daat_detail}")
                session.reject_candidate(
                    candidate,
                    "Triple validation failed: " + "; ".join(reason_parts),
                )

        # --- Phase 4 : Détection d'émergence ---
        emergence_signals = self.emergence.detect(session)
        session.emergence_signals = emergence_signals

        # Déterminer le pearl_level de la session
        session.pearl_level = self._determine_pearl_level(session)

        # Compléter la session
        session.complete()

        # --- Persister ---
        saved = self.db.save_session(session)
        session.id = saved.id
        session.created_at = saved.created_at
        self._persist_candidates(session)

        # --- Phase 6 : Ratzo — analyser les rejets pour le prochain cycle ---
        try:
            self._ratzo_result = self.ratzo_v_shov.ratzo_cycle(session.id)
        except Exception as e:
            log.warning("Ratzo cycle failed (session %s): %s", session.id, e, exc_info=True)
            self._ratzo_result = None

        return session

    def assess_novelty(
        self, candidate: CandidateInsight,
    ) -> NoveltyAssessment:
        """Évaluer la nouveauté d'un candidat seul."""
        return self.novelty.assess(candidate)

    def validate_insight(
        self, candidate: CandidateInsight, domain: str = "",
    ) -> InsightValidation:
        """Valider un candidat — triple validation."""
        return self.validator.validate(candidate, domain)

    def self_diagnose(self) -> dict:
        """Auto-diagnostic — les 4 niveaux de Ghagiel.

        Vérifie les sessions récentes pour les anti-patterns :
          Nogah : trop d'insights (>50% des candidats passent)
          Ruach : insights en boucle (mêmes insights qui reviennent)
          Anan  : hallucination marquée comme insight
          Mamash : aucun insight (blocage créatif)
        """
        sessions = self.db.get_sessions(limit=10)
        if not sessions:
            return {"level": "healthy", "issues": []}

        issues: list[str] = []

        for session in sessions:
            total = session.total_candidates
            found = session.insights_found
            rejected = session.rejected_count

            # Nogah — inflation (>50% des candidats passent)
            if total > 0 and found / total > 0.5:
                issues.append(
                    f"Ghagiel-Nogah: session '{session.question[:40]}' — "
                    f"{found}/{total} candidates passed ({found/total:.0%}), "
                    "insight inflation suspected"
                )

            # Mamash — aucun insight malgré des candidats
            if total > 3 and found == 0:
                issues.append(
                    f"Ghagiel-Mamash: session '{session.question[:40]}' — "
                    f"{total} candidates, 0 insights — creative block"
                )

        # Ruach — doublons entre sessions
        all_insights = self._gather_past_insights()
        if len(all_insights) != len(set(all_insights)):
            issues.append(
                "Ghagiel-Ruach: duplicate insights detected across sessions"
            )

        # Anan — insights à haute confiance non triple-validés
        for session in sessions:
            if session.id:
                candidates = self.db.get_candidates(
                    session.id, status="insight",
                )
                for c in candidates:
                    triple = (
                        c.binah_validated
                        and c.gevurah_validated
                        and c.daat_validated
                    )
                    if not triple and c.confidence >= 0.7:
                        issues.append(
                            f"Ghagiel-Anan: '{c.description[:40]}' — "
                            "high confidence but not triple-validated, "
                            "possible hallucination"
                        )

        # Déterminer le niveau
        if not issues:
            level = "healthy"
        elif any("Mamash" in i for i in issues):
            level = "mamash"
        elif any("Anan" in i for i in issues):
            level = "anan"
        elif any("Ruach" in i for i in issues):
            level = "ruach"
        else:
            level = "nogah"

        return {"level": level, "issues": issues}

    def report(self) -> str:
        """Rapport lisible — Malkuth de Chokmah."""
        sessions = self.db.get_sessions(limit=5)
        diag = self.self_diagnose()
        modules = self.orchestrator.modules_available()

        lines = [
            "=== InsightForge Report (Chokmah) ===",
            f"Modules available: {len(modules)}/8 ({', '.join(modules)})",
            f"Recent sessions: {len(sessions)}",
        ]

        for session in sessions:
            em = "!" if self.emergence.has_emergence(session) else " "
            lines.append(
                f"  [{em}] '{session.question[:50]}' — "
                f"{session.insights_found} insights / "
                f"{session.total_candidates} candidates "
                f"(Pearl: {session.pearl_level})"
            )

        # Résumé global
        total_insights = sum(s.insights_found for s in sessions)
        total_candidates = sum(s.total_candidates for s in sessions)
        if total_candidates > 0:
            rate = total_insights / total_candidates
            lines.append(
                f"\nInsight rate: {total_insights}/{total_candidates} "
                f"({rate:.0%})"
            )
            if rate > 0.5:
                lines.append("  ⚠ Rate > 50% — Ghagiel-Nogah risk")
            elif rate == 0 and total_candidates > 5:
                lines.append("  ⚠ Rate = 0% — Ghagiel-Mamash risk")

        lines.append(f"\nSelf-diagnosis: {diag['level']}")
        if diag["issues"]:
            lines.append("Issues:")
            for issue in diag["issues"]:
                lines.append(f"  - {issue}")

        lines.append(f"\nOmer calibration:")
        lines.append(f"  min_novelty_score: {self.min_novelty_score}")
        lines.append(f"  max_insights_per_session: {self.max_insights}")
        lines.append(f"  require_causal_validation: {self.require_causal}")
        lines.append(f"  require_selfmodel_check: {self.require_selfmodel}")
        lines.append(f"  min_modules_consulted: {self.min_modules}")
        lines.append(f"  hallucination_triple_check: {self.hallucination_triple}")
        lines.append(f"  store_non_insights: {self.store_non_insights}")

        return "\n".join(lines)

    # --- Helpers privés ---

    def _gather_existing_knowledge(self, question: str) -> list[str]:
        """Rassembler les connaissances existantes (Yesod).

        Limité à 30 entrées les plus pertinentes pour éviter que le
        corpus ne grandisse indéfiniment et ne bloque le filtre de novelty
        (vocabulaire kabbalistique partagé → faux positifs Jaccard).
        """
        if not self.yesod:
            return []
        try:
            results = self.yesod.recall(question, min_confidence=0.3, limit=30)
            if isinstance(results, list):
                return [
                    getattr(r, "content", str(r)) for r in results[:30]
                ]
            return []
        except Exception:
            return []

    def _gather_past_insights(self) -> list[str]:
        """Rassembler les insights passés pour dédup.

        Limité aux 5 dernières sessions — au-delà, les insights
        sont suffisamment différents pour que le Jaccard ne les confonde pas.
        """
        sessions = self.db.get_sessions(limit=5)
        past: list[str] = []
        for session in sessions:
            if session.id:
                candidates = self.db.get_candidates(
                    session.id, status="insight",
                )
                past.extend(c.description for c in candidates)
        return past

    def _determine_pearl_level(self, session: InsightSession) -> str:
        """Déterminer le Pearl level de la session.

        Basé sur le plus haut niveau atteint par les insights validés.
        """
        if not session.validated_insights:
            return "association"

        has_causal = any(
            c.binah_validated for c in session.validated_insights
        )
        has_triple = any(
            c.binah_validated and c.gevurah_validated and c.daat_validated
            for c in session.validated_insights
        )

        if has_triple:
            return "counterfactual"
        if has_causal:
            return "intervention"
        return "association"

    def _persist_candidates(self, session: InsightSession) -> None:
        """Persister les candidats et évaluations.

        חָכְמָה → יְסוֹד — Les insights validés descendent dans la mémoire
        fondamentale pour enrichir les futures requêtes. Sans cette boucle,
        Chokmah génère puis oublie.
        """
        if not session.id:
            return

        # Tous les candidats (insights + rejetés + pending + incubating + survivants).
        # Sprint 8b fix 4 : les candidats borderline marqués 'incubating' par
        # assess_novelty étaient jamais persistés car absents de cette liste
        # (et leur INSERT était rejeté par la contrainte CHECK).
        incubating = getattr(session, "incubating_candidates", []) or []
        all_candidates = (
            session.validated_insights
            + session.rejected
            + session.pending
            + incubating
            + session.surviving_candidates()
        )

        for candidate in all_candidates:
            if candidate.status == "rejected" and not self.store_non_insights:
                continue
            candidate.session_id = session.id
            saved = self.db.save_candidate(candidate)

            # Sauver les évaluations de nouveauté associées
            for novelty in session.novelty_assessments:
                if saved.id:
                    novelty.candidate_id = saved.id
                    self.db.save_novelty(novelty)
                    break  # Une évaluation par candidat

        # ── Boucle Chokmah → Yesod : persister les insights validés ──
        if self.yesod and session.validated_insights:
            for insight in session.validated_insights:
                try:
                    self.yesod.remember(
                        content=f"[Insight Chokmah] {insight.description}",
                        source_sephirah="chokmah",
                        confidence=min(0.85, 0.5 + insight.novelty_score * 0.5),
                        domain=insight.domain or "insight",
                        tags=["insight", "chokmah", "validated"],
                    )
                except Exception as _exc:

                    import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)  # Ne pas bloquer la persistance principale

    def close(self):
        """Fermer la connexion DB."""
        self.db.close()
