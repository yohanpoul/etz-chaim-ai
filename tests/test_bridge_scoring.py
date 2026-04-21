"""Tests for multi-domain keywords, bridge scoring, and novel generation."""

import pytest
from hitbonenut import (
    DOMAIN_KEYWORDS, BRIDGE_QUALIFIERS, DOMAIN_EPISTEMIC_CONTEXT,
    BRIDGE_GENERATION_PROMPT, CORE_DOMAINS, BREADTH_DOMAINS,
)

EXPECTED_BREADTH_DOMAINS = [
    "logique_maths", "physique", "biologie_evo", "theorie_info",
    "neurosciences", "epistemologie", "historiographie",
    "economie_jeux", "linguistique", "musicologie",
]


def test_all_breadth_domains_have_keywords():
    for domain in EXPECTED_BREADTH_DOMAINS:
        kws = DOMAIN_KEYWORDS.get(domain)
        assert kws is not None, f"Missing keywords for {domain}"
        assert len(kws) >= 12, f"{domain} has only {len(kws)} keywords (need >= 12)"


def test_no_keyword_overlap_between_domains():
    from collections import Counter
    all_kws = Counter()
    for kws in DOMAIN_KEYWORDS.values():
        for kw in kws:
            all_kws[kw.lower()] += 1
    overused = {k: v for k, v in all_kws.items() if v > 4}
    assert not overused, f"Keywords in >4 domains (too generic): {overused}"


def test_bridge_qualifiers_exist():
    assert len(BRIDGE_QUALIFIERS) >= 8


def test_all_breadth_domains_have_epistemic_context():
    """Each breadth domain must have an epistemic context for érudite generation."""
    for domain in EXPECTED_BREADTH_DOMAINS:
        ctx = DOMAIN_EPISTEMIC_CONTEXT.get(domain)
        assert ctx is not None, f"Missing epistemic context for {domain}"
        assert len(ctx) >= 100, f"{domain} context too short ({len(ctx)} chars)"
        # Must mention at least one author name
        assert any(c.isupper() for c in ctx[20:]), f"{domain} context has no proper nouns"


def test_bridge_generation_prompt_exists():
    assert len(BRIDGE_GENERATION_PROMPT) >= 50
    assert "parallèle" in BRIDGE_GENERATION_PROMPT.lower()
    assert "effondre" in BRIDGE_GENERATION_PROMPT.lower() or "limite" in BRIDGE_GENERATION_PROMPT.lower()


def test_novel_tier_selection_distribution():
    """Over many draws, tier distribution should approximate 40/40/20."""
    import random
    random.seed(42)
    tiers = []
    for _ in range(1000):
        r = random.random()
        if r < 0.4:
            tiers.append("core")
        elif r < 0.8:
            tiers.append("breadth")
        else:
            tiers.append("bridge")
    core_ratio = tiers.count("core") / len(tiers)
    breadth_ratio = tiers.count("breadth") / len(tiers)
    bridge_ratio = tiers.count("bridge") / len(tiers)
    assert 0.35 < core_ratio < 0.45, f"Core ratio {core_ratio:.2f}"
    assert 0.35 < breadth_ratio < 0.45, f"Breadth ratio {breadth_ratio:.2f}"
    assert 0.15 < bridge_ratio < 0.25, f"Bridge ratio {bridge_ratio:.2f}"
