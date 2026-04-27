"""LLM response cache — sha256 keyed, content-addressed, atomic writes.

Sauve chaque appel LLM successful pour :
- Reproductibilité offline (re-bench sans payer 2× l'API)
- Replay reviewer (ship le cache.tar.gz, reviewer judge sans accès API gen)
- Resume après crash (avant même le checkpoint, si LLM call a réussi mais
  le checkpoint n'a pas été flush)

Cache key = sha256(json({model, prompt, temperature, system_prompt, thinking})).
Idempotent : 2 appels mêmes params → 1 entrée cache.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class CacheEntry:
    """Entrée cache LLM."""

    response_text: str
    latency_ms: int
    tokens_input: int = 0
    tokens_output: int = 0
    tokens_cache_read: int = 0
    tokens_cache_creation: int = 0
    cost_usd: float = 0.0
    model: str = ""
    cached_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CacheEntry:
        return cls(**d)


def cache_key(
    model: str,
    prompt: str,
    temperature: float = 0.0,
    system_prompt: str | None = None,
    thinking: bool = False,
) -> str:
    """Compute deterministic sha256 cache key.

    Inclut tous les paramètres qui affectent la génération.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "temperature": round(temperature, 4),
        "system_prompt": system_prompt or "",
        "thinking": bool(thinking),
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class LLMCache:
    """Cache filesystem-backed avec atomic writes.

    Structure :
        cache_dir/
        ├── ab/                    # premiers 2 chars sha256 (sharding)
        │   └── ab12cd34....json
        └── ...
    """

    def __init__(self, cache_dir: Path | str):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._hits = 0
        self._misses = 0
        self._writes = 0

    def _path_for(self, key: str) -> Path:
        """Sharded path : cache_dir/ab/ab12cd34....json."""
        shard = key[:2]
        shard_dir = self.cache_dir / shard
        shard_dir.mkdir(exist_ok=True)
        return shard_dir / f"{key}.json"

    def get(self, key: str) -> CacheEntry | None:
        """Lookup cache entry by key."""
        path = self._path_for(key)
        if not path.exists():
            self._misses += 1
            return None
        try:
            data = json.loads(path.read_text())
            self._hits += 1
            return CacheEntry.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError):
            # Corrupted entry — treat as miss
            self._misses += 1
            return None

    def put(self, key: str, entry: CacheEntry) -> None:
        """Atomic write : tmp + fsync + rename."""
        import time as _time
        if entry.cached_at == 0.0:
            entry.cached_at = _time.time()

        path = self._path_for(key)
        tmp = path.with_suffix(".json.tmp")
        with tmp.open("w") as f:
            json.dump(entry.to_dict(), f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(path)
        self._writes += 1

    def stats(self) -> dict[str, int]:
        """Hit/miss/write counters depuis instanciation."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "writes": self._writes,
            "hit_rate_pct": round(hit_rate * 100, 1),
        }

    def size_bytes(self) -> int:
        """Taille totale cache sur disque."""
        return sum(
            f.stat().st_size
            for f in self.cache_dir.rglob("*.json")
            if f.is_file()
        )

    def count(self) -> int:
        """Nombre d'entrées cache."""
        return sum(1 for _ in self.cache_dir.rglob("*.json"))


if __name__ == "__main__":
    # Smoke test
    import tempfile
    import shutil

    tmp = Path(tempfile.mkdtemp())
    try:
        cache = LLMCache(tmp / "cache")

        key1 = cache_key("opus", "What is Tsimtsum?", 0.0)
        key2 = cache_key("opus", "What is Tsimtsum?", 0.0)
        key3 = cache_key("opus", "What is Tsimtsum?", 0.7)
        assert key1 == key2  # déterministe
        assert key1 != key3  # temperature différente

        # Miss puis hit
        assert cache.get(key1) is None
        cache.put(key1, CacheEntry(
            response_text="Tsimtsum is contraction.",
            latency_ms=12000,
            tokens_input=15,
            tokens_output=30,
            cost_usd=0.0024,
            model="claude-opus-4-20250514",
        ))
        entry = cache.get(key1)
        assert entry is not None
        assert entry.response_text == "Tsimtsum is contraction."
        assert entry.tokens_input == 15

        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["writes"] == 1

        assert cache.count() == 1
        assert cache.size_bytes() > 0

        print("PASS — LLM cache atomic put+get+stats working")
        print(f"  cache size: {cache.size_bytes()} bytes ({cache.count()} entries)")
        print(f"  stats: {stats}")
    finally:
        shutil.rmtree(tmp)
