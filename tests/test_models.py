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

