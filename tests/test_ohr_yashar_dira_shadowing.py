"""Tests du fix Dira shadowing dans ohr_yashar._generate_malkuth_response.

Sprint 8e — Réactivation de l'optimisation Dira BeTachtonim (Tanya ch. 36).

Bug diagnostiqué :
    Dans _generate_malkuth_response, la variable `route` (RouteDecision)
    assignée section Hod (ligne 2359) était SHADOWÉE par une loop
    `for route in mochin_dispatch["routes"]:` (ligne 2370). Après la
    loop, `route` contenait le dernier STRING du dispatch au lieu du
    RouteDecision d'origine. Le bloc Dira BeTachtonim (ligne 2556)
    appelait alors `route.detected_domain` sur un string → AttributeError
    avalé par `log.debug("fallback: %s", e)`.

    Résultat : l'optimisation Dira BeTachtonim (éviter de monter à
    Atzilut quand le savoir a déjà descendu) ne s'activait JAMAIS
    lorsque mochin_dispatch avait au moins une route. Bug latent,
    silencieux, gaspillage LLM potentiel.

Fix (hybride, 3 changements) :
    1. Renommer la loop variable `route` → `_mochin_route` ligne 2370
       pour ne plus shadow `route` (fix root cause).
    2. Auto-suffisance défensive du bloc Dira : lire `ctx.get("route_decision")`
       dans `_route_decision` local (pattern Sprint 8d).
    3. Élever `log.debug("fallback...")` → `log.warning("Dira optimization
       skipped...")` pour visibilité des futurs problèmes.

Tests :
    1. Non-régression shadowing — `route` n'est plus écrasée.
    2. Flow complet Dira — dira_domain est correctement calculé même
       quand mochin_dispatch a des routes.
    3. Visibilité erreurs — log.warning remonte en cas d'exception.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import patch

import pytest


# ── Helpers ─────────────────────────────────────────────────


def _ollama_stub(olam, prompt, timeout=60, **kwargs):
    """Stub minimal d'ollama_generate."""
    return f"[Réponse stub {olam}]", 100.0


@pytest.fixture
def mock_llm():
    """Patch ollama_generate pour éviter tout appel réseau."""
    with patch("olamot.ollama_generate", side_effect=_ollama_stub) as m, \
         patch("olamot.get_provider", return_value="ollama"):
        yield m


def _make_route_decision(
    domain: str = "kabbalah",
    declined: bool = False,
    competence: float = 0.7,
):
    """Fabrique une fausse RouteDecision."""
    return SimpleNamespace(
        detected_domain=domain,
        did_decline=declined,
        competence_score=competence,
        decline_reason=None,
    )


def _mochin_dispatch_with_routes():
    """Fabrique un mochin_dispatch non-vide (cas du bug)."""
    return {
        "routes": [
            "Da'at→Gevurah (2 biais actifs)",
            "Da'at→Chesed (confiance basse)",
            "Da'at→Tiferet (1 faiblesse)",
        ],
        "binah_to_tiferet": {"predicted_weaknesses": ["sur-confiance"]},
        "binah_to_gevurah": {"active_biases": ["confirmation"]},
        "binah_to_chesed": {"low_confidence": True},
        "blocked": [],
    }


# ── 1. Non-régression shadowing ─────────────────────────────


class TestDiraShadowingFix:
    """Vérifie que `route` n'est plus écrasée par la loop mochin_dispatch.

    Avant le fix : avec mochin_dispatch non-vide + start_world=briah,
    `route.detected_domain` ligne 2556 levait AttributeError (route
    était un string). Après le fix : la loop utilise `_mochin_route`
    donc `route` (ou `_route_decision` relu depuis ctx) reste un
    RouteDecision exploitable.
    """

    def test_mochin_dispatch_non_empty_does_not_break_dira_block(self, mock_llm):
        """Le cas précis qui déclenchait le bug : mochin_dispatch peuplé."""
        from ohr_yashar import _generate_malkuth_response

        tree = {}  # pas de yesod → bloc Dira n'entre pas dans le if
        ctx = {
            "intent": {"type": "factuel", "depth": "briah"},
            "route_decision": _make_route_decision(domain="kabbalah"),
            "mochin_dispatch": _mochin_dispatch_with_routes(),
        }
        # Ne doit pas lever.
        response = _generate_malkuth_response(tree, "Test Dira", ctx)
        assert isinstance(response, str)
        assert len(response) > 0

    def test_route_decision_still_accessible_after_mochin_loop(self, mock_llm):
        """Invariant : après la loop mochin_dispatch, `route_decision` dans
        ctx doit toujours être consultable comme RouteDecision.

        Test structurel : on patche _get_dira_engine pour capturer le
        domain passé à should_invoke_atzilut. Si le shadowing était actif,
        une AttributeError serait levée avant l'appel → jamais capturé.
        """
        import ohr_yashar
        from ohr_yashar import _generate_malkuth_response

        captured_domains = []

        class FakeDira:
            yesod = None

            def should_invoke_atzilut(self, query, domain=None):
                captured_domains.append(domain)
                return True  # ne pas downgrade start_world

        # yesod_inst doit être truthy pour que le bloc Dira entre
        fake_yesod = SimpleNamespace(recall=lambda *a, **k: [], introspect=lambda: None)
        tree = {"yesod": fake_yesod}
        ctx = {
            "intent": {"type": "factuel", "depth": "briah"},
            "route_decision": _make_route_decision(domain="kabbalah"),
            "mochin_dispatch": _mochin_dispatch_with_routes(),
        }

        # Force start_world="briah" pour que le bloc Dira entre.
        # _HISHTALSHELUT_STATE.forced_world est consulté ligne 2468.
        original_forced = ohr_yashar._HISHTALSHELUT_STATE.get("forced_world")
        ohr_yashar._HISHTALSHELUT_STATE["forced_world"] = "briah"
        try:
            with patch("ohr_yashar._get_dira_engine", return_value=FakeDira()):
                _generate_malkuth_response(tree, "Question kabbale", ctx)
        finally:
            ohr_yashar._HISHTALSHELUT_STATE["forced_world"] = original_forced

        # Si le shadowing était encore actif, AttributeError avant cet appel
        # → captured_domains serait vide.
        assert captured_domains, (
            "should_invoke_atzilut jamais appelé — indicateur du shadowing "
            "ancien (AttributeError avant l'appel) ou condition start_world "
            "pas remplie."
        )
        # Le domaine transmis doit être "kabbalah" (depuis route_decision),
        # PAS un fragment du dernier string du mochin_dispatch.
        assert captured_domains[0] == "kabbalah", (
            f"dira_domain attendu 'kabbalah' (depuis route_decision.detected_domain), "
            f"reçu {captured_domains[0]!r}. Le fix de shadowing n'a pas fonctionné."
        )


# ── 2. Flow complet Dira avec start_world="briah" ───────────


class TestDiraOptimizationFlow:
    """Vérifie que l'optimisation Dira BeTachtonim peut s'activer quand
    assez de dira memories existent. Avant le fix, l'AttributeError
    silencieuse empêchait toujours cette optimisation.
    """

    def test_dira_optimization_downgrades_start_world_to_yetzirah(self, mock_llm):
        """Si should_invoke_atzilut retourne False → start_world='yetzirah',
        ctx['dira_optimization']=True, ctx['dira_optimized_from']='briah'.
        """
        import ohr_yashar
        from ohr_yashar import _generate_malkuth_response

        class PlentyDira:
            yesod = None

            def should_invoke_atzilut(self, query, domain=None):
                return False  # suffisamment de Dira → rester bas

        fake_yesod = SimpleNamespace(
            recall=lambda *a, **k: [], introspect=lambda: None,
        )
        tree = {"yesod": fake_yesod}
        ctx = {
            "intent": {"type": "briah", "depth": "briah"},
            "route_decision": _make_route_decision(domain="kabbalah"),
            "mochin_dispatch": _mochin_dispatch_with_routes(),
        }

        original_forced = ohr_yashar._HISHTALSHELUT_STATE.get("forced_world")
        ohr_yashar._HISHTALSHELUT_STATE["forced_world"] = "briah"
        try:
            with patch("ohr_yashar._get_dira_engine", return_value=PlentyDira()):
                _generate_malkuth_response(tree, "Question profonde", ctx)
        finally:
            ohr_yashar._HISHTALSHELUT_STATE["forced_world"] = original_forced

        # L'optimisation Dira doit avoir tagué ctx.
        assert ctx.get("dira_optimization") is True, (
            "dira_optimization=True attendu quand should_invoke_atzilut "
            "renvoie False et start_world='briah'."
        )
        assert ctx.get("dira_optimized_from") == "briah", (
            f"dira_optimized_from attendu 'briah', reçu "
            f"{ctx.get('dira_optimized_from')!r}"
        )


# ── 3. Visibilité des erreurs (log.warning, pas log.debug) ──


class TestDiraErrorVisibility:
    """Si une erreur surgit dans le bloc Dira, elle doit remonter en
    WARNING. Avant le fix : log.debug avalait silencieusement.
    """

    def test_dira_exception_logged_as_warning(self, mock_llm, caplog):
        """DiraEngine.should_invoke_atzilut lève → log.warning remonté."""
        import ohr_yashar
        from ohr_yashar import _generate_malkuth_response

        class BoomDira:
            yesod = None

            def should_invoke_atzilut(self, query, domain=None):
                raise RuntimeError("simulated Dira engine failure")

        fake_yesod = SimpleNamespace(
            recall=lambda *a, **k: [], introspect=lambda: None,
        )
        tree = {"yesod": fake_yesod}
        ctx = {
            "intent": {"type": "briah", "depth": "briah"},
            "route_decision": _make_route_decision(),
            "mochin_dispatch": _mochin_dispatch_with_routes(),
        }

        original_forced = ohr_yashar._HISHTALSHELUT_STATE.get("forced_world")
        ohr_yashar._HISHTALSHELUT_STATE["forced_world"] = "briah"
        try:
            with patch("ohr_yashar._get_dira_engine", return_value=BoomDira()), \
                 caplog.at_level(logging.WARNING, logger="etz-malkuth"):
                _generate_malkuth_response(tree, "Test", ctx)
        finally:
            ohr_yashar._HISHTALSHELUT_STATE["forced_world"] = original_forced

        matching = [
            r for r in caplog.records
            if "Dira optimization skipped" in r.getMessage()
            and r.levelno >= logging.WARNING
        ]
        assert matching, (
            "Attendu WARNING 'Dira optimization skipped: ...'. "
            f"Records capturés: "
            f"{[(r.levelname, r.name, r.getMessage()[:80]) for r in caplog.records]}"
        )
