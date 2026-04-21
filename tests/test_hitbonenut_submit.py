"""Tests de _submit_insight_candidate — Sprint 5.5.

Couvre la propagation de connects_domains depuis hitbonenut vers
CandidateInsight, condition nécessaire à la validation Gevurah
_local_quality_check (insight_validator.py:409-412).

Avant Sprint 5.5 : connects_domains défaut [] → reject systématique
"no connected domains".
Après Sprint 5.5 : [domain, "hitbonenut"] (filtré des Falsy).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hitbonenut import HitbonenutEngine
from insightforge.insight_validator import InsightValidator


CORPUS_PATH = Path(__file__).parent.parent / "hitbonenut_corpus.yaml"


@pytest.fixture
def engine():
    """Engine sans schema, avec tree vide modifiable."""
    with patch.object(HitbonenutEngine, "_ensure_schema"):
        eng = HitbonenutEngine(
            tree={},
            db_url="postgresql://localhost/etz_chaim_test",
            corpus_path=CORPUS_PATH,
        )
    return eng


def _capture_candidate(engine, **kwargs):
    """Helper : injecter chokmah mock et capturer le candidate soumis."""
    chokmah = MagicMock()
    engine.tree["chokmah"] = chokmah
    engine._submit_insight_candidate(**kwargs)
    chokmah.db.save_candidate.assert_called_once()
    return chokmah.db.save_candidate.call_args[0][0]


class TestConnectsDomainsPopulated:
    """Test 1 — connects_domains posé correctement avec domain valide."""

    def test_contains_domain_and_hitbonenut(self, engine):
        candidate = _capture_candidate(
            engine,
            question="Qu'est-ce que le Tzimtzum ?",
            response="Le Tzimtzum est la contraction primordiale.",
            domain="kabbalah",
            score=0.7,
        )
        assert "kabbalah" in candidate.connects_domains
        assert "hitbonenut" in candidate.connects_domains

    def test_no_falsy_values(self, engine):
        candidate = _capture_candidate(
            engine,
            question="Q?",
            response="A.",
            domain="physics",
            score=0.5,
        )
        for d in candidate.connects_domains:
            assert d
            assert isinstance(d, str)

    def test_length_is_two(self, engine):
        candidate = _capture_candidate(
            engine,
            question="Q?",
            response="A.",
            domain="biology",
            score=0.4,
        )
        assert len(candidate.connects_domains) == 2


class TestFallbackDomainEmpty:
    """Test 2 — domain None/vide : pas de None/empty dans connects_domains."""

    def test_domain_none_yields_hitbonenut_only(self, engine):
        candidate = _capture_candidate(
            engine,
            question="Q?",
            response="A.",
            domain=None,
            score=0.5,
        )
        assert candidate.connects_domains == ["hitbonenut"]

    def test_domain_empty_string_yields_hitbonenut_only(self, engine):
        candidate = _capture_candidate(
            engine,
            question="Q?",
            response="A.",
            domain="",
            score=0.5,
        )
        assert candidate.connects_domains == ["hitbonenut"]


class TestCandidateStructureIntact:
    """Test 3 — non-régression sur les autres champs du candidate."""

    def test_status_is_pending(self, engine):
        candidate = _capture_candidate(
            engine,
            question="Q?",
            response="A.",
            domain="kabbalah",
            score=0.5,
        )
        assert candidate.status == "pending"

    def test_source_module_is_hitbonenut(self, engine):
        candidate = _capture_candidate(
            engine,
            question="Q?",
            response="A.",
            domain="kabbalah",
            score=0.5,
        )
        assert candidate.source_module == "hitbonenut"

    def test_description_qa_format(self, engine):
        candidate = _capture_candidate(
            engine,
            question="Quoi ?",
            response="Cela.",
            domain="kabbalah",
            score=0.5,
        )
        assert candidate.description.startswith("Q: Quoi ?")
        assert "A: Cela." in candidate.description

    def test_domain_field_preserved(self, engine):
        candidate = _capture_candidate(
            engine,
            question="Q?",
            response="A.",
            domain="kabbalah",
            score=0.5,
        )
        assert candidate.domain == "kabbalah"

    def test_scores_preserved(self, engine):
        candidate = _capture_candidate(
            engine,
            question="Q?",
            response="A.",
            domain="kabbalah",
            score=0.42,
        )
        assert candidate.novelty_score == 0.42
        assert candidate.confidence == 0.42


class TestLocalQualityCheckPasses:
    """Test 4 — _local_quality_check ne rejette plus sur connects_domains."""

    def test_validator_accepts_populated_candidate(self, engine):
        candidate = _capture_candidate(
            engine,
            question="Q? Une description suffisamment longue pour passer.",
            response="Une réponse riche et instructive sur le Tzimtzum.",
            domain="kabbalah",
            score=0.5,
        )
        validator = InsightValidator.__new__(InsightValidator)
        ok, msg = validator._local_quality_check(candidate)
        assert ok, f"Expected pass, got reject: {msg}"
        assert "no connected domains" not in msg

    def test_validator_still_rejects_empty_connects(self, engine):
        """Garde-fou : si connects_domains vide, le rejet demeure."""
        from insightforge.models import CandidateInsight

        bad = CandidateInsight(
            description="Description suffisante de plus de 30 caractères ici.",
            source_module="hitbonenut",
            domain="kabbalah",
            novelty_score=0.5,
            confidence=0.5,
            status="pending",
            connects_domains=[],
        )
        validator = InsightValidator.__new__(InsightValidator)
        ok, msg = validator._local_quality_check(bad)
        assert not ok
        assert "no connected domains" in msg
