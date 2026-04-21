"""Tests — Soul routing wiring into world selection (R10).

Verifies that moach_shalit_al_halev() recommendations correctly
influence the start_world selection in the generation pipeline.

These tests exercise the wiring logic directly without needing the
full _generate_malkuth_response pipeline.
"""

import logging

import pytest

from tanya.dual_soul import DualSoulEngine


# ─── Helper : simulate the world selection logic from main.py ──

def _simulate_world_selection(
    soul_decision: dict | None,
    intent_depth: str = "yetzirah",
    forced_world: str | None = None,
) -> dict:
    """Reproduce the world selection logic from _generate_malkuth_response.

    Returns a dict with:
        start_world: the selected world
        tanya_override: whether Tanya overrode the default
        tanya_override_from: the world before override (if any)
        tanya_intent_conflict: conflict info (if any)
    """
    ctx: dict = {}
    intent = {"depth": intent_depth}
    log = logging.getLogger("test-soul-routing")

    # Step 1: Base world selection (mirrors main.py lines 2615-2624)
    if forced_world:
        start_world = forced_world
    else:
        depth = intent.get("depth", "yetzirah")
        if depth == "briah":
            start_world = "yetzirah"
        else:
            start_world = "assiah"

    # Step 2: Tanya override (mirrors main.py lines 2626-2699)
    try:
        if soul_decision:
            _soul_olam = soul_decision["recommended_olam"]
            _soul_conf = soul_decision["complexity_score"]
            _soul_dom = soul_decision["dominant_soul"]
            _chain = ["assiah", "yetzirah", "briah", "atziluth"]
            _current_idx = (
                _chain.index(start_world) if start_world in _chain else 0
            )
            _soul_idx = (
                _chain.index(_soul_olam)
                if _soul_olam in _chain
                else _current_idx
            )

            _SOUL_CONFIDENCE_THRESHOLD = 0.5

            if _soul_conf >= _SOUL_CONFIDENCE_THRESHOLD:
                if _soul_dom == "elokit" and _soul_idx > _current_idx:
                    ctx["tanya_override"] = True
                    ctx["tanya_override_from"] = _chain[_current_idx]
                    start_world = _soul_olam
                elif _soul_dom == "behamit" and _soul_idx < _current_idx:
                    ctx["tanya_override"] = True
                    ctx["tanya_override_from"] = _chain[_current_idx]
                    start_world = _soul_olam

                _intent_depth = intent.get("depth", "yetzirah")
                if (
                    _soul_dom == "elokit"
                    and _soul_olam in ("briah", "atziluth")
                    and _intent_depth not in ("briah", "atziluth")
                ):
                    ctx["tanya_intent_conflict"] = {
                        "soul_olam": _soul_olam,
                        "intent_depth": _intent_depth,
                        "resolved": "soul_applied",
                    }
    except Exception as e:
        log.warning("Tanya soul routing failed (non-fatal): %s", e)

    return {
        "start_world": start_world,
        "tanya_override": ctx.get("tanya_override", False),
        "tanya_override_from": ctx.get("tanya_override_from"),
        "tanya_intent_conflict": ctx.get("tanya_intent_conflict"),
    }


# ─── Tests ─────────────────────────────────────────────────────


class TestSoulRoutingElokit:
    """Elokit (divine soul) recommendations push the world UP."""

    def test_elokit_overrides_assiah_to_briah(self):
        """Elokit recommending briah should override assiah start."""
        result = _simulate_world_selection(
            soul_decision={
                "dominant_soul": "elokit",
                "recommended_olam": "briah",
                "complexity_score": 0.7,
                "reason": "test",
            },
            intent_depth="yetzirah",  # default -> assiah
        )
        assert result["start_world"] == "briah"
        assert result["tanya_override"] is True
        assert result["tanya_override_from"] == "assiah"

    def test_elokit_overrides_yetzirah_to_briah(self):
        """Elokit recommending briah should override yetzirah start."""
        result = _simulate_world_selection(
            soul_decision={
                "dominant_soul": "elokit",
                "recommended_olam": "briah",
                "complexity_score": 0.6,
                "reason": "test",
            },
            intent_depth="briah",  # -> yetzirah start
        )
        assert result["start_world"] == "briah"
        assert result["tanya_override"] is True
        assert result["tanya_override_from"] == "yetzirah"

    def test_elokit_no_override_when_already_at_briah(self):
        """Elokit recommending briah when already at briah = no change."""
        result = _simulate_world_selection(
            soul_decision={
                "dominant_soul": "elokit",
                "recommended_olam": "briah",
                "complexity_score": 0.8,
                "reason": "test",
            },
            forced_world="briah",
        )
        assert result["start_world"] == "briah"
        assert result["tanya_override"] is False

    def test_elokit_low_confidence_no_override(self):
        """Elokit with low confidence should not override."""
        result = _simulate_world_selection(
            soul_decision={
                "dominant_soul": "elokit",
                "recommended_olam": "briah",
                "complexity_score": 0.3,  # Below threshold
                "reason": "test",
            },
            intent_depth="yetzirah",
        )
        assert result["start_world"] == "assiah"
        assert result["tanya_override"] is False

    def test_elokit_detects_intent_conflict(self):
        """Elokit overriding to briah when intent says yetzirah = conflict."""
        result = _simulate_world_selection(
            soul_decision={
                "dominant_soul": "elokit",
                "recommended_olam": "briah",
                "complexity_score": 0.7,
                "reason": "test",
            },
            intent_depth="yetzirah",
        )
        assert result["tanya_intent_conflict"] is not None
        assert result["tanya_intent_conflict"]["soul_olam"] == "briah"
        assert result["tanya_intent_conflict"]["intent_depth"] == "yetzirah"


class TestSoulRoutingBehamit:
    """Behamit (animal soul) recommendations push the world DOWN."""

    def test_behamit_overrides_yetzirah_to_assiah(self):
        """Behamit recommending assiah should override yetzirah start."""
        result = _simulate_world_selection(
            soul_decision={
                "dominant_soul": "behamit",
                "recommended_olam": "assiah",
                "complexity_score": 0.8,  # High confidence in simplicity
                "reason": "test",
            },
            forced_world="yetzirah",
        )
        assert result["start_world"] == "assiah"
        assert result["tanya_override"] is True
        assert result["tanya_override_from"] == "yetzirah"

    def test_behamit_no_override_when_already_low(self):
        """Behamit recommending assiah when already at assiah = no change."""
        result = _simulate_world_selection(
            soul_decision={
                "dominant_soul": "behamit",
                "recommended_olam": "assiah",
                "complexity_score": 0.7,
                "reason": "test",
            },
            intent_depth="yetzirah",  # default -> assiah
        )
        assert result["start_world"] == "assiah"
        assert result["tanya_override"] is False

    def test_behamit_low_confidence_no_override(self):
        """Behamit with low confidence should not override."""
        result = _simulate_world_selection(
            soul_decision={
                "dominant_soul": "behamit",
                "recommended_olam": "assiah",
                "complexity_score": 0.2,
                "reason": "test",
            },
            forced_world="briah",
        )
        assert result["start_world"] == "briah"
        assert result["tanya_override"] is False


class TestSoulRoutingNoDecision:
    """When no soul_decision exists, world selection is unchanged."""

    def test_no_soul_decision_default(self):
        result = _simulate_world_selection(soul_decision=None)
        assert result["start_world"] == "assiah"
        assert result["tanya_override"] is False

    def test_no_soul_decision_with_intent_briah(self):
        result = _simulate_world_selection(
            soul_decision=None, intent_depth="briah",
        )
        assert result["start_world"] == "yetzirah"
        assert result["tanya_override"] is False


class TestSoulRoutingSafety:
    """Tanya routing failures must not break cmd_ask."""

    def test_malformed_soul_decision_handled(self):
        """Missing keys in soul_decision should not crash."""
        result = _simulate_world_selection(
            soul_decision={"dominant_soul": "elokit"},  # Missing fields
        )
        # Should not crash — falls through to default
        assert result["start_world"] == "assiah"
        assert result["tanya_override"] is False

    def test_invalid_olam_handled(self):
        """Invalid recommended_olam should not crash."""
        result = _simulate_world_selection(
            soul_decision={
                "dominant_soul": "elokit",
                "recommended_olam": "invalid_world",
                "complexity_score": 0.9,
                "reason": "test",
            },
        )
        # Should not crash — soul_idx == current_idx, no override
        assert result["start_world"] == "assiah"


class TestSoulRoutingEndToEnd:
    """End-to-end with real DualSoulEngine producing decisions."""

    def setup_method(self):
        self.engine = DualSoulEngine()

    def test_complex_query_influences_world(self):
        """A genuinely complex query should produce elokit routing."""
        decision = self.engine.moach_shalit_al_halev(
            "Pourquoi le Tsimtsum de Luria differe-t-il fondamentalement "
            "de celui de Shneur Zalman ? Analyse les implications "
            "epistemologiques de cette divergence et explique comment "
            "cela affecte notre comprehension de la causalite."
        )
        result = _simulate_world_selection(soul_decision=decision)
        assert result["start_world"] in ("briah", "atziluth")
        assert result["tanya_override"] is True

    def test_simple_query_stays_low(self):
        """A simple query should stay at assiah/yetzirah."""
        decision = self.engine.moach_shalit_al_halev("ok")
        result = _simulate_world_selection(soul_decision=decision)
        assert result["start_world"] in ("assiah", "yetzirah")

    def test_medium_query_depends_on_confidence(self):
        """A medium query's result depends on the complexity score."""
        decision = self.engine.moach_shalit_al_halev(
            "Explique la structure de base"
        )
        result = _simulate_world_selection(soul_decision=decision)
        # Whether it overrides depends on the complexity score
        # but it should NOT crash regardless
        assert result["start_world"] in (
            "assiah", "yetzirah", "briah", "atziluth",
        )
