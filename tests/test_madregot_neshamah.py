"""Tests MadregotNeshamah — מדרגות נשמה — Niveaux d'âme pour Hitbonenut.

Couvre :
  - 5 niveaux définis avec prompts distincts
  - Distribution 70/20/10 respectée
  - score_by_level retourne des scores cohérents
  - soul_level influence bien le type de questions
  - Intégration dans HitbonenutEngine
"""

from __future__ import annotations

import random
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from madregot_neshamah import (
    MadregahLevel,
    MadregotNeshamah,
    LEVEL_PROMPTS,
    DISTRIBUTION_CURRENT,
    DISTRIBUTION_BELOW,
    DISTRIBUTION_ABOVE,
)


# ── Fixtures ────────────────────────────────────────────────

@pytest.fixture
def madregot():
    return MadregotNeshamah()


CORPUS_PATH = Path(__file__).parent.parent / "hitbonenut_corpus.yaml"


@pytest.fixture
def engine():
    """HitbonenutEngine avec corpus réel mais sans DB."""
    from hitbonenut import HitbonenutEngine
    with patch.object(HitbonenutEngine, "_ensure_schema"):
        eng = HitbonenutEngine(
            tree={},
            db_url="postgresql://localhost/etz_chaim_test",
            corpus_path=CORPUS_PATH,
        )
    return eng


# ── 5 niveaux définis ──────────────────────────────────────

class TestLevelDefinitions:
    def test_five_levels_exist(self):
        """Exactement 5 niveaux dans MadregahLevel."""
        assert len(MadregahLevel) == 5

    def test_levels_ordered(self):
        """Nefesh < Ruach < Neshamah < Chayah < Yechidah."""
        assert MadregahLevel.NEFESH < MadregahLevel.RUACH
        assert MadregahLevel.RUACH < MadregahLevel.NESHAMAH
        assert MadregahLevel.NESHAMAH < MadregahLevel.CHAYAH
        assert MadregahLevel.CHAYAH < MadregahLevel.YECHIDAH

    def test_each_level_has_prompt(self):
        """Chaque niveau a un LevelPrompt défini."""
        for level in MadregahLevel:
            assert level in LEVEL_PROMPTS
            lp = LEVEL_PROMPTS[level]
            assert lp.level == level
            assert lp.olam  # non vide
            assert lp.style  # non vide
            assert "{domain}" in lp.prompt_template
            assert lp.scoring_hint  # non vide

    def test_prompts_are_distinct(self):
        """Chaque niveau a un prompt template différent."""
        templates = [lp.prompt_template for lp in LEVEL_PROMPTS.values()]
        assert len(set(templates)) == 5

    def test_olamot_mapping(self):
        """Les Olamot correspondent aux niveaux."""
        assert LEVEL_PROMPTS[MadregahLevel.NEFESH].olam == "Assiah"
        assert LEVEL_PROMPTS[MadregahLevel.RUACH].olam == "Yetzirah"
        assert LEVEL_PROMPTS[MadregahLevel.NESHAMAH].olam == "Briah"
        assert LEVEL_PROMPTS[MadregahLevel.CHAYAH].olam == "Atzilut"
        assert LEVEL_PROMPTS[MadregahLevel.YECHIDAH].olam == "Adam Kadmon"

    def test_styles_mapping(self):
        """Les styles correspondent aux niveaux."""
        assert LEVEL_PROMPTS[MadregahLevel.NEFESH].style == "factuel"
        assert LEVEL_PROMPTS[MadregahLevel.RUACH].style == "analytique"
        assert LEVEL_PROMPTS[MadregahLevel.NESHAMAH].style == "contemplatif"
        assert LEVEL_PROMPTS[MadregahLevel.CHAYAH].style == "paradoxal"
        assert LEVEL_PROMPTS[MadregahLevel.YECHIDAH].style == "unificateur"


# ── get_question_level ─────────────────────────────────────

class TestGetQuestionLevel:
    def test_known_levels(self, madregot):
        """Chaque string soul_level mappe correctement."""
        assert madregot.get_question_level("nefesh") == MadregahLevel.NEFESH
        assert madregot.get_question_level("ruach") == MadregahLevel.RUACH
        assert madregot.get_question_level("neshamah") == MadregahLevel.NESHAMAH
        assert madregot.get_question_level("chayah") == MadregahLevel.CHAYAH
        assert madregot.get_question_level("yechidah") == MadregahLevel.YECHIDAH

    def test_case_insensitive(self, madregot):
        """Le mapping est case-insensitive."""
        assert madregot.get_question_level("NEFESH") == MadregahLevel.NEFESH
        assert madregot.get_question_level("Ruach") == MadregahLevel.RUACH

    def test_unknown_defaults_nefesh(self, madregot):
        """Un niveau inconnu fallback sur Nefesh."""
        assert madregot.get_question_level("unknown") == MadregahLevel.NEFESH
        assert madregot.get_question_level("") == MadregahLevel.NEFESH


# ── Distribution 70/20/10 ─────────────────────────────────

class TestDistribution:
    def test_distribution_sums_to_one(self):
        """70% + 20% + 10% = 100%."""
        total = DISTRIBUTION_CURRENT + DISTRIBUTION_BELOW + DISTRIBUTION_ABOVE
        assert abs(total - 1.0) < 1e-9

    def test_distribution_statistical(self, madregot):
        """Sur 10000 tirages, la distribution 70/20/10 est respectée."""
        random.seed(42)
        counts = {level: 0 for level in MadregahLevel}
        n = 10000

        for _ in range(n):
            level = madregot.select_level_for_question("ruach")
            counts[level] += 1

        # Ruach est le niveau courant → ~70%
        assert 0.65 < counts[MadregahLevel.RUACH] / n < 0.75
        # Nefesh est en dessous → ~20%
        assert 0.15 < counts[MadregahLevel.NEFESH] / n < 0.25
        # Neshamah est au dessus → ~10%
        assert 0.06 < counts[MadregahLevel.NESHAMAH] / n < 0.14

    def test_nefesh_no_below(self, madregot):
        """Au niveau Nefesh, pas de niveau en dessous — consolidation = Nefesh."""
        random.seed(42)
        counts = {level: 0 for level in MadregahLevel}

        for _ in range(10000):
            level = madregot.select_level_for_question("nefesh")
            counts[level] += 1

        # Nefesh = 70% current + 20% below (clampé à Nefesh) = ~90%
        assert counts[MadregahLevel.NEFESH] / 10000 > 0.85
        # Ruach = 10% aspiration
        assert 0.06 < counts[MadregahLevel.RUACH] / 10000 < 0.14

    def test_yechidah_no_above(self, madregot):
        """Au niveau Yechidah, pas de niveau au dessus — aspiration = Yechidah."""
        random.seed(42)
        counts = {level: 0 for level in MadregahLevel}

        for _ in range(10000):
            level = madregot.select_level_for_question("yechidah")
            counts[level] += 1

        # Yechidah = 70% current + 10% above (clampé) = ~80%
        assert counts[MadregahLevel.YECHIDAH] / 10000 > 0.75
        # Chayah = 20% consolidation
        assert 0.15 < counts[MadregahLevel.CHAYAH] / 10000 < 0.25


# ── build_level_prompt ─────────────────────────────────────

class TestBuildLevelPrompt:
    def test_nefesh_prompt_contains_factuel(self, madregot):
        """Prompt Nefesh contient le mot 'FACTUELLE'."""
        prompt = madregot.build_level_prompt(MadregahLevel.NEFESH, "gematria")
        assert "FACTUELLE" in prompt
        assert "NEFESH" in prompt
        assert "Assiah" in prompt

    def test_ruach_prompt_contains_analytique(self, madregot):
        """Prompt Ruach contient le mot 'ANALYTIQUE'."""
        prompt = madregot.build_level_prompt(MadregahLevel.RUACH, "sephiroth")
        assert "ANALYTIQUE" in prompt
        assert "RUACH" in prompt

    def test_neshamah_prompt_contains_contemplatif(self, madregot):
        """Prompt Neshamah contient 'CONTEMPLATIVE'."""
        prompt = madregot.build_level_prompt(MadregahLevel.NESHAMAH, "ohr")
        assert "CONTEMPLATIVE" in prompt
        assert "NESHAMAH" in prompt

    def test_chayah_prompt_contains_paradoxal(self, madregot):
        """Prompt Chayah contient 'PARADOXALE'."""
        prompt = madregot.build_level_prompt(MadregahLevel.CHAYAH, "tzimtzum")
        assert "PARADOXALE" in prompt
        assert "CHAYAH" in prompt

    def test_yechidah_prompt_contains_unificatrice(self, madregot):
        """Prompt Yechidah contient 'UNIFICATRICE'."""
        prompt = madregot.build_level_prompt(MadregahLevel.YECHIDAH, "ein_sof")
        assert "UNIFICATRICE" in prompt
        assert "YECHIDAH" in prompt

    def test_domain_injected(self, madregot):
        """Le domaine est injecté dans le prompt."""
        prompt = madregot.build_level_prompt(MadregahLevel.NEFESH, "gematria")
        assert "gematria" in prompt

    def test_past_questions_included(self, madregot):
        """Les questions passées apparaissent dans le prompt."""
        past = ["Combien de Sephiroth?", "Qu'est-ce que Keter?"]
        prompt = madregot.build_level_prompt(
            MadregahLevel.NEFESH, "sephiroth", past_questions=past,
        )
        assert "DÉJÀ posées" in prompt
        assert "Combien de Sephiroth?" in prompt

    def test_insights_included(self, madregot):
        """Les insights sont inclus dans le prompt."""
        insights = ["Le Tzimtzum est lié à l'Information Bottleneck"]
        prompt = madregot.build_level_prompt(
            MadregahLevel.RUACH, "kabbale", insights=insights,
        )
        assert "Insights récents" in prompt
        assert "Information Bottleneck" in prompt

    def test_weak_domains_included(self, madregot):
        """Les domaines faibles apparaissent."""
        prompt = madregot.build_level_prompt(
            MadregahLevel.NEFESH, "gematria", weak_domains=["ohr", "tzeruf"],
        )
        assert "ohr" in prompt
        assert "tzeruf" in prompt

    def test_attempt_retry_message(self, madregot):
        """Les tentatives suivantes mentionnent la créativité."""
        prompt = madregot.build_level_prompt(
            MadregahLevel.NEFESH, "gematria", attempt=2,
        )
        assert "Tentative 3" in prompt
        assert "créatif" in prompt


# ── score_by_level ─────────────────────────────────────────

class TestScoreByLevel:
    def test_empty_response_zero(self, madregot):
        """Réponse vide → score 0."""
        assert madregot.score_by_level("", MadregahLevel.NEFESH, 0.5) == 0.0

    def test_nefesh_concise_bonus(self, madregot):
        """Nefesh : réponse concise (10-80 mots) → bonus."""
        response = "Keter est la première Sephirah, la couronne, au sommet de l'Arbre."
        score = madregot.score_by_level(response, MadregahLevel.NEFESH, 0.5)
        assert score > 0.5  # bonus appliqué

    def test_ruach_structure_markers(self, madregot):
        """Ruach : marqueurs analytiques → bonus."""
        response = (
            "D'une part, Chesed représente l'expansion sans limite. "
            "D'autre part, Gevurah impose la contraction et le jugement. "
            "La dialectique entre ces deux forces crée Tiferet."
        )
        score = madregot.score_by_level(response, MadregahLevel.RUACH, 0.5)
        assert score >= 0.58  # bonus pour 3 marqueurs

    def test_neshamah_depth_markers(self, madregot):
        """Neshamah : marqueurs de profondeur → bonus."""
        response = (
            "La signification profonde du Reshimu va au-delà de la simple trace. "
            "Essentiellement, c'est le mystère de la mémoire divine — "
            "la contemplation de ce qui persiste quand tout a été retiré. "
            "Au cœur de cette question se trouve l'intériorité de l'Ein Sof."
        )
        score = madregot.score_by_level(response, MadregahLevel.NESHAMAH, 0.5)
        assert score >= 0.55

    def test_neshamah_short_penalty(self, madregot):
        """Neshamah : réponse trop courte → malus."""
        response = "Le Reshimu est une trace."
        score = madregot.score_by_level(response, MadregahLevel.NESHAMAH, 0.5)
        assert score < 0.5  # malus pour < 50 mots

    def test_chayah_tension_bonus(self, madregot):
        """Chayah : marqueurs de tension → bonus."""
        response = (
            "Le paradoxe du Tsimtsum est qu'il est à la fois réel et "
            "métaphorique. Simultanément, l'Ein Sof se contracte et ne "
            "se contracte pas. Cette tension est irréductible — la "
            "coincidentia oppositorum est la seule approche possible. "
            "Les opposés se rencontrent dans un mystère qui transcende la logique."
        )
        score = madregot.score_by_level(response, MadregahLevel.CHAYAH, 0.5)
        assert score >= 0.58

    def test_chayah_resolution_penalty(self, madregot):
        """Chayah : résoudre le paradoxe au lieu de l'habiter → malus."""
        response = (
            "Il n'y a pas de paradoxe en réalité. La solution est "
            "simplement que le Tsimtsum est une métaphore."
        )
        score = madregot.score_by_level(response, MadregahLevel.CHAYAH, 0.5)
        assert score < 0.5  # malus sévère

    def test_yechidah_unity_markers(self, madregot):
        """Yechidah : marqueurs d'unité → bonus."""
        response = (
            "L'unité de l'Ein Sof transcende toute multiplicité. "
            "Le devekut ultime mène au bittul — l'effacement du moi "
            "dans la totalité de la lumière divine. Au-delà des mots, "
            "dans le silence de la contemplation, toute séparation "
            "se révèle illusoire. La transparence est totale."
        )
        score = madregot.score_by_level(response, MadregahLevel.YECHIDAH, 0.5)
        assert score >= 0.58

    def test_score_clamped_zero_one(self, madregot):
        """Le score est toujours entre 0.0 et 1.0."""
        # base_score très haut + gros bonus ne dépasse pas 1.0
        response = (
            "Le paradoxe est à la fois irréductible et simultanément "
            "une tension entre les opposés. La coincidentia oppositorum "
            "transcende la logique ordinaire. Ce mystère est au-delà."
        )
        score = madregot.score_by_level(response, MadregahLevel.CHAYAH, 0.95)
        assert score <= 1.0

        # base_score très bas + gros malus ne descend pas sous 0.0
        score = madregot.score_by_level("court", MadregahLevel.NESHAMAH, 0.02)
        assert score >= 0.0


# ── get_difficulty_for_level ───────────────────────────────

class TestDifficultyMapping:
    def test_nefesh_basique(self, madregot):
        assert madregot.get_difficulty_for_level(MadregahLevel.NEFESH) == "basique"

    def test_ruach_intermediaire(self, madregot):
        assert madregot.get_difficulty_for_level(MadregahLevel.RUACH) == "intermediaire"

    def test_neshamah_avancee(self, madregot):
        assert madregot.get_difficulty_for_level(MadregahLevel.NESHAMAH) == "avancee"

    def test_chayah_erudite(self, madregot):
        assert madregot.get_difficulty_for_level(MadregahLevel.CHAYAH) == "erudite"

    def test_yechidah_erudite(self, madregot):
        assert madregot.get_difficulty_for_level(MadregahLevel.YECHIDAH) == "erudite"


# ── Intégration HitbonenutEngine ───────────────────────────

class TestEngineIntegration:
    def test_engine_has_madregot(self, engine):
        """L'engine a un attribut madregot de type MadregotNeshamah."""
        assert hasattr(engine, "madregot")
        assert isinstance(engine.madregot, MadregotNeshamah)

    @patch.object(MadregotNeshamah, "score_by_level", return_value=0.65)
    def test_score_response_with_soul_level(self, mock_score, engine):
        """_score_response avec soul_level appelle score_by_level."""
        response = (
            "Le tzimtzum est la contraction de Ein Sof selon Luria. "
            "Le reshimu persiste comme trace. La shevirah brise les kelim."
        )
        score, kw = engine._score_response(
            "Qu'est-ce que le Tzimtzum?", response,
            "kabbale_lurianique", {},
            soul_level="ruach",
        )
        mock_score.assert_called_once()
        assert score == 0.65

    def test_score_response_without_soul_level(self, engine):
        """_score_response sans soul_level fonctionne comme avant."""
        response = (
            "Le tzimtzum est la contraction de Ein Sof selon Luria. "
            "Le reshimu persiste. La shevirah brise les kelim."
        )
        score, kw = engine._score_response(
            "Qu'est-ce que le Tzimtzum?", response,
            "kabbale_lurianique", {},
        )
        assert score > 0
        assert kw > 0

    def test_novel_question_difficulty_from_soul_level(self, engine):
        """_select_next_question retourne la difficulté du soul level pour les novel."""
        with patch.object(engine, "generate_novel_question", return_value="Q novel?"), \
             patch.object(engine, "_get_soul_level", return_value="neshamah"), \
             patch.object(engine, "_get_weak_domains", return_value=[]), \
             patch("random.random", return_value=0.65):  # 0.6-0.8 = novel
            text, domain, diff = engine._select_next_question(0, 0)
            assert text == "Q novel?"
            assert domain == "novel"
            assert diff == "avancee"  # neshamah → avancee

    def test_novel_question_difficulty_nefesh(self, engine):
        """Soul level nefesh → difficulté basique pour novel."""
        with patch.object(engine, "generate_novel_question", return_value="Q basique?"), \
             patch.object(engine, "_get_soul_level", return_value="nefesh"), \
             patch.object(engine, "_get_weak_domains", return_value=[]), \
             patch("random.random", return_value=0.65):
            text, domain, diff = engine._select_next_question(0, 0)
            assert diff == "basique"

    def test_novel_question_difficulty_chayah(self, engine):
        """Soul level chayah → difficulté erudite pour novel."""
        with patch.object(engine, "generate_novel_question", return_value="Q érudite?"), \
             patch.object(engine, "_get_soul_level", return_value="chayah"), \
             patch.object(engine, "_get_weak_domains", return_value=[]), \
             patch("random.random", return_value=0.65):
            text, domain, diff = engine._select_next_question(0, 0)
            assert diff == "erudite"
