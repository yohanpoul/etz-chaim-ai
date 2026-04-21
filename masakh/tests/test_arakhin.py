"""Tests Arakhin — עֲרָכִין — recatégorisation dynamique.

Couvre :
  - evaluate_role pour chaque Olam
  - reformulate pour chaque rôle
  - transform (raccourci)
  - Cas d'erreur (Olam / rôle inconnus)
  - Variante orthographique atzilut / atziluth
  - Malkhut = fait brut non modifié
"""

import pytest

from masakh.arakhin import Arakhin, OLAM_TO_ROLE, VALID_ROLES, _TEMPLATES


# ── Fixtures ───────────────────────────────────────────────

@pytest.fixture
def arakhin():
    return Arakhin()


FACT = "Chaque composant doit être testable isolément"


# ── evaluate_role ──────────────────────────────────────────

class TestEvaluateRole:

    def test_atzilut_gives_keter(self, arakhin):
        assert arakhin.evaluate_role(FACT, "atzilut") == "keter"

    def test_atziluth_gives_keter(self, arakhin):
        """Variante orthographique avec h final."""
        assert arakhin.evaluate_role(FACT, "atziluth") == "keter"

    def test_briah_gives_binah(self, arakhin):
        assert arakhin.evaluate_role(FACT, "briah") == "binah"

    def test_yetzirah_gives_tiferet(self, arakhin):
        assert arakhin.evaluate_role(FACT, "yetzirah") == "tiferet"

    def test_assiah_gives_malkhut(self, arakhin):
        assert arakhin.evaluate_role(FACT, "assiah") == "malkhut"

    def test_unknown_task_type_raises(self, arakhin):
        with pytest.raises(ValueError, match="task_type inconnu"):
            arakhin.evaluate_role(FACT, "ein_sof")

    def test_all_olamot_covered(self):
        """Chaque Olam du mapping a un rôle valide."""
        for olam, role in OLAM_TO_ROLE.items():
            assert role in VALID_ROLES


# ── reformulate ────────────────────────────────────────────

class TestReformulate:

    def test_keter_adds_principle_prefix(self, arakhin):
        result = arakhin.reformulate(FACT, "keter")
        assert result == f"Le principe fondamental est : {FACT}"

    def test_binah_adds_framework_prefix(self, arakhin):
        result = arakhin.reformulate(FACT, "binah")
        assert result == f"Le framework à appliquer : {FACT}"

    def test_tiferet_adds_pattern_prefix(self, arakhin):
        result = arakhin.reformulate(FACT, "tiferet")
        assert result == f"Le pattern validé : {FACT}"

    def test_malkhut_returns_fact_unchanged(self, arakhin):
        result = arakhin.reformulate(FACT, "malkhut")
        assert result == FACT

    def test_unknown_role_raises(self, arakhin):
        with pytest.raises(ValueError, match="Rôle inconnu"):
            arakhin.reformulate(FACT, "gevurah")

    def test_all_roles_have_templates(self):
        """Chaque rôle valide a un template."""
        for role in VALID_ROLES:
            assert role in _TEMPLATES


# ── transform (raccourci) ─────────────────────────────────

class TestTransform:

    def test_atzilut_transform(self, arakhin):
        result = arakhin.transform(FACT, "atzilut")
        assert result.startswith("Le principe fondamental est :")
        assert FACT in result

    def test_briah_transform(self, arakhin):
        result = arakhin.transform(FACT, "briah")
        assert result.startswith("Le framework à appliquer :")

    def test_yetzirah_transform(self, arakhin):
        result = arakhin.transform(FACT, "yetzirah")
        assert result.startswith("Le pattern validé :")

    def test_assiah_transform(self, arakhin):
        result = arakhin.transform(FACT, "assiah")
        assert result == FACT

    def test_transform_equals_evaluate_then_reformulate(self, arakhin):
        """transform() = evaluate_role() + reformulate()."""
        for olam in ("atzilut", "briah", "yetzirah", "assiah"):
            role = arakhin.evaluate_role(FACT, olam)
            expected = arakhin.reformulate(FACT, role)
            assert arakhin.transform(FACT, olam) == expected

    def test_transform_unknown_raises(self, arakhin):
        with pytest.raises(ValueError):
            arakhin.transform(FACT, "adam_kadmon")


# ── Propriétés structurelles ──────────────────────────────

class TestStructural:

    def test_four_roles_exactly(self):
        assert len(VALID_ROLES) == 4

    def test_malkhut_template_is_identity(self):
        """Malkhut = le fait tel quel, sans transformation."""
        assert _TEMPLATES["malkhut"] == "{fact}"

    def test_each_role_mentions_fact(self):
        """Chaque template contient {fact}."""
        for role, tmpl in _TEMPLATES.items():
            assert "{fact}" in tmpl, f"Template {role} manque {{fact}}"
