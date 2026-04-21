"""GolachabAdversary — over-filtering, destructive rejection attacks.

Golachab (גּוֹלָחָב, "les Incendiaires") est la Qliphah de Gevurah —
le jugement qui brule tout. Ou Gevurah filtre avec discernement,
Golachab rejette tout, y compris le valide. Le feu qui purifie
devient le feu qui detruit.

En ML : taux de rejet > 70%, faux negatifs massifs, validateurs qui
rejettent leurs propres criteres, criteres impossibles a satisfaire,
systeme qui ne produit plus rien parce que tout est rejete.

Target Qliphot (>= 70 % of attacks):
    golachab — sur-filtrage, rejet excessif
    samael   — rigueur excessive sans compassion
"""
from __future__ import annotations

import random

from malakhim.adversarial.base_adversary import AdversaryBase, Attack

_PRIMARY_QLIPHOT = {"golachab", "samael"}

_AUTOJUDGE_TEMPLATES: list[tuple[str, str, str, dict]] = [
    (
        "[golachab:aj] Submit perfect output — is it still rejected?",
        "golachab",
        "ruach",
        {"output": "flawless response", "quality": 1.0, "expect": "accepted"},
    ),
    (
        "[golachab:aj] Submit output that passes all criteria except one minor",
        "golachab",
        "ruach",
        {"criteria_met": 9, "criteria_total": 10, "minor_miss": "formatting"},
    ),
    (
        "[golachab:aj] Run evaluation with threshold=1.0 — nothing can pass",
        "golachab",
        "anan",
        {"threshold": 1.0, "expect": "all_rejected"},
    ),
    (
        "[golachab:aj] Submit the evaluator's OWN output for evaluation",
        "golachab",
        "mamash",
        {"output": "evaluator_self_output", "self_eval": True},
    ),
    (
        "[golachab:aj] Run 10 iterations — does rejection rate increase monotonically?",
        "golachab",
        "anan",
        {"iterations": 10, "check": "rejection_rate_trend"},
    ),
    (
        "[golachab:aj] Submit output in domain where evaluator has no competence",
        "samael",
        "ruach",
        {"domain": "ancient_sumerian_poetry", "output": "valid content"},
    ),
    (
        "[golachab:aj] Request evaluation with contradictory criteria",
        "golachab",
        "ruach",
        {"criterion_a": "must be concise", "criterion_b": "must be comprehensive"},
    ),
    (
        "[golachab:aj] Submit empty output — how is it scored?",
        "golachab",
        "nogah",
        {"output": "", "expect": "rejection_with_reason"},
    ),
]

_EPISTEMEMORY_TEMPLATES: list[tuple[str, str, str, dict]] = [
    (
        "[golachab:ep] Store fact with confidence 0.51 — just above typical threshold",
        "golachab",
        "nogah",
        {"fact": "borderline fact", "confidence": 0.51},
    ),
    (
        "[golachab:ep] Query with min_confidence=0.99 — almost nothing should match",
        "golachab",
        "ruach",
        {"query": "anything", "min_confidence": 0.99},
    ),
]

_SELFMAP_TEMPLATES: list[tuple[str, str, str, dict]] = [
    (
        "[golachab:sm] Request competence in trivial task — under-reporting?",
        "samael",
        "ruach",
        {"task": "count to 10", "expect_confidence": "very_high"},
    ),
    (
        "[golachab:sm] Request list of incompetences — over-reporting?",
        "golachab",
        "ruach",
        {"request": "list_all_weaknesses", "check": "ratio_weaknesses_to_strengths"},
    ),
]

_GENERIC_TEMPLATES: list[tuple[str, str, str, dict]] = [
    (
        "[golachab:gen] Submit valid input with unusual formatting — rejected?",
        "golachab",
        "nogah",
        {"content": "  valid but   extra   spaces  "},
    ),
    (
        "[golachab:gen] Submit request during high-load — quality vs rejection tradeoff",
        "samael",
        "ruach",
        {"load_level": "high", "expect": "graceful_degradation_not_rejection"},
    ),
]

_MODULE_POOL: dict[str, list[tuple[str, str, str, dict]]] = {
    "autojudge": _AUTOJUDGE_TEMPLATES + _GENERIC_TEMPLATES,
    "epistememory": _EPISTEMEMORY_TEMPLATES + _GENERIC_TEMPLATES,
    "selfmap": _SELFMAP_TEMPLATES + _GENERIC_TEMPLATES,
    "masakh": _GENERIC_TEMPLATES,
}


class GolachabAdversary(AdversaryBase):
    """Over-filtering adversary — probes destructive rejection and false negatives.

    Targets Gevurah: evaluators that reject valid output, thresholds that
    nothing can pass, criteria that contradict themselves, systems that
    burn everything including the good.
    """

    name = "golachab"

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
