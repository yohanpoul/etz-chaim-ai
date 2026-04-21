"""Tests du HishtalshelutEngine — סֵדֶר הִשְׁתַּלְשְׁלוּת.

Couvre :
  - Constants et mappings (OLAMOT_DESCENDING, OLAM_HEBREW, etc.)
  - detect_world() — détection du monde d'entrée
  - _format_descent() — interpénétration Malkut↔Keter
  - descend() — chaîne de descente complète
  - ascend() — chaîne de remontée Or Chozer
  - get_chain_state() — état de la chaîne
  - Transitions et logging
  - DescentStep / AscentStep / DescentResult dataclasses
  - Edge cases : erreurs, mondes manquants, etc.
"""

import time
from unittest.mock import patch, MagicMock

import pytest

from hishtalshelut import (
    HishtalshelutEngine,
    OLAMOT_DESCENDING,
    OLAM_HEBREW,
    OLAM_SEPHIRAH,
    OLAM_TO_CHAIN,
    CHAIN_TO_OLAM,
    DescentStep,
    AscentStep,
    DescentResult,
)


# ── Helpers ──────────────────────────────────────────────────

def _fresh_state() -> dict:
    """Créer un _HISHTALSHELUT_STATE vierge."""
    return {
        "current_world": "assiah",
        "forced_world": None,
        "ascents": 0,
        "descents": 0,
        "highest_reached": "assiah",
        "log": [],
    }


def _olamot_chain() -> list[str]:
    """Chaîne ascendante comme dans main.py."""
    return ["assiah", "yetzirah", "briah", "atziluth"]


class MockYesod:
    """Stub Yesod avec remember()."""
    def __init__(self):
        self.remembered: list[dict] = []

    def remember(self, **kwargs):
        self.remembered.append(kwargs)

    def introspect(self):
        return MagicMock(total=100)

    def self_diagnose(self):
        return {"status": "ok"}


def _stub_tree() -> dict:
    """Arbre minimal avec un Yesod stub."""
    yesod = MockYesod()
    return {
        "yesod": yesod,
        "hod": MagicMock(self_diagnose=lambda: {"status": "ok"}),
        "malkuth": MagicMock(),
        "tiferet": MagicMock(),
        "binah": MagicMock(),
        "chokmah": MagicMock(),
        "keter": MagicMock(),
    }


def _make_engine(state=None) -> HishtalshelutEngine:
    """Créer un engine avec état frais."""
    return HishtalshelutEngine(
        state or _fresh_state(),
        _olamot_chain(),
    )


# ── Constants ────────────────────────────────────────────────

class TestConstants:

    def test_olamot_descending_count(self):
        assert len(OLAMOT_DESCENDING) == 4

    def test_olamot_descending_order(self):
        assert OLAMOT_DESCENDING == ("atzilut", "briah", "yetzirah", "assiah")

    def test_olam_hebrew_all_present(self):
        for w in OLAMOT_DESCENDING:
            assert w in OLAM_HEBREW
            assert len(OLAM_HEBREW[w]) > 0

    def test_olam_sephirah_all_present(self):
        for w in OLAMOT_DESCENDING:
            assert w in OLAM_SEPHIRAH

    def test_olam_sephirah_values(self):
        assert OLAM_SEPHIRAH["atzilut"] == "keter"
        assert OLAM_SEPHIRAH["briah"] == "binah"
        assert OLAM_SEPHIRAH["yetzirah"] == "tiferet"
        assert OLAM_SEPHIRAH["assiah"] == "malkuth"

    def test_olam_to_chain_all_present(self):
        for w in OLAMOT_DESCENDING:
            assert w in OLAM_TO_CHAIN

    def test_chain_to_olam_inverse(self):
        for w in OLAMOT_DESCENDING:
            chain = OLAM_TO_CHAIN[w]
            assert CHAIN_TO_OLAM[chain] == w

    def test_atzilut_chain_name(self):
        """main.py utilise 'atziluth' (avec h), nous 'atzilut'."""
        assert OLAM_TO_CHAIN["atzilut"] == "atziluth"


# ── detect_world ─────────────────────────────────────────────

class TestDetectWorld:

    def test_strategic_query(self):
        engine = _make_engine()
        world = engine.detect_world(
            "Quelle est la stratégie et la vision globale de la mission ?"
        )
        assert world == "atzilut"

    def test_design_query(self):
        engine = _make_engine()
        world = engine.detect_world(
            "Design de l'interface entre les modules d'analyse causale"
        )
        assert world == "briah"

    def test_implementation_query(self):
        engine = _make_engine()
        world = engine.detect_world(
            "Implémente une fonction qui calcule la gematria"
        )
        assert world == "yetzirah"

    def test_execution_query(self):
        engine = _make_engine()
        world = engine.detect_world(
            "Lance les tests et affiche le status"
        )
        assert world == "assiah"

    def test_short_simple_query_defaults_assiah(self):
        engine = _make_engine()
        world = engine.detect_world("status")
        assert world == "assiah"

    def test_long_query_favors_atzilut(self):
        engine = _make_engine()
        long_query = "Explique le sens profond " * 30  # > 500 chars
        world = engine.detect_world(long_query)
        # Long query should favor higher worlds
        assert world in ("atzilut", "briah")

    def test_no_keywords_defaults_yetzirah(self):
        engine = _make_engine()
        # > 50 chars pour éviter le bonus assiah, aucun keyword → défaut yetzirah
        world = engine.detect_world("abcdefgh ijklmnop qrstuvwx yzabcdef ghijklmn opqrstuv")
        assert world == "yetzirah"

    def test_depth_markers_favor_atzilut(self):
        engine = _make_engine()
        world = engine.detect_world(
            "Démontre un isomorphisme formel entre les deux structures"
        )
        assert world == "atzilut"


# ── _format_descent ──────────────────────────────────────────

class TestFormatDescent:

    def test_atzilut_to_briah(self):
        result = HishtalshelutEngine._format_descent(
            "Direction stratégique : organiser par thèmes",
            "atzilut", "briah",
        )
        assert "Keter de" in result
        assert "בְּרִיאָה" in result
        assert "אֲצִילוּת" in result
        assert "design" in result.lower() or "interface" in result.lower()

    def test_briah_to_yetzirah(self):
        result = HishtalshelutEngine._format_descent(
            "Architecture en 3 modules", "briah", "yetzirah",
        )
        assert "Keter de" in result
        assert "Implémente" in result or "Code" in result

    def test_yetzirah_to_assiah(self):
        result = HishtalshelutEngine._format_descent(
            "Fonction calculate()", "yetzirah", "assiah",
        )
        assert "Keter de" in result
        assert "Exécute" in result or "Persiste" in result

    def test_truncation_at_1000_chars(self):
        long_text = "x" * 2000
        result = HishtalshelutEngine._format_descent(
            long_text, "atzilut", "briah",
        )
        # Le texte original devrait être tronqué
        assert len(long_text) > len(result)

    def test_generic_fallback(self):
        result = HishtalshelutEngine._format_descent(
            "Quelque chose", "assiah", "yetzirah",
        )
        assert "Keter de" in result


# ── DescentStep / AscentStep / DescentResult ─────────────────

class TestDataclasses:

    def test_descent_step_to_dict(self):
        step = DescentStep(
            world="briah",
            hebrew="בְּרִיאָה",
            input_text="input",
            output_text="output résultat",
            latency_ms=150.0,
            tokens_est=10,
            status="ok",
            confidence=0.55,
        )
        d = step.to_dict()
        assert d["world"] == "briah"
        assert d["status"] == "ok"
        assert d["latency_ms"] == 150.0
        assert d["input_len"] == 5
        assert d["output_len"] == 15

    def test_ascent_step_to_dict(self):
        step = AscentStep(
            world="yetzirah",
            hebrew="יְצִירָה",
            insight="Un insight",
            enrichment="Enrichi via Yesod",
        )
        d = step.to_dict()
        assert d["world"] == "yetzirah"
        assert d["insight_len"] == 10
        assert d["enrichment_len"] == 17

    def test_descent_result_to_dict(self):
        result = DescentResult(
            starting_world="atzilut",
            ending_world="assiah",
            final_output="Le résultat final",
            total_latency_ms=500.0,
            query="une requête de test",
        )
        d = result.to_dict()
        assert d["starting_world"] == "atzilut"
        assert d["ending_world"] == "assiah"
        assert d["n_steps"] == 0
        assert d["total_latency_ms"] == 500.0


# ── descend (avec mock Ollama) ───────────────────────────────

class TestDescend:

    def _mock_generate(self, world, prompt, timeout=60, **kwargs):
        """Stub ollama_generate qui retourne un texte par monde."""
        responses = {
            "atziluth": ("Concept stratégique depuis Atzilut", 100.0),
            "briah": ("Design architectural depuis Briah", 80.0),
            "yetzirah": ("Implémentation concrète depuis Yetzirah", 60.0),
            "assiah": ("Résultat d'exécution depuis Assiah", 40.0),
        }
        return responses.get(world, ("réponse générique", 50.0))

    @patch("hishtalshelut.ollama_generate")
    @patch("hishtalshelut.get_provider", return_value="ollama")
    def test_full_descent_atzilut_to_assiah(self, mock_provider, mock_gen):
        mock_gen.side_effect = self._mock_generate
        engine = _make_engine()
        tree = _stub_tree()

        result = engine.descend("Test query", tree, starting_world="atzilut")

        assert result.starting_world == "atzilut"
        assert result.ending_world == "assiah"
        assert len(result.steps) == 4
        assert result.final_output != ""
        assert result.total_latency_ms > 0
        # Chaque monde a produit un résultat
        for step in result.steps:
            assert step.status == "ok"

    @patch("hishtalshelut.ollama_generate")
    @patch("hishtalshelut.get_provider", return_value="ollama")
    def test_descent_from_briah(self, mock_provider, mock_gen):
        mock_gen.side_effect = self._mock_generate
        engine = _make_engine()
        tree = _stub_tree()

        result = engine.descend("Test", tree, starting_world="briah")

        assert result.starting_world == "briah"
        assert len(result.steps) == 3  # briah, yetzirah, assiah

    @patch("hishtalshelut.ollama_generate")
    @patch("hishtalshelut.get_provider", return_value="ollama")
    def test_descent_from_assiah(self, mock_provider, mock_gen):
        mock_gen.side_effect = self._mock_generate
        engine = _make_engine()
        tree = _stub_tree()

        result = engine.descend("Test", tree, starting_world="assiah")

        assert len(result.steps) == 1  # only assiah
        assert result.final_output != ""

    @patch("hishtalshelut.ollama_generate")
    @patch("hishtalshelut.get_provider", return_value="ollama")
    def test_descent_logs_transitions(self, mock_provider, mock_gen):
        mock_gen.side_effect = self._mock_generate
        state = _fresh_state()
        engine = HishtalshelutEngine(state, _olamot_chain())
        tree = _stub_tree()

        engine.descend("Test", tree, starting_world="atzilut")

        # 3 transitions : atzilut→briah, briah→yetzirah, yetzirah→assiah
        descent_logs = [
            e for e in state["log"] if e["direction"] == "descent"
        ]
        assert len(descent_logs) == 3

    @patch("hishtalshelut.ollama_generate")
    @patch("hishtalshelut.get_provider", return_value="ollama")
    def test_descent_updates_state(self, mock_provider, mock_gen):
        mock_gen.side_effect = self._mock_generate
        state = _fresh_state()
        engine = HishtalshelutEngine(state, _olamot_chain())
        tree = _stub_tree()

        engine.descend("Test", tree, starting_world="atzilut")

        assert state["descents"] == 3  # 3 descent transitions
        assert state["current_world"] == "assiah"

    @patch("hishtalshelut.ollama_generate")
    @patch("hishtalshelut.get_provider", return_value="ollama")
    def test_descent_history(self, mock_provider, mock_gen):
        mock_gen.side_effect = self._mock_generate
        engine = _make_engine()
        tree = _stub_tree()

        engine.descend("Test 1", tree)
        engine.descend("Test 2", tree)

        assert len(engine.history) == 2

    @patch("hishtalshelut.ollama_generate", side_effect=Exception("Ollama down"))
    @patch("hishtalshelut.get_provider", return_value="ollama")
    def test_descent_handles_errors(self, mock_provider, mock_gen):
        engine = _make_engine()
        tree = _stub_tree()

        result = engine.descend("Test", tree, starting_world="yetzirah")

        # All steps should be errors
        assert all(s.status == "error" for s in result.steps)
        # final_output should be empty since nothing worked
        assert result.final_output == ""

    @patch("hishtalshelut.ollama_generate")
    @patch("hishtalshelut.get_provider", return_value="ollama")
    def test_descent_partial_error_fallback(self, mock_provider, mock_gen):
        """Si un monde échoue, les suivants continuent."""
        call_count = [0]
        def partial_fail(world, prompt, timeout=60, **kwargs):
            call_count[0] += 1
            if world == "briah":
                raise Exception("Briah down")
            return (f"OK from {world}", 50.0)

        mock_gen.side_effect = partial_fail
        engine = _make_engine()
        tree = _stub_tree()

        result = engine.descend("Test", tree, starting_world="atzilut")

        # briah failed, but others should work
        statuses = [s.status for s in result.steps]
        assert "error" in statuses
        assert "ok" in statuses
        # final output should come from assiah
        assert result.final_output != ""


# ── ascend ───────────────────────────────────────────────────

class TestAscend:

    def _make_descent_result(self) -> DescentResult:
        """Créer un DescentResult simulé."""
        return DescentResult(
            starting_world="atzilut",
            ending_world="assiah",
            steps=[
                DescentStep(
                    world=w,
                    hebrew=OLAM_HEBREW[w],
                    input_text="in",
                    output_text=f"output {w}",
                    status="ok",
                )
                for w in OLAMOT_DESCENDING
            ],
            final_output="Résultat final",
            query="Test",
        )

    def test_ascend_basic(self):
        engine = _make_engine()
        tree = _stub_tree()
        descent = self._make_descent_result()

        steps = engine.ascend(descent, ["Insight 1"], tree)

        # Should traverse all 4 worlds in reverse
        assert len(steps) == 4
        worlds = [s.world for s in steps]
        assert worlds == list(reversed(list(OLAMOT_DESCENDING)))

    def test_ascend_enrichment(self):
        engine = _make_engine()
        tree = _stub_tree()
        descent = self._make_descent_result()

        steps = engine.ascend(descent, ["Insight from execution"], tree)

        # Each step should have enrichment
        for step in steps:
            assert step.enrichment != ""
            assert step.status == "ok"

    def test_ascend_persists_in_yesod(self):
        engine = _make_engine()
        tree = _stub_tree()
        descent = self._make_descent_result()

        engine.ascend(descent, ["Important insight"], tree)

        # Yesod should have received remembers
        yesod = tree["yesod"]
        assert len(yesod.remembered) > 0
        # Check tags contain hishtalshelut and or_chozer
        for r in yesod.remembered:
            assert "hishtalshelut" in r["tags"]
            assert "or_chozer" in r["tags"]

    def test_ascend_no_insights(self):
        engine = _make_engine()
        tree = _stub_tree()
        descent = self._make_descent_result()

        steps = engine.ascend(descent, [], tree)

        assert len(steps) == 0

    def test_ascend_logs_transitions(self):
        state = _fresh_state()
        engine = HishtalshelutEngine(state, _olamot_chain())
        tree = _stub_tree()
        descent = self._make_descent_result()

        engine.ascend(descent, ["Insight"], tree)

        ascent_logs = [
            e for e in state["log"] if e["direction"] == "ascent"
        ]
        # 3 ascent transitions: assiah→yetzirah, yetzirah→briah, briah→atzilut
        assert len(ascent_logs) == 3

    def test_ascend_multiple_insights(self):
        engine = _make_engine()
        tree = _stub_tree()
        descent = self._make_descent_result()

        steps = engine.ascend(
            descent,
            ["Insight A", "Insight B", "Insight C"],
            tree,
        )

        # Combined insights should be in each step
        for step in steps:
            assert "Insight A" in step.insight
            assert "Insight B" in step.insight

    def test_ascend_with_partial_descent(self):
        """Ascend only through worlds that succeeded in descent."""
        engine = _make_engine()
        tree = _stub_tree()
        descent = DescentResult(
            starting_world="briah",
            ending_world="assiah",
            steps=[
                DescentStep(
                    world="briah", hebrew="", input_text="", output_text="ok",
                    status="ok",
                ),
                DescentStep(
                    world="yetzirah", hebrew="", input_text="", output_text="",
                    status="error", error="failed",
                ),
                DescentStep(
                    world="assiah", hebrew="", input_text="", output_text="ok",
                    status="ok",
                ),
            ],
            final_output="ok",
            query="Test",
        )

        steps = engine.ascend(descent, ["Insight"], tree)

        # Only briah and assiah succeeded, so ascend through those 2
        assert len(steps) == 2
        worlds = [s.world for s in steps]
        assert "yetzirah" not in worlds


# ── get_chain_state ──────────────────────────────────────────

class TestGetChainState:

    def test_fresh_state(self):
        engine = _make_engine()
        state = engine.get_chain_state()

        assert state["current_world"] == "assiah"
        assert state["highest_reached"] == "assiah"
        assert state["ascents"] == 0
        assert state["descents"] == 0
        assert state["total_descents_full"] == 0
        assert state["total_ascents_full"] == 0
        assert state["forced_world"] is None

    def test_worlds_info(self):
        engine = _make_engine()
        state = engine.get_chain_state()

        assert "worlds" in state
        assert len(state["worlds"]) == 4
        for w in OLAMOT_DESCENDING:
            assert w in state["worlds"]
            assert "hebrew" in state["worlds"][w]
            assert "sephirah" in state["worlds"][w]

    def test_after_descent(self):
        state_dict = _fresh_state()
        state_dict["descents"] = 5
        state_dict["ascents"] = 2
        state_dict["highest_reached"] = "briah"
        engine = HishtalshelutEngine(state_dict, _olamot_chain())

        state = engine.get_chain_state()

        assert state["descents"] == 5
        assert state["ascents"] == 2
        assert state["highest_reached"] == "briah"

    def test_forced_world(self):
        state_dict = _fresh_state()
        state_dict["forced_world"] = "briah"
        engine = HishtalshelutEngine(state_dict, _olamot_chain())

        state = engine.get_chain_state()
        assert state["forced_world"] == "briah"


# ── Properties ───────────────────────────────────────────────

class TestProperties:

    def test_current_world(self):
        state = _fresh_state()
        state["current_world"] = "briah"
        engine = HishtalshelutEngine(state, _olamot_chain())
        assert engine.current_world == "briah"

    def test_current_world_chain_mapping(self):
        """Quand main.py stocke 'atziluth', la propriété retourne 'atzilut'."""
        state = _fresh_state()
        state["current_world"] = "atziluth"
        engine = HishtalshelutEngine(state, _olamot_chain())
        assert engine.current_world == "atzilut"

    def test_descent_count(self):
        state = _fresh_state()
        state["descents"] = 7
        engine = HishtalshelutEngine(state, _olamot_chain())
        assert engine.descent_count == 7

    def test_ascent_count(self):
        state = _fresh_state()
        state["ascents"] = 3
        engine = HishtalshelutEngine(state, _olamot_chain())
        assert engine.ascent_count == 3

    def test_highest_reached_mapping(self):
        state = _fresh_state()
        state["highest_reached"] = "atziluth"
        engine = HishtalshelutEngine(state, _olamot_chain())
        assert engine.highest_reached == "atzilut"


# ── Confidence estimation ────────────────────────────────────

class TestConfidenceEstimation:

    def test_empty_response(self):
        assert HishtalshelutEngine._estimate_confidence("") == 0.1

    def test_very_short(self):
        assert HishtalshelutEngine._estimate_confidence("ok") == 0.1

    def test_error_response(self):
        assert HishtalshelutEngine._estimate_confidence("[Erreur] blah") == 0.05

    def test_uncertain_response(self):
        conf = HishtalshelutEngine._estimate_confidence(
            "Je ne sais pas et je suis pas sûr de la réponse"
        )
        assert conf <= 0.25

    def test_short_response(self):
        conf = HishtalshelutEngine._estimate_confidence(
            "Voici une réponse assez courte."
        )
        assert conf == 0.3

    def test_normal_response(self):
        conf = HishtalshelutEngine._estimate_confidence(
            "Voici une réponse normale avec suffisamment de contenu pour être "
            "considérée comme une réponse raisonnable et satisfaisante."
        )
        assert conf == 0.55


# ── Edge cases ───────────────────────────────────────────────

class TestEdgeCases:

    def test_engine_without_tree(self):
        engine = _make_engine()
        tree = {}  # Empty tree

        steps = engine.ascend(
            DescentResult(
                starting_world="atzilut",
                ending_world="assiah",
                steps=[
                    DescentStep(
                        world="assiah", hebrew="", input_text="",
                        output_text="ok", status="ok",
                    ),
                ],
                final_output="ok",
                query="Test",
            ),
            ["Insight"],
            tree,
        )

        # Should still work, just no persistence
        assert len(steps) == 1
        assert "non disponible" in steps[0].enrichment

    def test_detect_world_empty_query(self):
        engine = _make_engine()
        world = engine.detect_world("")
        # Empty = short = should lean assiah
        assert world in OLAMOT_DESCENDING

    def test_descent_result_query_truncation(self):
        result = DescentResult(
            starting_world="atzilut",
            ending_world="assiah",
            query="x" * 500,
        )
        d = result.to_dict()
        assert len(d["query"]) <= 200

    def test_format_descent_empty_result(self):
        formatted = HishtalshelutEngine._format_descent(
            "", "atzilut", "briah",
        )
        assert "Keter de" in formatted

    def test_multiple_sequential_descents(self):
        """Plusieurs descentes successives ne corrompent pas l'état."""
        state = _fresh_state()
        engine = HishtalshelutEngine(state, _olamot_chain())

        with patch("hishtalshelut.ollama_generate",
                    return_value=("response", 50.0)), \
             patch("hishtalshelut.get_provider", return_value="ollama"):
            tree = _stub_tree()
            engine.descend("Q1", tree, starting_world="yetzirah")
            engine.descend("Q2", tree, starting_world="yetzirah")
            engine.descend("Q3", tree, starting_world="yetzirah")

        assert len(engine.history) == 3
        assert state["descents"] > 0

    def test_atzilut_skipped_no_api_key(self):
        """Atzilut est skipped si pas de clé API et provider=anthropic."""
        engine = _make_engine()
        tree = _stub_tree()

        with patch("hishtalshelut.get_provider", return_value="anthropic"), \
             patch.dict("os.environ", {}, clear=True), \
             patch("hishtalshelut.ollama_generate",
                    return_value=("response from lower", 50.0)):
            result = engine.descend("Test", tree, starting_world="atzilut")

        # Atzilut should be skipped
        atz_step = result.steps[0]
        assert atz_step.world == "atzilut"
        assert atz_step.status == "skipped"
