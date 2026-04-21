"""Tests TDD pour bridge/sifrei_reader.py.

Couvre:
- Backward compat Sprint 9 (3 tests initiaux)
- API généralisée Sprint 10 Phase B : 5 helpers, cache mtime, corpus complet.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from bridge import sifrei_reader
from bridge.sifrei_reader import (
    load_all_ids,
    load_assertion,
    load_by_concept,
    load_by_module,
    load_by_partzuf,
    search,
)

# ──────────────── Sprint 9 backward compat ────────────────


def test_bridge_loads_ec_k5_001() -> None:
    result = load_assertion("EC-K5-001")
    assert result is not None
    required_fields = {"id", "source_he", "source_ref", "assertion"}
    assert required_fields.issubset(result.keys())
    assert result["id"] == "EC-K5-001"
    assert result["source_ref"] == "Sha'ar HaKlalim 5:1"


def test_bridge_returns_none_for_unknown_assertion() -> None:
    assert load_assertion("EC-XXX-999") is None
    assert load_assertion("") is None


def test_bridge_preserves_hebrew_text() -> None:
    result = load_assertion("EC-K5-001")
    assert result is not None
    source_he = result["source_he"]
    assert "תרין מזלות" in source_he
    assert "נוצר חסד" in source_he
    assert "ונקה" in source_he


# ──────────────── Sprint 10 Phase B : corpus généralisé ────────────────


def test_load_assertion_finds_zohar_idra_rabba() -> None:
    """Z-IR-T08-001 (Zohar Idra Rabba Tikkun 8) doit être chargeable."""
    result = load_assertion("Z-IR-T08-001")
    assert result is not None
    assert result["id"] == "Z-IR-T08-001"
    assert "source_aramaic" in result
    assert "translation_fr" in result


def test_load_assertion_finds_heikhal_03_vital() -> None:
    """EC-H3S2-T08-001 (Vital Notzer Chesed) doit être chargeable."""
    result = load_assertion("EC-H3S2-T08-001")
    assert result is not None
    assert result["id"] == "EC-H3S2-T08-001"


def test_load_assertion_finds_relation() -> None:
    """Les REL-* sont indexées au même titre que les EC-*."""
    result = load_assertion("REL-K5-001")
    assert result is not None
    assert result["id"] == "REL-K5-001"
    assert result.get("type") == "flux"


def test_load_assertion_finds_principe_generatif() -> None:
    """Les PG-* (principes génératifs) sont indexés."""
    result = load_assertion("PG-K5-001")
    assert result is not None
    assert result["id"] == "PG-K5-001"
    assert "formalisation" in result


def test_load_all_ids_returns_large_corpus() -> None:
    """Le corpus complet doit compter >1500 items (1020 assertions + 472 REL + 204 PG)."""
    ids = load_all_ids()
    assert len(ids) > 1500, f"Corpus trop petit: {len(ids)} items"
    assert "EC-K5-001" in ids
    assert "Z-IR-T08-001" in ids
    assert "REL-K5-001" in ids
    assert "PG-K5-001" in ids


def test_load_by_concept_finds_notzer_chesed() -> None:
    """Le concept `notzer_chesed` est référencé par EC-K5-001 + le corpus Batch 1."""
    results = load_by_concept("notzer_chesed")
    ids = {r["id"] for r in results}
    assert "EC-K5-001" in ids, f"EC-K5-001 absent de load_by_concept('notzer_chesed'): {ids}"


def test_load_by_module_finds_arikh_anpin() -> None:
    """EC-K5-001/002/003 mappent à partzufim/arikh_anpin.py."""
    results = load_by_module("partzufim/arikh_anpin.py")
    ids = {r["id"] for r in results}
    assert "EC-K5-001" in ids
    assert "EC-K5-002" in ids
    assert "EC-K5-003" in ids


def test_load_by_partzuf_finds_abba() -> None:
    """Le partzuf `abba` est cité par de multiples assertions."""
    results = load_by_partzuf("abba")
    assert len(results) >= 3
    ids = {r["id"] for r in results}
    assert "EC-K5-002" in ids


def test_search_finds_hebrew_fragment() -> None:
    """search('תרין מזלות') trouve au moins EC-K5-001."""
    results = search("תרין מזלות")
    ids = {r["id"] for r in results}
    assert "EC-K5-001" in ids


def test_search_empty_query_returns_empty() -> None:
    assert search("") == []


def test_search_unknown_query_returns_empty() -> None:
    assert search("ZZZZ_this_string_should_not_exist_in_corpus_XXXX") == []


def test_cache_invalidates_on_mtime_change(tmp_path: Path) -> None:
    """Si un YAML change, le prochain load_all_ids reflète le changement."""
    fake_root = tmp_path / "sefarim"
    fake_root.mkdir()
    yaml_path = fake_root / "test.yaml"
    yaml_path.write_text(
        "assertions:\n"
        '  - id: "TEST-001"\n'
        '    source_he: "אלף"\n'
        '    source_ref: "Test 1:1"\n'
        '    assertion: "Premier test"\n',
        encoding="utf-8",
    )

    original_root = sifrei_reader._SIFREI_ROOT
    sifrei_reader._SIFREI_ROOT = fake_root
    sifrei_reader._FILE_MTIMES.clear()
    sifrei_reader._INDEX.clear()
    sifrei_reader._BY_CONCEPT.clear()
    sifrei_reader._BY_MODULE.clear()
    sifrei_reader._BY_PARTZUF.clear()
    try:
        assert load_assertion("TEST-001") is not None
        assert load_assertion("TEST-002") is None

        yaml_path.write_text(
            "assertions:\n"
            '  - id: "TEST-001"\n'
            '    source_he: "אלף"\n'
            '    source_ref: "Test 1:1"\n'
            '    assertion: "Premier test"\n'
            '  - id: "TEST-002"\n'
            '    source_he: "בית"\n'
            '    source_ref: "Test 2:1"\n'
            '    assertion: "Second test"\n',
            encoding="utf-8",
        )
        future = time.time() + 10
        os.utime(yaml_path, (future, future))

        assert load_assertion("TEST-002") is not None
        assert load_assertion("TEST-001") is not None
    finally:
        sifrei_reader._SIFREI_ROOT = original_root
        sifrei_reader._FILE_MTIMES.clear()
        sifrei_reader._INDEX.clear()
        sifrei_reader._BY_CONCEPT.clear()
        sifrei_reader._BY_MODULE.clear()
        sifrei_reader._BY_PARTZUF.clear()


def test_load_assertion_returns_copy_not_reference() -> None:
    """Modifier le dict renvoyé ne doit pas polluer l'index."""
    a = load_assertion("EC-K5-001")
    b = load_assertion("EC-K5-001")
    assert a is not None and b is not None
    a["source_ref"] = "TAMPERED"
    assert b["source_ref"] != "TAMPERED"
