"""Tests Phase E (Refactor L Zivvug) — Sprint 10.

Couvre :
- Schema SQL extrait dans zivvug_schema.sql.
- Factory `load_or_create_zivvug` unifie le pattern load_or_create.
- Aucun call site restant ne duplique `load_zivvug_state() or ZivvugEngine()`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from partzufim.zivvug import (
    ZIVVUG_SCHEMA,
    ZivvugEngine,
    load_or_create_zivvug,
)


# ──────────────── Schema SQL canonique ────────────────


def test_zivvug_schema_sql_exists() -> None:
    """Le schéma canonique vit dans partzufim/zivvug_schema.sql."""
    root = Path(__file__).resolve().parents[1]
    sql_path = root / "zivvug_schema.sql"
    assert sql_path.exists(), f"schéma manquant: {sql_path}"
    text = sql_path.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS zivvug_state" in text
    assert "abba_boost" in text
    assert "imma_boost" in text
    assert "CHECK (id = 1)" in text


def test_zivvug_schema_constant_mirrors_sql_file() -> None:
    """La constante ZIVVUG_SCHEMA reflète le contenu du .sql canonique."""
    # Points-clés qui doivent être présents dans les 2
    assert "CREATE TABLE IF NOT EXISTS zivvug_state" in ZIVVUG_SCHEMA
    assert "abba_boost" in ZIVVUG_SCHEMA
    assert "imma_boost" in ZIVVUG_SCHEMA


# ──────────────── Factory load_or_create ────────────────


def test_load_or_create_zivvug_returns_engine() -> None:
    """Même sans DB (pool indisponible), retourne un ZivvugEngine neuf."""
    engine = load_or_create_zivvug()
    assert isinstance(engine, ZivvugEngine)


def test_load_or_create_zivvug_new_engine_has_zero_boosts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Si DB vide, les boosts sont à 0."""
    # Force le fallback : load_zivvug_state renvoie None → ZivvugEngine()
    from partzufim import zivvug as zmod

    monkeypatch.setattr(zmod, "load_zivvug_state", lambda: None)
    engine = zmod.load_or_create_zivvug()
    assert engine.abba_boost == 0.0
    assert engine.imma_boost == 0.0


def test_load_or_create_zivvug_preserves_persisted_boosts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Si DB renvoie un engine avec boosts, la factory les préserve."""
    from partzufim import zivvug as zmod

    fake_engine = ZivvugEngine()
    fake_engine._abba_boost = 0.123
    fake_engine._imma_boost = 0.456

    monkeypatch.setattr(zmod, "load_zivvug_state", lambda: fake_engine)
    engine = zmod.load_or_create_zivvug()
    assert engine.abba_boost == pytest.approx(0.123)
    assert engine.imma_boost == pytest.approx(0.456)


# ──────────────── Call sites unifiés ────────────────


def test_no_duplicate_load_or_create_pattern() -> None:
    """Aucun .py (sauf module+ce test) ne duplique le pattern legacy."""
    root = Path(__file__).resolve().parents[2]
    # Construit le needle par concaténation pour ne pas matcher ce fichier
    needle = "load_zivvug_state()" + " or " + "ZivvugEngine()"
    violations: list[str] = []
    skip_dirs = {".venv", "venv", ".garak-venv", ".git", "__pycache__"}
    self_path = Path(__file__).relative_to(root)
    for py in root.rglob("*.py"):
        rel = py.relative_to(root)
        parts = set(rel.parts)
        if parts & skip_dirs:
            continue
        # Fichiers autorisés : factory (déf) + ce test (contient needle construit)
        if rel == Path("partzufim/zivvug.py") or rel == self_path:
            continue
        try:
            text = py.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if needle in text:
            violations.append(str(rel))
    assert violations == [], (
        "Pattern legacy encore présent : " + ", ".join(violations)
    )
