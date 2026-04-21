"""Tests HitbonenutJudge — évaluation des réponses kabbalistiques."""

from autojudge.domains.hitbonenut import HitbonenutJudge


class TestHitbonenutJudge:
    """HitbonenutJudge — loss function pour les réponses Hitbonenut."""

    def test_compute_metrics_returns_six_axes(self):
        judge = HitbonenutJudge()
        judge.set_context("Qu'est-ce que le Tzimtzum ?", "tzimtzum")
        m = judge.compute_metrics(
            "Le Tzimtzum est la contraction de l'Ein Sof. "
            "Luria enseigne que le Kav pénètre le Halal panui. "
            "Le Reshimu reste comme empreinte dans l'espace vide. "
            "Les Kelim se forment à partir de cette dynamique."
        )
        assert set(m.keys()) == {
            "kabbalistic_depth", "domain_keywords", "structure",
            "diversity", "relevance", "length",
        }
        assert all(0 <= v <= 1 for v in m.values())

    def test_empty_response_returns_zeros(self):
        judge = HitbonenutJudge()
        judge.set_context("test", "general")
        m = judge.compute_metrics("")
        assert all(v == 0.0 for v in m.values())

    def test_error_response_returns_zeros(self):
        judge = HitbonenutJudge()
        judge.set_context("test", "general")
        m = judge.compute_metrics("[erreur génération: timeout]")
        assert all(v == 0.0 for v in m.values())

    def test_kabbalistic_depth_high_for_rich_text(self):
        judge = HitbonenutJudge()
        judge.set_context("test", "general")
        rich = (
            "Le Zohar enseigne que les Sefirot s'organisent en Partzufim. "
            "Keter transcende Chokmah et Binah. Le Tzimtzum crée l'espace "
            "pour les Olamot d'Atziluth, Briah, Yetzirah et Assiah. "
            "Le Tikkun restaure les Kelim brisés par la Shevirah."
        )
        m = judge.compute_metrics(rich)
        assert m["kabbalistic_depth"] >= 0.5

    def test_kabbalistic_depth_low_for_generic_text(self):
        judge = HitbonenutJudge()
        judge.set_context("test", "general")
        generic = (
            "C'est une question intéressante qui mérite réflexion. "
            "On peut dire que ce sujet est complexe et multifacette. "
            "Il faut considérer plusieurs aspects de la question."
        )
        m = judge.compute_metrics(generic)
        assert m["kabbalistic_depth"] <= 0.2

    def test_domain_keywords_detected(self):
        judge = HitbonenutJudge()
        judge.set_context("Qu'est-ce que le Tzimtzum ?", "tzimtzum")
        text = (
            "Le Tzimtzum est la contraction de l'Ein Sof. "
            "Le Halal panui est l'espace vide créé par cette contraction. "
            "Le Reshimu et le Kav permettent la reconstruction. "
            "Le Din est le principe de limitation qui gouverne ce processus."
        )
        m = judge.compute_metrics(text)
        assert m["domain_keywords"] >= 0.5

    def test_compute_quality_weighted(self):
        judge = HitbonenutJudge()
        metrics = {
            "kabbalistic_depth": 0.8,
            "domain_keywords": 0.7,
            "structure": 0.6,
            "diversity": 0.5,
            "relevance": 0.9,
            "length": 0.8,
        }
        q = judge.compute_quality(metrics)
        expected = (0.8 * 0.30 + 0.7 * 0.25 + 0.6 * 0.15
                    + 0.5 * 0.10 + 0.9 * 0.10 + 0.8 * 0.10)
        assert abs(q - round(expected, 4)) < 0.001

    def test_generate_hypothesis_targets_weakness(self):
        judge = HitbonenutJudge()
        judge.set_context("test", "tzimtzum")
        text = "Oui c'est bien."
        hyp = judge.generate_hypothesis(text)
        assert isinstance(hyp, str)
        assert len(hyp) > 10

    def test_evaluate_returns_domain_score(self):
        judge = HitbonenutJudge()
        judge.set_context("Qu'est-ce que le Tzimtzum ?", "tzimtzum")
        response = (
            "Le Tzimtzum est la contraction de l'Ein Sof pour créer "
            "un espace vide (Halal panui). Selon Luria, le Kav pénètre "
            "cet espace et le Reshimu reste comme trace."
        )
        score = judge.evaluate(response, response)
        assert 0 <= score.quality <= 1
        assert isinstance(score.metrics, dict)
        assert score.explanation

    def test_loss_description(self):
        judge = HitbonenutJudge()
        desc = judge.get_loss_description()
        assert "kabbalistic_depth" in desc
        assert "domain_keywords" in desc

    def test_structure_detection(self):
        judge = HitbonenutJudge()
        judge.set_context("test", "general")

        unstructured = "Le Tzimtzum est important. C'est un concept clé."
        structured = (
            "**Introduction**\n\n"
            "Le Tzimtzum est un concept fondamental.\n\n"
            "**Développement**\n\n"
            "Premièrement, il implique une contraction.\n"
            "- Le Halal panui est créé\n"
            "- Le Kav pénètre l'espace\n\n"
            "Ensuite, le Reshimu reste comme trace."
        )

        m_un = judge.compute_metrics(unstructured)
        m_st = judge.compute_metrics(structured)
        assert m_st["structure"] > m_un["structure"]

    def test_set_context_updates_domain(self):
        judge = HitbonenutJudge()
        judge.set_context("Question A", "partzufim")
        assert judge._current_domain == "partzufim"
        assert judge._current_question == "Question A"

        judge.set_context("Question B", "olamot")
        assert judge._current_domain == "olamot"
