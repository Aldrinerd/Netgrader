# src/topics/__init__.py
"""
Configuration topics: what a lab teaches, as opposed to what a rule checks.

registry.py   which topics exist, which rule categories each owns, and how
              each is detected in a reference file
weights.py    how a lab's points are split between topics
<topic>.py    a grader for one topic (static_routes.py is the first)
"""

# The two types below are the contract every grader module shares with the
# evaluator. They live here, not in evaluator.py, so a grader never imports
# the evaluator (which imports the registry, which imports the graders).
from dataclasses import dataclass
from typing import Callable

from src.models import DiscoveredLink, EvaluationPolicies, InterfaceData, ParsedDevice


@dataclass
class EvalContext:
    """What a grader may consult about the student's submission."""
    devices: dict[str, ParsedDevice]
    links: list[DiscoveredLink]
    policies: EvaluationPolicies
    device_mapping: dict[str, str]
    find_device: Callable[[str], ParsedDevice | None]
    find_interface: Callable[[ParsedDevice, str], InterfaceData | None]


@dataclass
class RuleOutcome:
    """A grader's verdict on one rule. The evaluator turns it into a RuleResult."""
    points_earned: float
    passed: bool
    actual: str
    feedback: str
