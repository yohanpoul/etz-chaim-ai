"""Tests pour /api/mazalengine — dashboard widget Sprint 9 post.

Endpoint qui lit ``~/.etz-chaim/daemon_events.jsonl`` et agrège les events
``mazal_tikkun`` par Mazal (elyon / tahton).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def fake_etz_home(tmp_path, monkeypatch):
    """Redirige ``Path.home()`` vers ``tmp_path`` + crée ``.etz-chaim/``."""
    etz = tmp_path / ".etz-chaim"
    etz.mkdir(exist_ok=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    return etz


def _write_events(etz_dir: Path, events: list[dict]) -> None:
    events_file = etz_dir / "daemon_events.jsonl"
    with events_file.open("w", encoding="utf-8") as fh:
        for evt in events:
            fh.write(json.dumps(evt) + "\n")


def test_api_mazalengine_returns_mazalot_structure(fake_etz_home) -> None:
    """Retourne un dict avec les 2 Mazalot (elyon + tahton) + doctrine_ref."""
    from web.blueprints import api as api_mod

    result = api_mod._compute_mazalengine_state()
    assert isinstance(result, dict)
    assert "mazalot" in result
    assert set(result["mazalot"].keys()) == {"elyon", "tahton"}
    assert result["doctrine_ref"] == "EC-K5-001"
    # Sprint 9 pilot count
    assert result.get("pilot_count") == 2
    # Chaque Mazal expose les champs requis
    for mazal in result["mazalot"].values():
        assert "tikkun_number" in mazal
        assert "translit" in mazal
        assert "hebrew_name" in mazal
        assert "total_tikkunim" in mazal
        assert "last_tikkun_ts" in mazal


def test_api_mazalengine_aggregates_tikkun_events(fake_etz_home) -> None:
    """Events mazal_tikkun corrects → count et last_* calculés."""
    from web.blueprints import api as api_mod

    events = [
        {"type": "daemon_heartbeat", "ts": 1000.0, "pid": 1234},  # filtré
        {
            "type": "daemon_task", "ts": 2000.0, "task": "mazal_tikkun",
            "mazal": "elyon", "tikkun": "notzer_chesed",
            "action": "chesed_starvation_signaled",
            "doctrine_ref": "EC-K5-001",
            "metrics": {"connections_recent": 0}, "window_hours": 24,
        },
        {
            "type": "daemon_task", "ts": 3000.0, "task": "mazal_tikkun",
            "mazal": "elyon", "tikkun": "notzer_chesed",
            "action": "chesed_starvation_signaled",
            "doctrine_ref": "EC-K5-001",
            "metrics": {"connections_recent": 0}, "window_hours": 24,
        },
        {
            "type": "daemon_task", "ts": 2500.0, "task": "mazal_tikkun",
            "mazal": "tahton", "tikkun": "ve_nakeh",
            "action": "stale_claims_signaled",
            "doctrine_ref": "EC-K5-001",
            "metrics": {"stale_count": 15}, "threshold_days": 30,
        },
    ]
    _write_events(fake_etz_home, events)

    result = api_mod._compute_mazalengine_state()
    assert result["mazalot"]["elyon"]["total_tikkunim"] == 2
    assert result["mazalot"]["elyon"]["last_tikkun_ts"] == 3000.0
    assert result["mazalot"]["elyon"]["last_action"] == "chesed_starvation_signaled"
    assert result["mazalot"]["elyon"]["last_metrics"] == {"connections_recent": 0}

    assert result["mazalot"]["tahton"]["total_tikkunim"] == 1
    assert result["mazalot"]["tahton"]["last_tikkun_ts"] == 2500.0
    assert result["mazalot"]["tahton"]["last_metrics"] == {"stale_count": 15}


def test_api_mazalengine_handles_missing_events_file(fake_etz_home) -> None:
    """Si daemon_events.jsonl n'existe pas → totaux à 0 sans crash."""
    from web.blueprints import api as api_mod

    # fake_etz_home existe mais pas de daemon_events.jsonl
    result = api_mod._compute_mazalengine_state()
    assert result["mazalot"]["elyon"]["total_tikkunim"] == 0
    assert result["mazalot"]["elyon"]["last_tikkun_ts"] is None
    assert result["mazalot"]["tahton"]["total_tikkunim"] == 0
    assert result["mazalot"]["tahton"]["last_tikkun_ts"] is None
