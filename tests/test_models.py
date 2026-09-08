# tests/test_models.py
import pytest
from src.models import (
    InterfaceData,
    ParsedDevice,
    DiscoveredLink,
    ContributingSignal,
    ConflictIssue,
    TopologyResult,
)

def test_interface_and_device_model():
    intf = InterfaceData(
        name="GigabitEthernet0/0",
        ip_address="192.168.1.1",
        subnet_mask="255.255.255.252",
        cidr=30,
        network_address="192.168.1.0",
        admin_status="up",
        line_status="up",
        evidence_lines={"ip": 12, "status": 45}
    )
    device = ParsedDevice(
        hostname="R1",
        canonical_name="R1",
        device_type="router",
        raw_filename="R1.txt",
        interfaces={"GigabitEthernet0/0": intf}
    )
    assert device.hostname == "R1"
    assert device.canonical_name == "R1"
    assert device.device_type == "router"
    assert device.interfaces["GigabitEthernet0/0"].cidr == 30
    assert device.interfaces["GigabitEthernet0/0"].evidence_lines["ip"] == 12

def test_discovered_link_model():
    signal = ContributingSignal(
        signal_type="CDP_NEIGHBOR_DETAIL",
        description="Explicit CDP neighbor match",
        weight=1.0,
        evidence=["R1.txt line 45"]
    )
    link = DiscoveredLink(
        source_device="R1",
        source_interface="GigabitEthernet0/0",
        target_device="R2",
        target_interface="GigabitEthernet0/0",
        confidence=1.0,
        classification="verified",
        signals=[signal],
        is_bidirectional=True
    )
    assert link.confidence == 1.0
    assert link.classification == "verified"
    assert link.is_bidirectional is True
    assert len(link.signals) == 1

def test_conflict_issue_and_topology_result():
    conflict = ConflictIssue(
        severity="error",
        category="subnet_mismatch",
        title="Subnet Mismatch on Physical Link",
        description="R1 and R2 are physically connected but have mismatched subnets",
        involved_devices=["R1", "R2"],
        involved_interfaces=["GigabitEthernet0/0", "GigabitEthernet0/0"],
        evidence_citations=["R1.txt: line 42", "R2.txt: line 38"]
    )
    result = TopologyResult(
        devices={},
        links=[],
        conflicts=[conflict]
    )
    assert len(result.conflicts) == 1
    assert result.conflicts[0].category == "subnet_mismatch"

def test_placeholder_parsed_device():
    dev = ParsedDevice(
        hostname="???",
        canonical_name="UNKNOWN_R1_Gi0/1",
        display_name="???",
        is_placeholder=True,
        device_type="unknown",
        placeholder_for_device="PLDT",
        placeholder_for_interface="GigabitEthernet0/1",
        raw_filename=""
    )
    assert dev.is_placeholder is True
    assert dev.display_name == "???"
    assert dev.device_type == "unknown"
    assert dev.placeholder_for_device == "PLDT"
    assert dev.placeholder_for_interface == "GigabitEthernet0/1"

def test_parsed_device_coordinates_and_cable_type():
    dev = ParsedDevice(
        hostname="Router1",
        canonical_name="Router1",
        x_coord=1250.5,
        y_coord=890.25
    )
    assert dev.x_coord == 1250.5
    assert dev.y_coord == 890.25
    
    link = DiscoveredLink(
        source_device="Router1",
        source_interface="FastEthernet0/0",
        target_device="Router2",
        target_interface="FastEthernet0/1",
        confidence=1.0,
        classification="verified",
        cable_type="eCrossOver",
        signals=[ContributingSignal(signal_type="PACKET_TRACER_PHYSICAL_CABLE", description="CrossOver cable", weight=1.0)]
    )
    assert link.cable_type == "eCrossOver"
    assert link.confidence == 1.0


def test_evaluation_policies_defaults():
    from src.models import EvaluationPolicies
    policies = EvaluationPolicies()
    assert policies.allow_dynamic_subnetting is False
    assert policies.enforce_prefix_length is True
    assert policies.verify_default_gateways is True
    assert policies.allow_custom_hostnames is False
    assert policies.strict_port_matching is True
    assert policies.strict_cable_type is True
    assert policies.allow_flexible_process_ids is True
    assert policies.grade_security_baseline is False
    assert policies.grade_interface_descriptions is False


def test_criteria_with_policies_and_new_categories():
    from src.models import EvaluationCriteria, EvaluationPolicies, EvaluationRule
    policies = EvaluationPolicies(
        allow_dynamic_subnetting=True,
        grade_security_baseline=True
    )
    rule1 = EvaluationRule(
        rule_id="rel_subnet_r1_r2",
        category="relational_subnet",
        description="Verify mutual /30 point-to-point subnet between R1 and R2",
        points=15.0,
        target_device="R1",
        target_interface="GigabitEthernet0/0",
        expected_value={
            "peer_device": "R2",
            "peer_interface": "GigabitEthernet0/0",
            "expected_prefixlen": 30,
            "link_type": "point_to_point"
        }
    )
    rule2 = EvaluationRule(
        rule_id="sec_r1_secret",
        category="security",
        description="Enable secret password configured on R1",
        points=5.0,
        target_device="R1",
        expected_value={"check_type": "enable_secret"}
    )
    criteria = EvaluationCriteria(
        lab_title="Dynamic Subnetting Lab",
        policies=policies,
        rules=[rule1, rule2]
    )
    assert criteria.policies.allow_dynamic_subnetting is True
    assert criteria.policies.grade_security_baseline is True
    assert len(criteria.rules) == 2
    assert criteria.rules[0].category == "relational_subnet"
    assert criteria.rules[1].category == "security"


def test_parsed_device_security_and_gateway_attributes():
    dev = ParsedDevice(
        hostname="R1",
        canonical_name="R1",
        device_type="router",
        default_gateway="192.168.1.1",
        has_enable_secret=True,
        has_password_encryption=True,
        has_vty_login=True,
        ospf_processes=[{"process_id": 1, "networks": [{"network": "10.0.0.0", "wildcard": "0.0.0.3", "area": 0}]}]
    )
    assert dev.default_gateway == "192.168.1.1"
    assert dev.has_enable_secret is True
    assert dev.has_password_encryption is True
    assert dev.has_vty_login is True
    assert len(dev.ospf_processes) == 1
    assert dev.ospf_processes[0]["process_id"] == 1

