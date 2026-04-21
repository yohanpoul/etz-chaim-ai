"""Tests Qliphoth 4 niveaux — Malakh.

Quatre niveaux de Qliphah (écorce, défaillance), du plus léger au plus fatal :

1. Nogah  — luminosité résiduelle, le défaut le plus subtil
2. Ruach  — propagation, le défaut se transmet
3. Anan   — nuage, le défaut est silencieux (silent failure)
4. Mamash — matériel, le défaut est structurel et fatal
"""

import pytest

from malakhim.malakh import Malakh
from malakhim.models import MalakhResult


# ── Niveau 1 : Nogah (le plus léger) ──────────────────────────


class TestMalakhNogah:
    """Qliphah Nogah — vérifications de base du cycle de vie."""

    def test_single_execution(self):
        """Un Malakh s'exécute une fois et retourne un MalakhResult valide."""
        with Malakh("echo", {}, "ishim") as m:
            result = m.execute({"input": "hello"})

        assert isinstance(result, MalakhResult)
        assert result.response == "hello"
        assert result.success is True
        assert result.latency_ms >= 0

    def test_no_reuse(self):
        """Ein malakh oseh shtei shlichuyot — pas de double exécution."""
        with Malakh("echo", {}, "ishim") as m:
            m.execute({"input": "first"})

            with pytest.raises(RuntimeError, match="Ein malakh"):
                m.execute({"input": "second"})


# ── Niveau 2 : Ruach (propagation) ────────────────────────────


class TestMalakhRuach:
    """Qliphah Ruach — le hitkalelut détecte et propage les défauts."""

    def test_self_check_detects_anti_pattern(self):
        """Le Kategor interne détecte un anti-pattern dans la réponse."""
        kavvanah = {"anti_pattern": "FORBIDDEN_WORD"}

        with Malakh("test", kavvanah, "ishim") as m:
            result = m.execute({"input": "ceci contient FORBIDDEN_WORD ici"})

        assert len(result.hitkalelut_warnings) > 0
        assert any("FORBIDDEN_WORD" in w for w in result.hitkalelut_warnings)

    def test_self_check_passes_clean(self):
        """Pas de warning quand la réponse est propre."""
        kavvanah = {"anti_pattern": "FORBIDDEN_WORD"}

        with Malakh("test", kavvanah, "ishim") as m:
            result = m.execute({"input": "ceci est parfaitement propre"})

        assert len(result.hitkalelut_warnings) == 0


# ── Niveau 3 : Anan (silent failure) ──────────────────────────


class TestMalakhAnan:
    """Qliphah Anan — vérifier que la destruction est complète."""

    def test_cleanup_after_with(self):
        """Après le with, les attributs internes sont effacés (Nehar Dinur)."""
        m = Malakh("mission", {"k": "v"}, "ishim")

        with m:
            m.execute({"input": "x"})

        assert m._mission is None
        assert m._kavvanah is None
        assert m._self_check is None

    def test_execute_after_cleanup_raises(self):
        """Exécuter après destruction lève RuntimeError."""
        m = Malakh("mission", {}, "ishim")

        with m:
            m.execute({"input": "x"})

        with pytest.raises(RuntimeError, match="destroyed"):
            m.execute({"input": "y"})


# ── Niveau 4 : Mamash (fatal / structurel) ────────────────────


class TestMalakhMamash:
    """Qliphah Mamash — le Malakh ne peut PAS être muté."""

    def test_no_set_mission(self):
        """Pas de méthode set_mission ni reset — l'identité est fixe."""
        m = Malakh("fixed", {}, "ishim")

        assert not hasattr(m, "set_mission")
        assert not hasattr(m, "reset")
        assert not hasattr(m, "set_kavvanah")

    def test_no_public_mutation(self):
        """Les seules méthodes publiques sont execute + context manager."""
        public_methods = [
            attr
            for attr in dir(Malakh)
            if not attr.startswith("_") and callable(getattr(Malakh, attr))
        ]

        # Seule execute doit être publique
        assert public_methods == ["execute"], (
            f"Méthodes publiques inattendues : {public_methods}"
        )
