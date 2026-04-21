"""Tests TDD pour MazalEngine pilot (Sprint 9 — EC-K5-001).

9 tests couvrant :
  - orchestrateur MazalEngine (detect + rectify + run)
  - Mazal Elyon (Notzer Chesed, Tikkun n°8)
  - Mazal Tahton (Ve-Nakeh, Tikkun n°13)
  - respect Hitlabshut (EC-K5-008)
  - non-régression orientation Sprint 7

Les tests mockent les requêtes DB via ``monkeypatch`` sur les méthodes
privées ``_count_*``, pour ne dépendre ni de PostgreSQL ni du pool.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest


def test_mazal_engine_detect_empty_tree_no_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    """MazalEngine.detect(None) ne crash pas même avec DB indisponible."""
    from mazalengine import MazalEngine

    engine = MazalEngine()

    # Mock les count pour simuler DB indisponible (retourne 0 / aucune deviation)
    monkeypatch.setattr(
        engine.mazal_elyon,
        "_count_recent_connections",
        lambda hours: 1,
    )
    monkeypatch.setattr(
        engine.mazal_tahton,
        "_count_stale_claims",
        lambda days: 0,
    )

    deviations = engine.detect(tree=None)
    assert isinstance(deviations, list)
    assert deviations == []


def test_mazal_elyon_detects_chesed_starvation(monkeypatch: pytest.MonkeyPatch) -> None:
    """0 connections/24h → deviation détectée par Mazal Elyon."""
    from mazalengine.mazal_elyon import MazalElyonNotzerChesed

    mazal = MazalElyonNotzerChesed()
    monkeypatch.setattr(mazal, "_count_recent_connections", lambda hours: 0)

    deviations = mazal.detect(tree=None)
    assert len(deviations) == 1
    dev = deviations[0]
    assert dev["mazal"] == "elyon"
    assert "metrics" in dev
    assert dev["metrics"]["connections_recent"] == 0


def test_mazal_elyon_tikkun_returns_structured_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """apply_tikkun retourne un event structuré avec doctrine_ref EC-K5-001."""
    from mazalengine.mazal_elyon import MazalElyonNotzerChesed

    mazal = MazalElyonNotzerChesed()
    monkeypatch.setattr(mazal, "_count_recent_connections", lambda hours: 0)
    deviations = mazal.detect(tree=None)
    event = mazal.apply_tikkun(deviations[0])

    assert event["mazal"] == "elyon"
    assert event["tikkun"] == "notzer_chesed"
    assert event["action"] == "chesed_starvation_signaled"
    assert event["doctrine_ref"] == "EC-K5-001"
    assert "metrics" in event


def test_mazal_tahton_detects_stale_claims_above_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """≥ STALE_MIN_COUNT claims stales → deviation retournée."""
    from mazalengine.mazal_tahton import MazalTahtonVeNakeh

    mazal = MazalTahtonVeNakeh()
    monkeypatch.setattr(
        mazal,
        "_count_stale_claims",
        lambda days: mazal.STALE_MIN_COUNT + 5,
    )

    deviations = mazal.detect(tree=None)
    assert len(deviations) == 1
    assert deviations[0]["mazal"] == "tahton"
    assert deviations[0]["metrics"]["stale_count"] >= mazal.STALE_MIN_COUNT


def test_mazal_tahton_dormant_below_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Count < STALE_MIN_COUNT → Mazal Tahton dormant (pas de deviation)."""
    from mazalengine.mazal_tahton import MazalTahtonVeNakeh

    mazal = MazalTahtonVeNakeh()
    monkeypatch.setattr(
        mazal,
        "_count_stale_claims",
        lambda days: mazal.STALE_MIN_COUNT - 1,
    )

    deviations = mazal.detect(tree=None)
    assert deviations == []


def test_mazal_engine_emits_events_on_tikkun(monkeypatch: pytest.MonkeyPatch) -> None:
    """MazalEngine.run() agrège events des 2 Mazalot avec deviations détectées."""
    from mazalengine import MazalEngine

    engine = MazalEngine()
    monkeypatch.setattr(
        engine.mazal_elyon,
        "_count_recent_connections",
        lambda hours: 0,
    )
    monkeypatch.setattr(
        engine.mazal_tahton,
        "_count_stale_claims",
        lambda days: engine.mazal_tahton.STALE_MIN_COUNT + 1,
    )

    events = engine.run(tree=None)
    mazalot = {e["mazal"] for e in events}
    assert mazalot == {"elyon", "tahton"}
    assert all("doctrine_ref" in e for e in events)


def test_mazal_engine_respects_hitlabshut() -> None:
    """MazalEngine ne contient JAMAIS d'écriture sur partzufim_state (EC-K5-008).

    Static check : aucun module mazalengine n'émet ``UPDATE partzufim_state``
    ni ``INSERT INTO partzufim_state``. Le respect du Hitlabshut est garanti
    au niveau du code source, pas seulement du comportement runtime.
    """
    import mazalengine
    import mazalengine.mazal_elyon
    import mazalengine.mazal_engine
    import mazalengine.mazal_tahton

    modules = [
        mazalengine,
        mazalengine.mazal_engine,
        mazalengine.mazal_elyon,
        mazalengine.mazal_tahton,
    ]
    for mod in modules:
        try:
            src = inspect.getsource(mod)
        except (TypeError, OSError):
            continue
        forbidden = [
            "UPDATE partzufim_state",
            "INSERT INTO partzufim_state",
            "partzufim_state SET",
            "UPDATE zivvug_state",
            "INSERT INTO zivvug_state",
        ]
        for needle in forbidden:
            assert needle not in src, f"Hitlabshut violation dans {mod.__name__}: {needle!r} trouvé"


def test_mazal_engine_doctrinal_ec_k5_reference() -> None:
    """Chaque Mazal expose DOCTRINE_REF == 'EC-K5-001'."""
    from mazalengine.mazal_elyon import MazalElyonNotzerChesed
    from mazalengine.mazal_tahton import MazalTahtonVeNakeh

    assert MazalElyonNotzerChesed.DOCTRINE_REF == "EC-K5-001"
    assert MazalTahtonVeNakeh.DOCTRINE_REF == "EC-K5-001"


def test_mazal_engine_orthogonal_to_orientation_sprint7() -> None:
    """MazalEngine n'importe ni ne modifie les mécanismes d'orientation.

    Static check : les modules mazalengine ne touchent ni aux regulators
    (Sprint 7) ni aux set_faculty / overall_score (Sprint 8 D1). Cela garantit
    qu'un run MazalEngine ne peut pas provoquer de transition panim↔achor.
    """
    modules_to_check = [
        Path("mazalengine/mazal_engine.py"),
        Path("mazalengine/mazal_elyon.py"),
        Path("mazalengine/mazal_tahton.py"),
    ]
    forbidden_imports = [
        "from partzufim",
        "import partzufim",
        "set_faculty",
        "update_all_partzufim",
        "check_transitions",
    ]
    project_root = Path(__file__).resolve().parents[2]
    for rel in modules_to_check:
        path = project_root / rel
        if not path.exists():
            continue
        src = path.read_text(encoding="utf-8")
        for needle in forbidden_imports:
            assert needle not in src, f"Orientation coupling dans {rel}: {needle!r} présent"
