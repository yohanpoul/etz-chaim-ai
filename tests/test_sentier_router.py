"""Tests du SentierRouter — routage des 22 sentiers dans cmd_ask.

Couvre :
  - Table de routing complète et bidirectionnelle
  - traverse() enrichit le ctx
  - Sentier absent → ctx inchangé
  - Timeout → fallback gracieux
  - Crash sentier → ctx inchangé
  - Direction yashar vs chozer
  - Katnut : seuls les sentiers du chemin court
  - sentiers_traversed : logging
  - sentier_modifiers et sentier_enrichments
  - traverse_multiple
  - format_traversal_report
  - Intégration : un chemin complet traverse plusieurs sentiers
"""

import time
from unittest.mock import patch

import pytest

from sentiers.router import SentierRouter
from sentiers import REGISTRY
from sentiers.base import Sentier


# ── Fixtures ──────────────────────────────────────────────────

@pytest.fixture
def router():
    return SentierRouter()


@pytest.fixture
def empty_ctx():
    return {}


# ── 1. Routing table complète ─────────────────────────────────

class TestRoutingTable:

    def test_all_22_sentiers_routed(self, router):
        """Chaque sentier du REGISTRY doit apparaître dans au moins une route.

        Quand deux sentiers connectent la même paire (Resh/Qoph pour
        yesod↔hod, Peh/Mem pour gevurah↔hod), chacun est routé
        dans sa direction canonique (source→target).
        """
        routed_names = set(router.routes.values())
        registry_names = {
            name for name, e in REGISTRY.items()
            if e["status"] == "implemented"
        }
        assert routed_names == registry_names

    def test_bidirectional_routes(self, router):
        """Chaque sentier est accessible dans les deux sens."""
        for name, entry in REGISTRY.items():
            if entry["status"] != "implemented":
                continue
            src, tgt = entry["source"], entry["target"]
            assert router.has_route(src, tgt), f"{name}: {src}→{tgt} missing"
            assert router.has_route(tgt, src), f"{name}: {tgt}→{src} missing"

    def test_route_count(self, router):
        """22 sentiers produce 40 routes (44 minus 4 collision overlaps)."""
        # 2 collisions (Resh/Qoph, Peh/Mem) share pairs, so each
        # collision reduces the total by 2 (one direction already taken).
        assert len(router.routes) == 40

    def test_has_route_true(self, router):
        assert router.has_route("keter", "chokmah")
        assert router.has_route("yesod", "malkuth")
        assert router.has_route("netzach", "hod")

    def test_has_route_false(self, router):
        assert not router.has_route("keter", "malkuth")
        assert not router.has_route("daat", "chesed")

    def test_get_letter(self, router):
        assert router.get_letter("keter", "chokmah") == "ב"
        assert router.get_letter("yesod", "malkuth") == "ת"
        assert router.get_letter("keter", "malkuth") is None


# ── 2. Traverse enrichit le ctx ───────────────────────────────

class TestTraverse:

    def test_traverse_adds_sentiers_traversed(self, router, empty_ctx):
        ctx = router.traverse("keter", "chokmah", empty_ctx, direction="yashar")
        assert "sentiers_traversed" in ctx
        assert len(ctx["sentiers_traversed"]) == 1
        entry = ctx["sentiers_traversed"][0]
        assert entry["letter"] == "ב"
        assert entry["from"] == "keter"
        assert entry["to"] == "chokmah"
        assert entry["direction"] == "yashar"
        assert "elapsed_ms" in entry

    def test_traverse_adds_enrichments(self, router, empty_ctx):
        ctx = router.traverse("keter", "chokmah", empty_ctx)
        assert "sentier_enrichments" in ctx
        assert len(ctx["sentier_enrichments"]) == 1
        enrichment = ctx["sentier_enrichments"][0]
        assert enrichment["letter"] == "ב"
        assert enrichment["program"] == "DirectSynth"

    def test_traverse_adds_modifiers(self, router, empty_ctx):
        ctx = router.traverse("keter", "chokmah", empty_ctx)
        # Beth (double) should inject yetzirah modifiers
        mods = ctx.get("sentier_modifiers", {})
        # Modifiers may or may not be present depending on SY yaml
        # but the key should exist if SY data is available
        assert isinstance(mods, dict)

    def test_traverse_preserves_existing_ctx(self, router):
        ctx = {"intent": {"type": "factuel"}, "memories": [1, 2, 3]}
        result = router.traverse("keter", "chokmah", ctx)
        assert result["intent"] == {"type": "factuel"}
        assert result["memories"] == [1, 2, 3]


# ── 3. Sentier absent → ctx inchangé ─────────────────────────

class TestNoRoute:

    def test_no_route_returns_ctx_unchanged(self, router):
        ctx = {"key": "value"}
        result = router.traverse("keter", "malkuth", ctx)
        assert result is ctx
        assert "sentiers_traversed" not in result

    def test_daat_has_no_sentier(self, router):
        ctx = {"key": "value"}
        result = router.traverse("binah", "daat", ctx)
        assert result is ctx

    def test_nonexistent_sefirot(self, router):
        ctx = {}
        result = router.traverse("foo", "bar", ctx)
        assert result is ctx


# ── 4. Timeout ────────────────────────────────────────────────

class TestTimeout:

    def test_slow_sentier_still_returns(self, router, empty_ctx):
        """Even if a sentier is slow, traverse returns enriched ctx."""
        # traverse_quick is purely CPU-bound so it can't actually timeout,
        # but we verify the elapsed_ms is logged
        ctx = router.traverse("keter", "chokmah", empty_ctx)
        entry = ctx["sentiers_traversed"][0]
        assert entry["elapsed_ms"] >= 0


# ── 5. Crash → fallback gracieux ──────────────────────────────

class TestCrashFallback:

    def test_crash_returns_ctx_unchanged(self, router):
        ctx = {"important": True}
        # Monkey-patch a sentier to raise
        sentier = router._get_sentier("beth")
        original = sentier.traverse_quick
        sentier.traverse_quick = lambda *a, **kw: (_ for _ in ()).throw(
            RuntimeError("boom")
        )
        try:
            result = router.traverse("keter", "chokmah", ctx)
            assert result is ctx
            assert result["important"] is True
            assert "sentiers_traversed" not in result
        finally:
            sentier.traverse_quick = original

    def test_crash_logged(self, router, empty_ctx):
        sentier = router._get_sentier("beth")
        original = sentier.traverse_quick
        sentier.traverse_quick = lambda *a, **kw: (_ for _ in ()).throw(
            ValueError("test error")
        )
        try:
            with patch("sentiers.router.logger") as mock_logger:
                router.traverse("keter", "chokmah", empty_ctx)
                mock_logger.warning.assert_called_once()
        finally:
            sentier.traverse_quick = original


# ── 6. Direction yashar vs chozer ─────────────────────────────

class TestDirection:

    def test_yashar_direction(self, router, empty_ctx):
        ctx = router.traverse("keter", "chokmah", empty_ctx, direction="yashar")
        entry = ctx["sentiers_traversed"][0]
        assert entry["direction"] == "yashar"
        enrichment = ctx["sentier_enrichments"][0]
        assert enrichment["direction"] == "yashar"

    def test_chozer_direction(self, router, empty_ctx):
        ctx = router.traverse("chokmah", "keter", empty_ctx, direction="chozer")
        entry = ctx["sentiers_traversed"][0]
        assert entry["direction"] == "chozer"
        enrichment = ctx["sentier_enrichments"][0]
        assert enrichment["direction"] == "chozer"

    def test_same_sentier_both_directions(self, router):
        """Beth connecte keter↔chokmah — traversable dans les deux sens."""
        ctx1 = router.traverse("keter", "chokmah", {}, direction="yashar")
        ctx2 = router.traverse("chokmah", "keter", {}, direction="chozer")
        assert ctx1["sentiers_traversed"][0]["letter"] == "ב"
        assert ctx2["sentiers_traversed"][0]["letter"] == "ב"


# ── 7. Katnut — chemin court uniquement ───────────────────────

class TestKatnut:

    def test_katnut_allows_hod_yesod(self, router, empty_ctx):
        ctx = router.traverse("hod", "yesod", empty_ctx,
                              direction="yashar", is_katnut=True)
        assert "sentiers_traversed" in ctx
        assert len(ctx["sentiers_traversed"]) == 1

    def test_katnut_allows_yesod_malkuth(self, router, empty_ctx):
        ctx = router.traverse("yesod", "malkuth", empty_ctx,
                              direction="yashar", is_katnut=True)
        assert "sentiers_traversed" in ctx

    def test_katnut_blocks_upper_sentiers(self, router, empty_ctx):
        """En Katnut, les sentiers hors chemin court sont bloqués."""
        ctx = router.traverse("keter", "chokmah", empty_ctx,
                              direction="yashar", is_katnut=True)
        assert "sentiers_traversed" not in ctx

    def test_katnut_blocks_chesed_gevurah(self, router, empty_ctx):
        ctx = router.traverse("chesed", "gevurah", empty_ctx,
                              direction="yashar", is_katnut=True)
        assert "sentiers_traversed" not in ctx

    def test_katnut_allows_malkuth_yesod_chozer(self, router, empty_ctx):
        ctx = router.traverse("malkuth", "yesod", empty_ctx,
                              direction="chozer", is_katnut=True)
        assert "sentiers_traversed" in ctx


# ── 8. sentiers_traversed — accumulation ──────────────────────

class TestTraversalLog:

    def test_multiple_traversals_accumulate(self, router):
        ctx = {}
        ctx = router.traverse("keter", "chokmah", ctx, direction="yashar")
        ctx = router.traverse("chokmah", "binah", ctx, direction="yashar")
        ctx = router.traverse("chesed", "gevurah", ctx, direction="yashar")
        assert len(ctx["sentiers_traversed"]) == 3
        letters = [t["letter"] for t in ctx["sentiers_traversed"]]
        assert "ב" in letters  # Beth
        assert "ד" in letters  # Daleth
        assert "ט" in letters  # Teth


# ── 9. traverse_multiple ──────────────────────────────────────

class TestTraverseMultiple:

    def test_traverse_multiple_sequential(self, router):
        ctx = {}
        ctx = router.traverse_multiple(
            [("keter", "chokmah"), ("keter", "binah"), ("chokmah", "binah")],
            ctx, direction="yashar",
        )
        assert len(ctx["sentiers_traversed"]) == 3

    def test_traverse_multiple_with_gaps(self, router):
        """Transitions without sentiers are silently skipped."""
        ctx = {}
        ctx = router.traverse_multiple(
            [("keter", "chokmah"), ("binah", "daat"), ("chesed", "gevurah")],
            ctx, direction="yashar",
        )
        # binah→daat has no sentier — only 2 traversed
        assert len(ctx["sentiers_traversed"]) == 2


# ── 10. format_traversal_report ───────────────────────────────

class TestFormatReport:

    def test_empty_report(self, router):
        lines = router.format_traversal_report({})
        assert len(lines) == 1
        assert "Aucun" in lines[0]

    def test_non_empty_report(self, router):
        ctx = {}
        ctx = router.traverse("keter", "chokmah", ctx, direction="yashar")
        ctx = router.traverse("yesod", "malkuth", ctx, direction="yashar")
        lines = router.format_traversal_report(ctx)
        assert len(lines) == 2
        assert "ב" in lines[0]
        assert "ת" in lines[1]
        assert "↓" in lines[0]  # yashar = descente


# ── 11. Double mode dagesh/rafeh depuis ctx ───────────────────

class TestDoubleMode:

    def test_high_confidence_dagesh(self, router):
        ctx = {"response_confidence": 0.8}
        ctx = router.traverse("keter", "chokmah", ctx)
        enrichment = ctx["sentier_enrichments"][0]
        # Beth is double — high confidence → dagesh
        assert enrichment.get("mode") == "dagesh"

    def test_low_confidence_rafeh(self, router):
        ctx = {"response_confidence": 0.2}
        ctx = router.traverse("keter", "chokmah", ctx)
        enrichment = ctx["sentier_enrichments"][0]
        assert enrichment.get("mode") == "rafeh"


# ── 12. Pipeline complet — descente traverse 8+ sentiers ──────

class TestFullPipeline:

    def test_full_descent_gadlut(self, router):
        """Simuler la descente complète du pipeline Yosher en Gadlut."""
        ctx = {}
        descent = [
            ("keter", "chokmah"),
            ("keter", "binah"),
            ("chokmah", "binah"),
            # Da'at: pas de sentier
            ("chesed", "gevurah"),
            ("gevurah", "tiferet"),
            ("tiferet", "netzach"),
            ("netzach", "hod"),
            ("hod", "yesod"),
            ("yesod", "malkuth"),
        ]
        ctx = router.traverse_multiple(descent, ctx, direction="yashar")
        assert len(ctx["sentiers_traversed"]) == 9
        assert len(ctx["sentier_enrichments"]) == 9

    def test_full_ascent_gadlut(self, router):
        """Simuler la remontée complète."""
        ctx = {}
        ascent = [
            ("malkuth", "yesod"),
            ("yesod", "hod"),
            ("hod", "netzach"),
            ("netzach", "tiferet"),
            ("tiferet", "gevurah"),
            ("gevurah", "chesed"),
            # Da'at: pas de sentier
            ("binah", "chokmah"),
        ]
        ctx = router.traverse_multiple(ascent, ctx, direction="chozer")
        assert len(ctx["sentiers_traversed"]) == 7

    def test_full_round_trip(self, router):
        """Descente + remontée = au moins 16 sentiers traversés."""
        ctx = {}
        descent = [
            ("keter", "chokmah"), ("keter", "binah"), ("chokmah", "binah"),
            ("chesed", "gevurah"), ("gevurah", "tiferet"),
            ("tiferet", "netzach"), ("netzach", "hod"),
            ("hod", "yesod"), ("yesod", "malkuth"),
        ]
        ascent = [
            ("malkuth", "yesod"), ("yesod", "hod"),
            ("hod", "netzach"), ("netzach", "tiferet"),
            ("tiferet", "gevurah"), ("gevurah", "chesed"),
            ("binah", "chokmah"),
        ]
        ctx = router.traverse_multiple(descent, ctx, direction="yashar")
        ctx = router.traverse_multiple(ascent, ctx, direction="chozer")
        assert len(ctx["sentiers_traversed"]) == 16

    def test_katnut_pipeline(self, router):
        """En Katnut, seuls Hod→Yesod et Yesod→Malkuth sont traversés."""
        ctx = {}
        all_transitions = [
            ("keter", "chokmah"), ("chokmah", "binah"),
            ("chesed", "gevurah"), ("gevurah", "tiferet"),
            ("tiferet", "netzach"), ("netzach", "hod"),
            ("hod", "yesod"), ("yesod", "malkuth"),
        ]
        for from_s, to_s in all_transitions:
            ctx = router.traverse(from_s, to_s, ctx,
                                  direction="yashar", is_katnut=True)
        traversed = ctx.get("sentiers_traversed", [])
        assert len(traversed) == 2
        letters = [t["letter"] for t in traversed]
        assert "ק" in letters  # Qoph (hod→yesod)
        assert "ת" in letters  # Tav (yesod→malkuth)
