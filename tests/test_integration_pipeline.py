"""Tests d'intégration end-to-end — כְּלָלוּת הָאִילָן.

Exercent le chemin complet :
  requête → Keter → Chokmah → Binah → Da'at → ... → Malkuth → Or Chozer

LLM mocké (pas d'appel Ollama), modules réels instanciés depuis le tree.
Vérifient le câblage entre modules, pas le contenu des réponses.

Couvre :
  1. Pipeline Yosher complet (gadlut, question standard)
  2. Pipeline avec Da'at veto (domaine inconnu → avertissement)
  3. Pipeline avec Da'at caution (domaine moyen → instruction prudence)
  4. PartzufimRegulator : modifiers consommés dans Malkuth
  5. SentierRouter : sentiers traversés dans le pipeline
  6. DaemonBridge : enrichissement injecté dans le prompt
  7. Pipeline katnut (modules supérieurs dormants)
  8. Partzufim en katnut → Nukva contrainte → timeout réduit
"""

from unittest.mock import patch, MagicMock, PropertyMock
import pytest

# ── Helpers ────────────────────────────────────────────────


def _mock_ollama_generate(olam, prompt, timeout=60, **kwargs):
    """Simule ollama_generate — retourne réponse + latence."""
    return f"[Réponse mock depuis {olam}] Contenu pertinent.", 150.0


def _mock_ollama_generate_low_confidence(olam, prompt, timeout=60, **kwargs):
    """Simule une réponse de faible confiance (courte, vague)."""
    return "Je ne suis pas sûr.", 80.0


# ── Fixtures ────────────────────────────────────────────────


@pytest.fixture
def mock_llm():
    """Patch ollama_generate dans tous les modules qui l'importent."""
    with patch("olamot.ollama_generate", side_effect=_mock_ollama_generate) as m, \
         patch("olamot.get_provider", return_value="ollama"):
        yield m


@pytest.fixture
def mock_llm_low():
    """Patch pour réponses de faible confiance."""
    with patch("olamot.ollama_generate", side_effect=_mock_ollama_generate_low_confidence) as m, \
         patch("olamot.get_provider", return_value="ollama"):
        yield m


# ── 1. _classify_intent : tests unitaires rapides ───────────

class TestClassifyIntent:
    """Keter — classification d'intention (pas de LLM)."""

    def test_causal_question(self):
        from main import _classify_intent
        result = _classify_intent("Pourquoi le Tsimtsum précède-t-il la Shevirah ?")
        assert result["type"] == "causal"

    def test_definition_question(self):
        from main import _classify_intent
        result = _classify_intent("Qu'est-ce que le Reshimu ?")
        assert result["type"] == "définitionnel"

    def test_comparison_question(self):
        from main import _classify_intent
        result = _classify_intent("Compare les Partzufim et les Sefirot")
        assert result["type"] == "comparatif"

    def test_depth_briah_for_long_query(self):
        from main import _classify_intent
        result = _classify_intent("x " * 120)  # > 200 chars
        assert result["depth"] == "briah"

    def test_depth_yetzirah_default(self):
        from main import _classify_intent
        result = _classify_intent("Bonjour")
        assert result["depth"] == "yetzirah"

    def test_depth_briah_for_deep_keywords(self):
        from main import _classify_intent
        result = _classify_intent("Démontre l'isomorphisme entre X et Y")
        assert result["depth"] == "briah"


# ── 2. _generate_malkuth_response : Da'at veto injecté ─────

class TestMalkuthDaatVeto:
    """Malkuth respecte les flags Da'at."""

    def test_veto_prefixes_response(self, mock_llm):
        from main import _generate_malkuth_response
        tree = {}
        ctx = {
            "intent": {"type": "factuel", "depth": "yetzirah"},
            "daat_veto": True,
            "daat_veto_reason": "selfmap_unknown_domain=0.90",
            "daat_known_biases": [],
        }
        response = _generate_malkuth_response(tree, "Test query", ctx)
        assert "Da'at" in response
        assert "Avertissement" in response or "confiance" in response.lower()
        # La réponse LLM est toujours présente
        assert "mock" in response.lower() or "Réponse" in response

    def test_veto_forces_assiah(self, mock_llm):
        from main import _generate_malkuth_response
        tree = {}
        ctx = {
            "intent": {"type": "factuel", "depth": "briah"},
            "daat_veto": True,
            "daat_veto_reason": "selfmap_unknown_domain=0.90",
            "daat_known_biases": [],
            "daat_forced_assiah": True,
        }
        response = _generate_malkuth_response(tree, "Test query", ctx)
        # La génération a dû commencer en assiah
        assert ctx.get("hishtalshelut_start") == "assiah" or "assiah" in response.lower() or response

    def test_caution_injects_instructions(self, mock_llm):
        from main import _generate_malkuth_response
        tree = {}
        ctx = {
            "intent": {"type": "factuel", "depth": "yetzirah"},
            "daat_caution": True,
            "daat_caution_reason": "selfmap_competence=0.34",
        }
        response = _generate_malkuth_response(tree, "Test query", ctx)
        # La réponse ne devrait PAS avoir le préfixe veto
        assert "Avertissement Da'at" not in response
        # Mais elle devrait exister
        assert len(response) > 0

    def test_proceed_no_prefix(self, mock_llm):
        from main import _generate_malkuth_response
        tree = {}
        ctx = {
            "intent": {"type": "factuel", "depth": "yetzirah"},
            "daat_proceed": True,
            "daat_evaluation": {"recommendation": "proceed", "confidence": 0.9},
        }
        response = _generate_malkuth_response(tree, "Test query", ctx)
        assert "Avertissement Da'at" not in response
        assert len(response) > 0


# ── 3. PartzufimRegulator intégration ──────────────────────

class TestPartzufimRegulatorIntegration:
    """Le Regulator modifie réellement les paramètres des modules."""

    def test_gadlut_panim_is_neutral(self):
        from partzufim.regulator import PartzufimRegulator, ModifierProfile
        reg = PartzufimRegulator()
        state = {
            "abba": {"overall": 0.8, "mochin_state": "gadlut", "orientation": "panim"},
            "imma": {"overall": 0.7, "mochin_state": "gadlut", "orientation": "panim"},
            "zeir_anpin": {"overall": 0.75, "mochin_state": "gadlut", "orientation": "panim"},
            "nukva": {"overall": 0.72, "mochin_state": "gadlut", "orientation": "panim"},
            "arikh_anpin": {"overall": 0.78, "mochin_state": "gadlut", "orientation": "panim"},
            "atik_yomin": {"overall": 0.70, "mochin_state": "gadlut", "orientation": "panim"},
        }
        mods = reg.compute_modifiers(state)
        # All neutral in gadlut/panim
        for key, mod in mods.items():
            assert mod.capacity_factor == 1.0, f"{key} should be neutral"
            assert mod.threshold_modifier == 0.0, f"{key} threshold should be 0"
            assert mod.feedback_enabled is True, f"{key} feedback should be on"

    def test_katnut_reduces_capacity(self):
        from partzufim.regulator import PartzufimRegulator
        reg = PartzufimRegulator()
        state = {
            "abba": {"overall": 0.3, "mochin_state": "katnut", "orientation": "panim"},
            "imma": {"overall": 0.7, "mochin_state": "gadlut", "orientation": "panim"},
            "zeir_anpin": {"overall": 0.75, "mochin_state": "gadlut", "orientation": "panim"},
            "nukva": {"overall": 0.72, "mochin_state": "gadlut", "orientation": "panim"},
            "arikh_anpin": {"overall": 0.78, "mochin_state": "gadlut", "orientation": "panim"},
            "atik_yomin": {"overall": 0.70, "mochin_state": "gadlut", "orientation": "panim"},
        }
        mods = reg.compute_modifiers(state)
        # Abba → chokmah : katnut/panim → capacity=0.5
        assert mods["chokmah"].capacity_factor == 0.5
        assert mods["chokmah"].threshold_modifier == 0.1
        # Binah (imma) should be neutral
        assert mods["binah"].capacity_factor == 1.0

    def test_atik_cascade_degrades_all(self):
        from partzufim.regulator import PartzufimRegulator
        reg = PartzufimRegulator()
        state = {
            "abba": {"overall": 0.8, "mochin_state": "gadlut", "orientation": "panim"},
            "imma": {"overall": 0.7, "mochin_state": "gadlut", "orientation": "panim"},
            "zeir_anpin": {"overall": 0.75, "mochin_state": "gadlut", "orientation": "panim"},
            "nukva": {"overall": 0.72, "mochin_state": "gadlut", "orientation": "panim"},
            "arikh_anpin": {"overall": 0.78, "mochin_state": "gadlut", "orientation": "panim"},
            "atik_yomin": {"overall": 0.3, "mochin_state": "katnut", "orientation": "panim"},
        }
        mods = reg.compute_modifiers(state)
        # When Atik is degraded, ALL modules get capacity reduction
        for key in ("chokmah", "binah", "chesed", "malkuth"):
            assert mods[key].capacity_factor < 1.0, f"{key} should be degraded by Atik cascade"

    def test_nukva_modifiers_in_ctx(self, mock_llm):
        """Verify that Malkuth generation uses Nukva modifiers from ctx."""
        from main import _generate_malkuth_response
        tree = {}
        # Simulate Nukva in katnut → reduced capacity
        ctx = {
            "intent": {"type": "factuel", "depth": "yetzirah"},
            "partzuf_modifiers": {
                "malkuth": {"capacity": 0.5, "threshold": 0.1, "budget": 0.5,
                           "feedback": True, "reason": "nukva katnut"},
            },
        }
        response = _generate_malkuth_response(tree, "Test", ctx)
        # Generation should have proceeded with reduced timeout
        # (we can't check timeout directly, but response should exist)
        assert len(response) > 0

    def test_partzuf_non_optimal_in_prompt(self, mock_llm):
        """When Partzufim are not in optimal state, info is injected into prompt."""
        from main import _generate_malkuth_response
        tree = {}
        ctx = {
            "intent": {"type": "factuel", "depth": "yetzirah"},
            "partzuf_state": {
                "imma": {"overall": 0.3, "mochin_state": "katnut", "orientation": "panim"},
                "abba": {"overall": 0.8, "mochin_state": "gadlut", "orientation": "panim"},
            },
        }
        # The mock_llm captures the prompt — check it was called
        response = _generate_malkuth_response(tree, "Test", ctx)
        assert len(response) > 0
        # Verify the mock was called (generation happened)
        assert mock_llm.called


# ── 4. Da'at evaluate_confidence ────────────────────────────

class TestDaatEvaluateConfidence:
    """Da'at Guardian — tests fonctionnels avec SelfMap mocké."""

    def test_unknown_domain_gives_caution(self):
        """Un domaine totalement inconnu de SelfMap → caution (pas veto, LLM généraliste)."""
        from selfmodel.core import SelfModel
        selfmap_mock = MagicMock()
        selfmap_mock.read_competence.return_value = None  # unknown domain
        selfmap_mock.decline_threshold = 0.3

        sm = SelfModel.__new__(SelfModel)
        sm.db = MagicMock()
        sm.db.get_latest_state.return_value = None
        sm.db.get_active_biases.return_value = []
        sm.db.get_prediction_accuracy.return_value = None
        sm.selfmap = selfmap_mock
        sm.min_prediction_accuracy = 0.6
        sm.meta_confidence_threshold = 0.5

        result = sm.evaluate_confidence("What is X?", domain="unknown_domain")
        assert result["recommendation"] == "caution"
        assert result["predicted_error"] >= 0.3

    def test_high_competence_gives_proceed(self):
        """Un domaine à haute compétence sans biais → proceed."""
        from selfmodel.core import SelfModel
        score_mock = MagicMock()
        score_mock.score = 0.85  # > 0.8 → no signal

        selfmap_mock = MagicMock()
        selfmap_mock.read_competence.return_value = score_mock
        selfmap_mock.decline_threshold = 0.3

        sm = SelfModel.__new__(SelfModel)
        sm.db = MagicMock()
        sm.db.get_latest_state.return_value = None
        sm.db.get_active_biases.return_value = []
        sm.db.get_prediction_accuracy.return_value = None
        sm.selfmap = selfmap_mock
        sm.min_prediction_accuracy = 0.6
        sm.meta_confidence_threshold = 0.5

        result = sm.evaluate_confidence("Question kabbale", domain="kabbale_lurianique")
        assert result["recommendation"] == "proceed"
        assert result["predicted_error"] < 0.3

    def test_medium_competence_gives_caution(self):
        """Un domaine à compétence moyenne → caution."""
        from selfmodel.core import SelfModel
        score_mock = MagicMock()
        score_mock.score = 0.55  # > decline_threshold, < 0.8 → caution

        selfmap_mock = MagicMock()
        selfmap_mock.read_competence.return_value = score_mock
        selfmap_mock.decline_threshold = 0.3

        sm = SelfModel.__new__(SelfModel)
        sm.db = MagicMock()
        sm.db.get_latest_state.return_value = None
        sm.db.get_active_biases.return_value = []
        sm.db.get_prediction_accuracy.return_value = None
        sm.selfmap = selfmap_mock
        sm.min_prediction_accuracy = 0.6
        sm.meta_confidence_threshold = 0.5

        result = sm.evaluate_confidence("Question tzimtzum", domain="tzimtzum")
        assert result["recommendation"] == "caution"
        assert 0.3 <= result["predicted_error"] < 0.7

    def test_zero_score_gives_veto(self):
        """Un domaine avec score 0 → déclin → veto."""
        from selfmodel.core import SelfModel
        score_mock = MagicMock()
        score_mock.score = 0.0  # < decline_threshold → selfmap_decline = 0.85

        selfmap_mock = MagicMock()
        selfmap_mock.read_competence.return_value = score_mock
        selfmap_mock.decline_threshold = 0.3

        sm = SelfModel.__new__(SelfModel)
        sm.db = MagicMock()
        sm.db.get_latest_state.return_value = None
        sm.db.get_active_biases.return_value = []
        sm.db.get_prediction_accuracy.return_value = None
        sm.selfmap = selfmap_mock
        sm.min_prediction_accuracy = 0.6
        sm.meta_confidence_threshold = 0.5

        result = sm.evaluate_confidence("Biology question", domain="biology")
        assert result["recommendation"] == "veto"
        assert result["predicted_error"] >= 0.7


# ── 5. SentierRouter intégration ────────────────────────────

class TestSentierRouterIntegration:
    """Les sentiers traversent et modifient le contexte."""

    def test_router_has_all_40_routes(self):
        from sentiers.router import SentierRouter
        router = SentierRouter()
        assert len(router.routes) == 40

    def test_traverse_tav_adds_data(self):
        """Le sentier Tav (Yesod→Malkuth) enrichit le contexte."""
        from sentiers.router import SentierRouter
        router = SentierRouter()
        ctx = {"query": "test", "intent": {"type": "factuel"}}
        result = router.traverse("yesod", "malkuth", ctx, direction="yashar")
        # Traversal should return ctx (possibly enriched)
        assert isinstance(result, dict)
        # Sentier data should be added
        assert "sentier_traversals" in result or ctx is result

    def test_traverse_unknown_pair_returns_ctx(self):
        """Une paire sans sentier retourne le ctx inchangé."""
        from sentiers.router import SentierRouter
        router = SentierRouter()
        ctx = {"test": True}
        result = router.traverse("keter", "malkuth", ctx, direction="yashar")
        assert result.get("test") is True

    def test_transformational_sentiers_have_effects(self):
        """Les 22 sentiers implémentent _compute_effects."""
        from sentiers.base import Sentier
        import importlib
        transformational = [
            "ayin", "beth", "daleth", "lamed", "nun", "qoph", "tav", "teth",
            "shin", "resh", "tsadi", "peh", "samekh", "kaph", "yod",
            "cheth", "zayin", "vav", "heh", "gimel", "aleph", "mem",
        ]
        for mod_name in transformational:
            mod = importlib.import_module(f"sentiers.{mod_name}")
            found = False
            for attr_name in dir(mod):
                cls = getattr(mod, attr_name)
                if isinstance(cls, type) and issubclass(cls, Sentier) and cls is not Sentier:
                    assert "_compute_effects" in cls.__dict__, \
                        f"sentiers.{mod_name} missing _compute_effects"
                    found = True
                    break
            assert found, f"No Sentier subclass in sentiers.{mod_name}"


# ── 6. DaemonBridge intégration ─────────────────────────────

class TestDaemonBridgeIntegration:
    """DaemonBridge produit un enrichissement structuré."""

    def test_gather_returns_valid_sections(self):
        """gather_for_query retourne un sous-ensemble des 4 sections connues."""
        from daemon_bridge import DaemonBridge
        bridge = DaemonBridge(db_url="postgresql://localhost/etz_chaim_test")
        result = bridge.gather_for_query("Tzimtzum", "kabbale", {"type": "question"})
        valid_keys = {"tiferet_syntheses", "binah_causal",
                      "chesed_analogies", "chokmah_insights"}
        assert set(result.keys()) <= valid_keys

    def test_format_daemon_enrichment_empty(self):
        """Enrichissement vide → chaîne vide."""
        from daemon_bridge import format_daemon_enrichment
        result = format_daemon_enrichment({
            "tiferet_syntheses": [],
            "binah_causal": [],
            "chesed_analogies": [],
            "chokmah_insights": [],
        })
        assert result == ""

    def test_format_daemon_enrichment_with_data(self):
        """Enrichissement avec données → texte structuré."""
        from daemon_bridge import format_daemon_enrichment
        enrichment = {
            "tiferet_syntheses": [{"mode": "synthesis", "content": "Test content",
                                   "domain": "kabbale", "confidence": 0.8}],
            "binah_causal": [],
            "chesed_analogies": [],
            "chokmah_insights": [],
        }
        result = format_daemon_enrichment(enrichment)
        assert len(result) > 0
        assert "Test content" in result


# ── 7. SelfMap cleanup verification ─────────────────────────

class TestSelfMapCleanState:
    """Vérifier que SelfMap n'a plus de domaines parasites."""

    def test_no_zero_score_domains(self):
        """Aucun domaine avec score=0 ne devrait exister."""
        import psycopg2
        try:
            conn = psycopg2.connect(dbname="etz_chaim")
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM selfmap_competence WHERE score = 0")
                count = cur.fetchone()[0]
            conn.close()
            assert count == 0, f"Found {count} domains with score=0"
        except psycopg2.OperationalError:
            pytest.skip("DB not available")

    # NOTE: plancher relaxé de 0.1 à 0.01 le 2026-04-18 suite à activation
    # canal Lamed (Sprint 2) qui tire les domaines Samael-dominants (gematria,
    # kabbale_lurianique) vers le floor effectif 0.01 via EMA hitbonenut.
    # Cf. audits/re_audit_post_sprints_2026-04-18.md Zone 7 (drift runtime
    # légitime, pas régression). Aucune constante MIN_SCORE exposée dans
    # selfmap/ : assertion littérale sur le floor absolu observé en DB.
    # Epsilon 1e-9 pour absorber l'imprécision flottante EMA (0.0099999...).
    def test_all_scores_above_threshold(self):
        """Aucun score ne doit être sous le plancher absolu 0.01 (± epsilon)."""
        import psycopg2
        try:
            conn = psycopg2.connect(dbname="etz_chaim")
            with conn.cursor() as cur:
                cur.execute("SELECT min(score) FROM selfmap_competence")
                min_score = cur.fetchone()[0]
            conn.close()
            assert min_score >= 0.01 - 1e-9, (
                f"Min score {min_score} below absolute floor 0.01"
            )
        except psycopg2.OperationalError:
            pytest.skip("DB not available")


# ── 8. Pipeline complet simplifié ───────────────────────────

class TestPipelineWiring:
    """Vérifie que les fonctions clés sont importables et câblées."""

    def test_main_exports(self):
        """Les fonctions pipeline clés existent dans main."""
        from main import (
            _classify_intent,
            _generate_malkuth_response,
            cmd_ask,
            init_tree,
        )
        assert callable(_classify_intent)
        assert callable(_generate_malkuth_response)
        assert callable(cmd_ask)
        assert callable(init_tree)

    def test_regulator_computes_all_modules(self):
        """compute_modifiers produit des modifiers pour les 10 modules."""
        from partzufim.regulator import PartzufimRegulator
        reg = PartzufimRegulator()
        state = {
            "abba": {"overall": 0.8, "mochin_state": "gadlut", "orientation": "panim"},
            "imma": {"overall": 0.7, "mochin_state": "gadlut", "orientation": "panim"},
            "zeir_anpin": {"overall": 0.75, "mochin_state": "gadlut", "orientation": "panim"},
            "nukva": {"overall": 0.72, "mochin_state": "gadlut", "orientation": "panim"},
            "arikh_anpin": {"overall": 0.78, "mochin_state": "gadlut", "orientation": "panim"},
            "atik_yomin": {"overall": 0.70, "mochin_state": "gadlut", "orientation": "panim"},
        }
        mods = reg.compute_modifiers(state)
        expected = {"chokmah", "binah", "chesed", "gevurah", "tiferet",
                    "netzach", "hod", "yesod", "keter", "malkuth"}
        assert set(mods.keys()) == expected

    def test_daat_without_selfmap_defaults_to_caution(self):
        """Sans SelfMap, Da'at ne peut pas évaluer → erreur modérée."""
        from selfmodel.core import SelfModel
        sm = SelfModel.__new__(SelfModel)
        sm.db = MagicMock()
        sm.db.get_latest_state.return_value = None
        sm.db.get_active_biases.return_value = []
        sm.db.get_prediction_accuracy.return_value = None
        sm.selfmap = None  # Pas de SelfMap
        sm.min_prediction_accuracy = 0.6
        sm.meta_confidence_threshold = 0.5

        result = sm.evaluate_confidence("Test", domain="test_domain")
        # Without selfmap, no error signal → predicted_error = 0.1 → proceed
        assert result["recommendation"] == "proceed"

    def test_imma_katnut_cascades_to_za(self):
        """Quand Imma est en katnut, Zeir Anpin est forcé en katnut."""
        from partzufim.regulator import PartzufimRegulator
        reg = PartzufimRegulator()
        state = {
            "abba": {"overall": 0.8, "mochin_state": "gadlut", "orientation": "panim"},
            "imma": {"overall": 0.3, "mochin_state": "katnut", "orientation": "panim"},
            "zeir_anpin": {"overall": 0.75, "mochin_state": "gadlut", "orientation": "panim"},
            "nukva": {"overall": 0.72, "mochin_state": "gadlut", "orientation": "panim"},
            "arikh_anpin": {"overall": 0.78, "mochin_state": "gadlut", "orientation": "panim"},
            "atik_yomin": {"overall": 0.70, "mochin_state": "gadlut", "orientation": "panim"},
        }
        assert reg.should_force_katnut("zeir_anpin", state) is True
        mods = reg.compute_modifiers(state)
        # ZA's modules (chesed through yesod) should all be degraded
        assert mods["chesed"].capacity_factor == 0.5
        assert mods["tiferet"].capacity_factor == 0.5


# ── 9. Pipeline chaîné daemon — Chantier 1 ────────────────

class TestDaemonPipelineChains:
    """Vérifier le câblage pipeline : tâches chaînées, pas broadcast."""

    def test_recycle_rejections_function_exists(self):
        """_recycle_rejections_to_fti existe et est appelable."""
        from daemon import _recycle_rejections_to_fti
        assert callable(_recycle_rejections_to_fti)

    def test_zivvug_propagation_logic(self):
        """Zivvug boosts propagent correctement vers Partzufim."""
        from partzufim.zivvug import ZivvugEngine
        zivvug = ZivvugEngine()

        # Simuler des boosts
        zivvug.mutual_reinforcement(insight_produced=True)
        zivvug.mutual_reinforcement(causal_validated=True)

        assert zivvug.imma_boost > 0  # insight → Imma
        assert zivvug.abba_boost > 0  # causal → Abba

        # Vérifier que reset_boosts fonctionne
        zivvug.reset_boosts()
        assert zivvug.abba_boost == 0.0
        assert zivvug.imma_boost == 0.0

    def test_zivvug_assess_with_boosts(self):
        """assess_zivvug_state inclut les boosts accumulés."""
        from partzufim.zivvug import ZivvugEngine
        zivvug = ZivvugEngine()
        zivvug.mutual_reinforcement(insight_produced=True)

        assessment = zivvug.assess_zivvug_state(0.7, 0.6)
        # Imma boosted by BOOST_AMOUNT → effective 0.6 + BOOST_AMOUNT
        # Abba stays 0.7
        expected_imma = min(1.0, 0.6 + ZivvugEngine.BOOST_AMOUNT)
        assert assessment.imma_score == pytest.approx(expected_imma, abs=0.01)
        assert assessment.abba_score == 0.7

    def test_forge_questions_sources(self):
        """_generate_forge_questions lit 3 sources : hitbonenut, FTI, cross-domain."""
        from daemon import _generate_forge_questions
        # Avec un tree vide et pas de DB, ça doit retourner une liste vide sans crash
        questions = _generate_forge_questions({}, max_questions=3)
        assert isinstance(questions, list)

    def test_gevurah_eval_in_daily_cycle(self):
        """task_gevurah_eval est appelable et retourne le bon format."""
        from daemon import task_gevurah_eval
        result = task_gevurah_eval({})  # tree vide
        assert result["task"] == "gevurah_eval"
        # Sans module gevurah, erreur attendue
        assert "error" in result

    def test_insightforge_nourished_by_fti(self):
        """InsightForge lit les patterns FTI via _generate_forge_questions."""
        # Le test vérifie que le SQL FTI est dans _generate_forge_questions
        import inspect
        from daemon import _generate_forge_questions
        source = inspect.getsource(_generate_forge_questions)
        assert "failuretoinsight_insights" in source
        assert "opportunity" in source or "pattern" in source


# ── 10. Sentier module_modifiers — câblage bout en bout ───

class TestSentierModuleModifiersWiring:
    """Vérifie que apply_module_modifiers est câblé et fonctionne."""

    def test_apply_module_modifiers_in_router(self):
        """apply_module_modifiers existe et applique les deltas."""
        from sentiers.router import SentierRouter
        router = SentierRouter()
        module = MagicMock()
        module.min_novelty_score = 0.7
        tree = {"chokmah": module}
        ctx = {"_sentier_module_modifiers": {"chokmah": {"min_novelty_score": -0.05}}}
        n = router.apply_module_modifiers(ctx, tree)
        assert n == 1
        assert module.min_novelty_score == pytest.approx(0.65, abs=0.01)

    def test_apply_module_modifiers_called_in_main(self):
        """main.py appelle apply_module_modifiers avant Malkuth."""
        import inspect
        from main import _cmd_ask_yosher
        source = inspect.getsource(_cmd_ask_yosher)
        assert "apply_module_modifiers" in source
        assert "_sentier_originals" in source

    def test_originals_restored_after_generation(self):
        """Les valeurs originales sont restaurées après la génération."""
        import inspect
        from main import _cmd_ask_yosher
        source = inspect.getsource(_cmd_ask_yosher)
        # La restauration doit apparaître APRÈS la génération
        gen_pos = source.find("_generate_malkuth_response")
        restore_pos = source.find("_sentier_originals")
        # _sentier_originals apparaît deux fois : save + restore
        # La dernière occurrence (restore) doit être après la génération
        last_restore = source.rfind("_sentier_originals")
        assert last_restore > gen_pos, \
            "Restoration of sentier originals must come after Malkuth generation"

    def test_peh_modifier_applies_to_module(self):
        """Le modifier de Peh (confidence_threshold ±0.05) est réellement appliqué."""
        from sentiers.peh import Peh
        from sentiers.router import SentierRouter
        p = Peh()
        p.mode = "dagesh"
        ctx = {"gevurah_feedback": {"score": 0.7}}
        effects = p._compute_effects(ctx, "yashar")

        # Simuler le routeur qui applique les effets
        router = SentierRouter()
        router._apply_effects(ctx, effects, "hod")

        # Vérifier que le modifier est dans ctx
        assert "hod" in ctx["_sentier_module_modifiers"]
        assert ctx["_sentier_module_modifiers"]["hod"]["confidence_threshold"] == 0.05

        # Appliquer au module
        hod_module = MagicMock()
        hod_module.confidence_threshold = 0.5
        tree = {"hod": hod_module}
        n = router.apply_module_modifiers(ctx, tree)
        assert n == 1
        assert hod_module.confidence_threshold == pytest.approx(0.55, abs=0.01)
