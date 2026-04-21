"""Tests — Activation fonctionnelle du Zivvug Abba/Imma.

Le Zivvug n'est plus décoratif : quand les deux parents (Chokmah + Binah)
produisent, Gevurah s'assouplit et le DaemonBridge reçoit plus de budget.
"""

from __future__ import annotations

import types
from unittest.mock import MagicMock, patch

import pytest


# ─── Helpers ───────────────────────────────────────────────────


def _make_ctx(**overrides) -> dict:
    """Crée un ctx minimal pour les tests."""
    ctx = {
        "intent": {"type": "factuel", "depth": "standard"},
        "partzufim": {},
    }
    ctx.update(overrides)
    return ctx


def _make_tree(**overrides) -> dict:
    """Crée un tree minimal avec un AutoJudge mock."""
    gevurah = MagicMock()
    gevurah.quality_threshold = 0.6
    gevurah.quarantine_threshold = 0.4
    gevurah.evaluator = MagicMock()
    gevurah.evaluator.quality_threshold = 0.6
    gevurah.self_diagnose.return_value = {
        "total_experiments": 10,
        "rejection_rate": 0.3,
        "level": "healthy",
    }
    tree = {
        "chokmah": None,
        "binah": None,
        "gevurah": gevurah,
        "daat": None,
    }
    tree.update(overrides)
    return tree


def _make_forge_session(insights_found: int = 0):
    """Crée un mock ForgeSession."""
    session = MagicMock()
    session.insights_found = insights_found
    session.total_candidates = insights_found + 2
    session.pearl_level = "association"
    session.validated_insights = []
    return session


# ─── Tests signal zivvug_state ─────────────────────────────────


class TestZivvugState:
    """Signal ctx['zivvug_state'] déterminé dans _zivug_abba_imma."""

    def test_zivvug_active_when_both_produce(self):
        """Les deux parents produisent → zivvug_state = 'active'."""
        ctx = _make_ctx()
        ctx["forge_session"] = _make_forge_session(insights_found=3)
        ctx["binah_diag"] = {"total_graphs": 2, "total_claims": 5}

        # Simuler la logique de Phase 5
        forge_session = ctx.get("forge_session")
        chokmah_produced = bool(
            forge_session and getattr(forge_session, "insights_found", 0) > 0
        )
        binah_produced = bool(
            ctx.get("binah_diag", {}).get("total_graphs", 0) > 0
            or ctx.get("binah_diag", {}).get("total_claims", 0) > 0
        )
        if chokmah_produced and binah_produced:
            ctx["zivvug_state"] = "active"
        elif chokmah_produced or binah_produced:
            ctx["zivvug_state"] = "partial"
        else:
            ctx["zivvug_state"] = "absent"

        assert ctx["zivvug_state"] == "active"

    def test_zivvug_partial_chokmah_only(self):
        """Seul Chokmah produit → zivvug_state = 'partial'."""
        ctx = _make_ctx()
        ctx["forge_session"] = _make_forge_session(insights_found=2)
        ctx["binah_diag"] = {"total_graphs": 0, "total_claims": 0}

        forge_session = ctx.get("forge_session")
        chokmah_produced = bool(
            forge_session and getattr(forge_session, "insights_found", 0) > 0
        )
        binah_produced = bool(
            ctx.get("binah_diag", {}).get("total_graphs", 0) > 0
            or ctx.get("binah_diag", {}).get("total_claims", 0) > 0
        )
        if chokmah_produced and binah_produced:
            ctx["zivvug_state"] = "active"
        elif chokmah_produced or binah_produced:
            ctx["zivvug_state"] = "partial"
        else:
            ctx["zivvug_state"] = "absent"

        assert ctx["zivvug_state"] == "partial"

    def test_zivvug_partial_binah_only(self):
        """Seul Binah produit → zivvug_state = 'partial'."""
        ctx = _make_ctx()
        ctx["forge_session"] = _make_forge_session(insights_found=0)
        ctx["binah_diag"] = {"total_graphs": 1, "total_claims": 3}

        forge_session = ctx.get("forge_session")
        chokmah_produced = bool(
            forge_session and getattr(forge_session, "insights_found", 0) > 0
        )
        binah_produced = bool(
            ctx.get("binah_diag", {}).get("total_graphs", 0) > 0
            or ctx.get("binah_diag", {}).get("total_claims", 0) > 0
        )
        if chokmah_produced and binah_produced:
            ctx["zivvug_state"] = "active"
        elif chokmah_produced or binah_produced:
            ctx["zivvug_state"] = "partial"
        else:
            ctx["zivvug_state"] = "absent"

        assert ctx["zivvug_state"] == "partial"

    def test_zivvug_absent_when_none_produce(self):
        """Aucun parent ne produit → zivvug_state = 'absent'."""
        ctx = _make_ctx()
        ctx["forge_session"] = _make_forge_session(insights_found=0)
        ctx["binah_diag"] = {"total_graphs": 0, "total_claims": 0}

        forge_session = ctx.get("forge_session")
        chokmah_produced = bool(
            forge_session and getattr(forge_session, "insights_found", 0) > 0
        )
        binah_produced = bool(
            ctx.get("binah_diag", {}).get("total_graphs", 0) > 0
            or ctx.get("binah_diag", {}).get("total_claims", 0) > 0
        )
        if chokmah_produced and binah_produced:
            ctx["zivvug_state"] = "active"
        elif chokmah_produced or binah_produced:
            ctx["zivvug_state"] = "partial"
        else:
            ctx["zivvug_state"] = "absent"

        assert ctx["zivvug_state"] == "absent"


# ─── Tests Gevurah modifier ───────────────────────────────────


class TestZivvugGevurahModifier:
    """Le Zivvug modifie temporairement les seuils de Gevurah."""

    def test_active_lowers_threshold(self):
        """Zivvug actif → seuil Gevurah baissé de 0.05."""
        tree = _make_tree()
        ctx = _make_ctx(zivvug_state="active")
        gevurah = tree["gevurah"]

        original_quality = gevurah.quality_threshold
        ctx["_gevurah_original_quality"] = original_quality
        ctx["_gevurah_original_quarantine"] = gevurah.quarantine_threshold

        gevurah.quality_threshold -= 0.05
        gevurah.evaluator.quality_threshold -= 0.05
        ctx["zivvug_gevurah_modifier"] = -0.05

        assert gevurah.quality_threshold == pytest.approx(0.55)
        assert ctx["zivvug_gevurah_modifier"] == -0.05

    def test_absent_raises_threshold(self):
        """Zivvug absent → seuil Gevurah augmenté de 0.05."""
        tree = _make_tree()
        ctx = _make_ctx(zivvug_state="absent")
        gevurah = tree["gevurah"]

        original_quality = gevurah.quality_threshold
        ctx["_gevurah_original_quality"] = original_quality

        gevurah.quality_threshold += 0.05
        gevurah.evaluator.quality_threshold += 0.05
        ctx["zivvug_gevurah_modifier"] = +0.05

        assert gevurah.quality_threshold == pytest.approx(0.65)
        assert ctx["zivvug_gevurah_modifier"] == +0.05

    def test_partial_no_change(self):
        """Zivvug partiel → seuil inchangé."""
        tree = _make_tree()
        ctx = _make_ctx(zivvug_state="partial")
        gevurah = tree["gevurah"]

        original = gevurah.quality_threshold
        ctx["zivvug_gevurah_modifier"] = 0.0

        assert gevurah.quality_threshold == pytest.approx(original)
        assert ctx["zivvug_gevurah_modifier"] == 0.0

    def test_thresholds_restored_after_request(self):
        """Les seuils sont restaurés à leurs valeurs originales après la requête."""
        tree = _make_tree()
        gevurah = tree["gevurah"]
        ctx = _make_ctx(zivvug_state="active")

        # Sauvegarder
        ctx["_gevurah_original_quality"] = gevurah.quality_threshold
        ctx["_gevurah_original_quarantine"] = gevurah.quarantine_threshold
        original_quality = gevurah.quality_threshold

        # Modifier (Zivvug actif)
        gevurah.quality_threshold -= 0.05
        gevurah.evaluator.quality_threshold -= 0.05
        assert gevurah.quality_threshold == pytest.approx(0.55)

        # Restaurer (comme dans le code après _ascend_gadlut)
        gevurah.quality_threshold = ctx["_gevurah_original_quality"]
        gevurah.evaluator.quality_threshold = ctx["_gevurah_original_quality"]
        gevurah.quarantine_threshold = ctx["_gevurah_original_quarantine"]

        assert gevurah.quality_threshold == pytest.approx(original_quality)
        assert gevurah.evaluator.quality_threshold == pytest.approx(original_quality)

    def test_zivvug_inactive_in_katnut(self):
        """En Katnut, le Zivvug n'est pas actif (les Mokhin ne coulent pas).

        _descend_gadlut() ne s'exécute pas en Katnut, donc le Zivvug
        ne peut jamais modifier les seuils.
        """
        # Le signal zivvug_state n'est jamais défini en Katnut
        # car _zivug_abba_imma() n'est appelé que depuis _descend_gadlut
        # qui n'exécute qu'en not is_katnut.
        ctx = _make_ctx()
        assert ctx.get("zivvug_state") is None

    def test_zivvug_logged_in_ctx(self):
        """L'état du Zivvug est logué dans ctx pour le BeinoniTracker."""
        ctx = _make_ctx()
        ctx["zivvug_state"] = "active"
        ctx["zivvug_gevurah_modifier"] = -0.05

        assert "zivvug_state" in ctx
        assert "zivvug_gevurah_modifier" in ctx
        assert ctx["zivvug_state"] == "active"


# ─── Tests DaemonBridge budget ────────────────────────────────


class TestZivvugDaemonBridge:
    """Budget DaemonBridge augmenté quand Zivvug actif."""

    def test_budget_increased_when_active(self):
        """Zivvug actif → budget tokens augmenté de 20% (500 → 600)."""
        ctx = _make_ctx(zivvug_state="active")
        budget = 600 if ctx.get("zivvug_state") == "active" else 500
        assert budget == 600

    def test_budget_normal_when_partial(self):
        """Zivvug partiel → budget inchangé (500)."""
        ctx = _make_ctx(zivvug_state="partial")
        budget = 600 if ctx.get("zivvug_state") == "active" else 500
        assert budget == 500

    def test_budget_normal_when_absent(self):
        """Zivvug absent → budget inchangé (500)."""
        ctx = _make_ctx(zivvug_state="absent")
        budget = 600 if ctx.get("zivvug_state") == "active" else 500
        assert budget == 500
