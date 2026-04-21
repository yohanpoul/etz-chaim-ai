"""Tests Even Shayish — le test des pierres de marbre."""

from malakhim.even_shayish import marble_test, MarbleTestResult


class TestMarbleTest:
    """Distinguer l'intention apparente de l'intention réelle."""

    def test_transparent_prompt_no_divergence(self):
        """Prompt clair et direct → pas de divergence."""
        result = marble_test("Implémente une fonction de tri en Python")
        assert result is None

    def test_validation_seeking(self):
        """'Est-ce correct' → cherche validation, pas analyse."""
        result = marble_test("est-ce que c'est bien ce que j'ai fait ?")
        assert result is not None
        assert "VALIDATION" in result.probable_real_intent
        assert result.divergence > 0

    def test_confusion_seeking_pedagogy(self):
        """'Je comprends pas' → cherche pédagogie, pas technique."""
        result = marble_test("je ne comprends pas comment fonctionne le garbage collector")
        assert result is not None
        assert "PÉDAGOGIE" in result.probable_real_intent

    def test_overwhelmed_seeking_triage(self):
        """'Résume' → cherche triage, pas synthèse élaborée."""
        result = marble_test("résume moi ce document en gros")
        assert result is not None
        assert "TRIAGE" in result.probable_real_intent

    def test_stuck_seeking_unblock(self):
        """'Aide' → cherche déblocage, pas solution complète."""
        result = marble_test("aide moi, ça marche pas du tout")
        assert result is not None
        assert "DÉBLOCAGE" in result.probable_real_intent

    def test_refactor_seeking_rewrite(self):
        """'Améliore' → peut-être 'réécris tout'."""
        result = marble_test("améliore ce code s'il te plaît")
        assert result is not None
        assert "RÉÉCRITURE" in result.probable_real_intent

    def test_impatience_detected(self):
        """'Vite' / 'juste' → impatience."""
        result = marble_test("juste dis-moi comment faire vite")
        assert result is not None
        assert "IMPATIENCE" in result.probable_real_intent

    def test_explicit_intention_skips(self):
        """Si kavvanah a une intention explicite → pas de test."""
        result = marble_test(
            "est-ce que c'est bien ?",
            kavvanah={"intention": "audit de sécurité complet"},
        )
        assert result is None

    def test_result_has_adjustment(self):
        """Le résultat contient une instruction d'ajustement."""
        result = marble_test("help je suis bloqué")
        assert result is not None
        assert len(result.adjustment) > 0
        assert len(result.signal) > 0
