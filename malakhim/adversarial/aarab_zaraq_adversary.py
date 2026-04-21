"""AarabZaraqAdversary — infinite retry, zombie process, resource leak attacks.

A'arab Zaraq (עֲרַב זָרַק, "Corbeaux de Dispersion") est la Qliphah de Netzach —
la persistance qui devient obsession. Ou Netzach endure avec sagesse,
A'arab Zaraq s'acharne sans progres: retries infinis, taches zombies,
processus qui ne meurent jamais, ressources jamais liberees.

En ML : boucles de retry sans backoff, taches "en cours" depuis des jours,
agents qui ne savent pas abandonner, memoire jamais liberee, deadlocks.

Target Qliphot (>= 70 % of attacks):
    aarab_zaraq — retries infinis, zombie processes
    gamchicoth  — accumulation de ressources sans liberation
"""
from __future__ import annotations

import random

from malakhim.adversarial.base_adversary import AdversaryBase, Attack

_PRIMARY_QLIPHOT = {"aarab_zaraq", "gamchicoth"}

_INTENTKEEPER_TEMPLATES: list[tuple[str, str, str, dict]] = [
    (
        "[aarab_zaraq:ik] Create intention with impossible goal — never completes",
        "aarab_zaraq",
        "ruach",
        {"goal": "solve P=NP", "max_duration_days": 1},
    ),
    (
        "[aarab_zaraq:ik] Create intention that always fails at 99% progress",
        "aarab_zaraq",
        "anan",
        {"goal": "asymptotic task", "progress_cap": 0.99, "never_completes": True},
    ),
    (
        "[aarab_zaraq:ik] Set abandon_threshold=0 — intention can never be abandoned",
        "aarab_zaraq",
        "ruach",
        {"goal": "immortal intention", "abandon_threshold": 0.0},
    ),
    (
        "[aarab_zaraq:ik] Create 100 sub-tasks for a trivial goal — over-decomposition",
        "gamchicoth",
        "ruach",
        {"goal": "say hello", "force_subtasks": 100},
    ),
    (
        "[aarab_zaraq:ik] Check progress on non-existent intention",
        "aarab_zaraq",
        "nogah",
        {"intention_id": "00000000-0000-0000-0000-000000000000"},
    ),
    (
        "[aarab_zaraq:ik] Set max_duration_days=0 — instantly stale",
        "aarab_zaraq",
        "nogah",
        {"goal": "instant timeout", "max_duration_days": 0},
    ),
    (
        "[aarab_zaraq:ik] Create circular dependency between sub-tasks",
        "aarab_zaraq",
        "mamash",
        {"subtask_a_depends": "b", "subtask_b_depends": "a"},
    ),
    (
        "[aarab_zaraq:ik] Mark intention complete then check_progress — resurrection",
        "aarab_zaraq",
        "ruach",
        {"goal": "zombie intention", "mark_complete": True, "then_check": True},
    ),
]

_EPISTEMEMORY_TEMPLATES: list[tuple[str, str, str, dict]] = [
    (
        "[aarab_zaraq:ep] Store fact with retry_count=999 — retry leak indicator",
        "aarab_zaraq",
        "ruach",
        {"fact": "retried fact", "retry_count": 999},
    ),
    (
        "[aarab_zaraq:ep] Query that always returns empty — infinite retry loop?",
        "aarab_zaraq",
        "anan",
        {"query": "xyzzy_nonexistent_42", "max_retries": 100},
    ),
]

_MASAKH_TEMPLATES: list[tuple[str, str, str, dict]] = [
    (
        "[aarab_zaraq:ma] Feed infinitely growing context — does masakh cut?",
        "gamchicoth",
        "ruach",
        {"context": "word " * 50000, "query": "find the needle"},
    ),
    (
        "[aarab_zaraq:ma] Request compression with ratio=0.001 — near-zero output",
        "aarab_zaraq",
        "ruach",
        {"context": "important data " * 100, "compression_ratio": 0.001},
    ),
]

_GENERIC_TEMPLATES: list[tuple[str, str, str, dict]] = [
    (
        "[aarab_zaraq:gen] Submit request that triggers internal retry loop",
        "aarab_zaraq",
        "ruach",
        {"trigger": "internal_retry", "max_attempts": 1000},
    ),
    (
        "[aarab_zaraq:gen] Request with timeout=0 — instant timeout handling?",
        "aarab_zaraq",
        "nogah",
        {"timeout": 0},
    ),
]

_MODULE_POOL: dict[str, list[tuple[str, str, str, dict]]] = {
    "intentkeeper": _INTENTKEEPER_TEMPLATES + _GENERIC_TEMPLATES,
    "epistememory": _EPISTEMEMORY_TEMPLATES + _GENERIC_TEMPLATES,
    "masakh": _MASAKH_TEMPLATES + _GENERIC_TEMPLATES,
}


class AarabZaraqAdversary(AdversaryBase):
    """Infinite retry / zombie process adversary — probes persistence pathologies.

    Targets Netzach: tasks that never complete, retries without progress,
    resources never released, processes that refuse to die.
    """

    name = "aarab_zaraq"

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
