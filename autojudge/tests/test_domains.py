"""Tests DomainJudge — WritingJudge + CodeJudge."""

from autojudge.domains.writing import WritingJudge
from autojudge.domains.code import CodeJudge


class TestWritingJudge:
    """WritingJudge — loss function de l'écriture."""

    def test_compute_metrics_returns_five_axes(self):
        judge = WritingJudge()
        m = judge.compute_metrics("This is a simple test sentence. It works well.")
        assert set(m.keys()) == {"readability", "diversity", "structure", "concision", "precision"}
        assert all(0 <= v <= 1 for v in m.values())

    def test_empty_text_returns_zeros(self):
        judge = WritingJudge()
        m = judge.compute_metrics("")
        assert all(v == 0.0 for v in m.values())

    def test_filler_removal_improves_concision(self):
        judge = WritingJudge()
        text = "This is really very basically just a totally simple test that is absolutely completely obvious."
        m_before = judge.compute_metrics(text)
        cleaned = judge.apply_modification(text, "Supprimer les mots de remplissage pour gagner en concision")
        m_after = judge.compute_metrics(cleaned)
        assert m_after["concision"] >= m_before["concision"]

    def test_evaluate_returns_domain_score(self):
        judge = WritingJudge()
        orig = "This is really very basically just a test. It is totally completely obvious. Actually it is really simple."
        modified = "This is a test. It is obvious. It is simple."
        score = judge.evaluate(orig, modified)
        assert 0 <= score.quality <= 1
        assert isinstance(score.metrics, dict)
        assert score.explanation  # non-empty

    def test_generate_hypothesis_targets_weakness(self):
        judge = WritingJudge()
        text = "This really very basically just totally completely absolutely obviously clearly essentially practically fundamentally test."
        hyp = judge.generate_hypothesis(text)
        assert isinstance(hyp, str)
        assert len(hyp) > 5

    def test_loss_description(self):
        judge = WritingJudge()
        desc = judge.get_loss_description()
        assert "readability" in desc
        assert "diversity" in desc

    def test_split_long_sentences(self):
        judge = WritingJudge()
        long_text = (
            "The quick brown fox jumps over the lazy dog, "
            "and then proceeds to run across the vast meadow "
            "while the sun sets behind the distant mountains "
            "creating a beautiful golden light across the landscape."
        )
        result = judge.apply_modification(long_text, "Simplifier les phrases longues")
        assert len(result) > 0

    def test_add_structure(self):
        judge = WritingJudge()
        flat = "First point here. Second point here. Third point here. Fourth point here."
        result = judge.apply_modification(flat, "Ajouter de la structure avec des paragraphes")
        assert "\n\n" in result


class TestCodeJudge:
    """CodeJudge — loss function du code."""

    def test_compute_metrics_valid_python(self):
        judge = CodeJudge()
        code = "def hello():\n    return 'world'\n"
        m = judge.compute_metrics(code)
        assert set(m.keys()) == {"syntax", "complexity", "readability", "modularity", "concision"}
        assert m["syntax"] == 1.0

    def test_syntax_error_detected(self):
        judge = CodeJudge()
        bad_code = "def hello(\n    return 'world'"
        m = judge.compute_metrics(bad_code)
        assert m["syntax"] == 0.0

    def test_empty_code_returns_zeros(self):
        judge = CodeJudge()
        m = judge.compute_metrics("")
        assert all(v == 0.0 for v in m.values())

    def test_evaluate_returns_domain_score(self):
        judge = CodeJudge()
        orig = "import os\nimport sys\n\ndef hello():\n    return 'world'\n"
        modified = "def hello():\n    return 'world'\n"
        score = judge.evaluate(orig, modified)
        assert 0 <= score.quality <= 1
        assert isinstance(score.metrics, dict)

    def test_remove_unused_imports(self):
        judge = CodeJudge()
        code = "import os\nimport sys\n\ndef hello():\n    return os.path.join('a', 'b')\n"
        result = judge.apply_modification(code, "Supprimer les imports inutilisés")
        assert "import os" in result
        assert "import sys" not in result

    def test_generate_hypothesis(self):
        judge = CodeJudge()
        code = "def f():\n    if True:\n        if True:\n            if True:\n                if True:\n                    pass\n"
        hyp = judge.generate_hypothesis(code)
        assert isinstance(hyp, str)

    def test_loss_description(self):
        judge = CodeJudge()
        desc = judge.get_loss_description()
        assert "syntax" in desc
        assert "complexity" in desc

    def test_high_complexity_penalized(self):
        judge = CodeJudge()
        simple = "def f():\n    return 1\n"
        nested = "def f():\n    if True:\n        for i in range(10):\n            while True:\n                if i > 5:\n                    try:\n                        pass\n                    except:\n                        pass\n"
        m_simple = judge.compute_metrics(simple)
        m_nested = judge.compute_metrics(nested)
        assert m_simple["complexity"] > m_nested["complexity"]
