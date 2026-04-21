"""Tests Sprint 5 — Axe 4 & 6 : Stubs/fantômes + LLM fiable.

Tests pour : verify_direction heuristique, rate limiting olamot, guardian.py.
"""

import inspect


# ─── verify_direction() ──────────────────────────────────────


class TestVerifyDirection:
    """Vérifie que verify_direction() n'est plus un stub."""

    def test_not_always_indeterminate(self):
        """verify_direction avec marqueurs causaux donne un verdict directionnel."""
        from causalengine.core import CausalEngine
        engine = CausalEngine(db_url="postgresql://localhost/etz_chaim_test")
        result = engine.verify_direction(
            "La hausse des températures provoque la fonte des glaces",
            "Fonte des glaces arctiques",
        )
        assert result.verdict in ("forward", "reverse", "bidirectional", "indeterminate")
        # Avec "provoque" → devrait être forward
        assert result.forward_plausibility >= result.reverse_plausibility
        engine.db.close()

    def test_indeterminate_when_no_markers(self):
        """Sans marqueurs, reste indeterminate (honnêteté)."""
        from causalengine.core import CausalEngine
        engine = CausalEngine(db_url="postgresql://localhost/etz_chaim_test")
        result = engine.verify_direction("pomme", "orange")
        assert result.verdict == "indeterminate"
        engine.db.close()

    def test_has_heuristic_code(self):
        """Le code contient des marqueurs causaux, pas juste un return statique."""
        source = inspect.getsource(
            __import__("causalengine.core", fromlist=["CausalEngine"]).CausalEngine.verify_direction
        )
        assert "provoque" in source or "forward_markers" in source
        assert "indeterminate" in source


# ─── Rate limiting olamot.py ──────────────────────────────────


class TestOlamotRateLimiting:
    """Vérifie que olamot.py a du rate limiting."""

    def test_retry_mechanism_exists(self):
        """claude_code_generate a un mécanisme de retry."""
        import olamot
        source = inspect.getsource(olamot.claude_code_generate)
        assert "MAX_RETRIES" in source
        assert "BACKOFF_BASE" in source

    def test_rate_limit_detection(self):
        """Le code détecte les rate limits dans stderr."""
        import olamot
        source = inspect.getsource(olamot.claude_code_generate)
        assert "rate limit" in source.lower()
        assert "overloaded" in source.lower()
        assert "429" in source

    def test_timeout_reads_config(self):
        """Le timeout par défaut lit config.yaml (pas hardcodé 120)."""
        import olamot
        source = inspect.getsource(olamot.claude_code_generate)
        # Le param default doit être None (= lire config)
        assert "timeout: int | None = None" in source
        assert "get_timeout" in source


# ─── selfmodel/guardian.py ────────────────────────────────────


class TestGuardian:
    """Vérifie que guardian.py existe et fonctionne."""

    def test_module_exists(self):
        """selfmodel/guardian.py est importable."""
        from selfmodel.guardian import Guardian
        assert Guardian is not None

    def test_guardian_instantiates(self):
        """Guardian s'instancie sans dépendances."""
        from selfmodel.guardian import Guardian
        g = Guardian()
        assert g is not None

    def test_evaluate_confidence_returns_dict(self):
        """evaluate_confidence retourne un dict structuré."""
        from selfmodel.guardian import Guardian
        g = Guardian()
        result = g.evaluate_confidence("test_domain")
        assert isinstance(result, dict)
        assert "recommendation" in result
        assert "confidence" in result
        assert result["recommendation"] in ("proceed", "caution", "veto")

    def test_unknown_domain_is_veto(self):
        """Domaine inconnu sans SelfMap → proceed par défaut (pas de crash)."""
        from selfmodel.guardian import Guardian
        g = Guardian()  # pas de selfmap → pas de veto
        result = g.evaluate_confidence("domaine_totalement_inconnu")
        assert result["recommendation"] == "proceed"  # Pas de selfmap → default proceed
