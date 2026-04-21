"""Tests du PartzufimRegulator — variateur analogique des Partzufim.

Couvre :
  - compute_modifiers pour chaque état (gadlut/katnut × panim/akhor)
  - Force katnut si score < 0.4
  - Bonus capacity si score > 0.85
  - Hystérésis : katnut à 0.4, gadlut à 0.6
  - Cascade Atik → tous dégradés
  - Cascade Imma katnut → ZA katnut
  - apply_to_tree modifie les attributs
  - Interaction Tzimtzum + Partzufim
  - Interaction Omer + Partzufim
  - Fallback si DB indisponible
  - check_transitions
"""

import pytest
from unittest.mock import patch, MagicMock

from partzufim.regulator import (
    PartzufimRegulator,
    ModifierProfile,
    MODULE_TUNABLE_ATTRS,
    KATNUT_THRESHOLD,
    GADLUT_THRESHOLD,
    HIGH_SCORE_BONUS,
    ATIK_CASCADE_THRESHOLD,
    PARTZUF_TO_MODULES,
)


# ── Helpers ──────────────────────────────────────────────────

def _make_state(overrides: dict | None = None) -> dict:
    """Crée un état de 6 Partzufim avec valeurs par défaut (gadlut/panim)."""
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


class StubModule:
    """Module simulé avec attributs modulables."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


# ── Tests compute_modifiers ─────────────────────────────────

class TestComputeModifiers:

    def test_gadlut_panim_full_capacity(self):
        """Gadlut + panim → capacity 1.0, threshold 0.0, feedback True."""
        reg = PartzufimRegulator()
        state = _make_state()
        mods = reg.compute_modifiers(state)

        # Abba → chokmah
        assert mods["chokmah"].capacity_factor == 1.0
        assert mods["chokmah"].threshold_modifier == 0.0
        assert mods["chokmah"].budget_factor == 1.0
        assert mods["chokmah"].feedback_enabled is True

    def test_katnut_panim_reduced_capacity(self):
        """Katnut + panim → capacity 0.5, threshold +0.1."""
        reg = PartzufimRegulator()
        state = _make_state({"abba": {"mochin_state": "katnut", "overall": 0.35}})
        mods = reg.compute_modifiers(state)

        assert mods["chokmah"].capacity_factor == 0.5
        assert mods["chokmah"].threshold_modifier == 0.1
        assert mods["chokmah"].budget_factor == 0.5
        assert mods["chokmah"].feedback_enabled is True

    def test_gadlut_akhor_feedback_disabled(self):
        """Gadlut + akhor → feedback disabled, capacity 0.8."""
        reg = PartzufimRegulator()
        state = _make_state({"imma": {"orientation": "akhor"}})
        mods = reg.compute_modifiers(state)

        assert mods["binah"].capacity_factor == 0.8
        assert mods["binah"].feedback_enabled is False

    def test_katnut_akhor_minimal(self):
        """Katnut + akhor → capacity 0.3, threshold +0.15, no feedback."""
        reg = PartzufimRegulator()
        state = _make_state({
            "nukva": {"mochin_state": "katnut", "orientation": "akhor", "overall": 0.3},
        })
        mods = reg.compute_modifiers(state)

        assert mods["malkuth"].capacity_factor == 0.3
        assert mods["malkuth"].threshold_modifier == 0.15
        assert mods["malkuth"].budget_factor == 0.3
        assert mods["malkuth"].feedback_enabled is False

    def test_score_below_04_forces_katnut(self):
        """Score < 0.4 → force katnut même si flag dit gadlut."""
        reg = PartzufimRegulator()
        state = _make_state({"abba": {"overall": 0.35, "mochin_state": "gadlut"}})
        mods = reg.compute_modifiers(state)

        # Devrait être katnut + panim = capacity 0.5
        assert mods["chokmah"].capacity_factor == 0.5
        assert mods["chokmah"].threshold_modifier == 0.1

    def test_score_above_085_bonus_capacity(self):
        """Score > 0.85 en gadlut → bonus capacity +10%."""
        reg = PartzufimRegulator()
        state = _make_state({"abba": {"overall": 0.90, "mochin_state": "gadlut"}})
        mods = reg.compute_modifiers(state)

        assert mods["chokmah"].capacity_factor == pytest.approx(1.1, abs=0.01)
        assert mods["chokmah"].budget_factor == pytest.approx(1.1, abs=0.01)

    def test_all_modules_covered(self):
        """Tous les modules régulés par un Partzuf ont un modifier."""
        reg = PartzufimRegulator()
        state = _make_state()
        mods = reg.compute_modifiers(state)

        for partzuf, modules in PARTZUF_TO_MODULES.items():
            for mk in modules:
                assert mk in mods, f"Module {mk} (Partzuf {partzuf}) manquant"


# ── Tests hystérésis ────────────────────────────────────────

class TestHysteresis:

    def test_katnut_threshold_04(self):
        """Score < 0.4 → should_force_katnut True."""
        reg = PartzufimRegulator()
        state = _make_state({"abba": {"overall": 0.39}})
        assert reg.should_force_katnut("abba", state) is True

    def test_score_between_04_06_no_gadlut(self):
        """Score entre 0.4 et 0.6 → pas de retour en gadlut."""
        reg = PartzufimRegulator()
        state = _make_state({"abba": {"overall": 0.55, "mochin_state": "katnut"}})
        assert reg.can_return_to_gadlut("abba", state) is False

    def test_score_above_06_allows_gadlut(self):
        """Score >= 0.6 → retour en gadlut autorisé."""
        reg = PartzufimRegulator()
        state = _make_state({"abba": {"overall": 0.65, "mochin_state": "katnut"}})
        assert reg.can_return_to_gadlut("abba", state) is True

    def test_already_gadlut_no_return(self):
        """Déjà en gadlut → can_return_to_gadlut False."""
        reg = PartzufimRegulator()
        state = _make_state({"abba": {"overall": 0.80, "mochin_state": "gadlut"}})
        assert reg.can_return_to_gadlut("abba", state) is False


# ── Tests cascades ──────────────────────────────────────────

class TestCascades:

    def test_atik_degraded_cascades_all(self):
        """Atik score < 0.5 → tous les Partzufim dégradés."""
        reg = PartzufimRegulator()
        state = _make_state({"atik_yomin": {"overall": 0.45}})
        mods = reg.compute_modifiers(state)

        # Tous les modules non-atik doivent être en katnut forcé
        for mk in ("chokmah", "binah", "chesed", "gevurah", "tiferet",
                    "netzach", "hod", "yesod", "malkuth", "keter"):
            if mk in mods:
                assert mods[mk].capacity_factor < 1.0, f"{mk} should be degraded"

    def test_atik_degraded_all_force_katnut(self):
        """Atik dégradé → should_force_katnut True pour tous."""
        reg = PartzufimRegulator()
        state = _make_state({"atik_yomin": {"overall": 0.45}})
        for name in PARTZUF_TO_MODULES:
            if name != "atik_yomin":
                assert reg.should_force_katnut(name, state) is True

    def test_imma_katnut_cascades_za(self):
        """Imma en katnut → ZA forcé en katnut."""
        reg = PartzufimRegulator()
        state = _make_state({"imma": {"mochin_state": "katnut", "overall": 0.35}})
        assert reg.should_force_katnut("zeir_anpin", state) is True

    def test_imma_katnut_blocks_za_gadlut_return(self):
        """Imma en katnut → ZA ne peut pas revenir en gadlut."""
        reg = PartzufimRegulator()
        state = _make_state({
            "imma": {"mochin_state": "katnut", "overall": 0.35},
            "zeir_anpin": {"mochin_state": "katnut", "overall": 0.70},
        })
        assert reg.can_return_to_gadlut("zeir_anpin", state) is False

    def test_imma_gadlut_no_cascade_za(self):
        """Imma en gadlut → pas de cascade sur ZA."""
        reg = PartzufimRegulator()
        state = _make_state()  # tous en gadlut
        assert reg.should_force_katnut("zeir_anpin", state) is False


# ── Tests apply_to_tree ─────────────────────────────────────

class TestApplyToTree:

    def test_modifies_instance_attributes(self):
        """apply_to_tree modifie les attributs des instances."""
        reg = PartzufimRegulator()

        forge = StubModule(min_novelty_score=0.7, max_insights_per_session=20)
        tree = {"chokmah": forge}

        state = _make_state({"abba": {"mochin_state": "katnut", "overall": 0.35}})
        mods = reg.compute_modifiers(state)
        reg.apply_to_tree(tree, mods)

        # capacity 0.5 × 20 = 10
        assert forge.max_insights_per_session == 10
        # threshold + 0.1 → 0.7 + 0.1 = 0.8
        assert forge.min_novelty_score == pytest.approx(0.8, abs=0.01)

    def test_neutral_state_no_modification(self):
        """Gadlut/panim (neutre) → aucune modification."""
        reg = PartzufimRegulator()

        forge = StubModule(min_novelty_score=0.7, max_insights_per_session=20)
        tree = {"chokmah": forge}

        state = _make_state()  # tous en gadlut/panim (score < 0.85, pas de bonus)
        mods = reg.compute_modifiers(state)
        reg.apply_to_tree(tree, mods)

        assert forge.max_insights_per_session == 20
        assert forge.min_novelty_score == 0.7

    def test_missing_module_no_crash(self):
        """Module absent du tree → pas de crash."""
        reg = PartzufimRegulator()
        tree = {}  # tree vide
        state = _make_state()
        mods = reg.compute_modifiers(state)
        reg.apply_to_tree(tree, mods)  # Ne doit pas lever d'exception

    def test_netzach_tunable_attrs_applied(self):
        """Netzach (IntentKeeper) — threshold + budget attrs modulated in katnut."""
        reg = PartzufimRegulator()

        keeper = StubModule(
            min_progress_at_quarter=0.10,
            max_failed_ratio=0.60,
            stale_days=7,
            zombie_days=180,
        )
        tree = {"netzach": keeper}

        # ZA en katnut → netzach katnut (capacity 0.5, threshold +0.1, budget 0.5)
        state = _make_state({"zeir_anpin": {"mochin_state": "katnut", "overall": 0.35}})
        mods = reg.compute_modifiers(state)
        reg.apply_to_tree(tree, mods)

        # threshold: 0.10 + 0.1 = 0.20, 0.60 + 0.1 = 0.70
        assert keeper.min_progress_at_quarter == pytest.approx(0.20, abs=0.01)
        assert keeper.max_failed_ratio == pytest.approx(0.70, abs=0.01)
        # budget: 7 × 0.5 = 3.5 → 4, 180 × 0.5 = 90
        assert keeper.stale_days == 4
        assert keeper.zombie_days == 90

    def test_hod_tunable_attrs_applied(self):
        """Hod (SelfMap) — decline_threshold modulated in katnut."""
        reg = PartzufimRegulator()

        selfmap = StubModule(decline_threshold=0.30)
        tree = {"hod": selfmap}

        # ZA en katnut → hod katnut (threshold +0.1)
        state = _make_state({"zeir_anpin": {"mochin_state": "katnut", "overall": 0.35}})
        mods = reg.compute_modifiers(state)
        reg.apply_to_tree(tree, mods)

        # threshold: 0.30 + 0.1 = 0.40
        assert selfmap.decline_threshold == pytest.approx(0.40, abs=0.01)

    def test_yesod_keter_malkuth_no_attrs_no_modification(self):
        """Yesod, Keter, Malkuth — empty tunable attrs, no modification even in katnut."""
        reg = PartzufimRegulator()

        # Simulate modules with arbitrary attributes (should NOT be touched)
        yesod_mod = StubModule(embedding_model="nomic-embed-text", some_val=42)
        keter_mod = StubModule(some_val=99)
        malkuth_mod = StubModule(some_val=77)
        tree = {"yesod": yesod_mod, "keter": keter_mod, "malkuth": malkuth_mod}

        # Force everything into katnut
        state = _make_state({
            "zeir_anpin": {"mochin_state": "katnut", "overall": 0.35},
            "arikh_anpin": {"mochin_state": "katnut", "overall": 0.35},
            "nukva": {"mochin_state": "katnut", "overall": 0.35},
        })
        mods = reg.compute_modifiers(state)
        reg.apply_to_tree(tree, mods)

        # Nothing should be modified — tunable attrs are empty
        assert yesod_mod.some_val == 42
        assert keter_mod.some_val == 99
        assert malkuth_mod.some_val == 77


# ── Tests Tzimtzum + Partzufim ──────────────────────────────

class TestTzimtzumInteraction:

    def test_tzimtzum_dormant_overrides_partzuf_gadlut(self):
        """Si Tzimtzum dit dormant, le module n'est pas dans le tree.

        Le Regulator ne peut pas modifier un module absent — le Tzimtzum
        prime naturellement puisqu'il retire le module du pipeline.
        """
        reg = PartzufimRegulator()

        # Tree sans chesed (Tzimtzum l'a mis en dormance)
        tree = {"chokmah": StubModule(min_novelty_score=0.7, max_insights_per_session=20)}

        state = _make_state()
        mods = reg.compute_modifiers(state)

        # chesed est dans les modifiers mais PAS dans le tree
        assert "chesed" in mods
        reg.apply_to_tree(tree, mods)
        # Pas d'erreur, chesed ignoré silencieusement


# ── Tests Omer + Partzufim ──────────────────────────────────

class TestOmerInteraction:

    def test_partzuf_applies_on_top_of_omer(self):
        """Omer met novelty à 0.5, Partzuf (katnut) ajoute +0.1 → 0.6."""
        reg = PartzufimRegulator()

        # Omer a déjà réglé le seuil
        forge = StubModule(min_novelty_score=0.5, max_insights_per_session=15)
        tree = {"chokmah": forge}

        state = _make_state({"abba": {"mochin_state": "katnut", "overall": 0.35}})
        mods = reg.compute_modifiers(state)
        reg.apply_to_tree(tree, mods)

        # threshold: 0.5 + 0.1 = 0.6
        assert forge.min_novelty_score == pytest.approx(0.6, abs=0.01)
        # capacity: 15 × 0.5 = 7.5 → arrondi à 8
        assert forge.max_insights_per_session == 8


# ── Tests load_state fallback ───────────────────────────────

class TestLoadStateFallback:

    def test_fallback_to_last_state(self):
        """Si DB échoue, retourne les dernières valeurs connues."""
        reg = PartzufimRegulator()
        known_state = _make_state()
        reg._last_state = known_state

        with patch("partzufim.db.load_all_partzufim", side_effect=Exception("DB down")):
            result = reg.load_state()
            assert result == known_state

    def test_empty_if_no_fallback(self):
        """Si DB échoue et pas de fallback → dict vide."""
        reg = PartzufimRegulator()
        reg._last_state = None

        with patch("partzufim.db.load_all_partzufim", side_effect=Exception("DB down")):
            result = reg.load_state()
            assert result == {}


# ── Tests trigger_katnut / trigger_gadlut ───────────────────

class TestTriggers:

    @patch("pool.get_conn")
    def test_trigger_katnut_updates_db(self, mock_conn):
        """trigger_katnut exécute UPDATE en DB."""
        mock_cur = MagicMock()
        mock_cur.rowcount = 1
        mock_cur_ctx = MagicMock()
        mock_cur_ctx.__enter__ = lambda s: mock_cur
        mock_cur_ctx.__exit__ = lambda s, *a: None
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = lambda s: mock_ctx
        mock_ctx.__exit__ = lambda s, *a: None
        mock_ctx.cursor.return_value = mock_cur_ctx
        mock_conn.return_value = mock_ctx

        reg = PartzufimRegulator()
        result = reg.trigger_katnut("abba", "test reason")
        assert result is True
        mock_cur.execute.assert_called_once()

    @patch("pool.get_conn")
    def test_trigger_gadlut_updates_db(self, mock_conn):
        """trigger_gadlut exécute UPDATE en DB."""
        mock_cur = MagicMock()
        mock_cur.rowcount = 1
        mock_cur_ctx = MagicMock()
        mock_cur_ctx.__enter__ = lambda s: mock_cur
        mock_cur_ctx.__exit__ = lambda s, *a: None
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = lambda s: mock_ctx
        mock_ctx.__exit__ = lambda s, *a: None
        mock_ctx.cursor.return_value = mock_cur_ctx
        mock_conn.return_value = mock_ctx

        reg = PartzufimRegulator()
        result = reg.trigger_gadlut("abba", "test recovery")
        assert result is True
        mock_cur.execute.assert_called_once()


# ── Tests check_transitions (intégration pipeline) ──────────

class TestCheckTransitions:

    @patch.object(PartzufimRegulator, "trigger_katnut", return_value=True)
    def test_detects_katnut_transition(self, mock_trigger):
        """check_transitions détecte une chute en katnut."""
        reg = PartzufimRegulator()
        state = _make_state({"abba": {"overall": 0.35, "mochin_state": "gadlut"}})
        transitions = reg.check_transitions(state, use_dynamic=False)

        assert len(transitions) >= 1
        abba_t = [t for t in transitions if t["partzuf"] == "abba"]
        assert len(abba_t) == 1
        assert abba_t[0]["to"] == "katnut"

    @patch.object(PartzufimRegulator, "trigger_gadlut", return_value=True)
    def test_detects_gadlut_recovery(self, mock_trigger):
        """check_transitions détecte un retour en gadlut."""
        reg = PartzufimRegulator()
        state = _make_state({"abba": {"overall": 0.70, "mochin_state": "katnut"}})
        transitions = reg.check_transitions(state, use_dynamic=False)

        abba_t = [t for t in transitions if t["partzuf"] == "abba"]
        assert len(abba_t) == 1
        assert abba_t[0]["to"] == "gadlut"

    @patch.object(PartzufimRegulator, "trigger_katnut", return_value=True)
    @patch.object(PartzufimRegulator, "trigger_gadlut", return_value=True)
    def test_no_transition_when_stable(self, mock_gadlut, mock_katnut):
        """Pas de transition si tout est stable (gadlut, scores > 0.6)."""
        reg = PartzufimRegulator()
        state = _make_state()  # tous gadlut, scores > 0.6
        transitions = reg.check_transitions(state, use_dynamic=False)

        # Aucune transition attendue
        assert transitions == []


# ── Tests empty/missing state ───────────────────────────────

class TestEdgeCases:

    def test_empty_state_returns_neutral_modifiers(self):
        """État vide → modifiers neutres (pas de modulation)."""
        reg = PartzufimRegulator()
        mods = reg.compute_modifiers({})

        for mk, profile in mods.items():
            assert profile.capacity_factor == 1.0
            assert profile.threshold_modifier == 0.0
            assert "absent de DB" in profile.reason

    def test_partial_state_handles_missing_partzuf(self):
        """État partiel (Partzuf manquant) → neutre pour ce Partzuf."""
        reg = PartzufimRegulator()
        state = {"abba": {"overall": 0.75, "mochin_state": "gadlut", "orientation": "panim"}}
        mods = reg.compute_modifiers(state)

        assert mods["chokmah"].capacity_factor == 1.0  # abba présent
        assert mods["binah"].capacity_factor == 1.0    # imma absent → neutre
        assert "absent de DB" in mods["binah"].reason

    def test_transitional_state_intermediate(self):
        """État transitional → modifiers intermédiaires."""
        reg = PartzufimRegulator()
        state = _make_state({"abba": {"mochin_state": "transitional", "overall": 0.55}})
        mods = reg.compute_modifiers(state)

        assert mods["chokmah"].capacity_factor == 0.75
        assert mods["chokmah"].threshold_modifier == 0.03

    def test_module_tunable_attrs_covers_all_modules(self):
        """MODULE_TUNABLE_ATTRS has an entry for every module in PARTZUF_TO_MODULES."""
        all_modules = set()
        for modules in PARTZUF_TO_MODULES.values():
            all_modules.update(modules)

        for module_key in all_modules:
            assert module_key in MODULE_TUNABLE_ATTRS, (
                f"Module '{module_key}' missing from MODULE_TUNABLE_ATTRS"
            )
            entry = MODULE_TUNABLE_ATTRS[module_key]
            assert "capacity" in entry, f"{module_key} missing 'capacity' key"
            assert "threshold" in entry, f"{module_key} missing 'threshold' key"
            assert "budget" in entry, f"{module_key} missing 'budget' key"


# ── Tests scores dynamiques ───────────────────────────────

class TestDynamicScores:

    def test_dynamic_score_blends_cumul_and_recent(self):
        """apply_dynamic_scores fusionne cumul (60%) et récent (40%)."""
        from partzufim.regulator import DYNAMIC_WEIGHT_CUMUL, DYNAMIC_WEIGHT_RECENT

        reg = PartzufimRegulator()
        state = _make_state({"abba": {"overall": 0.80}})

        dynamic = {
            "abba": {
                "dynamic_score": 0.3,
                "recent_metrics": {"insights_24h": 0},
                "should_achor": False,
                "achor_reason": "",
            },
        }

        reg.apply_dynamic_scores(state, dynamic)

        expected = DYNAMIC_WEIGHT_CUMUL * 0.80 + DYNAMIC_WEIGHT_RECENT * 0.3
        assert state["abba"]["overall"] == pytest.approx(expected, abs=0.01)

    def test_score_drops_with_zero_activity(self):
        """Score chute si 0 activité récente (INACTIVITY_SCORE=0.5)."""
        from partzufim.regulator import INACTIVITY_SCORE, DYNAMIC_WEIGHT_CUMUL, DYNAMIC_WEIGHT_RECENT

        reg = PartzufimRegulator()
        state = _make_state({"abba": {"overall": 0.75}})

        # Simuler 0 activité → dynamic_score = INACTIVITY_SCORE (0.3)
        dynamic = {
            "abba": {
                "dynamic_score": INACTIVITY_SCORE,
                "recent_metrics": {},
                "should_achor": True,
                "achor_reason": "0 insights en 24h",
            },
        }

        reg.apply_dynamic_scores(state, dynamic)

        expected = DYNAMIC_WEIGHT_CUMUL * 0.75 + DYNAMIC_WEIGHT_RECENT * INACTIVITY_SCORE
        assert state["abba"]["overall"] == pytest.approx(expected, abs=0.01)
        # Avec les poids rééquilibrés (0.6/0.4), le score cumulatif
        # protège mieux contre la chute — le score reste au-dessus de 0.5
        assert state["abba"]["overall"] > 0.5

    def test_katnut_triggered_by_dynamic_score(self):
        """Score dynamique très bas → should_force_katnut True."""
        reg = PartzufimRegulator()
        # Cumulatif = 0.40 (bas), récent = 0.1 (très faible)
        # Blended = 0.6*0.40 + 0.4*0.1 = 0.24 + 0.04 = 0.28 < 0.4 → katnut !
        state = _make_state({"abba": {"overall": 0.40, "mochin_state": "gadlut"}})

        dynamic = {
            "abba": {
                "dynamic_score": 0.1,
                "recent_metrics": {},
                "should_achor": False,
                "achor_reason": "",
            },
        }

        reg.apply_dynamic_scores(state, dynamic)
        assert reg.should_force_katnut("abba", state) is True

    def test_achor_on_inactivity(self):
        """Inactivité 24h → orientation passe de panim à achor."""
        reg = PartzufimRegulator()
        state = _make_state({"imma": {"overall": 0.60, "orientation": "panim"}})

        dynamic = {
            "imma": {
                "dynamic_score": 0.3,
                "recent_metrics": {},
                "should_achor": True,
                "achor_reason": "0 claims en 24h",
            },
        }

        reg.apply_dynamic_scores(state, dynamic)
        assert state["imma"]["orientation"] == "akhor"

    def test_panim_restored_on_activity_resume(self):
        """Reprise d'activité → orientation revient de achor à panim."""
        reg = PartzufimRegulator()
        state = _make_state({"imma": {"overall": 0.60, "orientation": "akhor"}})

        dynamic = {
            "imma": {
                "dynamic_score": 0.7,
                "recent_metrics": {"claims_24h": 5},
                "should_achor": False,
                "achor_reason": "",
            },
        }

        reg.apply_dynamic_scores(state, dynamic)
        assert state["imma"]["orientation"] == "panim"

    def test_cascade_imma_katnut_via_dynamic(self):
        """Imma en katnut via score dynamique → ZA forcé katnut aussi."""
        reg = PartzufimRegulator()
        # Imma : cumul=0.35 (bas), récent=0.1 (très faible)
        # Blended = 0.6*0.35 + 0.4*0.1 = 0.21 + 0.04 = 0.25 < 0.4
        state = _make_state({
            "imma": {"overall": 0.35, "mochin_state": "gadlut"},
            "zeir_anpin": {"overall": 0.70, "mochin_state": "gadlut"},
        })

        dynamic = {
            "imma": {
                "dynamic_score": 0.1,
                "recent_metrics": {},
                "should_achor": False,
                "achor_reason": "",
            },
        }

        reg.apply_dynamic_scores(state, dynamic)
        # Imma score < 0.4 → ZA forcé katnut via cascade
        assert reg.should_force_katnut("zeir_anpin", state) is True

    def test_gadlut_return_after_activity_boost(self):
        """Score dynamique remonte > 0.6 après reprise → retour gadlut."""
        reg = PartzufimRegulator()
        state = _make_state({
            "abba": {"overall": 0.50, "mochin_state": "katnut"},
        })

        dynamic = {
            "abba": {
                "dynamic_score": 0.85,
                "recent_metrics": {"insights_24h": 10},
                "should_achor": False,
                "achor_reason": "",
            },
        }

        reg.apply_dynamic_scores(state, dynamic)
        # Blended = 0.6*0.50 + 0.4*0.85 = 0.30 + 0.34 = 0.64 > 0.6
        assert state["abba"]["overall"] > 0.6
        assert reg.can_return_to_gadlut("abba", state) is True

    def test_atik_yomin_is_average_of_others(self):
        """Atik Yomin = moyenne des 5 autres Partzufim dynamiques."""
        reg = PartzufimRegulator()
        state = _make_state()

        # Simuler des scores dynamiques variés
        dynamic = {}
        scores = {"abba": 0.8, "imma": 0.3, "zeir_anpin": 0.5, "nukva": 0.6, "arikh_anpin": 0.4}
        for name, s in scores.items():
            dynamic[name] = {
                "dynamic_score": s,
                "recent_metrics": {},
                "should_achor": False,
                "achor_reason": "",
            }
        # Atik = mean of others
        avg = sum(scores.values()) / len(scores)
        dynamic["atik_yomin"] = {
            "dynamic_score": round(avg, 3),
            "recent_metrics": {"avg_of_others": round(avg, 3)},
            "should_achor": False,
            "achor_reason": "",
        }

        reg.apply_dynamic_scores(state, dynamic)
        # Atik blended = 0.6*0.87 + 0.4*avg
        expected_atik = 0.6 * 0.87 + 0.4 * avg
        assert state["atik_yomin"]["overall"] == pytest.approx(expected_atik, abs=0.02)

    def test_check_transitions_with_dynamic(self):
        """check_transitions(use_dynamic=False) ne modifie pas les scores."""
        reg = PartzufimRegulator()
        state = _make_state()

        # Sans dynamic, pas de transition (tous gadlut, scores > 0.6)
        with patch.object(reg, "trigger_katnut", return_value=True) as mock_k:
            with patch.object(reg, "trigger_gadlut", return_value=True) as mock_g:
                transitions = reg.check_transitions(state, use_dynamic=False)
                assert transitions == []
