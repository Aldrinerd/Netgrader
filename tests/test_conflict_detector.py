# tests/test_conflict_detector.py
import pytest
from src.conflict_detector import detect_conflicts
from src.fusion_engine import infer_topology_links
from src.parsers import parse_device_bundle

def test_detect_subnet_mismatch_and_down_interface():
    r1_txt = """
    hostname R1
    interface GigabitEthernet0/0
     description Link to R2
     ip address 192.168.1.1 255.255.255.0
    show cdp neighbors detail
    Device ID: R2
    Interface: GigabitEthernet0/0,  Port ID (outgoing port): GigabitEthernet0/0
    show ip interface brief
    GigabitEthernet0/0 192.168.1.1 YES manual administratively down down
    """
    r2_txt = """
    hostname R2
    interface GigabitEthernet0/0
     description Link to R1
     ip address 192.168.2.2 255.255.255.0
    show cdp neighbors detail
    Device ID: R1
    Interface: GigabitEthernet0/0,  Port ID (outgoing port): GigabitEthernet0/0
    show ip interface brief
    GigabitEthernet0/0 192.168.2.2 YES manual up up
    """
    d1 = parse_device_bundle(r1_txt, "R1.txt")
    d2 = parse_device_bundle(r2_txt, "R2.txt")
    devices = {"R1": d1, "R2": d2}
    links = infer_topology_links(devices)
    
    conflicts = detect_conflicts(devices, links)
    categories = [c.category for c in conflicts]
    assert "subnet_mismatch" in categories
    assert "interface_down" in categories
    
    sub_conflict = next(c for c in conflicts if c.category == "subnet_mismatch")
    assert "R1" in sub_conflict.involved_devices
    assert "R2" in sub_conflict.involved_devices
    assert any("R1.txt" in cit for cit in sub_conflict.evidence_citations)

def test_detect_duplicate_ip():
    r1_txt = """
    hostname R1
    interface GigabitEthernet0/1
     ip address 192.168.10.1 255.255.255.0
    """
    r2_txt = """
    hostname R2
    interface GigabitEthernet0/1
     ip address 192.168.10.1 255.255.255.0
    """
    d1 = parse_device_bundle(r1_txt, "R1.txt")
    d2 = parse_device_bundle(r2_txt, "R2.txt")
    devices = {"R1": d1, "R2": d2}
    links = infer_topology_links(devices)
    
    conflicts = detect_conflicts(devices, links)
    categories = [c.category for c in conflicts]
    assert "duplicate_ip" in categories
    dup = next(c for c in conflicts if c.category == "duplicate_ip")
    assert "192.168.10.1" in dup.description

def test_detect_trunk_native_vlan_mismatch():
    sw1_txt = """
    hostname SW1
    interface FastEthernet0/24
     switchport mode trunk
     switchport trunk native vlan 1
    show cdp neighbors detail
    Device ID: SW2
    Interface: FastEthernet0/24,  Port ID (outgoing port): FastEthernet0/24
    """
    sw2_txt = """
    hostname SW2
    interface FastEthernet0/24
     switchport mode trunk
     switchport trunk native vlan 99
    show cdp neighbors detail
    Device ID: SW1
    Interface: FastEthernet0/24,  Port ID (outgoing port): FastEthernet0/24
    """
    d1 = parse_device_bundle(sw1_txt, "SW1.txt")
    d2 = parse_device_bundle(sw2_txt, "SW2.txt")
    devices = {"SW1": d1, "SW2": d2}
    links = infer_topology_links(devices)
    
    conflicts = detect_conflicts(devices, links)
    categories = [c.category for c in conflicts]
    assert "vlan_trunk_mismatch" in categories

def test_conflict_detector_ignores_placeholder_devices():
    from src.models import ParsedDevice, DiscoveredLink, ContributingSignal
    dev = ParsedDevice(hostname="R1", canonical_name="R1", raw_filename="R1.txt")
    placeholder = ParsedDevice(
        hostname="???",
        canonical_name="UNKNOWN_R1_Gi0/0",
        display_name="???",
        is_placeholder=True,
        device_type="unknown"
    )
    devices = {"R1": dev, "UNKNOWN_R1_Gi0/0": placeholder}
    link = DiscoveredLink(
        source_device="R1",
        source_interface="GigabitEthernet0/0",
        target_device="UNKNOWN_R1_Gi0/0",
        target_interface="Unspecified",
        confidence=0.5,
        classification="inferred",
        signals=[ContributingSignal(signal_type="ACTIVE_PORT_CARRIER", description="Active port carrier", weight=0.5)]
    )
    conflicts = detect_conflicts(devices, [link])
    assert not any(c.category == "subnet_mismatch" for c in conflicts)
    assert not any(c.category == "vlan_trunk_mismatch" for c in conflicts)

