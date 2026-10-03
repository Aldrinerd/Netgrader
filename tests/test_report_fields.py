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


# --- expected_text and location (Task 2) ------------------------------------

from src.app import process_bundle_dict
from src.criteria_generator import generate_criteria_from_topology
from src.evaluator import evaluate_student_submission
from src.models import EvaluationPolicies
from src.report_fields import expected_text
from tests.fixtures import network_bundle


def _rule(category, expected, **kw):
    return EvaluationRule(
        rule_id="r", category=category, description="d",
        target_device=kw.pop("target_device", "R1"),
        target_interface=kw.pop("target_interface", "GigabitEthernet0/0"),
        expected_value=expected, **kw,
    )


STRICT = EvaluationPolicies()


def test_expected_ip():
    assert expected_text(_rule("interface_ip", {"ip_address": "10.0.0.1", "cidr": 30}), STRICT) == "10.0.0.1/30"


def test_expected_cable_names_the_cable_only_when_cable_type_is_graded():
    rule = _rule("cabling", {
        "source_device": "R1", "source_interface": "GigabitEthernet0/0",
        "target_device": "R2", "target_interface": "GigabitEthernet0/1",
        "cable_type": "eCrossOver",
    })
    assert expected_text(rule, STRICT) == "A cable from R1 GigabitEthernet0/0 to R2 GigabitEthernet0/1 (crossover)"
    assert expected_text(rule, EvaluationPolicies(strict_cable_type=False)) == \
        "A cable from R1 GigabitEthernet0/0 to R2 GigabitEthernet0/1"


def test_expected_link_agreement_shows_the_value_only_when_dictated():
    rule = _rule("link_agreement", {
        "peer_device": "R2", "peer_interface": "GigabitEthernet0/1",
        "attribute": "ospf_hello_interval", "reference_value": 10,
    })
    assert expected_text(rule, STRICT) == "Both ends agree on the OSPF hello interval"
    assert expected_text(rule, EvaluationPolicies(enforce_reference_link_values=True)) == \
        "Both ends agree on the OSPF hello interval: 10"


def test_expected_routing_mentions_process_id_only_when_graded():
    rule = _rule("routing", {"protocol": "ospf", "area": 0, "process_id": 10}, target_interface=None)
    assert expected_text(rule, STRICT) == "OSPF advertising networks into area 0"
    assert expected_text(rule, EvaluationPolicies(allow_flexible_process_ids=False)) == \
        "OSPF advertising networks into area 0, process ID 10"


def test_expected_text_never_raises():
    assert expected_text(_rule("link_agreement", {"attribute": "no_such_attr"}), STRICT) is None
    assert expected_text(_rule("interface_ip", "not a dict"), STRICT) is None
    assert expected_text(_rule("security", {"check_type": "unknown"}), STRICT) is None


def test_every_generated_rule_gets_expected_text():
    ref = process_bundle_dict(network_bundle("ospf_clean"))
    criteria = generate_criteria_from_topology(ref, lab_title="t")
    report = evaluate_student_submission(criteria, ref)
    assert all(r.expected_text for r in report.results)


def test_location_fields_on_a_flawed_submission():
    ref = process_bundle_dict(network_bundle("ospf_clean"))
    criteria = generate_criteria_from_topology(ref, lab_title="t")
    report = evaluate_student_submission(criteria, process_bundle_dict(network_bundle("subnet_cabling_error")))

    on_r3 = [r for r in report.results if r.target_device == "R3"]
    assert on_r3 and all(r.matched_device is None for r in on_r3)

    r1_r2 = [r for r in report.results if r.category == "cabling"
             and {r.target_device, (criteria_rule(criteria, r).expected_value or {}).get("target_device")} == {"R1", "R2"}]
    assert r1_r2
    for r in r1_r2:
        assert r.matched_device in ("R1", "R2") and r.peer_device in ("R1", "R2")
        assert r.peer_device != r.matched_device and r.peer_interface

    r1_r3 = [r for r in report.results if r.category == "cabling"
             and {r.target_device, (criteria_rule(criteria, r).expected_value or {}).get("target_device")} == {"R1", "R3"}]
    assert r1_r3 and all(r.peer_device is None and r.peer_interface is None for r in r1_r3
                         if r.target_device == "R1")

    device_only = [r for r in report.results if r.category in ("device", "routing", "interface_ip")]
    assert all(r.peer_device is None for r in device_only)


def criteria_rule(criteria, result):
    return next(rule for rule in criteria.rules if rule.rule_id == result.rule_id)


def test_matched_device_follows_custom_hostname_mapping():
    ref = process_bundle_dict(network_bundle("ospf_clean"))
    criteria = generate_criteria_from_topology(
        ref, lab_title="t", policies=EvaluationPolicies(allow_custom_hostnames=True))

    student = ref.model_copy(deep=True)
    dev = student.devices.pop("R3")
    dev.hostname = dev.display_name = "Core3"
    dev.canonical_name = "core3"
    student.devices["Core3"] = dev
    for link in student.links:
        if link.source_device == "R3":
            link.source_device = "Core3"
        if link.target_device == "R3":
            link.target_device = "Core3"

    report = evaluate_student_submission(criteria, student)
    on_r3 = [r for r in report.results if r.target_device == "R3"]
    assert on_r3 and all(r.matched_device == "Core3" for r in on_r3)
    peers = {r.peer_device for r in report.results if r.peer_device}
    assert "Core3" in peers and "R3" not in peers
