"""Tests Sprint 4 — Axe 15 & 3 : Réseau fragmenté + Qliphoth actives.

Tests pour : connexions init_tree, triple validation, correction biais.
"""


# ─── Connexions réseau ────────────────────────────────────────


class TestInitTreeConnections:
    """Vérifie que les connexions manquantes sont maintenant injectées."""

    def test_dissensuengine_has_autojudge_attr(self):
        """DissensuEngine a l'attribut autojudge (pour injection tardive)."""
        from dissensuengine.core import DissensuEngine
        engine = DissensuEngine(db_url="postgresql://localhost/etz_chaim_test")
        assert hasattr(engine, "autojudge")
        engine.db.close()

    def test_autojudge_has_dissensus_attr(self):
        """AutoJudge a l'attribut dissensus (pour injection tardive)."""
        from autojudge.core import AutoJudge
        judge = AutoJudge(db_url="postgresql://localhost/etz_chaim_test")
        assert hasattr(judge, "dissensus")

    def test_explorationengine_has_dissensus_attr(self):
        """ExplorationEngine a l'attribut dissensus."""
        from explorationengine.core import ExplorationEngine
        engine = ExplorationEngine(db_url="postgresql://localhost/etz_chaim_test")
        assert hasattr(engine, "dissensus")
        assert hasattr(engine, "failuretoinsight")
        engine.db.close()

    def test_intentkeeper_has_exploration_attr(self):
        """IntentKeeper a l'attribut exploration."""
        from intentkeeper.core import IntentKeeper
        keeper = IntentKeeper(db_url="postgresql://localhost/etz_chaim_test")
        assert hasattr(keeper, "exploration")
        keeper.db.close()

    def test_init_tree_code_has_injections(self):
        """init_tree contient les injections tardives pour les 5 connexions."""
        import inspect
        from main import init_tree
        source = inspect.getsource(init_tree)
        assert "tiferet.autojudge = gevurah" in source
        assert "gevurah.dissensus = tiferet" in source
        assert "chesed.dissensus = tiferet" in source
        assert "chesed.failuretoinsight = lamed" in source
        assert "netzach.exploration = chesed" in source


# ─── Triple Validation InsightForge ───────────────────────────


class TestTripleValidation:
    """Vérifie que la triple validation est activée par défaut."""

    def test_default_is_true(self):
        """DEFAULT_HALLUCINATION_TRIPLE est True."""
        from insightforge.core import DEFAULT_HALLUCINATION_TRIPLE
        assert DEFAULT_HALLUCINATION_TRIPLE is True

    def test_forge_default_requires_triple(self):
        """InsightForge par défaut exige la triple validation."""
        from insightforge.core import InsightForge
        forge = InsightForge(db_url="postgresql://localhost/etz_chaim_test")
        assert forge.validator.require_triple is True
        forge.close()

    def test_override_still_works(self):
        """On peut encore override à False si explicitement demandé."""
        from insightforge.core import InsightForge
        forge = InsightForge(
            db_url="postgresql://localhost/etz_chaim_test",
            hallucination_triple_check=False,
        )
        assert forge.validator.require_triple is False
        forge.close()


# ─── Correction des biais ─────────────────────────────────────


class TestBiasCorrection:
    """Vérifie que task_daat_correct_biases existe et fonctionne."""

    def test_task_exists(self):
        """task_daat_correct_biases existe dans daemon.py."""
        from daemon import task_daat_correct_biases
        assert callable(task_daat_correct_biases)

    def test_task_returns_report(self):
        """Retourne un report dict avec les bons champs."""
        from daemon import task_daat_correct_biases
        result = task_daat_correct_biases({})
        assert isinstance(result, dict)
        assert result["task"] == "daat_correct_biases"
        assert "error" in result

    def test_task_handles_missing_daat(self):
        """Gère l'absence de Da'at."""
        from daemon import task_daat_correct_biases
        result = task_daat_correct_biases({"daat": None})
        assert "error" in result

    def test_task_in_daily_cycle(self):
        """task_daat_correct_biases est appelée dans le cycle quotidien."""
        import inspect
        from daemon import run_cycle
        source = inspect.getsource(run_cycle)
        assert "daat_correct" in source


# ─── Gamaliel-Anan (Yesod) — déjà adressé Sprint 2 ──────────


class TestGamalielAnan:
    """Vérifie que le GC gère les données mortes (Sprint 2)."""

    def test_gc_deprecates_dead_entries(self):
        """task_gc marque les entries mortes."""
        import inspect
        from daemon import task_gc
        source = inspect.getsource(task_gc)
        assert "access_count = 0" in source
        assert "30 days" in source
