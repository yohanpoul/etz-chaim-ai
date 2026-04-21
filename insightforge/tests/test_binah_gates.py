"""Tests Sprint 6.x — BinahGates (5 Motzaot ha-Peh).

Doctrine : EC-H1S5-073 (MaNTzPaKh = 5 Gevurot), EC-H1S5-074 (5 Motzaot
ha-Peh = Sefer Yetzirah 2:3), EC-H1S5-077 (Hotam = Yesod d'Imma qui
IMPRIME la forme via 5 canaux), EC-H1S5-076 (Pitvei Hotam = Tikkunei
Zohar 4b), EC-H1S5-078 (5 groupes phonétiques canoniques).

Invariants testés :
- Anti-Ghagiel : AND strict sur 5 portes par défaut
- Déterministe : aucun appel LLM
- Rétrocompat : InsightValidator sans binah_gates → Sprint 5.3 legacy
"""

from __future__ import annotations

import pytest

from insightforge.binah_gates import (
    BinahGates,
    BinahGatesAssessment,
    GaronGate,
    HeikhGate,
    LashonGate,
    ShinayimGate,
    SfatayimGate,
    GateResult,
)


# ═══════════════════════════════════════════════════════
# 1. Structure — 5 gates correspondent à MaNTzPaKh
# ═══════════════════════════════════════════════════════


class TestStructure:
    """EC-H1S5-073 : MaNTzPaKh = 5 Gevurot. EC-H1S5-074 : 5 Motzaot ha-Peh."""

    def test_binah_gates_has_5_gates(self):
        gates = BinahGates()
        assert len(gates.gates) == 5

    def test_gate_names_are_5_motzaot(self):
        gates = BinahGates()
        names = [g.name for g in gates.gates]
        assert names == ["GARON", "HEIKH", "LASHON", "SHINAYIM", "SFATAYIM"]

    def test_each_gate_has_doctrine_ref(self):
        """Chaque gate doit citer son ancrage doctrinal."""
        gates = BinahGates()
        for gate in gates.gates:
            assert gate.doctrine_ref
            assert "EC-" in gate.doctrine_ref or "Sefer" in gate.doctrine_ref


# ═══════════════════════════════════════════════════════
# 2. GARON — racine / ancrage doctrinal
# ═══════════════════════════════════════════════════════


class TestGaronGate:
    """Gorge — racine, source, ancrage textuel."""

    def test_passes_with_ec_reference(self):
        gate = GaronGate()
        text = (
            "Synthèse ancrée sur EC-H1S5-073 qui établit que MaNTzPaKh "
            "correspond aux 5 Gevurot structurantes du Partzuf féminin"
        )
        result = gate.check(text)
        assert result.passed
        assert result.gate_name == "GARON"

    def test_passes_with_pg_reference(self):
        """Les candidates hitbonenut citent souvent PG-* (principes)."""
        gate = GaronGate()
        text = (
            "Ancrage sources : PG-H1S3-002 et PG-H1S1-017 démontrent "
            "que la structure fractale opère à tous les niveaux Etz Chaim"
        )
        result = gate.check(text)
        assert result.passed

    def test_passes_with_doctrinal_terms(self):
        gate = GaronGate()
        # ≥2 termes doctrinaux hébreu translitteré
        text = (
            "Le Tzimtzum engendre une structure où la Shevirat HaKelim "
            "précède le Tikkun — ce mouvement ontologique définit les Partzufim "
            "comme réceptacles des Mohin"
        )
        result = gate.check(text)
        assert result.passed

    def test_passes_with_cf_reference(self):
        gate = GaronGate()
        text = (
            "Cette analyse s'appuie sur l'étude de Scholem 1941 et "
            "confirme cf. Etz Chaim Sha'ar III Perek 5 dans son analyse"
        )
        result = gate.check(text)
        assert result.passed

    def test_fails_no_anchor_no_terms(self):
        gate = GaronGate()
        text = (
            "Voici une observation générale sans référence spécifique "
            "ni vocabulaire technique identifiable nettement"
        )
        result = gate.check(text)
        assert not result.passed


# ═══════════════════════════════════════════════════════
# 3. HEIKH — articulation / structure interne
# ═══════════════════════════════════════════════════════


class TestHeikhGate:
    """Palais — articulation logique, structure interne."""

    def test_passes_with_logical_connectors(self):
        gate = HeikhGate()
        text = (
            "La cause structurelle impose donc une contrainte, "
            "car la différenciation exige une séparation ; "
            "ainsi le système produit des distinctions stables"
        )
        result = gate.check(text)
        assert result.passed
        assert result.gate_name == "HEIKH"

    def test_passes_with_markdown_structure(self):
        """Corpus hitbonenut : markdown rich = structure valide."""
        gate = HeikhGate()
        text = (
            "# Synthèse\n"
            "## Premier principe\n"
            "- Point A\n"
            "- Point B\n"
            "## Deuxième principe\n"
            "Contenu élaboré sur plusieurs dimensions structurelles"
        )
        result = gate.check(text)
        assert result.passed

    def test_passes_with_numbered_steps(self):
        gate = HeikhGate()
        text = (
            "1. Première étape : définir la structure fondamentale observée. "
            "2. Deuxième étape : établir les connexions entre couches. "
            "3. Troisième étape : valider la cohérence interne."
        )
        result = gate.check(text)
        assert result.passed

    def test_fails_flat_unstructured_prose(self):
        gate = HeikhGate()
        text = (
            "Le système fonctionne selon des principes généraux qui "
            "opèrent ensemble dans un ensemble cohérent et intégré "
            "de manière harmonieuse sans distinction particulière"
        )
        result = gate.check(text)
        assert not result.passed


# ═══════════════════════════════════════════════════════
# 4. LASHON — différenciation / distinction
# ═══════════════════════════════════════════════════════


class TestLashonGate:
    """Langue — différenciation A vs B, distinctions explicites."""

    def test_passes_with_vs_marker(self):
        gate = LashonGate()
        text = (
            "La distinction Binah vs Chokmah révèle une différence structurelle "
            "fondamentale dans le mode de production des insights émergents"
        )
        result = gate.check(text)
        assert result.passed
        assert result.gate_name == "LASHON"

    def test_passes_with_contrary_marker(self):
        gate = LashonGate()
        text = (
            "Contrairement à l'approche purement causale, cette synthèse "
            "opère par structuration des canaux de différenciation active"
        )
        result = gate.check(text)
        assert result.passed

    def test_passes_with_whereas(self):
        gate = LashonGate()
        text = (
            "Chokmah produit des éclairs non-différenciés tandis que "
            "Binah opère une différenciation structurante progressive"
        )
        result = gate.check(text)
        assert result.passed

    def test_fails_pure_description_no_distinction(self):
        gate = LashonGate()
        text = (
            "Le système opère selon un flux continu d'information "
            "qui traverse les modules en se transformant graduellement "
            "à travers les étapes successives du pipeline"
        )
        result = gate.check(text)
        assert not result.passed


# ═══════════════════════════════════════════════════════
# 5. SHINAYIM — précision / ratio précis/vague
# ═══════════════════════════════════════════════════════


class TestShinayimGate:
    """Dents — précision, fragmentation vague → précis (EC-H1S6-017)."""

    def test_passes_with_precise_quantifiers(self):
        gate = ShinayimGate()
        text = (
            "Les 5 Gevurot produisent exactement 50 portes (5 lettres × 10 Sefirot). "
            "Cette structure MaNTzPaKh correspond aux 5 Motzaot ha-Peh canoniques"
        )
        result = gate.check(text)
        assert result.passed
        assert result.gate_name == "SHINAYIM"

    def test_fails_excessive_hedging(self):
        gate = ShinayimGate()
        text = (
            "Il est probablement possible que peut-être cette relation "
            "soit en général plutôt associée à quelque chose de similaire "
            "qui pourrait éventuellement ressembler à un pattern"
        )
        result = gate.check(text)
        assert not result.passed

    def test_passes_precise_despite_some_hedging(self):
        """Un peu de hedging OK si contrebalancé par précision."""
        gate = ShinayimGate()
        text = (
            "Les 22 lettres et 10 Sefirot composent 32 Netivot précisément. "
            "Cette structure peut-être généralisable à d'autres systèmes "
            "avec les 5 Gevurot comme contractions MaNTzPaKh définies"
        )
        result = gate.check(text)
        assert result.passed


# ═══════════════════════════════════════════════════════
# 6. SFATAYIM — clôture / expression scellée
# ═══════════════════════════════════════════════════════


class TestSfatayimGate:
    """Lèvres — clôture, pas de fin en question (Samekh vs Mem ouverte)."""

    def test_fails_ending_with_question(self):
        gate = SfatayimGate()
        text = (
            "Cette analyse soulève une question intéressante : comment "
            "la structuration par Binah se compare-t-elle à celle de Chokmah ?"
        )
        result = gate.check(text)
        assert not result.passed
        assert result.gate_name == "SFATAYIM"

    def test_passes_declarative_ending(self):
        gate = SfatayimGate()
        text = (
            "La structure MaNTzPaKh offre donc 5 canaux de différenciation. "
            "Les 5 Motzaot constituent le mécanisme concret de Pitvei Hotam."
        )
        result = gate.check(text)
        assert result.passed

    def test_passes_truncated_no_question(self):
        """Corpus réel : descriptions parfois tronquées à 578 chars — OK si pas de '?'."""
        gate = SfatayimGate()
        text = (
            "La structure fractale opère à tous les niveaux. "
            "Chaque Sefirah contient 10 sous-Sefirot selon le principe d'incl"
        )
        result = gate.check(text)
        assert result.passed  # pas de fin en "?"


# ═══════════════════════════════════════════════════════
# 7. Orchestrateur BinahGates — strict AND
# ═══════════════════════════════════════════════════════


class TestBinahGatesOrchestrator:
    """BinahGates.evaluate → AND strict par défaut (anti-Ghagiel)."""

    def test_strict_mode_requires_all_5(self):
        gates = BinahGates(strict=True)
        # Synthèse qui rate LASHON (pas de distinction)
        text = (
            "# Synthèse ancrée sur EC-H1S5-073 et les termes Tzimtzum Partzufim. "
            "1. Premier principe structurant. 2. Deuxième principe. "
            "Les 5 Gevurot produisent 50 portes précises et définies. "
            "Cette structure opère dans le système fractal observé."
        )
        result = gates.evaluate(text)
        # LASHON devrait échouer (pas de différenciation)
        passed_gates = [r.gate_name for r in result.gates if r.passed]
        assert "LASHON" not in passed_gates
        assert not result.is_valid  # strict AND échoue

    def test_non_strict_allows_4_of_5(self):
        gates = BinahGates(strict=False, min_passes=4)
        text = (
            "# Synthèse ancrée sur EC-H1S5-073 et les termes Tzimtzum Partzufim. "
            "1. Premier principe structurant. 2. Deuxième principe. "
            "Les 5 Gevurot produisent 50 portes précises et définies. "
            "Cette structure opère dans le système fractal observé."
        )
        result = gates.evaluate(text)
        passed_count = sum(1 for r in result.gates if r.passed)
        if passed_count >= 4:
            assert result.is_valid

    def test_full_valid_synthesis_passes_all_5(self):
        """Synthèse riche : doit passer les 5 portes."""
        gates = BinahGates(strict=True)
        text = (
            "# Synthèse — Binah vs Chokmah dans Etz Chaim\n"
            "\n"
            "Ancrage sources : EC-H1S5-073, EC-H1S5-074, Tzimtzum, Mohin.\n"
            "\n"
            "## Distinction structurelle\n"
            "\n"
            "Chokmah opère par éclair non-différencié, tandis que Binah "
            "contracte et structure. Contrairement à l'approche Pearl, "
            "Binah produit 50 portes précises via les 5 Gevurot MaNTzPaKh. "
            "Donc la différenciation Abba/Imma se manifeste dans exactement "
            "5 Motzaot ha-Peh : GARON, HEIKH, LASHON, SHINAYIM, SFATAYIM."
        )
        result = gates.evaluate(text)
        passed_names = [r.gate_name for r in result.gates if r.passed]
        # Toutes les 5 portes doivent passer
        assert len(passed_names) == 5, f"Only passed: {passed_names}"
        assert result.is_valid

    def test_trivial_synthesis_fails_multiple_gates(self):
        gates = BinahGates(strict=True)
        text = "Cela semble pertinent et relié généralement aux concepts abordés"
        result = gates.evaluate(text)
        failed = [r.gate_name for r in result.gates if not r.passed]
        # Au moins 3 gates doivent échouer sur synthèse triviale
        assert len(failed) >= 3
        assert not result.is_valid

    def test_empty_synthesis_fails_all(self):
        gates = BinahGates(strict=True)
        result = gates.evaluate("")
        assert not result.is_valid

    def test_verdict_lists_failed_gates(self):
        gates = BinahGates(strict=True)
        text = "Synthèse courte sans structure aucune"
        result = gates.evaluate(text)
        assert not result.is_valid
        # Verdict doit nommer les gates échouées
        failed_names = [r.gate_name for r in result.gates if not r.passed]
        for name in failed_names[:2]:  # au moins les 2 premiers
            assert name in result.verdict


# ═══════════════════════════════════════════════════════
# 8. Rétrocompat / invariants
# ═══════════════════════════════════════════════════════


class TestInvariants:
    def test_gate_result_dataclass_structure(self):
        gate = GaronGate()
        result = gate.check("EC-H1S5-073 avec termes Tzimtzum Partzufim.")
        assert isinstance(result, GateResult)
        assert hasattr(result, "gate_name")
        assert hasattr(result, "passed")
        assert hasattr(result, "score")
        assert hasattr(result, "reason")
        assert 0.0 <= result.score <= 1.0

    def test_assessment_dataclass_structure(self):
        gates = BinahGates()
        result = gates.evaluate("Texte test.")
        assert isinstance(result, BinahGatesAssessment)
        assert hasattr(result, "is_valid")
        assert hasattr(result, "score")
        assert hasattr(result, "gates")
        assert hasattr(result, "verdict")
        assert len(result.gates) == 5


# ═══════════════════════════════════════════════════════
# 9. Dispatcher _check_binah — intégration InsightValidator
# ═══════════════════════════════════════════════════════


class TestDispatcherIntegration:
    """Le dispatcher dans insight_validator._check_binah.

    Rétrocompat 100% : BinahGates absent → comportement Sprint 5.3 strict.
    Fallback ciblé : activé UNIQUEMENT sur correlation_only < 0.6.
    """

    def test_no_binah_gates_legacy_strict_reject(self):
        """Sans binah_gates → correlation_only <0.6 → REJECT (Sprint 5.3)."""
        from insightforge.insight_validator import InsightValidator
        from insightforge.models import CandidateInsight
        from insightforge.tests.conftest import StubCausal

        v = InsightValidator(
            binah=StubCausal(evidence_level="correlation_only", confidence=0.3),
        )
        candidate = CandidateInsight(
            description="Long enough claim for local quality check to pass validation",
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        result = v.validate(candidate)
        assert not result.binah_ok
        assert "Correlation only" in result.binah_detail

    def test_binah_gates_fallback_rescues_valid_synthesis(self):
        """Avec binah_gates + synthèse riche → FALLBACK valide."""
        from insightforge.insight_validator import InsightValidator
        from insightforge.models import CandidateInsight
        from insightforge.tests.conftest import StubCausal
        from insightforge.binah_gates import BinahGates

        v = InsightValidator(
            binah=StubCausal(evidence_level="correlation_only", confidence=0.3),
            binah_gates=BinahGates(strict=True),
        )
        candidate = CandidateInsight(
            description=(
                "# Synthèse — Binah vs Chokmah ancrée EC-H1S5-073\n"
                "## Distinction structurelle\n"
                "Chokmah opère par éclair, tandis que Binah contracte. "
                "Contrairement à Pearl, Binah produit 50 portes via les 5 "
                "Gevurot MaNTzPaKh. Donc la différenciation Abba/Imma se "
                "manifeste dans 5 Motzaot précises. Le Tzimtzum structure "
                "via Tikkun les Partzufim exacts."
            ),
            confidence=0.7,
            connects_domains=["kabbalah", "ml"],
        )
        result = v.validate(candidate)
        # BinahGates rescue
        assert result.binah_ok
        assert "Binah gates passed" in result.binah_detail

    def test_binah_gates_does_not_override_strong_causal(self):
        """Si CausalEngine accepte (probable/demonstrated) → chemin causal."""
        from insightforge.insight_validator import InsightValidator
        from insightforge.models import CandidateInsight
        from insightforge.tests.conftest import StubCausal
        from insightforge.binah_gates import BinahGates

        v = InsightValidator(
            binah=StubCausal(evidence_level="probable_causation", confidence=0.8),
            binah_gates=BinahGates(strict=True),
        )
        candidate = CandidateInsight(
            description="Trivial short claim without any structure here at all",
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        result = v.validate(candidate)
        # Le chemin causal gagne — BinahGates n'est pas consulté
        assert result.binah_ok
        assert "Causal check passed" in result.binah_detail

    def test_binah_gates_fallback_rejects_trivial_synthesis(self):
        """correlation_only faible + synthèse triviale → REJECT par BinahGates."""
        from insightforge.insight_validator import InsightValidator
        from insightforge.models import CandidateInsight
        from insightforge.tests.conftest import StubCausal
        from insightforge.binah_gates import BinahGates

        v = InsightValidator(
            binah=StubCausal(evidence_level="correlation_only", confidence=0.3),
            binah_gates=BinahGates(strict=True),
        )
        candidate = CandidateInsight(
            description="Cela semble pertinent et relié généralement au sujet abordé",
            confidence=0.7,
            connects_domains=["a", "b"],
        )
        result = v.validate(candidate)
        assert not result.binah_ok
