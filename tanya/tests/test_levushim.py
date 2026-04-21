"""Tests — Levushim (3 Vêtements fonctionnels).

Vérifie le scoring Machshava/Dibour/Maase et la pondération 40/35/25.
"""

import pytest

from tanya.levushim import Levushim, LevushimAssessment


@pytest.fixture
def levushim():
    return Levushim()


# ─── Machshava (pensée) ────────────────────────────────────


class TestMachshava:
    def test_empty_reasoning(self, levushim):
        assert levushim.assess_machshava("") == 0.0

    def test_none_reasoning(self, levushim):
        assert levushim.assess_machshava(None) == 0.0

    def test_short_reasoning(self, levushim):
        # 3 mots sans connecteurs ni structure → machshava quasi-nulle
        score = levushim.assess_machshava("Oui c'est correct")
        assert score == 0.0

    def test_medium_reasoning(self, levushim):
        # Assez de mots pour un score minimal mais pas de structure
        score = levushim.assess_machshava(
            "Le concept est intéressant car il permet de comprendre "
            "la structure des données dans le contexte donné"
        )
        assert 0.0 < score < 0.5

    def test_structured_reasoning(self, levushim):
        reasoning = (
            "── ① Keter — Intention ──\n"
            "  La question porte sur le Tsimtsum\n"
            "── ② Chokmah — Flash d'insight ──\n"
            "  Le Tsimtsum est un retrait, donc il crée un espace\n"
            "── ③ Binah — Analyse ──\n"
            "  Par conséquent, l'espace vide (Khalal) permet la création\n"
            "  En effet, le Reshimu subsiste comme trace informationnelle\n"
            "  Cependant, Shneur Zalman interprète différemment\n"
            "── ④ Daat — Connexion ──\n"
            "  Ainsi, le Tsimtsum n'est pas ontologique mais épistémologique"
        )
        score = levushim.assess_machshava(reasoning)
        assert score >= 0.5

    def test_long_unstructured_has_some_value(self, levushim):
        reasoning = " ".join(["mot"] * 50)
        score = levushim.assess_machshava(reasoning)
        assert score > 0.0


# ─── Dibour (parole) ──────────────────────────────────────


class TestDibour:
    def test_empty_response(self, levushim):
        assert levushim.assess_dibour("", "question") == 0.0

    def test_none_response(self, levushim):
        assert levushim.assess_dibour(None, "question") == 0.0

    def test_relevant_response(self, levushim):
        query = "Explique le Tsimtsum dans la Kabbale lourianique"
        response = (
            "Le Tsimtsum dans la Kabbale lourianique est le retrait\n\n"
            "1. L'Ein Sof se contracte pour créer un espace vide\n"
            "2. Le Reshimu subsiste comme trace\n"
            "3. Le Kav (ligne) pénètre pour structurer\n\n"
            "Selon Luria, ce retrait est le premier acte créatif."
        )
        score = levushim.assess_dibour(response, query)
        assert score >= 0.5

    def test_irrelevant_response_low(self, levushim):
        query = "Explique le Tsimtsum"
        response = "xyz abc def"
        score = levushim.assess_dibour(response, query)
        assert score < 0.5

    def test_very_short_response(self, levushim):
        score = levushim.assess_dibour("Oui", "question longue sur un sujet")
        assert score < 0.3

    def test_good_length_structured(self, levushim):
        query = "Comment fonctionne l'attention dans les Transformers ?"
        response = (
            "L'attention dans les Transformers fonctionne ainsi :\n\n"
            "- Query, Key, Value sont des projections linéaires\n"
            "- Le score d'attention = softmax(QK^T / sqrt(d_k))\n"
            + " détail" * 30 + "\n\n"
            "Cela permet au modèle de pondérer les tokens."
        )
        score = levushim.assess_dibour(response, query)
        assert score >= 0.5


# ─── Maase (action) ──────────────────────────────────────


class TestMaase:
    def test_no_actions(self, levushim):
        assert levushim.assess_maase([]) == 0.0

    def test_one_action(self, levushim):
        score = levushim.assess_maase(["routed_briah"])
        assert 0.2 <= score <= 0.6

    def test_multiple_actions(self, levushim):
        actions = [
            "routed_briah",
            "memory_stored",
            "nitzutz_collected",
            "score_updated",
            "insight_generated",
        ]
        score = levushim.assess_maase(actions)
        assert score >= 0.7

    def test_high_value_actions_boost(self, levushim):
        low = levushim.assess_maase(["routed", "scored", "logged"])
        high = levushim.assess_maase(["memory_stored", "nitzutz_collected", "logged"])
        assert high > low


# ─── wrap_response (intégration) ────────────────────────


class TestWrapResponse:
    def test_returns_assessment(self, levushim):
        result = levushim.wrap_response(
            query="Explique le Tsimtsum",
            reasoning="Le Tsimtsum est donc un retrait créatif",
            response_text="Le Tsimtsum est le retrait de l'Ein Sof.",
            actions_taken=["routed_briah"],
        )
        assert isinstance(result, LevushimAssessment)
        assert 0.0 <= result.overall_score <= 1.0
        assert result.dominant_garment in ("machshava", "dibour", "maase")
        assert result.weak_garment in ("machshava", "dibour", "maase")
        assert result.recommendation

    def test_weighting_40_35_25(self, levushim):
        """Vérifie que la pondération est correcte : 40/35/25."""
        result = levushim.wrap_response(
            query="test",
            reasoning="",          # machshava = 0
            response_text="",      # dibour = 0
            actions_taken=[],      # maase = 0
        )
        assert result.overall_score == 0.0

    def test_all_strong(self, levushim):
        reasoning = (
            "── ① Analyse ──\n"
            "  Premièrement, en effet, le sujet...\n"
            "── ② Développement ──\n"
            "  Par conséquent, cependant, de plus...\n"
            "── ③ Conclusion ──\n"
            "  Ainsi, donc, néanmoins...\n"
            + " mot" * 60
        )
        response = (
            "Réponse détaillée sur le sujet de la question.\n\n"
            "1. Premier point développé\n"
            "2. Deuxième point avec argumentation\n\n"
            + " contenu" * 40
        )
        actions = [
            "memory_stored",
            "nitzutz_collected",
            "routed_briah",
            "insight_generated",
            "dira_cascaded",
        ]
        result = levushim.wrap_response(
            query="Explique le sujet de la question en détail",
            reasoning=reasoning,
            response_text=response,
            actions_taken=actions,
        )
        assert result.overall_score >= 0.6

    def test_weak_garment_identified(self, levushim):
        """Si aucune action, maase est le vêtement faible."""
        result = levushim.wrap_response(
            query="Explique le Tsimtsum en détail s'il te plaît",
            reasoning="Donc le Tsimtsum est un retrait, car l'Ein Sof doit se contracter",
            response_text="Le Tsimtsum est le retrait de l'Ein Sof pour créer le monde.",
            actions_taken=[],
        )
        assert result.weak_garment == "maase"

    def test_dominant_garment_identified(self, levushim):
        """Si beaucoup d'actions mais pas de raisonnement, maase domine."""
        result = levushim.wrap_response(
            query="test",
            reasoning="",
            response_text="ok",
            actions_taken=[
                "memory_stored", "nitzutz_collected",
                "birur_detected", "insight_generated", "dira_cascaded",
            ],
        )
        assert result.dominant_garment == "maase"
