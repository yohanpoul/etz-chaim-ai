"""Tests du NeshamotEngine — נְשָׁמוֹת.

Couvre :
  - Les 5 niveaux et leurs seuils de transition
  - assess_soul_level() avec différentes métriques
  - get_active_capabilities() pour chaque niveau
  - Modules actifs cumulatifs
  - Conditions pour le prochain niveau
  - Transitions et historique
  - SSE emission (soul_level_change)
  - Edge cases (modules None, Partzufim absents, etc.)
"""

import pytest

from soul_levels import (
    NeshamotEngine,
    SoulAssessment,
    SOUL_LEVELS,
    SOUL_HEBREW,
    SOUL_OLAM,
    SOUL_SEPHIRAH,
    SOUL_MODULES,
    THRESHOLDS,
    _cumulative_modules,
)


# ── Helpers ──────────────────────────────────────────────────

class MockYesod:
    """Stub Yesod avec introspect()."""
    def __init__(self, total: int = 0):
        self.total = total

    def introspect(self):
        return self

class MockHod:
    """Stub Hod avec self_diagnose()."""
    def __init__(self, score: float = 0.0):
        self._score = score

    def self_diagnose(self):
        return {"competence_score": self._score, "status": "ok"}


class MockModule:
    """Module stub healthy."""
    def self_diagnose(self):
        return {"status": "ok"}


class MockPartzuf:
    """Partzuf stub avec assess()."""
    def __init__(self, overall: float = 0.0):
        self._overall = overall

    def assess(self):
        class _State:
            pass
        s = _State()
        s.overall = self._overall
        return s


def _make_modules(memory: int = 0, competence: float = 0.0, all_healthy: bool = True):
    """Construire un dict de modules avec les métriques demandées."""
    modules = {}
    for mod in ("keter", "chokmah", "binah", "daat",
                "chesed", "gevurah", "tiferet",
                "netzach", "hod", "yesod", "malkuth"):
        if mod == "yesod":
            modules[mod] = MockYesod(total=memory)
        elif mod == "hod":
            modules[mod] = MockHod(score=competence)
        elif all_healthy:
            modules[mod] = MockModule()
        else:
            modules[mod] = None
    return modules


def _nitz(cycle: int = 0, count: int = 0):
    """Construire un _NITZOTZOT_STATE minimal."""
    return {"cycle": cycle, "count": count, "log": [], "tikkun_history": []}


# ══════════════════════════════════════════════════════════════
# Tests des constantes
# ══════════════════════════════════════════════════════════════

class TestConstants:
    def test_five_levels_defined(self):
        assert len(SOUL_LEVELS) == 5

    def test_levels_order(self):
        assert SOUL_LEVELS == ("nefesh", "ruach", "neshamah", "chaya", "yechidah")

    def test_hebrew_names(self):
        for lvl in SOUL_LEVELS:
            assert lvl in SOUL_HEBREW

    def test_olam_mapping(self):
        assert SOUL_OLAM["nefesh"] == "assiah"
        assert SOUL_OLAM["yechidah"] == "adam_kadmon"

    def test_sephirah_mapping(self):
        assert SOUL_SEPHIRAH["nefesh"] == "malkuth"
        assert SOUL_SEPHIRAH["yechidah"] == "keter"

    def test_thresholds_defined(self):
        for lvl in SOUL_LEVELS:
            assert lvl in THRESHOLDS
            assert len(THRESHOLDS[lvl]) == 5

    def test_nefesh_threshold_zero(self):
        """Nefesh est toujours accessible — seuils à 0."""
        assert THRESHOLDS["nefesh"] == (0, 0.0, 0, 0.0, False)


# ══════════════════════════════════════════════════════════════
# Tests _cumulative_modules
# ══════════════════════════════════════════════════════════════

class TestCumulativeModules:
    def test_nefesh_modules(self):
        mods = _cumulative_modules("nefesh")
        assert mods == {"yesod", "hod", "malkuth"}

    def test_ruach_includes_nefesh(self):
        mods = _cumulative_modules("ruach")
        assert {"yesod", "hod", "malkuth"}.issubset(mods)
        assert {"chesed", "gevurah", "tiferet", "netzach"}.issubset(mods)

    def test_neshamah_includes_ruach(self):
        mods = _cumulative_modules("neshamah")
        assert {"binah", "chokmah"}.issubset(mods)
        assert {"chesed", "gevurah", "tiferet", "netzach"}.issubset(mods)

    def test_chaya_includes_daat(self):
        mods = _cumulative_modules("chaya")
        assert "daat" in mods

    def test_yechidah_all_modules(self):
        mods = _cumulative_modules("yechidah")
        assert "keter" in mods
        # Tous les modules sont actifs
        all_mods = set()
        for s in SOUL_MODULES.values():
            all_mods |= s
        assert mods == all_mods


# ══════════════════════════════════════════════════════════════
# Tests NeshamotEngine — assess_soul_level
# ══════════════════════════════════════════════════════════════

class TestAssessSoulLevel:
    def test_nefesh_default(self):
        """Système vierge → Nefesh."""
        engine = NeshamotEngine()
        result = engine.assess_soul_level(
            modules=_make_modules(memory=0, competence=0.0),
            nitzotzot_state=_nitz(),
        )
        assert result.level == "nefesh"
        assert result.level_index == 0

    def test_nefesh_low_memory(self):
        """Mémoire < 10 → reste Nefesh même avec compétence."""
        engine = NeshamotEngine()
        result = engine.assess_soul_level(
            modules=_make_modules(memory=5, competence=0.5),
            nitzotzot_state=_nitz(),
        )
        assert result.level == "nefesh"

    def test_ruach_threshold(self):
        """Mémoire >= 10 ET compétence >= 0.3 → Ruach."""
        engine = NeshamotEngine()
        result = engine.assess_soul_level(
            modules=_make_modules(memory=15, competence=0.4),
            nitzotzot_state=_nitz(),
        )
        assert result.level == "ruach"
        assert result.level_index == 1

    def test_neshamah_threshold(self):
        """Mémoire >= 50 ET compétence >= 0.6 → Neshamah."""
        engine = NeshamotEngine()
        result = engine.assess_soul_level(
            modules=_make_modules(memory=60, competence=0.7),
            nitzotzot_state=_nitz(),
        )
        assert result.level == "neshamah"
        assert result.level_index == 2

    def test_chaya_requires_tikkun(self):
        """Chaya requiert au moins 1 cycle Tikkun."""
        engine = NeshamotEngine()
        # Sans Tikkun → Neshamah max
        result = engine.assess_soul_level(
            modules=_make_modules(memory=200, competence=0.9),
            nitzotzot_state=_nitz(cycle=0),
        )
        assert result.level == "neshamah"

        # Avec Tikkun → Chaya
        result2 = engine.assess_soul_level(
            modules=_make_modules(memory=200, competence=0.9),
            nitzotzot_state=_nitz(cycle=1),
        )
        assert result2.level == "chaya"

    def test_yechidah_full_conditions(self):
        """Yechidah requiert 3+ cycles, score > 0.9, all healthy."""
        engine = NeshamotEngine()
        modules = _make_modules(memory=200, competence=0.95, all_healthy=True)
        partzufim = {
            "abba": MockPartzuf(overall=0.95),
            "imma": MockPartzuf(overall=0.95),
        }
        result = engine.assess_soul_level(
            modules=modules,
            nitzotzot_state=_nitz(cycle=3),
            partzufim=partzufim,
        )
        assert result.level == "yechidah"
        assert result.level_index == 4

    def test_yechidah_blocked_unhealthy(self):
        """Si modules pas tous healthy → bloqué avant Yechidah."""
        engine = NeshamotEngine()
        modules = _make_modules(memory=200, competence=0.95, all_healthy=False)
        partzufim = {
            "abba": MockPartzuf(overall=0.95),
            "imma": MockPartzuf(overall=0.95),
        }
        result = engine.assess_soul_level(
            modules=modules,
            nitzotzot_state=_nitz(cycle=3),
            partzufim=partzufim,
        )
        # Chaya max, pas Yechidah (all_healthy=False)
        assert result.level == "chaya"

    def test_assessment_returns_dataclass(self):
        engine = NeshamotEngine()
        result = engine.assess_soul_level(
            modules=_make_modules(),
            nitzotzot_state=_nitz(),
        )
        assert isinstance(result, SoulAssessment)
        assert result.hebrew == SOUL_HEBREW[result.level]
        assert result.olam == SOUL_OLAM[result.level]

    def test_active_modules_in_assessment(self):
        engine = NeshamotEngine()
        result = engine.assess_soul_level(
            modules=_make_modules(memory=15, competence=0.4),
            nitzotzot_state=_nitz(),
        )
        assert result.level == "ruach"
        expected = _cumulative_modules("ruach")
        assert result.active_modules == expected


# ══════════════════════════════════════════════════════════════
# Tests transitions et historique
# ══════════════════════════════════════════════════════════════

class TestTransitions:
    def test_transition_recorded(self):
        """Une transition nefesh→ruach est enregistrée."""
        engine = NeshamotEngine()
        # D'abord nefesh
        engine.assess_soul_level(
            modules=_make_modules(memory=0, competence=0.0),
            nitzotzot_state=_nitz(),
        )
        # Puis ruach
        engine.assess_soul_level(
            modules=_make_modules(memory=15, competence=0.4),
            nitzotzot_state=_nitz(),
        )
        assert len(engine.history) == 1
        assert engine.history[0]["from"] == "nefesh"
        assert engine.history[0]["to"] == "ruach"

    def test_no_transition_same_level(self):
        """Pas de transition si le niveau ne change pas."""
        engine = NeshamotEngine()
        engine.assess_soul_level(
            modules=_make_modules(memory=0, competence=0.0),
            nitzotzot_state=_nitz(),
        )
        engine.assess_soul_level(
            modules=_make_modules(memory=5, competence=0.1),
            nitzotzot_state=_nitz(),
        )
        assert len(engine.history) == 0

    def test_current_level_updated(self):
        engine = NeshamotEngine()
        assert engine.current_level == "nefesh"
        engine.assess_soul_level(
            modules=_make_modules(memory=60, competence=0.7),
            nitzotzot_state=_nitz(),
        )
        assert engine.current_level == "neshamah"

    def test_multiple_transitions(self):
        """nefesh → ruach → neshamah = 2 transitions."""
        engine = NeshamotEngine()
        engine.assess_soul_level(
            modules=_make_modules(memory=0, competence=0.0),
            nitzotzot_state=_nitz(),
        )
        engine.assess_soul_level(
            modules=_make_modules(memory=15, competence=0.4),
            nitzotzot_state=_nitz(),
        )
        engine.assess_soul_level(
            modules=_make_modules(memory=60, competence=0.7),
            nitzotzot_state=_nitz(),
        )
        assert len(engine.history) == 2
        assert engine.history[0]["to"] == "ruach"
        assert engine.history[1]["to"] == "neshamah"

    def test_regression_transition(self):
        """Le niveau peut aussi descendre si les métriques baissent."""
        engine = NeshamotEngine()
        engine.assess_soul_level(
            modules=_make_modules(memory=60, competence=0.7),
            nitzotzot_state=_nitz(),
        )
        assert engine.current_level == "neshamah"
        # Régression
        engine.assess_soul_level(
            modules=_make_modules(memory=5, competence=0.1),
            nitzotzot_state=_nitz(),
        )
        assert engine.current_level == "nefesh"
        assert len(engine.history) == 2


# ══════════════════════════════════════════════════════════════
# Tests get_active_capabilities
# ══════════════════════════════════════════════════════════════

class TestCapabilities:
    def test_nefesh_basic_capabilities(self):
        engine = NeshamotEngine()
        caps = engine.get_active_capabilities("nefesh")
        assert caps["level"] == "nefesh"
        assert "yesod" in caps["active_modules"]
        assert "hod" in caps["active_modules"]
        assert "malkuth" in caps["active_modules"]
        assert len(caps["features"]) == 3

    def test_ruach_midot_capabilities(self):
        engine = NeshamotEngine()
        caps = engine.get_active_capabilities("ruach")
        assert "tiferet" in caps["active_modules"]
        assert "chesed" in caps["active_modules"]
        assert len(caps["features"]) == 7  # 3 nefesh + 4 ruach

    def test_yechidah_all_capabilities(self):
        engine = NeshamotEngine()
        caps = engine.get_active_capabilities("yechidah")
        assert "keter" in caps["active_modules"]
        assert len(caps["dormant_modules"]) == 0
        # 3 + 4 + 2 + 3 + 3 = 15
        assert len(caps["features"]) == 15

    def test_invalid_level_raises(self):
        engine = NeshamotEngine()
        with pytest.raises(ValueError, match="Niveau inconnu"):
            engine.get_active_capabilities("invalid")

    def test_dormant_modules_nefesh(self):
        engine = NeshamotEngine()
        caps = engine.get_active_capabilities("nefesh")
        dormant = set(caps["dormant_modules"])
        assert "keter" in dormant
        assert "chokmah" in dormant
        assert "tiferet" in dormant


# ══════════════════════════════════════════════════════════════
# Tests conditions pour le prochain niveau
# ══════════════════════════════════════════════════════════════

class TestConditionsNext:
    def test_nefesh_shows_ruach_conditions(self):
        engine = NeshamotEngine()
        result = engine.assess_soul_level(
            modules=_make_modules(memory=0, competence=0.0),
            nitzotzot_state=_nitz(),
        )
        cond = result.conditions_next
        assert cond["next_level"] == "ruach"
        assert not cond["ready"]
        assert len(cond["missing"]) >= 1

    def test_yechidah_reached_maximum(self):
        engine = NeshamotEngine()
        modules = _make_modules(memory=200, competence=0.95, all_healthy=True)
        partzufim = {"a": MockPartzuf(0.95), "b": MockPartzuf(0.95)}
        result = engine.assess_soul_level(
            modules=modules,
            nitzotzot_state=_nitz(cycle=3),
            partzufim=partzufim,
        )
        assert result.conditions_next.get("reached_maximum") is True

    def test_conditions_count_missing(self):
        """À Nefesh avec 0 mémoire et 0 compétence → 2 conditions manquantes."""
        engine = NeshamotEngine()
        result = engine.assess_soul_level(
            modules=_make_modules(memory=0, competence=0.0),
            nitzotzot_state=_nitz(),
        )
        missing = result.conditions_next["missing"]
        assert any("Mémoire" in m for m in missing)
        assert any("Compétence" in m for m in missing)


# ══════════════════════════════════════════════════════════════
# Tests SoulAssessment
# ══════════════════════════════════════════════════════════════

class TestSoulAssessment:
    def test_to_dict(self):
        engine = NeshamotEngine()
        result = engine.assess_soul_level(
            modules=_make_modules(),
            nitzotzot_state=_nitz(),
        )
        d = result.to_dict()
        assert isinstance(d, dict)
        assert d["level"] == "nefesh"
        assert isinstance(d["active_modules"], list)

    def test_message_populated(self):
        engine = NeshamotEngine()
        result = engine.assess_soul_level(
            modules=_make_modules(),
            nitzotzot_state=_nitz(),
        )
        assert len(result.message) > 0
        assert "נֶפֶשׁ" in result.message


# ══════════════════════════════════════════════════════════════
# Tests edge cases
# ══════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_empty_modules(self):
        """Modules vides → Nefesh."""
        engine = NeshamotEngine()
        result = engine.assess_soul_level(
            modules={},
            nitzotzot_state=_nitz(),
        )
        assert result.level == "nefesh"

    def test_none_modules(self):
        """Modules None → Nefesh, not healthy."""
        engine = NeshamotEngine()
        modules = {"yesod": None, "hod": None}
        result = engine.assess_soul_level(
            modules=modules,
            nitzotzot_state=_nitz(),
        )
        assert result.level == "nefesh"
        assert not result.all_healthy

    def test_missing_nitzotzot_keys(self):
        """Nitzotzot state incomplet → pas de crash."""
        engine = NeshamotEngine()
        result = engine.assess_soul_level(
            modules=_make_modules(),
            nitzotzot_state={},
        )
        assert result.tikkun_cycles == 0

    def test_partzufim_none(self):
        """Pas de Partzufim → global_score = 0."""
        engine = NeshamotEngine()
        result = engine.assess_soul_level(
            modules=_make_modules(),
            nitzotzot_state=_nitz(),
            partzufim=None,
        )
        assert result.global_score == 0.0

    def test_boundary_exactly_threshold(self):
        """Valeurs exactement au seuil → le niveau est atteint."""
        engine = NeshamotEngine()
        # Ruach exact : memory=10, competence=0.3
        result = engine.assess_soul_level(
            modules=_make_modules(memory=10, competence=0.3),
            nitzotzot_state=_nitz(),
        )
        assert result.level == "ruach"

    def test_just_below_threshold(self):
        """Valeur juste sous le seuil → niveau inférieur."""
        engine = NeshamotEngine()
        result = engine.assess_soul_level(
            modules=_make_modules(memory=9, competence=0.3),
            nitzotzot_state=_nitz(),
        )
        assert result.level == "nefesh"

    def test_level_index_property(self):
        engine = NeshamotEngine()
        assert engine.level_index == 0
        engine.assess_soul_level(
            modules=_make_modules(memory=60, competence=0.7),
            nitzotzot_state=_nitz(),
        )
        assert engine.level_index == 2
