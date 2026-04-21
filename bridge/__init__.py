"""bridge — Pont entre Sifrei Yesod (doctrine) et code Etz Chaim AI.

Sprint 10 Phase B : chargeur généralisé sur tout le corpus
`sifrei_yesod/sefarim/` avec cache mtime-invalidation et indices inversés
(concept / module / partzuf).

Public API:
    load_assertion(id)        -> dict | None
    load_by_concept(cid)      -> list[dict]
    load_by_module(path)      -> list[dict]
    load_by_partzuf(name)     -> list[dict]
    load_all_ids()            -> list[str]
    search(query)             -> list[dict]
"""

from bridge.sifrei_reader import (
    load_all_ids,
    load_assertion,
    load_by_concept,
    load_by_module,
    load_by_partzuf,
    search,
)

__all__ = [
    "load_all_ids",
    "load_assertion",
    "load_by_concept",
    "load_by_module",
    "load_by_partzuf",
    "search",
]
