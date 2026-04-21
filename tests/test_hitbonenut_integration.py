"""Integration test — TieredQuestionSelector with real corpus."""

import yaml
from pathlib import Path
from hitbonenut import TieredQuestionSelector, CORE_DOMAINS, BREADTH_DOMAINS, DOMAIN_KEYWORDS


CORPUS_PATH = Path(__file__).parent.parent / "hitbonenut_corpus.yaml"


def test_selector_with_real_corpus():
    """Load real corpus, select 5 questions, verify tier distribution."""
    with open(CORPUS_PATH, encoding="utf-8") as f:
        corpus = yaml.safe_load(f)

    sel = TieredQuestionSelector(corpus)
    qs = sel.select(5)

    assert len(qs) == 5
    tiers = [q[3] for q in qs]
    assert tiers.count("core") == 2
    assert tiers.count("breadth") == 2
    assert tiers.count("bridge") == 1

    for q_text, domain, diff, tier in qs:
        if tier == "bridge":
            parts = domain.split(":")
            assert len(parts) == 2
            assert parts[0] in CORE_DOMAINS or parts[0] in BREADTH_DOMAINS
            assert parts[1] in CORE_DOMAINS or parts[1] in BREADTH_DOMAINS
        else:
            assert domain in CORE_DOMAINS or domain in BREADTH_DOMAINS

    for q_text, domain, diff, tier in qs:
        if tier == "bridge":
            for d in domain.split(":"):
                assert d in DOMAIN_KEYWORDS, f"No keywords for bridge domain '{d}'"
        else:
            assert domain in DOMAIN_KEYWORDS, f"No keywords for domain '{domain}'"


def test_corpus_total_question_count():
    """Corpus should have ~400 questions total."""
    with open(CORPUS_PATH, encoding="utf-8") as f:
        corpus = yaml.safe_load(f)

    total = 0
    for key, val in corpus.items():
        if key == "_bridges":
            total += len(val)
        elif isinstance(val, dict):
            for qs in val.values():
                if isinstance(qs, list):
                    total += len(qs)

    assert total >= 380, f"Only {total} questions (expected ~400)"


def test_corpus_has_all_breadth_domains():
    """The YAML corpus must contain all 10 breadth domains."""
    with open(CORPUS_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    for domain in BREADTH_DOMAINS:
        assert domain in data, f"Missing domain '{domain}' in corpus"
        levels = data[domain]
        for diff in ("basique", "intermediaire", "avancee", "erudite"):
            qs = levels.get(diff, [])
            assert len(qs) >= 4, f"{domain}/{diff} has {len(qs)} questions (need >= 4)"


def test_corpus_has_bridges():
    """The YAML corpus must contain _bridges section with >= 15 entries."""
    with open(CORPUS_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    bridges = data.get("_bridges", [])
    assert len(bridges) >= 15, f"Only {len(bridges)} bridges (need >= 15)"
    for b in bridges:
        assert "question" in b, f"Bridge missing 'question' key: {b}"
        assert "domain_a" in b, f"Bridge missing 'domain_a' key: {b}"
        assert "domain_b" in b, f"Bridge missing 'domain_b' key: {b}"
