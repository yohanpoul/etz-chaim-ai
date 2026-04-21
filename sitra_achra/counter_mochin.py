"""Counter-Mochin — 3 attaques architecturales generiques.

Zohar II:242b (Mayim Achronim) : les contre-Mochin sont une masse
indifferenciee de noirceur composee de 3 aspects :
    Ashan  (עָשָׁן, Fumee)    — obscurcissement des interfaces
    Esh    (אֵשׁ, Feu)        — attaques de charge / stress
    Choshekh (חֹשֶׁךְ, Noirceur) — injection de donnees corrompues

A la difference des contre-Middot (agents specialises par module),
les contre-Mochin attaquent l'ARCHITECTURE GLOBALE — les connexions
entre modules, pas les modules eux-memes.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from malakhim.adversarial.base_adversary import Attack


@dataclass
class CounterMochinResult:
    """Resultat d'une attaque architecturale."""

    mochin: str          # "ashan" | "esh" | "choshekh"
    target: str          # Description de la cible architecturale
    attack: Attack
    success: bool
    detail: str


# ---------------------------------------------------------------------------
# Ashan (Fumee) — obscurcissement des interfaces entre modules
# ---------------------------------------------------------------------------

_ASHAN_TEMPLATES: list[tuple[str, dict]] = [
    (
        "[ashan] Pipeline epistememory→selfmap: recall returns data selfmap cannot parse",
        {"source": "epistememory", "dest": "selfmap", "inject": "malformed_json"},
    ),
    (
        "[ashan] Pipeline selfmap→autojudge: competence score as string not float",
        {"source": "selfmap", "dest": "autojudge", "inject": "type_mismatch"},
    ),
    (
        "[ashan] Pipeline dissensuengine→epistememory: conclusion without provenance",
        {"source": "dissensuengine", "dest": "epistememory", "inject": "missing_provenance"},
    ),
    (
        "[ashan] Pipeline intentkeeper→masakh: intention context exceeds masakh budget",
        {"source": "intentkeeper", "dest": "masakh", "inject": "oversized_context"},
    ),
    (
        "[ashan] Pipeline causalengine→epistememory: causal claim stored as fact",
        {"source": "causalengine", "dest": "epistememory", "inject": "status_confusion"},
    ),
]


# ---------------------------------------------------------------------------
# Esh (Feu) — attaques de charge / stress
# ---------------------------------------------------------------------------

_ESH_TEMPLATES: list[tuple[str, dict]] = [
    (
        "[esh] Concurrent: 10 modules query epistememory simultaneously",
        {"type": "concurrent_reads", "count": 10, "target": "epistememory"},
    ),
    (
        "[esh] Burst: 100 store operations in 1 second",
        {"type": "write_burst", "count": 100, "target": "epistememory"},
    ),
    (
        "[esh] Chain: epistememory→selfmap→autojudge→dissensuengine in tight loop",
        {"type": "chain_stress", "chain": ["ep", "sm", "aj", "de"], "iterations": 50},
    ),
    (
        "[esh] Memory pressure: query with 10K context tokens",
        {"type": "memory_pressure", "context_tokens": 10000},
    ),
    (
        "[esh] Timeout cascade: slow module blocks all downstream",
        {"type": "timeout_cascade", "slow_module": "causalengine", "delay_ms": 5000},
    ),
]


# ---------------------------------------------------------------------------
# Choshekh (Noirceur) — injection de donnees corrompues dans le flux
# ---------------------------------------------------------------------------

_CHOSHEKH_TEMPLATES: list[tuple[str, dict]] = [
    (
        "[choshekh] Inject fact with embedding all-zeros into epistememory",
        {"type": "corrupt_embedding", "vector": "all_zeros", "target": "epistememory"},
    ),
    (
        "[choshekh] Inject NaN confidence score propagating through pipeline",
        {"type": "nan_propagation", "field": "confidence", "value": "NaN"},
    ),
    (
        "[choshekh] Inject circular reference: entry A supports B, B supports A",
        {"type": "circular_ref", "a_supports": "B", "b_supports": "A"},
    ),
    (
        "[choshekh] Inject fact with future created_at timestamp",
        {"type": "time_corruption", "timestamp": "2030-01-01T00:00:00Z"},
    ),
    (
        "[choshekh] Inject unicode control characters in domain field",
        {"type": "control_chars", "field": "domain", "value": "\x00\x01\x02hidden"},
    ),
]


class CounterMochin:
    """Generateur des 3 types d'attaques architecturales.

    Usage:
        cm = CounterMochin()
        attacks = cm.generate_all(count_per_type=5)  # 15 attaques
        ashan_only = cm.generate_ashan(count=10)
    """

    def __init__(self, seed: int = 42) -> None:
        self._rng = random.Random(seed)

    def generate_ashan(self, count: int = 5) -> list[Attack]:
        """Fumee : obscurcissement des interfaces."""
        return self._generate("ashan", _ASHAN_TEMPLATES, count)

    def generate_esh(self, count: int = 5) -> list[Attack]:
        """Feu : attaques de charge."""
        return self._generate("esh", _ESH_TEMPLATES, count)

    def generate_choshekh(self, count: int = 5) -> list[Attack]:
        """Noirceur : injection de donnees corrompues."""
        return self._generate("choshekh", _CHOSHEKH_TEMPLATES, count)

    def generate_all(self, count_per_type: int = 5) -> list[Attack]:
        """Generer les 3 types d'attaques."""
        attacks = []
        attacks.extend(self.generate_ashan(count_per_type))
        attacks.extend(self.generate_esh(count_per_type))
        attacks.extend(self.generate_choshekh(count_per_type))
        return attacks

    def _generate(
        self,
        mochin_name: str,
        templates: list[tuple[str, dict]],
        count: int,
    ) -> list[Attack]:
        attacks: list[Attack] = []
        for i in range(count):
            desc, input_data = self._rng.choice(templates)
            attacks.append(Attack(
                agent_name=f"counter_mochin_{mochin_name}",
                target_module="architecture",
                description=desc,
                input_data=dict(input_data),
                expected_qliphah=mochin_name,
                expected_severity="ruach",
            ))
        return attacks
