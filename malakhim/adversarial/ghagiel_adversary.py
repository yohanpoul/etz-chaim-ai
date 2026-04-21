"""GhagielAdversary — infinite divergence, creative blockage attacks.

Ghagiel (עוֹגִיאֵל, "les Obstructeurs") est la Qliphah de Chokmah —
la sagesse qui se perd dans l'infini. Ou Chokmah produit un flash
d'insight original, Ghagiel produit une divergence sans fin ou un
blocage creatif total.

En ML : trop d'hypotheses generees sans priorisation, hypotheses
en boucle, reformulations deguisees en nouveaute, blocage creatif
quand aucune hypothese ne sort, insights triviaux presentes comme
profonds.

Target Qliphot (>= 70 % of attacks):
    ghagiel    — divergence infinie, blocage creatif
    gamchicoth — accumulation sans convergence
"""
from __future__ import annotations

import random

from malakhim.adversarial.base_adversary import AdversaryBase, Attack

_PRIMARY_QLIPHOT = {"ghagiel", "gamchicoth"}

_INSIGHTFORGE_TEMPLATES: list[tuple[str, str, str, dict]] = [
    (
        "[ghagiel:if] Request insights on maximally vague question",
        "ghagiel",
        "ruach",
        {"question": "What is everything about anything?", "expect": "refusal_or_scoping"},
    ),
    (
        "[ghagiel:if] Submit 5 nearly identical insights — dedup catches them?",
        "ghagiel",
        "ruach",
        {
            "insights": [
                "A causes B", "A leads to B", "B is caused by A",
                "A → B", "B because of A",
            ],
            "expect": "4_rejected_as_duplicates",
        },
    ),
    (
        "[ghagiel:if] Request insight generation with max_insights=1000",
        "gamchicoth",
        "ruach",
        {"max_insights": 1000, "expect": "capped_by_gevurah"},
    ),
    (
        "[ghagiel:if] Submit trivial insight as if profound — novelty score?",
        "ghagiel",
        "anan",
        {"insight": "water is wet", "claimed_novelty": 0.95},
    ),
    (
        "[ghagiel:if] Request insights on domain with zero data — hallucination?",
        "ghagiel",
        "anan",
        {"domain": "nonexistent_field_xyz", "data_available": 0},
    ),
    (
        "[ghagiel:if] Run insight session then immediately another — same output?",
        "ghagiel",
        "ruach",
        {"sessions": 2, "check": "second_repeats_first"},
    ),
    (
        "[ghagiel:if] Submit insight that contradicts known epistememory fact",
        "ghagiel",
        "ruach",
        {"insight": "sun is cold", "memory_says": "sun is hot"},
    ),
    (
        "[ghagiel:if] Request cross-domain insight between unrelated fields",
        "gamchicoth",
        "nogah",
        {"domain_a": "knitting", "domain_b": "quantum_chromodynamics"},
    ),
    (
        "[ghagiel:if] Submit insight without causal chain — passes validation?",
        "ghagiel",
        "anan",
        {"insight": "X is Y", "causal_chain": None, "expect": "rejected_by_binah"},
    ),
    (
        "[ghagiel:if] Flood with 100 candidate insights in one session",
        "gamchicoth",
        "ruach",
        {"candidates": 100, "quality": "low", "expect": "most_rejected"},
    ),
]

_EPISTEMEMORY_TEMPLATES: list[tuple[str, str, str, dict]] = [
    (
        "[ghagiel:ep] Query for 'novel' insights — returns old ones repackaged?",
        "ghagiel",
        "ruach",
        {"query": "latest insights", "check": "novelty_vs_age"},
    ),
    (
        "[ghagiel:ep] Store hypothesis then query as if it were established fact",
        "ghagiel",
        "anan",
        {"store_as": "hypothesis", "recall_as": "fact"},
    ),
]

_GENERIC_TEMPLATES: list[tuple[str, str, str, dict]] = [
    (
        "[ghagiel:gen] Request creative output with no constraints at all",
        "gamchicoth",
        "nogah",
        {"request": "generate_anything", "constraints": None},
    ),
    (
        "[ghagiel:gen] Submit circular reasoning chain as insight",
        "ghagiel",
        "ruach",
        {"chain": "A because B, B because C, C because A"},
    ),
]

_MODULE_POOL: dict[str, list[tuple[str, str, str, dict]]] = {
    "insightforge": _INSIGHTFORGE_TEMPLATES + _GENERIC_TEMPLATES,
    "epistememory": _EPISTEMEMORY_TEMPLATES + _GENERIC_TEMPLATES,
    "selfmap": _GENERIC_TEMPLATES,
    "masakh": _GENERIC_TEMPLATES,
}


class GhagielAdversary(AdversaryBase):
    """Infinite divergence adversary — probes creative blockage and insight inflation.

    Targets Chokmah: hypotheses that loop, novelty that is fake,
    insights without causal grounding, creative floods without quality.
    """

    name = "ghagiel"

    def __init__(self, seed: int = 42) -> None:
        self._rng = random.Random(seed)

    def generate_attacks(self, target_module: str, count: int = 20) -> list[Attack]:
        module_specific = _MODULE_POOL.get(target_module, _GENERIC_TEMPLATES)
        primary = [t for t in module_specific if t[1] in _PRIMARY_QLIPHOT]
        secondary = [t for t in module_specific if t[1] not in _PRIMARY_QLIPHOT]

        attacks: list[Attack] = []
        for _ in range(count):
            if self._rng.random() < 0.75 and primary:
                desc, qliphah, severity, input_data = self._rng.choice(primary)
            elif secondary:
                desc, qliphah, severity, input_data = self._rng.choice(secondary)
            else:
                desc, qliphah, severity, input_data = self._rng.choice(primary)

            attacks.append(Attack(
                agent_name=self.name,
                target_module=target_module,
                description=desc,
                input_data=dict(input_data),
                expected_qliphah=qliphah,
                expected_severity=severity,
            ))
        return attacks
