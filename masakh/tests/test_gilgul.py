"""Tests Gilgul — גִּלְגּוּל — migration de patterns Tikkun/Onesh.

Couvre :
  - classify_reshimo : Tikkun, Onesh, Neutral correctement
  - Erreurs de configuration détectées → Onesh
  - purge_onesh : retire les Onesh, garde les Tikkun et Neutral
  - get_tikkun_patterns : retourne les meilleurs, triés par score
  - Filtrage par olam
  - Pas de score → neutral
"""

import pytest

from masakh.gilgul import (
    Gilgul,
    TIKKUN,
    ONESH,
    NEUTRAL,
    TIKKUN_SCORE_THRESHOLD,
    ONESH_SCORE_THRESHOLD,
)


@pytest.fixture
def gilgul():
    return Gilgul()


def _reshimo(olam: str, score: float | None, level: str = "gimel",
             kavvanah: dict | None = None) -> dict:
    """Construire un Reshimo minimal pour les tests."""
    aviut = {"masakh_level": level, "was_filtered": True}
    if score is not None:
        aviut["score"] = score
    if kavvanah is not None:
        aviut["kavvanah"] = kavvanah
    elif level in ("gimel", "dalet"):
        aviut["kavvanah"] = {"intention": "test"}
    return {
        "olam": olam,
        "reshimo_hitlabshut": {"response_preview": "test"},
        "reshimo_aviut": aviut,
    }


# ── classify_reshimo ──────────────────────────────────────

class TestClassify:

    def test_high_score_is_tikkun(self, gilgul):
        r = _reshimo("briah", 0.85)
        assert gilgul.classify_reshimo(r) == TIKKUN

    def test_threshold_score_is_tikkun(self, gilgul):
        r = _reshimo("briah", TIKKUN_SCORE_THRESHOLD)
        assert gilgul.classify_reshimo(r) == TIKKUN

    def test_low_score_is_onesh(self, gilgul):
        r = _reshimo("briah", 0.1)
        assert gilgul.classify_reshimo(r) == ONESH

    def test_mid_score_is_neutral(self, gilgul):
        r = _reshimo("briah", 0.5)
        assert gilgul.classify_reshimo(r) == NEUTRAL

    def test_no_score_is_neutral(self, gilgul):
        r = _reshimo("briah", None)
        assert gilgul.classify_reshimo(r) == NEUTRAL

    def test_zero_score_is_onesh(self, gilgul):
        r = _reshimo("briah", 0.0)
        assert gilgul.classify_reshimo(r) == ONESH

    def test_just_below_tikkun_is_neutral(self, gilgul):
        r = _reshimo("briah", TIKKUN_SCORE_THRESHOLD - 0.01)
        assert gilgul.classify_reshimo(r) == NEUTRAL

    def test_just_at_onesh_boundary_is_onesh(self, gilgul):
        r = _reshimo("briah", ONESH_SCORE_THRESHOLD - 0.01)
        assert gilgul.classify_reshimo(r) == ONESH


# ── Erreurs de configuration → Onesh ────────��────────────

class TestConfigErrors:

    def test_no_olam_is_onesh(self, gilgul):
        r = {"olam": "", "reshimo_aviut": {"score": 0.9, "masakh_level": "bet"}}
        assert gilgul.classify_reshimo(r) == ONESH

    def test_no_masakh_level_is_onesh(self, gilgul):
        r = {"olam": "briah", "reshimo_aviut": {"score": 0.9}}
        assert gilgul.classify_reshimo(r) == ONESH

    def test_gimel_without_kavvanah_is_onesh(self, gilgul):
        r = {"olam": "briah", "reshimo_aviut": {
            "score": 0.9, "masakh_level": "gimel"
        }}
        assert gilgul.classify_reshimo(r) == ONESH

    def test_dalet_without_kavvanah_is_onesh(self, gilgul):
        r = {"olam": "atziluth", "reshimo_aviut": {
            "score": 0.9, "masakh_level": "dalet"
        }}
        assert gilgul.classify_reshimo(r) == ONESH

    def test_bet_without_kavvanah_ok(self, gilgul):
        """Bet et Aleph n'exigent pas de Kavvanah."""
        r = _reshimo("yetzirah", 0.8, level="bet", kavvanah=None)
        # Override pour ne pas avoir de kavvanah auto
        r["reshimo_aviut"].pop("kavvanah", None)
        assert gilgul.classify_reshimo(r) == TIKKUN

    def test_empty_aviut_is_neutral(self, gilgul):
        r = {"olam": "briah", "reshimo_aviut": None}
        assert gilgul.classify_reshimo(r) == NEUTRAL


# ── purge_onesh ───────────────────────────────────────────

class TestPurge:

    def test_purge_removes_onesh(self, gilgul):
        data = [
            _reshimo("briah", 0.9),   # tikkun
            _reshimo("briah", 0.1),   # onesh
            _reshimo("briah", 0.5),   # neutral
        ]
        kept, purged = gilgul.purge_onesh(data)
        assert purged == 1
        assert len(kept) == 2

    def test_purge_preserves_tikkun(self, gilgul):
        data = [_reshimo("briah", 0.85)]
        kept, purged = gilgul.purge_onesh(data)
        assert purged == 0
        assert len(kept) == 1

    def test_purge_preserves_neutral(self, gilgul):
        data = [_reshimo("briah", 0.5)]
        kept, purged = gilgul.purge_onesh(data)
        assert purged == 0
        assert len(kept) == 1

    def test_purge_all_onesh(self, gilgul):
        data = [
            _reshimo("briah", 0.1),
            _reshimo("briah", 0.2),
        ]
        kept, purged = gilgul.purge_onesh(data)
        assert purged == 2
        assert len(kept) == 0

    def test_purge_modifies_in_place(self, gilgul):
        data = [
            _reshimo("briah", 0.9),
            _reshimo("briah", 0.1),
        ]
        gilgul.purge_onesh(data)
        assert len(data) == 1

    def test_purge_by_olam(self, gilgul):
        data = [
            _reshimo("briah", 0.1),   # onesh briah
            _reshimo("assiah", 0.1),  # onesh assiah — pas touché
        ]
        # Assiah est à level "gimel" par défaut dans le helper, corrigeons
        data[1]["reshimo_aviut"]["masakh_level"] = "aleph"
        kept, purged = gilgul.purge_onesh(data, olam="briah")
        assert purged == 1
        assert len(kept) == 1
        assert kept[0]["olam"] == "assiah"

    def test_purge_empty_list(self, gilgul):
        data = []
        kept, purged = gilgul.purge_onesh(data)
        assert purged == 0
        assert kept == []


# ── get_tikkun_patterns ─────────────���─────────────────────

class TestGetTikkun:

    def test_returns_tikkun_only(self, gilgul):
        data = [
            _reshimo("briah", 0.9),
            _reshimo("briah", 0.1),
            _reshimo("briah", 0.5),
        ]
        patterns = gilgul.get_tikkun_patterns("briah", reshimot=data)
        assert len(patterns) == 1
        assert patterns[0]["reshimo_aviut"]["score"] == 0.9

    def test_sorted_by_score_desc(self, gilgul):
        data = [
            _reshimo("briah", 0.75),
            _reshimo("briah", 0.95),
            _reshimo("briah", 0.8),
        ]
        patterns = gilgul.get_tikkun_patterns("briah", reshimot=data)
        scores = [p["reshimo_aviut"]["score"] for p in patterns]
        assert scores == sorted(scores, reverse=True)

    def test_limit(self, gilgul):
        data = [_reshimo("briah", 0.8 + i * 0.01) for i in range(10)]
        patterns = gilgul.get_tikkun_patterns("briah", limit=3, reshimot=data)
        assert len(patterns) == 3

    def test_filters_by_olam(self, gilgul):
        data = [
            _reshimo("briah", 0.9),
            _reshimo("assiah", 0.9),
        ]
        # Fix assiah level
        data[1]["reshimo_aviut"]["masakh_level"] = "aleph"
        data[1]["reshimo_aviut"].pop("kavvanah", None)
        patterns = gilgul.get_tikkun_patterns("briah", reshimot=data)
        assert len(patterns) == 1
        assert patterns[0]["olam"] == "briah"

    def test_empty_if_no_tikkun(self, gilgul):
        data = [_reshimo("briah", 0.2)]
        patterns = gilgul.get_tikkun_patterns("briah", reshimot=data)
        assert patterns == []

    def test_empty_list(self, gilgul):
        patterns = gilgul.get_tikkun_patterns("briah", reshimot=[])
        assert patterns == []
