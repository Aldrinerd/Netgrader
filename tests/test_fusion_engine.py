# tests/test_fusion_engine.py
import pytest
from src.fusion_engine import calculate_noisy_or, infer_topology_links
from src.models import ParsedDevice, InterfaceData, CDPNeighbor, RouteEntry
from src.parsers import parse_device_bundle

def test_noisy_or_math():
    assert calculate_noisy_or([]) == 0.0
    assert calculate_noisy_or([0.90]) == 0.90
    # Combining 0.90 and 0.80 -> 1 - (0.10 * 0.20) = 0.98
    assert round(calculate_noisy_or([0.90, 0.80]), 4) == 0.98
    # Combining 0.35 and 0.25 -> 1 - (0.65 * 0.75) = 1 - 0.4875 = 0.5125
    assert round(calculate_noisy_or([0.35, 0.25]), 4) == 0.5125

def test_infer_links_with_cdp_and_subnet():
    r1_txt = """
    hostname R1
    interface GigabitEthernet0/0
     description Link to R2
     ip address 10.0.0.1 255.255.255.252
    show cdp neighbors detail
    Device ID: R2
    Interface: GigabitEthernet0/0,  Port ID (outgoing port): GigabitEthernet0/0
    show ip route
    O 10.0.0.4/30 [110/2] via 10.0.0.2, GigabitEthernet0/0
    """
    r2_txt = """
    hostname R2
    interface GigabitEthernet0/0
     description Link to R1
     ip address 10.0.0.2 255.255.255.252
    show cdp neighbors detail
    Device ID: R1
    Interface: GigabitEthernet0/0,  Port ID (outgoing port): GigabitEthernet0/0
    """
    d1 = parse_device_bundle(r1_txt, "R1.txt")
    d2 = parse_device_bundle(r2_txt, "R2.txt")
    devices = {"R1": d1, "R2": d2}
    
    links = infer_topology_links(devices)
    assert len(links) == 1
    link = links[0]
    
    assert link.source_device == "R1"
    assert link.target_device == "R2"
    assert link.source_interface == "GigabitEthernet0/0"
    assert link.target_interface == "GigabitEthernet0/0"
    assert link.confidence >= 0.95
    assert link.classification == "verified"
    assert link.is_bidirectional is True
    
    signal_types = [s.signal_type for s in link.signals]
    assert "CDP_NEIGHBOR_DETAIL" in signal_types
    assert "P2P_SUBNET_30_31" in signal_types

def test_infer_switch_trunk_link():
    sw1_txt = """
    hostname SW1
    interface FastEthernet0/24
     switchport mode trunk
     switchport trunk native vlan 99
     switchport trunk allowed vlan 10,20,99
    show cdp neighbors detail
    Device ID: SW2
    Interface: FastEthernet0/24,  Port ID (outgoing port): FastEthernet0/24
    """
    sw2_txt = """
    hostname SW2
    interface FastEthernet0/24
     switchport mode trunk
     switchport trunk native vlan 99
     switchport trunk allowed vlan 10,20,99
    show cdp neighbors detail
    Device ID: SW1
    Interface: FastEthernet0/24,  Port ID (outgoing port): FastEthernet0/24
    """
    d1 = parse_device_bundle(sw1_txt, "SW1.txt")
    d2 = parse_device_bundle(sw2_txt, "SW2.txt")
    devices = {"SW1": d1, "SW2": d2}
    
    links = infer_topology_links(devices)
    assert len(links) == 1
    link = links[0]
    assert link.classification == "verified"
    signal_types = [s.signal_type for s in link.signals]
    assert "CDP_NEIGHBOR_DETAIL" in signal_types
    assert "TRUNK_CONFIG_PAIR" in signal_types
