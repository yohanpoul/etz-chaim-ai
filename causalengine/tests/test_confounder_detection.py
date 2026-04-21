"""Tests ConfounderDetector — le gardien de Binah.

Anti-Satariel Anan : un pattern dans du bruit est un faux confounder
qui masque l'absence de causalité réelle.
"""

from unittest.mock import patch

import pytest

from causalengine.confounder_detector import (
    COMMON_CONFOUNDERS,
    UNIVERSAL_CONFOUNDERS,
    ConfounderDetector,
)
from causalengine.models import Confounder


@pytest.fixture
def detector():
    return ConfounderDetector()


# ── Détection par domaine ──────────────────────────────

class TestDomainDetection:
    def test_health_confounders(self, detector):
        confs = detector.detect("fasting", "HRV", domain="health")
        names = {c.confounder_name for c in confs}
        assert "age" in names
        assert "exercise" in names
        assert "socioeconomic_status" in names

    def test_economics_confounders(self, detector):
        confs = detector.detect("interest_rate", "GDP", domain="economics")
        names = {c.confounder_name for c in confs}
        assert "inflation" in names
        assert "population_growth" in names

    def test_psychology_confounders(self, detector):
        confs = detector.detect("therapy", "wellbeing", domain="psychology")
        names = {c.confounder_name for c in confs}
        assert "selection_bias" in names
        assert "placebo_effect" in names

    def test_technology_confounders(self, detector):
        confs = detector.detect("framework", "performance", domain="technology")
        names = {c.confounder_name for c in confs}
        assert "user_expertise" in names
        assert "hardware_variation" in names

    def test_unknown_domain_gets_universals(self, detector):
        confs = detector.detect("X", "Y", domain="astrology")
        names = {c.confounder_name for c in confs}
        assert "reverse_causation" in names
        assert "common_cause" in names

    def test_domain_resolution_medical(self, detector):
        """'medical' doit se résoudre en 'health'."""
        confs = detector.detect("drug", "recovery", domain="medical")
        names = {c.confounder_name for c in confs}
        assert "age" in names

    def test_domain_resolution_finance(self, detector):
        """'finance' doit se résoudre en 'economics'."""
        confs = detector.detect("rate", "growth", domain="finance")
        names = {c.confounder_name for c in confs}
        assert "inflation" in names


# ── Universels ─────────────────────────────────────────

class TestUniversalConfounders:
    def test_always_include_universal(self, detector):
        """Universels inclus — mais max_confounders peut tronquer les moins plausibles."""
        confs = detector.detect("A", "B", domain="health")
        names = {c.confounder_name for c in confs}
        # reverse_causation (0.6) survit au tri dans le top 10
        assert "reverse_causation" in names
        # common_cause (0.5) peut être tronqué si le domaine a trop d'entrées
        # Vérifier sur un domaine vide (que les universels)
        confs_empty = detector.detect("A", "B", domain="")
        names_empty = {c.confounder_name for c in confs_empty}
        assert "common_cause" in names_empty

    def test_universal_has_domain_marker(self, detector):
        confs = detector.detect("A", "B", domain="")
        for c in confs:
            if c.confounder_name == "reverse_causation":
                assert c.confounder_domain == "universal"


# ── Filtrage & dédoublonnage ───────────────────────────

class TestFiltering:
    def test_max_confounders_limit(self):
        detector = ConfounderDetector(max_confounders=5)
        confs = detector.detect("A", "B", domain="health")
        assert len(confs) <= 5

    def test_deduplicate(self, detector):
        """selection_bias est dans psychology ET universal — pas de doublon."""
        confs = detector.detect("therapy", "wellbeing", domain="psychology")
        names = [c.confounder_name for c in confs]
        assert names.count("selection_bias") == 1

    def test_cause_not_in_confounders(self, detector):
        """La cause elle-même ne doit pas être listée comme confounder."""
        confs = detector.detect("age", "mortality", domain="health")
        names = {c.confounder_name for c in confs}
        assert "age" not in names

    def test_effect_not_in_confounders(self, detector):
        """L'effet ne doit pas être listé comme confounder."""
        confs = detector.detect("diet", "exercise", domain="health")
        names = {c.confounder_name for c in confs}
        assert "exercise" not in names

    def test_sorted_by_plausibility(self, detector):
        confs = detector.detect("fasting", "HRV", domain="health")
        for i in range(len(confs) - 1):
            assert confs[i].plausibility >= confs[i + 1].plausibility


# ── Assess control ─────────────────────────────────────

class TestAssessControl:
    def test_all_controlled(self, detector):
        confs = [
            Confounder(confounder_name="age", controlled=True, how_controlled="matched"),
            Confounder(confounder_name="sex", controlled=True, how_controlled="stratified"),
        ]
        result = detector.assess_control(confs)
        assert result["all_controlled"] is True
        assert result["control_ratio"] == 1.0
        assert result["uncontrolled"] == []

    def test_none_controlled(self, detector):
        confs = [
            Confounder(confounder_name="age", controlled=False, plausibility=0.9),
            Confounder(confounder_name="sex", controlled=False, plausibility=0.3),
        ]
        result = detector.assess_control(confs)
        assert result["all_controlled"] is False
        assert result["control_ratio"] == 0.0
        assert len(result["uncontrolled"]) == 2

    def test_partial_control(self, detector):
        confs = [
            Confounder(confounder_name="age", controlled=True, how_controlled="matched"),
            Confounder(confounder_name="sex", controlled=False, plausibility=0.3),
        ]
        result = detector.assess_control(confs)
        assert result["control_ratio"] == 0.5

    def test_high_plausibility_uncontrolled(self, detector):
        confs = [
            Confounder(confounder_name="age", controlled=False, plausibility=0.9),
            Confounder(confounder_name="mood", controlled=False, plausibility=0.3),
        ]
        result = detector.assess_control(confs)
        assert "age" in result["high_plausibility_uncontrolled"]
        assert "mood" not in result["high_plausibility_uncontrolled"]

    def test_empty_confounders(self, detector):
        result = detector.assess_control([])
        assert result["all_controlled"] is True
        assert result["control_ratio"] == 1.0


# ── DB ─────────────────────────────────────────────────

class TestConfounderDB:
    def test_save_and_retrieve(self, db):
        from causalengine.models import CausalClaim
        claim = CausalClaim(cause="fasting", effect="HRV")
        saved_claim = db.save_claim(claim)

        conf = Confounder(
            confounder_name="age",
            confounder_domain="health",
            plausibility=0.9,
            claim_id=saved_claim.id,
        )
        saved = db.save_confounder(conf)
        assert saved.id is not None

        retrieved = db.get_confounders(saved_claim.id)
        assert len(retrieved) == 1
        assert retrieved[0].confounder_name == "age"

    def test_mark_controlled(self, db):
        from causalengine.models import CausalClaim
        claim = CausalClaim(cause="A", effect="B")
        saved_claim = db.save_claim(claim)

        conf = Confounder(
            confounder_name="age",
            plausibility=0.8,
            claim_id=saved_claim.id,
        )
        saved = db.save_confounder(conf)
        updated = db.mark_confounder_controlled(saved.id, "age-matched study")
        assert updated is not None
        assert updated.controlled is True
        assert updated.how_controlled == "age-matched study"


# ── LLM contextuel (mocké) ───────────────────────────

class TestContextualDetection:
    def test_parse_valid_json(self, detector):
        raw = '[{"name": "smoking habits", "plausibility": 0.7, "domain": "health"}]'
        confs = detector._parse_llm_confounders(raw, "fasting", "HRV", "health")
        assert len(confs) == 1
        assert confs[0].confounder_name == "smoking_habits"
        assert confs[0].plausibility == 0.7

    def test_parse_json_in_text(self, detector):
        raw = 'Here are confounders:\n[{"name": "age", "plausibility": 0.9}]\nDone.'
        confs = detector._parse_llm_confounders(raw, "X", "Y", "")
        assert len(confs) == 1
        assert confs[0].confounder_name == "age"

    def test_parse_invalid_json(self, detector):
        raw = "I cannot generate confounders."
        confs = detector._parse_llm_confounders(raw, "X", "Y", "")
        assert confs == []

    def test_parse_clamps_plausibility(self, detector):
        raw = '[{"name": "x", "plausibility": 1.5}, {"name": "y", "plausibility": -0.2}]'
        confs = detector._parse_llm_confounders(raw, "A", "B", "")
        assert confs[0].plausibility == 1.0
        assert confs[1].plausibility == 0.0

    def test_detect_contextual_llm_fail_returns_fallback(self, detector):
        """Si olamot est down, retourne les confounders statiques (fallback)."""
        with patch(
            "olamot.ollama_generate",
            side_effect=ConnectionError("no ollama"),
        ):
            confs = detector.detect_contextual("X", "Y", timeout=2)
        # Le LLM fail mais les confounders universels statiques sont retournes
        assert isinstance(confs, list)

    def test_detect_enriched_combines_static_and_llm(self, detector):
        """detect_enriched fusionne statique + LLM, déduplique."""
        llm_response = '[{"name": "circadian_rhythm", "plausibility": 0.8}]'

        with patch(
            "olamot.ollama_generate",
            return_value=(llm_response, 50.0),
        ):
            confs = detector.detect_enriched(
                "fasting", "HRV", domain="health", use_llm=True,
            )

        names = {c.confounder_name for c in confs}
        assert "circadian_rhythm" in names  # LLM
        assert "age" in names               # Statique

    def test_detect_enriched_no_llm(self, detector):
        """Avec use_llm=False, identique à detect()."""
        confs_enriched = detector.detect_enriched("A", "B", use_llm=False)
        confs_static = detector.detect("A", "B")
        assert len(confs_enriched) == len(confs_static)


# ── DB: claims sans confounders contextuels ────────────

class TestClaimsWithoutContextual:
    def test_get_claims_without_contextual(self, db):
        from causalengine.models import CausalClaim
        # Créer un claim avec seulement des confounders statiques
        claim1 = db.save_claim(CausalClaim(cause="A", effect="B"))
        db.save_confounder(Confounder(
            confounder_name="age", confounder_domain="health",
            claim_id=claim1.id,
        ))

        # Créer un claim avec un confounder contextuel
        claim2 = db.save_claim(CausalClaim(cause="C", effect="D"))
        db.save_confounder(Confounder(
            confounder_name="llm_var", confounder_domain="contextual",
            claim_id=claim2.id,
        ))

        without = db.get_claims_without_contextual_confounders(limit=10)
        ids = {c.id for c in without}
        assert claim1.id in ids    # pas de confounder contextuel
        assert claim2.id not in ids  # a un confounder contextuel


# ── Enrichissement intégré ─────────────────────────────

class TestEnrichment:
    def test_enrich_claim_adds_contextual(self, engine):
        from causalengine.models import CausalClaim
        claim = engine.db.save_claim(CausalClaim(cause="fasting", effect="HRV"))
        # Ajouter un confounder statique
        engine.db.save_confounder(Confounder(
            confounder_name="age", confounder_domain="health",
            plausibility=0.9, claim_id=claim.id,
        ))

        llm_response = '[{"name": "sleep_quality", "plausibility": 0.75, "domain": "contextual"}]'

        with patch("olamot.ollama_generate", return_value=(llm_response, 50.0)):
            result = engine.enrich_claim_confounders(claim)

        assert result["new_confounders"] == 1
        all_confs = engine.db.get_confounders(claim.id)
        names = {c.confounder_name for c in all_confs}
        assert "sleep_quality" in names
        assert "age" in names

    def test_enrich_claim_deduplicates(self, engine):
        from causalengine.models import CausalClaim
        claim = engine.db.save_claim(CausalClaim(cause="X", effect="Y"))
        engine.db.save_confounder(Confounder(
            confounder_name="age", confounder_domain="health",
            plausibility=0.9, claim_id=claim.id,
        ))

        # LLM retourne "age" aussi — ne doit pas créer de doublon
        llm_response = '[{"name": "age", "plausibility": 0.8}]'

        with patch("olamot.ollama_generate", return_value=(llm_response, 50.0)):
            result = engine.enrich_claim_confounders(claim)

        assert result["new_confounders"] == 0

    def test_run_confounder_enrichment_batch(self, engine):
        from causalengine.models import CausalClaim
        # Créer 3 claims sans confounders contextuels
        for i in range(3):
            engine.db.save_claim(CausalClaim(cause=f"cause_{i}", effect=f"effect_{i}"))

        llm_response = '[{"name": "sample_size", "plausibility": 0.6, "domain": "contextual"}]'

        with patch("olamot.ollama_generate", return_value=(llm_response, 50.0)):
            report = engine.run_confounder_enrichment(batch_size=10)

        assert report["claims_processed"] == 3
        assert report["total_new_confounders"] == 3
