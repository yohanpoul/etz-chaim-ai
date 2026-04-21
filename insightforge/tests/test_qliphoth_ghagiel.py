"""Tests anti-Ghagiel — les 4 niveaux de Qliphoth de Chokmah.

Ghagiel = les Obstructeurs. Le danger de Chokmah : confondre
l'hallucination avec l'insight.

4 niveaux :
  Nogah  — insight inflation (>50% des candidats passent)
  Ruach  — insights en boucle (dédup sémantique)
  Anan   — hallucination marquée comme insight
  Mamash — blocage créatif (aucun insight)
"""

import pytest

from insightforge.core import InsightForge
from insightforge.emergence_detector import EmergenceDetector
from insightforge.insight_validator import InsightValidator
from insightforge.models import (
    CandidateInsight,
    EmergenceSignal,
    InsightSession,
    InsightValidation,
    NoveltyAssessment,
)
from insightforge.novelty_assessor import NoveltyAssessor

from .conftest import (
    StubCausal,
    StubConnection,
    StubExploration,
    StubSelfModel,
    StubAutoJudge,
    StubEpisteMemory,
    StubSelfMap,
    StubDissensus,
    StubIntentKeeper,
    TEST_DB_URL,
)


# ════════════════════════════════════════════════
# 1. Nogah — Insight inflation
# ════════════════════════════════════════════════

class TestNogah:
    """Trop d'insights = suspicion d'inflation.
    Anti-pattern : plus de 50% des candidats sont marqués 'insight'.
    """

    def test_max_insights_enforced(self):
        """Le paramètre max_insights_per_session empêche l'inflation."""
        forge = InsightForge(
            db_url=TEST_DB_URL,
            exploration=StubExploration(connections=[
                StubConnection(
                    description=f"Connection {i} between domain_{i} and domain_{i+10}",
                    domain_a=f"domain_{i}",
                    domain_b=f"domain_{i+10}",
                    novelty_score=0.8,
                )
                for i in range(10)
            ]),
            causal=StubCausal(),
            selfmodel=StubSelfModel(),
            max_insights_per_session=3,
            min_modules_consulted=1,
            hallucination_triple_check=False,
        )
        try:
            session = forge.forge("Test inflation", max_explore=10)
            assert session.insights_found <= 3
        finally:
            from insightforge.tests.conftest import _truncate
            _truncate()
            forge.close()

    def test_strict_novelty_threshold_prevents_inflation(self):
        """Un seuil de nouveauté élevé filtre les faux insights."""
        assessor = NoveltyAssessor(min_novelty=0.95)
        candidates = [
            CandidateInsight(
                description=f"Candidate {i} with mediocre novelty score in general domain context",
                confidence=0.6,
                connects_domains=["a", "b"],
            )
            for i in range(5)
        ]
        results = assessor.assess_batch(candidates)
        new_count = sum(1 for r in results if r.is_genuinely_new)
        # With 0.95 threshold, most should fail
        assert new_count < len(candidates)

    def test_diagnose_detects_inflation(self, db):
        """Le diagnostic détecte l'inflation dans les sessions passées."""
        from insightforge.models import InsightSession
        # Créer une session avec trop d'insights
        session = InsightSession(
            question="Inflated session",
            total_candidates=10,
            insights_found=8,  # 80% > 50% = Nogah
            rejected_count=2,
            status="completed",
        )
        saved = db.save_session(session)

        forge = InsightForge(db_url=TEST_DB_URL)
        try:
            diag = forge.self_diagnose()
            assert any("Nogah" in i for i in diag["issues"])
        finally:
            from insightforge.tests.conftest import _truncate
            _truncate()
            forge.close()


# ════════════════════════════════════════════════
# 2. Ruach — Insights en boucle
# ════════════════════════════════════════════════

class TestRuach:
    """Les mêmes insights qui reviennent sous des formes différentes.
    Anti-pattern : pas de dédup sémantique.
    """

    def test_batch_dedup_prevents_loops(self):
        """La dédup inter-candidats dans un batch bloque les boucles."""
        assessor = NoveltyAssessor()
        candidates = [
            CandidateInsight(
                description="Astrocyte computation mirrors attention mechanisms in transformer neural network architectures",
                confidence=0.8,
                connects_domains=["neuro", "ml"],
            ),
            CandidateInsight(
                description="Astrocyte computation mirrors attention mechanisms in transformer neural network architectures",
                confidence=0.9,
                connects_domains=["neuro", "ml"],
            ),
        ]
        results = assessor.assess_batch(candidates)
        # Le deuxième doit être détecté comme doublon
        assert results[1].is_reformulation
        assert results[1].novelty_score == 0.0

    def test_past_insights_prevent_loops(self):
        """Les insights passés empêchent les boucles entre sessions."""
        assessor = NoveltyAssessor(
            past_insights=[
                "Astrocyte computation mirrors attention mechanisms in transformer architectures",
            ],
        )
        candidate = CandidateInsight(
            description="Astrocyte computation mirrors attention mechanisms in transformer architectures",
            confidence=0.9,
            connects_domains=["neuro", "ml"],
        )
        result = assessor.assess(candidate)
        assert result.is_reformulation
        assert not result.is_genuinely_new

    def test_similar_but_different_passes(self):
        """Des insights similaires mais substantiellement différents passent."""
        assessor = NoveltyAssessor(
            past_insights=[
                "Astrocyte computation mirrors attention mechanisms",
            ],
        )
        candidate = CandidateInsight(
            description="Causal discovery algorithms can identify hidden confounders in observational epidemiological studies of cancer",
            confidence=0.7,
            connects_domains=["causality", "epidemiology"],
        )
        result = assessor.assess(candidate)
        assert not result.is_reformulation


# ════════════════════════════════════════════════
# 3. Anan — Hallucination comme insight
# ════════════════════════════════════════════════

class TestAnan:
    """Le pire : un insight marqué 'chokmah' qui est une hallucination.
    Anti-pattern : pas de triple validation.
    """

    def test_triple_validation_blocks_hallucination(self):
        """La triple validation bloque les candidats non vérifiés."""
        v = InsightValidator(
            binah=StubCausal(
                evidence_level="correlation_only", confidence=0.3,
            ),
            gevurah=StubAutoJudge(),
            daat=StubSelfModel(high_risk=True),
            require_triple=True,
        )
        candidate = CandidateInsight(
            description="Seemingly profound insight that is actually hallucinated without evidence",
            confidence=0.9,
            connects_domains=["a", "b"],
        )
        result = v.validate(candidate)
        # Binah FAIL (correlation only), Da'at FAIL (high risk) → NOT valid
        assert not result.is_valid

    def test_high_confidence_low_evidence_rejected(self):
        """Haute confiance + faible preuve = Anan typique."""
        v = InsightValidator(
            binah=StubCausal(
                evidence_level="correlation_only", confidence=0.2,
            ),
            require_triple=True,
        )
        candidate = CandidateInsight(
            description="Very confident claim without any causal evidence to support it",
            confidence=0.95,  # Très confiant
            connects_domains=["a", "b"],
        )
        result = v.validate(candidate)
        assert not result.binah_ok

    def test_daat_error_prediction_catches_hallucination(self):
        """Da'at qui prédit une erreur bloque l'insight."""
        v = InsightValidator(
            daat=StubSelfModel(high_risk=True),
            require_triple=True,
        )
        candidate = CandidateInsight(
            description="Insight in a domain where system predicts errors with high confidence",
            confidence=0.8,
            connects_domains=["a", "b"],
        )
        result = v.validate(candidate)
        assert not result.daat_ok

    def test_no_sources_flagged(self):
        """Un insight sans données sources dans Yesod est suspect."""
        v = InsightValidator(
            yesod=StubEpisteMemory(memories=[]),
        )
        candidate = CandidateInsight(
            description="Insight with absolutely no supporting data in memory store",
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        result = v.validate(candidate)
        assert "no supporting" in result.binah_detail.lower()


# ════════════════════════════════════════════════
# 4. Mamash — Blocage créatif
# ════════════════════════════════════════════════

class TestMamash:
    """Aucun insight produit = blocage créatif.
    Anti-pattern : le système ne génère rien d'utile.
    """

    def test_diagnose_detects_creative_block(self, db):
        """Le diagnostic détecte le blocage créatif."""
        session = InsightSession(
            question="Session with creative block",
            total_candidates=10,
            insights_found=0,  # Aucun insight malgré 10 candidats
            rejected_count=10,
            status="completed",
        )
        db.save_session(session)

        forge = InsightForge(db_url=TEST_DB_URL)
        try:
            diag = forge.self_diagnose()
            assert any("Mamash" in i for i in diag["issues"])
        finally:
            from insightforge.tests.conftest import _truncate
            _truncate()
            forge.close()

    def test_few_candidates_no_mamash(self, db):
        """Peu de candidats (<=3) ne déclenche pas Mamash."""
        session = InsightSession(
            question="Small session",
            total_candidates=2,
            insights_found=0,
            rejected_count=2,
            status="completed",
        )
        db.save_session(session)

        forge = InsightForge(db_url=TEST_DB_URL)
        try:
            diag = forge.self_diagnose()
            assert not any("Mamash" in i for i in diag["issues"])
        finally:
            from insightforge.tests.conftest import _truncate
            _truncate()
            forge.close()

    def test_empty_exploration_no_candidates(self):
        """Exploration vide = 0 candidats, pas de blocage (rien à forger)."""
        forge = InsightForge(
            db_url=TEST_DB_URL,
            exploration=StubExploration(connections=[]),
            min_modules_consulted=1,
        )
        try:
            session = forge.forge("Empty exploration")
            assert session.total_candidates == 0
            assert session.insights_found == 0
        finally:
            from insightforge.tests.conftest import _truncate
            _truncate()
            forge.close()


# ════════════════════════════════════════════════
# 5. Hiérarchie Qliphoth
# ════════════════════════════════════════════════

class TestQliphothHierarchy:
    """La hiérarchie : Mamash > Anan > Ruach > Nogah."""

    def test_mamash_worst_level(self, db):
        """Mamash est le niveau le plus grave."""
        session = InsightSession(
            question="Mamash session",
            total_candidates=5,
            insights_found=0,
            rejected_count=5,
            status="completed",
        )
        db.save_session(session)

        forge = InsightForge(db_url=TEST_DB_URL)
        try:
            diag = forge.self_diagnose()
            assert diag["level"] == "mamash"
        finally:
            from insightforge.tests.conftest import _truncate
            _truncate()
            forge.close()

    def test_healthy_no_issues(self):
        """Pas de sessions = healthy."""
        forge = InsightForge(db_url=TEST_DB_URL)
        try:
            from insightforge.tests.conftest import _truncate
            _truncate()
            diag = forge.self_diagnose()
            assert diag["level"] == "healthy"
            assert diag["issues"] == []
        finally:
            forge.close()


# ════════════════════════════════════════════════
# 6. Émergence — signaux
# ════════════════════════════════════════════════

class TestEmergence:
    """L'émergence n'est pas un Qliphoth — c'est le but.
    Mais les signaux doivent être filtrés.
    """

    def test_cross_domain_signal(self, emergence):
        session = InsightSession(question="Test")
        session.add_candidate(CandidateInsight(
            description="Cross-domain insight connecting physics and biology in novel way",
            connects_domains=["physics", "biology"],
            confidence=0.8,
        ))
        signals = emergence.detect(session)
        cross = [s for s in signals if s.signal_type == "cross_domain"]
        assert len(cross) >= 1

    def test_no_signal_for_single_domain(self, emergence):
        session = InsightSession(question="Test")
        session.add_candidate(CandidateInsight(
            description="Single domain insight without cross connections",
            connects_domains=["physics"],
            confidence=0.8,
        ))
        signals = emergence.detect(session)
        cross = [s for s in signals if s.signal_type == "cross_domain"]
        assert len(cross) == 0

    def test_synergy_signal(self, emergence):
        session = InsightSession(question="Test")
        session.modules_consulted = ["chesed", "binah", "tiferet"]
        session.add_candidate(CandidateInsight(
            description="Insight from chesed module",
            source_module="chesed",
            confidence=0.7,
        ))
        session.add_candidate(CandidateInsight(
            description="Insight from tiferet module",
            source_module="tiferet",
            confidence=0.7,
        ))
        signals = emergence.detect(session)
        synergy = [s for s in signals if s.signal_type == "synergy"]
        assert len(synergy) >= 1

    def test_tension_resolved_signal(self, emergence):
        session = InsightSession(question="Test")
        session.modules_consulted = ["tiferet"]
        session.add_candidate(CandidateInsight(
            description="Resolution of tension between competing hypotheses in the system",
            source_module="tiferet",
            confidence=0.8,
        ))
        signals = emergence.detect(session)
        tensions = [
            s for s in signals if s.signal_type == "tension_resolved"
        ]
        assert len(tensions) >= 1

    def test_non_deducible_signal(self, emergence):
        session = InsightSession(question="Test")
        session.add_candidate(CandidateInsight(
            description="Non-deducible insight that emerged from module combination",
            connects_domains=["physics", "biology"],
            confidence=0.8,
            binah_validated=True,
            gevurah_validated=True,
            daat_validated=True,
        ))
        signals = emergence.detect(session)
        nd = [s for s in signals if s.signal_type == "non_deducible"]
        assert len(nd) >= 1

    def test_weak_signals_filtered(self):
        detector = EmergenceDetector(min_signal_strength=0.9)
        session = InsightSession(question="Test")
        session.add_candidate(CandidateInsight(
            description="Weak cross-domain connection between somewhat related fields",
            connects_domains=["physics", "biology"],
            confidence=0.3,
        ))
        signals = detector.detect(session)
        # Most signals should be filtered at 0.9 threshold
        assert len(signals) == 0 or all(
            s.strength >= 0.9 for s in signals
        )

    def test_max_signals_enforced(self):
        detector = EmergenceDetector(max_signals=2)
        session = InsightSession(question="Test")
        for i in range(10):
            session.add_candidate(CandidateInsight(
                description=f"Cross domain connection number {i} between field_{i} and field_{i+10}",
                connects_domains=[f"domain_{i}", f"domain_{i+10}"],
                confidence=0.8,
            ))
        signals = detector.detect(session)
        assert len(signals) <= 2

    def test_has_emergence(self, emergence):
        session = InsightSession(question="Test")
        session.add_candidate(CandidateInsight(
            description="Strong cross-domain validated insight for emergence detection",
            connects_domains=["physics", "biology", "cs"],
            confidence=0.9,
            binah_validated=True,
            gevurah_validated=True,
            daat_validated=True,
        ))
        assert emergence.has_emergence(session)

    def test_no_emergence_empty(self, emergence):
        session = InsightSession(question="Test")
        assert not emergence.has_emergence(session)

    def test_strongest_signal(self, emergence):
        session = InsightSession(question="Test")
        session.add_candidate(CandidateInsight(
            description="Strong cross-domain triple validated candidate for signal test",
            connects_domains=["a", "b", "c"],
            confidence=0.9,
            binah_validated=True,
            gevurah_validated=True,
            daat_validated=True,
        ))
        strongest = emergence.strongest_signal(session)
        assert strongest is not None
        assert strongest.strength > 0

    def test_strongest_signal_none_on_empty(self, emergence):
        session = InsightSession(question="Test")
        assert emergence.strongest_signal(session) is None


# ════════════════════════════════════════════════
# 7. InsightForge intégration
# ════════════════════════════════════════════════

class TestInsightForgeIntegration:
    def test_forge_produces_session(self, forge):
        session = forge.forge("What is the nature of insight?")
        assert isinstance(session, InsightSession)
        assert session.status == "completed"
        assert session.question == "What is the nature of insight?"

    def test_forge_has_candidates(self, forge):
        session = forge.forge("How does creativity emerge?")
        assert session.total_candidates > 0

    def test_forge_modules_consulted(self, forge):
        session = forge.forge("Test modules")
        assert len(session.modules_consulted) > 0

    def test_forge_persists_session(self, forge):
        session = forge.forge("Persistence test")
        assert session.id is not None

    def test_forge_with_domain(self, forge):
        session = forge.forge(
            "How does attention work?",
            domain="neuroscience",
        )
        assert session.domain == "neuroscience"

    def test_forge_minimal(self, forge_minimal):
        session = forge_minimal.forge("Minimal test")
        assert session.status == "completed"
        assert session.total_candidates > 0

    def test_report(self, forge):
        forge.forge("Test for report")
        report = forge.report()
        assert "InsightForge Report" in report
        assert "Chokmah" in report

    def test_assess_novelty_standalone(self, forge):
        candidate = CandidateInsight(
            description="Standalone novelty assessment of a cross-domain quantum biology connection",
            confidence=0.8,
            connects_domains=["quantum", "biology"],
        )
        result = forge.assess_novelty(candidate)
        assert isinstance(result, NoveltyAssessment)

    def test_validate_insight_standalone(self, forge):
        candidate = CandidateInsight(
            description="Standalone validation test for triple check on this candidate",
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        result = forge.validate_insight(candidate)
        assert isinstance(result, InsightValidation)


# ════════════════════════════════════════════════
# 8. Omer — calibration
# ════════════════════════════════════════════════

class TestOmerConfig:
    def test_default_values(self):
        forge = InsightForge(db_url=TEST_DB_URL)
        try:
            assert forge.min_novelty_score == 0.45
            assert forge.max_insights == 20
            assert forge.require_causal is True
            assert forge.require_selfmodel is True
            assert forge.min_modules == 5
            assert forge.hallucination_triple is True   # Anti-Ghagiel : triple validation obligatoire
            assert forge.store_non_insights is True
        finally:
            forge.close()

    def test_custom_values(self):
        forge = InsightForge(
            db_url=TEST_DB_URL,
            min_novelty_score=0.5,
            max_insights_per_session=10,
            require_causal_validation=False,
            min_modules_consulted=2,
        )
        try:
            assert forge.min_novelty_score == 0.5
            assert forge.max_insights == 10
            assert forge.require_causal is False
            assert forge.min_modules == 2
        finally:
            forge.close()

    def test_novelty_threshold_propagated(self):
        forge = InsightForge(
            db_url=TEST_DB_URL,
            min_novelty_score=0.9,
        )
        try:
            assert forge.novelty.min_novelty == 0.9
        finally:
            forge.close()

    def test_triple_check_propagated(self):
        forge = InsightForge(
            db_url=TEST_DB_URL,
            hallucination_triple_check=False,
        )
        try:
            assert forge.validator.require_triple is False
        finally:
            forge.close()


# ════════════════════════════════════════════════
# 9. DB persistence
# ════════════════════════════════════════════════

class TestDBPersistence:
    def test_session_saved(self, db):
        session = InsightSession(
            question="Test DB save",
            domain="test",
        )
        saved = db.save_session(session)
        assert saved.id is not None
        assert saved.question == "Test DB save"

    def test_session_retrieved(self, db):
        session = InsightSession(question="Test retrieve")
        saved = db.save_session(session)
        retrieved = db.get_session(saved.id)
        assert retrieved is not None
        assert retrieved.question == "Test retrieve"

    def test_candidate_saved(self, db):
        session = InsightSession(question="Test candidate")
        saved_session = db.save_session(session)
        candidate = CandidateInsight(
            description="Test candidate description",
            session_id=saved_session.id,
            source_module="chesed",
            confidence=0.7,
        )
        saved = db.save_candidate(candidate)
        assert saved.id is not None
        assert saved.description == "Test candidate description"

    def test_candidates_retrieved(self, db):
        session = InsightSession(question="Test candidates")
        saved_session = db.save_session(session)
        for i in range(3):
            db.save_candidate(CandidateInsight(
                description=f"Candidate {i}",
                session_id=saved_session.id,
                novelty_score=0.5 + i * 0.1,
            ))
        candidates = db.get_candidates(saved_session.id)
        assert len(candidates) == 3

    def test_novelty_saved(self, db):
        session = InsightSession(question="Test novelty")
        saved_session = db.save_session(session)
        candidate = db.save_candidate(CandidateInsight(
            description="Test",
            session_id=saved_session.id,
        ))
        novelty = NoveltyAssessment(
            candidate_id=candidate.id,
            is_genuinely_new=True,
            novelty_score=0.85,
            reasoning="Test reasoning",
        )
        saved = db.save_novelty(novelty)
        assert saved.id is not None
        assert saved.is_genuinely_new

    def test_session_update(self, db):
        session = InsightSession(question="Test update")
        saved = db.save_session(session)
        saved.status = "completed"
        saved.insights_found = 3
        updated = db.update_session(saved)
        assert updated.status == "completed"
        assert updated.insights_found == 3
