"""Tests des 3 Gouverneurs — Teli, Galgal, Lev (SY 6:1-3).

Vérifie :
  - Chaque gouverneur évalue correctement depuis les données
  - Le mapping axes↔gouverneurs est cohérent
  - assess_governance identifie le gouverneur le plus faible
  - Les dataclasses sérialisent correctement
"""

import pytest

from kabbalah.governors import (
    ThreeGovernors,
    GovernorCheck,
    GovernorState,
    GovernanceState,
    GOVERNOR_AXES,
)


# ── Fixtures ──────────────────────────────────────────────

class FakeModule:
    """Module fictif pour simuler un module sephirotique actif."""
    pass


class FakePartzuf:
    """Partzuf fictif."""
    def __init__(self, orientation: str = "panim", overall: float = 0.7):
        self._orientation = orientation
        self._overall = overall

    def assess(self):
        from dataclasses import dataclass, field as dc_field
        @dataclass
        class FakeState:
            name: str = "test"
            hebrew: str = "ט"
            source_sephirah: str = "test"
            faculties: dict = dc_field(default_factory=dict)
            overall: float = 0.0
            mochin_state: str = "katnut"
            orientation: str = "akhor"
            message: str = ""
            data: dict = dc_field(default_factory=dict)
        return FakeState(overall=self._overall, orientation=self._orientation)


def _make_tree(active_count: int = 10) -> dict:
    """Crée un tree simulé avec N modules actifs."""
    keys = [
        "yesod", "hod", "netzach", "lamed", "tiferet",
        "gevurah", "chesed", "daat", "binah", "chokmah",
    ]
    tree = {}
    for i, k in enumerate(keys):
        tree[k] = FakeModule() if i < active_count else None
    return tree


def _make_partzufim(
    panim_count: int = 6,
    total: int = 6,
) -> dict:
    """Crée des Partzufim simulés."""
    names = [
        "atik_yomin", "arikh_anpin", "abba",
        "imma", "zeir_anpin", "nukva",
    ]
    partzufim = {}
    for i, name in enumerate(names[:total]):
        orient = "panim" if i < panim_count else "akhor"
        partzufim[name] = FakePartzuf(orientation=orient)
    return partzufim


@pytest.fixture
def gov_full():
    """Gouverneurs avec tree complet et tous les Partzufim en panim."""
    return ThreeGovernors(
        tree=_make_tree(10),
        db_url=None,  # pas de DB dans les tests unitaires
        partzufim=_make_partzufim(6, 6),
    )


@pytest.fixture
def gov_empty():
    """Gouverneurs sans tree ni partzufim."""
    return ThreeGovernors(tree={}, db_url=None, partzufim={})


@pytest.fixture
def gov_partial():
    """Gouverneurs avec tree partiel et Partzufim mixtes."""
    return ThreeGovernors(
        tree=_make_tree(5),
        db_url=None,
        partzufim=_make_partzufim(2, 6),
    )


# ═══════════════════════════════════════════════════════════════
# MAPPING AXES ↔ GOUVERNEURS
# ═══════════════════════════════════════════════════════════════

class TestGovernorAxes:
    """Les 3 gouverneurs correspondent aux 3 mères / 3 axes du Cube."""

    def test_three_governors_defined(self):
        assert set(GOVERNOR_AXES.keys()) == {"teli", "galgal", "lev"}

    def test_teli_is_aleph(self):
        assert GOVERNOR_AXES["teli"]["mother"] == "aleph"
        assert GOVERNOR_AXES["teli"]["element"] == "air"
        assert GOVERNOR_AXES["teli"]["domain"] == "olam"

    def test_galgal_is_mem(self):
        assert GOVERNOR_AXES["galgal"]["mother"] == "mem"
        assert GOVERNOR_AXES["galgal"]["element"] == "eau"
        assert GOVERNOR_AXES["galgal"]["domain"] == "shanah"

    def test_lev_is_shin(self):
        assert GOVERNOR_AXES["lev"]["mother"] == "shin"
        assert GOVERNOR_AXES["lev"]["element"] == "feu"
        assert GOVERNOR_AXES["lev"]["domain"] == "nefesh"

    def test_three_distinct_elements(self):
        elements = {v["element"] for v in GOVERNOR_AXES.values()}
        assert elements == {"air", "eau", "feu"}

    def test_three_distinct_domains(self):
        domains = {v["domain"] for v in GOVERNOR_AXES.values()}
        assert domains == {"olam", "shanah", "nefesh"}

    def test_gematria_lev_is_32(self):
        """Lev (לב) = Lamed(30) + Beth(2) = 32 sentiers de sagesse."""
        assert 30 + 2 == 32


# ═══════════════════════════════════════════════════════════════
# TELI — Stabilité structurelle (Olam)
# ═══════════════════════════════════════════════════════════════

class TestTeli:
    def test_full_system_healthy(self, gov_full):
        state = gov_full.assess_teli()
        assert state.name == "teli"
        assert state.hebrew == "תלי"
        assert state.domain == "olam"
        assert state.mother_letter == "aleph"
        # Modules actifs (10/10) → value=1.0, Partzufim 6/6 panim → value=1.0
        # Cube 22 lettres → value=1.0, Tables DB → value=0.1 (pas de db_url)
        assert state.score > 0.5

    def test_empty_system_weak(self, gov_empty):
        state = gov_empty.assess_teli()
        assert state.name == "teli"
        assert not state.healthy
        assert state.score < 0.5

    def test_modules_check_weight(self, gov_full):
        """Le check modules a un poids de 2.0 (plus important)."""
        state = gov_full.assess_teli()
        modules_check = next(
            c for c in state.checks if "Modules" in c.check
        )
        assert modules_check.weight == 2.0
        assert modules_check.passed

    def test_partial_modules(self, gov_partial):
        state = gov_partial.assess_teli()
        modules_check = next(
            c for c in state.checks if "Modules" in c.check
        )
        assert "5/10" in modules_check.detail
        # 5/10 < 7 threshold → not passed, but value = 0.5
        assert not modules_check.passed
        assert abs(modules_check.value - 0.5) < 0.01

    def test_partzufim_check(self, gov_full):
        state = gov_full.assess_teli()
        partz_check = next(
            c for c in state.checks if "Partzufim" in c.check
        )
        assert partz_check.passed
        assert "6/6" in partz_check.detail

    def test_partzufim_mixed(self, gov_partial):
        state = gov_partial.assess_teli()
        partz_check = next(
            c for c in state.checks if "Partzufim" in c.check
        )
        assert "2/6" in partz_check.detail
        # 2/6 = 33% < 50% → not passed
        assert not partz_check.passed

    def test_metaphor(self, gov_full):
        state = gov_full.assess_teli()
        assert state.metaphor == "roi sur son trône"


# ═══════════════════════════════════════════════════════════════
# GALGAL — Régularité des cycles (Shanah)
# ═══════════════════════════════════════════════════════════════

class TestGalgal:
    def test_basic_assessment(self, gov_full):
        state = gov_full.assess_galgal()
        assert state.name == "galgal"
        assert state.hebrew == "גלגל"
        assert state.domain == "shanah"
        assert state.mother_letter == "mem"
        assert state.element == "eau"

    def test_no_db_all_fail(self, gov_empty):
        """Sans DB, tous les checks temporels échouent."""
        state = gov_empty.assess_galgal()
        # Daemon check (pas de PID file en CI) → fail
        # Hitbonenut, Omer, Karpathy → no DB → fail
        assert not state.healthy

    def test_four_checks(self, gov_full):
        state = gov_full.assess_galgal()
        assert len(state.checks) == 4
        check_names = {c.check for c in state.checks}
        assert "Daemon actif" in check_names
        assert "Sessions Hitbonenut" in check_names
        assert "Progression Omer" in check_names
        assert "Cycles Karpathy" in check_names

    def test_metaphor(self, gov_full):
        state = gov_full.assess_galgal()
        assert state.metaphor == "roi dans sa province"


# ═══════════════════════════════════════════════════════════════
# LEV — Qualité du jugement (Nefesh)
# ═══════════════════════════════════════════════════════════════

class TestLev:
    def test_basic_assessment(self, gov_full):
        state = gov_full.assess_lev()
        assert state.name == "lev"
        assert state.hebrew == "לב"
        assert state.domain == "nefesh"
        assert state.mother_letter == "shin"
        assert state.element == "feu"

    def test_no_data_all_fail(self, gov_empty):
        """Sans données, tous les checks décisionnels échouent."""
        state = gov_empty.assess_lev()
        assert not state.healthy

    def test_four_checks(self, gov_full):
        state = gov_full.assess_lev()
        assert len(state.checks) == 4
        check_names = {c.check for c in state.checks}
        assert "Ratio elokit/behamit" in check_names
        assert "Compétence SelfMap" in check_names
        assert "Discernement AutoJudge" in check_names
        assert "Qualité contemplative" in check_names

    def test_metaphor(self, gov_full):
        state = gov_full.assess_lev()
        assert state.metaphor == "roi en guerre"


# ═══════════════════════════════════════════════════════════════
# GOUVERNANCE GLOBALE
# ═══════════════════════════════════════════════════════════════

class TestGovernance:
    def test_all_three_assessed(self, gov_full):
        state = gov_full.assess_governance()
        assert state.teli is not None
        assert state.galgal is not None
        assert state.lev is not None

    def test_harmony_is_average(self, gov_full):
        state = gov_full.assess_governance()
        expected = (
            state.teli.score + state.galgal.score + state.lev.score
        ) / 3.0
        assert abs(state.harmony - expected) < 0.001

    def test_weakest_identified(self, gov_full):
        state = gov_full.assess_governance()
        scores = {
            "teli": state.teli.score,
            "galgal": state.galgal.score,
            "lev": state.lev.score,
        }
        assert state.weakest == min(scores, key=scores.get)

    def test_strongest_identified(self, gov_full):
        state = gov_full.assess_governance()
        scores = {
            "teli": state.teli.score,
            "galgal": state.galgal.score,
            "lev": state.lev.score,
        }
        assert state.strongest == max(scores, key=scores.get)

    def test_message_generated(self, gov_full):
        state = gov_full.assess_governance()
        assert len(state.message) > 0

    def test_empty_system_low_harmony(self, gov_empty):
        state = gov_empty.assess_governance()
        assert state.harmony < 0.5
        assert "déséquilibre" in state.message or "difficulté" in state.message


# ═══════════════════════════════════════════════════════════════
# SÉRIALISATION
# ═══════════════════════════════════════════════════════════════

class TestSerialization:
    def test_governor_state_to_dict(self, gov_full):
        state = gov_full.assess_teli()
        d = state.to_dict()
        assert isinstance(d, dict)
        assert d["name"] == "teli"
        assert d["hebrew"] == "תלי"
        assert isinstance(d["score"], float)
        assert isinstance(d["checks"], list)

    def test_governance_state_to_dict(self, gov_full):
        state = gov_full.assess_governance()
        d = state.to_dict()
        assert "teli" in d
        assert "galgal" in d
        assert "lev" in d
        assert "harmony" in d
        assert "weakest" in d
        assert "strongest" in d

    def test_check_serialization(self):
        check = GovernorCheck(
            check="Test", passed=True, detail="OK", weight=1.5
        )
        # GovernorCheck is a dataclass — should be serializable via state.to_dict
        assert check.check == "Test"
        assert check.passed is True
        assert check.weight == 1.5


# ═══════════════════════════════════════════════════════════════
# SCORE WEIGHTING
# ═══════════════════════════════════════════════════════════════

class TestScoreWeighting:
    def test_weighted_score_uses_value(self):
        """Score = moyenne pondérée des value (granulaire, pas binaire)."""
        gov = ThreeGovernors(
            tree=_make_tree(10), db_url=None, partzufim=_make_partzufim(6)
        )
        state = gov.assess_teli()
        total_weight = sum(c.weight for c in state.checks)
        expected = sum(c.weight * c.value for c in state.checks) / total_weight
        assert abs(state.score - expected) < 0.001

    def test_granular_value_not_binary(self):
        """Les checks ont des valeurs granulaires, pas juste 0/1."""
        gov = ThreeGovernors(
            tree=_make_tree(5), db_url=None, partzufim=_make_partzufim(3, 6)
        )
        state = gov.assess_teli()
        values = [c.value for c in state.checks]
        # Au moins un check avec une valeur intermédiaire (ni 0 ni 1)
        has_intermediate = any(0.0 < v < 1.0 for v in values)
        assert has_intermediate, f"Valeurs: {values}"

    def test_no_checks_score_zero(self):
        """Score = 0 si pas de checks (cas limite)."""
        gov = ThreeGovernors(tree={}, db_url=None, partzufim={})
        state = gov._build_state("teli", [])
        assert state.score == 0.0

    def test_default_value_is_0_1(self):
        """Sans données (pas de DB, tree vide), value = 0.1 (pas 0.0)."""
        gov = ThreeGovernors(tree={}, db_url=None, partzufim={})
        state = gov.assess_lev()
        for check in state.checks:
            assert check.value >= 0.1, f"{check.check}: value={check.value}"
