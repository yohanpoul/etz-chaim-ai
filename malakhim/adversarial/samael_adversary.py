"""SamaelAdversary — over-rigidity and false-negative attacks.

Samael (סַמָּאֵל) in Kabbalistic tradition is the accusing angel, the prince of
severity who applies Din (strict judgment) without mercy.  As a Qliphah it
manifests as excessive rigidity: refusing valid input, blocking legitimate
inference, applying rules so strictly that truth itself is rejected.

In the ML context this maps to false negatives, over-conservative thresholds,
blocked retrieval of valid memories, and systems that silence themselves when
they should speak.
"""
from __future__ import annotations

import random
from typing import Any

from malakhim.adversarial.base_adversary import AdversaryBase, Attack


# ---------------------------------------------------------------------------
# Target Qliphot for Samael (over-rigidity / false-negative failure modes)
# ---------------------------------------------------------------------------
_PRIMARY_QLIPHOT = {"golachab", "samael"}

# ---------------------------------------------------------------------------
# Module-specific templates: (description, qliphah, severity, input_data)
# ---------------------------------------------------------------------------

_EPISTEMEMORY_TEMPLATES: list[tuple[str, str, str, dict]] = [
    (
        "[samael:ep] Retrieve fact with valid but unusual unicode casing",
        "samael",
        "ruach",
        {"query": "WATER IS WET", "expected_match": "water is wet"},
    ),
    (
        "[samael:ep] Query fact that exists but with slight reformulation",
        "samael",
        "ruach",
        {"query": "Is H₂O a liquid?", "stored_form": "water is a liquid"},
    ),
    (
        "[samael:ep] Force confidence threshold rejection on borderline fact",
        "golachab",
        "anan",
        {"fact": "plausible claim", "confidence": 0.501},
    ),
    (
        "[samael:ep] Submit fact with valid domain that triggers false-domain-rejection",
        "golachab",
        "ruach",
        {"domain": "mathematics", "fact": "2+2=4"},
    ),
    (
        "[samael:ep] Probe retrieval of recently-stored fact within same session",
        "samael",
        "nogah",
        {"delay_ms": 0, "fact": "just stored value"},
    ),
    (
        "[samael:ep] Query fact with accented characters vs ASCII-only store",
        "golachab",
        "ruach",
        {"query": "naïve", "stored": "naive"},
    ),
]

_SELFMAP_TEMPLATES: list[tuple[str, str, str, dict]] = [
    (
        "[samael:sm] Claim competence that is actually within training scope",
        "samael",
        "ruach",
        {"domain": "python_programming", "query": "write a for loop"},
    ),
    (
        "[samael:sm] Request capability description — over-conservative response",
        "golachab",
        "anan",
        {"request": "list_all_capabilities"},
    ),
    (
        "[samael:sm] Ask system to rate its own confidence on routine task",
        "samael",
        "nogah",
        {"task": "add two numbers", "expected_confidence": "high"},
    ),
    (
        "[samael:sm] Probe for false uncertainty on well-established fact",
        "golachab",
        "ruach",
        {"fact": "Paris is the capital of France", "expected_certainty": "high"},
    ),
    (
        "[samael:sm] Request simple reasoning — trigger unjustified refusal",
        "samael",
        "ruach",
        {"reasoning_task": "if A then B, A, therefore?"},
    ),
]

_MASAKH_TEMPLATES: list[tuple[str, str, str, dict]] = [
    (
        "[samael:ma] Feed short but valid context — probe over-aggressive filtering",
        "samael",
        "ruach",
        {"context": "The answer is 42.", "query": "What is the answer?"},
    ),
    (
        "[samael:ma] Submit low-entropy but relevant context",
        "golachab",
        "ruach",
        {"context": "yes yes yes yes relevant token yes", "query": "is it relevant?"},
    ),
    (
        "[samael:ma] Context with correct answer in first sentence — later noise",
        "samael",
        "anan",
        {"context": "Answer: blue. " + "noise " * 500, "query": "what colour?"},
    ),
    (
        "[samael:ma] Verify Reshimu retains signal after aggressive compression",
        "golachab",
        "mamash",
        {"context": "critical fact: X=7", "compression_ratio": 0.99},
    ),
    (
        "[samael:ma] Submit valid context but unconventional structure",
        "samael",
        "nogah",
        {"context": {"nested": {"answer": "yes"}}, "query": "is it yes?"},
    ),
]

_GENERIC_TEMPLATES: list[tuple[str, str, str, dict]] = [
    (
        "[samael:gen] Submit entirely valid input — probe false-alarm rate",
        "samael",
        "nogah",
        {"input": "completely normal value"},
    ),
    (
        "[samael:gen] Repeat identical query 5x — probe idempotency refusal",
        "golachab",
        "ruach",
        {"query": "normal query", "repeat": 5},
    ),
    (
        "[samael:gen] Valid input with extra unknown keys — probe strict schema",
        "samael",
        "nogah",
        {"required_field": "value", "unknown_extra": "harmless"},
    ),
    (
        "[samael:gen] Trigger boundary: confidence exactly at threshold",
        "golachab",
        "ruach",
        {"confidence": 0.5},
    ),
]

_MODULE_POOL: dict[str, list[tuple[str, str, str, dict]]] = {
    "epistememory": _EPISTEMEMORY_TEMPLATES + _GENERIC_TEMPLATES,
    "selfmap": _SELFMAP_TEMPLATES + _GENERIC_TEMPLATES,
    "masakh": _MASAKH_TEMPLATES + _GENERIC_TEMPLATES,
}


class SamaelAdversary(AdversaryBase):
    """Over-rigidity adversary — probes false-negative and blocking failure modes.

    At least 70 % of attacks target ``golachab`` or ``samael`` Qliphot.
    Module-specific template banks ensure distinct attack surfaces per module.
    """

    name = "samael"

    def __init__(self, seed: int = 42) -> None:
        self._rng = random.Random(seed)

    def generate_attacks(
        self,
        target_module: str,
        count: int = 20,
    ) -> list[Attack]:
        """Produce ``count`` over-rigidity attacks for ``target_module``.

        The pool is weighted so that primary Qliphot (golachab, samael)
        appear in >= 70 % of generated attacks.

        Parameters
        ----------
        target_module : one of "epistememory", "selfmap", "masakh"
        count         : number of attacks (default 20)
        """
        module_specific = _MODULE_POOL.get(target_module, _GENERIC_TEMPLATES)
        primary = [t for t in module_specific if t[1] in _PRIMARY_QLIPHOT]
        secondary = [t for t in module_specific if t[1] not in _PRIMARY_QLIPHOT]

        attacks: list[Attack] = []
        for _ in range(count):
            # Enforce >= 70 % primary target ratio
            if self._rng.random() < 0.75 and primary:
                desc, qliphah, severity, input_data = self._rng.choice(primary)
            elif secondary:
                desc, qliphah, severity, input_data = self._rng.choice(secondary)
            else:
                desc, qliphah, severity, input_data = self._rng.choice(primary)

            attacks.append(
                Attack(
                    agent_name=self.name,
                    target_module=target_module,
                    description=desc,
                    input_data=dict(input_data),
                    expected_qliphah=qliphah,
                    expected_severity=severity,
                )
            )
        return attacks
