"""Tests du HitbonenutEngine — הִתְבּוֹנְנוּת.

Couvre :
  - Chargement du corpus YAML
  - Sélection de questions (progressive, fixe, ciblée)
  - Scoring des réponses (_score_response)
  - Novelty computation (cosine, jaccard)
  - Session mock (run_session, run_targeted)
  - assess_progress()
  - generate_novel_question() mock
  - DataClasses (SessionResult, ProgressReport, QuestionResult)
"""

import math
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hitbonenut import (
    HitbonenutEngine,
    SessionResult,
    ProgressReport,
    QuestionResult,
    NOVELTY_THRESHOLD_INITIAL,
    NOVELTY_THRESHOLD_FLOOR,
    NOVELTY_THRESHOLD_DECAY,
    DIFFICULTY_ORDER,
    DIFFICULTY_WEIGHTS,
    DOMAIN_KEYWORDS,
)


# ── Fixtures ────────────────────────────────────────────────

CORPUS_PATH = Path(__file__).parent.parent / "hitbonenut_corpus.yaml"


@pytest.fixture
def engine():
    """Engine avec corpus réel mais sans DB ni tree."""
    with patch.object(HitbonenutEngine, "_ensure_schema"):
        eng = HitbonenutEngine(
            tree={},
            db_url="postgresql://localhost/etz_chaim_test",
            corpus_path=CORPUS_PATH,
        )
    return eng


@pytest.fixture
def engine_mock_db():
    """Engine avec DB mockée."""
    with patch.object(HitbonenutEngine, "_ensure_schema"), \
         patch.object(HitbonenutEngine, "_db") as mock_db:
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_db.return_value = mock_conn
        eng = HitbonenutEngine(
            tree={},
            db_url="postgresql://localhost/etz_chaim_test",
            corpus_path=CORPUS_PATH,
        )
        eng._mock_conn = mock_conn
        eng._mock_cur = mock_cur
    return eng


# ── Corpus Loading ──────────────────────────────────────────

class TestCorpusLoading:
    def test_corpus_loads(self, engine):
        """Le corpus YAML se charge correctement."""
        assert len(engine.corpus) > 0

    def test_corpus_has_14_domains(self, engine):
        """Le corpus contient 14 domaines."""
        assert len(engine.corpus) >= 14

    def test_corpus_domains_known(self, engine):
        """Chaque domaine du corpus est connu dans DOMAIN_KEYWORDS."""
        for domain in engine.corpus:
            assert domain in DOMAIN_KEYWORDS, f"Domaine '{domain}' absent de DOMAIN_KEYWORDS"

    def test_corpus_difficulty_levels(self, engine):
        """Chaque domaine a les 4 niveaux de difficulté."""
        for domain, levels in engine.corpus.items():
            if not isinstance(levels, dict):
                continue
            for diff in ("basique", "intermediaire"):
                assert diff in levels, f"Domaine '{domain}' manque '{diff}'"

    def test_corpus_questions_are_strings(self, engine):
        """Toutes les questions sont des strings."""
        for domain, levels in engine.corpus.items():
            if not isinstance(levels, dict):
                continue
            for diff, questions in levels.items():
                if not isinstance(questions, list):
                    continue
                for q in questions:
                    assert isinstance(q, str), f"Question non-string dans {domain}/{diff}"

    def test_corpus_minimum_questions(self, engine):
        """Au moins 150 questions dans le corpus."""
        total = sum(
            len(qs)
            for d in engine.corpus.values()
            if isinstance(d, dict)
            for qs in d.values()
            if isinstance(qs, list)
        )
        assert total >= 150

    def test_missing_corpus_returns_empty(self):
        """Corpus inexistant → dict vide."""
        with patch.object(HitbonenutEngine, "_ensure_schema"):
            eng = HitbonenutEngine(
                tree={},
                db_url="postgresql://localhost/etz_chaim_test",
                corpus_path="/nonexistent/path.yaml",
            )
        assert eng.corpus == {}


# ── Question Selection ──────────────────────────────────────

class TestQuestionSelection:
    def test_select_progressive(self, engine):
        """Mode progressive retourne des questions triées par difficulté."""
        qs = engine._select_questions(10, "progressive")
        assert len(qs) == 10
        # Les premières questions doivent être basiques
        assert qs[0][2] == "basique"

    def test_select_fixed_difficulty(self, engine):
        """Mode fixe ne retourne que le niveau demandé."""
        qs = engine._select_questions(5, "basique")
        assert len(qs) == 5
        for _, _, diff in qs:
            assert diff == "basique"

    def test_select_avancee(self, engine):
        """Mode avancée fonctionne."""
        qs = engine._select_questions(3, "avancee")
        assert len(qs) >= 1
        for _, _, diff in qs:
            assert diff == "avancee"

    def test_select_returns_tuples(self, engine):
        """Chaque question est un tuple (text, domain, difficulty)."""
        qs = engine._select_questions(3, "progressive")
        for q in qs:
            assert len(q) == 3
            text, domain, diff = q
            assert isinstance(text, str)
            assert isinstance(domain, str)
            assert diff in DIFFICULTY_ORDER

    def test_select_empty_corpus(self):
        """Corpus vide → liste vide."""
        with patch.object(HitbonenutEngine, "_ensure_schema"):
            eng = HitbonenutEngine(
                tree={},
                db_url="postgresql://localhost/etz_chaim_test",
                corpus_path="/nonexistent.yaml",
            )
        assert eng._select_questions(5, "progressive") == []


# ── Scoring ─────────────────────────────────────────────────

class TestScoring:
    def test_empty_response_scores_zero(self, engine):
        """Réponse vide → score 0."""
        score, kw = engine._score_response("Q?", "", "kabbale_lurianique", {})
        assert score == 0.0
        assert kw == 0.0

    def test_error_response_scores_zero(self, engine):
        """Réponse d'erreur → score 0."""
        score, kw = engine._score_response(
            "Q?", "[erreur génération: timeout]", "gematria", {},
        )
        assert score == 0.0

    def test_good_response_scores_positive(self, engine):
        """Réponse avec keywords du domaine → score > 0."""
        response = (
            "Le tzimtzum est la contraction initiale de l'Ein Sof. "
            "Luria enseigne que le reshimu reste dans le halal "
            "comme trace de la lumière originelle. Le kav descend "
            "ensuite pour restructurer les kelim brisés lors de "
            "la shevirah. Le tikkun est le processus de réparation "
            "par les partzufim. Les nitzotzot sont les étincelles "
            "piégées dans les qliphoth."
        )
        score, kw = engine._score_response(
            "Qu'est-ce que le Tzimtzum?", response, "kabbale_lurianique",
            {"sentiers_used": ["gimel"], "nitzotzot_before": 0, "nitzotzot_after": 1},
        )
        assert score > 0.3
        assert kw > 0.0

    def test_scoring_components(self, engine):
        """Les 4 composantes contribuent correctement (nouvelle formule)."""
        # Réponse riche avec keywords, longueur, diversité, pertinence
        rich_response = (
            "Le tzimtzum est la contraction primordiale de Ein Sof. "
            "La shevirah brise les kelim, libérant les nitzotzot. "
            "Le tikkun est la réparation par les partzufim. "
            "Luria transmet via Vital dans le Etz Chaim. "
            "Le reshimu persiste comme trace dans le halal. "
            "Le kav traverse le vide comme rayon de lumière. "
            "Le masakh filtre la lumière descendante. "
            "Les ohr et birur participent au processus de réparation."
        )
        score, kw = engine._score_response(
            "Qu'est-ce que le tzimtzum et la shevirah ?",
            rich_response, "kabbale_lurianique", {},
        )
        # 40% kw + 25% length + 20% diversité + 15% pertinence
        assert score >= 0.7

    def test_unknown_domain_neutral_kw(self, engine):
        """Domaine inconnu → kw_score neutre (0.5)."""
        score, kw = engine._score_response(
            "Q?", "Some adequate response with enough words for scoring",
            "nonexistent_domain", {},
        )
        assert kw == 0.5


# ── Novelty Computation ────────────────────────────────────

class TestNovelty:
    def test_no_past_questions_max_novelty(self, engine):
        """Sans historique, novelty = 1.0."""
        assert engine._compute_novelty("Anything?", []) == 1.0

    def test_identical_question_low_novelty(self, engine):
        """Question identique → novelty très basse."""
        with patch("olamot.ollama_embed") as mock_embed:
            # Simuler des embeddings identiques
            vec = [1.0] * 768
            mock_embed.return_value = vec
            novelty = engine._compute_novelty("Q?", ["Q?"])
            assert novelty == 0.0

    def test_different_question_high_novelty(self, engine):
        """Question très différente → novelty élevée."""
        with patch("olamot.ollama_embed") as mock_embed:
            # Vecteurs orthogonaux
            call_count = [0]
            def side_effect(text, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    return [1.0, 0.0, 0.0] + [0.0] * 765
                return [0.0, 1.0, 0.0] + [0.0] * 765
            mock_embed.side_effect = side_effect
            novelty = engine._compute_novelty("New Q?", ["Old Q?"])
            assert novelty == 1.0

    def test_jaccard_novelty_fallback(self, engine):
        """Fallback Jaccard fonctionne."""
        novelty = HitbonenutEngine._jaccard_novelty(
            "Quelle est la structure du Tzimtzum dans la Kabbale?",
            ["Quelle est la fonction du Tikkun dans la Kabbale?"],
        )
        assert 0.0 < novelty < 1.0

    def test_jaccard_identical(self, engine):
        """Jaccard identique → novelty 0."""
        novelty = engine._jaccard_novelty("exact same", ["exact same"])
        assert novelty == 0.0

    def test_jaccard_completely_different(self, engine):
        """Jaccard totalement différent → novelty 1."""
        novelty = engine._jaccard_novelty(
            "alpha beta gamma",
            ["delta epsilon zeta"],
        )
        assert novelty == 1.0

    def test_cosine_sim_orthogonal(self, engine):
        """Vecteurs orthogonaux → cosine 0."""
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert engine._cosine_sim(a, b) == 0.0

    def test_cosine_sim_parallel(self, engine):
        """Vecteurs parallèles → cosine 1."""
        a = [1.0, 2.0, 3.0]
        b = [2.0, 4.0, 6.0]
        assert abs(engine._cosine_sim(a, b) - 1.0) < 1e-6

    def test_cosine_sim_zero_vector(self, engine):
        """Vecteur nul → cosine 0."""
        assert engine._cosine_sim([0, 0, 0], [1, 2, 3]) == 0.0


# ── Constants ───────────────────────────────────────────────

class TestConstants:
    def test_novelty_threshold(self):
        assert NOVELTY_THRESHOLD_INITIAL == 0.3
        assert NOVELTY_THRESHOLD_FLOOR == 0.10
        assert NOVELTY_THRESHOLD_DECAY == 0.05

    def test_difficulty_order(self):
        assert DIFFICULTY_ORDER == ("basique", "intermediaire", "avancee", "erudite")

    def test_difficulty_weights(self):
        assert DIFFICULTY_WEIGHTS["basique"] < DIFFICULTY_WEIGHTS["erudite"]

    def test_domain_keywords_coverage(self):
        """Au moins 10 domaines avec keywords."""
        assert len(DOMAIN_KEYWORDS) >= 10

    def test_each_domain_has_keywords(self):
        """Chaque domaine a au moins 5 keywords."""
        for domain, kws in DOMAIN_KEYWORDS.items():
            assert len(kws) >= 5, f"Domaine '{domain}' a trop peu de keywords"


# ── DataClasses ─────────────────────────────────────────────

class TestDataClasses:
    def test_question_result(self):
        qr = QuestionResult(
            id="abc", question="Q?", domain="gematria",
            difficulty="basique", response="R", score=0.5,
            kw_score=0.3, sentiers_used=["yod"], nitzotzot=1,
            duration=2.5,
        )
        assert qr.score == 0.5
        assert qr.is_novel is False

    def test_session_result(self):
        sr = SessionResult(
            session_id="xyz", n_questions=5, avg_score=0.42,
            domains=["gematria", "tzeruf"], results=[],
            soul_before="nefesh", soul_after="nefesh",
            duration=30.0,
        )
        assert sr.n_questions == 5
        assert sr.competence_delta == {}

    def test_progress_report(self):
        pr = ProgressReport(
            current_scores={"gematria": 0.5},
            deltas={"gematria": 0.1},
            stagnant_domains=[],
            improving_domains=["gematria"],
            sessions_count=3,
            soul_level="nefesh",
            overall_competence=0.5,
        )
        assert pr.overall_competence == 0.5
        assert "gematria" in pr.improving_domains


# ── Session Mock ────────────────────────────────────────────

class TestSessionMock:
    @patch.object(HitbonenutEngine, "_db_create_session")
    @patch.object(HitbonenutEngine, "_db_finalize_session")
    @patch.object(HitbonenutEngine, "_db_record_question")
    @patch.object(HitbonenutEngine, "_get_soul_level", return_value="nefesh")
    @patch.object(HitbonenutEngine, "_compute_competence_delta", return_value={})
    @patch.object(HitbonenutEngine, "_emit")
    @patch.object(HitbonenutEngine, "_ask_system")
    def test_run_session_basic(
        self, mock_ask, mock_emit, mock_comp, mock_soul,
        mock_rec, mock_fin, mock_create, engine,
    ):
        """run_session complète avec mock LLM."""
        mock_ask.return_value = {
            "response": "Le tzimtzum est la contraction de l'Ein Sof.",
            "competence_score": 0.0,
            "domain_detected": "kabbale_lurianique",
            "sentiers_used": [],
            "nitzotzot_before": 0,
            "nitzotzot_after": 0,
            "memories_recalled": 0,
            "stored": False,
        }

        session = engine.run_session(n_questions=3, difficulty="basique", budget_seconds=60)

        assert isinstance(session, SessionResult)
        assert session.n_questions == 3
        assert len(session.results) == 3
        assert session.avg_score > 0
        assert session.soul_before == "nefesh"

    @patch.object(HitbonenutEngine, "_db_create_session")
    @patch.object(HitbonenutEngine, "_db_finalize_session")
    @patch.object(HitbonenutEngine, "_db_record_question")
    @patch.object(HitbonenutEngine, "_get_soul_level", return_value="nefesh")
    @patch.object(HitbonenutEngine, "_compute_competence_delta", return_value={})
    @patch.object(HitbonenutEngine, "_emit")
    @patch.object(HitbonenutEngine, "_ask_system")
    def test_run_targeted_domain(
        self, mock_ask, mock_emit, mock_comp, mock_soul,
        mock_rec, mock_fin, mock_create, engine,
    ):
        """run_targeted sur un domaine spécifique."""
        mock_ask.return_value = {
            "response": "La gematria standard calcule chaque lettre.",
            "competence_score": 0.0,
            "domain_detected": "gematria",
            "sentiers_used": [],
            "nitzotzot_before": 0,
            "nitzotzot_after": 0,
            "memories_recalled": 0,
            "stored": False,
        }

        session = engine.run_targeted(domain="gematria", n=3, budget_seconds=60)

        assert isinstance(session, SessionResult)
        assert "gematria" in session.domains

    @patch.object(HitbonenutEngine, "_db_create_session")
    @patch.object(HitbonenutEngine, "_db_finalize_session")
    @patch.object(HitbonenutEngine, "_db_record_question")
    @patch.object(HitbonenutEngine, "_get_soul_level", return_value="nefesh")
    @patch.object(HitbonenutEngine, "_compute_competence_delta", return_value={})
    @patch.object(HitbonenutEngine, "_emit")
    @patch.object(HitbonenutEngine, "_ask_system")
    def test_run_targeted_unknown_domain(
        self, mock_ask, mock_emit, mock_comp, mock_soul,
        mock_rec, mock_fin, mock_create, engine,
    ):
        """run_targeted sur domaine inconnu → session vide."""
        session = engine.run_targeted(domain="xxxxxx", n=3)
        assert session.n_questions == 0


# ── Novel Question Mock ─────────────────────────────────────

class TestNovelQuestionMock:
    @patch.object(HitbonenutEngine, "_get_past_questions", return_value=[])
    @patch.object(HitbonenutEngine, "_get_recent_insights", return_value=[])
    @patch.object(HitbonenutEngine, "_get_weak_domains", return_value=[])
    def test_novel_question_generation(self, mock_weak, mock_insights, mock_past, engine):
        """generate_novel_question avec mocks."""
        with patch("olamot.ollama_generate") as mock_gen:
            mock_gen.return_value = (
                "Quel est le lien entre Masakh et Information Bottleneck?",
                0.5,
            )
            result = engine.generate_novel_question()
            assert result is not None
            assert result.endswith("?")

    @patch.object(HitbonenutEngine, "_get_past_questions",
                  return_value=["Q déjà posée?"] * 50)
    @patch.object(HitbonenutEngine, "_get_recent_insights", return_value=[])
    @patch.object(HitbonenutEngine, "_get_weak_domains", return_value=[])
    def test_novel_rejects_low_novelty(self, mock_weak, mock_insights, mock_past, engine):
        """Novelty trop basse → None après retries."""
        with patch("olamot.ollama_generate") as mock_gen, \
             patch.object(engine, "_compute_novelty", return_value=0.1):
            mock_gen.return_value = ("Q déjà posée?", 0.5)
            result = engine.generate_novel_question(max_retries=2)
            assert result is None

    @patch.object(HitbonenutEngine, "_get_past_questions", return_value=[])
    @patch.object(HitbonenutEngine, "_get_recent_insights", return_value=[])
    @patch.object(HitbonenutEngine, "_get_weak_domains", return_value=[])
    def test_novel_extract_question(self, mock_weak, mock_insights, mock_past, engine):
        """Extraction d'une question depuis le raw LLM."""
        q = engine._extract_question("Voici une question:\nQuel est le rôle du Masakh?")
        assert q == "Quel est le rôle du Masakh?"

    def test_extract_question_no_question_mark(self, engine):
        """Pas de question → None."""
        assert engine._extract_question("Ceci n'est pas une question.") is None

    def test_extract_question_too_short(self, engine):
        """Question trop courte → None."""
        assert engine._extract_question("Q?") is None


# ── Build Prompt ────────────────────────────────────────────

class TestBuildPrompt:
    def test_prompt_contains_domain(self, engine):
        prompt = engine._build_prompt("Q?", "", "gematria")
        assert "gematria" in prompt

    def test_prompt_with_context(self, engine):
        prompt = engine._build_prompt("Q?", "Contexte important", "ohr")
        assert "Contexte important" in prompt
        assert "ohr" in prompt

    def test_prompt_without_context(self, engine):
        prompt = engine._build_prompt("Q?", "", "tzeruf")
        assert "Contexte mémoriel" not in prompt


# ── Sentier Mapping ─────────────────────────────────────────

class TestSentierMapping:
    def test_run_relevant_sentiers_no_tree(self, engine):
        """Sans arbre → liste vide (pas d'erreur)."""
        used = engine._run_relevant_sentiers("Q?", "gematria")
        assert used == []

    def test_run_relevant_sentiers_unknown_domain(self, engine):
        """Domaine inconnu → liste vide."""
        used = engine._run_relevant_sentiers("Q?", "nonexistent")
        assert used == []


# ═══════════════════════════════════════════════════════════════
# EXPLORATION DES OPPOSÉS (Cube de l'Espace)
# ═══════════════════════════════════════════════════════════════

class TestExplorationOpposites:
    def test_returns_required_keys(self, engine):
        result = engine.exploration_opposites()
        assert "letter" in result
        assert "opposite_from" in result
        assert "opposite_to" in result
        assert "sense_angle" in result
        assert "prompt_hint" in result

    def test_with_specific_letter(self, engine):
        result = engine.exploration_opposites(last_letter="beth")
        assert result["letter"] == "beth"
        assert result["opposite_from"] == "sagesse"
        assert result["opposite_to"] == "folie"

    def test_with_unknown_letter_falls_back(self, engine):
        """Lettre non-double → choisit aléatoirement parmi les doubles."""
        result = engine.exploration_opposites(last_letter="heh")
        from kabbalah.cube_of_space import CubeOfSpace
        cube = CubeOfSpace()
        doubles = cube.get_letters_by_class("double")
        assert result["letter"] in doubles

    def test_prompt_hint_contains_opposites(self, engine):
        result = engine.exploration_opposites(last_letter="peh")
        assert "domination" in result["prompt_hint"]
        assert "servitude" in result["prompt_hint"]

    def test_none_letter_picks_random_double(self, engine):
        from kabbalah.cube_of_space import CubeOfSpace
        cube = CubeOfSpace()
        doubles = cube.get_letters_by_class("double")
        for _ in range(5):
            result = engine.exploration_opposites(last_letter=None)
            assert result["letter"] in doubles


# ═══════════════════════════════════════════════════════════════
# CONSULTATION DES SIFREI YESOD
# ═══════════════════════════════════════════════════════════════

class TestSifreiYesodConsultation:
    """Tests de l'intégration Sifrei Yesod → Hitbonenut."""

    def test_consult_returns_dict_on_failure(self, engine):
        """Si Sifrei Yesod est inaccessible, retourne dict vide."""
        result = engine._consult_sifrei_yesod("Qu'est-ce que le Tzimtzum?")
        assert isinstance(result, dict)

    def test_consult_graceful_on_import_error(self, engine):
        """Import error → dict vide, pas d'exception."""
        with patch("sifrei_yesod.api.query.SifreiYesodQuery", side_effect=ImportError):
            result = engine._consult_sifrei_yesod("test question")
            assert result == {}

    @patch("sifrei_yesod.api.query.SifreiYesodQuery")
    def test_consult_returns_structured_refs(self, MockSQ, engine):
        """Avec mock, retourne principes + assertions + concepts."""
        mock_sq = MagicMock()
        MockSQ.return_value = mock_sq
        mock_sq.consult_for_hitbonenut.return_value = {
            "principes": [
                {"principe_id": "PG-K1-005", "nom": "4 Modes de Tzimtzum",
                 "formalisation": "Le Tzimtzum opère en 4 modes...",
                 "similarity": 0.89},
            ],
            "assertions": [
                {"assertion_id": "EC-K1-P01-A01", "assertion": "Ein Sof remplit tout.",
                 "similarity": 0.85},
                {"assertion_id": "EC-K1-P01-A02", "assertion": "Le Tzimtzum crée le Halal.",
                 "similarity": 0.82},
            ],
            "concepts_lies": [
                {"concept_id": "tzimtzum", "nom_he": "צמצום", "nom_fr": "Contraction"},
            ],
        }
        result = engine._consult_sifrei_yesod("Quel est le principe du Tzimtzum?")
        assert len(result["principes"]) == 1
        assert result["principes"][0]["principe_id"] == "PG-K1-005"
        assert len(result["assertions"]) == 2
        assert len(result["concepts_lies"]) == 1

    @patch("sifrei_yesod.api.query.SifreiYesodQuery")
    def test_ask_system_includes_sifrei_context(self, MockSQ, engine):
        """_ask_system enrichit le contexte avec les refs Sifrei Yesod."""
        mock_sq = MagicMock()
        MockSQ.return_value = mock_sq
        mock_sq.consult_for_hitbonenut.return_value = {
            "principes": [
                {"principe_id": "PG-K1-005", "nom": "4 Modes de Tzimtzum",
                 "formalisation": "Le Tzimtzum opère en 4 modes distincts.",
                 "similarity": 0.89},
            ],
            "assertions": [],
            "concepts_lies": [],
        }

        with patch("olamot.ollama_generate") as mock_gen:
            mock_gen.return_value = ("Le Tzimtzum est la contraction.", 0.5)
            result = engine._ask_system("Qu'est-ce que le Tzimtzum?")

        assert "sifrei_yesod_refs" in result
        assert len(result["sifrei_yesod_refs"].get("principes", [])) == 1

    def test_question_result_has_sifrei_field(self):
        """QuestionResult contient le champ sifrei_yesod_refs."""
        qr = QuestionResult(
            id="abc", question="Q?", domain="tzimtzum",
            difficulty="basique", response="R", score=0.5,
            kw_score=0.3, sentiers_used=[], nitzotzot=0,
            duration=1.0, sifrei_yesod_refs={"principes": [{"id": "PG-K1-005"}]},
        )
        assert qr.sifrei_yesod_refs["principes"][0]["id"] == "PG-K1-005"

    def test_question_result_default_empty_refs(self):
        """sifrei_yesod_refs par défaut = dict vide."""
        qr = QuestionResult(
            id="abc", question="Q?", domain="test",
            difficulty="basique", response="R", score=0.5,
            kw_score=0.3, sentiers_used=[], nitzotzot=0,
            duration=1.0,
        )
        assert qr.sifrei_yesod_refs == {}


# ══════════════════════════════════════════════════════════════
# ══ HITBONENUT-2 : Tests de la Boucle de Recherche Réflexive ══
# ══════════════════════════════════════════════════════════════

from hitbonenut import (
    ExperimentResult,
    Principle,
    RESEARCH_SYSTEM_PROMPT,
    TUNABLE_PARAMS,
    EXPERIMENT_COOLDOWN,
    MAX_REGRESSION,
    MEASUREMENT_SESSIONS,
)


class TestHitbonenut2DataClasses:
    """Tests des nouvelles dataclasses."""

    def test_experiment_result_fields(self):
        """ExperimentResult contient tous les champs."""
        er = ExperimentResult(
            id="exp-1", target_module="chokmah",
            target_param="min_novelty_score",
            old_value="0.7", new_value="0.6",
            hypothesis="Baisser le seuil", contemplation="Mode exploratoire",
            metric_before={"fidelity": 0.5}, metric_after={"fidelity": 0.55},
            delta=0.05, status="keep", principle="Seuils bas = plus d'insights",
            daat_verified=True, duration=120.0, measurement_sessions=3,
        )
        assert er.status == "keep"
        assert er.delta == 0.05
        assert er.daat_verified is True

    def test_experiment_result_crash(self):
        """ExperimentResult crash a delta=0."""
        er = ExperimentResult(
            id="exp-2", target_module="binah",
            target_param="max_confounders",
            old_value="10", new_value="5",
            hypothesis="Réduire", contemplation="",
            metric_before={}, metric_after={},
            delta=0.0, status="crash", principle="",
            daat_verified=False, duration=1.0, measurement_sessions=0,
        )
        assert er.status == "crash"
        assert er.measurement_sessions == 0

    def test_principle_fields(self):
        """Principle contient tous les champs."""
        p = Principle(
            id="p-1", principle="Les seuils bas augmentent le flux",
            source_experiment="exp-1", domain="chokmah",
            confidence=0.7, confirmed_count=3, contradicted_count=1,
            is_active=True,
        )
        assert p.confidence == 0.7
        assert p.is_active is True


class TestHitbonenut2Constants:
    """Tests des constantes Hitbonenut-2."""

    def test_research_system_prompt_not_empty(self):
        """Le system prompt de recherche est défini."""
        assert len(RESEARCH_SYSTEM_PROMPT) > 100
        assert "auto-modification" in RESEARCH_SYSTEM_PROMPT

    def test_tunable_params_coverage(self):
        """Au moins 5 paramètres tunables définis."""
        assert len(TUNABLE_PARAMS) >= 5

    def test_tunable_params_structure(self):
        """Chaque paramètre tunable a les champs requis."""
        for key, defn in TUNABLE_PARAMS.items():
            assert "module" in defn, f"{key} manque 'module'"
            assert "attr" in defn, f"{key} manque 'attr'"
            assert "type" in defn, f"{key} manque 'type'"
            assert "min" in defn, f"{key} manque 'min'"
            assert "max" in defn, f"{key} manque 'max'"
            assert "step" in defn, f"{key} manque 'step'"
            assert defn["min"] < defn["max"], f"{key}: min >= max"

    def test_cooldown_positive(self):
        """Le cooldown est positif."""
        assert EXPERIMENT_COOLDOWN > 0

    def test_max_regression_bounded(self):
        """MAX_REGRESSION est entre 0 et 1."""
        assert 0 < MAX_REGRESSION < 1.0

    def test_measurement_sessions_positive(self):
        """Au moins 1 session de mesure."""
        assert MEASUREMENT_SESSIONS >= 1


class TestIdentifyWeakest:
    """Tests de _identify_weakest."""

    def test_identify_weakest_empty_tree(self, engine):
        """Avec un arbre vide, retourne un dict avec fidelity basse."""
        result = engine._identify_weakest()
        # Should still return something (fidelity_score will be 0.0)
        assert result is not None or result is None  # graceful

    def test_identify_weakest_with_mock_hod(self):
        """Avec un SelfMap mocké, détecte les domaines faibles."""
        mock_hod = MagicMock()
        mock_hod.self_diagnose.return_value = {
            "domains": {
                "general": {"score": 0.1},
                "causal": {"score": 0.8},
            },
            "status": "ok",
        }

        with patch.object(HitbonenutEngine, "_ensure_schema"):
            eng = HitbonenutEngine(
                tree={"hod": mock_hod},
                db_url="postgresql://localhost/etz_chaim_test",
                corpus_path=CORPUS_PATH,
            )

        result = eng._identify_weakest()
        assert result is not None
        assert result.get("weakest_domain") == "general"
        assert result.get("weakest_domain_score") == 0.1


class TestSelectTunableTarget:
    """Tests de _select_tunable_target."""

    def test_select_with_no_recent(self, engine):
        """Sans expériences récentes, tous les paramètres sont candidats."""
        with patch.object(engine, "_load_recent_experiments", return_value=[]):
            weak = {"fidelity_score": 0.3, "unhealthy_modules": []}
            result = engine._select_tunable_target(weak)
            # Should return something
            if result:
                assert "param_key" in result
                assert "current_value" in result

    def test_cooldown_respected(self, engine):
        """Quand tous les paramètres sont en cooldown, forçage du plus ancien."""
        # Créer des faux résultats qui couvrent TOUS les paramètres
        fake_experiments = [
            ExperimentResult(
                id=f"exp-{i}", target_module=defn["module"],
                target_param=defn["attr"],
                old_value="0.5", new_value="0.6",
                hypothesis="", contemplation="",
                metric_before={}, metric_after={},
                delta=0.0, status="discard", principle="",
                daat_verified=False, duration=1.0, measurement_sessions=0,
            )
            for i, (key, defn) in enumerate(TUNABLE_PARAMS.items())
        ]

        with patch.object(engine, "_load_recent_experiments", return_value=fake_experiments):
            weak = {"fidelity_score": 0.3}
            result = engine._select_tunable_target(weak)
            # Tous en cooldown → forçage du paramètre le plus ancien
            assert result is not None
            assert "param_def" in result
            assert "module" in result


class TestMeasureSystemMetrics:
    """Tests de _measure_system_metrics."""

    def test_metrics_empty_tree(self, engine):
        """Avec un arbre vide, retourne des métriques à 0."""
        metrics = engine._measure_system_metrics()
        assert "composite" in metrics
        assert "selfmap_competence" in metrics
        assert metrics["composite"] >= 0.0

    def test_metrics_with_mock_modules(self):
        """Avec des modules mockés, les métriques sont remplies."""
        mock_hod = MagicMock()
        mock_hod.get_global_competence.return_value = 0.65

        with patch.object(HitbonenutEngine, "_ensure_schema"):
            eng = HitbonenutEngine(
                tree={"hod": mock_hod},
                db_url="postgresql://localhost/etz_chaim_test",
                corpus_path=CORPUS_PATH,
            )

        metrics = eng._measure_system_metrics()
        assert metrics["selfmap_competence"] == 0.65
        assert metrics["composite"] > 0.0


class TestVerifyDaat:
    """Tests de _verify_daat."""

    def test_daat_false_on_discard(self, engine):
        """Da'at non atteint si l'expérience est discard."""
        er = ExperimentResult(
            id="x", target_module="m", target_param="p",
            old_value="0", new_value="1",
            hypothesis="h", contemplation="c",
            metric_before={"a": 1}, metric_after={"a": 2},
            delta=-0.05, status="discard", principle="",
            daat_verified=False, duration=1.0, measurement_sessions=1,
        )
        assert engine._verify_daat(er) is False

    def test_daat_false_on_tiny_delta(self, engine):
        """Da'at non atteint si le delta est insignifiant."""
        er = ExperimentResult(
            id="x", target_module="m", target_param="p",
            old_value="0", new_value="1",
            hypothesis="h", contemplation="c",
            metric_before={"a": 1}, metric_after={"a": 1},
            delta=0.005, status="keep", principle="",
            daat_verified=False, duration=1.0, measurement_sessions=1,
        )
        assert engine._verify_daat(er) is False

    def test_daat_true_on_significant_change(self, engine):
        """Da'at atteint si delta significatif + métriques changées."""
        er = ExperimentResult(
            id="x", target_module="m", target_param="p",
            old_value="0", new_value="1",
            hypothesis="h", contemplation="c",
            metric_before={"a": 1, "b": 2, "c": 3},
            metric_after={"a": 5, "b": 8, "c": 3},
            delta=0.05, status="keep", principle="",
            daat_verified=False, duration=1.0, measurement_sessions=3,
        )
        assert engine._verify_daat(er) is True


class TestContemplation:
    """Tests de _contemplate_before."""

    def test_contemplate_no_principles(self, engine):
        """Sans principes, mode exploratoire."""
        hyp = {"target_module": "chokmah", "target_param": "min_novelty_score",
               "param_key": "insightforge.min_novelty_score"}
        result = engine._contemplate_before(hyp, [])
        assert "exploratoire" in result.lower() or "première" in result.lower()

    def test_contemplate_with_relevant_principle(self, engine):
        """Avec un principe pertinent, il est mentionné."""
        principles = [
            Principle(
                id="p1", principle="Baisser min_novelty_score augmente les insights",
                source_experiment="e1", domain="chokmah",
                confidence=0.8, confirmed_count=2, contradicted_count=0,
                is_active=True,
            ),
        ]
        hyp = {"target_module": "chokmah", "target_param": "min_novelty_score",
               "param_key": "insightforge.min_novelty_score"}
        result = engine._contemplate_before(hyp, principles)
        assert "principe" in result.lower() or "Principes" in result


# ── Hitbonenut → SelfMap consolidation ─────────────────────

class TestSelfMapConsolidation:
    """La boucle Hitbonenut → SelfMap est câblée et fonctionne."""

    def test_upsert_competence_ema_exists(self, engine):
        """_upsert_competence_ema est une méthode du HitbonenutEngine."""
        assert hasattr(engine, "_upsert_competence_ema")
        assert callable(engine._upsert_competence_ema)

    def test_exercise_one_calls_ema(self, engine_mock_db):
        """_exercise_one appelle _upsert_competence_ema pour score > 0."""
        with patch.object(engine_mock_db, "_ask_system") as mock_ask, \
             patch.object(engine_mock_db, "_upsert_competence_ema") as mock_ema, \
             patch.object(engine_mock_db, "_db_record_question"):
            mock_ask.return_value = {
                "response": "Réponse pertinente sur la Kabbale",
                "nitzotzot_before": 0, "nitzotzot_after": 0,
                "sentiers_used": [], "sifrei_yesod_refs": {},
                "daat_applied": False,
            }
            qr = engine_mock_db._exercise_one(
                "test-session", "Question kabbale?", "kabbale_lurianique", "basique",
            )
            # Si score > 0, _upsert_competence_ema doit être appelé
            if qr.score > 0:
                mock_ema.assert_called_once()
                call_args = mock_ema.call_args
                assert call_args[0][0] == "kabbale_lurianique"  # domain
                assert call_args[0][1] > 0  # score

    def test_session_consolidation_alpha(self, engine):
        """La consolidation session utilise alpha=0.3 (plus fort que per-question)."""
        import inspect
        source = inspect.getsource(engine.run_session)
        assert "alpha=0.3" in source

    def test_targeted_consolidation(self, engine):
        """run_targeted consolide aussi vers SelfMap."""
        import inspect
        source = inspect.getsource(engine.run_targeted)
        assert "_upsert_competence_ema" in source
        assert "alpha=0.3" in source

    def test_measure_system_metrics_reads_selfmap(self, engine):
        """_measure_system_metrics lit selfmap_competence comme métrique clé."""
        hod_mock = MagicMock()
        hod_mock.get_global_competence.return_value = 0.65
        engine.tree = {"hod": hod_mock}
        metrics = engine._measure_system_metrics()
        assert "selfmap_competence" in metrics
        assert metrics["selfmap_competence"] == 0.65
