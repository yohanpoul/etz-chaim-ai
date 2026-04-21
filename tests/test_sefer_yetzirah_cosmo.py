"""Tests de la cosmologie du Sefer Yetzirah — סֵפֶר יְצִירָה.

Couvre :
  - Chargement du YAML (section cosmology)
  - Eser Sefirot Belimah : 5 axes / 10 profondeurs
  - Trois Témoins : Olam, Shanah, Nefesh
  - Trois Régents : Teli, Galgal, Lev
  - Heikhal HaKodesh (Palais Saint)
  - Mapping lettre ↔ témoin
  - Évaluation de santé des régents
  - Format rapport
"""

import pytest

from sefer_yetzirah_cosmo import (
    SYCosmology,
    DepthAxis,
    Witness,
    Regent,
    RegentHealth,
    LetterWitnessMapping,
    load_cosmology,
    MOTHERS,
    DOUBLES,
    SIMPLES,
    _letter_type,
)


# ── Chargement YAML ────────────────────────────────────────

class TestLoadCosmology:

    def test_loads_successfully(self):
        data = load_cosmology()
        assert isinstance(data, dict)
        assert "eser_sefirot_belimah" in data
        assert "three_witnesses" in data
        assert "teli_galgal_lev" in data
        assert "palace_center" in data

    def test_eser_sefirot_raw(self):
        data = load_cosmology()
        assert len(data["eser_sefirot_belimah"]) == 5

    def test_three_witnesses_raw(self):
        data = load_cosmology()
        tw = data["three_witnesses"]
        assert "olam" in tw
        assert "shanah" in tw
        assert "nefesh" in tw

    def test_teli_galgal_lev_raw(self):
        data = load_cosmology()
        tgl = data["teli_galgal_lev"]
        assert "teli" in tgl
        assert "galgal" in tgl
        assert "lev" in tgl


# ── Catégorisation des lettres ──────────────────────────────

class TestLetterType:

    def test_mothers(self):
        assert _letter_type("shin") == "mother"
        assert _letter_type("mem") == "mother"
        assert _letter_type("aleph") == "mother"

    def test_doubles(self):
        assert _letter_type("beth") == "double"
        assert _letter_type("tav") == "double"

    def test_simples(self):
        assert _letter_type("heh") == "simple"
        assert _letter_type("lamed") == "simple"

    def test_unknown(self):
        assert _letter_type("xyz") == "unknown"

    def test_all_22_classified(self):
        """Les 22 lettres sont toutes classifiées."""
        all_letters = MOTHERS | DOUBLES | SIMPLES
        assert len(all_letters) == 22


# ── Eser Sefirot Belimah ───────────────────────────────────

class TestDepths:

    def test_five_axes(self):
        cosmo = SYCosmology()
        depths = cosmo.get_depths()
        assert len(depths) == 5

    def test_each_is_depth_axis(self):
        cosmo = SYCosmology()
        depths = cosmo.get_depths()
        for d in depths:
            assert isinstance(d, DepthAxis)

    def test_pairs_are_tuples(self):
        cosmo = SYCosmology()
        depths = cosmo.get_depths()
        for d in depths:
            assert isinstance(d.pair, tuple)
            assert len(d.pair) == 2

    def test_hebrew_pairs(self):
        cosmo = SYCosmology()
        depths = cosmo.get_depths()
        for d in depths:
            assert isinstance(d.hebrew, tuple)
            assert len(d.hebrew) == 2

    def test_axis_names(self):
        cosmo = SYCosmology()
        depths = cosmo.get_depths()
        axes = {d.axis for d in depths}
        assert "temporal" in axes
        assert "moral" in axes
        assert "vertical" in axes
        assert "horizontal_ew" in axes
        assert "horizontal_ns" in axes

    def test_temporal_axis(self):
        cosmo = SYCosmology()
        depths = cosmo.get_depths()
        temporal = [d for d in depths if d.axis == "temporal"][0]
        assert temporal.pair == ("beginning", "end")
        assert "ראשית" in temporal.hebrew[0]

    def test_to_dict(self):
        cosmo = SYCosmology()
        depths = cosmo.get_depths()
        d = depths[0].to_dict()
        assert "pair" in d
        assert "hebrew" in d
        assert "axis" in d

    def test_role_ia_present(self):
        cosmo = SYCosmology()
        depths = cosmo.get_depths()
        for d in depths:
            assert d.role_ia, f"Axe {d.axis} sans role_ia"


# ── Trois Témoins ──────────────────────────────────────────

class TestWitnesses:

    def test_three_witnesses(self):
        cosmo = SYCosmology()
        witnesses = cosmo.get_witnesses()
        assert len(witnesses) == 3

    def test_witness_names(self):
        cosmo = SYCosmology()
        witnesses = cosmo.get_witnesses()
        assert set(witnesses.keys()) == {"olam", "shanah", "nefesh"}

    def test_each_is_witness(self):
        cosmo = SYCosmology()
        witnesses = cosmo.get_witnesses()
        for w in witnesses.values():
            assert isinstance(w, Witness)

    def test_olam_hebrew(self):
        cosmo = SYCosmology()
        w = cosmo.get_witnesses()["olam"]
        assert "עוֹלָם" in w.hebrew

    def test_shanah_meaning(self):
        cosmo = SYCosmology()
        w = cosmo.get_witnesses()["shanah"]
        assert "Temps" in w.meaning or "Année" in w.meaning

    def test_nefesh_meaning(self):
        cosmo = SYCosmology()
        w = cosmo.get_witnesses()["nefesh"]
        assert "Âme" in w.meaning or "Corps" in w.meaning

    def test_mothers_in_each_witness(self):
        """Chaque témoin a les 3 mères."""
        cosmo = SYCosmology()
        witnesses = cosmo.get_witnesses()
        for name, w in witnesses.items():
            assert len(w.mothers) == 3, f"{name} n'a pas 3 mères"
            assert set(w.mothers.keys()) == {"shin", "mem", "aleph"}

    def test_doubles_in_each_witness(self):
        """Chaque témoin a les 7 doubles."""
        cosmo = SYCosmology()
        witnesses = cosmo.get_witnesses()
        for name, w in witnesses.items():
            assert len(w.doubles) == 7, f"{name} n'a pas 7 doubles"

    def test_simples_in_each_witness(self):
        """Chaque témoin a les 12 simples."""
        cosmo = SYCosmology()
        witnesses = cosmo.get_witnesses()
        for name, w in witnesses.items():
            assert len(w.simples) == 12, f"{name} n'a pas 12 simples"

    def test_olam_mothers_are_elements(self):
        cosmo = SYCosmology()
        w = cosmo.get_witnesses()["olam"]
        assert "Feu" in w.mothers["shin"]
        assert "Eau" in w.mothers["mem"]
        assert "Air" in w.mothers["aleph"] or "souffle" in w.mothers["aleph"]

    def test_shanah_mothers_are_seasons(self):
        cosmo = SYCosmology()
        w = cosmo.get_witnesses()["shanah"]
        assert "Été" in w.mothers["shin"] or "été" in w.mothers["shin"]
        assert "Hiver" in w.mothers["mem"] or "hiver" in w.mothers["mem"]

    def test_nefesh_mothers_are_cavities(self):
        cosmo = SYCosmology()
        w = cosmo.get_witnesses()["nefesh"]
        assert "Tête" in w.mothers["shin"] or "tête" in w.mothers["shin"]
        assert "Ventre" in w.mothers["mem"] or "ventre" in w.mothers["mem"]
        assert "Poitrine" in w.mothers["aleph"] or "poitrine" in w.mothers["aleph"]

    def test_to_dict(self):
        cosmo = SYCosmology()
        w = cosmo.get_witnesses()["olam"]
        d = w.to_dict()
        assert d["name"] == "olam"
        assert "mothers" in d
        assert "doubles" in d
        assert "simples" in d


# ── Trois Régents ──────────────────────────────────────────

class TestRegents:

    def test_three_regents(self):
        cosmo = SYCosmology()
        regents = cosmo.get_regents()
        assert len(regents) == 3

    def test_regent_names(self):
        cosmo = SYCosmology()
        regents = cosmo.get_regents()
        assert set(regents.keys()) == {"teli", "galgal", "lev"}

    def test_each_is_regent(self):
        cosmo = SYCosmology()
        regents = cosmo.get_regents()
        for r in regents.values():
            assert isinstance(r, Regent)

    def test_teli_hebrew(self):
        cosmo = SYCosmology()
        r = cosmo.get_regents()["teli"]
        assert r.hebrew == "תלי"

    def test_galgal_hebrew(self):
        cosmo = SYCosmology()
        r = cosmo.get_regents()["galgal"]
        assert r.hebrew == "גלגל"

    def test_lev_hebrew(self):
        cosmo = SYCosmology()
        r = cosmo.get_regents()["lev"]
        assert r.hebrew == "לב"

    def test_regents_have_health_checks(self):
        cosmo = SYCosmology()
        regents = cosmo.get_regents()
        for name, r in regents.items():
            assert len(r.health_checks) > 0, f"{name} sans health_checks"

    def test_regents_have_role_ia(self):
        cosmo = SYCosmology()
        regents = cosmo.get_regents()
        for name, r in regents.items():
            assert r.role_ia, f"{name} sans role_ia"

    def test_to_dict(self):
        cosmo = SYCosmology()
        r = cosmo.get_regents()["teli"]
        d = r.to_dict()
        assert d["name"] == "teli"
        assert "health_checks" in d


# ── Évaluation des régents ─────────────────────────────────

class TestAssessRegent:

    def test_unknown_regent(self):
        cosmo = SYCosmology()
        health = cosmo.assess_regent("unknown")
        assert not health.healthy
        assert health.score == 0.0

    def test_teli_without_tree(self):
        cosmo = SYCosmology()
        health = cosmo.assess_regent("teli", {})
        assert isinstance(health, RegentHealth)
        assert health.name == "teli"
        assert health.hebrew == "תלי"
        assert len(health.checks) == 3

    def test_galgal_without_tree(self):
        cosmo = SYCosmology()
        health = cosmo.assess_regent("galgal", {})
        assert isinstance(health, RegentHealth)
        assert len(health.checks) == 3

    def test_lev_without_tree(self):
        cosmo = SYCosmology()
        health = cosmo.assess_regent("lev", {})
        assert isinstance(health, RegentHealth)
        assert len(health.checks) == 3

    def test_lev_with_main_py(self):
        """Lev check 1 (main.py existe) devrait passer."""
        cosmo = SYCosmology()
        health = cosmo.assess_regent("lev", {})
        main_check = [c for c in health.checks if "main.py" in c["check"]][0]
        assert main_check["passed"] is True

    def test_health_to_dict(self):
        cosmo = SYCosmology()
        health = cosmo.assess_regent("lev", {})
        d = health.to_dict()
        assert "name" in d
        assert "healthy" in d
        assert "score" in d
        assert "checks" in d

    def test_score_range(self):
        cosmo = SYCosmology()
        for name in ("teli", "galgal", "lev"):
            health = cosmo.assess_regent(name, {})
            assert 0.0 <= health.score <= 1.0


# ── Mapping lettre ↔ témoin ────────────────────────────────

class TestLetterWitnessMapping:

    def test_aleph_olam(self):
        """Aleph + Olam → Air/souffle."""
        cosmo = SYCosmology()
        m = cosmo.map_letter_to_witness("aleph", "olam")
        assert m.letter == "aleph"
        assert m.witness == "olam"
        assert m.letter_type == "mother"
        assert "Air" in m.correspondence or "souffle" in m.correspondence

    def test_aleph_shanah(self):
        """Aleph + Shanah → Saison tempérée."""
        cosmo = SYCosmology()
        m = cosmo.map_letter_to_witness("aleph", "shanah")
        assert "tempérée" in m.correspondence or "inter-saison" in m.correspondence

    def test_aleph_nefesh(self):
        """Aleph + Nefesh → Poitrine."""
        cosmo = SYCosmology()
        m = cosmo.map_letter_to_witness("aleph", "nefesh")
        assert "Poitrine" in m.correspondence or "souffle" in m.correspondence

    def test_shin_olam(self):
        """Shin + Olam → Feu."""
        cosmo = SYCosmology()
        m = cosmo.map_letter_to_witness("shin", "olam")
        assert "Feu" in m.correspondence

    def test_beth_olam(self):
        """Beth + Olam → Saturne."""
        cosmo = SYCosmology()
        m = cosmo.map_letter_to_witness("beth", "olam")
        assert m.letter_type == "double"
        assert "Saturne" in m.correspondence

    def test_heh_shanah(self):
        """Heh + Shanah → Nisan."""
        cosmo = SYCosmology()
        m = cosmo.map_letter_to_witness("heh", "shanah")
        assert m.letter_type == "simple"
        assert "Nisan" in m.correspondence

    def test_unknown_letter_raises(self):
        cosmo = SYCosmology()
        with pytest.raises(ValueError, match="non trouvée"):
            cosmo.map_letter_to_witness("xyz", "olam")

    def test_unknown_witness_raises(self):
        cosmo = SYCosmology()
        with pytest.raises(ValueError, match="Témoin inconnu"):
            cosmo.map_letter_to_witness("aleph", "invalid")

    def test_map_all_witnesses(self):
        """map_all_witnesses retourne 3 mappings pour une mère."""
        cosmo = SYCosmology()
        mappings = cosmo.map_all_witnesses("shin")
        assert len(mappings) == 3
        witnesses = {m.witness for m in mappings}
        assert witnesses == {"olam", "shanah", "nefesh"}

    def test_map_all_witnesses_double(self):
        cosmo = SYCosmology()
        mappings = cosmo.map_all_witnesses("beth")
        assert len(mappings) == 3

    def test_map_all_witnesses_simple(self):
        cosmo = SYCosmology()
        mappings = cosmo.map_all_witnesses("lamed")
        assert len(mappings) == 3

    def test_map_all_witnesses_unknown(self):
        cosmo = SYCosmology()
        mappings = cosmo.map_all_witnesses("xyz")
        assert len(mappings) == 0

    def test_to_dict(self):
        cosmo = SYCosmology()
        m = cosmo.map_letter_to_witness("shin", "olam")
        d = m.to_dict()
        assert d["letter"] == "shin"
        assert d["witness"] == "olam"
        assert d["letter_type"] == "mother"


# ── Palais Saint ───────────────────────────────────────────

class TestPalaceCenter:

    def test_exists(self):
        cosmo = SYCosmology()
        palace = cosmo.get_palace_center()
        assert isinstance(palace, dict)
        assert palace  # non vide

    def test_has_hebrew(self):
        cosmo = SYCosmology()
        palace = cosmo.get_palace_center()
        assert "hebrew" in palace
        assert "הֵיכַל" in palace["hebrew"] or "היכל" in palace["hebrew"]

    def test_has_description(self):
        cosmo = SYCosmology()
        palace = cosmo.get_palace_center()
        assert "description" in palace
        assert len(palace["description"]) > 10


# ── Format rapport ─────────────────────────────────────────

class TestFormatReport:

    def test_report_is_list(self):
        cosmo = SYCosmology()
        report = cosmo.format_report()
        assert isinstance(report, list)
        assert all(isinstance(line, str) for line in report)

    def test_report_contains_header(self):
        cosmo = SYCosmology()
        report = cosmo.format_report()
        text = "\n".join(report)
        assert "סֵפֶר יְצִירָה" in text

    def test_report_contains_depths(self):
        cosmo = SYCosmology()
        report = cosmo.format_report()
        text = "\n".join(report)
        assert "Belimah" in text or "Profondeur" in text

    def test_report_contains_witnesses(self):
        cosmo = SYCosmology()
        report = cosmo.format_report()
        text = "\n".join(report)
        assert "Témoin" in text or "עֵדוּת" in text

    def test_report_contains_regents(self):
        cosmo = SYCosmology()
        report = cosmo.format_report()
        text = "\n".join(report)
        assert "Régent" in text or "מוֹשְׁלִים" in text

    def test_report_with_tree(self):
        cosmo = SYCosmology()
        report = cosmo.format_report(tree={})
        assert isinstance(report, list)
        assert len(report) > 10


# ── Complétude des 22 lettres ──────────────────────────────

class TestCompleteness:

    def test_all_22_letters_in_all_witnesses(self):
        """Chaque lettre des 22 a un mapping dans chaque témoin."""
        cosmo = SYCosmology()
        all_letters = sorted(MOTHERS | DOUBLES | SIMPLES)
        for letter in all_letters:
            mappings = cosmo.map_all_witnesses(letter)
            assert len(mappings) == 3, (
                f"Lettre {letter} n'a que {len(mappings)} mapping(s) "
                f"au lieu de 3"
            )

    def test_mothers_3(self):
        assert len(MOTHERS) == 3

    def test_doubles_7(self):
        assert len(DOUBLES) == 7

    def test_simples_12(self):
        assert len(SIMPLES) == 12
