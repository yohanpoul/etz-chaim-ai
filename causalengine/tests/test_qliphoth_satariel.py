"""Tests Qliphoth de Binah — Satariel (les Dissimulateurs).

4 niveaux d'anti-patterns causaux :
  Nogah  : hedging sans vérification
  Ruach  : corrélation comme causalité
  Anan   : faux pattern dans du bruit
  Mamash : causalité inversée

Plus : tests d'intégration CausalEngine complets.
"""

import pytest

from causalengine.confounder_detector import ConfounderDetector
from causalengine.dag_builder import CycleError, DAGBuilder
from causalengine.evidence_scorer import EvidenceScorer
from causalengine.language_enforcer import LanguageEnforcer
from causalengine.models import (
    CausalAssessment,
    CausalClaim,
    CausalEdge,
    CausalGraph,
    CausalNode,
    Confounder,
    DirectionAssessment,
)
from causalengine.pearl_criteria import PearlCriteria


# ── Satariel Nogah — hedging sans vérification ────────

class TestNogah:
    """Dire "possible" sans vérifier = hedging paresseux."""

    def test_hedging_without_checking(self):
        """Un claim sans confounder checké ne peut pas monter."""
        scorer = EvidenceScorer()
        claim = CausalClaim(cause="fasting", effect="HRV")
        # Pas de confounders vérifiés → bloqué à correlation_only
        level = scorer.score(claim, [])
        assert level == "correlation_only"

    def test_cannot_upgrade_without_work(self):
        """can_upgrade doit lister les critères manquants."""
        scorer = EvidenceScorer()
        ok, missing = scorer.can_upgrade(
            "correlation_only", "probable_causation", [], None,
        )
        assert ok is False
        assert len(missing) >= 1

    def test_engine_diagnose_nogah(self, engine):
        """L'engine détecte le pattern Nogah."""
        # Sauvegarder un claim sans confounders
        claim = CausalClaim(cause="X", effect="Y")
        engine.db.save_claim(claim)
        diag = engine.self_diagnose()
        assert any("Nogah" in i for i in diag["issues"])


# ── Satariel Ruach — corrélation comme causalité ──────

class TestRuach:
    """Ne jamais présenter une corrélation comme une causalité."""

    def test_correlation_as_causation_detected(self):
        """Le LanguageEnforcer attrape 'causes' sur correlation_only."""
        enforcer = LanguageEnforcer()
        corrections = enforcer.check(
            "Fasting causes better HRV", "correlation_only",
        )
        assert len(corrections) >= 1

    def test_enforce_language_corrects(self):
        enforcer = LanguageEnforcer(strictness="strict")
        corrected, _ = enforcer.enforce(
            "Coffee causes alertness", "correlation_only",
        )
        assert "causes" not in corrected.lower()

    def test_appropriate_language_for_correlation(self):
        enforcer = LanguageEnforcer()
        lang = enforcer.appropriate_language("correlation_only")
        # Aucun verbe causal fort ne doit être dans la liste
        for phrase in lang:
            assert "causes" not in phrase.lower()


# ── Satariel Anan — faux pattern dans du bruit ────────

class TestAnan:
    """Confiance haute + preuve basse = faux pattern."""

    def test_high_confidence_low_evidence_warning(self):
        """Le scorer ne doit jamais donner haute confiance sur correlation_only."""
        scorer = EvidenceScorer()
        # Même avec beaucoup de confounders contrôlés,
        # si level=correlation_only, confidence reste modeste
        conf = scorer.compute_confidence("correlation_only", [])
        assert conf <= 0.5

    def test_engine_diagnose_anan(self, engine):
        """L'engine détecte Anan : haute confidence + low evidence."""
        # Forcer un claim pathologique
        claim = CausalClaim(
            cause="noise_X", effect="noise_Y",
            evidence_level="correlation_only",
            confidence=0.8,
            known_confounders=["a", "b"],
        )
        engine.db.save_claim(claim)
        diag = engine.self_diagnose()
        assert any("Anan" in i for i in diag["issues"])


# ── Satariel Mamash — causalité inversée ──────────────

class TestMamash:
    """Confondre cause et effet — la pire erreur."""

    def test_reversed_causation_detected_in_dag(self):
        """Un cycle A→B + B→A est détecté et rejeté."""
        builder = DAGBuilder()
        nodes = [
            CausalNode(node_id="A", name="A"),
            CausalNode(node_id="B", name="B"),
        ]
        edges = [
            CausalEdge(source="A", target="B"),
            CausalEdge(source="B", target="A"),
        ]
        with pytest.raises(CycleError):
            builder.build("reversed", nodes, edges)

    def test_direction_indeterminate_blocks_upgrade(self):
        """Sans direction vérifiée, pas de probable_causation."""
        scorer = EvidenceScorer()
        claim = CausalClaim(cause="A", effect="B")
        confs = [
            Confounder(confounder_name=f"c{i}", controlled=True, plausibility=0.5)
            for i in range(5)
        ]
        direction = DirectionAssessment(verdict="indeterminate")
        level = scorer.score(claim, confs, direction)
        assert level == "correlation_only"

    def test_engine_diagnose_mamash(self, engine):
        """L'engine détecte Mamash : causal claim sans direction vérifiée."""
        claim = CausalClaim(
            cause="A", effect="B",
            evidence_level="probable_causation",
            direction_verified=False,
            known_confounders=["x"],
        )
        engine.db.save_claim(claim)
        diag = engine.self_diagnose()
        assert any("Mamash" in i for i in diag["issues"])


# ── Hiérarchie Qliphoth ───────────────────────────────

class TestHierarchy:
    """Mamash > Anan > Ruach > Nogah — le pire domine."""

    def test_mamash_overrides_all(self, engine):
        """Si Mamash présent, le level est mamash."""
        # Nogah
        engine.db.save_claim(CausalClaim(cause="A", effect="B"))
        # Mamash
        engine.db.save_claim(CausalClaim(
            cause="C", effect="D",
            evidence_level="probable_causation",
            direction_verified=False,
            known_confounders=["x"],
        ))
        diag = engine.self_diagnose()
        assert diag["level"] == "mamash"

    def test_anan_overrides_ruach_and_nogah(self, engine):
        """Anan prime sur Ruach et Nogah."""
        # Nogah
        engine.db.save_claim(CausalClaim(cause="A", effect="B"))
        # Anan
        engine.db.save_claim(CausalClaim(
            cause="X", effect="Y",
            evidence_level="correlation_only",
            confidence=0.8,
            known_confounders=["a"],
        ))
        diag = engine.self_diagnose()
        assert diag["level"] == "anan"


# ── Intégration CausalEngine ──────────────────────────

class TestCausalEngineIntegration:
    def test_check_claim_returns_assessment(self, engine):
        assessment = engine.check_claim("fasting", "HRV", domain="health")
        assert isinstance(assessment, CausalAssessment)
        assert assessment.claim.cause == "fasting"
        assert assessment.claim.effect == "HRV"
        assert assessment.pearl_level in ("association", "intervention", "counterfactual")

    def test_check_claim_detects_confounders(self, engine):
        assessment = engine.check_claim("fasting", "HRV", domain="health")
        assert len(assessment.confounders) > 0
        names = {c.confounder_name for c in assessment.confounders}
        # health domain → age, exercise etc.
        assert "age" in names or "exercise" in names

    def test_check_claim_default_is_correlation(self, engine):
        """Sans direction fournie, reste à correlation_only."""
        assessment = engine.check_claim("A", "B")
        assert assessment.claim.evidence_level == "correlation_only"
        assert assessment.pearl_level == "association"

    def test_check_claim_with_direction(self, engine):
        direction = DirectionAssessment(
            verdict="forward", forward_plausibility=0.8,
        )
        assessment = engine.check_claim(
            "smoking", "cancer", domain="health",
            direction=direction,
        )
        # Avec direction forward + health confounders → probable_causation
        assert assessment.claim.evidence_level in (
            "correlation_only", "probable_causation",
        )

    def test_check_claim_generates_warnings(self, engine):
        assessment = engine.check_claim("X", "Y")
        # Sans direction ni confounders spécifiques → warnings
        assert len(assessment.warnings) > 0

    def test_check_claim_language_correction(self, engine):
        assessment = engine.check_claim("fasting", "HRV", domain="health")
        # Le texte test "fasting causes HRV" doit être corrigé
        if assessment.language_correction:
            assert assessment.language_correction.corrected != ""

    def test_build_causal_graph(self, engine):
        nodes = [
            CausalNode(node_id="fasting", name="Fasting"),
            CausalNode(node_id="hrv", name="HRV"),
            CausalNode(node_id="exercise", name="Exercise"),
        ]
        edges = [
            CausalEdge(source="fasting", target="hrv"),
            CausalEdge(source="exercise", target="hrv"),
        ]
        graph = engine.build_causal_graph(
            name="HRV Study", nodes=nodes, edges=edges, domain="health",
        )
        assert graph.name == "HRV Study"
        assert graph.confounders_checked is True
        assert graph.evidence_level in ("association", "intervention", "counterfactual")

    def test_detect_confounders_via_engine(self, engine):
        confs = engine.detect_confounders("fasting", "HRV", "health")
        assert len(confs) > 0

    def test_verify_direction_default(self, engine):
        direction = engine.verify_direction("A", "B")
        assert direction.verdict == "indeterminate"

    def test_enforce_language_via_engine(self, engine):
        corrected, corrections = engine.enforce_language(
            "Coffee causes alertness", "correlation_only",
        )
        assert len(corrections) >= 1

    def test_pearl_level_via_engine(self, engine):
        claim = CausalClaim(cause="A", effect="B", evidence_level="probable_causation")
        level = engine.pearl_level(claim)
        assert level == "intervention"

    def test_report(self, engine):
        engine.check_claim("fasting", "HRV", domain="health")
        report = engine.report()
        assert "CausalEngine Report" in report
        assert "Binah" in report

    def test_self_diagnose_healthy(self, engine):
        """Engine fraîche = healthy."""
        diag = engine.self_diagnose()
        assert diag["level"] == "healthy"
        assert diag["issues"] == []

    def test_claim_persisted(self, engine):
        engine.check_claim("fasting", "HRV", domain="health")
        claims = engine.db.get_claims(limit=10)
        assert len(claims) >= 1
        assert claims[0].cause == "fasting"

    def test_confounders_persisted(self, engine):
        assessment = engine.check_claim("fasting", "HRV", domain="health")
        if assessment.claim.id:
            confs = engine.db.get_confounders(assessment.claim.id)
            assert len(confs) > 0


# ── Configuration Omer ─────────────────────────────────

class TestOmerConfig:
    def test_max_confounders_respected(self):
        detector = ConfounderDetector(max_confounders=3)
        confs = detector.detect("A", "B", domain="health")
        assert len(confs) <= 3

    def test_language_strictness_strict(self):
        e = LanguageEnforcer(strictness="strict")
        corrected, _ = e.enforce("X causes Y", "correlation_only")
        assert "causes" not in corrected.lower()

    def test_language_strictness_permissive(self):
        e = LanguageEnforcer(strictness="permissive")
        corrected, corrections = e.enforce("X causes Y", "correlation_only")
        assert corrected == "X causes Y"  # pas modifié
        assert len(corrections) >= 1  # mais signalé

    def test_expose_uncertainty_in_report(self, engine):
        engine.expose_uncertainty = True
        engine.check_claim("A", "B")
        report = engine.report()
        assert "Uncertainty" in report
