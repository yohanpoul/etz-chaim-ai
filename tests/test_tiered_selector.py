"""Tests for TieredQuestionSelector — round-robin tiered question selection."""

import pytest
from hitbonenut import TieredQuestionSelector, CORE_DOMAINS, BREADTH_DOMAINS


@pytest.fixture
def corpus():
    c = {}
    for domain in CORE_DOMAINS:
        c[domain] = {
            "basique": [f"{domain} basique Q1", f"{domain} basique Q2"],
            "intermediaire": [f"{domain} inter Q1", f"{domain} inter Q2"],
            "avancee": [f"{domain} avancee Q1", f"{domain} avancee Q2"],
            "erudite": [f"{domain} erudite Q1", f"{domain} erudite Q2"],
        }
    for domain in BREADTH_DOMAINS:
        c[domain] = {
            "basique": [f"{domain} basique Q1", f"{domain} basique Q2"],
            "intermediaire": [f"{domain} inter Q1", f"{domain} inter Q2"],
            "avancee": [f"{domain} avancee Q1", f"{domain} avancee Q2"],
            "erudite": [f"{domain} erudite Q1", f"{domain} erudite Q2"],
        }
    c["_bridges"] = [
        {"question": f"Bridge Q{i}", "domain_a": "kabbale_lurianique", "domain_b": "physique"}
        for i in range(15)
    ]
    return c


def test_select_returns_5_questions(corpus):
    sel = TieredQuestionSelector(corpus)
    qs = sel.select(5)
    assert len(qs) == 5


def test_select_tier_distribution(corpus):
    sel = TieredQuestionSelector(corpus)
    qs = sel.select(5)
    tiers = [q[3] for q in qs]
    assert tiers.count("core") == 2
    assert tiers.count("breadth") == 2
    assert tiers.count("bridge") == 1


def test_select_tuple_format(corpus):
    sel = TieredQuestionSelector(corpus)
    qs = sel.select(5)
    for q_text, domain, difficulty, tier in qs:
        assert isinstance(q_text, str) and len(q_text) > 0
        assert isinstance(domain, str) and len(domain) > 0
        assert difficulty in ("basique", "intermediaire", "avancee", "erudite")
        assert tier in ("core", "breadth", "bridge")


def test_round_robin_covers_all_core_domains(corpus):
    sel = TieredQuestionSelector(corpus)
    seen_core = set()
    for _ in range(50):
        qs = sel.select(5)
        for q_text, domain, diff, tier in qs:
            if tier == "core":
                seen_core.add(domain)
    assert seen_core == set(CORE_DOMAINS)


def test_round_robin_covers_all_breadth_domains(corpus):
    sel = TieredQuestionSelector(corpus)
    seen_breadth = set()
    for _ in range(50):
        qs = sel.select(5)
        for q_text, domain, diff, tier in qs:
            if tier == "breadth":
                seen_breadth.add(domain)
    assert seen_breadth == set(BREADTH_DOMAINS)


def test_bridge_questions_have_domain_metadata(corpus):
    sel = TieredQuestionSelector(corpus)
    qs = sel.select(5)
    bridges = [q for q in qs if q[3] == "bridge"]
    assert len(bridges) == 1
    assert ":" in bridges[0][1]


def test_difficulty_weighting_favors_erudite(corpus):
    sel = TieredQuestionSelector(corpus)
    diffs = []
    for _ in range(200):
        qs = sel.select(5)
        for q_text, domain, diff, tier in qs:
            if tier != "bridge":
                diffs.append(diff)
    erudite_ratio = diffs.count("erudite") / len(diffs)
    assert 0.25 < erudite_ratio < 0.55, f"Erudite ratio {erudite_ratio:.2f} out of range"


def test_empty_corpus_returns_empty():
    sel = TieredQuestionSelector({})
    qs = sel.select(5)
    assert qs == []
