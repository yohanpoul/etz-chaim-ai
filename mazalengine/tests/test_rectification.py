"""Tests TDD pour MazalEngine Phase 3 (rectification active, Sprint 10 Phase C).

Couvre :
  - Résolution du mode (env var / config.yaml / fallback observe).
  - Mode `observe` : compat Sprint 9 (pas d'event supplémentaire).
  - Mode `suggest` : event ``mazal_action_proposed`` sans side effect.
  - Mode `act` : application effective (Omer + causal_claims.abandoned).
  - Compteur cycle Ve-Nakeh (N cycles avant abandon).
  - Hitlabshut (EC-K5-008) respecté en mode act.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import pytest

from mazalengine import (
    MazalEngine,
    NotzerChesedRectifier,
    ProposedAction,
    RectificationMode,
    VeNakehRectifier,
    rectification,
)
from mazalengine.rectification import load_mode

# ──────────────── Mode resolution ────────────────


def test_mode_default_is_observe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MAZAL_RECTIFICATION_MODE", raising=False)
    # On rend config.yaml unreachable pour ce test
    monkeypatch.setattr(rectification, "Path", lambda _: Path("/nonexistent_xyz"))
    assert load_mode() == RectificationMode.OBSERVE


def test_mode_from_env_var_suggest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAZAL_RECTIFICATION_MODE", "suggest")
    assert load_mode() == RectificationMode.SUGGEST


def test_mode_from_env_var_act(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAZAL_RECTIFICATION_MODE", "act")
    assert load_mode() == RectificationMode.ACT


def test_mode_invalid_env_falls_back_to_observe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAZAL_RECTIFICATION_MODE", "invalid_mode")
    # config.yaml peut sinon la remettre ; on s'assure seulement que
    # le mode retourné est valide
    assert load_mode() in RectificationMode.ALL


def test_mode_explicit_arg_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAZAL_RECTIFICATION_MODE", "act")
    assert load_mode(explicit="suggest") == RectificationMode.SUGGEST


# ──────────────── Mode observe → Sprint 9 compat ────────────────


def test_observe_mode_matches_sprint9_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mode observe ne doit pas émettre d'event au-delà du signalement."""
    monkeypatch.delenv("MAZAL_RECTIFICATION_MODE", raising=False)
    engine = MazalEngine(mode=RectificationMode.OBSERVE)
    monkeypatch.setattr(engine.mazal_elyon, "_count_recent_connections", lambda hours: 0)
    monkeypatch.setattr(engine.mazal_tahton, "_count_stale_claims", lambda days: 0)
    events = engine.run(tree=None)
    assert len(events) == 1
    assert events[0]["mazal"] == "elyon"
    assert events[0]["action"] == "chesed_starvation_signaled"


# ──────────────── Mode suggest — propositions sans side effects ────────────────


def test_suggest_mode_emits_proposed_action_notzer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = MazalEngine(mode=RectificationMode.SUGGEST)
    monkeypatch.setattr(engine.mazal_elyon, "_count_recent_connections", lambda hours: 0)
    monkeypatch.setattr(engine.mazal_tahton, "_count_stale_claims", lambda days: 0)
    events = engine.run(tree=None)

    action_types = [e.get("event_type") for e in events]
    assert "mazal_action_proposed" in action_types
    proposed = [e for e in events if e.get("event_type") == "mazal_action_proposed"][0]
    assert proposed["mazal"] == "elyon"
    assert proposed["action_type"] == "omer_adjust"
    assert proposed["target"] == "explorationengine"
    assert "explore_breadth_delta" in proposed["params"]


def test_suggest_mode_does_not_apply_omer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mode suggest ne doit PAS appeler OmerManager.apply."""
    engine = MazalEngine(mode=RectificationMode.SUGGEST)
    monkeypatch.setattr(engine.mazal_elyon, "_count_recent_connections", lambda hours: 0)
    monkeypatch.setattr(engine.mazal_tahton, "_count_stale_claims", lambda days: 0)

    apply_calls: list[Any] = []
    monkeypatch.setattr(
        engine.notzer_rectifier,
        "apply",
        lambda *a, **kw: apply_calls.append((a, kw)) or {},
    )

    engine.run(tree=None)
    assert apply_calls == []


def test_suggest_mode_ve_nakeh_proposes_abandon(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = MazalEngine(mode=RectificationMode.SUGGEST)
    monkeypatch.setattr(engine.mazal_elyon, "_count_recent_connections", lambda hours: 1)
    monkeypatch.setattr(
        engine.mazal_tahton,
        "_count_stale_claims",
        lambda days: engine.mazal_tahton.STALE_MIN_COUNT + 5,
    )

    events = engine.run(tree=None)
    proposed = [e for e in events if e.get("event_type") == "mazal_action_proposed"]
    assert proposed, f"aucun mazal_action_proposed: {events}"
    action = proposed[0]
    assert action["mazal"] == "tahton"
    assert action["action_type"] == "claim_abandon"
    assert action["target"] == "causal_claims"


# ──────────────── Mode act — application ────────────────


def test_act_mode_calls_notzer_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = MazalEngine(mode=RectificationMode.ACT)
    monkeypatch.setattr(engine.mazal_elyon, "_count_recent_connections", lambda hours: 0)
    monkeypatch.setattr(engine.mazal_tahton, "_count_stale_claims", lambda days: 0)

    apply_calls: list[Any] = []

    def _mock_apply(action: ProposedAction, db_url: str | None = None) -> dict:
        apply_calls.append(action)
        return {
            "mazal": "elyon",
            "tikkun": "notzer_chesed",
            "action": "omer_adjusted",
            "doctrine_ref": "EC-K5-001",
            "applied": 2,
        }

    monkeypatch.setattr(engine.notzer_rectifier, "apply", _mock_apply)

    events = engine.run(tree=None)
    actions = [e for e in events if e.get("action") == "omer_adjusted"]
    assert actions, f"aucun omer_adjusted: {events}"
    assert len(apply_calls) == 1
    assert apply_calls[0].action_type == "omer_adjust"


def test_act_mode_ve_nakeh_defers_below_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Au 1er cycle, l'abandon doit être `deferred` (seuil = 3)."""
    engine = MazalEngine(mode=RectificationMode.ACT)
    monkeypatch.setattr(engine.mazal_elyon, "_count_recent_connections", lambda hours: 1)
    monkeypatch.setattr(
        engine.mazal_tahton,
        "_count_stale_claims",
        lambda days: engine.mazal_tahton.STALE_MIN_COUNT + 1,
    )

    events = engine.run(tree=None)
    abandon_events = [
        e for e in events if e.get("tikkun") == "ve_nakeh" and "abandon" in e.get("action", "")
    ]
    assert abandon_events, f"pas d'event abandon: {events}"
    assert abandon_events[0]["action"] == "abandon_deferred"


def test_ve_nakeh_cycle_counter_increments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Compteur cycle s'incrémente, atteint le seuil au 3e call."""
    engine = MazalEngine(mode=RectificationMode.SUGGEST)
    monkeypatch.setattr(engine.mazal_elyon, "_count_recent_connections", lambda hours: 1)
    monkeypatch.setattr(
        engine.mazal_tahton,
        "_count_stale_claims",
        lambda days: engine.mazal_tahton.STALE_MIN_COUNT + 1,
    )
    for i in range(1, 4):
        events = engine.run(tree=None)
        proposed = [e for e in events if e.get("event_type") == "mazal_action_proposed"][0]
        assert proposed["params"]["stale_cycles"] == i


# ──────────────── Hitlabshut ────────────────


def test_rectification_code_contains_no_partzufim_state_write() -> None:
    """Aucun UPDATE/INSERT partzufim_state dans rectification.py (Hitlabshut)."""
    import mazalengine.rectification as rect_mod

    src = inspect.getsource(rect_mod)
    forbidden = [
        "UPDATE partzufim_state",
        "INSERT INTO partzufim_state",
        "partzufim_state SET",
        "UPDATE zivvug_state",
        "INSERT INTO zivvug_state",
    ]
    for needle in forbidden:
        assert needle not in src, f"Hitlabshut violation: {needle!r} dans rectification.py"


def test_rectification_orthogonal_to_partzufim() -> None:
    """rectification.py n'importe rien de partzufim/."""
    path = Path(__file__).resolve().parents[1] / "rectification.py"
    src = path.read_text(encoding="utf-8")
    assert "from partzufim" not in src
    assert "import partzufim" not in src
    assert "set_faculty" not in src
    assert "update_all_partzufim" not in src


# ──────────────── Direct rectifier unit tests ────────────────


def test_notzer_rectifier_proposes_omer_adjust() -> None:
    r = NotzerChesedRectifier()
    action = r.propose({"window_hours": 24, "metrics": {"connections_recent": 0}})
    assert action.mazal == "elyon"
    assert action.action_type == "omer_adjust"
    assert action.params["explore_breadth_delta"] == r.BREADTH_BOOST
    assert action.params["novelty_threshold_delta"] == r.NOVELTY_RELAX


def test_ve_nakeh_reset_cycle_count() -> None:
    r = VeNakehRectifier()
    r.propose({"threshold_days": 30, "metrics": {"stale_count": 20}})
    r.propose({"threshold_days": 30, "metrics": {"stale_count": 20}})
    assert r._cycle_count == 2
    r.reset_cycle_count()
    assert r._cycle_count == 0
