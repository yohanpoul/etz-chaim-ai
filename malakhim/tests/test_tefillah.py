"""Tests Tefillah — enrichissement progressif par couches."""

from malakhim.tefillah import enrich_by_worlds, enrichment_to_system_prompt, EnrichedUnderstanding


class TestEnrichByWorlds:
    """4 couches d'enrichissement : Assiah → Yetzirah → Briah → Atziluth."""

    def test_all_four_layers(self):
        result = enrich_by_worlds(
            "Analyse les failles de sécurité du module auth",
            nature="analytic",
        )
        assert isinstance(result, EnrichedUnderstanding)
        assert result.layers_completed == 4
        assert result.literal != ""
        assert result.structured != ""

    def test_analytic_has_steps(self):
        result = enrich_by_worlds("analyse ce code", nature="analytic")
        assert "comprendre" in result.structured.lower() or "étape" in result.structured.lower()

    def test_strategic_has_options(self):
        result = enrich_by_worlds("quelle stratégie adopter", nature="strategic")
        assert "option" in result.structured.lower() or "arbitrage" in result.structured.lower()

    def test_intention_detected(self):
        result = enrich_by_worlds(
            "est-ce que c'est bien ce code ?",
            nature="analytic",
        )
        assert "VALIDATION" in result.intentional or "confirmation" in result.intentional.lower()

    def test_explicit_kavvanah_used(self):
        result = enrich_by_worlds(
            "test",
            kavvanah={"intention": "trouver les bugs critiques"},
        )
        assert "trouver les bugs" in result.intentional

    def test_causal_reasoning_detected(self):
        result = enrich_by_worlds("pourquoi ce module échoue-t-il ?")
        assert "causal" in result.conceptual.lower()


class TestEnrichmentToSystemPrompt:
    """Conversion enrichissement → system prompt."""

    def test_all_layers_present(self):
        enrichment = EnrichedUnderstanding(
            literal="le prompt brut",
            structured="étape 1, étape 2",
            conceptual="raisonnement causal",
            intentional="comprendre la cause racine",
            layers_completed=4,
        )
        sp = enrichment_to_system_prompt(enrichment)
        assert "INTENTION PROFONDE" in sp
        assert "CADRE CONCEPTUEL" in sp
        assert "PLAN IMPLICITE" in sp
        assert "REQUÊTE LITTÉRALE" in sp

    def test_intention_first(self):
        """L'intention pure est en PREMIER — le plus haut informe le plus bas."""
        enrichment = EnrichedUnderstanding(
            literal="a", structured="b", conceptual="c", intentional="d",
            layers_completed=4,
        )
        sp = enrichment_to_system_prompt(enrichment)
        assert sp.index("INTENTION") < sp.index("REQUÊTE")
