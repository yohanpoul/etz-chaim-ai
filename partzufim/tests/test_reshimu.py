"""Tests TDD pour partzufim/reshimu.py (Sprint 10 Phase D Option B).

Couvre :
- Init schema idempotent.
- record() accumule et plafonne à MAX.
- get() / get_all_for().
- decay() diminue proportionnellement.
- reset() vide le store.
- Hitlabshut : aucune écriture sur partzufim_state.
- Intégration update_all_partzufim (mémoire-only, sans DB).
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from partzufim.reshimu import (
    MAX_RESHIMU,
    ReshimuManager,
    SCHEMA_SQL,
)


def _make_memory_mgr() -> ReshimuManager:
    """ReshimuManager en mode mémoire (pas de DB)."""
    return ReshimuManager(memory_only=True)


# ──────────────── record / get ────────────────


def test_record_accumulates_in_memory() -> None:
    mgr = _make_memory_mgr()
    v1 = mgr.record("abba", "chokhmah", 0.055)
    assert v1 == pytest.approx(0.055 * ReshimuManager.TRACE_FACTOR)
    v2 = mgr.record("abba", "chokhmah", 0.055)
    assert v2 == pytest.approx(2 * 0.055 * ReshimuManager.TRACE_FACTOR)


def test_record_caps_at_max() -> None:
    mgr = _make_memory_mgr()
    # Push 50 cycles at BOOST=0.055 -> 50 * 0.011 = 0.55 but capped at 0.3
    for _ in range(50):
        mgr.record("abba", "tiferet", 0.055)
    assert mgr.get("abba", "tiferet") == pytest.approx(MAX_RESHIMU)


def test_record_zero_returns_current() -> None:
    mgr = _make_memory_mgr()
    mgr.record("imma", "binah", 0.1)
    current = mgr.get("imma", "binah")
    assert mgr.record("imma", "binah", 0.0) == current
    assert mgr.record("imma", "binah", -0.5) == current


def test_get_returns_zero_for_unknown() -> None:
    mgr = _make_memory_mgr()
    assert mgr.get("unknown", "unknown") == 0.0


def test_get_all_for_partzuf() -> None:
    mgr = _make_memory_mgr()
    mgr.record("abba", "chokhmah", 0.055)
    mgr.record("abba", "tiferet", 0.055)
    mgr.record("imma", "binah", 0.055)
    d = mgr.get_all_for("abba")
    assert set(d.keys()) == {"chokhmah", "tiferet"}
    assert d["chokhmah"] > 0 and d["tiferet"] > 0
    assert "binah" not in d


# ──────────────── decay ────────────────


def test_decay_reduces_values() -> None:
    mgr = _make_memory_mgr()
    mgr.record("abba", "chokhmah", 0.1)
    before = mgr.get("abba", "chokhmah")
    n = mgr.decay(rate=0.1)
    assert n == 1
    after = mgr.get("abba", "chokhmah")
    assert after == pytest.approx(before * 0.9)


def test_decay_skips_zero_values() -> None:
    mgr = _make_memory_mgr()
    # Aucune entrée → rien à décayer
    assert mgr.decay() == 0
    # Après record puis reset, no entries
    mgr.record("abba", "chokhmah", 0.1)
    mgr.reset()
    assert mgr.decay() == 0


def test_decay_default_rate() -> None:
    mgr = _make_memory_mgr()
    mgr.record("abba", "chokhmah", 0.1)
    before = mgr.get("abba", "chokhmah")
    mgr.decay()  # default DECAY_RATE = 0.05
    after = mgr.get("abba", "chokhmah")
    assert after == pytest.approx(before * (1.0 - ReshimuManager.DECAY_RATE))


# ──────────────── reset ────────────────


def test_reset_all() -> None:
    mgr = _make_memory_mgr()
    mgr.record("abba", "chokhmah", 0.1)
    mgr.record("imma", "binah", 0.1)
    mgr.reset()
    assert mgr.get("abba", "chokhmah") == 0.0
    assert mgr.get("imma", "binah") == 0.0


def test_reset_one_partzuf() -> None:
    mgr = _make_memory_mgr()
    mgr.record("abba", "chokhmah", 0.1)
    mgr.record("imma", "binah", 0.1)
    mgr.reset(partzuf="abba")
    assert mgr.get("abba", "chokhmah") == 0.0
    assert mgr.get("imma", "binah") > 0.0


# ──────────────── Hitlabshut ────────────────


def test_reshimu_code_contains_no_partzufim_state_write() -> None:
    """Aucun UPDATE/INSERT sur partzufim_state (EC-K5-008)."""
    import partzufim.reshimu as mod

    src = inspect.getsource(mod)
    forbidden = [
        "UPDATE partzufim_state",
        "INSERT INTO partzufim_state",
        "partzufim_state SET",
        "UPDATE zivvug_state",
        "INSERT INTO zivvug_state",
    ]
    for needle in forbidden:
        assert needle not in src, (
            f"Hitlabshut violation: {needle!r} trouvé dans reshimu.py"
        )


def test_reshimu_schema_is_faculty_level() -> None:
    """Le schema touche faculty_reshimot (Kelim), pas partzufim_state."""
    assert "faculty_reshimot" in SCHEMA_SQL
    assert "partzufim_state" not in SCHEMA_SQL
    assert "zivvug_state" not in SCHEMA_SQL


# ──────────────── Cumulativité (propriété principale) ────────────────


def test_reshimu_cumulates_across_cycles() -> None:
    """3 cycles stables → Reshimu converge mais reste strictement croissant
    jusqu'au plafond."""
    mgr = _make_memory_mgr()
    values = []
    for _ in range(10):
        mgr.record("abba", "chokhmah", 0.055)
        values.append(mgr.get("abba", "chokhmah"))
    # Strictement croissant tant qu'on est sous MAX
    for i in range(1, len(values)):
        if values[i - 1] < MAX_RESHIMU:
            assert values[i] > values[i - 1], (
                f"Non-croissant cycle {i}: {values[i-1]} -> {values[i]}"
            )


def test_reshimu_decay_dominates_when_no_boost() -> None:
    """Sans boost mais avec decay, les Reshimot tendent vers 0."""
    mgr = _make_memory_mgr()
    mgr.record("abba", "chokhmah", 0.1)
    before = mgr.get("abba", "chokhmah")
    for _ in range(50):
        mgr.decay(rate=0.1)
    after = mgr.get("abba", "chokhmah")
    assert after < before * 0.01  # <1% de la valeur initiale


# ──────────────── Orthogonalité Partzufim ────────────────


def test_reshimu_module_orthogonal_to_zivvug_engine() -> None:
    """reshimu.py ne dépend pas de ZivvugEngine (orthogonalité des 3 systèmes Zivvug)."""
    path = Path(__file__).resolve().parents[1] / "reshimu.py"
    src = path.read_text(encoding="utf-8")
    assert "from partzufim.zivvug" not in src
    assert "import ZivvugEngine" not in src
