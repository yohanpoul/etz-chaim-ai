"""Tests des Syzygies — SY 4:2-3.

Vérifie :
  - Les 7 définitions sont complètes et cohérentes
  - assess_syzygy_with_score produit dagesh/rafeh correctement
  - Le pont vers les Qliphoth fonctionne
  - get_balance produit un BalanceState cohérent
  - Les seuils sont correctement appliqués
"""

import pytest

from kabbalah.syzygies import (
    Syzygies,
    SyzygyDef,
    SyzygyState,
    BalanceState,
    SYZYGY_DEFS,
    MODULE_THRESHOLDS,
)


@pytest.fixture
def syz():
    # Sans DB — toutes les évaluations retomberont en rafeh (pas de données)
    return Syzygies(db_url="")


# ═══════════════════════════════════════════════════════════════
# DÉFINITIONS — 7 paires complètes
# ═══════════════════════════════════════════════════════════════

class TestDefinitions:
    def test_7_syzygies(self):
        assert len(SYZYGY_DEFS) == 7

    def test_7_thresholds(self):
        assert len(MODULE_THRESHOLDS) == 7

    def test_all_modules_have_thresholds(self):
        for module in SYZYGY_DEFS:
            assert module in MODULE_THRESHOLDS

    def test_all_have_hebrew(self):
        for module, defn in SYZYGY_DEFS.items():
            assert defn.hebrew, f"{module} manque hebrew"
            assert defn.dagesh_hebrew, f"{module} manque dagesh_hebrew"
            assert defn.rafeh_hebrew, f"{module} manque rafeh_hebrew"

    def test_all_have_qliphah(self):
        for module, defn in SYZYGY_DEFS.items():
            assert defn.qliphah, f"{module} manque qliphah"
            assert defn.sephirah, f"{module} manque sephirah"

    EXPECTED_LETTERS = {
        "insightforge": "beth",
        "epistememory": "gimel",
        "explorationengine": "daleth",
        "hitbonenut": "kaph",
        "autojudge": "peh",
        "dissensuengine": "resh",
        "selfmap": "tav",
    }

    @pytest.mark.parametrize("module,letter", list(EXPECTED_LETTERS.items()))
    def test_letter_mapping(self, module, letter):
        assert SYZYGY_DEFS[module].letter == letter

    EXPECTED_OPPOSITES = {
        "insightforge": ("sagesse", "folie"),
        "epistememory": ("richesse", "pauvreté"),
        "explorationengine": ("fertilité", "désolation"),
        "hitbonenut": ("vie", "mort"),
        "autojudge": ("domination", "servitude"),
        "dissensuengine": ("paix", "guerre"),
        "selfmap": ("grâce", "laideur"),
    }

    @pytest.mark.parametrize("module,pair", list(EXPECTED_OPPOSITES.items()))
    def test_opposites(self, module, pair):
        dagesh, rafeh = pair
        defn = SYZYGY_DEFS[module]
        assert defn.dagesh == dagesh
        assert defn.rafeh == rafeh


# ═══════════════════════════════════════════════════════════════
# ASSESS_SYZYGY_WITH_SCORE — Évaluation directe
# ═══════════════════════════════════════════════════════════════

class TestAssessWithScore:
    def test_high_score_is_dagesh(self, syz):
        state = syz.assess_syzygy_with_score("insightforge", 0.80)
        assert state.side == "dagesh"
        assert state.attribute == "sagesse"
        assert state.qliphah_active is False

    def test_low_score_is_rafeh(self, syz):
        state = syz.assess_syzygy_with_score("insightforge", 0.10)
        assert state.side == "rafeh"
        assert state.attribute == "folie"
        assert state.qliphah_active is True
        assert state.qliphah_name == "ghagiel"

    def test_middle_score_is_dagesh(self, syz):
        """Entre les seuils → dagesh (fragile mais positif)."""
        state = syz.assess_syzygy_with_score("insightforge", 0.30)
        assert state.side == "dagesh"

    def test_unknown_module_raises(self, syz):
        with pytest.raises(KeyError, match="inconnu"):
            syz.assess_syzygy_with_score("unknown", 0.5)

    def test_all_modules_dagesh(self, syz):
        for module in SYZYGY_DEFS:
            state = syz.assess_syzygy_with_score(module, 0.90)
            assert state.side == "dagesh"

    def test_all_modules_rafeh(self, syz):
        for module in SYZYGY_DEFS:
            state = syz.assess_syzygy_with_score(module, 0.01)
            assert state.side == "rafeh"
            assert state.qliphah_active is True


# ═══════════════════════════════════════════════════════════════
# ASSESS_SYZYGY — Sans DB (rafeh par défaut)
# ═══════════════════════════════════════════════════════════════

class TestAssessWithoutDB:
    def test_no_db_returns_rafeh(self, syz):
        """Sans DB, pas de données → côté rafeh par prudence."""
        state = syz.assess_syzygy("insightforge")
        assert state.side == "rafeh"
        assert state.score == 0.0
        assert "Pas de données" in state.detail

    def test_unknown_module_raises(self, syz):
        with pytest.raises(KeyError):
            syz.assess_syzygy("nonexistent")


# ═══════════════════════════════════════════════════════════════
# PONT QLIPHOTH
# ═══════════════════════════════════════════════════════════════

class TestQliphothBridge:
    def test_rafeh_activates_qliphah(self, syz):
        """Le côté rafeh d'une syzygie = Qliphah active."""
        state = syz.assess_syzygy_with_score("autojudge", 0.05)
        assert state.qliphah_active is True
        assert state.qliphah_name == "golachab"

    def test_dagesh_no_qliphah(self, syz):
        state = syz.assess_syzygy_with_score("selfmap", 0.80)
        assert state.qliphah_active is False

    def test_insightforge_qliphah_is_ghagiel(self, syz):
        """InsightForge en folie → Ghagiel (Qliphah de Chokmah)."""
        state = syz.assess_syzygy_with_score("insightforge", 0.05)
        assert state.qliphah_name == "ghagiel"
        assert SYZYGY_DEFS["insightforge"].sephirah == "chokmah"


# ═══════════════════════════════════════════════════════════════
# BALANCE — Vue d'ensemble
# ═══════════════════════════════════════════════════════════════

class TestBalance:
    def test_no_db_all_rafeh(self, syz):
        """Sans DB → tous en rafeh."""
        balance = syz.get_balance()
        assert balance.rafeh_count == 7
        assert balance.dagesh_count == 0
        assert balance.harmony == 0.0

    def test_to_dict(self, syz):
        balance = syz.get_balance()
        d = balance.to_dict()
        assert "dagesh_count" in d
        assert "syzygies" in d
        assert len(d["syzygies"]) == 7


# ═══════════════════════════════════════════════════════════════
# SERIALIZATION
# ═══════════════════════════════════════════════════════════════

class TestSerialization:
    def test_syzygy_state_to_dict(self, syz):
        state = syz.assess_syzygy_with_score("hitbonenut", 0.70)
        d = state.to_dict()
        assert d["module"] == "hitbonenut"
        assert d["letter"] == "kaph"
        assert d["hebrew"] == "כ"
        assert d["side"] == "dagesh"
        assert d["attribute"] == "vie"
        assert d["qliphah_active"] is False
        assert d["qliphah_name"] is None  # pas active

    def test_all_definitions(self):
        defs = Syzygies.get_all_definitions()
        assert len(defs) == 7
        for module, d in defs.items():
            assert "dagesh" in d
            assert "rafeh" in d
            assert "qliphah" in d
