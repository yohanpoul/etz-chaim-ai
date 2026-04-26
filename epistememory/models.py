"""Modèles de données — Binah-de-Yesod : classification structurée."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID


class SourceSephirah(str, Enum):
    KETER = "keter"
    CHOKMAH = "chokmah"
    BINAH = "binah"
    CHESED = "chesed"
    GEVURAH = "gevurah"
    TIFERET = "tiferet"
    NETZACH = "netzach"
    HOD = "hod"
    YESOD = "yesod"
    MALKUTH = "malkuth"
    DAAT = "daat"
    EXTERNAL = "external"
    SIFREI_YESOD = "sifrei_yesod"
    UNKNOWN = "unknown"


class EpistemicStatus(str, Enum):
    HYPOTHESIS = "hypothesis"
    CORRELATION = "correlation"
    VERIFIED_ONCE = "verified_once"
    VERIFIED_MULTI = "verified_multi"
    FACT = "fact"
    CONTESTED = "contested"
    DEPRECATED = "deprecated"


@dataclass
class MemoryEntry:
    """Une entrée en mémoire avec ses méta-données épistémiques."""

    id: UUID
    content: str
    source_sephirah: SourceSephirah
    confidence: float
    epistemic_status: EpistemicStatus
    created_at: datetime
    last_accessed: datetime | None = None
    access_count: int = 0
    domain: str | None = None
    tags: list[str] = field(default_factory=list)
    contradicts: list[UUID] = field(default_factory=list)
    supports: list[UUID] = field(default_factory=list)
    supersedes: UUID | None = None
    superseded_by: UUID | None = None
    ttl_days: int | None = None
    expires_at: datetime | None = None
    source_detail: dict[str, Any] | None = None
    similarity: float | None = None  # score de similarité lors du recall
    warning: str | None = None  # alertes Nogah (near_expiration, etc.)


@dataclass
class MemoryStats:
    """Hod-de-Yesod : la mémoire se décrit elle-même."""

    total_entries: int
    active_entries: int
    deprecated_entries: int
    by_status: dict[str, int]
    by_domain: dict[str, int]
    by_source: dict[str, int]
    avg_confidence: float
    contradictions_open: int
    near_expiration: int
    oldest_entry: datetime | None
    newest_entry: datetime | None


@dataclass
class GCReport:
    """Gevurah-de-Yesod : rapport du garbage collector."""

    expired_count: int
    expired_ids: list[UUID]
    deprecated_count: int
    deprecated_ids: list[UUID]
    low_confidence_count: int
    low_confidence_ids: list[UUID]
    total_removed: int
