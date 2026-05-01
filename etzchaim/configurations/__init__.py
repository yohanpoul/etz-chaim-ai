"""etzchaim.configurations — public namespace for the composition layers.

Public neutral facade over the internal `partzufim/` package. Use this
namespace in user-facing code, docs, and examples. The internal package
remains accessible for developers who need direct module access.
"""

from __future__ import annotations

from partzufim import (
    PartzufBase as Configuration,
    PartzufState as ConfigurationState,
    ZivugResult as CouplingResult,
    ZivvugAssessment as CouplingAssessment,
    ZivvugEngine as CouplingEngine,
    ZivvugState as CouplingState,
    FACULTY_NAMES,
    AtikYomin as InvariantConfig,
    ArikhAnpin as StrategicConfig,
    Abba as GenerativeConfig,
    Imma as StructuringConfig,
    ZeirAnpin as ExecutionConfig,
    Nukva as InterfaceConfig,
    feedback_from_malkuth as feedback_from_action,
    get_partzuf as get_configuration,
    init_partzufim as init_configurations,
    list_partzufim as list_configurations,
    update_all_partzufim as update_all_configurations,
)

__all__ = [
    "Configuration",
    "ConfigurationState",
    "CouplingResult",
    "CouplingAssessment",
    "CouplingEngine",
    "CouplingState",
    "FACULTY_NAMES",
    "InvariantConfig",
    "StrategicConfig",
    "GenerativeConfig",
    "StructuringConfig",
    "ExecutionConfig",
    "InterfaceConfig",
    "feedback_from_action",
    "get_configuration",
    "init_configurations",
    "list_configurations",
    "update_all_configurations",
]
