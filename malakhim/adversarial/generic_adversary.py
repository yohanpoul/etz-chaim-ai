"""GenericAdversary — blind baseline adversary for Qliphoth testing.

Generates type-agnostic, module-agnostic attacks drawn from a fixed palette
of 12 templates.  It has NO knowledge of internal module logic; it represents
the floor that every specialized adversary must beat.

Kabbalistic framing
--------------------
This is the Klipat Nogah in pure form: undifferentiated adversarial pressure
that precedes any intentional targeting.  Like the primordial chaos before
Birur (refinement), it probes without discernment — exposing only the most
obvious failure modes.  Specialized adversaries (Samael, Gamaliel, …) refine
this undifferentiated pressure into targeted strikes.
"""
from __future__ import annotations

import random
from typing import Any

from malakhim.adversarial.base_adversary import AdversaryBase, Attack


# ---------------------------------------------------------------------------
# Attack templates
# ---------------------------------------------------------------------------
# Each entry: (description_template, input_data_factory, expected_qliphah, severity)
# description_template uses {n} for the sequential index.
# input_data_factory is a callable() → dict[str, Any].

_TEMPLATES: list[tuple[str, Any, str, str]] = [
    (
        "[generic #{n}] empty string input",
        lambda: {"content": ""},
        "golachab",
        "nogah",
    ),
    (
        "[generic #{n}] None value input",
        lambda: {"content": None},
        "gamaliel",
        "ruach",
    ),
    (
        "[generic #{n}] extremely long string (10K chars)",
        lambda: {"content": "A" * 10_000},
        "gamchicoth",
        "ruach",
    ),
    (
        "[generic #{n}] integer where string expected",
        lambda: {"content": 42},
        "gamaliel",
        "ruach",
    ),
    (
        "[generic #{n}] negative confidence value",
        lambda: {"confidence": -0.5},
        "samael",
        "nogah",
    ),
    (
        "[generic #{n}] confidence above 1.0",
        lambda: {"confidence": 1.7},
        "samael",
        "nogah",
    ),
    (
        "[generic #{n}] SQL injection in content",
        lambda: {"content": "'; DROP TABLE memories; --"},
        "gamaliel",
        "mamash",
    ),
    (
        "[generic #{n}] unicode edge case (RTL+LTR mix)",
        lambda: {"content": "\u202eRTL override\u202c mixed with LTR"},
        "satariel",
        "anan",
    ),
    (
        "[generic #{n}] empty dict input",
        lambda: {},
        "golachab",
        "nogah",
    ),
    (
        "[generic #{n}] nested dict 100 levels deep",
        lambda: _build_nested_dict(100),
        "gamchicoth",
        "ruach",
    ),
    (
        "[generic #{n}] boolean where string expected",
        lambda: {"content": True},
        "gamaliel",
        "nogah",
    ),
    (
        "[generic #{n}] list where string expected",
        lambda: {"content": ["item1", "item2"]},
        "gamaliel",
        "nogah",
    ),
]

_N_TEMPLATES = len(_TEMPLATES)


def _build_nested_dict(depth: int) -> dict[str, Any]:
    """Build a dict nested ``depth`` levels deep."""
    node: dict[str, Any] = {"value": "leaf"}
    for _ in range(depth - 1):
        node = {"child": node}
    return node


# ---------------------------------------------------------------------------
# GenericAdversary
# ---------------------------------------------------------------------------

class GenericAdversary(AdversaryBase):
    """Blind baseline adversary — no module-specific knowledge.

    Uses a fixed palette of 12 attack templates, cycling through them
    deterministically (seeded RNG for reproducibility).  The baseline
    that all specialized adversaries must beat.
    """

    name = "generic"

    def __init__(self, seed: int = 42) -> None:
        self._rng = random.Random(seed)

    def generate_attacks(
        self,
        target_module: str,
        count: int = 20,
    ) -> list[Attack]:
        """Return ``count`` blind attacks aimed at ``target_module``.

        Templates are cycled (with wraparound) so even small counts produce
        the full variety of failure modes, and large counts repeat templates
        with distinct sequential indices.

        Parameters
        ----------
        target_module : one of "epistememory", "selfmap", "masakh"
        count         : number of attacks to produce (default 20)
        """
        attacks: list[Attack] = []
        for i in range(count):
            template_idx = i % _N_TEMPLATES
            desc_tmpl, input_factory, qliphah, severity = _TEMPLATES[template_idx]
            description = desc_tmpl.replace("{n}", str(i + 1))
            attacks.append(
                Attack(
                    agent_name=self.name,
                    target_module=target_module,
                    description=description,
                    input_data=input_factory(),
                    expected_qliphah=qliphah,
                    expected_severity=severity,
                )
            )
        return attacks
