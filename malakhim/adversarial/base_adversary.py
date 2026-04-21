"""Base class and data models for adversarial agents (Qliphoth testing).

Each adversary is a Qliphah incarnate: it embodies one failure mode and
generates targeted attacks to expose that mode in Etz Chaim modules.

Architecture
------------
Attack          — immutable description of a single test case
AttackResult    — the outcome of executing one Attack
AdversaryBase   — ABC that all specialized adversaries implement
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Severity levels (Qliphoth ladder, ascending gravity)
# ---------------------------------------------------------------------------
VALID_SEVERITIES = frozenset({"nogah", "ruach", "anan", "mamash"})
VALID_MODULES = frozenset({"epistememory", "selfmap", "masakh"})


@dataclass
class Attack:
    """Immutable description of a single adversarial probe.

    Fields
    ------
    agent_name       : name of the adversary that generated this attack
    target_module    : which Etz Chaim module is under test
    description      : human-readable explanation of the attack strategy
    input_data       : kwargs / payload forwarded to the target
    expected_qliphah : ground-truth Qliphah this attack should trigger
    expected_severity: ground-truth severity (nogah / ruach / anan / mamash)
    """

    agent_name: str
    target_module: str          # "epistememory" | "selfmap" | "masakh"
    description: str
    input_data: dict[str, Any]
    expected_qliphah: str
    expected_severity: str      # "nogah" | "ruach" | "anan" | "mamash"


@dataclass
class AttackResult:
    """Outcome of executing one Attack against a live module.

    Fields
    ------
    attack           : the original Attack that was run
    success          : True when the attack found a real flaw
    actual_response  : whatever the module returned (or raised)
    exception        : stringified exception, if any
    actual_qliphah   : Qliphah detected by the module (may be None)
    actual_severity  : severity reported by the module (may be None)

    Properties
    ----------
    qliphah_match    : actual_qliphah == expected_qliphah
    severity_match   : actual_severity == expected_severity
    """

    attack: Attack
    success: bool
    actual_response: Any
    exception: str | None
    actual_qliphah: str | None
    actual_severity: str | None

    @property
    def qliphah_match(self) -> bool:
        return self.actual_qliphah == self.attack.expected_qliphah

    @property
    def severity_match(self) -> bool:
        return self.actual_severity == self.attack.expected_severity


class AdversaryBase(ABC):
    """Abstract base for all Qliphoth adversarial agents.

    Subclasses MUST:
    - set the class attribute ``name`` (str)
    - implement ``generate_attacks``

    The name identifies the adversary in reports and attack metadata.
    """

    name: str  # subclass must override

    @abstractmethod
    def generate_attacks(
        self,
        target_module: str,
        count: int = 20,
    ) -> list[Attack]:
        """Produce ``count`` Attack instances aimed at ``target_module``.

        Parameters
        ----------
        target_module : one of "epistememory", "selfmap", "masakh"
        count         : how many attacks to generate (default 20)

        Returns
        -------
        list[Attack]  — each populated with self.name as agent_name
        """
