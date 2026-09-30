# tests/test_parsers.py
import pytest
from src.models import InterfaceData, ParsedDevice
from src.parsers import (
    canonical_device_name,
    classify_device_role,
    normalize_interface_name,
    parse_device_bundle,
)

SAMPLE_ROUTER = """
R1# show running-config
hostname R1
!
interface GigabitEthernet0/0
 description Link to R2
 ip address 10.0.0.1 255.255.255.252
!
interface GigabitEthernet0/1
 description LAN Network
 ip address 192.168.1.1 255.255.255.0
!
router ospf 1
 network 10.0.0.0 0.0.0.3 area 0
 network 192.168.1.0 0.0.0.255 area 0
!
R1# show cdp neighbors detail
-------------------------
Device ID: R2.cisco.lab
Entry address(es): 
  IP address: 10.0.0.2
Platform: Cisco 2911,  Capabilities: Router
Interface: GigabitEthernet0/0,  Port ID (outgoing port): GigabitEthernet0/0
!
R1# show ip interface brief
Interface              IP-Address      OK? Method Status                Protocol
GigabitEthernet0/0     10.0.0.1        YES manual up                    up      
GigabitEthernet0/1     192.168.1.1     YES manual up                    up      
GigabitEthernet0/2     unassigned      YES unset  administratively down down
!
R1# show ip route
Gateway of last resort is not set
C    10.0.0.0/30 is directly connected, GigabitEthernet0/0
C    192.168.1.0/24 is directly connected, GigabitEthernet0/1
O    10.0.0.4/30 [110/2] via 10.0.0.2, 00:05:12, GigabitEthernet0/0
S    172.16.0.0/16 [1/0] via 10.0.0.2
"""

SAMPLE_SWITCH = """
SW1# show running-config
hostname SW1
!
interface FastEthernet0/1
 description Trunk to SW2
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,99
!
interface FastEthernet0/2
 description PC1 Access
 switchport mode access
 switchport access vlan 10
!
interface Vlan10
 ip address 192.168.10.2 255.255.255.0
!
SW1# show cdp neighbors detail
-------------------------
Device ID: SW2
Platform: cisco WS-C2960-24TT-L,  Capabilities: Switch
Interface: FastEthernet0/1,  Port ID (outgoing port): FastEthernet0/1
!
SW1# show vlan brief
VLAN Name                             Status    Ports
---- -------------------------------- --------- -------------------------------
1    default                          active    Fa0/3, Fa0/4
10   Faculty                          active    Fa0/2
20   Students                         active    
99   Management                       active    
!
SW1# show interfaces trunk
Port        Mode             Encapsulation  Status        Native vlan
Fa0/1       on               802.1q         trunking      99

Port        Vlans allowed on trunk
Fa0/1       10,20,99
!
SW1# show mac address-table
          Mac Address Table
-------------------------------------------
Vlan    Mac Address       Type        Ports
----    -----------       --------    -----
  10    0050.7966.6801    DYNAMIC     Fa0/2
  10    0050.7966.6802    DYNAMIC     Fa0/1
  20    0050.7966.6803    DYNAMIC     Fa0/1
"""

def test_normalization_helpers():
    assert normalize_interface_name("Gi0/0") == "GigabitEthernet0/0"
    assert normalize_interface_name("GigabitEthernet0/0.10") == "GigabitEthernet0/0.10"
    assert normalize_interface_name("fa0/1") == "FastEthernet0/1"
    assert normalize_interface_name("Se0/1/0") == "Serial0/1/0"
    assert canonical_device_name("R2.cisco.lab") == "R2"
    assert canonical_device_name("SW1") == "SW1"

def test_parse_router_bundle():
    device = parse_device_bundle(SAMPLE_ROUTER, "R1.txt")
    assert device.hostname == "R1"
    assert device.canonical_name == "R1"
    assert device.device_type == "router"
    
    assert "GigabitEthernet0/0" in device.interfaces
    gi0 = device.interfaces["GigabitEthernet0/0"]
    assert gi0.ip_address == "10.0.0.1"
    assert gi0.subnet_mask == "255.255.255.252"
    assert gi0.cidr == 30
    assert gi0.network_address == "10.0.0.0"
    assert gi0.admin_status == "up"
    assert gi0.line_status == "up"
    assert gi0.description == "Link to R2"
    
    gi2 = device.interfaces.get("GigabitEthernet0/2")
    assert gi2 is not None
    assert gi2.admin_status == "administratively down"
    assert gi2.line_status == "down"
    
    assert len(device.cdp_neighbors) == 1
    cdp = device.cdp_neighbors[0]
    assert cdp.device_id == "R2"
    assert cdp.local_interface == "GigabitEthernet0/0"
    assert cdp.remote_interface == "GigabitEthernet0/0"
    assert cdp.remote_ip == "10.0.0.2"
    
    assert len(device.routes) >= 4
    static_route = next((r for r in device.routes if r.protocol == "S"), None)
    assert static_route is not None
    assert static_route.network == "172.16.0.0"
    assert static_route.next_hop == "10.0.0.2"

def test_parse_switch_bundle():
    device = parse_device_bundle(SAMPLE_SWITCH, "SW1.txt")
    assert device.hostname == "SW1"
    assert device.device_type == "switch"
    
    fa1 = device.interfaces["FastEthernet0/1"]
    assert fa1.is_switchport is True
    assert fa1.switchport_mode == "trunk"
    assert fa1.trunk_native_vlan == 99
    assert 10 in fa1.trunk_allowed_vlans
    assert 20 in fa1.trunk_allowed_vlans
    
    fa2 = device.interfaces["FastEthernet0/2"]
    assert fa2.switchport_mode == "access"
    assert fa2.access_vlan == 10
    
    assert 10 in device.vlans
    assert device.vlans[10] == "Faculty"
    
    assert len(device.mac_table) == 3
    mac_fa1 = [m for m in device.mac_table if m.port == "FastEthernet0/1"]
    assert len(mac_fa1) == 2

def test_parse_split_filtered_router_bundle():
    filtered_text = """
    R1# show run | include hostname
    hostname PASIG_EDGE_RTR1
    !
    R1# show run | include interface|ip address|ipv6 address|description|switchport
    interface GigabitEthernet0/0
     description TO PASIG CORE SW1
     ip address 172.16.254.5 255.255.255.252
     ipv6 address 2001:DB8:ACAD:FF::2/127
    !
    interface GigabitEthernet0/1
     description TO PASIG CORE SW2
     ip address 172.16.254.9 255.255.255.252
    !
    R1# show run | include router |network |neighbor |ip route|ipv6 route|ip routing
    ip route 10.10.10.0 255.255.255.0 172.16.254.6
    !
    R1# show cdp neighbors detail
    Device ID: PASIG_CORE_SW1
    Interface: GigabitEthernet0/0, Port ID: GigabitEthernet0/1
    !
    R1# show ip interface brief
    Interface              IP-Address      OK? Method Status Protocol
    GigabitEthernet0/0     172.16.254.5    YES manual up     up
    GigabitEthernet0/1     172.16.254.9    YES manual up     up
    !
    R1# show ip route
    C    172.16.254.4/30 is directly connected, GigabitEthernet0/0
    """
    dev = parse_device_bundle(filtered_text, "PASIG_EDGE_RTR1.txt")
    assert dev.hostname == "PASIG_EDGE_RTR1"
    assert "GigabitEthernet0/0" in dev.interfaces
    assert dev.interfaces["GigabitEthernet0/0"].ip_address == "172.16.254.5"
    assert dev.interfaces["GigabitEthernet0/0"].ipv6_address == "2001:DB8:ACAD:FF::2/127"
    assert dev.interfaces["GigabitEthernet0/0"].description == "TO PASIG CORE SW1"
    assert len(dev.cdp_neighbors) == 1
    assert dev.cdp_neighbors[0].device_id == "PASIG_CORE_SW1"
    assert any(r.network == "10.10.10.0" and r.protocol == "S" for r in dev.routes)


def test_parse_security_and_ospf_from_config():
    raw_config = """
    hostname CoreRouter
    service password-encryption
    enable secret 5 $1$mERr$hx5rVt7rPNoS4wqbXKX7x0
    !
    interface GigabitEthernet0/0
     description Connection_to_Dist1
     ip address 10.0.0.1 255.255.255.252
    !
    router ospf 10
     network 10.0.0.0 0.0.0.3 area 0
     network 192.168.1.0 0.0.0.255 area 0
    !
    line vty 0 4
     login
     password 7 0822455B0A0A
    !
    """
    dev = parse_device_bundle(raw_config, "CoreRouter.txt")
    assert dev.has_enable_secret is True
    assert dev.has_password_encryption is True
    assert dev.has_vty_login is True
    assert dev.interfaces["GigabitEthernet0/0"].description == "Connection_to_Dist1"
    assert len(dev.ospf_processes) == 1
    assert dev.ospf_processes[0]["process_id"] == 10
    assert len(dev.ospf_processes[0]["networks"]) == 2
    assert dev.ospf_processes[0]["networks"][0]["area"] == 0


def test_parse_switch_default_gateway():
    raw_config = """
    hostname SW1
    ip default-gateway 192.168.1.1
    """
    dev = parse_device_bundle(raw_config, "SW1.txt")
    assert dev.default_gateway == "192.168.1.1"




# --- Layer 2 vs Layer 3 switch classification -------------------------------
#
# device_type is assigned as a side effect of any `switchport` line while the
# config is being scanned, so before classify_device_role() existed every
# multilayer switch came out as a plain "switch". These lock the distinction.

L2_ACCESS_SWITCH = """
hostname ACCESS_SW
!
interface GigabitEthernet0/1
 switchport mode trunk
!
interface FastEthernet0/1
 switchport mode access
 switchport access vlan 10
!
interface Vlan1
 no ip address
!
interface Vlan99
 ip address 172.16.0.227 255.255.255.240
!
ip default-gateway 172.16.0.225
"""

MULTILAYER_SWITCH = """
hostname CORE_SW
!
ip routing
!
interface GigabitEthernet1/0/1
 switchport mode trunk
!
interface GigabitEthernet1/0/23
 no switchport
 ip address 172.16.254.6 255.255.255.252
!
interface Vlan10
 ip address 172.16.0.129 255.255.255.224
!
interface Vlan20
 ip address 172.16.0.161 255.255.255.240
"""


def test_l2_switch_stays_a_switch():
    """A management SVI is not routing. One addressed SVI must not promote."""
    dev = parse_device_bundle(L2_ACCESS_SWITCH, "ACCESS_SW.txt")
    assert dev.device_type == "switch"
    assert dev.has_ip_routing is False


def test_multilayer_switch_is_classified_l3():
    dev = parse_device_bundle(MULTILAYER_SWITCH, "CORE_SW.txt")
    assert dev.device_type == "l3_switch"
    assert dev.has_ip_routing is True


def test_ip_route_does_not_count_as_ip_routing():
    """`ip route` is a static route on a plain router, not L3 switching."""
    raw = """
    hostname R9
    interface GigabitEthernet0/0
     ip address 10.0.0.1 255.255.255.252
    ip route 0.0.0.0 0.0.0.0 10.0.0.2
    """
    dev = parse_device_bundle(raw, "R9.txt")
    assert dev.has_ip_routing is False
    assert dev.device_type == "router"


def test_routed_port_promotes_without_ip_routing_line():
    """`no switchport` + an address is a routed port: only an L3 switch has one."""
    raw = """
    hostname CORE2
    interface GigabitEthernet1/0/1
     switchport mode trunk
    interface GigabitEthernet1/0/24
     no switchport
     ip address 172.16.254.14 255.255.255.252
    """
    dev = parse_device_bundle(raw, "CORE2.txt")
    assert dev.device_type == "l3_switch"


def test_hardware_model_overrides_configuration():
    """A 3560 is multilayer hardware even before routing is switched on, and a
    2960 cannot route however its config reads."""
    l3 = ParsedDevice(hostname="S1", canonical_name="s1", device_type="switch",
                      hardware_model="3560-24PS")
    classify_device_role(l3)
    assert l3.device_type == "l3_switch"

    l2 = ParsedDevice(hostname="S2", canonical_name="s2", device_type="switch",
                      hardware_model="2960-24TT", has_ip_routing=True)
    classify_device_role(l2)
    assert l2.device_type == "switch"


def test_classification_never_demotes_a_router_or_host():
    """No switching evidence means the caller's answer stands."""
    router = ParsedDevice(hostname="R1", canonical_name="r1", device_type="router")
    router.interfaces["GigabitEthernet0/0"] = InterfaceData(
        name="GigabitEthernet0/0", ip_address="10.0.0.1"
    )
    classify_device_role(router)
    assert router.device_type == "router"

    host = ParsedDevice(hostname="PC0", canonical_name="pc0", device_type="host")
    classify_device_role(host)
    assert host.device_type == "host"


# --- OSPF block termination -------------------------------------------------

def test_ospf_networks_survive_sub_commands_before_them():
    """
    A real `router ospf` block opens with router-id, log-adjacency-changes and
    area range statements. Those were closing the block because the check
    looked at the STRIPPED line, so every `network` after them was discarded
    and OSPF went ungraded on any realistic config. Found on a 66-device
    Packet Tracer lab where 8 routers ran OSPF and the rubric graded none of
    it.
    """
    raw = """
hostname EDGE_RTR2
router ospf 1
 router-id 172.16.254.10
 log-adjacency-changes
 passive-interface GigabitEthernet0/2
 area 1 range 172.16.0.0 255.255.255.0
 network 172.16.254.12 0.0.0.3 area 1
 network 192.168.0.0 0.0.0.255 area 0
!
interface GigabitEthernet0/0
 ip address 10.0.0.1 255.255.255.252
"""
    dev = parse_device_bundle(raw, "EDGE_RTR2.txt")
    assert len(dev.ospf_processes) == 1
    networks = dev.ospf_processes[0]["networks"]
    assert len(networks) == 2
    assert {n["area"] for n in networks} == {0, 1}
    # The block must still close: the interface after `!` is not swallowed.
    assert "GigabitEthernet0/0" in dev.interfaces


def test_a_following_router_block_closes_the_previous_one():
    """`router bgp` after `router ospf` must not inherit its networks."""
    raw = """
hostname R9
router ospf 1
 router-id 1.1.1.1
 network 10.0.0.0 0.0.0.3 area 0
router bgp 65120
 bgp log-neighbor-changes
 neighbor 203.0.113.1 remote-as 65100
"""
    dev = parse_device_bundle(raw, "R9.txt")
    assert len(dev.ospf_processes) == 1
    assert len(dev.ospf_processes[0]["networks"]) == 1


# --- Issue #4 / #5: security baseline parsing ---

def test_enable_password_is_not_enable_secret():
    """`enable password` is the weak form the checkpoint exists to catch (#4)."""
    dev = parse_device_bundle("hostname R1\nenable password cisco\n", "R1.txt")
    assert dev.has_enable_secret is False
    assert dev.has_enable_password is True


def test_enable_secret_is_detected():
    dev = parse_device_bundle("hostname R1\nenable secret 5 $1$abc$xyz\n", "R1.txt")
    assert dev.has_enable_secret is True
    assert dev.has_enable_password is False


def test_vty_login_after_other_subcommands():
    """
    `show running-config` prints exec-timeout before login. The block must not
    close at the first sub-command that is not login/password (#5).
    """
    cfg = (
        "hostname R1\n"
        "line vty 0 4\n"
        " exec-timeout 5 0\n"
        " login local\n"
        " transport input ssh\n"
        "!\n"
    )
    assert parse_device_bundle(cfg, "R1.txt").has_vty_login is True


def test_vty_login_in_uniformly_indented_paste():
    cfg = (
        "    hostname R1\n"
        "    line vty 0 4\n"
        "     exec-timeout 5 0\n"
        "     login\n"
        "    !\n"
    )
    assert parse_device_bundle(cfg, "R1.txt").has_vty_login is True


def test_vty_no_login_is_not_secured():
    cfg = "hostname R1\nline vty 0 4\n password cisco\n no login\n!\n"
    assert parse_device_bundle(cfg, "R1.txt").has_vty_login is False


def test_login_outside_vty_block_does_not_count():
    cfg = "hostname R1\nline vty 0 4\n exec-timeout 5 0\n!\nline con 0\n login\n!\n"
    assert parse_device_bundle(cfg, "R1.txt").has_vty_login is False
