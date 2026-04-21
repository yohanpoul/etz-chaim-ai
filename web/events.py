"""web/events.py — Event bus pour le World SSE + persistence JSONL.

Bus thread-safe : n'importe quel module peut emettre un evenement,
les clients SSE connectes a /api/world/events les recoivent en temps reel.
Chaque evenement est aussi ecrit dans ~/.etz-chaim/daemon_events.jsonl
pour que le dashboard puisse relire l'historique.
"""

from __future__ import annotations

import json
import queue
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generator

# ── JSONL persistence ───────────────────────────────────────
EVENTS_JSONL = Path.home() / ".etz-chaim" / "daemon_events.jsonl"
_jsonl_lock = threading.Lock()


@dataclass
class WorldEvent:
    """Un evenement du monde."""
    event_type: str          # import_start, ohr_yashar_step, nitzutz, etc.
    data: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_sse(self) -> str:
        payload = {"type": self.event_type, "ts": self.timestamp, **self.data}
        return f"event: world\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


class WorldEventBus:
    """Bus d'evenements thread-safe avec multi-subscriber SSE."""

    def __init__(self, maxsize: int = 200) -> None:
        self._lock = threading.Lock()
        self._subscribers: dict[int, queue.Queue] = {}
        self._next_id = 0
        self._history: list[WorldEvent] = []
        self._maxsize = maxsize

    def emit(self, event_type: str, **data: Any) -> None:
        """Emettre un evenement vers tous les subscribers + ecrire en JSONL."""
        evt = WorldEvent(event_type=event_type, data=data)
        with self._lock:
            self._history.append(evt)
            if len(self._history) > self._maxsize:
                self._history = self._history[-self._maxsize:]
            dead = []
            for sid, q in self._subscribers.items():
                try:
                    q.put_nowait(evt)
                except queue.Full:
                    dead.append(sid)
            for sid in dead:
                del self._subscribers[sid]
        # Persistence JSONL (hors du lock SSE pour ne pas bloquer)
        _write_jsonl(evt)

    def subscribe(self) -> tuple[int, queue.Queue]:
        """Creer un subscriber. Retourne (id, queue)."""
        with self._lock:
            sid = self._next_id
            self._next_id += 1
            q: queue.Queue = queue.Queue(maxsize=500)
            self._subscribers[sid] = q
            return sid, q

    def unsubscribe(self, sid: int) -> None:
        with self._lock:
            self._subscribers.pop(sid, None)

    def stream(self, timeout: float = 30.0) -> Generator[str, None, None]:
        """Generateur SSE pour un client."""
        sid, q = self.subscribe()
        try:
            # Envoyer un heartbeat initial
            yield ": connected\n\n"
            while True:
                try:
                    evt = q.get(timeout=timeout)
                    yield evt.to_sse()
                except queue.Empty:
                    # Heartbeat pour garder la connexion
                    yield ": heartbeat\n\n"
        except GeneratorExit as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
        finally:
            self.unsubscribe(sid)

    def recent(self, n: int = 50) -> list[WorldEvent]:
        with self._lock:
            return list(self._history[-n:])


def _write_jsonl(evt: WorldEvent) -> None:
    """Ecrire un evenement dans le fichier JSONL (append, thread-safe)."""
    line = json.dumps(
        {"type": evt.event_type, "ts": evt.timestamp, **evt.data},
        ensure_ascii=False,
        default=str,
    )
    with _jsonl_lock:
        try:
            with open(EVENTS_JSONL, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)  # Ne pas crasher le daemon si le fichier est inaccessible


# ── Singleton global ─────────────────────────────────────────
_bus: WorldEventBus | None = None
_bus_lock = threading.Lock()


def get_event_bus() -> WorldEventBus:
    """Obtenir le bus global (lazy singleton)."""
    global _bus
    if _bus is None:
        with _bus_lock:
            if _bus is None:
                _bus = WorldEventBus()
    return _bus


def emit(event_type: str, **data: Any) -> None:
    """Raccourci : emettre un evenement sur le bus global."""
    get_event_bus().emit(event_type, **data)
