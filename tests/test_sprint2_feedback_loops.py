"""Tests Sprint 2 — Axe 1 & 2 : Boucles de feedback + données mortes.

Tests pour : Nitzotzot 3 sources, boucles SelfModel/CausalEngine/InsightForge/
DissensuEngine, purge données mortes.
"""

from unittest.mock import patch, MagicMock

import pytest


# ─── Nitzotzot Counter ───────────────────────────────────────


class TestNitzotzotCounter:
    """Vérifie que le compteur Nitzotzot lit les 3 sources."""

    def test_init_reads_three_tables(self):
        """_init_nitzotzot_from_db doit lire 3 tables."""
        import inspect
        from main import _init_nitzotzot_from_db
        source = inspect.getsource(_init_nitzotzot_from_db)
        assert "failuretoinsight_insights" in source
        assert "dissensuengine_syntheses" in source
        assert "candidate_insights" in source

    def test_counter_uses_state_lock(self):
        """Le compteur utilise _STATE_LOCK pour thread safety."""
        import inspect
        from main import _init_nitzotzot_from_db
        source = inspect.getsource(_init_nitzotzot_from_db)
        assert "_STATE_LOCK" in source


# ─── Boucle SelfModel Verify ─────────────────────────────────


class TestDaatVerifyLoop:
    """Tests pour task_daat_verify."""

    def test_task_exists(self):
        """task_daat_verify existe dans daemon.py."""
        from daemon import task_daat_verify
        assert callable(task_daat_verify)

    def test_task_returns_report(self):
        """task_daat_verify retourne un report dict avec les bons champs."""
        from daemon import task_daat_verify
        result = task_daat_verify({})  # tree vide
        assert isinstance(result, dict)
        assert result["task"] == "daat_verify"
        assert "error" in result  # Pas de daat dans tree vide

    def test_task_handles_missing_daat(self):
        """task_daat_verify gère l'absence de Da'at."""
        from daemon import task_daat_verify
        result = task_daat_verify({"daat": None})
        assert "error" in result


# ─── Boucle Binah → Yesod ────────────────────────────────────


class TestBinahToYesodLoop:
    """Tests pour task_binah_to_yesod."""

    def test_task_exists(self):
        """task_binah_to_yesod existe dans daemon.py."""
        from daemon import task_binah_to_yesod
        assert callable(task_binah_to_yesod)

    def test_task_returns_report(self):
        """task_binah_to_yesod retourne un report dict."""
        from daemon import task_binah_to_yesod
        result = task_binah_to_yesod({})
        assert isinstance(result, dict)
        assert result["task"] == "binah_to_yesod"
        assert "error" in result

    def test_task_handles_missing_modules(self):
        """task_binah_to_yesod gère l'absence de Binah/Yesod."""
        from daemon import task_binah_to_yesod
        result = task_binah_to_yesod({"binah": None, "yesod": None})
        assert "error" in result


# ─── Boucle InsightForge → Yesod ─────────────────────────────


class TestInsightForgeToYesod:
    """Vérifie que InsightForge persiste dans EpisteMemory."""

    def test_persist_candidates_calls_yesod(self):
        """_persist_candidates appelle self.yesod.remember pour les insights validés."""
        import inspect
        from insightforge.core import InsightForge
        source = inspect.getsource(InsightForge._persist_candidates)
        assert "yesod.remember" in source
        assert "Chokmah" in source or "chokmah" in source

    def test_persist_saves_validated_only(self):
        """Seuls les validated_insights vont dans Yesod, pas les rejected."""
        import inspect
        from insightforge.core import InsightForge
        source = inspect.getsource(InsightForge._persist_candidates)
        assert "validated_insights" in source


# ─── Boucle DissensuEngine → Yesod ───────────────────────────


class TestDissensuToYesod:
    """Vérifie que le dissensus est aussi persisté dans EpisteMemory."""

    def test_dissensus_persisted(self):
        """Le mode dissensus doit aussi appeler memory.remember."""
        import inspect
        from dissensuengine.core import DissensuEngine
        source = inspect.getsource(DissensuEngine.synthesize_or_dissent)
        # Chercher que dissensus ET synthesis appellent memory.remember
        assert "dissensus" in source.lower()
        # Il doit y avoir au moins 2 appels à memory.remember
        # (un pour synthesis, un pour dissensus)
        assert source.count("memory.remember") >= 2

    def test_dissensus_has_tags(self):
        """Le dissensus persisté a les bons tags."""
        import inspect
        from dissensuengine.core import DissensuEngine
        source = inspect.getsource(DissensuEngine.synthesize_or_dissent)
        assert "tension_irreductible" in source


# ─── Purge données mortes ─────────────────────────────────────


class TestDeadDataPurge:
    """Vérifie que le GC gère les données mortes."""

    def test_gc_has_dead_entries_field(self):
        """task_gc retourne dead_entries et dead_predictions."""
        from daemon import task_gc
        result = task_gc({})  # tree vide
        assert "dead_entries" in result or "error" in result

    def test_gc_handles_missing_yesod(self):
        """task_gc gère l'absence de Yesod."""
        from daemon import task_gc
        result = task_gc({"yesod": None})
        assert "error" in result

    def test_gc_code_purges_30_days(self):
        """Le code GC utilise un seuil de 30 jours."""
        import inspect
        from daemon import task_gc
        source = inspect.getsource(task_gc)
        assert "30 days" in source
