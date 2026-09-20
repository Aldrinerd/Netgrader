# tests/test_link_agreement.py
"""
Link-scoped evaluation rules (Phase 1).

The rules these cover are the first in the engine whose subject is a LINK
rather than a device, so the things worth pinning down are: the predicates
themselves, that endpoints resolve in either direction and under the relevant
policies, that generation stays proportional to the reference, and that a
native VLAN mismatch is charged exactly once.
"""

import pytest

from src.criteria_generator import generate_criteria_from_topology
from src.evaluator import evaluate_student_submission
from src.link_attributes import (
    LINK_ATTRIBUTES,
    applicable_attributes,
    compare,
)
from src.models import (
    DiscoveredLink,
    EvaluationPolicies,
    InterfaceData,
    ParsedDevice,
    TopologyResult,
)

NATIVE_VLAN = LINK_ATTRIBUTES["trunk_native_vlan"]
ALLOWED_VLANS = LINK_ATTRIBUTES["trunk_allowed_vlans"]
SWITCHPORT_MODE = LINK_ATTRIBUTES["switchport_mode"]


def trunk(name, native=99, allowed=(10, 20), mode="trunk"):
    return InterfaceData(
        name=name,
        is_switchport=True,
        switchport_mode=mode,
        trunk_native_vlan=native,
        trunk_allowed_vlans=list(allowed),
    )


def switch(hostname, interfaces):
    return ParsedDevice(
        hostname=hostname,
        canonical_name=hostname.lower(),
        display_name=hostname,
        device_type="switch",
        interfaces=interfaces,
    )


def two_switch_topology(native_a=99, native_b=99, allowed_a=(10, 20), allowed_b=(10, 20),
                        mode_a="trunk", mode_b="trunk"):
    sw1 = switch("SW1", {"GigabitEthernet0/1": trunk("GigabitEthernet0/1", native_a, allowed_a, mode_a)})
    sw2 = switch("SW2", {"GigabitEthernet0/1": trunk("GigabitEthernet0/1", native_b, allowed_b, mode_b)})
    return TopologyResult(
        devices={"SW1": sw1, "SW2": sw2},
        links=[DiscoveredLink(
            source_device="SW1", source_interface="GigabitEthernet0/1",
            target_device="SW2", target_interface="GigabitEthernet0/1",
            confidence=0.99, classification="verified", cable_type="eCrossOver",
        )],
    )


def grade(reference, student, policies=None):
    criteria = generate_criteria_from_topology(reference, policies=policies or EvaluationPolicies())
    return criteria, evaluate_student_submission(criteria, student)


def link_results(report):
    return [r for r in report.results if r.category == "link_agreement"]


# --- Predicate: equal -------------------------------------------------------

def test_equal_passes_when_both_ends_match():
    topo = two_switch_topology(native_a=99, native_b=99)
    verdict = compare(NATIVE_VLAN, topo.devices["SW1"], topo.devices["SW1"].interfaces["GigabitEthernet0/1"],
                      topo.devices["SW2"], topo.devices["SW2"].interfaces["GigabitEthernet0/1"])
    assert verdict.passed


def test_equal_fails_and_explains_when_ends_differ():
    topo = two_switch_topology(native_a=1, native_b=99)
    verdict = compare(NATIVE_VLAN, topo.devices["SW1"], topo.devices["SW1"].interfaces["GigabitEthernet0/1"],
                      topo.devices["SW2"], topo.devices["SW2"].interfaces["GigabitEthernet0/1"])
    assert not verdict.passed
    assert "1" in verdict.actual and "99" in verdict.actual
    assert "differs" in verdict.reason


def test_equal_fails_when_one_end_has_no_value():
    a = trunk("Gi0/1", allowed=(10, 20))
    b = trunk("Gi0/1", allowed=())
    dev = switch("X", {})
    verdict = compare(ALLOWED_VLANS, dev, a, dev, b)
    assert not verdict.passed
    assert "not configured on both ends" in verdict.reason


# --- Predicate: compatible --------------------------------------------------

@pytest.mark.parametrize("mode_a,mode_b,expected", [
    ("trunk", "trunk", True),
    ("access", "access", True),
    ("trunk", "dynamic desirable", True),
    ("trunk", "dynamic auto", True),
    ("dynamic desirable", "dynamic auto", True),
    ("dynamic desirable", "dynamic desirable", True),
    ("trunk", "access", False),
    ("dynamic auto", "dynamic auto", False),
])
def test_switchport_mode_matrix(mode_a, mode_b, expected):
    dev = switch("X", {})
    a = trunk("Gi0/1", mode=mode_a)
    b = trunk("Gi0/1", mode=mode_b)
    assert compare(SWITCHPORT_MODE, dev, a, dev, b).passed is expected


def test_auto_auto_explains_the_silent_failure():
    """The pairing that produces no error message needs the best explanation."""
    dev = switch("X", {})
    a = trunk("Gi0/1", mode="dynamic auto")
    b = trunk("Gi0/1", mode="dynamic auto")
    verdict = compare(SWITCHPORT_MODE, dev, a, dev, b)
    assert not verdict.passed
    assert "neither end ever asks to trunk" in verdict.reason


# --- Applicability ----------------------------------------------------------

def test_trunk_attributes_do_not_apply_to_access_links():
    dev = switch("X", {})
    access_a = trunk("Fa0/1", mode="access")
    access_b = trunk("Fa0/1", mode="access")
    keys = {a.key for a in applicable_attributes(dev, access_a, dev, access_b)}
    assert "trunk_native_vlan" not in keys
    assert "switchport_mode" in keys


def test_switchport_mode_does_not_apply_when_one_end_is_a_router():
    """A router port has no switchport mode, and must not be asked for one."""
    sw = switch("SW1", {})
    router = ParsedDevice(hostname="R1", canonical_name="r1", device_type="router")
    sw_port = trunk("Fa0/1", mode="access")
    router_port = InterfaceData(name="GigabitEthernet0/0", ip_address="10.0.0.1")
    assert applicable_attributes(sw, sw_port, router, router_port) == []


def test_generation_is_proportional_to_the_reference():
    """A lab with no trunks emits no trunk rules."""
    topo = two_switch_topology(mode_a="access", mode_b="access")
    criteria = generate_criteria_from_topology(topo)
    keys = {(r.expected_value or {}).get("attribute") for r in criteria.rules
            if r.category == "link_agreement"}
    assert keys == {"switchport_mode"}


def test_points_still_total_exactly_the_target():
    topo = two_switch_topology()
    criteria = generate_criteria_from_topology(topo, target_total_points=100.0)
    assert round(sum(r.points for r in criteria.rules), 1) == 100.0
    assert link_results(evaluate_student_submission(criteria, topo))


# --- Endpoint resolution ----------------------------------------------------

def test_rule_matches_a_link_discovered_in_the_opposite_direction():
    reference = two_switch_topology()
    student = two_switch_topology()
    student.links = [DiscoveredLink(
        source_device="SW2", source_interface="GigabitEthernet0/1",
        target_device="SW1", target_interface="GigabitEthernet0/1",
        confidence=0.99, classification="verified", cable_type="eCrossOver",
    )]
    _, report = grade(reference, student)
    assert all(r.passed for r in link_results(report))


def test_custom_hostnames_still_resolve_both_endpoints():
    reference = two_switch_topology()
    student = two_switch_topology()
    student.devices = {
        "ACCESS-A": switch("ACCESS-A", {"GigabitEthernet0/1": trunk("GigabitEthernet0/1")}),
        "ACCESS-B": switch("ACCESS-B", {"GigabitEthernet0/1": trunk("GigabitEthernet0/1")}),
    }
    student.links = [DiscoveredLink(
        source_device="ACCESS-A", source_interface="GigabitEthernet0/1",
        target_device="ACCESS-B", target_interface="GigabitEthernet0/1",
        confidence=0.99, classification="verified", cable_type="eCrossOver",
    )]
    policies = EvaluationPolicies(allow_custom_hostnames=True)
    _, report = grade(reference, student, policies)
    assert all(r.passed for r in link_results(report)), [
        (r.rule_id, r.actual_value) for r in link_results(report) if not r.passed
    ]


def test_missing_peer_interface_fails_with_a_clear_reason():
    reference = two_switch_topology()
    student = two_switch_topology()
    student.devices["SW2"].interfaces = {}
    _, report = grade(reference, student)
    failed = [r for r in link_results(report) if not r.passed]
    assert failed
    assert any("missing" in r.feedback.lower() for r in failed)


# --- Policy: enforce_reference_link_values ----------------------------------

def test_agreeing_on_a_different_value_passes_by_default():
    """Both ends on native VLAN 999 form a working trunk. That is correct."""
    reference = two_switch_topology(native_a=99, native_b=99)
    student = two_switch_topology(native_a=999, native_b=999)
    _, report = grade(reference, student)
    native = [r for r in link_results(report) if "native" in r.description.lower()]
    assert native and all(r.passed for r in native)


def test_agreeing_on_a_different_value_fails_when_the_instructor_dictated_it():
    reference = two_switch_topology(native_a=99, native_b=99)
    student = two_switch_topology(native_a=999, native_b=999)
    policies = EvaluationPolicies(enforce_reference_link_values=True)
    _, report = grade(reference, student, policies)
    native = [r for r in link_results(report) if "native" in r.description.lower()]
    assert native and not any(r.passed for r in native)
    assert "requires" in native[0].feedback


# --- The point of Phase 1 ---------------------------------------------------

def test_native_vlan_mismatch_now_costs_points():
    """
    Before link rules existed this was detected by the conflict detector,
    displayed in the topology drawer, and worth nothing.
    """
    reference = two_switch_topology(native_a=99, native_b=99)
    student = two_switch_topology(native_a=1, native_b=99)
    _, report = grade(reference, student)
    native = [r for r in link_results(report) if "native" in r.description.lower()]
    assert native
    assert not native[0].passed
    assert native[0].points_earned == 0.0
    assert report.percentage < 100.0


def test_a_native_vlan_mismatch_is_charged_once():
    """
    vlan_trunk used to dock half credit per interface for a native VLAN that
    differed from the reference. With the link rule owning that question, the
    mistake must cost the link rule's points and nothing else.
    """
    reference = two_switch_topology(native_a=99, native_b=99)
    student = two_switch_topology(native_a=1, native_b=99)
    _, report = grade(reference, student)

    trunk_results = [r for r in report.results if r.category == "vlan_trunk"]
    assert trunk_results, "expected trunk rules in this topology"
    assert all(r.passed for r in trunk_results), (
        "vlan_trunk must no longer penalise native VLAN: "
        f"{[(r.rule_id, r.feedback) for r in trunk_results if not r.passed]}"
    )

    native = [r for r in link_results(report) if "native" in r.description.lower()]
    lost = sum(r.points_possible - r.points_earned for r in report.results if not r.passed)
    assert round(lost, 1) == round(native[0].points_possible, 1)


def test_failed_link_rule_gets_guidance():
    reference = two_switch_topology(native_a=99, native_b=99)
    student = two_switch_topology(native_a=1, native_b=99)
    _, report = grade(reference, student)
    failed = [r for r in link_results(report) if not r.passed]
    assert failed
    assert failed[0].guidance
    assert "untagged" in failed[0].guidance


def test_no_rule_is_generated_that_the_reference_itself_fails():
    """
    A rule the instructor's own file cannot satisfy is unachievable by
    definition and would put 100% out of reach for the whole class. Found on
    the real captures, where a trunk's two ends carry different allowed-VLAN
    lists.
    """
    reference = two_switch_topology(allowed_a=(10, 20), allowed_b=(10, 20, 30))
    criteria = generate_criteria_from_topology(reference)
    keys = {(r.expected_value or {}).get("attribute") for r in criteria.rules
            if r.category == "link_agreement"}
    assert "trunk_allowed_vlans" not in keys
    # The attributes the reference does satisfy are still generated.
    assert "trunk_native_vlan" in keys


def test_the_reference_always_scores_full_marks():
    """The load-bearing invariant: the worked answer must be achievable."""
    reference = two_switch_topology(allowed_a=(10, 20), allowed_b=(10, 20, 30))
    criteria = generate_criteria_from_topology(reference)
    report = evaluate_student_submission(criteria, reference)
    assert report.percentage == 100.0, [
        (r.rule_id, r.actual_value) for r in report.results if not r.passed
    ]
