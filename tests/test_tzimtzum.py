"""Tests du TzimtzumEngine — צִמְצוּם.

Couvre :
  - Contraction vers un domaine focal
  - Modules dormants et actifs pendant la contraction
  - État du Kav (קַו) = Keter toujours actif
  - Expansion (Hitpashtut) et restauration
  - Reshimu : traces résiduelles, insights_during_contraction
  - Réintégration des insights post-expansion
  - get_halal_state() complet
  - Détection automatique (contraction/expansion)
  - Double contraction refusée
  - Expansion sans contraction refusée
"""

import time

import pytest

from tzimtzum import (
    TzimtzumEngine, Reshimu, KAV_MODULE, SEPHIROT_MODULES,
    SystemPressure, TzimtzumPhase, TzimtzumAction,
    CONTRACTION_THRESHOLD, EXPANSION_THRESHOLD,
)


# ── Helpers ──────────────────────────────────────────────────

def _fresh_state() -> dict:
    """Créer un _TZIMTZUM_STATE vierge."""
    return {
        "active": False,
        "focused_domain": None,
        "excluded_domains": [],
        "reshimu": [],
        "contraction_count": 0,
        "expansion_count": 0,
        "log": [],
    }


def _stub_tree(**overrides) -> dict:
    """Arbre stub minimal — chaque module est un objet basique."""
    tree = {}
    for mod in SEPHIROT_MODULES:
        tree[mod] = overrides.get(mod, object())
    return tree


class MockModule:
    """Module stub avec self_diagnose()."""

    def __init__(self, diag: dict | None = None):
        self._diag = diag or {"status": "ok"}
        self._remembered: list[dict] = []

    def self_diagnose(self) -> dict:
        return dict(self._diag)

    def remember(self, **kwargs):
        self._remembered.append(kwargs)


# ── Reshimu dataclass ────────────────────────────────────────

class TestReshimu:

    def test_creation(self):
        r = Reshimu(
            timestamp=1000.0,
            focused_domain="kabbale",
            excluded_domains=["physique", "chimie"],
            excluded_modules=["chesed", "netzach"],
            pre_contraction_state={"chesed": {"total": 42}},
            reason="test",
        )
        assert r.focused_domain == "kabbale"
        assert r.insights_during_contraction == []

    def test_to_dict(self):
        r = Reshimu(
            timestamp=1000.0,
            focused_domain="ia",
            excluded_domains=["bio"],
            excluded_modules=["netzach"],
            pre_contraction_state={},
            reason="test",
            insights_during_contraction=["insight1"],
        )
        d = r.to_dict()
        assert d["focused_domain"] == "ia"
        assert d["insights_during_contraction"] == ["insight1"]
        # Vérifier que c'est une copie, pas une référence
        d["insights_during_contraction"].append("extra")
        assert len(r.insights_during_contraction) == 1


# ── Contraction ──────────────────────────────────────────────

class TestContraction:

    def test_contract_basic(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        tree = _stub_tree()
        ctx = {}

        result = engine.contract("kabbale", tree, ctx, reason="focus CLI")
        assert result["action"] == "contracted"
        assert result["domain"] == "kabbale"
        assert result["kav"] == "keter"
        assert engine.is_contracted is True
        assert engine.focused_domain == "kabbale"

    def test_contract_updates_state(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        engine.contract("math", _stub_tree(), {}, reason="test")

        assert state["active"] is True
        assert state["focused_domain"] == "math"
        assert state["contraction_count"] == 1
        assert len(state["log"]) == 1
        assert state["log"][0]["action"] == "tzimtzum"

    def test_double_contraction_refused(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        engine.contract("kabbale", _stub_tree(), {})

        result = engine.contract("physique", _stub_tree(), {})
        assert result["action"] == "already_contracted"
        assert result["focused_domain"] == "kabbale"

    def test_contract_creates_reshimu(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        engine.contract("ia", _stub_tree(), {}, reason="test reshimu")

        reshimot = engine.get_reshimot()
        assert len(reshimot) == 1
        assert reshimot[0]["focused_domain"] == "ia"
        assert reshimot[0]["reason"] == "test reshimu"

    def test_contract_with_chesed_domains(self):
        """Les domaines explorés par Chesed (sauf le focal) sont exclus."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        ctx = {
            "chesed_diag": {
                "domains_explored": ["kabbale", "physique", "chimie"],
            }
        }
        result = engine.contract("kabbale", _stub_tree(), ctx)
        assert "physique" in result["excluded_domains"]
        assert "chimie" in result["excluded_domains"]
        assert "kabbale" not in result["excluded_domains"]

    def test_contract_propagates_ctx(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        ctx = {}
        engine.contract("ia", _stub_tree(), ctx)

        assert ctx["tzimtzum_active"] is True
        assert ctx["tzimtzum_focused_domain"] == "ia"
        assert isinstance(ctx["tzimtzum_dormant_modules"], list)


# ── Modules dormants / actifs ────────────────────────────────

class TestModuleDormancy:

    def test_kav_always_active(self):
        """Le Kav (Keter) reste TOUJOURS actif pendant la contraction."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        engine.contract("kabbale", _stub_tree(), {})

        assert engine.is_module_active("keter") is True
        assert "keter" in engine.get_active_modules()
        assert "keter" not in engine.get_dormant_modules()

    def test_structural_modules_active(self):
        """Yesod, Hod, Tiferet, Malkuth restent toujours actifs."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        engine.contract("kabbale", _stub_tree(), {})

        for mod in ("yesod", "hod", "tiferet", "malkuth"):
            assert engine.is_module_active(mod), f"{mod} devrait être actif"

    def test_chesed_dormant(self):
        """Chesed (exploration) est mis en dormance pendant la contraction."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        engine.contract("kabbale", _stub_tree(), {})

        assert engine.is_module_active("chesed") is False
        assert "chesed" in engine.get_dormant_modules()

    def test_netzach_dormant(self):
        """Netzach (intentions) est mis en dormance pendant la contraction."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        engine.contract("kabbale", _stub_tree(), {})

        assert engine.is_module_active("netzach") is False
        assert "netzach" in engine.get_dormant_modules()

    def test_all_active_when_not_contracted(self):
        """Tous les modules sont actifs quand pas de contraction."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)

        for mod in SEPHIROT_MODULES:
            assert engine.is_module_active(mod) is True

    def test_chokmah_gevurah_active(self):
        """Chokmah (insight) et Gevurah (jugement) restent actifs."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        engine.contract("kabbale", _stub_tree(), {})

        assert engine.is_module_active("chokmah") is True
        assert engine.is_module_active("gevurah") is True

    def test_binah_daat_active_with_competence(self):
        """Binah et Da'at restent actifs si Hod montre de la compétence."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        hod_mock = MockModule({"competence_score": 0.5})
        tree = _stub_tree(hod=hod_mock)

        engine.contract("kabbale", tree, {})
        assert engine.is_module_active("binah") is True
        assert engine.is_module_active("daat") is True

    def test_pre_contraction_state_captured(self):
        """L'état pré-contraction des modules dormants est capturé."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        chesed_mock = MockModule({"total_connections": 42})
        tree = _stub_tree(chesed=chesed_mock)

        engine.contract("kabbale", tree, {})
        reshimot = engine.get_reshimot()
        pre_state = reshimot[0]["pre_contraction_state"]
        # Chesed devrait être dans le pre_state (il est dormant et a self_diagnose)
        assert "chesed" in pre_state
        assert pre_state["chesed"]["total_connections"] == 42


# ── Expansion (Hitpashtut) ───────────────────────────────────

class TestExpansion:

    def test_expand_basic(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        tree = _stub_tree()
        ctx = {}

        engine.contract("kabbale", tree, ctx)
        result = engine.expand(tree, ctx)

        assert result["action"] == "expanded"
        assert result["from_domain"] == "kabbale"
        assert engine.is_contracted is False
        assert engine.focused_domain is None

    def test_expand_without_contraction(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        result = engine.expand(_stub_tree(), {})
        assert result["action"] == "not_contracted"

    def test_expand_updates_state(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        engine.contract("ia", _stub_tree(), {})
        engine.expand(_stub_tree(), {})

        assert state["active"] is False
        assert state["focused_domain"] is None
        assert state["expansion_count"] == 1

    def test_expand_reactivates_all_modules(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        engine.contract("kabbale", _stub_tree(), {})
        dormant_before = engine.get_dormant_modules()
        assert len(dormant_before) > 0

        engine.expand(_stub_tree(), {})
        assert len(engine.get_dormant_modules()) == 0
        assert engine.get_active_modules() == set(SEPHIROT_MODULES)

    def test_expand_recovers_excluded_domains(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        ctx = {
            "chesed_diag": {
                "domains_explored": ["kabbale", "physique", "chimie"],
            }
        }
        engine.contract("kabbale", _stub_tree(), ctx)
        result = engine.expand(_stub_tree(), {})
        assert "physique" in result["recovered_domains"]
        assert "chimie" in result["recovered_domains"]

    def test_expand_returns_reactivated_modules(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        engine.contract("kabbale", _stub_tree(), {})
        result = engine.expand(_stub_tree(), {})
        assert len(result["reactivated_modules"]) > 0

    def test_expand_propagates_ctx(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        ctx = {}
        engine.contract("ia", _stub_tree(), ctx)
        engine.expand(_stub_tree(), ctx)

        assert ctx["tzimtzum_active"] is False
        assert ctx["hitpashut_from"] == "ia"

    def test_multiple_cycles(self):
        """Contract → expand → contract → expand."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        tree = _stub_tree()

        engine.contract("kabbale", tree, {})
        engine.expand(tree, {})
        assert state["contraction_count"] == 1
        assert state["expansion_count"] == 1

        engine.contract("physique", tree, {})
        engine.expand(tree, {})
        assert state["contraction_count"] == 2
        assert state["expansion_count"] == 2
        assert len(engine.get_reshimot()) == 2


# ── Insights pendant la contraction ──────────────────────────

class TestInsights:

    def test_add_insight_during_contraction(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        engine.contract("ia", _stub_tree(), {})

        ok = engine.add_insight("Les Transformers sont des cas particuliers")
        assert ok is True

        reshimot = engine.get_reshimot()
        assert len(reshimot[0]["insights_during_contraction"]) == 1

    def test_add_insight_refused_when_not_contracted(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        ok = engine.add_insight("Ceci ne devrait pas fonctionner")
        assert ok is False

    def test_insights_returned_on_expand(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        engine.contract("ia", _stub_tree(), {})
        engine.add_insight("Insight A")
        engine.add_insight("Insight B")

        result = engine.expand(_stub_tree(), {})
        assert result["insights"] == ["Insight A", "Insight B"]

    def test_insights_distributed_to_dormant_modules(self):
        """Les insights sont distribués aux modules dormants via Yesod."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        yesod_mock = MockModule()
        tree = _stub_tree(yesod=yesod_mock)

        engine.contract("ia", tree, {})
        engine.add_insight("Clé de compréhension")
        result = engine.expand(tree, {})

        # Yesod devrait avoir reçu des remember() pour chaque module dormant
        assert len(yesod_mock._remembered) > 0
        # Chaque module dormant reçoit l'insight
        distributed = result.get("insights_distributed", {})
        assert len(distributed) > 0

    def test_insights_in_state_dict(self):
        """Les insights sont aussi dans le _TZIMTZUM_STATE."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        engine.contract("ia", _stub_tree(), {})
        engine.add_insight("Test insight sync")

        assert len(state["reshimu"]) == 1
        assert "Test insight sync" in state["reshimu"][-1]["insights_during_contraction"]


# ── get_halal_state ──────────────────────────────────────────

class TestHalalState:

    def test_halal_not_contracted(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        halal = engine.get_halal_state()

        assert halal["contracted"] is False
        assert halal["focused_domain"] is None
        assert halal["kav"] == "keter"
        assert halal["kav_active"] is True
        assert len(halal["dormant_modules"]) == 0
        assert set(halal["active_modules"]) == set(SEPHIROT_MODULES)

    def test_halal_contracted(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        engine.contract("kabbale", _stub_tree(), {})
        halal = engine.get_halal_state()

        assert halal["contracted"] is True
        assert halal["focused_domain"] == "kabbale"
        assert halal["contraction_count"] == 1
        assert halal["reshimu_count"] == 1
        assert len(halal["dormant_modules"]) > 0
        assert "keter" in halal["active_modules"]

    def test_halal_current_insights(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        engine.contract("ia", _stub_tree(), {})
        engine.add_insight("Insight 1")
        engine.add_insight("Insight 2")
        halal = engine.get_halal_state()

        assert halal["current_insights"] == 2

    def test_halal_after_expand(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        engine.contract("ia", _stub_tree(), {})
        engine.expand(_stub_tree(), {})
        halal = engine.get_halal_state()

        assert halal["contracted"] is False
        assert halal["expansion_count"] == 1
        assert halal["current_insights"] == 0


# ── Détection automatique ────────────────────────────────────

class TestDetection:

    def test_detect_contraction_trigger(self):
        """Connexions > 10 et validées < connexions/3 → trigger."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        ctx = {
            "chesed_diag": {"total_connections": 18, "total_explorations": 10},
            "gevurah_diag": {"total_experiments": 0, "rejection_rate": 0.0},
        }
        result = engine.detect_contraction(ctx)
        assert result["trigger"] is True

    def test_detect_contraction_no_trigger_few_connections(self):
        """Peu de connexions → pas de trigger."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        ctx = {
            "chesed_diag": {"total_connections": 5, "total_explorations": 3},
            "gevurah_diag": {"total_experiments": 4, "rejection_rate": 0.2},
        }
        result = engine.detect_contraction(ctx)
        assert result["trigger"] is False

    def test_detect_contraction_no_trigger_enough_validated(self):
        """Assez de validations → pas de trigger."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        ctx = {
            "chesed_diag": {"total_connections": 18, "total_explorations": 10},
            "gevurah_diag": {"total_experiments": 7, "rejection_rate": 0.2},
        }
        result = engine.detect_contraction(ctx)
        assert result["trigger"] is False

    def test_detect_expansion_trigger(self):
        """Contracté + Hod > 0.8 + tensions < 2 → expansion."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        engine.contract("ia", _stub_tree(), {})

        ctx = {
            "mochin": {"competence_score": 0.9},
            "tiferet_diag": {"open_tensions": 1},
        }
        result = engine.detect_expansion(ctx)
        assert result["trigger"] is True

    def test_detect_expansion_no_trigger_not_contracted(self):
        """Pas contracté → pas d'expansion possible."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        ctx = {
            "mochin": {"competence_score": 0.9},
            "tiferet_diag": {"open_tensions": 0},
        }
        result = engine.detect_expansion(ctx)
        assert result["trigger"] is False

    def test_detect_expansion_no_trigger_low_hod(self):
        """Hod bas → maîtrise insuffisante → pas d'expansion."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        engine.contract("ia", _stub_tree(), {})

        ctx = {
            "mochin": {"competence_score": 0.3},
            "tiferet_diag": {"open_tensions": 0},
        }
        result = engine.detect_expansion(ctx)
        assert result["trigger"] is False


# ── Format rapport ───────────────────────────────────────────

class TestFormatReport:

    def test_format_report_contracted(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        engine.contract("ia", _stub_tree(), {})
        lines = engine.format_report({})

        text = "\n".join(lines)
        assert "צִמְצוּם" in text
        assert "CONTRACTION" in text
        assert "ia" in text
        assert "keter" in text.lower()

    def test_format_report_stable(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        lines = engine.format_report({})

        text = "\n".join(lines)
        assert "stable" in text

    def test_format_expansion_report(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        engine.contract("kabbale", _stub_tree(), {})
        engine.add_insight("Découverte importante")
        result = engine.expand(_stub_tree(), {})
        lines = engine.format_expansion_report(result)

        text = "\n".join(lines)
        assert "הִתְפַּשְׁטוּת" in text
        assert "EXPANSION" in text
        assert "kabbale" in text


# ── Constantes ───────────────────────────────────────────────

class TestConstants:

    def test_kav_is_keter(self):
        assert KAV_MODULE == "keter"

    def test_sephirot_count(self):
        assert len(SEPHIROT_MODULES) == 11

    def test_sephirot_contains_keter(self):
        assert "keter" in SEPHIROT_MODULES

    def test_sephirot_contains_malkuth(self):
        assert "malkuth" in SEPHIROT_MODULES


# ── SystemPressure & assess_system_pressure ─────────────────

class TestSystemPressure:

    def test_all_zeros_no_pressure(self):
        """Aucune donnée → pression 0."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        p = engine.assess_system_pressure()
        assert p.global_pressure == 0.0
        assert p.phase == TzimtzumPhase.EXPANSION

    def test_high_pressure_contraction(self):
        """Haute pression (> 0.7) → phase CONTRACTION."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        p = engine.assess_system_pressure(
            open_tensions=90, resolved_tensions=10,
            hypotheses=95, facts=5,
            insights_rejected=90, insights_accepted=5, insights_pending=5,
            causal_claims_weak=85, causal_claims_total=100,
        )
        assert p.global_pressure > CONTRACTION_THRESHOLD
        assert p.phase == TzimtzumPhase.CONTRACTION

    def test_low_pressure_expansion(self):
        """Basse pression (< 0.3) → phase EXPANSION."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        p = engine.assess_system_pressure(
            open_tensions=5, resolved_tensions=95,
            hypotheses=10, facts=90,
            insights_rejected=5, insights_accepted=90, insights_pending=5,
            causal_claims_weak=10, causal_claims_total=100,
        )
        assert p.global_pressure < EXPANSION_THRESHOLD
        assert p.phase == TzimtzumPhase.EXPANSION

    def test_mid_pressure_stable(self):
        """Pression intermédiaire → phase STABLE."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        p = engine.assess_system_pressure(
            open_tensions=50, resolved_tensions=50,
            hypotheses=50, facts=50,
            insights_rejected=50, insights_accepted=30, insights_pending=20,
            causal_claims_weak=50, causal_claims_total=100,
        )
        assert EXPANSION_THRESHOLD <= p.global_pressure <= CONTRACTION_THRESHOLD
        assert p.phase == TzimtzumPhase.STABLE

    def test_pressure_to_dict(self):
        """to_dict() contient toutes les clés."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        p = engine.assess_system_pressure(
            open_tensions=10, resolved_tensions=10,
        )
        d = p.to_dict()
        assert "global_pressure" in d
        assert "phase" in d
        assert "tension_pressure" in d
        assert "memory_pressure" in d

    def test_tension_pressure_calculation(self):
        """tension_pressure = open / (open + resolved)."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        p = engine.assess_system_pressure(
            open_tensions=80, resolved_tensions=20,
        )
        assert abs(p.tension_pressure - 0.8) < 0.01

    def test_memory_pressure_calculation(self):
        """memory_pressure = hypotheses / (hypotheses + facts)."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        p = engine.assess_system_pressure(
            hypotheses=60, facts=40,
        )
        assert abs(p.memory_pressure - 0.6) < 0.01

    def test_insight_pressure_calculation(self):
        """insight_pressure = rejected / (rejected + accepted + pending)."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        p = engine.assess_system_pressure(
            insights_rejected=70, insights_accepted=20, insights_pending=10,
        )
        assert abs(p.insight_pressure - 0.7) < 0.01

    def test_causal_pressure_calculation(self):
        """causal_pressure = weak / total."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        p = engine.assess_system_pressure(
            causal_claims_weak=30, causal_claims_total=100,
        )
        assert abs(p.causal_pressure - 0.3) < 0.01


# ── regulate ────────────────────────────────────────────────

class TestRegulate:

    def test_contraction_triggers_contract(self):
        """regulate() avec pression haute → contraction."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        p = SystemPressure(
            tension_pressure=0.9, memory_pressure=0.9,
            insight_pressure=0.9, causal_pressure=0.9,
            global_pressure=0.9, phase=TzimtzumPhase.CONTRACTION,
        )
        action = engine.regulate(p, _stub_tree(), {}, weakest_domain="kabbale")
        assert action.phase == TzimtzumPhase.CONTRACTION
        assert action.kav_domain == "kabbale"
        assert engine.is_contracted is True

    def test_expansion_triggers_expand(self):
        """regulate() avec pression basse et contracté → expansion."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        tree = _stub_tree()
        engine.contract("kabbale", tree, {}, reason="test")

        p = SystemPressure(
            tension_pressure=0.1, memory_pressure=0.1,
            insight_pressure=0.1, causal_pressure=0.1,
            global_pressure=0.1, phase=TzimtzumPhase.EXPANSION,
        )
        action = engine.regulate(p, tree, {})
        assert action.phase == TzimtzumPhase.EXPANSION
        assert engine.is_contracted is False

    def test_stable_no_change(self):
        """regulate() avec pression stable → pas de changement."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        p = SystemPressure(
            tension_pressure=0.5, memory_pressure=0.5,
            insight_pressure=0.5, causal_pressure=0.5,
            global_pressure=0.5, phase=TzimtzumPhase.STABLE,
        )
        action = engine.regulate(p, _stub_tree(), {})
        assert action.phase == TzimtzumPhase.STABLE
        assert action.adjustments == {}

    def test_contraction_creates_reshimu(self):
        """regulate() contraction → crée un reshimu."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        p = SystemPressure(
            tension_pressure=0.9, memory_pressure=0.9,
            insight_pressure=0.9, causal_pressure=0.9,
            global_pressure=0.9, phase=TzimtzumPhase.CONTRACTION,
        )
        action = engine.regulate(p, _stub_tree(), {}, weakest_domain="ia")
        assert action.reshimu_snapshot is not None
        assert action.reshimu_snapshot["focused_domain"] == "ia"

    def test_contraction_adjustments(self):
        """regulate() contraction → adjustments corrects."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        p = SystemPressure(
            tension_pressure=0.9, memory_pressure=0.9,
            insight_pressure=0.9, causal_pressure=0.9,
            global_pressure=0.9, phase=TzimtzumPhase.CONTRACTION,
        )
        action = engine.regulate(p, _stub_tree(), {}, weakest_domain="ia")
        assert action.adjustments["hitbonenut_focus"] == "ia"
        assert action.adjustments["chesed"] == "dormant"

    def test_expansion_adjustments(self):
        """regulate() expansion → adjustments d'ouverture."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        tree = _stub_tree()
        engine.contract("ia", tree, {}, reason="test")

        p = SystemPressure(
            tension_pressure=0.1, memory_pressure=0.1,
            insight_pressure=0.1, causal_pressure=0.1,
            global_pressure=0.1, phase=TzimtzumPhase.EXPANSION,
        )
        action = engine.regulate(p, tree, {})
        assert action.adjustments["hitbonenut_focus"] == "all"
        assert action.adjustments["exploration_walks"] == "increased"

    def test_expansion_when_not_contracted(self):
        """regulate() expansion sans contraction → 'déjà étendu'."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        p = SystemPressure(
            tension_pressure=0.1, memory_pressure=0.1,
            insight_pressure=0.1, causal_pressure=0.1,
            global_pressure=0.1, phase=TzimtzumPhase.EXPANSION,
        )
        action = engine.regulate(p, _stub_tree(), {})
        assert action.reason == "déjà étendu"
        assert action.adjustments == {}

    def test_recontraction_different_domain(self):
        """Si déjà contracté et nouvelle contraction sur autre domaine → expand puis contract."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        tree = _stub_tree()
        engine.contract("kabbale", tree, {}, reason="initial")

        p = SystemPressure(
            tension_pressure=0.9, memory_pressure=0.9,
            insight_pressure=0.9, causal_pressure=0.9,
            global_pressure=0.9, phase=TzimtzumPhase.CONTRACTION,
        )
        action = engine.regulate(p, tree, {}, weakest_domain="physique")
        assert action.kav_domain == "physique"
        assert engine.focused_domain == "physique"
        # L'expansion intermédiaire est comptée
        assert state["expansion_count"] == 1
        assert state["contraction_count"] == 2

    def test_same_domain_already_contracted(self):
        """Si déjà contracté sur le même domaine → pas de re-contraction."""
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        tree = _stub_tree()
        engine.contract("kabbale", tree, {}, reason="initial")

        p = SystemPressure(
            tension_pressure=0.9, memory_pressure=0.9,
            insight_pressure=0.9, causal_pressure=0.9,
            global_pressure=0.9, phase=TzimtzumPhase.CONTRACTION,
        )
        action = engine.regulate(p, tree, {}, weakest_domain="kabbale")
        assert action.reason.startswith("déjà contracté")
        assert state["contraction_count"] == 1  # pas de re-contraction


# ── get_kav_focus ───────────────────────────────────────────

class TestKavFocus:

    def test_kav_focus_when_contracted(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        engine.contract("ia", _stub_tree(), {})
        assert engine.get_kav_focus() == "ia"

    def test_kav_focus_when_not_contracted(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        assert engine.get_kav_focus() is None

    def test_kav_focus_after_expand(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        tree = _stub_tree()
        engine.contract("ia", tree, {})
        engine.expand(tree, {})
        assert engine.get_kav_focus() is None


# ── get_reshimu_snapshot ────────────────────────────────────

class TestReshimuSnapshot:

    def test_snapshot_none_before_contraction(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        assert engine.get_reshimu_snapshot() is None

    def test_snapshot_after_contraction(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        engine.contract("kabbale", _stub_tree(), {}, reason="test")
        snap = engine.get_reshimu_snapshot()
        assert snap is not None
        assert snap["focused_domain"] == "kabbale"
        assert snap["reason"] == "test"

    def test_snapshot_is_latest(self):
        state = _fresh_state()
        engine = TzimtzumEngine(state)
        tree = _stub_tree()
        engine.contract("kabbale", tree, {}, reason="first")
        engine.expand(tree, {})
        engine.contract("physique", tree, {}, reason="second")
        snap = engine.get_reshimu_snapshot()
        assert snap["focused_domain"] == "physique"
        assert snap["reason"] == "second"


# ── TzimtzumPhase enum ──────────────────────────────────────

class TestTzimtzumPhase:

    def test_values(self):
        assert TzimtzumPhase.CONTRACTION.value == "contraction"
        assert TzimtzumPhase.STABLE.value == "stable"
        assert TzimtzumPhase.EXPANSION.value == "expansion"

    def test_thresholds(self):
        assert CONTRACTION_THRESHOLD == 0.7
        assert EXPANSION_THRESHOLD == 0.3
