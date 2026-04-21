"""Gate tests for Sprint 10 folio_map Zohar ↔ Sefaria sections + meta.yaml presence."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent / "sefarim" / "zohar" / "idra_rabba"
FOLIO_MAP_PATH = ROOT / "folio_map.yaml"
VITAL_ROOT = Path(__file__).resolve().parent.parent / "sefarim" / "etz_chaim" / "heikhal_03_arikh_anpin"


@pytest.fixture(scope="module")
def folio_map():
    assert FOLIO_MAP_PATH.exists(), f"folio_map.yaml missing at {FOLIO_MAP_PATH}"
    with FOLIO_MAP_PATH.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def test_folio_map_exists(folio_map):
    assert folio_map is not None


def test_folio_map_has_dikna_section(folio_map):
    """Section 10 (ouverture Dikna) must be mapped."""
    sections = folio_map.get("sections", {})
    assert "section_10" in sections, "Missing section_10 in folio_map"
    s = sections["section_10"]
    assert "dikna_content" in s or "introduction" in (s.get("theme", "").lower() + s.get("dikna_content", ""))


def test_folio_map_tikkunei_dikna_mapping_present(folio_map):
    """tikkunei_dikna_mapping must map Tikkunim 1..13 to Sefaria sections."""
    mapping = folio_map.get("tikkunei_dikna_mapping")
    assert mapping is not None, "Missing tikkunei_dikna_mapping"
    for n in range(1, 14):
        key = f"tikkun_{n}"
        assert key in mapping, f"Missing {key}"


def test_folio_map_t11_flagged_as_missing(folio_map):
    """Empirically found: T11 missing from Sefaria Mantua — must be flagged."""
    mapping = folio_map["tikkunei_dikna_mapping"]
    t11 = mapping["tikkun_11"]
    assert (
        t11.get("sefaria_section") is None
        or t11.get("status", "") == "MISSING_IN_SEFARIA_MANTUA"
    ), "T11 should be flagged as missing in Sefaria"


def test_folio_map_dikna_sections_cover_11_to_22(folio_map):
    """Sections 11-22 must cover Tikkunim (13 positions though T11 missing)."""
    sections = folio_map.get("sections", {})
    for n in [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22]:
        key = f"section_{n}"
        assert key in sections, f"Missing {key}"


def test_ashlag_sulam_segmentation_declared(folio_map):
    """Audit 12.0.b : segmentation Sulam must be declared."""
    value = folio_map.get("ashlag_sulam_segmentation")
    assert value in ("per_tikkun", "per_section", "mixed"), (
        f"Invalid segmentation value: {value}"
    )


# ─── Meta.yaml presence ───

def test_zohar_meta_exists():
    path = ROOT.parent / "meta.yaml"
    assert path.exists(), f"Missing zohar/meta.yaml at {path}"
    data = yaml.safe_load(path.open(encoding="utf-8"))
    assert data["meta"]["sefer"] == "zohar"


def test_idra_rabba_meta_exists():
    path = ROOT / "meta.yaml"
    assert path.exists()
    data = yaml.safe_load(path.open(encoding="utf-8"))
    assert data["meta"]["parashah"] == "Naso"
    assert "127b-145a" in data["meta"]["folio_range"]


def test_section_03_meta_exists():
    path = ROOT / "section_03_tikkunei_dikna_13" / "meta.yaml"
    assert path.exists()
    data = yaml.safe_load(path.open(encoding="utf-8"))
    assert "doctrinal_function" in data["meta"]
    assert "Ze'ir Anpin" in data["meta"]["doctrinal_function"]
    assert data["meta"]["tikkunim_count"] == 13


def test_heikhal_03_meta_exists():
    path = VITAL_ROOT / "meta.yaml"
    assert path.exists()
    data = yaml.safe_load(path.open(encoding="utf-8"))
    assert data["meta"]["heikhal"] == 3
    assert data["meta"]["heikhal_name_he"] == "היכל אריך אנפין"


def test_shaar_02_dikna_meta_exists():
    path = VITAL_ROOT / "shaar_02_dikna" / "meta.yaml"
    assert path.exists()
    data = yaml.safe_load(path.open(encoding="utf-8"))
    assert data["meta"]["shaar"] == 2
    assert data["meta"]["tikkunim_count"] == 13
    assert "doctrinal_function" in data["meta"]
