"""Tests Counter-Mochin — 3 attaques architecturales."""

from sitra_achra.counter_mochin import CounterMochin


class TestCounterMochin:

    def test_generate_ashan(self):
        cm = CounterMochin()
        attacks = cm.generate_ashan(count=3)
        assert len(attacks) == 3
        assert all(a.agent_name == "counter_mochin_ashan" for a in attacks)
        assert all(a.target_module == "architecture" for a in attacks)

    def test_generate_esh(self):
        cm = CounterMochin()
        attacks = cm.generate_esh(count=3)
        assert len(attacks) == 3
        assert all(a.agent_name == "counter_mochin_esh" for a in attacks)

    def test_generate_choshekh(self):
        cm = CounterMochin()
        attacks = cm.generate_choshekh(count=3)
        assert len(attacks) == 3
        assert all(a.agent_name == "counter_mochin_choshekh" for a in attacks)

    def test_generate_all(self):
        cm = CounterMochin()
        attacks = cm.generate_all(count_per_type=4)
        assert len(attacks) == 12  # 3 types × 4

        agents = {a.agent_name for a in attacks}
        assert "counter_mochin_ashan" in agents
        assert "counter_mochin_esh" in agents
        assert "counter_mochin_choshekh" in agents

    def test_attacks_have_input_data(self):
        cm = CounterMochin()
        attacks = cm.generate_all(count_per_type=2)
        for a in attacks:
            assert isinstance(a.input_data, dict)
            assert len(a.input_data) > 0

    def test_reproducibility(self):
        """Meme seed → memes attaques."""
        cm1 = CounterMochin(seed=123)
        cm2 = CounterMochin(seed=123)
        a1 = cm1.generate_all(count_per_type=3)
        a2 = cm2.generate_all(count_per_type=3)
        assert [a.description for a in a1] == [a.description for a in a2]
