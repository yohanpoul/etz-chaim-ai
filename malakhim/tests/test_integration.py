"""Tests d'intégration — Malakh + PekidahRegistry cycle complet.

Cinq scénarios de bout en bout :
  1. Cycle de vie réussi : naissance → exécution → mort + enregistrement Pekidah
  2. Cycle de défaillance : réponse vide → hitkalelut → kategor activé
  3. Progression de maturation IYM : IBUR → YENIKAH → MOCHIN → IBUR (Hizdakchut)
  4. Flux complet Memuneh : classify → route → dispatch → record
  5. Intégration Kategor + DebtReport : accumulation + tikkun + purge

Ces tests valident l'interaction entre Malakh (éphémère) et PekidahRegistry
(persistant) — deux plans distincts : le Malakh naît et meurt, le Pekidah garde mémoire.
"""

import pytest

from malakhim.kategor.debt import get_debt_report, purge_resolved
from malakhim.malakh import Malakh
from malakhim.memuneh.router import Memuneh
from malakhim.models import MalakhStage
from malakhim.pekidah.registry import PekidahRegistry


# ── 1. Cycle de vie réussi ───────────────────────────────────────────────────


class TestMalakhLifecycle:
    """Cycle complet : register → execute → record_outcome → record_success."""

    def test_full_lifecycle(self):
        # 1. Registre + registration de l'agent
        reg = PekidahRegistry()
        reg.register("test_agent", ["analysis"])

        # 2. Créer le Malakh avec une fonction d'exécution, kavvanah et ordre
        execute_fn = lambda ctx: f"Analysis of: {ctx['input']}"  # noqa: E731
        kavvanah = {"critere_succes": 5}  # longueur minimale = 5 caractères

        with Malakh(
            "analyze",
            kavvanah=kavvanah,
            order="malakhim",
            execute_fn=execute_fn,
        ) as m:
            result = m.execute({"input": "test data"})

        # 3. Vérifications post-exécution
        assert result.success is True
        assert "Analysis of: test data" in result.response

        # 4. Enregistrement dans le Pekidah
        reg.record_outcome("test_agent", "analysis", score=0.8)
        reg.record_success(
            "test_agent",
            "analysis",
            "deep analysis",
            {"depth": "max"},
            0.8,
        )

        # 5. Vérifier que le Malakh est détruit
        assert m._mission is None
        assert m._destroyed is True


# ── 2. Cycle de défaillance ──────────────────────────────────────────────────


class TestFailureLifecycle:
    """Cycle d'échec : réponse vide → hitkalelut → kategor actif."""

    def test_failure_lifecycle(self):
        # 1. Register agent, créer Malakh avec fonction renvoyant chaîne vide
        reg = PekidahRegistry()
        reg.register("test_agent", ["math"])

        with Malakh(
            "solve",
            order="ishim",
            execute_fn=lambda ctx: "",
        ) as m:
            result = m.execute({"input": "solve equation"})

        # 2. hitkalelut détecte la réponse vide → success=False
        assert result.success is False
        assert len(result.hitkalelut_warnings) > 0

        # 3. Enregistrement de l'outcome bas + pattern d'échec
        reg.record_outcome("test_agent", "math", score=0.1)
        reg.record_failure(
            "test_agent",
            "math",
            "empty_response",
            "solve equation",
            0.1,
        )

        # 4. Vérifier que le kategor est actif
        failures = reg.check_failures("test_agent", "math", "solve equation")
        assert len(failures) > 0


# ── 3. Progression de maturation IYM ────────────────────────────────────────


class TestMaturationProgression:
    """Progression IBUR → YENIKAH → MOCHIN → IBUR (Hizdakchut)."""

    def test_maturation_progression(self):
        reg = PekidahRegistry()
        reg.register("learner", ["coding"])

        # 1. Stade initial : IBUR
        profile = reg._agents["learner"]
        assert profile.stage == MalakhStage.IBUR

        # 2. 15 outcomes à score 0.5 → YENIKAH
        #    (>= 10 tâches, score moyen ~ 0.5, entre IBUR_SCORE_MAX=0.3 et MOCHIN_SCORE_MIN=0.6)
        for _ in range(15):
            reg.record_outcome("learner", "coding", score=0.5)
        assert profile.stage == MalakhStage.YENIKAH

        # 3. 50 outcomes à score 0.85 → MOCHIN
        #    (total >= 65 tâches, score EMA converge vers 0.85 >> 0.6)
        for _ in range(50):
            reg.record_outcome("learner", "coding", score=0.85)
        assert profile.stage == MalakhStage.MOCHIN

        # 4. 30 outcomes à score 0.1 → retour IBUR (Hizdakchut)
        #    (EMA 0.8^30 ≈ 0.001 → score ≈ 0.1 < IBUR_SCORE_MAX=0.3)
        for _ in range(30):
            reg.record_outcome("learner", "coding", score=0.1)
        assert profile.stage == MalakhStage.IBUR


# ── 4. Flux complet Memuneh ──────────────────────────────────────────────────


class TestMemunehIntegration:
    """Flux complet : classify → route → dispatch → record."""

    def test_full_routing_pipeline(self):
        """Le Memuneh route et dispatch en un seul appel."""
        reg = PekidahRegistry()
        reg.register("analyst", ["analysis"])
        memuneh = Memuneh(registry=reg)

        result = memuneh.dispatch(
            prompt="Analyse ce passage du Zohar en profondeur",
            kavvanah={"agent_id": "analyst", "domain": "analysis"},
            execute_fn=lambda ctx: f"Deep analysis of: {ctx['input']}",
        )

        assert result.success
        assert "Deep analysis" in result.response
        # Le registre a été mis à jour
        assert reg._agents["analyst"].total_tasks > 0

    def test_kategor_prevents_repeat(self):
        """Un Kategor actif produit un warning au routage."""
        reg = PekidahRegistry()
        reg.register("solver", ["math"])
        memuneh = Memuneh(registry=reg)

        # Enregistrer un échec dans le domaine "math"
        reg.record_failure("solver", "math", "hallucination", "solve integral", 0.1)

        # Router une tâche similaire — domain doit correspondre au pattern enregistré
        decision = memuneh.route(
            "solve integral calculus",
            {"agent_id": "solver", "domain": "math"},
        )
        assert len(decision.warnings) > 0
        assert any("kategor" in w.lower() or "hallucination" in w.lower() for w in decision.warnings)


# ── 5. Intégration Kategor + DebtReport ─────────────────────────────────────


class TestDebtIntegration:
    """Intégration Kategor + DebtReport."""

    def test_debt_accumulates_and_resolves(self):
        """La dette s'accumule avec les échecs et se résout avec les tikkun."""
        reg = PekidahRegistry()
        reg.register("coder", ["python"])
        memuneh = Memuneh(registry=reg)

        # Dispatch qui échoue (réponse vide) — agent_id requis pour que
        # Memuneh.dispatch() enregistre le pattern d'échec dans le registre
        result = memuneh.dispatch(
            "write code",
            kavvanah={"agent_id": "coder", "domain": "python"},
            execute_fn=lambda ctx: "",
        )
        assert not result.success

        # La dette existe
        report = get_debt_report(reg)
        assert report.total_active >= 1

        # Résoudre tous les échecs actifs (tikkun)
        for pattern_id, f in list(reg._failures.items()):
            if f.active:
                reg.resolve_failure(pattern_id, "fixed the issue")

        # Purger les patterns résolus
        purged = purge_resolved(reg)
        assert purged >= 1

        # Plus de dette active
        report2 = get_debt_report(reg)
        assert report2.total_active == 0
