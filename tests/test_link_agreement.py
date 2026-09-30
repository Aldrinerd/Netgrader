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
    from src.link_attributes import _compare_equal
    verdict = _compare_equal(NATIVE_VLAN, 99, None, "SW1", "SW2")
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


# --- VLAN coverage across a trunk -------------------------------------------
#
# The two allowed lists do NOT have to be identical. What breaks connectivity
# is a VLAN with members on both sides being pruned on one of them.

def access(name, vlan):
    return InterfaceData(name=name, is_switchport=True, switchport_mode="access", access_vlan=vlan)


def svi(name, ip):
    return InterfaceData(name=name, ip_address=ip)


def campus(allowed_access=(10, 80), allowed_core=(10, 20, 80)):
    """An access switch with VLAN 10 and 80 users, uplinked to a core with a
    gateway for 10, 20 and 80. VLAN 20 has no members on the access switch."""
    acc = switch("ACCESS", {
        "GigabitEthernet0/1": trunk("GigabitEthernet0/1", allowed=allowed_access),
        "FastEthernet0/1": access("FastEthernet0/1", 10),
        "FastEthernet0/2": access("FastEthernet0/2", 80),
    })
    core = switch("CORE", {
        "GigabitEthernet0/1": trunk("GigabitEthernet0/1", allowed=allowed_core),
        "Vlan10": svi("Vlan10", "10.0.10.1"),
        "Vlan20": svi("Vlan20", "10.0.20.1"),
        "Vlan80": svi("Vlan80", "10.0.80.1"),
    })
    return TopologyResult(
        devices={"ACCESS": acc, "CORE": core},
        links=[DiscoveredLink(
            source_device="ACCESS", source_interface="GigabitEthernet0/1",
            target_device="CORE", target_interface="GigabitEthernet0/1",
            confidence=0.99, classification="verified", cable_type="eCrossOver",
        )],
    )


def coverage_verdict(topo):
    return compare(
        ALLOWED_VLANS,
        topo.devices["ACCESS"], topo.devices["ACCESS"].interfaces["GigabitEthernet0/1"],
        topo.devices["CORE"], topo.devices["CORE"].interfaces["GigabitEthernet0/1"],
    )


def test_different_allowed_lists_pass_when_every_shared_vlan_is_permitted():
    """
    The real-world case from captures/: a core pruned to the VLANs it serves
    and an access switch left near-default. Different lists, working link.
    """
    assert coverage_verdict(campus()).passed


def test_a_vlan_with_no_local_members_need_not_be_carried():
    """
    VLAN 20 has a gateway on the core and no port on the access switch, so
    pruning it costs nothing. This is exactly PASIC_CORE_SW's VLAN 20 (SALES)
    against IT_DEPARTMENT_SW, which pings end to end perfectly.
    """
    topo = campus(allowed_access=(10, 80), allowed_core=(10, 20, 80))
    verdict = coverage_verdict(topo)
    assert verdict.passed
    assert "20" not in verdict.actual


def test_a_shared_vlan_pruned_on_one_end_fails_and_names_it():
    topo = campus(allowed_access=(10,), allowed_core=(10, 20, 80))
    verdict = coverage_verdict(topo)
    assert not verdict.passed
    assert "80" in verdict.actual
    assert "ACCESS" in verdict.actual
    assert "dropped at the trunk" in verdict.reason


def test_an_unset_allowed_list_permits_everything():
    topo = campus(allowed_access=(), allowed_core=(10, 20, 80))
    assert coverage_verdict(topo).passed


def test_coverage_does_not_apply_when_the_ends_share_no_vlans():
    dev_a = switch("A", {"Gi0/1": trunk("Gi0/1"), "Fa0/1": access("Fa0/1", 10)})
    dev_b = switch("B", {"Gi0/1": trunk("Gi0/1"), "Fa0/1": access("Fa0/1", 50)})
    keys = {a.key for a in applicable_attributes(
        dev_a, dev_a.interfaces["Gi0/1"], dev_b, dev_b.interfaces["Gi0/1"])}
    assert "trunk_allowed_vlans" not in keys


# --- Reference achievability ------------------------------------------------

def test_no_rule_is_generated_that_the_reference_itself_fails():
    """
    A rule the instructor's own file cannot satisfy is unachievable by
    definition and would put 100% out of reach for the whole class.
    """
    reference = campus(allowed_access=(10,), allowed_core=(10, 20, 80))
    criteria = generate_criteria_from_topology(reference)
    keys = {(r.expected_value or {}).get("attribute") for r in criteria.rules
            if r.category == "link_agreement"}
    assert "trunk_allowed_vlans" not in keys
    # Attributes the reference does satisfy are still generated.
    assert "trunk_native_vlan" in keys


def test_the_reference_always_scores_full_marks():
    """The load-bearing invariant: the worked answer must be achievable."""
    for reference in (campus(), campus(allowed_access=(10,))):
        criteria = generate_criteria_from_topology(reference)
        report = evaluate_student_submission(criteria, reference)
        assert report.percentage == 100.0, [
            (r.rule_id, r.actual_value) for r in report.results if not r.passed
        ]


def test_a_student_who_prunes_a_populated_vlan_loses_the_points():
    reference = campus()
    student = campus(allowed_access=(10,))
    _, report = grade(reference, student)
    coverage = [r for r in link_results(report)
                if r.rule_id.startswith("linkagree_trunk_allowed_vlans_")]
    assert coverage and not coverage[0].passed
    assert "80" in coverage[0].actual_value


# --- Phase 2: interface-level protocol attributes ---------------------------

HELLO = LINK_ATTRIBUTES["ospf_hello_interval"]
MTU = LINK_ATTRIBUTES["mtu"]
DUPLEX = LINK_ATTRIBUTES["duplex"]
CHANNEL = LINK_ATTRIBUTES["channel_group_mode"]
ENCAP = LINK_ATTRIBUTES["encapsulation"]
CLOCK = LINK_ATTRIBUTES["clock_rate"]


def routed(name="GigabitEthernet0/0", ip="10.0.0.1", **kwargs):
    return InterfaceData(name=name, ip_address=ip, cidr=30, **kwargs)


def router(hostname="R1"):
    return ParsedDevice(hostname=hostname, canonical_name=hostname.lower(),
                        display_name=hostname, device_type="router")


def check(attr, intf_a, intf_b):
    return compare(attr, router("R1"), intf_a, router("R2"), intf_b)


# --- implicit defaults: the thing that stops false positives ---------------

def test_an_unwritten_setting_is_compared_at_its_ios_default():
    """
    One end writing `ip ospf hello-interval 10` and the other writing nothing
    is agreement: 10 is the default. Treating the silent end as "unset" would
    fail a correct link.
    """
    assert check(HELLO, routed(ospf_hello_interval=10), routed(ip="10.0.0.2")).passed


def test_changing_one_end_off_the_default_is_caught():
    verdict = check(HELLO, routed(ospf_hello_interval=5), routed(ip="10.0.0.2"))
    assert not verdict.passed
    assert "5" in verdict.actual and "10" in verdict.actual


def test_both_ends_silent_generates_no_rule():
    """Two defaults already agree, so a checkpoint would be noise."""
    keys = {a.key for a in applicable_attributes(
        router("R1"), routed(), router("R2"), routed(ip="10.0.0.2"))}
    assert "ospf_hello_interval" not in keys
    assert "mtu" not in keys
    assert "duplex" not in keys


def test_hardcoded_speed_against_autonegotiation_is_caught():
    """The classic duplex-mismatch setup: one end fixed, one end auto."""
    verdict = check(DUPLEX, routed(duplex="full"), routed(ip="10.0.0.2"))
    assert not verdict.passed
    assert "full" in verdict.actual and "auto" in verdict.actual


def test_mtu_mismatch_is_caught_and_explained():
    verdict = check(MTU, routed(mtu=1400), routed(ip="10.0.0.2"))
    assert not verdict.passed
    assert "1400" in verdict.actual and "1500" in verdict.actual


def test_ospf_attributes_do_not_apply_to_unaddressed_interfaces():
    """A switchport has no OSPF settings to disagree about."""
    sw_port = InterfaceData(name="Fa0/1", is_switchport=True, switchport_mode="access",
                            access_vlan=10, ospf_hello_interval=5)
    keys = {a.key for a in applicable_attributes(
        router("R1"), sw_port, router("R2"), sw_port)}
    assert "ospf_hello_interval" not in keys


# --- EtherChannel matrix ----------------------------------------------------

@pytest.mark.parametrize("mode_a,mode_b,expected", [
    ("active", "active", True),
    ("active", "passive", True),
    ("on", "on", True),
    ("desirable", "desirable", True),
    ("desirable", "auto", True),
    ("passive", "passive", False),
    ("auto", "auto", False),
    ("active", "on", False),
    ("active", "desirable", False),
    ("on", "passive", False),
])
def test_etherchannel_matrix(mode_a, mode_b, expected):
    a = routed(name="Gi0/1", channel_group=1, channel_group_mode=mode_a)
    b = routed(name="Gi0/1", ip="10.0.0.2", channel_group=1, channel_group_mode=mode_b)
    assert check(CHANNEL, a, b).passed is expected


def test_lacp_passive_on_both_ends_explains_the_silence():
    a = routed(name="Gi0/1", channel_group=1, channel_group_mode="passive")
    b = routed(name="Gi0/1", ip="10.0.0.2", channel_group=1, channel_group_mode="passive")
    verdict = check(CHANNEL, a, b)
    assert not verdict.passed
    assert "neither end ever asks to bundle" in verdict.reason
    assert "No error is logged" in verdict.reason


# --- exactly_one: serial clock rate -----------------------------------------

def serial(ip, clock=None):
    return InterfaceData(name="Serial0/0/0", ip_address=ip, cidr=30, clock_rate=clock)


def test_clock_rate_on_exactly_one_end_passes():
    assert check(CLOCK, serial("10.0.0.1", 64000), serial("10.0.0.2")).passed
    assert check(CLOCK, serial("10.0.0.1"), serial("10.0.0.2", 64000)).passed


def test_clock_rate_on_neither_end_fails():
    verdict = check(CLOCK, serial("10.0.0.1"), serial("10.0.0.2"))
    assert not verdict.passed
    assert "neither end" in verdict.actual
    assert "line protocol stays down" in verdict.reason


def test_clock_rate_on_both_ends_fails_and_names_them():
    verdict = check(CLOCK, serial("10.0.0.1", 64000), serial("10.0.0.2", 64000))
    assert not verdict.passed
    assert "both ends" in verdict.actual
    assert "R1" in verdict.reason and "R2" in verdict.reason


def test_serial_attributes_do_not_apply_to_ethernet():
    keys = {a.key for a in applicable_attributes(
        router("R1"), routed(), router("R2"), routed(ip="10.0.0.2"))}
    assert "clock_rate" not in keys
    assert "encapsulation" not in keys


def test_encapsulation_mismatch_on_a_serial_link_is_caught():
    a = InterfaceData(name="Serial0/0/0", ip_address="10.0.0.1", cidr=30, encapsulation="ppp")
    b = InterfaceData(name="Serial0/0/0", ip_address="10.0.0.2", cidr=30)
    verdict = check(ENCAP, a, b)
    assert not verdict.passed
    assert "ppp" in verdict.actual and "hdlc" in verdict.actual


def test_an_attribute_the_reference_never_sets_is_not_graded():
    """
    Documents a real limit of reference-driven rubrics, so it is a decision on
    the record rather than a surprise.

    Attributes gated on "either end writes it" only produce a rule when the
    INSTRUCTOR'S file writes it. A real router config always emits `speed` and
    `duplex`, so those are always graded; it only emits `mtu` or OSPF timers
    when someone set them deliberately. A student who breaks MTU on a lab that
    never mentioned MTU therefore loses nothing.

    That is the correct trade -- the reference is the specification, and
    grading what the lab did not ask for would be inventing requirements --
    but it means link agreement is only as complete as the reference.
    """
    reference = two_switch_topology()
    for host in ("SW1", "SW2"):
        reference.devices[host].interfaces["GigabitEthernet0/1"].ip_address = "10.0.0.1"
    criteria = generate_criteria_from_topology(reference)
    keys = {(r.expected_value or {}).get("attribute") for r in criteria.rules
            if r.category == "link_agreement"}
    assert "mtu" not in keys

    # Set it in the reference and the checkpoint appears.
    for host, mtu in (("SW1", 1500), ("SW2", 1500)):
        reference.devices[host].interfaces["GigabitEthernet0/1"].mtu = mtu
    keys = {(r.expected_value or {}).get("attribute") for r in
            generate_criteria_from_topology(reference).rules
            if r.category == "link_agreement"}
    assert "mtu" in keys
