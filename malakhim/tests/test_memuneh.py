"""Tests Qliphoth — Memuneh (routeur ontologique).

Vérifie les 3 axes du routage :
  1. Classification de nature (classify_nature)
  2. Routage complet avec consultation Pekidah (route)
  3. Dispatch avec exécution et enregistrement (dispatch)
"""

import pytest

from malakhim.memuneh.router import Memuneh, RoutingDecision
from malakhim.models import MalakhResult
from malakhim.pekidah.registry import PekidahRegistry


# ── classify_nature ────────────────────────────────────────────


class TestClassifyNature:
    """Vérification de la classification ontologique des tâches."""

    def test_strategic_from_kavvanah(self):
        """Nature explicite dans kavvanah → retour direct."""
        m = Memuneh()
        result = m.classify_nature("anything", kavvanah={"nature": "strategic"})
        assert result == "strategic"

    def test_analytic_from_keywords(self):
        """Mots-clés analytiques dans un prompt suffisamment long."""
        m = Memuneh()
        prompt = "analyse ce texte en profondeur et compare les résultats"
        result = m.classify_nature(prompt)
        assert result == "analytic"

    def test_mechanic_short_prompt(self):
        """Prompt court → mechanic."""
        m = Memuneh()
        result = m.classify_nature("list files")
        assert result == "mechanic"

    def test_default_execution(self):
        """Prompt moyen sans mot-clé spécifique → execution."""
        m = Memuneh()
        prompt = "do something normal that does not match any keyword at all here"
        result = m.classify_nature(prompt)
        assert result == "execution"

    def test_olam_in_kavvanah_deduces_nature(self):
        """kavvanah["olam"] déduit la nature correspondante."""
        m = Memuneh()
        result = m.classify_nature("whatever", kavvanah={"olam": "briah"})
        assert result == "analytic"

    def test_strategic_requires_long_prompt(self):
        """Strategic ne matche que si le prompt est long (>200 chars)."""
        m = Memuneh()
        short = "design this"  # < 50 chars → mechanic
        result = m.classify_nature(short)
        assert result == "mechanic"

        long_prompt = "design " + "x " * 120  # > 200 chars
        result = m.classify_nature(long_prompt)
        assert result == "strategic"


# ── route ──────────────────────────────────────────────────────


class TestRoute:
    """Vérification du routage complet (Mesharet ↕)."""

    def test_route_strategic(self):
        """Strategic → atziluth, opus, dalet."""
        m = Memuneh()
        decision = m.route("x", kavvanah={"nature": "strategic"})

        assert isinstance(decision, RoutingDecision)
        assert decision.nature == "strategic"
        assert decision.olam == "atziluth"
        assert decision.model == "opus"
        assert decision.masakh_level == "dalet"

    def test_route_mechanic(self):
        """Mechanic → assiah, qwen3.5:9b, aleph."""
        m = Memuneh()
        decision = m.route("x", kavvanah={"nature": "mechanic"})

        assert decision.nature == "mechanic"
        assert decision.olam == "assiah"
        assert decision.model == "qwen3.5:9b"
        assert decision.provider == "ollama"
        assert decision.masakh_level == "aleph"

    def test_route_with_kategor_warning(self):
        """Si un Kategor actif matche le prompt, warnings non vide."""
        registry = PekidahRegistry()
        registry.register("agent_a", ["code"])
        registry.record_failure(
            agent_id="agent_a",
            domain="code",
            error_type="timeout",
            prompt="analyse the complex architecture design patterns",
            score=0.2,
        )

        m = Memuneh(registry=registry)
        decision = m.route(
            "analyse the complex architecture design patterns here",
            kavvanah={
                "nature": "analytic",
                "agent_id": "agent_a",
                "domain": "code",
            },
        )

        assert len(decision.warnings) > 0
        assert any("Kategor" in w for w in decision.warnings)

    def test_route_with_budget_downgrade(self):
        """budget_max insuffisant pour strategic → descend vers un olam inférieur."""
        m = Memuneh()
        decision = m.route(
            "x",
            kavvanah={"nature": "strategic"},
            budget_max=1000,
        )

        # atziluth coûte 10000, budget=1000 → doit descendre
        assert decision.olam != "atziluth"
        assert any("Budget downgrade" in w for w in decision.warnings)
        assert decision.confidence < 1.0

    def test_route_without_registry(self):
        """Sans registre, le routage fonctionne quand même (pas de warnings Pekidah)."""
        m = Memuneh(registry=None)
        decision = m.route("x", kavvanah={"nature": "execution"})

        assert decision.olam == "yetzirah"
        assert decision.model == "haiku"
        assert decision.confidence == 1.0


# ── dispatch ───────────────────────────────────────────────────


class TestDispatch:
    """Vérification du dispatch complet (route + execute + record)."""

    def test_dispatch_creates_and_executes_malakh(self):
        """dispatch → MalakhResult avec success.

        Note : sans execute_fn, olamot.ollama_generate est utilisé (LLM réel).
        On vérifie la structure du résultat, pas le contenu exact de la réponse.
        """
        m = Memuneh()
        result = m.dispatch("hello world", kavvanah={"nature": "mechanic"})

        assert isinstance(result, MalakhResult)
        assert result.success is True
        assert isinstance(result.response, str)
        assert len(result.response) > 0
        assert "routing" in result.metadata
        assert result.metadata["routing"]["olam"] == "assiah"

    def test_dispatch_with_custom_execute_fn(self):
        """dispatch avec execute_fn personnalisée."""
        m = Memuneh()

        def upper_fn(ctx: dict) -> str:
            return ctx["input"].upper()

        result = m.dispatch(
            "hello",
            kavvanah={"nature": "mechanic"},
            execute_fn=upper_fn,
        )

        assert result.response == "HELLO"
        assert result.success is True

    def test_dispatch_records_outcome(self):
        """Après dispatch, le registre Pekidah est mis à jour."""
        registry = PekidahRegistry()
        registry.register("bot_1", ["general"])

        m = Memuneh(registry=registry)
        m.dispatch(
            "do the thing right now please",
            kavvanah={
                "nature": "execution",
                "agent_id": "bot_1",
                "domain": "general",
            },
        )

        profile = registry._agents["bot_1"]
        assert profile.total_tasks == 1

    def test_dispatch_records_success_pattern(self):
        """Score > 0.7 + success → enregistre un Praklite."""
        registry = PekidahRegistry()
        registry.register("bot_2", ["general"])

        m = Memuneh(registry=registry)
        result = m.dispatch(
            "do the thing right now please",
            kavvanah={
                "nature": "execution",
                "agent_id": "bot_2",
                "domain": "general",
            },
        )

        # Le Malakh par défaut retourne score=1.0 + success=True
        assert result.success is True
        assert result.score > 0.7

        strategies = registry.get_best_strategies("general")
        assert len(strategies) >= 1


# ── olamot integration ─────────────────────────────────────────


class TestOlamotIntegration:
    """Vérification de l'intégration olamot.py dans dispatch."""

    def test_dispatch_without_execute_fn_uses_fallback(self):
        """Sans execute_fn et sans olamot configuré, le fallback retourne l'input."""
        m = Memuneh()
        result = m.dispatch("test prompt", kavvanah={"nature": "mechanic"})
        # _make_olamot_fn retourne l'input si olamot lève ImportError ou Exception
        assert result.response is not None
        assert isinstance(result.response, str)

    def test_dispatch_without_execute_fn_passes_routing(self):
        """dispatch sans execute_fn remplit quand même les metadata routing."""
        m = Memuneh()
        result = m.dispatch("test prompt", kavvanah={"nature": "mechanic"})
        assert "routing" in result.metadata
        assert result.metadata["routing"]["olam"] == "assiah"

    def test_dispatch_budget_max_passed_to_route(self):
        """budget_max est transmis à route() via dispatch()."""
        m = Memuneh()
        result = m.dispatch(
            "test prompt",
            kavvanah={"nature": "strategic"},
            execute_fn=lambda ctx: str(ctx.get("input", "")),
            budget_max=1000,
        )
        # atziluth coûte 10000 > budget 1000 → downgrade
        assert result.metadata["routing"]["olam"] != "atziluth"
        assert any(
            "Budget downgrade" in w
            for w in result.metadata["routing"]["warnings"]
        )
