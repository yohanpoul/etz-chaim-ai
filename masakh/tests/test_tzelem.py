"""Tests du Tzelem — Moule archetypal.

Couvre :
  - detect pour chaque combinaison Olam/Kavvanah
  - apply produit l'instruction correcte
  - Cas limites (pas de kavvanah, olam inconnu)
  - Les 5 templates
"""

import pytest

from masakh.tzelem import Tzelem, TEMPLATES, _OLAM_DEFAULT


class TestDetect:

    def test_exploration_keyword(self):
        tz = Tzelem()
        assert tz.detect({"intention": "explorer les possibilites"}, "briah") == "exploration"

    def test_audit_keyword(self):
        tz = Tzelem()
        assert tz.detect({"intention": "audit du systeme"}, "assiah") == "audit"

    def test_analyse_keyword(self):
        tz = Tzelem()
        assert tz.detect({"intention": "analyser le code source"}, "yetzirah") == "analyse_technique"

    def test_implementation_keyword(self):
        tz = Tzelem()
        assert tz.detect({"intention": "implementer la feature"}, "briah") == "implementation"

    def test_dialogue_keyword(self):
        tz = Tzelem()
        assert tz.detect({"intention": "comparer les architectures"}, "briah") == "dialogue_erudit"

    def test_no_kavvanah_atziluth(self):
        tz = Tzelem()
        assert tz.detect(None, "atziluth") == "analyse_technique"

    def test_no_kavvanah_briah(self):
        tz = Tzelem()
        assert tz.detect(None, "briah") == "dialogue_erudit"

    def test_no_kavvanah_yetzirah(self):
        tz = Tzelem()
        assert tz.detect(None, "yetzirah") == "implementation"

    def test_no_kavvanah_assiah(self):
        tz = Tzelem()
        assert tz.detect(None, "assiah") == "implementation"

    def test_empty_intention_falls_to_olam(self):
        tz = Tzelem()
        assert tz.detect({"intention": ""}, "briah") == "dialogue_erudit"

    def test_unknown_olam_defaults_to_implementation(self):
        tz = Tzelem()
        assert tz.detect(None, "unknown_world") == "implementation"

    def test_kavvanah_without_intention(self):
        tz = Tzelem()
        assert tz.detect({"critere_succes": "ok"}, "briah") == "dialogue_erudit"


class TestApply:

    def test_all_templates_exist(self):
        assert len(TEMPLATES) == 5

    def test_apply_analyse_technique(self):
        tz = Tzelem()
        result = tz.apply("analyse_technique")
        assert "[TZELEM]" in result
        assert "diagnostic" in result.lower()

    def test_apply_dialogue_erudit(self):
        tz = Tzelem()
        result = tz.apply("dialogue_erudit")
        assert "sources" in result.lower()

    def test_apply_implementation(self):
        tz = Tzelem()
        result = tz.apply("implementation")
        assert "code" in result.lower()

    def test_apply_exploration(self):
        tz = Tzelem()
        result = tz.apply("exploration")
        assert "hypotheses" in result.lower()

    def test_apply_audit(self):
        tz = Tzelem()
        result = tz.apply("audit")
        assert "metriques" in result.lower()

    def test_apply_unknown_raises(self):
        tz = Tzelem()
        with pytest.raises(ValueError, match="Tzelem inconnu"):
            tz.apply("nonexistent")

    def test_apply_format(self):
        """Chaque apply retourne [TZELEM] ... [/TZELEM]."""
        tz = Tzelem()
        for name in TEMPLATES:
            result = tz.apply(name)
            assert result.startswith("[TZELEM]")
            assert result.endswith("[/TZELEM]")
