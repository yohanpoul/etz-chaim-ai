"""Tests des 3 Livres Créateurs — SY 1:1.

Vérifie :
  - Sepher : détection de contenu textuel riche
  - Sephar : détection de contenu numérique/quantitatif
  - Sippur : détection de contenu dialogique
  - Équilibre : entropie, balance_ratio, dominant/deficient
"""

import math
import pytest

from kabbalah.three_books import ThreeBooks, CreationBalance


@pytest.fixture
def tb():
    return ThreeBooks()


# ═══════════════════════════════════════════════════════════════
# SEPHER — Traitement textuel
# ═══════════════════════════════════════════════════════════════

class TestSepher:
    def test_long_text_high_score(self, tb):
        text = "Le Zohar affirme que " * 100  # texte riche
        a = tb.assess_sepher(text)
        assert a.book == "sepher"
        assert a.hebrew == "סֵפֶר"
        assert a.score > 0.3

    def test_empty_text_low_score(self, tb):
        a = tb.assess_sepher("")
        assert a.score == 0.0

    def test_hebrew_text_detected(self, tb):
        text = "Le concept de צמצום (Tsimtsum) et la שבירה (Shevirah) sont centraux"
        a = tb.assess_sepher(text)
        assert a.indicators["hebrew_presence"] > 0.0

    def test_short_text_lower(self, tb):
        a = tb.assess_sepher("ok")
        assert a.score < 0.2


# ═══════════════════════════════════════════════════════════════
# SEPHAR — Traitement numérique
# ═══════════════════════════════════════════════════════════════

class TestSephar:
    def test_numbers_detected(self, tb):
        text = "Le score est de 0.85 et la gematria vaut 314"
        a = tb.assess_sephar(text)
        assert a.indicators["numbers"] > 0.0

    def test_scores_in_data(self, tb):
        a = tb.assess_sephar("texte", data={"score": 0.8, "gematria": 314})
        assert a.indicators["scores"] > 0.0

    def test_comparisons_detected(self, tb):
        text = "Le ratio est supérieur à 50% et le score= 0.9"
        a = tb.assess_sephar(text)
        assert a.indicators["comparisons"] > 0.0

    def test_no_numbers_low(self, tb):
        a = tb.assess_sephar("aucun chiffre ici")
        assert a.indicators["numbers"] == 0.0


# ═══════════════════════════════════════════════════════════════
# SIPPUR — Traitement dialogique
# ═══════════════════════════════════════════════════════════════

class TestSippur:
    def test_questions_detected(self, tb):
        text = "Qu'est-ce que le Tsimtsum ? Pourquoi la Shevirah ? Comment le Tikkun ?"
        a = tb.assess_sippur(text)
        assert a.indicators["questions"] == 1.0  # 3 questions → max

    def test_synthesis_markers(self, tb):
        text = "En résumé, d'une part le Zohar affirme X, d'autre part le Tanya dit Y"
        a = tb.assess_sippur(text)
        assert a.indicators["synthesis"] > 0.0

    def test_citations_detected(self, tb):
        text = "Selon Scholem (op. cit., p. 42), cf. Idel vol. 2, ch. 3"
        a = tb.assess_sippur(text)
        assert a.indicators["citations"] > 0.0

    def test_no_dialogue_low(self, tb):
        a = tb.assess_sippur("texte neutre sans question ni synthèse")
        assert a.score < 0.2


# ═══════════════════════════════════════════════════════════════
# ASSESS_INTERACTION — Les 3 à la fois
# ═══════════════════════════════════════════════════════════════

class TestAssessInteraction:
    def test_returns_3_books(self, tb):
        result = tb.assess_interaction("Un texte", {"score": 0.5})
        assert set(result.keys()) == {"sepher", "sephar", "sippur"}

    def test_each_has_correct_book(self, tb):
        result = tb.assess_interaction("texte", {})
        assert result["sepher"].book == "sepher"
        assert result["sephar"].book == "sephar"
        assert result["sippur"].book == "sippur"


# ═══════════════════════════════════════════════════════════════
# CREATION_BALANCE — Équilibre global
# ═══════════════════════════════════════════════════════════════

class TestCreationBalance:
    def test_empty_interactions(self, tb):
        balance = tb.get_creation_balance([])
        assert balance.n_interactions == 0
        assert balance.entropy == 0.0

    def test_single_interaction(self, tb):
        interactions = [{"text": "Un texte avec des questions ? Et un score de 0.85"}]
        balance = tb.get_creation_balance(interactions)
        assert balance.n_interactions == 1
        assert balance.sepher + balance.sephar + balance.sippur == pytest.approx(1.0)

    def test_balanced_interactions(self, tb):
        """Des interactions variées devraient être plus équilibrées."""
        interactions = [
            {"text": "Un long texte riche " * 50},  # sepher heavy
            {"text": "Score = 42, ratio > 50%, gematria = 314",
             "data": {"score": 0.9, "gematria": 314}},  # sephar heavy
            {"text": "Qu'est-ce que ? Pourquoi ? Selon Scholem, en résumé, "
                     "d'une part X, d'autre part Y, cf. Idel p. 42"},  # sippur heavy
        ]
        balance = tb.get_creation_balance(interactions)
        assert balance.n_interactions == 3
        # L'entropie devrait être raisonnablement élevée
        assert balance.entropy > 0.5

    def test_proportions_sum_to_one(self, tb):
        interactions = [
            {"text": "texte " * 20},
            {"text": "autre texte avec 42 scores"},
        ]
        balance = tb.get_creation_balance(interactions)
        total = balance.sepher + balance.sephar + balance.sippur
        assert total == pytest.approx(1.0)

    def test_max_entropy(self, tb):
        """L'entropie maximale = log2(3) ≈ 1.585."""
        max_e = math.log2(3)
        assert max_e == pytest.approx(1.585, abs=0.001)

    def test_to_dict(self, tb):
        balance = tb.get_creation_balance([{"text": "test"}])
        d = balance.to_dict()
        assert "sepher" in d
        assert "sephar" in d
        assert "sippur" in d
        assert "entropy" in d
        assert "balance_ratio" in d
        assert "dominant" in d
        assert "deficient" in d

    def test_dominant_identified(self, tb):
        """Un ensemble très textuel → sepher dominant."""
        interactions = [{"text": "Un très long texte riche en vocabulaire " * 100}]
        balance = tb.get_creation_balance(interactions)
        assert balance.dominant == "sepher"
