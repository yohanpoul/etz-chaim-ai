"""Format an aware datetime into a short human-readable age string."""
from __future__ import annotations

from datetime import datetime, timezone


def human_age(birthtime: datetime) -> str:
    """Return a short human age string for a past timestamp.

    Examples:
        <10s   -> "just now"
        <60s   -> "45s"
        <60m   -> "30m"
        <24h   -> "3h 22m"
        >=24h  -> "2d 2h"

    Args:
        birthtime: An aware ``datetime`` (must have ``tzinfo``).

    Raises:
        ValueError: if ``birthtime`` is naive.
    """
    if birthtime.tzinfo is None:
        raise ValueError("human_age requires an aware datetime")
    now = datetime.now(timezone.utc)
    delta_s = (now - birthtime).total_seconds()
    if delta_s < 10:
        return "just now"
    if delta_s < 60:
        return f"{int(delta_s)}s"
    if delta_s < 3600:
        return f"{int(delta_s // 60)}m"
    if delta_s < 86400:
        h = int(delta_s // 3600)
        m = int((delta_s % 3600) // 60)
        return f"{h}h {m}m"
    d = int(delta_s // 86400)
    h = int((delta_s % 86400) // 3600)
    return f"{d}d {h}h"
