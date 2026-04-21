"""Tests Reshimo — le cycle du Nehar Dinur se ferme."""

from malakhim.reshimo import (
    record_reshimo, get_reshimot_for_domain,
    get_cycle_insights, clear, Reshimo,
)


class TestRecordReshimo:
    """La trace du Malakh dissous est enregistrée."""

    def setup_method(self):
        clear()

    def test_record_creates_reshimo(self):
        r = record_reshimo(
            result_metadata={"routing": {"nature": "analytic", "olam": "yetzirah"}, "shem_index": 42},
            response="une réponse", score=0.8, success=True,
            incomplete=False, prompt="analyse ce code python",
        )
        assert isinstance(r, Reshimo)
        assert r.nature == "analytic"
        assert r.shem_index == 42
        assert r.score == 0.8

    def test_reshimot_accumulate(self):
        for i in range(5):
            record_reshimo(
                result_metadata={"routing": {"nature": "execution", "olam": "assiah"}},
                response="r", score=0.5 + i * 0.1, success=True,
                incomplete=False, prompt=f"tâche {i}",
            )
        results = get_reshimot_for_domain("general")
        assert len(results) == 5

    def test_domain_filtering(self):
        record_reshimo(
            result_metadata={"routing": {"nature": "analytic", "olam": "briah", "domain": "code"}},
            response="r", score=0.8, success=True, incomplete=False,
            prompt="analyse code",
        )
        record_reshimo(
            result_metadata={"routing": {"nature": "analytic", "olam": "briah", "domain": "security"}},
            response="r", score=0.7, success=True, incomplete=False,
            prompt="audit sécurité",
        )
        assert len(get_reshimot_for_domain("code")) == 1
        assert len(get_reshimot_for_domain("security")) == 1


class TestCycleInsights:
    """Le cycle extrait des leçons des Malakhim dissous."""

    def setup_method(self):
        clear()

    def test_empty_domain_no_insights(self):
        assert get_cycle_insights("empty") == {}

    def test_success_rate_computed(self):
        for i in range(10):
            record_reshimo(
                result_metadata={"routing": {"nature": "execution", "olam": "yetzirah"}},
                response="r", score=0.8 if i < 7 else 0.2,
                success=i < 7, incomplete=False, prompt="tâche test",
            )
        insights = get_cycle_insights("general")
        assert insights["total_reshimot"] == 10
        assert insights["success_rate"] == 0.7

    def test_recurring_excess_detected(self):
        for _ in range(5):
            record_reshimo(
                result_metadata={
                    "routing": {"nature": "analytic", "olam": "briah"},
                    "samael": {"sephirah_source": "gevurah"},
                },
                response="r", score=0.3, success=False,
                incomplete=False, prompt="test",
            )
        insights = get_cycle_insights("general")
        assert insights["recurring_excess"] == "gevurah"

    def test_best_shem_tracked(self):
        # Shem #9 réussit bien
        for _ in range(3):
            record_reshimo(
                result_metadata={
                    "routing": {"nature": "execution", "olam": "yetzirah"},
                    "shem_index": 9,
                },
                response="r", score=0.9, success=True,
                incomplete=False, prompt="test",
            )
        # Shem #20 réussit moins
        record_reshimo(
            result_metadata={
                "routing": {"nature": "execution", "olam": "yetzirah"},
                "shem_index": 20,
            },
            response="r", score=0.4, success=True,
            incomplete=False, prompt="test",
        )
        insights = get_cycle_insights("general")
        assert insights["best_shem"] == 9
