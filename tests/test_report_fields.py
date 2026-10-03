# tests/test_report_fields.py
"""
Presentational fields on each checkpoint for the linked report (spec 5.5).
They describe what the evaluator already decided and never move a score.
"""
import re
import typing

import pytest

from src.feedback import (
    _LINK_AGREEMENT_COMMANDS, attach_guidance, explain, topic_for, verify_commands,
)
from src.link_attributes import LINK_ATTRIBUTES
from src.models import EvaluationRule, RuleResult

CATEGORIES = typing.get_args(EvaluationRule.model_fields["category"].annotation)


def _result(category, passed=False, rule_id="r", **overrides):
    fields = dict(
        rule_id=rule_id, category=category, description="d",
        points_possible=10.0, points_earned=10.0 if passed else 0.0, passed=passed,
        actual_value="x", feedback="f",
        target_device="R1", target_interface="GigabitEthernet0/0",
    )
    fields.update(overrides)
    return RuleResult(**fields)


@pytest.mark.parametrize("category", CATEGORIES)
def test_every_category_has_commands_to_check_with(category):
    assert verify_commands(_result(category))


def test_every_link_attribute_has_its_own_commands():
    assert set(LINK_ATTRIBUTES) <= set(_LINK_AGREEMENT_COMMANDS)


def test_link_agreement_commands_follow_the_attribute():
    result = _result("link_agreement", rule_id="linkagree_ospf_hello_interval_r1_g0_0__r2_g0_0")
    assert verify_commands(result) == ["show ip ospf interface"]
    trunk = _result("link_agreement", rule_id="linkagree_trunk_native_vlan_s1_g0_1__s2_g0_1")
    assert verify_commands(trunk) == ["show interfaces trunk"]


# One failing result per guidance sentence that names a command.
SENTENCES = [
    ("device", {}),
    ("interface_ip", {"actual_value": "No IP configured (Unassigned)"}),
    ("interface_ip", {"actual_value": "10.0.0.9/24"}),
    ("interface_status", {"actual_value": "administratively down"}),
    ("cabling", {"actual_value": "Disconnected / Uncabled"}),
    ("vlan_trunk", {"feedback": "Expected 802.1Q trunk port, but interface is configured as 'access'."}),
    ("vlan_trunk", {"feedback": "Expected Access VLAN 10, but port is assigned to VLAN 1."}),
    ("routing", {}),
]


@pytest.mark.parametrize("category,overrides", SENTENCES)
def test_commands_named_in_guidance_are_listed_as_data(category, overrides):
    result = _result(category, **overrides)
    named = set(re.findall(r"'(show [^']+)'", explain(result)))
    assert named, "sample should exercise a sentence that names a command"
    assert named <= set(verify_commands(result))


def test_attach_guidance_sets_topic_on_every_result_and_commands_on_failures(make_report):
    report = make_report([_result("cabling", passed=True), _result("routing", passed=False)])
    before = [(r.points_earned, r.passed) for r in report.results]
    attach_guidance(report)
    assert [r.topic for r in report.results] == [topic_for("cabling"), topic_for("routing")]
    assert report.results[0].verify_commands == []
    assert report.results[1].verify_commands == verify_commands(report.results[1])
    assert [(r.points_earned, r.passed) for r in report.results] == before


def test_unknown_category_falls_back_to_the_generic_topic():
    assert topic_for("not_a_category") == "Lab requirements"
    assert verify_commands(_result("not_a_category")) == []


@pytest.fixture
def make_report():
    from src.models import EvaluationReport, TopologyResult

    def build(results):
        return EvaluationReport(
            lab_title="t", total_score=0, max_score=0, percentage=0,
            passed_count=0, failed_count=0, grade_letter="F",
            results=results, topology=TopologyResult(),
        )
    return build
