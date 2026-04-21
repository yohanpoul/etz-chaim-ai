"""Pont Sifrei Yesod → code Etz Chaim AI (Sprint 10 Phase B).

Permet aux modules (MazalEngine, futurs) de citer leurs sources primaires
hébraïques/araméennes (Rabbi Hayyim Vital, Etz Chaim + Zohar Idra Rabba).

Scope généralisé (post-Sprint 9 Phase 0) :
    - tout le corpus `sifrei_yesod/sefarim/` (EC-*, Z-IR-*, REL-*, PG-*).
    - cache mtime-invalidation par fichier (rebuild quand un YAML change).
    - indices inversés par concept / module / partzuf.
    - API minimale étendue avec 5 helpers.

API publique:
    load_assertion(id)       -> dict | None         (item complet)
    load_by_concept(id)      -> list[dict]          (assertions citant ce concept)
    load_by_module(path)     -> list[dict]          (mapping.modules contient path)
    load_by_partzuf(name)    -> list[dict]          (mapping.partzufim contient name)
    load_all_ids()           -> list[str]           (tous les IDs indexés)
    search(query, fields=()) -> list[dict]          (substring sur fields, case-insensitive)

Backward compat Sprint 9 : load_assertion("EC-K5-001") reste fidèle.
"""

from __future__ import annotations

import threading
from pathlib import Path

import yaml

_SIFREI_ROOT = Path(__file__).resolve().parent.parent / "sifrei_yesod" / "sefarim"

_LOCK = threading.Lock()
_FILE_MTIMES: dict[Path, float] = {}
_INDEX: dict[str, tuple[Path, dict]] = {}
_BY_CONCEPT: dict[str, set[str]] = {}
_BY_MODULE: dict[str, set[str]] = {}
_BY_PARTZUF: dict[str, set[str]] = {}

_ITEM_KEYS = ("assertions", "relations", "principes_generatifs")
_DEFAULT_SEARCH_FIELDS = (
    "source_he",
    "source_aramaic",
    "assertion",
    "source_ref",
    "translation_fr",
    "nature",
    "formalisation",
)


def _all_yaml_files() -> list[Path]:
    if not _SIFREI_ROOT.exists():
        return []
    return [p for p in _SIFREI_ROOT.rglob("*.yaml") if p.name != "meta.yaml"]


def _parse_file(path: Path) -> list[dict]:
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except (OSError, yaml.YAMLError):
        return []
    if not isinstance(data, dict):
        return []
    items: list[dict] = []
    for key in _ITEM_KEYS:
        for item in data.get(key, []) or []:
            if isinstance(item, dict) and item.get("id"):
                items.append(item)
    return items


def _index_item(path: Path, item: dict) -> None:
    aid = item["id"]
    _INDEX[aid] = (path, item)
    for concept in item.get("concepts", []) or []:
        cid = concept.get("id") if isinstance(concept, dict) else None
        if cid:
            _BY_CONCEPT.setdefault(cid, set()).add(aid)
    mapping = item.get("mapping") or {}
    for module_path in mapping.get("modules", []) or []:
        if module_path:
            _BY_MODULE.setdefault(module_path, set()).add(aid)
    for partzuf in mapping.get("partzufim", []) or []:
        if partzuf:
            _BY_PARTZUF.setdefault(partzuf, set()).add(aid)


def _ensure_index() -> None:
    """Rebuild index if any YAML mtime changed (or first call)."""
    with _LOCK:
        files = _all_yaml_files()
        try:
            current_mtimes = {p: p.stat().st_mtime for p in files}
        except OSError:
            current_mtimes = {}
        if current_mtimes == _FILE_MTIMES and _INDEX:
            return
        _INDEX.clear()
        _BY_CONCEPT.clear()
        _BY_MODULE.clear()
        _BY_PARTZUF.clear()
        for path in files:
            for item in _parse_file(path):
                _index_item(path, item)
        _FILE_MTIMES.clear()
        _FILE_MTIMES.update(current_mtimes)


def load_assertion(ec_id: str) -> dict | None:
    """Charge un item indexé (assertion, relation ou principe génératif) par id.

    Args:
        ec_id: identifiant canonique (ex: ``"EC-K5-001"``, ``"Z-IR-T08-001"``,
            ``"REL-K5-001"``, ``"PG-K5-001"``).

    Returns:
        Dict avec les clés de l'item (``id``, ``source_he``/``source_aramaic``,
        ``assertion``, etc.). ``None`` si l'id n'est pas trouvé.
    """
    if not ec_id:
        return None
    _ensure_index()
    entry = _INDEX.get(ec_id)
    if entry is None:
        return None
    return dict(entry[1])


def load_by_concept(concept_id: str) -> list[dict]:
    """Items dont ``concepts[].id`` contient ``concept_id``."""
    if not concept_id:
        return []
    _ensure_index()
    ids = _BY_CONCEPT.get(concept_id, set())
    return [dict(_INDEX[aid][1]) for aid in sorted(ids)]


def load_by_module(module_path: str) -> list[dict]:
    """Items dont ``mapping.modules`` contient ``module_path``."""
    if not module_path:
        return []
    _ensure_index()
    ids = _BY_MODULE.get(module_path, set())
    return [dict(_INDEX[aid][1]) for aid in sorted(ids)]


def load_by_partzuf(name: str) -> list[dict]:
    """Items dont ``mapping.partzufim`` contient ``name``."""
    if not name:
        return []
    _ensure_index()
    ids = _BY_PARTZUF.get(name, set())
    return [dict(_INDEX[aid][1]) for aid in sorted(ids)]


def load_all_ids() -> list[str]:
    """Tous les IDs indexés (triés)."""
    _ensure_index()
    return sorted(_INDEX.keys())


def search(query: str, fields: tuple[str, ...] = _DEFAULT_SEARCH_FIELDS) -> list[dict]:
    """Recherche substring case-insensitive sur ``fields``.

    Hebrew/Aramaic sont insensibles à la casse — le lowering est no-op.
    """
    if not query:
        return []
    _ensure_index()
    needle = query.lower()
    hits: list[tuple[str, dict]] = []
    for aid, (_path, item) in _INDEX.items():
        for field in fields:
            val = item.get(field, "")
            if isinstance(val, str) and needle in val.lower():
                hits.append((aid, item))
                break
    hits.sort(key=lambda t: t[0])
    return [dict(item) for _aid, item in hits]
