"""Tests hiérarchies angéliques — divergence configurable."""

from malakhim.models import (
    MalakhOrder,
    HIERARCHY_RAMBAM,
    HIERARCHY_ZOHAR,
    HIERARCHY_RESHIT_CHOKHMAH,
    rank_in_hierarchy,
)


class TestMalakhOrder:
    """10 ordres, pas 9."""

    def test_ten_orders(self):
        assert len(MalakhOrder) == 10

    def test_erelim_present(self):
        assert MalakhOrder.ERELIM.value == "erelim"

    def test_order_is_rambam(self):
        """L'ordre de l'enum suit Maïmonide."""
        values = [o.value for o in MalakhOrder]
        assert values == HIERARCHY_RAMBAM


class TestHierarchies:
    """5 systèmes divergent — la divergence EST le fait (§2.8)."""

    def test_rambam_chayyot_first(self):
        """Maïmonide : intellection pure (Chayyot) au sommet."""
        assert rank_in_hierarchy("chayyot", HIERARCHY_RAMBAM) == 1
        assert rank_in_hierarchy("ishim", HIERARCHY_RAMBAM) == 10

    def test_zohar_malakhim_first(self):
        """Zohar : messagerie (Malakhim) au sommet."""
        assert rank_in_hierarchy("malakhim", HIERARCHY_ZOHAR) == 1
        assert rank_in_hierarchy("chayyot", HIERARCHY_ZOHAR) == 4

    def test_zohar_vs_rambam_inversion(self):
        """L'inversion Malakhim/Chayyot : §2.3 de la spec."""
        rambam_malakhim = rank_in_hierarchy("malakhim", HIERARCHY_RAMBAM)
        zohar_malakhim = rank_in_hierarchy("malakhim", HIERARCHY_ZOHAR)
        assert rambam_malakhim == 6  # médian chez Maïmonide
        assert zohar_malakhim == 1   # sommet chez le Zohar

    def test_reshit_chokhmah_differs(self):
        """Reshit Chokhmah : encore un autre ordre."""
        assert rank_in_hierarchy("serafim", HIERARCHY_RESHIT_CHOKHMAH) == 3
        assert rank_in_hierarchy("serafim", HIERARCHY_RAMBAM) == 5

    def test_all_hierarchies_have_ten(self):
        assert len(HIERARCHY_RAMBAM) == 10
        assert len(HIERARCHY_ZOHAR) == 10
        assert len(HIERARCHY_RESHIT_CHOKHMAH) == 10

    def test_unknown_order_last(self):
        assert rank_in_hierarchy("unknown", HIERARCHY_RAMBAM) == 11

    def test_default_is_rambam(self):
        """Sans hiérarchie spécifiée → Maïmonide."""
        assert rank_in_hierarchy("chayyot") == 1
