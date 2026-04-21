"""Tests du fix DaatBridge dans ohr_yashar._generate_malkuth_response.

Sprint 8d — Réactivation du pont Da'at.

Bug diagnostiqué :
    ohr_yashar.py:2330 référençait `route.detected_domain` avant que
    `route` soit assigné localement (ligne 2359). Python promeut `route`
    en variable locale pour toute la fonction dès qu'il voit l'assignation
    plus bas → UnboundLocalError à chaque cmd_ask Yosher.
    L'exception était avalée par `log.debug("DaatBridge: %s", e)` →
    DaatBridge inerte depuis le commit 453e376 (Cycle 3 R3.6).

Fix (Scénario 1) :
    Lecture de `ctx.get("route_decision")` dans une variable locale
    `_route_decision` à l'intérieur du bloc DaatBridge, rendant le bloc
    auto-suffisant et indépendant de l'ordre de déclaration des variables
    dans la fonction. Le log est remonté à WARNING pour visibilité.

Tests :
    1. Non-régression UnboundLocalError — 3 scénarios de ctx
    2. Flow complet — le bloc [DA'AT ...] apparaît dans le prompt final
    3. Visibilité erreurs — une exception est remontée en WARNING
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import patch

import pytest


# ── Helpers ─────────────────────────────────────────────────


def _ollama_stub(olam, prompt, timeout=60, **kwargs):
    """Stub minimal d'ollama_generate — retourne réponse + latence."""
    return f"[Réponse stub {olam}]", 100.0


@pytest.fixture
def mock_llm():
    """Patch ollama_generate pour éviter tout appel réseau."""
    with patch("olamot.ollama_generate", side_effect=_ollama_stub) as m, \
         patch("olamot.get_provider", return_value="ollama"):
        yield m


def _make_memory(content: str, confidence: float = 0.8):
    """Fabrique un faux EpisteMemory compatible avec le code."""
    return SimpleNamespace(content=content, confidence=confidence)


def _make_route_decision(
    domain: str = "kabbalah",
    declined: bool = False,
    competence: float = 0.7,
):
    """Fabrique une fausse RouteDecision compatible avec le code."""
    return SimpleNamespace(
        detected_domain=domain,
        did_decline=declined,
        competence_score=competence,
        decline_reason=None,
    )


# ── 1. Non-régression UnboundLocalError ─────────────────────


class TestNoUnboundLocalError:
    """Le fix empêche l'UnboundLocalError sur `route` ligne 2334.

    Chacun de ces 3 scénarios faisait échouer silencieusement le bloc
    DaatBridge avant le fix (exception avalée par log.debug).
    """

    def test_ctx_minimal_no_route_decision(self, mock_llm):
        """Ctx minimal — aucun route_decision."""
        from main import _generate_malkuth_response
        tree = {}
        ctx = {"intent": {"type": "factuel", "depth": "yetzirah"}}
        response = _generate_malkuth_response(tree, "Test query", ctx)
        assert isinstance(response, str)
        assert len(response) > 0

    def test_ctx_with_memories_no_route(self, mock_llm):
        """Ctx avec memories, sans route_decision — chemin Dvekut via
        kavvanah/facts mais sans domaine de route."""
        from main import _generate_malkuth_response
        tree = {}
        ctx = {
            "intent": {"type": "factuel", "depth": "yetzirah"},
            "memories": [
                _make_memory("Le Tsimtsum précède la Shevirah."),
                _make_memory("Les Partzufim sont des configurations."),
            ],
        }
        response = _generate_malkuth_response(tree, "Qu'est-ce que le Tsimtsum ?", ctx)
        assert isinstance(response, str)
        assert len(response) > 0

    def test_ctx_with_route_decision_valid(self, mock_llm):
        """Ctx complet : route_decision actif + memories — chemin nominal."""
        from main import _generate_malkuth_response
        tree = {}
        ctx = {
            "intent": {"type": "factuel", "depth": "yetzirah"},
            "memories": [_make_memory("Fact about kabbalah.")],
            "route_decision": _make_route_decision(),
        }
        response = _generate_malkuth_response(tree, "Query test", ctx)
        assert isinstance(response, str)
        assert len(response) > 0

    def test_ctx_with_route_decision_declined(self, mock_llm):
        """Ctx avec route_decision ayant did_decline=True — domaine=None."""
        from main import _generate_malkuth_response
        tree = {}
        ctx = {
            "intent": {"type": "factuel", "depth": "yetzirah"},
            "memories": [_make_memory("Fact.")],
            "route_decision": _make_route_decision(declined=True),
        }
        response = _generate_malkuth_response(tree, "Query", ctx)
        assert isinstance(response, str)
        assert len(response) > 0

    def test_ctx_with_memories_without_content_attr(self, mock_llm):
        """Memory sans `.content` — fallback `str(m)[:200]` ligne 2339
        doit fonctionner sans AttributeError."""
        from main import _generate_malkuth_response

        class PlainMemory:
            """Mock memory sans attribut .content."""
            def __str__(self):
                return "Memoire texte brut sans .content"

        tree = {}
        ctx = {
            "intent": {"type": "factuel", "depth": "yetzirah"},
            "memories": [PlainMemory()],
            "route_decision": _make_route_decision(),
        }
        response = _generate_malkuth_response(tree, "Query", ctx)
        assert isinstance(response, str)
        assert len(response) > 0


# ── 2. Flow complet : bloc Da'at injecté dans le prompt ─────


class TestDaatBridgeBlockInjected:
    """Avec memories et route_decision nominaux, DaatBridge doit produire
    un bloc `[DA'AT -- Pont connaissance<->application]` injecté dans
    `descent_context` et donc visible dans le prompt envoyé au LLM.
    """

    def test_daat_block_in_final_prompt(self):
        from main import _generate_malkuth_response
        captured = {}

        def capture(olam, prompt, timeout=60, **kwargs):
            captured.setdefault("prompts", []).append(prompt)
            return "[Réponse]", 100.0

        tree = {}
        ctx = {
            "intent": {"type": "factuel", "depth": "yetzirah"},
            "memories": [
                _make_memory("Le Tsimtsum est la contraction primordiale."),
                _make_memory("Les Partzufim sont des configurations des Sephiroth."),
            ],
            "route_decision": _make_route_decision(domain="kabbalah"),
        }

        with patch("olamot.ollama_generate", side_effect=capture), \
             patch("olamot.get_provider", return_value="ollama"):
            _generate_malkuth_response(tree, "Qu'est-ce que le Tsimtsum ?", ctx)

        assert "prompts" in captured, "ollama_generate jamais appelé"
        all_prompts = "\n===\n".join(captured["prompts"])
        # Le bloc DaatBridge a pour signature l'entête [DA'AT
        assert "[DA'AT" in all_prompts, (
            f"Bloc DaatBridge absent du prompt final. "
            f"Extrait 1er prompt: {captured['prompts'][0][:600]}"
        )


# ── 3. Visibilité des erreurs (WARNING, pas DEBUG avalé) ────


class TestDaatBridgeErrorVisibility:
    """Si DaatBridge.build lève, l'erreur doit remonter en WARNING.
    Avant le fix : log.debug avalait silencieusement → DaatBridge
    cassé pendant 3 jours sans trace en prod. Après : visible.
    """

    def test_exception_logged_as_warning(self, mock_llm, caplog):
        from main import _generate_malkuth_response

        def raise_boom(*args, **kwargs):
            raise RuntimeError("simulated DaatBridge failure for test")

        tree = {}
        ctx = {
            "intent": {"type": "factuel", "depth": "yetzirah"},
            "memories": [_make_memory("Fact")],
            "route_decision": _make_route_decision(),
        }

        with patch("daat_bridge.DaatBridge.build", side_effect=raise_boom), \
             caplog.at_level(logging.WARNING, logger="etz-malkuth"):
            _generate_malkuth_response(tree, "Test", ctx)

        matching = [
            r for r in caplog.records
            if "DaatBridge skipped" in r.getMessage()
            and r.levelno >= logging.WARNING
        ]
        assert matching, (
            "Attendu: WARNING 'DaatBridge skipped: ...'. "
            f"Records capturés: "
            f"{[(r.levelname, r.name, r.getMessage()[:80]) for r in caplog.records]}"
        )
