"""Tests Partzufim ↔ Masakh — F11 (EC-SHK-057, EC-SHK-083).

Le Katnut/Gadlut des Partzufim influence le niveau du Masakh :
  - Partzufim en katnut → Masakh monte d'un niveau (plus de filtrage)
  - Partzufim en gadlut → Masakh peut descendre d'un niveau
  - Cascades : Atik dégradé → tout katnut, Imma katnut → ZA katnut

Couvre :
  - regulate_masakh_from_partzufim() module-level function
  - _effective_mochin_for_masakh() cascade logic
  - Constructor offset via _PARTZUFIM_MASAKH_OFFSET
  - Interaction with hizdakchut (no conflict)
  - Edge cases (already at dalet/shoresh, empty state)
  - Reset function
"""

import pytest

from masakh import (
    Masakh,
    LEVEL_ORDER,
    OLAM_DEFAULT_LEVEL,
    regulate_masakh_from_partzufim,
    get_partzufim_masakh_offset,
    reset_partzufim_masakh_offset,
    reset_hizdakchut_levels,
    auto_hizdakchut,
    _effective_mochin_for_masakh,
    _PARTZUFIM_MASAKH_OFFSET,
    _PARTZUF_KATNUT_THRESHOLD,
    _PARTZUF_ATIK_CASCADE,
    _HIZDAKCHUT_LEVELS,
)


# ── Helpers ─────────────────────────────────────────────────

def _make_partzuf_state(overrides: dict | None = None) -> dict:
    """État par défaut : tous en gadlut/panim avec bon score."""
    defaults = {
        "atik_yomin": {"overall": 0.87, "mochin_state": "gadlut", "orientation": "panim"},
        "arikh_anpin": {"overall": 0.82, "mochin_state": "gadlut", "orientation": "panim"},
        "abba": {"overall": 0.75, "mochin_state": "gadlut", "orientation": "panim"},
        "imma": {"overall": 0.64, "mochin_state": "gadlut", "orientation": "panim"},
        "zeir_anpin": {"overall": 0.79, "mochin_state": "gadlut", "orientation": "panim"},
        "nukva": {"overall": 0.74, "mochin_state": "gadlut", "orientation": "panim"},
    }
    if overrides:
        for k, v in overrides.items():
            if k in defaults:
                defaults[k].update(v)
            else:
                defaults[k] = v
    return defaults


@pytest.fixture(autouse=True)
def _clean_masakh_state():
    """Reset all module-level state before each test."""
    _PARTZUFIM_MASAKH_OFFSET.clear()
    _HIZDAKCHUT_LEVELS.clear()
    yield
    _PARTZUFIM_MASAKH_OFFSET.clear()
    _HIZDAKCHUT_LEVELS.clear()


# ── Tests _effective_mochin_for_masakh ──────────────────────

class TestEffectiveMochin:

    def test_all_gadlut(self):
        state = _make_partzuf_state()
        za, nukva = _effective_mochin_for_masakh(state)
        assert za == "gadlut"
        assert nukva == "gadlut"

    def test_za_katnut_direct(self):
        state = _make_partzuf_state({"zeir_anpin": {"mochin_state": "katnut"}})
        za, nukva = _effective_mochin_for_masakh(state)
        assert za == "katnut"
        assert nukva == "gadlut"

    def test_nukva_katnut_direct(self):
        state = _make_partzuf_state({"nukva": {"mochin_state": "katnut"}})
        za, nukva = _effective_mochin_for_masakh(state)
        assert za == "gadlut"
        assert nukva == "katnut"

    def test_cascade_atik_degraded(self):
        """Atik < 0.5 → ZA et Nukva forcés en katnut."""
        state = _make_partzuf_state({"atik_yomin": {"overall": 0.3}})
        za, nukva = _effective_mochin_for_masakh(state)
        assert za == "katnut"
        assert nukva == "katnut"

    def test_cascade_imma_katnut_forces_za(self):
        """Imma en katnut → ZA forcé en katnut, Nukva inchangée."""
        state = _make_partzuf_state({"imma": {"mochin_state": "katnut"}})
        za, nukva = _effective_mochin_for_masakh(state)
        assert za == "katnut"
        assert nukva == "gadlut"

    def test_cascade_imma_low_score_forces_za(self):
        """Imma score < 0.4 → ZA forcé en katnut."""
        state = _make_partzuf_state({"imma": {"overall": 0.3, "mochin_state": "gadlut"}})
        za, nukva = _effective_mochin_for_masakh(state)
        assert za == "katnut"

    def test_za_low_score_forces_katnut(self):
        """ZA score < 0.4 → katnut même si mochin_state dit gadlut."""
        state = _make_partzuf_state({
            "zeir_anpin": {"overall": 0.35, "mochin_state": "gadlut"},
        })
        za, nukva = _effective_mochin_for_masakh(state)
        assert za == "katnut"

    def test_nukva_low_score_forces_katnut(self):
        """Nukva score < 0.4 → katnut."""
        state = _make_partzuf_state({
            "nukva": {"overall": 0.2, "mochin_state": "gadlut"},
        })
        za, nukva = _effective_mochin_for_masakh(state)
        assert nukva == "katnut"

    def test_transitional_state(self):
        state = _make_partzuf_state({
            "zeir_anpin": {"mochin_state": "transitional"},
            "nukva": {"mochin_state": "transitional"},
        })
        za, nukva = _effective_mochin_for_masakh(state)
        assert za == "transitional"
        assert nukva == "transitional"

    def test_empty_state(self):
        za, nukva = _effective_mochin_for_masakh({})
        assert za == "transitional"
        assert nukva == "transitional"


# ── Tests regulate_masakh_from_partzufim (module function) ──

class TestRegulateMasakhFromPartzufim:

    def test_katnut_sets_negative_offset(self):
        """Katnut → offset = -1 sur tous les olamot."""
        state = _make_partzuf_state({"zeir_anpin": {"mochin_state": "katnut"}})
        regulate_masakh_from_partzufim(state)
        offsets = get_partzufim_masakh_offset()
        for olam in OLAM_DEFAULT_LEVEL:
            assert offsets[olam] == -1

    def test_gadlut_sets_positive_offset(self):
        """Gadlut → offset = +1 sur tous les olamot."""
        state = _make_partzuf_state()
        regulate_masakh_from_partzufim(state)
        offsets = get_partzufim_masakh_offset()
        for olam in OLAM_DEFAULT_LEVEL:
            assert offsets[olam] == 1

    def test_transitional_sets_zero_offset(self):
        state = _make_partzuf_state({
            "zeir_anpin": {"mochin_state": "transitional"},
            "nukva": {"mochin_state": "transitional"},
        })
        regulate_masakh_from_partzufim(state)
        offsets = get_partzufim_masakh_offset()
        for olam in OLAM_DEFAULT_LEVEL:
            assert offsets[olam] == 0

    def test_returns_changed_olamot(self):
        """Retourne les olamot dont le niveau effectif a changé."""
        state = _make_partzuf_state({"nukva": {"mochin_state": "katnut"}})
        results = regulate_masakh_from_partzufim(state)
        # briah: gimel→dalet, yetzirah: bet→gimel, assiah: aleph→bet
        # atziluth: dalet→dalet (already max) → NOT in results
        assert "atziluth" not in results
        assert "briah" in results
        assert results["briah"]["from"] == "gimel"
        assert results["briah"]["to"] == "dalet"

    def test_empty_state_clears_offsets(self):
        _PARTZUFIM_MASAKH_OFFSET["briah"] = -1
        regulate_masakh_from_partzufim({})
        assert get_partzufim_masakh_offset() == {}

    def test_idempotent_same_state(self):
        """Appels répétés avec le même état → pas de changement."""
        state = _make_partzuf_state({"zeir_anpin": {"mochin_state": "katnut"}})
        r1 = regulate_masakh_from_partzufim(state)
        r2 = regulate_masakh_from_partzufim(state)
        assert len(r1) > 0
        assert len(r2) == 0  # Same offset, no change

    def test_transition_katnut_to_gadlut(self):
        """Passage katnut → gadlut change l'offset de -1 à +1."""
        katnut_state = _make_partzuf_state({"zeir_anpin": {"mochin_state": "katnut"}})
        regulate_masakh_from_partzufim(katnut_state)
        assert get_partzufim_masakh_offset()["briah"] == -1

        gadlut_state = _make_partzuf_state()
        results = regulate_masakh_from_partzufim(gadlut_state)
        assert get_partzufim_masakh_offset()["briah"] == 1
        # briah: base=gimel, old offset=-1 (→dalet), new offset=+1 (→bet)
        assert results["briah"]["from"] == "dalet"
        assert results["briah"]["to"] == "bet"


# ── Tests Constructor Offset ───────────────────────────────

class TestConstructorOffset:

    def test_no_offset_default_level(self):
        """Sans offset, le Masakh utilise le niveau par défaut."""
        m = Masakh("briah")
        assert m.level == "gimel"

    def test_negative_offset_pushes_up(self):
        """Offset -1 → monte d'un niveau."""
        _PARTZUFIM_MASAKH_OFFSET["briah"] = -1
        m = Masakh("briah")
        assert m.level == "dalet"  # gimel → dalet

    def test_positive_offset_pushes_down(self):
        """Offset +1 → descend d'un niveau."""
        _PARTZUFIM_MASAKH_OFFSET["briah"] = 1
        m = Masakh("briah")
        assert m.level == "bet"  # gimel → bet

    def test_offset_clamped_at_dalet(self):
        """Offset ne dépasse pas dalet (le plus filtrant)."""
        _PARTZUFIM_MASAKH_OFFSET["atziluth"] = -1
        m = Masakh("atziluth")
        assert m.level == "dalet"  # dalet - 1 = still dalet (clamped)

    def test_offset_clamped_at_shoresh(self):
        """Offset ne dépasse pas shoresh (le moins filtrant)."""
        _PARTZUFIM_MASAKH_OFFSET["assiah"] = 1
        m = Masakh("assiah")
        assert m.level == "shoresh"  # aleph + 1 = shoresh

    def test_explicit_level_ignores_offset(self):
        """Level explicite → offset ignoré (pour auto_hizdakchut)."""
        _PARTZUFIM_MASAKH_OFFSET["briah"] = -1
        m = Masakh("briah", level="bet")
        assert m.level == "bet"  # level explicite prime

    def test_offset_combines_with_hizdakchut(self):
        """Offset s'applique SUR le niveau hizdakchut."""
        _HIZDAKCHUT_LEVELS["briah"] = "bet"  # hizdakchut a ajusté à bet
        _PARTZUFIM_MASAKH_OFFSET["briah"] = -1  # partzufim pousse up
        m = Masakh("briah")
        assert m.level == "gimel"  # bet - 1 = gimel

    def test_offset_on_hizdakchut_positive(self):
        """Gadlut + hizdakchut combinés."""
        _HIZDAKCHUT_LEVELS["briah"] = "bet"
        _PARTZUFIM_MASAKH_OFFSET["briah"] = 1  # gadlut
        m = Masakh("briah")
        assert m.level == "aleph"  # bet + 1 = aleph


# ── Tests Reset ────────────────────────────────────────────

class TestReset:

    def test_reset_clears_offsets(self):
        _PARTZUFIM_MASAKH_OFFSET["briah"] = -1
        _PARTZUFIM_MASAKH_OFFSET["assiah"] = 1
        reset_partzufim_masakh_offset()
        assert get_partzufim_masakh_offset() == {}

    def test_after_reset_default_levels(self):
        _PARTZUFIM_MASAKH_OFFSET["briah"] = -1
        reset_partzufim_masakh_offset()
        m = Masakh("briah")
        assert m.level == "gimel"


# ── Tests interaction avec hizdakchut ──────────────────────

class TestInteractionHizdakchut:

    def test_auto_hizdakchut_not_affected_by_offset(self):
        """auto_hizdakchut passe level= explicite → offset ignoré."""
        _PARTZUFIM_MASAKH_OFFSET["briah"] = -1

        # auto_hizdakchut crée Masakh(olam, level=current_level)
        # Le level explicite doit ignorer l'offset
        m = Masakh("briah", level="gimel")
        assert m.level == "gimel"  # NOT dalet

    def test_partzufim_and_hizdakchut_independent(self):
        """Les deux régulations ne se contaminent pas."""
        # Setup hizdakchut
        _HIZDAKCHUT_LEVELS["yetzirah"] = "gimel"
        # Setup partzufim
        _PARTZUFIM_MASAKH_OFFSET["yetzirah"] = -1

        # Constructor: base=gimel (hizdakchut), offset=-1 → dalet
        m = Masakh("yetzirah")
        assert m.level == "dalet"

        # Reset partzufim only
        reset_partzufim_masakh_offset()
        # Now: base=gimel (hizdakchut still there), offset=0
        m2 = Masakh("yetzirah")
        assert m2.level == "gimel"

        # Reset hizdakchut too
        reset_hizdakchut_levels()
        m3 = Masakh("yetzirah")
        assert m3.level == "bet"  # default for yetzirah


# ── Tests end-to-end ───────────────────────────────────────

class TestEndToEnd:

    def test_full_cycle_katnut_then_gadlut(self):
        """Cycle complet : neutre → katnut → gadlut → neutre."""
        # 1. Initial: pas d'offset
        m1 = Masakh("briah")
        assert m1.level == "gimel"

        # 2. Partzufim passent en katnut
        katnut_state = _make_partzuf_state({
            "zeir_anpin": {"mochin_state": "katnut"},
        })
        results = regulate_masakh_from_partzufim(katnut_state)
        assert "briah" in results
        m2 = Masakh("briah")
        assert m2.level == "dalet"  # gimel → dalet

        # 3. Partzufim reviennent en gadlut
        gadlut_state = _make_partzuf_state()
        results = regulate_masakh_from_partzufim(gadlut_state)
        assert "briah" in results
        m3 = Masakh("briah")
        assert m3.level == "bet"  # gimel → bet

        # 4. Reset
        reset_partzufim_masakh_offset()
        m4 = Masakh("briah")
        assert m4.level == "gimel"  # back to default

    def test_cascade_atik_affects_all_olamot(self):
        """Atik dégradé → tous les olamot montent d'un niveau."""
        state = _make_partzuf_state({"atik_yomin": {"overall": 0.3}})
        results = regulate_masakh_from_partzufim(state)

        # atziluth (dalet) → already max → no change
        assert "atziluth" not in results
        # briah (gimel→dalet)
        assert results["briah"]["to"] == "dalet"
        # yetzirah (bet→gimel)
        assert results["yetzirah"]["to"] == "gimel"
        # assiah (aleph→bet)
        assert results["assiah"]["to"] == "bet"


# ── Test synchronisation des seuils ────────────────────────

class TestThresholdSync:
    """Les seuils de cascade dupliqués dans masakh/__init__.py doivent
    rester synchronisés avec les valeurs canoniques de partzufim.regulator."""

    def test_cascade_thresholds_match_regulator(self):
        from partzufim.regulator import KATNUT_THRESHOLD, ATIK_CASCADE_THRESHOLD
        assert _PARTZUF_KATNUT_THRESHOLD == KATNUT_THRESHOLD
        assert _PARTZUF_ATIK_CASCADE == ATIK_CASCADE_THRESHOLD
