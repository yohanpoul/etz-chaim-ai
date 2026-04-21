"""Tests du Shem HaMephorash — 72 trigrammes comme agents paramétrés."""

import pytest
from malakhim.shem.agents import (
    ShemAgent, SHEMOT_72, get_director, get_trigram,
    compute_balance, ColumnBalance, GEMATRIA,
)


class TestShemot72Data:
    def test_72_trigrams_exist(self):
        assert len(SHEMOT_72) == 72

    def test_first_trigram_is_vhv(self):
        assert SHEMOT_72[0] == (1, "והו", "VHV")

    def test_last_trigram_is_mvm(self):
        assert SHEMOT_72[71] == (72, "מום", "MVM")

    def test_duplicates_exist(self):
        """VHV apparaît aux positions 1 et 49 — propriété de la dérivation."""
        assert SHEMOT_72[0][2] == "VHV"
        assert SHEMOT_72[48][2] == "VHV"


class TestDirectors:
    def test_12_directors(self):
        """72 trigrammes / 6 = 12 directeurs."""
        directors = set(get_director(i) for i in range(1, 73))
        assert len(directors) == 12
        assert min(directors) == 0
        assert max(directors) == 11

    def test_first_six_same_director(self):
        for i in range(1, 7):
            assert get_director(i) == 0

    def test_seventh_new_director(self):
        assert get_director(7) == 1


class TestColumnBalance:
    def test_balance_computed(self):
        # והו = vav(6) + heh(5) + vav(6) → presque équilibré
        balance = compute_balance("והו")
        assert isinstance(balance, ColumnBalance)
        assert abs(balance.chesed_weight + balance.gevurah_weight + balance.tiferet_weight - 1.0) < 0.01

    def test_shin_dominant_chesed(self):
        # שאה = shin(300) + aleph(1) + heh(5) → Chesed dominant (shin est la PREMIÈRE lettre)
        balance = compute_balance("שאה")
        assert balance.dominant == "chesed"

    def test_gematria_values(self):
        assert GEMATRIA['א'] == 1
        assert GEMATRIA['י'] == 10
        assert GEMATRIA['ק'] == 100
        assert GEMATRIA['ת'] == 400


class TestShemAgent:
    def test_create_agent(self):
        agent = ShemAgent(1)
        assert agent.transliteration == "VHV"
        assert agent.director == 0

    def test_invalid_index_raises(self):
        with pytest.raises(ValueError):
            ShemAgent(0)
        with pytest.raises(ValueError):
            ShemAgent(73)

    def test_execute_with_fn(self):
        agent = ShemAgent(9)  # HZY — vision
        result = agent.execute(
            "observe this pattern",
            execute_fn=lambda ctx: f"observed: {ctx['input'][:30]}",
        )
        assert result.success
        assert "observed" in result.response
        assert result.metadata["shem_trigram"] == "HZY"
        assert result.metadata["shem_director"] == 1

    def test_style_injected_in_kavvanah(self):
        """Le trigramme injecte un style via la kavvanah."""
        captured = {}
        def spy_fn(ctx):
            return ctx.get("input", "")

        agent = ShemAgent(4)  # OLM — עלם dominant = ayin(70) en Chesed
        result = agent.execute("test", execute_fn=spy_fn)
        assert result.metadata["shem_balance"] in ("chesed", "gevurah", "tiferet")

    def test_repr(self):
        agent = ShemAgent(9)
        r = repr(agent)
        assert "HZY" in r
        assert "#9" in r

    def test_all_72_can_be_created(self):
        """Les 72 agents peuvent tous être instanciés sans erreur."""
        for i in range(1, 73):
            agent = ShemAgent(i)
            assert agent.index == i
