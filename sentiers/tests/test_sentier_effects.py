"""Tests des effets transformationnels des sentiers.

Couvre :
  - Qoph : injecte recall_domain dans le ctx
  - Tav : détecte la dérive et ajoute un warning
  - Beth : modifie novelty_threshold en mode exploratoire
  - Teth : filtre les explorations faibles
  - Lamed : extrait les rejection_patterns
  - Ayin : détecte le désalignement intention/compétence
  - Nun : vérifie l'alignement synthèse/intention
  - Daleth : prépare les insights pour analyse Binah
  - Sentier inactif si condition non remplie
  - Routeur applique les effets (ctx_additions, module_modifiers, warnings)
"""

import pytest
from unittest.mock import MagicMock

from sentiers.qoph import Qoph
from sentiers.tav import Tav
from sentiers.beth import Beth
from sentiers.teth import Teth
from sentiers.lamed import Lamed
from sentiers.ayin import Ayin
from sentiers.nun import Nun
from sentiers.daleth import Daleth
from sentiers.router import SentierRouter


# ── Helpers ──────────────────────────────────────────────────

def _route_mock(domain="kabbale", score=0.7, declined=False):
    """Simule un route_decision de SelfMap."""
    mock = MagicMock()
    mock.detected_domain = domain
    mock.competence_score = score
    mock.did_decline = declined
    mock.decline_reason = "test" if declined else ""
    return mock


# ── Qoph — enrichir le recall ───────────────────────────────

class TestQophEffects:

    def test_qoph_injects_recall_domain(self):
        """Qoph injecte recall_domain depuis Hod dans le ctx."""
        q = Qoph()
        ctx = {"route_decision": _route_mock(domain="kabbale")}
        effects = q._compute_effects(ctx, "yashar")

        assert effects["applied"] is True
        assert effects["ctx_additions"]["recall_domain"] == "kabbale"

    def test_qoph_fallback_to_mochin_domain(self):
        """Qoph utilise mochin.domain si route_decision absent."""
        q = Qoph()
        ctx = {"mochin": {"domain": "philosophie"}}
        effects = q._compute_effects(ctx, "yashar")

        assert effects["applied"] is True
        assert effects["ctx_additions"]["recall_domain"] == "philosophie"

    def test_qoph_no_effect_without_domain(self):
        """Qoph ne fait rien si aucun domaine détecté."""
        q = Qoph()
        effects = q._compute_effects({}, "yashar")
        assert effects["applied"] is False


# ── Tav — check de cohérence ────────────────────────────────

class TestTavEffects:

    def test_tav_detects_drift_shallow_with_many_traversals(self):
        """Tav détecte une dérive si question factuelle + trop de traversées."""
        t = Tav()
        ctx = {
            "intent": {"type": "factual", "depth": "shallow"},
            "sentier_enrichments": [{} for _ in range(10)],
        }
        effects = t._compute_effects(ctx, "yashar")

        assert effects["applied"] is True
        assert len(effects["warnings"]) >= 1
        assert "Recentre" in effects["warnings"][0]

    def test_tav_detects_domain_drift(self):
        """Tav détecte un changement de domaine entre intent et route."""
        t = Tav()
        ctx = {
            "intent": {"type": "analytical", "depth": "medium"},
            "mochin": {"domain": "neuroscience"},
            "route_decision": _route_mock(domain="philosophie"),
        }
        effects = t._compute_effects(ctx, "yashar")

        assert effects["applied"] is True
        assert any("Dérive domaine" in w for w in effects["warnings"])

    def test_tav_warns_no_high_conf_memories(self):
        """Tav avertit si toutes les mémoires rappelées ont basse confiance."""
        t = Tav()
        low_mem = MagicMock()
        low_mem.confidence = 0.2
        ctx = {
            "intent": {"type": "factual", "depth": "medium"},
            "memories": [low_mem, low_mem, low_mem],
        }
        effects = t._compute_effects(ctx, "yashar")

        assert effects["applied"] is True
        assert any("haute confiance" in w for w in effects["warnings"])

    def test_tav_no_drift_normal_query(self):
        """Tav ne fait rien si la query est cohérente."""
        t = Tav()
        ctx = {
            "intent": {"type": "analytical", "depth": "deep"},
            "sentier_enrichments": [{} for _ in range(3)],
        }
        effects = t._compute_effects(ctx, "yashar")
        assert effects["applied"] is False


# ── Beth — exploration boost ─────────────────────────────────

class TestBethEffects:

    def test_beth_modifies_novelty_for_exploratory(self):
        """Beth abaisse novelty_threshold pour queries exploratoires."""
        b = Beth()
        ctx = {
            "intent": {"type": "explore", "depth": "deep"},
            "mochin": {"competence_score": 0.7},
        }
        effects = b._compute_effects(ctx, "yashar")

        assert effects["applied"] is True
        assert effects["ctx_additions"]["beth_exploration_boost"] is True
        # dagesh mode (competence >= 0.5) → delta = -0.05
        assert effects["module_modifiers"]["min_novelty_score"] == -0.05

    def test_beth_rafeh_bigger_delta(self):
        """Beth en mode rafeh (basse confiance) → delta plus grand."""
        b = Beth()
        b.mode = "rafeh"
        ctx = {
            "intent": {"type": "creative", "depth": "deep"},
            "mochin": {"competence_score": 0.3},
        }
        effects = b._compute_effects(ctx, "yashar")

        assert effects["applied"] is True
        assert effects["module_modifiers"]["min_novelty_score"] == -0.1

    def test_beth_no_effect_factual(self):
        """Beth ne fait rien pour une query factuelle."""
        b = Beth()
        ctx = {"intent": {"type": "factual", "depth": "shallow"}}
        effects = b._compute_effects(ctx, "yashar")
        assert effects["applied"] is False


# ── Teth — filtrage pré-jugement ─────────────────────────────

class TestTethEffects:

    def test_teth_filters_weak_explorations(self):
        """Teth filtre les explorations avec score < 0.3."""
        t = Teth()
        ctx = {
            "daemon_enrichment": {
                "analogies": [
                    {"text": "good", "score": 0.8},
                    {"text": "weak", "score": 0.1},
                    {"text": "ok", "score": 0.5},
                ],
                "explorations": [
                    {"text": "bad", "score": 0.05},
                ],
            },
        }
        effects = t._compute_effects(ctx, "yashar")

        assert effects["applied"] is True
        assert effects["ctx_additions"]["pre_filtered"] is True
        assert effects["ctx_additions"]["teth_filtered_count"] == 2
        assert effects["ctx_additions"]["teth_kept_count"] == 2

    def test_teth_no_effect_without_explorations(self):
        """Teth ne fait rien s'il n'y a pas d'explorations."""
        t = Teth()
        effects = t._compute_effects({}, "yashar")
        assert effects["applied"] is False


# ── Lamed — rejection patterns ───────────────────────────────

class TestLamedEffects:

    def test_lamed_extracts_rejection_patterns(self):
        """Lamed extrait les motifs de rejet pour Tiferet."""
        l = Lamed()
        ctx = {
            "autojudge_rejections": [
                {"reason": "Insuffisamment sourcé"},
                {"reason": "Confiance trop basse"},
            ],
        }
        effects = l._compute_effects(ctx, "yashar")

        assert effects["applied"] is True
        assert len(effects["ctx_additions"]["rejection_patterns"]) == 2
        assert effects["ctx_additions"]["lamed_active"] is True

    def test_lamed_captures_teth_filter_signal(self):
        """Lamed note que Teth a filtré des explorations faibles."""
        l = Lamed()
        ctx = {"teth_filtered_count": 3}
        effects = l._compute_effects(ctx, "yashar")

        assert effects["applied"] is True
        assert any("Teth" in p for p in effects["ctx_additions"]["rejection_patterns"])

    def test_lamed_no_effect_without_rejections(self):
        """Lamed ne fait rien sans rejets."""
        l = Lamed()
        effects = l._compute_effects({}, "yashar")
        assert effects["applied"] is False


# ── Ayin — alignement intention/compétence ───────────────────

class TestAyinEffects:

    def test_ayin_detects_misalignment(self):
        """Ayin détecte quand la compétence est insuffisante."""
        a = Ayin()
        ctx = {
            "route_decision": _route_mock(domain="physique_quantique", score=0.2),
            "intent": {"type": "analytical", "depth": "deep"},
        }
        effects = a._compute_effects(ctx, "yashar")

        assert effects["applied"] is True
        assert effects["ctx_additions"]["ayin_misalignment"] is True
        assert len(effects["warnings"]) >= 1
        assert "insuffisante" in effects["warnings"][0]

    def test_ayin_warns_deep_question_medium_competence(self):
        """Ayin avertit pour question profonde avec compétence moyenne."""
        a = Ayin()
        ctx = {
            "route_decision": _route_mock(domain="soufisme", score=0.5),
            "intent": {"type": "explore", "depth": "philosophical"},
        }
        effects = a._compute_effects(ctx, "yashar")

        assert effects["applied"] is True
        assert "nuancer" in effects["warnings"][0]

    def test_ayin_no_effect_high_competence(self):
        """Ayin ne fait rien si compétence suffisante."""
        a = Ayin()
        ctx = {
            "route_decision": _route_mock(domain="kabbale", score=0.85),
            "intent": {"type": "factual", "depth": "shallow"},
        }
        effects = a._compute_effects(ctx, "yashar")
        assert effects["applied"] is False


# ── Nun — alignement synthèse/intention ──────────────────────

class TestNunEffects:

    def test_nun_detects_alignment(self):
        """Nun confirme l'alignement synthèse/intention."""
        n = Nun()
        ctx = {
            "tiferet_diag": {"syntheses": 3},
            "intent": {"type": "analytical", "depth": "deep"},
        }
        effects = n._compute_effects(ctx, "yashar")

        assert effects["applied"] is True
        assert effects["ctx_additions"]["intent_alignment"] is True

    def test_nun_warns_no_intent(self):
        """Nun avertit si synthèse sans intention identifiée."""
        n = Nun()
        ctx = {
            "tiferet_diag": {"syntheses": 2},
            "intent": {"type": "", "depth": ""},
        }
        effects = n._compute_effects(ctx, "yashar")

        assert effects["applied"] is True
        assert effects["ctx_additions"]["intent_alignment"] is False
        assert len(effects["warnings"]) >= 1


# ── Daleth — insights pour Binah ─────────────────────────────

class TestDalethEffects:

    def test_daleth_passes_insights_dagesh(self):
        """Daleth en dagesh passe tous les insights à Binah."""
        d = Daleth()
        d.mode = "dagesh"
        ctx = {
            "daemon_enrichment": {
                "insights": [{"text": "a", "confidence": 0.9}, {"text": "b", "confidence": 0.4}],
            },
            "mochin": {"competence_score": 0.7},
        }
        effects = d._compute_effects(ctx, "yashar")

        assert effects["applied"] is True
        assert effects["ctx_additions"]["daleth_n_insights"] == 2
        assert effects["ctx_additions"]["daleth_mode"] == "dagesh"

    def test_daleth_filters_in_rafeh(self):
        """Daleth en rafeh ne garde que le meilleur insight."""
        d = Daleth()
        d.mode = "rafeh"
        ctx = {
            "daemon_enrichment": {
                "insights": [
                    {"text": "good", "confidence": 0.9},
                    {"text": "ok", "confidence": 0.5},
                ],
            },
            "mochin": {"competence_score": 0.3},
        }
        effects = d._compute_effects(ctx, "yashar")

        assert effects["applied"] is True
        assert effects["ctx_additions"]["daleth_n_insights"] == 1


# ── Routeur — application des effets ─────────────────────────

class TestRouterApplyEffects:

    def test_router_applies_ctx_additions(self):
        """Le routeur merge les ctx_additions dans le ctx."""
        router = SentierRouter()
        ctx = {"existing": True}
        effects = {
            "ctx_additions": {"recall_domain": "kabbale", "extra": 42},
            "module_modifiers": {},
            "warnings": [],
            "applied": True,
        }
        router._apply_effects(ctx, effects, "yesod")

        assert ctx["recall_domain"] == "kabbale"
        assert ctx["extra"] == 42
        assert ctx["existing"] is True

    def test_router_accumulates_warnings(self):
        """Le routeur accumule les warnings dans ctx['sentier_warnings']."""
        router = SentierRouter()
        ctx = {}
        effects = {
            "ctx_additions": {},
            "module_modifiers": {},
            "warnings": ["Recentre", "Dérive domaine"],
            "applied": True,
        }
        router._apply_effects(ctx, effects, "malkuth")

        assert ctx["sentier_warnings"] == ["Recentre", "Dérive domaine"]

    def test_router_accumulates_module_modifiers(self):
        """Le routeur stocke les module_modifiers pour application."""
        router = SentierRouter()
        ctx = {}
        effects = {
            "ctx_additions": {},
            "module_modifiers": {"min_novelty_score": -0.05},
            "warnings": [],
            "applied": True,
        }
        router._apply_effects(ctx, effects, "chokmah")

        assert ctx["_sentier_module_modifiers"]["chokmah"]["min_novelty_score"] == -0.05

    def test_router_apply_module_modifiers_to_tree(self):
        """apply_module_modifiers applique les deltas aux attributs des modules."""
        router = SentierRouter()

        module = MagicMock()
        module.min_novelty_score = 0.7
        tree = {"chokmah": module}

        ctx = {
            "_sentier_module_modifiers": {
                "chokmah": {"min_novelty_score": -0.05},
            },
        }

        n_applied = router.apply_module_modifiers(ctx, tree)
        assert n_applied == 1
        assert module.min_novelty_score == pytest.approx(0.65, abs=0.01)

    def test_router_no_effects_not_applied(self):
        """Le routeur n'applique rien si applied=False."""
        router = SentierRouter()
        ctx = {}
        effects = {
            "ctx_additions": {"should_not_appear": True},
            "module_modifiers": {},
            "warnings": [],
            "applied": False,
        }
        # _apply_effects est appelé uniquement si applied=True dans traverse()
        # Vérifions le comportement via traverse_quick
        # Le routeur vérifie effects.get("applied") avant d'appeler _apply_effects
        # Donc ici, si on l'appelle quand même, ça merge — c'est le routeur qui filtre
        # Le test vérifie le contrat du routeur via traverse()

        # Construire un sentier qui ne s'active pas
        from sentiers.beth import Beth
        b = Beth()
        ctx_test = {"intent": {"type": "factual", "depth": "shallow"}}
        b.traverse_quick(ctx_test, "yashar")

        # Les effets ne doivent pas être appliqués (applied=False)
        effects_after = ctx_test.get("_last_sentier_effects", {})
        assert effects_after.get("applied") is False
        # Pas de beth_exploration_boost
        assert "beth_exploration_boost" not in ctx_test


# ── Shin — feu rapide ──────────────────────────────────────

class TestShinEffects:

    def test_shin_activates_on_short_factual(self):
        from sentiers.shin import Shin
        s = Shin()
        ctx = {"query": "Qu'est-ce?", "intent": {"type": "factuel", "depth": "yetzirah"}}
        effects = s._compute_effects(ctx, "yashar")
        assert effects["applied"] is True
        assert effects["ctx_additions"]["shin_fire_mode"] is True

    def test_shin_no_effect_on_long_query(self):
        from sentiers.shin import Shin
        s = Shin()
        ctx = {"query": "x " * 40, "intent": {"type": "analytical", "depth": "briah"}}
        effects = s._compute_effects(ctx, "yashar")
        assert effects["applied"] is False


# ── Resh — persist policy ──────────────────────────────────

class TestReshEffects:

    def test_resh_activates_with_memories(self):
        from sentiers.resh import Resh
        r = Resh()
        mem = MagicMock()
        mem.confidence = 0.8
        ctx = {"memories": [mem, mem]}
        effects = r._compute_effects(ctx, "yashar")
        assert effects["applied"] is True
        assert "resh_persist_mode" in effects["ctx_additions"]

    def test_resh_rafeh_warns_low_confidence(self):
        from sentiers.resh import Resh
        r = Resh()
        r.mode = "rafeh"
        low = MagicMock()
        low.confidence = 0.2
        ctx = {"memories": [low, low, low, low]}
        effects = r._compute_effects(ctx, "yashar")
        assert effects["applied"] is True
        assert len(effects["warnings"]) >= 1

    def test_resh_no_effect_without_memories(self):
        from sentiers.resh import Resh
        r = Resh()
        effects = r._compute_effects({}, "yashar")
        assert effects["applied"] is False


# ── Tsadi — intent-guided recall ───────────────────────────

class TestTsadiEffects:

    def test_tsadi_activates_with_intent(self):
        from sentiers.tsadi import Tsadi
        t = Tsadi()
        ctx = {"intent": {"type": "causal", "depth": "briah"}}
        effects = t._compute_effects(ctx, "yashar")
        assert effects["applied"] is True
        assert effects["ctx_additions"]["tsadi_intent_guided_recall"] is True
        assert effects["ctx_additions"]["tsadi_deep_fixation"] is True

    def test_tsadi_no_effect_on_greeting(self):
        from sentiers.tsadi import Tsadi
        t = Tsadi()
        ctx = {"intent": {"type": "greeting", "depth": ""}}
        effects = t._compute_effects(ctx, "yashar")
        assert effects["applied"] is False


# ── Peh — validation mode ──────────────────────────────────

class TestPehEffects:

    def test_peh_dagesh_raises_threshold(self):
        from sentiers.peh import Peh
        p = Peh()
        p.mode = "dagesh"
        ctx = {"gevurah_feedback": {"score": 0.6}}
        effects = p._compute_effects(ctx, "yashar")
        assert effects["applied"] is True
        assert effects["module_modifiers"]["confidence_threshold"] > 0

    def test_peh_rafeh_lowers_threshold(self):
        from sentiers.peh import Peh
        p = Peh()
        p.mode = "rafeh"
        ctx = {"gevurah_feedback": {"score": 0.4}}
        effects = p._compute_effects(ctx, "yashar")
        assert effects["applied"] is True
        assert effects["module_modifiers"]["confidence_threshold"] < 0

    def test_peh_no_effect_without_feedback(self):
        from sentiers.peh import Peh
        p = Peh()
        effects = p._compute_effects({}, "yashar")
        assert effects["applied"] is False


# ── Samekh — introspection ─────────────────────────────────

class TestSamekhEffects:

    def test_samekh_activates_with_diag(self):
        from sentiers.samekh import Samekh
        s = Samekh()
        ctx = {"tiferet_diag": {"tensions": 3}}
        effects = s._compute_effects(ctx, "yashar")
        assert effects["applied"] is True
        assert effects["ctx_additions"]["samekh_introspection"] is True

    def test_samekh_warns_many_tensions(self):
        from sentiers.samekh import Samekh
        s = Samekh()
        ctx = {"tiferet_diag": {"tensions": 10}}
        effects = s._compute_effects(ctx, "yashar")
        assert effects["applied"] is True
        assert len(effects["warnings"]) >= 1

    def test_samekh_no_effect_without_diag(self):
        from sentiers.samekh import Samekh
        s = Samekh()
        effects = s._compute_effects({}, "yashar")
        assert effects["applied"] is False


# ── Kaph — retention mode ──────────────────────────────────

class TestKaphEffects:

    def test_kaph_dagesh_keeps_all(self):
        from sentiers.kaph import Kaph
        k = Kaph()
        k.mode = "dagesh"
        ctx = {"daemon_enrichment": {"analogies": [{"score": 0.2}, {"score": 0.8}]}}
        effects = k._compute_effects(ctx, "yashar")
        assert effects["applied"] is True
        assert effects["ctx_additions"]["kaph_retained"] == 2

    def test_kaph_rafeh_prunes_weak(self):
        from sentiers.kaph import Kaph
        k = Kaph()
        k.mode = "rafeh"
        ctx = {"daemon_enrichment": {"analogies": [{"score": 0.2}, {"score": 0.8}]}}
        effects = k._compute_effects(ctx, "yashar")
        assert effects["applied"] is True
        assert effects["ctx_additions"]["kaph_retained"] == 1
        assert effects["ctx_additions"]["kaph_pruned"] == 1

    def test_kaph_no_effect_without_analogies(self):
        from sentiers.kaph import Kaph
        k = Kaph()
        effects = k._compute_effects({}, "yashar")
        assert effects["applied"] is False


# ── Yod — data signal ─────────────────────────────────────

class TestYodEffects:

    def test_yod_signals_data(self):
        from sentiers.yod import Yod
        y = Yod()
        ctx = {"daemon_enrichment": {"analogies": [{"a": 1}], "explorations": [{"b": 2}]}}
        effects = y._compute_effects(ctx, "yashar")
        assert effects["applied"] is True
        assert effects["ctx_additions"]["yod_data_count"] == 2

    def test_yod_no_effect_empty(self):
        from sentiers.yod import Yod
        y = Yod()
        effects = y._compute_effects({"daemon_enrichment": {"analogies": [], "explorations": []}}, "yashar")
        assert effects["applied"] is False


# ── Cheth — causal constraints ─────────────────────────────

class TestChethEffects:

    def test_cheth_signals_constraints(self):
        from sentiers.cheth import Cheth
        c = Cheth()
        ctx = {"daemon_enrichment": {"binah_causal": [{"claim": "A→B"}]}}
        effects = c._compute_effects(ctx, "yashar")
        assert effects["applied"] is True
        assert effects["ctx_additions"]["cheth_causal_constraints"] is True

    def test_cheth_no_effect_without_causal(self):
        from sentiers.cheth import Cheth
        c = Cheth()
        effects = c._compute_effects({}, "yashar")
        assert effects["applied"] is False


# ── Zayin — anomaly detection ──────────────────────────────

class TestZayinEffects:

    def test_zayin_warns_unsynthesized(self):
        from sentiers.zayin import Zayin
        z = Zayin()
        ctx = {"daemon_enrichment": {"binah_causal": [{"x": 1}], "tiferet_syntheses": []}}
        effects = z._compute_effects(ctx, "yashar")
        assert effects["applied"] is True
        assert len(effects["warnings"]) >= 1
        assert effects["ctx_additions"]["zayin_unsynthesized_claims"] is True

    def test_zayin_no_effect_empty(self):
        from sentiers.zayin import Zayin
        z = Zayin()
        effects = z._compute_effects({"daemon_enrichment": {"binah_causal": [], "tiferet_syntheses": []}}, "yashar")
        assert effects["applied"] is False


# ── Vav — insight feed ─────────────────────────────────────

class TestVavEffects:

    def test_vav_signals_insights(self):
        from sentiers.vav import Vav
        v = Vav()
        ctx = {"daemon_enrichment": {"chokmah_insights": [{"i": 1}, {"i": 2}]}}
        effects = v._compute_effects(ctx, "yashar")
        assert effects["applied"] is True
        assert effects["ctx_additions"]["vav_n_insights"] == 2

    def test_vav_no_effect_without_insights(self):
        from sentiers.vav import Vav
        v = Vav()
        effects = v._compute_effects({}, "yashar")
        assert effects["applied"] is False


# ── Heh — direct perception ───────────────────────────────

class TestHehEffects:

    def test_heh_injects_best_insight(self):
        from sentiers.heh import Heh
        h = Heh()
        ctx = {"daemon_enrichment": {"chokmah_insights": [
            {"text": "low", "confidence": 0.2},
            {"text": "high", "confidence": 0.85},
        ]}}
        effects = h._compute_effects(ctx, "yashar")
        assert effects["applied"] is True
        assert effects["ctx_additions"]["heh_insight_confidence"] == pytest.approx(0.85, abs=0.01)

    def test_heh_no_effect_low_confidence(self):
        from sentiers.heh import Heh
        h = Heh()
        ctx = {"daemon_enrichment": {"chokmah_insights": [{"text": "x", "confidence": 0.1}]}}
        effects = h._compute_effects(ctx, "yashar")
        assert effects["applied"] is False


# ── Gimel — cache strategy ─────────────────────────────────

class TestGimelEffects:

    def test_gimel_activates_on_deep(self):
        from sentiers.gimel import Gimel
        g = Gimel()
        ctx = {"intent": {"type": "causal", "depth": "briah"}}
        effects = g._compute_effects(ctx, "yashar")
        assert effects["applied"] is True
        assert "gimel_cache_strategy" in effects["ctx_additions"]

    def test_gimel_no_effect_shallow(self):
        from sentiers.gimel import Gimel
        g = Gimel()
        ctx = {"intent": {"type": "factual", "depth": "yetzirah"}}
        effects = g._compute_effects(ctx, "yashar")
        assert effects["applied"] is False


# ── Aleph — balance ────────────────────────────────────────

class TestAlephEffects:

    def test_aleph_detects_imbalance(self):
        from sentiers.aleph import Aleph
        a = Aleph()
        ctx = {"sentier_modifiers": {"speed": 0.9, "patience": 0.1, "aggressiveness": 0.8}}
        effects = a._compute_effects(ctx, "yashar")
        assert effects["applied"] is True
        assert effects["ctx_additions"]["aleph_balance_correction"] is True

    def test_aleph_no_effect_balanced(self):
        from sentiers.aleph import Aleph
        a = Aleph()
        ctx = {"sentier_modifiers": {"speed": 0.5, "patience": 0.5}}
        effects = a._compute_effects(ctx, "yashar")
        assert effects["applied"] is False


# ── Mem — validation flow ──────────────────────────────────

class TestMemEffects:

    def test_mem_signals_validation_flow(self):
        from sentiers.mem import Mem
        m = Mem()
        ctx = {"gevurah_feedback": {"score": 0.7, "passed": True}}
        effects = m._compute_effects(ctx, "yashar")
        assert effects["applied"] is True
        assert effects["ctx_additions"]["mem_validation_flow"] is True

    def test_mem_no_effect_without_feedback(self):
        from sentiers.mem import Mem
        m = Mem()
        effects = m._compute_effects({}, "yashar")
        assert effects["applied"] is False
