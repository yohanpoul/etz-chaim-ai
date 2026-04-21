"""pause_state.py — Persistance de l'état de pause Hitbonenut / Karpathy.

Fichier : ~/.etz-chaim/pause_state.json
Format  : {"hitbonenut_paused": false, "karpathy_paused": false}
"""

from __future__ import annotations

import json
from pathlib import Path

PAUSE_FILE = Path.home() / ".etz-chaim" / "pause_state.json"

_DEFAULTS = {
    "hitbonenut_paused": False,
    "karpathy_paused": False,
}


def _read() -> dict:
    if PAUSE_FILE.exists():
        try:
            return {**_DEFAULTS, **json.loads(PAUSE_FILE.read_text())}
        except (json.JSONDecodeError, OSError) as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
    return dict(_DEFAULTS)


def _write(state: dict) -> None:
    PAUSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    PAUSE_FILE.write_text(json.dumps(state, indent=2) + "\n")


def is_paused(target: str) -> bool:
    """Check if hitbonenut or karpathy is paused."""
    return _read().get(f"{target}_paused", False)


def set_paused(target: str, paused: bool) -> None:
    """Set pause state for hitbonenut or karpathy."""
    state = _read()
    state[f"{target}_paused"] = paused
    _write(state)


def get_all() -> dict:
    """Return full pause state."""
    return _read()
