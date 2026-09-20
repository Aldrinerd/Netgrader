# tests/test_policy_toggles.py
"""
Regression suite proving every instructor policy toggle actually changes grading.

Each case grades ONE mutated submission twice -- once under the lenient setting
and once under the strict setting of a single toggle -- and asserts the lenient
run scores strictly higher. A toggle that silently does nothing (which is what
happened to the gateway and routing policies before these tests existed) fails
here immediately.

This is the evidence behind the "consistency of grading" research question: the
rubric's strictness is controlled, declared, and verifiable.
"""
import copy

import pytest

from src.criteria_generator import generate_criteria_from_topology
from src.evaluator import evaluate_student_submission
from src.models import (
    DiscoveredLink, EvaluationPolicies, InterfaceData, ParsedDevice, TopologyResult,
)


def intf(name, ip=None, cidr=None, mask=None, net=None, desc=None,
         sw=None, vlan=None, native=1, admin="up"):
    return InterfaceData(
        name=name, ip_address=ip, cidr=cidr, subnet_mask=mask, network_address=net,
        description=desc, is_switchport=bool(sw), switchport_mode=sw,
        access_vlan=vlan, trunk_native_vlan=native, admin_status=admin,
    )


def build_reference():
    """A small but complete CCNA-style reference topology."""
    r1 = ParsedDevice(
        hostname="R1", canonical_name="r1", display_name="R1", device_type="router",
        has_enable_secret=True, has_password_encryption=True, has_vty_login=True,
        ospf_processes=[{"process_id": 1, "networks": [
            {"network": "10.0.0.0", "wildcard": "0.0.0.3", "area": 0},
            {"network": "192.168.1.0", "wildcard": "0.0.0.255", "area": 0}]}],
        interfaces={
            "GigabitEthernet0/0": intf("GigabitEthernet0/0", "10.0.0.1", 30, "255.255.255.252", "10.0.0.0", "Link to R2"),
            "GigabitEthernet0/1": intf("GigabitEthernet0/1", "192.168.1.1", 24, "255.255.255.0", "192.168.1.0", "LAN gateway"),
        },
    )
    r2 = ParsedDevice(
        hostname="R2", canonical_name="r2", display_name="R2", device_type="router",
        has_enable_secret=True, has_password_encryption=True, has_vty_login=True,
        ospf_processes=[{"process_id": 1, "networks": [
            {"network": "10.0.0.0", "wildcard": "0.0.0.3", "area": 0}]}],
        interfaces={
            "GigabitEthernet0/0": intf("GigabitEthernet0/0", "10.0.0.2", 30, "255.255.255.252", "10.0.0.0", "Link to R1"),
        },
    )
    sw1 = ParsedDevice(
        hostname="SW1", canonical_name="sw1", display_name="SW1", device_type="switch",
        has_enable_secret=True, has_password_encryption=True, has_vty_login=True,
        default_gateway="192.168.1.1",
        interfaces={
            "GigabitEthernet0/1": intf("GigabitEthernet0/1", sw="trunk", native=1, desc="Uplink to R1"),
            "FastEthernet0/1": intf("FastEthernet0/1", sw="access", vlan=10, desc="PC1"),
        },
    )
    pc1 = ParsedDevice(
        hostname="PC1", canonical_name="pc1", display_name="PC1", device_type="host",
        default_gateway="192.168.1.1",
        interfaces={
            "FastEthernet0": intf("FastEthernet0", "192.168.1.10", 24, "255.255.255.0", "192.168.1.0"),
        },
    )
    devices = {"R1": r1, "R2": r2, "SW1": sw1, "PC1": pc1}
    links = [
        DiscoveredLink(source_device="R1", source_interface="GigabitEthernet0/0",
                       target_device="R2", target_interface="GigabitEthernet0/0",
                       confidence=1.0, classification="verified", cable_type="eCrossOver"),
        DiscoveredLink(source_device="R1", source_interface="GigabitEthernet0/1",
                       target_device="SW1", target_interface="GigabitEthernet0/1",
                       confidence=1.0, classification="verified", cable_type="eStraightThrough"),
        DiscoveredLink(source_device="SW1", source_interface="FastEthernet0/1",
                       target_device="PC1", target_interface="FastEthernet0",
                       confidence=1.0, classification="verified", cable_type="eStraightThrough"),
    ]
    return TopologyResult(devices=devices, links=links, conflicts=[])


# ---------------- mutations: each breaks ONLY what one toggle governs -------------

def m_readdress(t):
    """Valid but completely different addressing scheme; prefixes preserved."""
    t.devices["R1"].interfaces["GigabitEthernet0/0"].ip_address = "172.16.5.1"
    t.devices["R1"].interfaces["GigabitEthernet0/0"].network_address = "172.16.5.0"
    t.devices["R2"].interfaces["GigabitEthernet0/0"].ip_address = "172.16.5.2"
    t.devices["R2"].interfaces["GigabitEthernet0/0"].network_address = "172.16.5.0"
    t.devices["R1"].interfaces["GigabitEthernet0/1"].ip_address = "10.20.30.1"
    t.devices["R1"].interfaces["GigabitEthernet0/1"].network_address = "10.20.30.0"
    t.devices["PC1"].interfaces["FastEthernet0"].ip_address = "10.20.30.50"
    t.devices["PC1"].interfaces["FastEthernet0"].network_address = "10.20.30.0"
    t.devices["PC1"].default_gateway = "10.20.30.1"
    t.devices["SW1"].default_gateway = "10.20.30.1"
    return t


def m_wrong_prefix(t):
    """Mutually consistent subnet, but the /30 link was built as a /24."""
    t = m_readdress(t)
    for dev, i in (("R1", "GigabitEthernet0/0"), ("R2", "GigabitEthernet0/0")):
        t.devices[dev].interfaces[i].cidr = 24
        t.devices[dev].interfaces[i].subnet_mask = "255.255.255.0"
        t.devices[dev].interfaces[i].network_address = "172.16.5.0"
    return t


def m_bad_gateway(t):
    t.devices["PC1"].default_gateway = "10.99.99.99"
    t.devices["SW1"].default_gateway = "10.99.99.99"
    return t


def m_rename(t):
    """Same topology, student's own naming convention."""
    mapping = {"R1": "EDGE-RTR", "R2": "CORE-RTR", "SW1": "ACCESS-SW", "PC1": "WORKSTATION"}
    new_devices = {}
    for old, dev in t.devices.items():
        dev.hostname = mapping[old]
        dev.canonical_name = mapping[old].lower()
        dev.display_name = mapping[old]
        new_devices[mapping[old]] = dev
    t.devices = new_devices
    for link in t.links:
        link.source_device = mapping.get(link.source_device, link.source_device)
        link.target_device = mapping.get(link.target_device, link.target_device)
    return t


def m_move_port(t):
    """Same speed class, different port number."""
    r1 = t.devices["R1"]
    r1.interfaces["GigabitEthernet0/2"] = r1.interfaces.pop("GigabitEthernet0/1")
    r1.interfaces["GigabitEthernet0/2"].name = "GigabitEthernet0/2"
    for link in t.links:
        if link.source_device == "R1" and link.source_interface == "GigabitEthernet0/1":
            link.source_interface = "GigabitEthernet0/2"
    return t


def m_wrong_cable(t):
    for link in t.links:
        if link.cable_type == "eStraightThrough":
            link.cable_type = "eCrossOver"
            link.conflicts = ["Incorrect Cable Type: straight-through expected"]
    return t


def m_ospf_pid(t):
    for host in ("R1", "R2"):
        for proc in t.devices[host].ospf_processes:
            proc["process_id"] = 99
    return t


def m_strip_security(t):
    for dev in t.devices.values():
        dev.has_enable_secret = False
        dev.has_password_encryption = False
        dev.has_vty_login = False
    return t


def m_strip_descriptions(t):
    for dev in t.devices.values():
        for i in dev.interfaces.values():
            i.description = None
    return t


def grade(policies, mutation=None):
    """Generate a rubric from the reference, then grade a (possibly mutated) copy."""
    ref = build_reference()
    criteria = generate_criteria_from_topology(ref, policies=policies, target_total_points=100.0)
    student = copy.deepcopy(ref)
    if mutation:
        student = mutation(student)
    return evaluate_student_submission(criteria, student)

# (toggle name, lenient settings, strict settings, mutation, scenario)
TOGGLE_CASES = [
    ("allow_dynamic_subnetting",
     {"allow_dynamic_subnetting": True}, {"allow_dynamic_subnetting": False},
     m_readdress, "student designs their own valid addressing scheme"),
    ("enforce_prefix_length",
     {"allow_dynamic_subnetting": True, "enforce_prefix_length": False},
     {"allow_dynamic_subnetting": True, "enforce_prefix_length": True},
     m_wrong_prefix, "point-to-point link built as /24 instead of /30"),
    ("verify_default_gateways",
     {"verify_default_gateways": False}, {"verify_default_gateways": True},
     m_bad_gateway, "PC gateway points outside the router subnet"),
    ("allow_custom_hostnames",
     {"allow_custom_hostnames": True}, {"allow_custom_hostnames": False},
     m_rename, "student uses their own device names"),
    ("strict_port_matching",
     {"strict_port_matching": False}, {"strict_port_matching": True},
     m_move_port, "same speed class, different port number"),
    ("strict_cable_type",
     {"strict_cable_type": False}, {"strict_cable_type": True},
     m_wrong_cable, "crossover used where straight-through was expected"),
    ("allow_flexible_process_ids",
     {"allow_flexible_process_ids": True}, {"allow_flexible_process_ids": False},
     m_ospf_pid, "OSPF process id 99 instead of 1"),
    ("grade_security_baseline",
     {"grade_security_baseline": False}, {"grade_security_baseline": True},
     m_strip_security, "no enable secret / password-encryption / vty login"),
    ("grade_interface_descriptions",
     {"grade_interface_descriptions": False}, {"grade_interface_descriptions": True},
     m_strip_descriptions, "no interface descriptions"),
]


@pytest.mark.parametrize(
    "toggle,lenient,strict,mutation,scenario",
    TOGGLE_CASES,
    ids=[case[0] for case in TOGGLE_CASES],
)
def test_toggle_changes_grading(toggle, lenient, strict, mutation, scenario):
    lenient_report = grade(EvaluationPolicies(**lenient), mutation)
    strict_report = grade(EvaluationPolicies(**strict), mutation)

    assert lenient_report.percentage > strict_report.percentage, (
        f"Policy '{toggle}' had no grading effect ({scenario}). "
        f"lenient={lenient_report.percentage}% strict={strict_report.percentage}%"
    )


def test_unmutated_reference_scores_full_marks():
    """A submission identical to the reference must always score 100%."""
    report = grade(EvaluationPolicies())
    assert report.percentage == 100.0
    assert report.failed_count == 0


def test_correct_custom_addressing_scores_full_marks():
    """
    The whole point of dynamic subnetting: a student who designs a completely
    different but correct addressing scheme loses nothing.

    This previously failed, because devices sharing one broadcast domain (a PC
    and its own default gateway) were reported as a duplicate-subnet collision.
    """
    report = grade(EvaluationPolicies(allow_dynamic_subnetting=True), m_readdress)
    failed = [r.description for r in report.results if not r.passed]
    assert report.percentage == 100.0, f"Correct custom addressing was penalised: {failed}"


def test_genuine_duplicate_subnet_is_still_caught():
    """Leniency must not go so far that a real subnet collision slips through."""
    def reuse_subnet_across_segments(topology):
        # Put the point-to-point link onto the LAN's subnet: a real error.
        for dev, intf in (("R1", "GigabitEthernet0/0"), ("R2", "GigabitEthernet0/0")):
            target = topology.devices[dev].interfaces[intf]
            target.cidr = 24
            target.subnet_mask = "255.255.255.0"
            target.network_address = "192.168.1.0"
        topology.devices["R1"].interfaces["GigabitEthernet0/0"].ip_address = "192.168.1.201"
        topology.devices["R2"].interfaces["GigabitEthernet0/0"].ip_address = "192.168.1.202"
        return topology

    report = grade(
        EvaluationPolicies(allow_dynamic_subnetting=True, enforce_prefix_length=False),
        reuse_subnet_across_segments,
    )
    assert report.percentage < 100.0
    assert any("already used" in r.feedback for r in report.results if not r.passed),         "A subnet reused across two different broadcast domains should be flagged."
