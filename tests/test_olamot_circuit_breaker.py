"""Tests pour le circuit breaker Ollama + le fallback cache d'embeddings.

Vérifie la recommandation I1 de l'audit Cycle 4 :
- Half-open : cooldown expiré → compteur reset à 0 (pas 5).
- Half-open : un échec post-cooldown ne re-ouvre pas immédiatement.
- Fallback cache : embedding servi depuis le cache si Ollama échoue.
- Fallback cache : embedding servi depuis le cache si CB ouvert.
"""

from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def _reset_cb_and_cache():
    """Reset l'état CB + cache entre chaque test."""
    import olamot
    olamot._ollama_cb_failures = 0
    olamot._ollama_cb_open_until = 0.0
    olamot._embed_cache_clear()
    yield
    olamot._ollama_cb_failures = 0
    olamot._ollama_cb_open_until = 0.0
    olamot._embed_cache_clear()


class _FakeResp:
    """urllib.urlopen context-manager fake."""

    def __init__(self, payload: dict):
        self._payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._payload


def _make_embedding_response(dim: int = 4) -> dict:
    return {"embeddings": [[0.1] * dim]}


# ─── Half-open behavior ───────────────────────────────────────


class TestHalfOpen:
    def test_open_raises_during_cooldown(self):
        import olamot
        olamot._ollama_cb_failures = olamot._OLLAMA_CB_THRESHOLD
        olamot._ollama_cb_open_until = time.monotonic() + 60.0
        with pytest.raises(olamot.OllamaCircuitOpenError):
            olamot._ollama_cb_check()

    def test_cooldown_expired_resets_counter(self):
        """Après cooldown, _cb_check ne doit PAS lever, et remettre
        le compteur à 0 pour éviter la re-ouverture immédiate."""
        import olamot
        olamot._ollama_cb_failures = olamot._OLLAMA_CB_THRESHOLD
        olamot._ollama_cb_open_until = time.monotonic() - 1.0  # déjà expiré

        olamot._ollama_cb_check()  # ne doit pas lever

        assert olamot._ollama_cb_failures == 0
        assert olamot._ollama_cb_open_until == 0.0

    def test_failure_after_half_open_goes_to_1_not_6(self):
        """Bug historique : sans reset, le 1er échec post-cooldown
        ferait _failures=6 et re-ouvrirait le circuit immédiatement."""
        import olamot
        olamot._ollama_cb_failures = olamot._OLLAMA_CB_THRESHOLD
        olamot._ollama_cb_open_until = time.monotonic() - 1.0

        olamot._ollama_cb_check()  # half-open, reset à 0
        olamot._ollama_cb_failure()  # premier échec post-recovery

        assert olamot._ollama_cb_failures == 1
        # Circuit ne doit PAS être ouvert après un seul échec.
        assert olamot._ollama_cb_open_until == 0.0

    def test_success_after_half_open_keeps_counter_at_zero(self):
        import olamot
        olamot._ollama_cb_failures = olamot._OLLAMA_CB_THRESHOLD
        olamot._ollama_cb_open_until = time.monotonic() - 1.0

        olamot._ollama_cb_check()  # half-open, reset
        olamot._ollama_cb_success()

        assert olamot._ollama_cb_failures == 0
        assert olamot._ollama_cb_open_until == 0.0


# ─── Embedding fallback cache ─────────────────────────────────


class TestEmbeddingFallbackCache:
    def test_cache_put_get_roundtrip(self):
        import olamot
        olamot._embed_cache_put("m", "hello", [0.1, 0.2, 0.3])
        assert olamot._embed_cache_get("m", "hello") == [0.1, 0.2, 0.3]

    def test_cache_miss_returns_none(self):
        import olamot
        assert olamot._embed_cache_get("m", "never-seen") is None

    def test_cache_isolates_by_model(self):
        import olamot
        olamot._embed_cache_put("m1", "x", [1.0])
        assert olamot._embed_cache_get("m2", "x") is None

    def test_cache_bounded_size(self):
        import olamot
        original = olamot._EMBED_CACHE_MAX_SIZE
        olamot._EMBED_CACHE_MAX_SIZE = 3
        try:
            for i in range(5):
                olamot._embed_cache_put("m", f"t{i}", [float(i)])
            # Les 2 plus anciens doivent avoir été évincés (LRU).
            assert olamot._embed_cache_get("m", "t0") is None
            assert olamot._embed_cache_get("m", "t1") is None
            assert olamot._embed_cache_get("m", "t4") == [4.0]
        finally:
            olamot._EMBED_CACHE_MAX_SIZE = original

    def test_embed_populates_cache_on_success(self):
        import olamot
        resp = _FakeResp(_make_embedding_response())
        with patch("olamot.urllib.request.urlopen", return_value=resp):
            vec = olamot.ollama_embed("hello", model="fake-model")
        assert vec == [0.1, 0.1, 0.1, 0.1]
        # Le cache doit maintenant contenir ce vecteur.
        assert olamot._embed_cache_get("fake-model", "hello") == vec

    def test_embed_falls_back_to_cache_on_ollama_failure(self):
        """Si Ollama échoue et qu'un embedding est en cache, on le sert."""
        import olamot
        # Pré-populer le cache.
        olamot._embed_cache_put("fake-model", "hello", [9.0, 9.0])

        def _boom(*a, **kw):
            raise ConnectionError("Ollama down")

        with patch("olamot.urllib.request.urlopen", side_effect=_boom):
            vec = olamot.ollama_embed("hello", model="fake-model")

        assert vec == [9.0, 9.0]
        # L'échec a tout de même été compté dans le CB.
        assert olamot._ollama_cb_failures == 1

    def test_embed_reraises_when_ollama_fails_and_cache_miss(self):
        import olamot

        def _boom(*a, **kw):
            raise ConnectionError("Ollama down")

        with patch("olamot.urllib.request.urlopen", side_effect=_boom):
            with pytest.raises(RuntimeError, match="Ollama embed failed"):
                olamot.ollama_embed("never-cached", model="fake-model")

    def test_embed_serves_cache_when_circuit_open(self):
        """Circuit ouvert → pas d'appel réseau, sert depuis cache."""
        import olamot
        olamot._embed_cache_put("fake-model", "hello", [7.7])
        olamot._ollama_cb_failures = olamot._OLLAMA_CB_THRESHOLD
        olamot._ollama_cb_open_until = time.monotonic() + 60.0

        def _should_not_be_called(*a, **kw):
            raise AssertionError("urlopen ne doit PAS être appelé")

        with patch(
            "olamot.urllib.request.urlopen", side_effect=_should_not_be_called
        ):
            vec = olamot.ollama_embed("hello", model="fake-model")

        assert vec == [7.7]

    def test_embed_reraises_circuit_open_when_no_cache(self):
        import olamot
        olamot._ollama_cb_failures = olamot._OLLAMA_CB_THRESHOLD
        olamot._ollama_cb_open_until = time.monotonic() + 60.0

        with pytest.raises(olamot.OllamaCircuitOpenError):
            olamot.ollama_embed("never-cached", model="fake-model")
