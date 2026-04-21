"""Tests ContextMonitor — monitoring 29 dimensions.

Couvre :
  - assess avec données complètes (tout ✓)
  - assess avec données incomplètes (✗ et △)
  - assess avec données minimales (tout ✗ sauf Malkhut)
  - score_global pondéré (v2: ✓×1 + △×0.5) correct dans chaque cas
  - 29 dimensions exactement
  - 20 auto-mesurables (v2), 9 non-applicables
  - Kavvanah partielle → △
  - Chesed/Gevurah partielle (Masakh non filtrant) → △
  - F2: Da'at(08) auto via daat_bridge dans pipeline_steps
  - F3: Zivvug(15) et Panim/Achor(24) via update_post_response
  - F4: Hitlabshut(19), Arakhin(20), Tzelem(21) via pipeline_steps
  - F4: IYM(23) via maturation_stage
  - F4: Gilgul(28) via tikkun_patterns_count
  - F5: Tsimtsum(29) via pressure_regulated OU was_filtered
  - Fix1: dim 25 (Katnut/Gadlut) séparée de dim 27 (Masakh)
  - Fix3: dims 12 (Yesod), 16 (Birur), 17 (ABYA), 22 (Stade) auto
  - Fix4: score pondéré (△ = 0.5)
"""

import pytest

from masakh.context_monitor import (
    ContextMonitor,
    DIMENSIONS,
    AUTO_IDS,
    STATUS_OK,
    STATUS_PARTIAL,
    STATUS_ABSENT,
    STATUS_NA,
)


@pytest.fixture
def monitor():
    return ContextMonitor()


def _full_call_data() -> dict:
    """Données complètes — tout opérant (sauf Zivvug/Panim qui sont post-response)."""
    return {
        "olam": "briah",
        "kavvanah": {"intention": "analyser la structure"},
        "masakh_log": {
            "was_filtered": True,
            "aviut_level": "gimel",
            "kashiut": 0.7,
            "tokens_rejected": 150,
        },
        "reshimo_written": True,
        "token_ratio_logged": True,
        # F4 fields
        "pipeline_steps": [
            "gilgul_init", "maturation", "rosh", "arakhin",
            "hitlabshut", "daat_bridge", "toch", "sof", "tzelem", "monitor",
        ],
        "maturation_stage": "mochin",
        "tikkun_patterns_count": 3,
        # F5 — Tsimtsum→Masakh pressure regulation
        "pressure_regulated": True,
        # Fix 3 — Yesod (mémoire active)
        "memory_active": True,
        # 29/29 — Tree signals
        "active_profile": "claude_max",
        "context_window": 200000,
        "model_think": True,
        "model_name": "claude-opus-4-7-20260416",
        "active_intention": {"satisfaction_criterion": "réponse complète"},
        "recent_insights": [{"novelty_score": 0.7}],
        "causal_confidence": 0.8,
        "unresolved_tensions": 0,
        "intent_progress": 0.6,
        "domain_competence": 0.85,
        "active_skills_count": 5,
    }


def _empty_call_data() -> dict:
    """Données minimales — presque rien."""
    return {"olam": "briah"}


def _partial_call_data() -> dict:
    """Données partielles — Kavvanah sans intention, Masakh non filtrant."""
    return {
        "olam": "yetzirah",
        "kavvanah": {"anti_pattern": "ne pas résumer"},
        "masakh_log": {
            "was_filtered": False,
            "aviut_level": "bet",
        },
        "reshimo_written": False,
        "token_ratio_logged": True,
        # F4 — pipeline partiel
        "pipeline_steps": ["rosh", "hitlabshut", "toch", "sof"],
        "maturation_stage": "yenikah",
        "tikkun_patterns_count": 0,
    }


# ── Structure ──────────────────────────────────────────────

class TestStructure:

    def test_29_dimensions(self):
        assert len(DIMENSIONS) == 29

    def test_29_auto_measurable(self):
        """v3: 29/29 dimensions auto."""
        assert len(AUTO_IDS) == 29

    def test_0_non_auto(self):
        """v3: 0 dimensions non-auto."""
        non_auto = [d for d in DIMENSIONS if not d["auto"]]
        assert len(non_auto) == 0

    def test_unique_ids(self):
        ids = [d["id"] for d in DIMENSIONS]
        assert len(ids) == len(set(ids))

    def test_ids_sequential(self):
        ids = [d["id"] for d in DIMENSIONS]
        expected = [f"{i:02d}" for i in range(1, 30)]
        assert ids == expected

    def test_auto_ids_correct(self):
        """v3: toutes les 29 dimensions sont auto."""
        expected = {f"{i:02d}" for i in range(1, 30)}
        assert AUTO_IDS == expected


# ── F2: Da'at(08) auto via pipeline_steps ──────────────────

class TestF2DaatDim:

    def test_daat_ok_when_bridge_in_steps(self, monitor):
        """F2: Da'at (08) = ✓ quand 'daat_bridge' dans pipeline_steps."""
        state = monitor.assess(_full_call_data())
        daat = next(d for d in state["dimensions"] if d["id"] == "08")
        assert daat["status"] == STATUS_OK

    def test_daat_absent_without_bridge(self, monitor):
        """F2: Da'at (08) = ✗ quand 'daat_bridge' absent des steps."""
        state = monitor.assess(_empty_call_data())
        daat = next(d for d in state["dimensions"] if d["id"] == "08")
        assert daat["status"] == STATUS_ABSENT

    def test_daat_in_auto_ids(self):
        assert "08" in AUTO_IDS


# ── F4: 5 nouvelles dimensions auto ──────────────────────

class TestF4NewAutoDims:

    def test_hitlabshut_ok_when_in_steps(self, monitor):
        """F4: Dim 19 Hitlabshut = ✓ quand 'hitlabshut' dans pipeline_steps."""
        state = monitor.assess(_full_call_data())
        dim = next(d for d in state["dimensions"] if d["id"] == "19")
        assert dim["status"] == STATUS_OK

    def test_hitlabshut_absent_without_step(self, monitor):
        data = {**_empty_call_data(), "pipeline_steps": ["rosh", "toch"]}
        state = monitor.assess(data)
        dim = next(d for d in state["dimensions"] if d["id"] == "19")
        assert dim["status"] == STATUS_ABSENT

    def test_arakhin_ok_when_in_steps(self, monitor):
        """F4: Dim 20 Arakhin = ✓ quand 'arakhin' dans pipeline_steps."""
        state = monitor.assess(_full_call_data())
        dim = next(d for d in state["dimensions"] if d["id"] == "20")
        assert dim["status"] == STATUS_OK

    def test_arakhin_absent_without_step(self, monitor):
        data = {**_empty_call_data(), "pipeline_steps": ["rosh", "toch"]}
        state = monitor.assess(data)
        dim = next(d for d in state["dimensions"] if d["id"] == "20")
        assert dim["status"] == STATUS_ABSENT

    def test_tzelem_ok_when_in_steps(self, monitor):
        """F4: Dim 21 Tzelem = ✓ quand 'tzelem' dans pipeline_steps."""
        state = monitor.assess(_full_call_data())
        dim = next(d for d in state["dimensions"] if d["id"] == "21")
        assert dim["status"] == STATUS_OK

    def test_tzelem_absent_without_step(self, monitor):
        data = {**_empty_call_data(), "pipeline_steps": ["rosh", "toch"]}
        state = monitor.assess(data)
        dim = next(d for d in state["dimensions"] if d["id"] == "21")
        assert dim["status"] == STATUS_ABSENT

    def test_iym_ok_with_stage(self, monitor):
        """F4: Dim 23 IYM = ✓ quand maturation_stage présent."""
        state = monitor.assess(_full_call_data())
        dim = next(d for d in state["dimensions"] if d["id"] == "23")
        assert dim["status"] == STATUS_OK

    def test_iym_absent_without_stage(self, monitor):
        state = monitor.assess(_empty_call_data())
        dim = next(d for d in state["dimensions"] if d["id"] == "23")
        assert dim["status"] == STATUS_ABSENT

    def test_gilgul_ok_with_patterns(self, monitor):
        """F4: Dim 28 Gilgul = ✓ quand tikkun_patterns_count > 0."""
        state = monitor.assess(_full_call_data())
        dim = next(d for d in state["dimensions"] if d["id"] == "28")
        assert dim["status"] == STATUS_OK

    def test_gilgul_absent_with_zero(self, monitor):
        data = {**_empty_call_data(), "tikkun_patterns_count": 0}
        state = monitor.assess(data)
        dim = next(d for d in state["dimensions"] if d["id"] == "28")
        assert dim["status"] == STATUS_ABSENT

    def test_gilgul_absent_without_count(self, monitor):
        state = monitor.assess(_empty_call_data())
        dim = next(d for d in state["dimensions"] if d["id"] == "28")
        assert dim["status"] == STATUS_ABSENT


# ── F5: Tsimtsum(29) via pressure_regulated ─────────────────

class TestF5Tsimtsum:

    def test_tsimtsum_in_auto_ids(self):
        """F5: Dim 29 est maintenant auto-mesurable."""
        assert "29" in AUTO_IDS

    def test_tsimtsum_ok_when_regulated(self, monitor):
        """F5: Dim 29 = ✓ quand pressure_regulated=True."""
        state = monitor.assess(_full_call_data())
        dim = next(d for d in state["dimensions"] if d["id"] == "29")
        assert dim["status"] == STATUS_OK

    def test_tsimtsum_ok_via_was_filtered(self, monitor):
        """Fix2: Dim 29 = ✓ quand was_filtered=True, même si pressure_regulated=False."""
        data = {**_full_call_data(), "pressure_regulated": False}
        # was_filtered=True dans masakh_log → Tsimtsum effectif
        state = monitor.assess(data)
        dim = next(d for d in state["dimensions"] if d["id"] == "29")
        assert dim["status"] == STATUS_OK

    def test_tsimtsum_absent_when_nothing_filtered(self, monitor):
        """Fix2: Dim 29 = ✗ quand ni pressure ni filtrage."""
        data = {**_full_call_data(), "pressure_regulated": False}
        data["masakh_log"] = {"was_filtered": False, "aviut_level": "bet"}
        state = monitor.assess(data)
        dim = next(d for d in state["dimensions"] if d["id"] == "29")
        assert dim["status"] == STATUS_ABSENT

    def test_tsimtsum_absent_when_missing(self, monitor):
        """F5: Dim 29 = ✗ quand pressure_regulated absent."""
        state = monitor.assess(_empty_call_data())
        dim = next(d for d in state["dimensions"] if d["id"] == "29")
        assert dim["status"] == STATUS_ABSENT


# ── Fix1: Katnut/Gadlut séparée de Masakh ────────────────

class TestFix1KatnutGadlut:

    def test_katnut_gadlut_mochin(self, monitor):
        """Fix1: maturation_stage=mochin → dim 25 = ✓ (Gadlut)."""
        state = monitor.assess(_full_call_data())
        dim = next(d for d in state["dimensions"] if d["id"] == "25")
        assert dim["status"] == STATUS_OK

    def test_katnut_gadlut_yenikah(self, monitor):
        """Fix1: maturation_stage=yenikah → dim 25 = △ (transition)."""
        data = {**_full_call_data(), "maturation_stage": "yenikah"}
        state = monitor.assess(data)
        dim = next(d for d in state["dimensions"] if d["id"] == "25")
        assert dim["status"] == STATUS_PARTIAL

    def test_katnut_gadlut_ibur(self, monitor):
        """Fix1: maturation_stage=ibur → dim 25 = ✗ (Katnut)."""
        data = {**_full_call_data(), "maturation_stage": "ibur"}
        state = monitor.assess(data)
        dim = next(d for d in state["dimensions"] if d["id"] == "25")
        assert dim["status"] == STATUS_ABSENT

    def test_katnut_gadlut_none(self, monitor):
        """Fix1: pas de maturation_stage → dim 25 = ✗."""
        state = monitor.assess(_empty_call_data())
        dim = next(d for d in state["dimensions"] if d["id"] == "25")
        assert dim["status"] == STATUS_ABSENT

    def test_masakh_independent(self, monitor):
        """Fix1: dim 27 (Masakh) reste indépendante de maturation_stage."""
        data = {**_full_call_data(), "maturation_stage": "ibur"}
        state = monitor.assess(data)
        masakh = next(d for d in state["dimensions"] if d["id"] == "27")
        assert masakh["status"] == STATUS_OK  # aviut_level=gimel


# ── Fix3: 4 nouvelles dimensions auto ─────────────────────

class TestFix3NewAutoDims:

    def test_yesod_ok_with_memory(self, monitor):
        """Fix3: Dim 12 = ✓ quand memory_active=True."""
        state = monitor.assess(_full_call_data())
        dim = next(d for d in state["dimensions"] if d["id"] == "12")
        assert dim["status"] == STATUS_OK

    def test_yesod_partial_with_tikkun(self, monitor):
        """Fix3: Dim 12 = △ quand pas de mémoire mais tikkun_patterns > 0."""
        data = {**_empty_call_data(), "tikkun_patterns_count": 2}
        state = monitor.assess(data)
        dim = next(d for d in state["dimensions"] if d["id"] == "12")
        assert dim["status"] == STATUS_PARTIAL

    def test_yesod_absent_without_memory(self, monitor):
        """Fix3: Dim 12 = ✗ sans mémoire ni tikkun."""
        state = monitor.assess(_empty_call_data())
        dim = next(d for d in state["dimensions"] if d["id"] == "12")
        assert dim["status"] == STATUS_ABSENT

    def test_birur_ok_with_rejected(self, monitor):
        """Fix3: Dim 16 = ✓ quand tokens_rejected > 0."""
        state = monitor.assess(_full_call_data())
        dim = next(d for d in state["dimensions"] if d["id"] == "16")
        assert dim["status"] == STATUS_OK

    def test_birur_partial_with_filter(self, monitor):
        """Fix3: Dim 16 = △ quand was_filtered mais 0 tokens rejetés."""
        data = {**_full_call_data()}
        data["masakh_log"] = {"was_filtered": True, "aviut_level": "gimel", "tokens_rejected": 0}
        state = monitor.assess(data)
        dim = next(d for d in state["dimensions"] if d["id"] == "16")
        assert dim["status"] == STATUS_PARTIAL

    def test_birur_absent_without_filter(self, monitor):
        """Fix3: Dim 16 = ✗ sans filtrage."""
        state = monitor.assess(_empty_call_data())
        dim = next(d for d in state["dimensions"] if d["id"] == "16")
        assert dim["status"] == STATUS_ABSENT

    def test_abya_ok_with_valid_world(self, monitor):
        """Fix3: Dim 17 = ✓ quand olam est un des 4 mondes."""
        for world in ("atziluth", "briah", "yetzirah", "assiah"):
            data = {**_empty_call_data(), "olam": world}
            state = monitor.assess(data)
            dim = next(d for d in state["dimensions"] if d["id"] == "17")
            assert dim["status"] == STATUS_OK, f"ABYA should be OK for {world}"

    def test_abya_partial_with_unknown_world(self, monitor):
        """Fix3: Dim 17 = △ quand olam spécifié mais pas un des 4."""
        data = {**_empty_call_data(), "olam": "unknown"}
        state = monitor.assess(data)
        dim = next(d for d in state["dimensions"] if d["id"] == "17")
        assert dim["status"] == STATUS_PARTIAL

    def test_abya_absent_without_olam(self, monitor):
        """Fix3: Dim 17 = ✗ quand pas d'olam."""
        data = {"pipeline_steps": []}
        state = monitor.assess(data)
        dim = next(d for d in state["dimensions"] if d["id"] == "17")
        assert dim["status"] == STATUS_ABSENT

    def test_stade_ok_partzufim(self, monitor):
        """Fix3: Dim 22 = ✓ (Partzufim) avec 9+ étapes pipeline."""
        state = monitor.assess(_full_call_data())
        dim = next(d for d in state["dimensions"] if d["id"] == "22")
        assert dim["status"] == STATUS_OK  # 10 steps in full data

    def test_stade_partial_berudim(self, monitor):
        """Fix3: Dim 22 = △ (Berudim) avec 7-8 étapes."""
        data = {**_empty_call_data(), "pipeline_steps": ["a", "b", "c", "d", "e", "f", "g"]}
        state = monitor.assess(data)
        dim = next(d for d in state["dimensions"] if d["id"] == "22")
        assert dim["status"] == STATUS_PARTIAL

    def test_stade_absent_nekudim(self, monitor):
        """Fix3: Dim 22 = ✗ (Nekudim/Akudim) avec < 7 étapes."""
        state = monitor.assess(_partial_call_data())
        dim = next(d for d in state["dimensions"] if d["id"] == "22")
        assert dim["status"] == STATUS_ABSENT  # 4 steps


# ── Fix4: Score pondéré ───────────────────────────────────

class TestFix4WeightedScore:

    def test_partial_gives_half_credit(self, monitor):
        """Fix4: △ vaut 0.5 dans le score, pas 0."""
        dims = [
            {"id": "1", "name": "a", "status": STATUS_OK},
            {"id": "2", "name": "b", "status": STATUS_PARTIAL},
            {"id": "3", "name": "c", "status": STATUS_ABSENT},
        ]
        # (1 + 0.5) / 3 = 0.5
        assert monitor._compute_score(dims) == 0.5

    def test_all_partial(self, monitor):
        """Fix4: Tout △ → score = 0.5 (pas 0)."""
        dims = [{"id": str(i), "name": "x", "status": STATUS_PARTIAL} for i in range(10)]
        assert monitor._compute_score(dims) == 0.5


# ── assess avec données complètes ─────────────────────────

class TestAssessComplete:

    def test_returns_all_29(self, monitor):
        state = monitor.assess(_full_call_data())
        assert len(state["dimensions"]) == 29

    def test_core_dims_ok(self, monitor):
        """Dims 01,09,13,14,18,25,27 sont OK avec full data."""
        state = monitor.assess(_full_call_data())
        core_ids = {"01", "09", "13", "14", "18", "25", "27"}
        core_dims = [d for d in state["dimensions"] if d["id"] in core_ids]
        assert all(d["status"] == STATUS_OK for d in core_dims)

    def test_f4_dims_ok(self, monitor):
        """F4: Dims 19,20,21,23,28 sont OK avec full data."""
        state = monitor.assess(_full_call_data())
        f4_ids = {"19", "20", "21", "23", "28"}
        f4_dims = [d for d in state["dimensions"] if d["id"] in f4_ids]
        assert all(d["status"] == STATUS_OK for d in f4_dims)

    def test_post_response_dims_absent_without_scores(self, monitor):
        """Les 2 dims post-response (15, 24) sont ABSENT sans scores."""
        state = monitor.assess(_full_call_data())
        zivvug = next(d for d in state["dimensions"] if d["id"] == "15")
        panim = next(d for d in state["dimensions"] if d["id"] == "24")
        assert zivvug["status"] == STATUS_ABSENT
        assert panim["status"] == STATUS_ABSENT

    def test_no_non_auto(self, monitor):
        """v3: 0 dims non-auto — toutes sont mesurées."""
        state = monitor.assess(_full_call_data())
        na_dims = [d for d in state["dimensions"] if d["status"] == STATUS_NA]
        assert len(na_dims) == 0

    def test_score_global_full(self, monitor):
        """27 OK + 2 ABSENT (Zivvug, Panim) = 27/29 (pondéré v3)."""
        state = monitor.assess(_full_call_data())
        assert state["score_global"] == pytest.approx(27 / 29, abs=0.01)

    def test_olam_in_result(self, monitor):
        state = monitor.assess(_full_call_data())
        assert state["olam"] == "briah"

    def test_has_timestamp(self, monitor):
        state = monitor.assess(_full_call_data())
        assert "timestamp" in state
        assert isinstance(state["timestamp"], float)


# ── assess avec données vides ──────────────────────────────

class TestAssessEmpty:

    def test_no_kavvanah(self, monitor):
        state = monitor.assess(_empty_call_data())
        kav = next(d for d in state["dimensions"] if d["id"] == "01")
        assert kav["status"] == STATUS_ABSENT

    def test_daat_is_absent_without_bridge(self, monitor):
        """F2: Da'at is auto → '✗' when daat_bridge not in steps."""
        state = monitor.assess(_empty_call_data())
        daat = next(d for d in state["dimensions"] if d["id"] == "08")
        assert daat["status"] == STATUS_ABSENT

    def test_olam_present(self, monitor):
        state = monitor.assess(_empty_call_data())
        malk = next(d for d in state["dimensions"] if d["id"] == "13")
        assert malk["status"] == STATUS_OK

    def test_score_low(self, monitor):
        state = monitor.assess(_empty_call_data())
        # Malkhut (olam) + ABYA (briah valid) = 2 ✓ → 2/29
        assert state["score_global"] == pytest.approx(2 / 29, abs=0.01)


# ── assess avec données partielles ────────────────────────

class TestAssessPartial:

    def test_kavvanah_partial(self, monitor):
        """Kavvanah sans 'intention' → △."""
        state = monitor.assess(_partial_call_data())
        kav = next(d for d in state["dimensions"] if d["id"] == "01")
        assert kav["status"] == STATUS_PARTIAL

    def test_chesed_gevurah_partial(self, monitor):
        """Masakh actif mais non filtrant → △."""
        state = monitor.assess(_partial_call_data())
        cg = next(d for d in state["dimensions"] if d["id"] == "09")
        assert cg["status"] == STATUS_PARTIAL

    def test_masakh_and_katnut(self, monitor):
        """Fix1: dim 25 (Katnut/Gadlut) séparée de dim 27 (Masakh).
        Partial data: maturation_stage=yenikah → dim 25 = △ (transition).
        aviut_level=bet → dim 27 = ✓ (Masakh calibré)."""
        state = monitor.assess(_partial_call_data())
        katnut = next(d for d in state["dimensions"] if d["id"] == "25")
        masakh = next(d for d in state["dimensions"] if d["id"] == "27")
        assert katnut["status"] == STATUS_PARTIAL  # yenikah = transition
        assert masakh["status"] == STATUS_OK        # aviut_level présent

    def test_token_ratio_logged(self, monitor):
        state = monitor.assess(_partial_call_data())
        makif = next(d for d in state["dimensions"] if d["id"] == "18")
        assert makif["status"] == STATUS_OK

    def test_reshimo_absent(self, monitor):
        state = monitor.assess(_partial_call_data())
        orc = next(d for d in state["dimensions"] if d["id"] == "14")
        assert orc["status"] == STATUS_ABSENT

    def test_f4_partial_pipeline(self, monitor):
        """Pipeline partiel: hitlabshut=✓, arakhin=✗, tzelem=✗."""
        state = monitor.assess(_partial_call_data())
        hit = next(d for d in state["dimensions"] if d["id"] == "19")
        ara = next(d for d in state["dimensions"] if d["id"] == "20")
        tze = next(d for d in state["dimensions"] if d["id"] == "21")
        assert hit["status"] == STATUS_OK
        assert ara["status"] == STATUS_ABSENT
        assert tze["status"] == STATUS_ABSENT

    def test_f4_iym_partial(self, monitor):
        """IYM=✓ (maturation_stage=yenikah)."""
        state = monitor.assess(_partial_call_data())
        iym = next(d for d in state["dimensions"] if d["id"] == "23")
        assert iym["status"] == STATUS_OK

    def test_f4_gilgul_zero(self, monitor):
        """Gilgul=✗ (tikkun_patterns_count=0)."""
        state = monitor.assess(_partial_call_data())
        gilgul = next(d for d in state["dimensions"] if d["id"] == "28")
        assert gilgul["status"] == STATUS_ABSENT

    def test_score_partial(self, monitor):
        """v3 pondéré 29/29: 6 ✓ + 4 △ = 8 / 29 ≈ 0.2759.
        ✓: 13, 17, 18, 19, 23, 27
        △: 01(Kavvanah), 07(Binah via hitlabshut), 09(Chesed/Gevurah), 25(Katnut)."""
        state = monitor.assess(_partial_call_data())
        assert state["score_global"] == pytest.approx(8 / 29, abs=0.01)


# ── Score global edge cases ───────────────────────────────

class TestScoreGlobal:

    def test_all_na_returns_zero(self, monitor):
        """Si aucune dimension applicable → 0.0."""
        score = monitor._compute_score([
            {"id": "x", "name": "x", "status": STATUS_NA}
            for _ in range(29)
        ])
        assert score == 0.0

    def test_mix_ok_absent(self, monitor):
        dims = [
            {"id": "1", "name": "a", "status": STATUS_OK},
            {"id": "2", "name": "b", "status": STATUS_ABSENT},
            {"id": "3", "name": "c", "status": STATUS_NA},
        ]
        # 1 OK / 2 applicable (OK + ABSENT) = 0.5
        assert monitor._compute_score(dims) == 0.5


# ── Panim/Achor (dim 24) ────────────────────────────────

class TestAssessAlignment:

    def test_no_kavvanah(self, monitor):
        score = monitor.assess_alignment(None, "ctx", "resp")
        assert score == 0.0

    def test_no_intention(self, monitor):
        score = monitor.assess_alignment({}, "ctx", "resp")
        assert score == 0.0

    def test_full_alignment(self, monitor):
        kav = {"intention": "analyser structure profonde"}
        ctx = "la structure profonde du texte"
        resp = "analyser cette structure profonde revele"
        score = monitor.assess_alignment(kav, ctx, resp)
        assert score > 0.5

    def test_no_alignment(self, monitor):
        kav = {"intention": "analyser structure"}
        ctx = "bonjour monde"
        resp = "salut"
        score = monitor.assess_alignment(kav, ctx, resp)
        assert score < 0.5

    def test_partial_alignment(self, monitor):
        kav = {"intention": "analyser structure profonde"}
        ctx = "structure du code"
        resp = "resultat inattendu"
        score = monitor.assess_alignment(kav, ctx, resp)
        assert 0.0 < score < 1.0

    def test_alignment_in_assess(self, monitor):
        """Dimension 24 dans assess avec alignment_score."""
        data = {**_full_call_data(), "alignment_score": 0.8}
        state = monitor.assess(data)
        panim = next(d for d in state["dimensions"] if d["id"] == "24")
        assert panim["status"] == STATUS_OK

    def test_alignment_low_in_assess(self, monitor):
        """Alignment < 0.4 → partial."""
        data = {**_full_call_data(), "alignment_score": 0.2}
        state = monitor.assess(data)
        panim = next(d for d in state["dimensions"] if d["id"] == "24")
        assert panim["status"] == STATUS_PARTIAL


# ── Zivvug (dim 15) ─────────────────────────────────────

class TestAssessZivvug:

    def test_no_enrichment(self, monitor):
        score = monitor.assess_zivvug("prompt", "prompt", None)
        assert score == 0.0

    def test_full_enrichment(self, monitor):
        score = monitor.assess_zivvug(
            "simple question",
            "voici une reponse enrichie avec architecture transformation novelty creativity",
            {
                "reshimo_aviut": {"score": 0.8, "was_filtered": True},
                "reshimo_hitlabshut": {"pipeline_steps": ["daat_bridge"]},
            },
        )
        assert score == 1.0

    def test_partial_enrichment(self, monitor):
        score = monitor.assess_zivvug(
            "simple question",
            "voici une reponse enrichie avec architecture transformation novelty creativity",
            {"reshimo_aviut": {"score": 0.4, "was_filtered": False}},
        )
        # Nouveaux concepts (+0.3) mais score bas et pas de filtrage ni daat
        assert score == 0.3

    def test_zivvug_in_assess(self, monitor):
        """Dimension 15 dans assess avec zivvug_score."""
        data = {**_full_call_data(), "zivvug_score": 0.5}
        state = monitor.assess(data)
        zivvug = next(d for d in state["dimensions"] if d["id"] == "15")
        assert zivvug["status"] == STATUS_OK

    def test_zivvug_low_in_assess(self, monitor):
        """Zivvug < 0.3 → partial."""
        data = {**_full_call_data(), "zivvug_score": 0.1}
        state = monitor.assess(data)
        zivvug = next(d for d in state["dimensions"] if d["id"] == "15")
        assert zivvug["status"] == STATUS_PARTIAL


# ── F3: update_post_response ─────────────────────────────

class TestUpdatePostResponse:

    def test_updates_zivvug_ok(self, monitor):
        """Post-response: Zivvug passe de ✗ à ✓ avec enrichissement."""
        state = monitor.assess(_full_call_data())
        # Avant: Zivvug = ✗
        zivvug = next(d for d in state["dimensions"] if d["id"] == "15")
        assert zivvug["status"] == STATUS_ABSENT

        monitor.update_post_response(
            state,
            prompt_final="simple question",
            response="voici une reponse enrichie avec architecture transformation novelty creativity",
            kavvanah={"intention": "analyser la structure"},
        )
        # Après: Zivvug = ✓ (nouveaux concepts = +0.3)
        zivvug = next(d for d in state["dimensions"] if d["id"] == "15")
        assert zivvug["status"] == STATUS_OK

    def test_updates_panim_ok(self, monitor):
        """Post-response: Panim/Achor passe de ✗ à ✓ avec bon alignement."""
        state = monitor.assess(_full_call_data())
        panim = next(d for d in state["dimensions"] if d["id"] == "24")
        assert panim["status"] == STATUS_ABSENT

        monitor.update_post_response(
            state,
            prompt_final="analyser la structure profonde",
            response="la structure profonde revele analyser",
            kavvanah={"intention": "analyser structure profonde"},
        )
        panim = next(d for d in state["dimensions"] if d["id"] == "24")
        assert panim["status"] == STATUS_OK

    def test_updates_panim_partial(self, monitor):
        """Post-response: Panim partial quand alignement < 0.4."""
        state = monitor.assess(_full_call_data())
        monitor.update_post_response(
            state,
            prompt_final="sujet completement different",
            response="structure du monde",
            kavvanah={"intention": "analyser structure profonde"},
        )
        panim = next(d for d in state["dimensions"] if d["id"] == "24")
        assert panim["status"] == STATUS_PARTIAL

    def test_zivvug_absent_no_enrichment(self, monitor):
        """Post-response: Zivvug reste ✗ si pas d'enrichissement."""
        state = monitor.assess(_full_call_data())
        monitor.update_post_response(
            state,
            prompt_final="mot",
            response="mot",
            kavvanah=None,
        )
        zivvug = next(d for d in state["dimensions"] if d["id"] == "15")
        assert zivvug["status"] == STATUS_ABSENT

    def test_score_recalculated(self, monitor):
        """Le score_global est recalculé après update_post_response."""
        state = monitor.assess(_full_call_data())
        score_before = state["score_global"]

        monitor.update_post_response(
            state,
            prompt_final="analyser la structure profonde",
            response="voici une reponse enrichie avec architecture transformation novelty creativity analyser structure profonde",
            kavvanah={"intention": "analyser structure profonde"},
        )
        # Au moins Zivvug et Panim passent de ✗ à ✓/△ → score augmente
        assert state["score_global"] >= score_before

    def test_returns_scores(self, monitor):
        """update_post_response expose alignment_score et zivvug_score."""
        state = monitor.assess(_full_call_data())
        result = monitor.update_post_response(
            state,
            prompt_final="analyser structure",
            response="structure analysee",
            kavvanah={"intention": "analyser structure"},
        )
        assert "alignment_score" in result
        assert "zivvug_score" in result
        assert isinstance(result["alignment_score"], float)
        assert isinstance(result["zivvug_score"], float)

    def test_modifies_in_place(self, monitor):
        """update_post_response modifie le state en place et le retourne."""
        state = monitor.assess(_full_call_data())
        result = monitor.update_post_response(
            state, "prompt", "response", None,
        )
        assert result is state


# ── Full data with all dimensions ──────────────────────────

class TestFullWithAllDims:

    def test_score_perfect_with_all_dims(self, monitor):
        """Toutes les 29 dimensions à OK -> score = 1.0."""
        data = {
            **_full_call_data(),
            "alignment_score": 0.8,
            "zivvug_score": 0.5,
        }
        state = monitor.assess(data)
        assert state["score_global"] == 1.0

    def test_all_29_ok(self, monitor):
        """Chaque dimension auto est OK avec données complètes + tree_signals."""
        data = {
            **_full_call_data(),
            "alignment_score": 0.8,
            "zivvug_score": 0.5,
        }
        state = monitor.assess(data)
        assert len(state["dimensions"]) == 29
        for dim in state["dimensions"]:
            assert dim["status"] == STATUS_OK, f"Dim {dim['id']} {dim['name']} should be OK"
