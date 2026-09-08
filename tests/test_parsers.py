# tests/test_parsers.py
import pytest
from src.parsers import parse_device_bundle, normalize_interface_name, canonical_device_name

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


