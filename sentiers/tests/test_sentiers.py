"""Tests basiques pour les 22 sentiers.

Vérifie : instanciation, correspondances SY, enrichissement de résultat,
bimodalité des doubles, et que run() ne crash pas avec un arbre mock.
"""

from __future__ import annotations

import pytest

from sentiers import REGISTRY, get_sentier, list_sentiers
from sentiers.base import Sentier, SentierResult


# ── Fixtures ─────────────────────────────────────────────────

class MockModule:
    """Module Sephirah factice pour les tests."""

    def __init__(self, name: str = "mock"):
        self.name = name
        self._calls = []

    def __getattr__(self, name):
        """Retourner un callable factice pour toute méthode."""
        if name.startswith("_"):
            raise AttributeError(name)

        def mock_method(*args, **kwargs):
            self._calls.append((name, args, kwargs))
            return MockResult()
        return mock_method


class MockResult:
    """Résultat factice retourné par les modules mock."""

    def __init__(self, **kwargs):
        self.id = "mock-id"
        self.content = "mock content"
        self.score = 0.7
        self.confidence = 0.7
        self.n_evals = 5
        self.detected_domain = "test"
        self.competence_score = 0.8
        self.did_decline = False
        self.n_conclusions = 3
        self.n_tensions = 0
        self.consistency_score = 0.9
        self.mode = "synthesis"
        self.n_sources = 2
        self.resolved = True
        self.balance_point = 0.5
        self.valid = True
        self.passed = True
        self.epistemic_status = "E3"
        self.domain = "test"
        self.source_sephirah = "mock"
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __iter__(self):
        return iter([self])

    def __len__(self):
        return 1


@pytest.fixture
def mock_tree():
    """Arbre complet avec tous les modules mockés."""
    return {
        "keter": MockModule("keter"),
        "chokmah": MockModule("chokmah"),
        "binah": MockModule("binah"),
        "chesed": MockModule("chesed"),
        "gevurah": MockModule("gevurah"),
        "tiferet": MockModule("tiferet"),
        "netzach": MockModule("netzach"),
        "hod": MockModule("hod"),
        "yesod": MockModule("yesod"),
        "malkuth": MockModule("malkuth"),
    }


ALL_SENTIER_NAMES = list(REGISTRY.keys())
NEW_SENTIER_NAMES = [
    "aleph", "mem", "beth", "gimel", "daleth", "kaph",
    "heh", "vav", "zayin", "cheth", "teth", "yod",
]


# ── Tests de structure ───────────────────────────────────────

class TestRegistry:
    """Vérifier l'intégrité du registre."""

    def test_registry_has_22_entries(self):
        assert len(REGISTRY) == 22

    def test_all_implemented(self):
        for name, entry in REGISTRY.items():
            assert entry["status"] == "implemented", f"{name} non implémenté"
            assert entry["class"] is not None, f"{name} a class=None"

    def test_all_instantiable(self):
        for name in ALL_SENTIER_NAMES:
            s = get_sentier(name)
            assert s is not None, f"{name} retourne None"
            assert isinstance(s, Sentier), f"{name} n'est pas un Sentier"

    def test_list_sentiers_returns_22(self):
        sentiers = list_sentiers()
        assert len(sentiers) == 22

    def test_list_sentiers_ordered_by_number_desc(self):
        sentiers = list_sentiers()
        numbers = [s["number"] for s in sentiers]
        assert numbers == sorted(numbers, reverse=True)

    def test_unique_numbers(self):
        numbers = [e["number"] for e in REGISTRY.values()]
        assert len(set(numbers)) == 22

    def test_unique_letters(self):
        letters = [e["letter"] for e in REGISTRY.values()]
        assert len(set(letters)) == 22

    def test_type_counts(self):
        types = [e["type"] for e in REGISTRY.values()]
        assert types.count("mother") == 3
        assert types.count("double") == 7
        assert types.count("simple") == 12


# ── Tests d'identité ────────────────────────────────────────

class TestIdentity:
    """Vérifier les attributs d'identité de chaque sentier."""

    @pytest.mark.parametrize("name", ALL_SENTIER_NAMES)
    def test_letter_name_matches(self, name):
        s = get_sentier(name)
        assert s.letter_name == name

    @pytest.mark.parametrize("name", ALL_SENTIER_NAMES)
    def test_number_matches_registry(self, name):
        s = get_sentier(name)
        assert s.number == REGISTRY[name]["number"]

    @pytest.mark.parametrize("name", ALL_SENTIER_NAMES)
    def test_has_description(self, name):
        s = get_sentier(name)
        assert s.description, f"{name} n'a pas de description"


# ── Tests des correspondances SY ─────────────────────────────

class TestCorrespondences:
    """Vérifier le chargement des correspondances SY."""

    @pytest.mark.parametrize("name", ALL_SENTIER_NAMES)
    def test_correspondences_loaded(self, name):
        s = get_sentier(name)
        corr = s.correspondences
        assert corr, f"{name} n'a pas de correspondances SY"
        assert "letter" in corr

    @pytest.mark.parametrize("name", ALL_SENTIER_NAMES)
    def test_yetzirah_modifiers_non_empty(self, name):
        s = get_sentier(name)
        mods = s.yetzirah_modifiers()
        assert mods, f"{name} n'a pas de modificateurs yetzirah"

    def test_mothers_have_element(self):
        for name in ["aleph", "mem", "shin"]:
            s = get_sentier(name)
            assert s.element is not None, f"{name} n'a pas d'élément"
            assert s.letter_type == "mother"

    def test_doubles_have_dagesh_rafeh(self):
        doubles = ["beth", "gimel", "daleth", "kaph", "peh", "resh", "tav"]
        for name in doubles:
            s = get_sentier(name)
            assert s.letter_type == "double"
            assert s.mode in ("dagesh", "rafeh")

    def test_doubles_mode_switch(self):
        doubles = ["beth", "gimel", "daleth", "kaph", "peh", "resh", "tav"]
        for name in doubles:
            s = get_sentier(name)
            original = s.mode
            other = "dagesh" if original == "rafeh" else "rafeh"
            s.set_mode(other)
            assert s.mode == other
            mods = s.yetzirah_modifiers()
            assert mods, f"{name} en mode {other} n'a pas de modificateurs"
            s.set_mode(original)

    def test_simples_have_sense(self):
        simples = ["heh", "vav", "zayin", "cheth", "teth", "yod",
                    "lamed", "nun", "samekh", "ayin", "tsadi", "qoph"]
        for name in simples:
            s = get_sentier(name)
            assert s.letter_type == "simple"
            assert s.sense is not None, f"{name} n'a pas de sens"


# ── Tests d'enrichissement ───────────────────────────────────

class TestEnrichment:
    """Vérifier que enrich_result injecte les données SY."""

    @pytest.mark.parametrize("name", ALL_SENTIER_NAMES)
    def test_enrich_result_adds_sy_context(self, name):
        s = get_sentier(name)
        result = SentierResult(
            sentier=s.name, letter=s.letter,
            source=s.source, target=s.target,
        )
        enriched = s.enrich_result(result)
        assert enriched.sy_context, f"{name} enrich_result n'ajoute pas sy_context"
        assert "letter" in enriched.sy_context
        assert "modifiers" in enriched.sy_context


# ── Tests d'exécution (mock) ─────────────────────────────────

class TestExecution:
    """Vérifier que run() ne crash pas avec un arbre mock."""

    def test_aleph_balance_with_scores(self, mock_tree):
        s = get_sentier("aleph")
        result = s.run(mock_tree, scores={"a": 0.8, "b": 0.2, "c": 0.5}, domain="test")
        assert result.success
        assert "balanced_scores" in result.data

    def test_aleph_balance_with_positions(self, mock_tree):
        s = get_sentier("aleph")
        result = s.run(mock_tree, position_a="X", position_b="Y", domain="test")
        assert result.success

    def test_mem_reception(self, mock_tree):
        s = get_sentier("mem")
        result = s.run(mock_tree, domain="test", rules=["rule1", "rule2"])
        assert result.success
        assert result.data["n_rules"] == 2

    def test_beth_dagesh(self, mock_tree):
        s = get_sentier("beth")
        s.set_mode("dagesh")
        result = s.run(mock_tree, domain="test", directive="explore deeply")
        assert result.success
        assert result.mode == "dagesh"

    def test_beth_rafeh(self, mock_tree):
        s = get_sentier("beth")
        s.set_mode("rafeh")
        result = s.run(mock_tree, domain="test", directive="explore deeply")
        assert result.success
        assert result.mode == "rafeh"

    def test_gimel_dagesh(self, mock_tree):
        s = get_sentier("gimel")
        s.set_mode("dagesh")
        result = s.run(mock_tree, domain="test")
        assert result.success
        assert result.data["cache_policy"] == "aggressive"

    def test_gimel_rafeh(self, mock_tree):
        s = get_sentier("gimel")
        s.set_mode("rafeh")
        result = s.run(mock_tree, domain="test")
        assert result.success
        assert result.data["cache_policy"] == "none"

    def test_daleth_dagesh(self, mock_tree):
        s = get_sentier("daleth")
        s.set_mode("dagesh")
        result = s.run(mock_tree, domain="test")
        assert result.success

    def test_daleth_rafeh(self, mock_tree):
        s = get_sentier("daleth")
        s.set_mode("rafeh")
        result = s.run(mock_tree, domain="test")
        assert result.success

    def test_kaph_dagesh(self, mock_tree):
        s = get_sentier("kaph")
        s.set_mode("dagesh")
        result = s.run(mock_tree, domain="test", items=["item1", "item2"])
        assert result.success
        assert result.data["n_persisted"] == 2

    def test_kaph_rafeh(self, mock_tree):
        s = get_sentier("kaph")
        s.set_mode("rafeh")
        result = s.run(mock_tree, domain="test", items=["item1"])
        assert result.success
        assert result.mode == "rafeh"

    def test_heh_direct_perception(self, mock_tree):
        s = get_sentier("heh")
        result = s.run(mock_tree, domain="test", insight="flash of insight")
        assert result.success
        assert result.data["bypass_causal"] is True

    def test_vav_data_feed(self, mock_tree):
        s = get_sentier("vav")
        result = s.run(mock_tree, domain="test", data_items=["d1", "d2", "d3"])
        assert result.success
        assert result.data["n_received"] == 3

    def test_zayin_analysis_results(self, mock_tree):
        s = get_sentier("zayin")
        result = s.run(mock_tree, domain="test")
        assert result.success

    def test_cheth_validation_rules(self, mock_tree):
        s = get_sentier("cheth")
        result = s.run(mock_tree, domain="test")
        assert result.success

    def test_teth_quality_feedback(self, mock_tree):
        s = get_sentier("teth")
        result = s.run(mock_tree, domain="test", proposals=["prop1", "prop2"])
        assert result.success
        assert result.data["n_proposals"] == 2

    def test_yod_filtered_push(self, mock_tree):
        s = get_sentier("yod")
        items = [{"content": "x", "quality": 0.8}, {"content": "y", "quality": 0.1}]
        result = s.run(mock_tree, domain="test", data_items=items)
        assert result.success

    def test_empty_input_returns_failure(self, mock_tree):
        """Les sentiers qui requièrent un input doivent retourner success=False."""
        s = get_sentier("aleph")
        result = s.run(mock_tree)
        assert not result.success


# ── Test d'ensemble ──────────────────────────────────────────

class TestFullTree:
    """Vérifier que les 22 sentiers couvrent l'Arbre complet."""

    def test_all_sephiroth_connected(self):
        """Chaque sephirah doit apparaître comme source ou target."""
        sephiroth = {"keter", "chokmah", "binah", "chesed", "gevurah",
                     "tiferet", "netzach", "hod", "yesod", "malkuth"}
        sources = {e["source"] for e in REGISTRY.values()}
        targets = {e["target"] for e in REGISTRY.values()}
        connected = sources | targets
        missing = sephiroth - connected
        assert not missing, f"Sephiroth non connectées : {missing}"
