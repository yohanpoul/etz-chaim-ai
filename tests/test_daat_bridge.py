"""Tests du DaatBridge -- Da'at -- Pont connaissance<->application.

Couvre :
  - dvekut : attachement au domaine (DB + contexte pur)
  - kishur : liaison faits<->question
  - kolel : coherence globale (positif + negatif)
  - build : orchestration complete
  - mode sans DB (contexte pur)
  - integration hitbonenut : daat_applied dans QuestionResult
"""

from unittest.mock import MagicMock

import pytest

from daat_bridge import DaatBridge, _extract_domain_keywords
from hitbonenut import QuestionResult


# ── Fixtures ────────────────────────────────────────────────

@pytest.fixture
def mock_db():
    """DB mockee retournant des exemples resolus."""
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    return conn, cur


@pytest.fixture
def bridge_with_db(mock_db):
    conn, _cur = mock_db
    return DaatBridge(lambda: conn)


@pytest.fixture
def bridge_no_db():
    """Bridge sans DB -- mode contexte pur."""
    return DaatBridge()


@pytest.fixture
def bridge_empty_db():
    """Bridge avec DB qui retourne 0 resultats."""
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    cur.fetchall.return_value = []
    return DaatBridge(lambda: conn)


# ── _extract_domain_keywords ──────────────────────────────

class TestExtractDomainKeywords:
    def test_from_domain(self):
        kws = _extract_domain_keywords("kabbale_lurianique")
        assert "kabbale" in kws
        assert "lurianique" in kws

    def test_from_kavvanah(self):
        kws = _extract_domain_keywords(None, {"intention": "analyser le Zohar"})
        assert "analyser" in kws
        assert "zohar" in kws

    def test_filters_short_words(self):
        kws = _extract_domain_keywords(None, {"intention": "a le de analyser"})
        assert "analyser" in kws
        assert "le" not in kws

    def test_filters_stopwords(self):
        kws = _extract_domain_keywords(None, {"intention": "faire dans cette analyse"})
        assert "analyse" in kws
        assert "faire" not in kws
        assert "dans" not in kws

    def test_deduplicates(self):
        kws = _extract_domain_keywords(
            "zohar", {"intention": "analyser le Zohar"},
        )
        assert kws.count("zohar") == 1

    def test_empty(self):
        assert _extract_domain_keywords(None) == []

    def test_none_kavvanah(self):
        kws = _extract_domain_keywords("test")
        assert kws == ["test"]


# ── Dvekut ──────────────────────────────────────────────────

class TestDvekut:
    def test_db_examples(self, bridge_with_db, mock_db):
        _, cur = mock_db
        cur.fetchall.return_value = [
            ("Qu'est-ce que le Tzimtzum?", "Le Tzimtzum est la contraction...", 0.92),
            ("Quel est le role du Kav?", "Le Kav est le rayon de lumiere...", 0.85),
        ]
        result = bridge_with_db.dvekut("kabbale_lurianique", "test?")
        assert len(result["db_examples"]) == 2
        assert result["db_examples"][0]["score"] == 0.92

    def test_no_db_still_works(self, bridge_no_db):
        result = bridge_no_db.dvekut(
            "kabbale", "Qu'est-ce que le Tzimtzum?",
            facts=["Le Tzimtzum est la contraction de l'Ein Sof"],
        )
        assert result["db_examples"] == []
        assert len(result["domain_facts"]) == 1

    def test_domain_filtering(self, bridge_no_db):
        result = bridge_no_db.dvekut(
            "kabbale", "test?",
            facts=["La Kabbale enseigne le Tsimtsum", "Python est un langage"],
        )
        assert "La Kabbale enseigne le Tsimtsum" in result["domain_facts"]
        assert "Python est un langage" not in result["domain_facts"]

    def test_no_keywords_takes_all(self, bridge_no_db):
        result = bridge_no_db.dvekut(
            None, "test?",
            facts=["Fait A", "Fait B"],
        )
        assert len(result["domain_facts"]) == 2

    def test_keywords_match_nothing_fallback_all(self, bridge_no_db):
        """Si les keywords ne matchent rien, prendre tout (mieux que rien)."""
        result = bridge_no_db.dvekut(
            "quantique", "test?",
            facts=["Fait sur la kabbale", "Fait sur le Zohar"],
        )
        assert len(result["domain_facts"]) == 2

    def test_context_items_included(self, bridge_no_db):
        result = bridge_no_db.dvekut(
            "code", "test?",
            context_items=["Le code doit etre DRY"],
        )
        assert len(result["domain_facts"]) >= 1

    def test_facts_and_context_items_merged(self, bridge_no_db):
        result = bridge_no_db.dvekut(
            None, "test?",
            facts=["Fait 1"],
            context_items=["Contexte 2"],
        )
        assert len(result["domain_facts"]) == 2

    def test_domain_keywords_returned(self, bridge_no_db):
        result = bridge_no_db.dvekut(
            "kabbale_lurianique", "test?",
            kavvanah={"intention": "analyser le Zohar"},
        )
        assert "kabbale" in result["domain_keywords"]
        assert "zohar" in result["domain_keywords"]

    def test_db_failure_returns_empty_examples(self):
        def failing_db():
            raise ConnectionError("no db")
        b = DaatBridge(failing_db)
        result = b.dvekut("test", "Q?")
        assert result["db_examples"] == []

    def test_response_truncated(self, bridge_with_db, mock_db):
        _, cur = mock_db
        long_response = "x" * 500
        cur.fetchall.return_value = [("Q?", long_response, 0.9)]
        result = bridge_with_db.dvekut("test", "Q?")
        assert len(result["db_examples"][0]["response"]) == 300

    def test_limit_respected(self, bridge_with_db, mock_db):
        _, cur = mock_db
        cur.fetchall.return_value = [("Q", "R", 0.9)]
        bridge_with_db.dvekut("gematria", "Q?", limit=1)
        call_args = cur.execute.call_args[0]
        assert call_args[1][1] == 1


# ── Kishur ──────────────────────────────────────────────────

class TestKishur:
    def test_with_facts(self, bridge_no_db):
        result = bridge_no_db.kishur(
            ["Le Tzimtzum cree le Halal", "Le Kav traverse le Halal"],
            "Quel est le lien entre Tzimtzum et Kav?",
        )
        assert "KISHUR" in result
        assert "Tzimtzum" in result
        assert "Kav" in result

    def test_empty_facts(self, bridge_no_db):
        result = bridge_no_db.kishur([], "Q?")
        assert result == ""

    def test_facts_truncated(self, bridge_no_db):
        long_fact = "x" * 200
        result = bridge_no_db.kishur([long_fact], "Q?")
        # Each fact truncated to 150 chars
        assert len(result) < len(long_fact) + 200

    def test_question_in_output(self, bridge_no_db):
        result = bridge_no_db.kishur(["Fait"], "Ma question precise?")
        assert "Ma question precise?" in result

    def test_max_6_facts(self, bridge_no_db):
        facts = [f"Fait {i}" for i in range(10)]
        result = bridge_no_db.kishur(facts, "Q?")
        assert "Fait 0" in result
        assert "Fait 5" in result
        assert "Fait 6" not in result


# ── Kolel ───────────────────────────────────────────────────

class TestKolel:
    def test_contains_why_and_why_not(self, bridge_no_db):
        result = bridge_no_db.kolel()
        assert "POURQUOI" in result
        assert "alternative" in result.lower()

    def test_contains_kolel_marker(self, bridge_no_db):
        result = bridge_no_db.kolel()
        assert "KOLEL" in result

    def test_contradiction_instruction(self, bridge_no_db):
        result = bridge_no_db.kolel()
        assert "contredit" in result


# ── Build ───────────────────────────────────────────────────

class TestBuild:
    def test_full_build_with_db(self, bridge_with_db, mock_db):
        _, cur = mock_db
        cur.fetchall.return_value = [
            ("Q resolue?", "Reponse resolue", 0.88),
        ]
        result = bridge_with_db.build(
            question="Nouvelle question?",
            domain="kabbale_lurianique",
            facts=["Fait 1", "Fait 2"],
        )
        assert result is not None
        assert "[DA'AT" in result
        assert "Exemples resolus" in result
        assert "KISHUR" in result
        assert "KOLEL" in result
        assert "[/DA'AT]" in result

    def test_build_without_db(self, bridge_no_db):
        """Build fonctionne sans DB si des faits sont fournis."""
        result = bridge_no_db.build(
            question="Qu'est-ce que le Tsimtsum?",
            facts=["Le Tsimtsum est la contraction de l'Ein Sof"],
        )
        assert result is not None
        assert "[DA'AT" in result
        assert "KISHUR" in result
        assert "KOLEL" in result
        # Pas d'exemples DB
        assert "Exemples resolus" not in result

    def test_build_with_context_items_only(self, bridge_no_db):
        """Build fonctionne avec juste des context_items."""
        result = bridge_no_db.build(
            question="Comment implémenter?",
            context_items=["DRY principle", "SOLID patterns"],
        )
        assert result is not None
        assert "KISHUR" in result

    def test_build_with_kavvanah_extracts_domain(self, bridge_no_db):
        """La kavvanah est utilisee pour extraire le domaine."""
        result = bridge_no_db.build(
            question="test?",
            facts=["Le Zohar enseigne..."],
            kavvanah={"intention": "analyser le Zohar"},
        )
        assert result is not None
        assert "Domaine" in result
        assert "zohar" in result.lower()

    def test_build_nothing_returns_none(self, bridge_no_db):
        """Sans faits ni contexte ni DB = None (pas de faux Da'at)."""
        result = bridge_no_db.build(question="Q?")
        assert result is None

    def test_build_empty_facts_returns_none(self, bridge_no_db):
        result = bridge_no_db.build(question="Q?", facts=[])
        assert result is None

    def test_build_with_empty_db_but_facts(self, bridge_empty_db):
        """DB vide mais faits presents = bloc Da'at genere."""
        result = bridge_empty_db.build(
            question="Q?",
            facts=["Un fait pertinent"],
        )
        assert result is not None
        assert "KISHUR" in result

    def test_build_domain_keywords_shown(self, bridge_no_db):
        result = bridge_no_db.build(
            question="Q?",
            domain="kabbale_lurianique",
            facts=["La kabbale enseigne"],
        )
        assert "kabbale" in result.lower()


# ── Integration QuestionResult ──────────────────────────────

class TestQuestionResultDaat:
    def test_daat_applied_default_false(self):
        qr = QuestionResult(
            id="abc", question="Q?", domain="test",
            difficulty="basique", response="R", score=0.5,
            kw_score=0.3, sentiers_used=[], nitzotzot=0,
            duration=1.0,
        )
        assert qr.daat_applied is False

    def test_daat_applied_true(self):
        qr = QuestionResult(
            id="abc", question="Q?", domain="test",
            difficulty="basique", response="R", score=0.5,
            kw_score=0.3, sentiers_used=[], nitzotzot=0,
            duration=1.0, daat_applied=True,
        )
        assert qr.daat_applied is True
