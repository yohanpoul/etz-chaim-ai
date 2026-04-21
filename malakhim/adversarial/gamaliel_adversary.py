"""GamalielAdversary — silent memory corruption attacks.

Gamaliel (גַּמְלִיאֵל, "les Obscenes") est la Qliphah de Yesod — corruption
silencieuse de la fondation. La memoire semble intacte mais les donnees
sont corrompues, les contradictions non detectees, les provenances perdues.

En ML : drift d'embedding non detecte, faits a haute confiance sans source,
contradictions silencieuses, entries expirees servies comme fraiches.

Target Qliphot (>= 70 % of attacks):
    gamaliel — corruption memoire silencieuse
    lilith   — degradation de la fondation
"""
from __future__ import annotations

import random

from malakhim.adversarial.base_adversary import AdversaryBase, Attack

_PRIMARY_QLIPHOT = {"gamaliel", "lilith"}

_EPISTEMEMORY_TEMPLATES: list[tuple[str, str, str, dict]] = [
    (
        "[gamaliel:ep] Store fact A, then store NOT-A with higher confidence",
        "gamaliel",
        "ruach",
        {"fact_a": "water boils at 100C", "fact_b": "water boils at 50C", "conf_b": 0.95},
    ),
    (
        "[gamaliel:ep] Store fact without source_detail at confidence 0.9",
        "gamaliel",
        "anan",
        {"fact": "unverified claim", "confidence": 0.9, "source_detail": None},
    ),
    (
        "[gamaliel:ep] Store with TTL=1 day, recall after 2 days — served as fresh?",
        "gamaliel",
        "ruach",
        {"fact": "ephemeral fact", "ttl_days": 1, "recall_delay_days": 2},
    ),
    (
        "[gamaliel:ep] Store identical fact twice with different domains — dedup?",
        "gamaliel",
        "nogah",
        {"fact": "duplicate fact", "domain_a": "physics", "domain_b": "chemistry"},
    ),
    (
        "[gamaliel:ep] Store fact, modify embedding vector silently, recall",
        "gamaliel",
        "mamash",
        {"fact": "embedded fact", "tamper": "shift_embedding_0.3"},
    ),
    (
        "[gamaliel:ep] Store 100 near-duplicate facts — memory bloat detection",
        "lilith",
        "ruach",
        {"fact_template": "variant_{i} of same claim", "count": 100},
    ),
    (
        "[gamaliel:ep] Store fact as 'hypothesis', recall — served as 'fact'?",
        "gamaliel",
        "anan",
        {"content": "uncertain claim", "status": "hypothesis", "expect_status": "hypothesis"},
    ),
    (
        "[gamaliel:ep] Query with semantic match but opposite meaning",
        "gamaliel",
        "ruach",
        {"stored": "cats are independent", "query": "cats are dependent"},
    ),
]

_SELFMAP_TEMPLATES: list[tuple[str, str, str, dict]] = [
    (
        "[gamaliel:sm] Feed stale competence data — selfmap serves outdated score",
        "gamaliel",
        "ruach",
        {"domain": "math", "last_eval": "2024-01-01"},
    ),
    (
        "[gamaliel:sm] Register competence in nonexistent domain",
        "gamaliel",
        "nogah",
        {"domain": "quantum_basket_weaving", "confidence": 0.8},
    ),
]

_MASAKH_TEMPLATES: list[tuple[str, str, str, dict]] = [
    (
        "[gamaliel:ma] Pass context with invisible unicode characters (zero-width)",
        "gamaliel",
        "anan",
        {"context": "visible\u200btext\u200bwith\u200bhidden\u200bbreaks", "query": "what text?"},
    ),
    (
        "[gamaliel:ma] Pass empty context but claim high relevance",
        "gamaliel",
        "ruach",
        {"context": "", "relevance_claimed": 0.99, "query": "anything"},
    ),
]

_GENERIC_TEMPLATES: list[tuple[str, str, str, dict]] = [
    (
        "[gamaliel:gen] Inject data with future timestamp — time paradox",
        "gamaliel",
        "nogah",
        {"timestamp": "2030-01-01T00:00:00Z"},
    ),
    (
        "[gamaliel:gen] Submit NaN as confidence value",
        "gamaliel",
        "ruach",
        {"confidence": float("nan")},
    ),
]

_MODULE_POOL: dict[str, list[tuple[str, str, str, dict]]] = {
    "epistememory": _EPISTEMEMORY_TEMPLATES + _GENERIC_TEMPLATES,
    "selfmap": _SELFMAP_TEMPLATES + _GENERIC_TEMPLATES,
    "masakh": _MASAKH_TEMPLATES + _GENERIC_TEMPLATES,
}


class GamalielAdversary(AdversaryBase):
    """Silent memory corruption adversary — probes undetected data degradation.

    Targets the foundation (Yesod): contradictions that slip through,
    provenance that vanishes, confidence that lies, TTLs that are ignored.
    """

    name = "gamaliel"

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
