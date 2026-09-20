# tests/fixtures.py
"""
Reference Cisco configuration bundles used by the test suite.

These were previously shipped as in-app "demo scenarios". The demo feature was
removed from the product, but the bundles remain valuable as realistic,
multi-device grading fixtures, so they live here instead.

  network_bundle("ospf_clean")            converged 3-router OSPF ring
  network_bundle("subnet_cabling_error")  subnet mismatch + downed link
  network_bundle("vlan_trunk_mismatch")   native VLAN mismatch on a trunk
"""

PRESET_FILES = {
    "ospf_clean": {
        "R1.txt": """R1# show running-config
hostname R1
!
interface GigabitEthernet0/0
 description Link to R2
 ip address 10.0.0.1 255.255.255.252
!
interface GigabitEthernet0/1
 description Link to R3
 ip address 10.0.0.5 255.255.255.252
!
interface GigabitEthernet0/2
 description HQ LAN Subnet
 ip address 192.168.10.1 255.255.255.0
!
router ospf 1
 network 10.0.0.0 0.0.0.3 area 0
 network 10.0.0.4 0.0.0.3 area 0
 network 192.168.10.0 0.0.0.255 area 0
!
R1# show cdp neighbors detail
-------------------------
Device ID: R2
Entry address(es): 
  IP address: 10.0.0.2
Platform: Cisco 2911,  Capabilities: Router
Interface: GigabitEthernet0/0,  Port ID (outgoing port): GigabitEthernet0/0
-------------------------
Device ID: R3
Entry address(es): 
  IP address: 10.0.0.6
Platform: Cisco 2911,  Capabilities: Router
Interface: GigabitEthernet0/1,  Port ID (outgoing port): GigabitEthernet0/0
!
R1# show ip interface brief
Interface              IP-Address      OK? Method Status                Protocol
GigabitEthernet0/0     10.0.0.1        YES manual up                    up      
GigabitEthernet0/1     10.0.0.5        YES manual up                    up      
GigabitEthernet0/2     192.168.10.1    YES manual up                    up      
!
R1# show ip route
Gateway of last resort is not set
C    10.0.0.0/30 is directly connected, GigabitEthernet0/0
C    10.0.0.4/30 is directly connected, GigabitEthernet0/1
C    192.168.10.0/24 is directly connected, GigabitEthernet0/2
O    10.0.0.8/30 [110/2] via 10.0.0.2, 00:12:34, GigabitEthernet0/0
O    192.168.20.0/24 [110/2] via 10.0.0.2, 00:12:34, GigabitEthernet0/0
O    192.168.30.0/24 [110/2] via 10.0.0.6, 00:12:34, GigabitEthernet0/1
""",
        "R2.txt": """R2# show running-config
hostname R2
!
interface GigabitEthernet0/0
 description Link to R1
 ip address 10.0.0.2 255.255.255.252
!
interface GigabitEthernet0/1
 description Link to R3
 ip address 10.0.0.9 255.255.255.252
!
interface GigabitEthernet0/2
 description Branch 1 LAN
 ip address 192.168.20.1 255.255.255.0
!
router ospf 1
 network 10.0.0.0 0.0.0.3 area 0
 network 10.0.0.8 0.0.0.3 area 0
 network 192.168.20.0 0.0.0.255 area 0
!
R2# show cdp neighbors detail
-------------------------
Device ID: R1
Entry address(es): 
  IP address: 10.0.0.1
Platform: Cisco 2911,  Capabilities: Router
Interface: GigabitEthernet0/0,  Port ID (outgoing port): GigabitEthernet0/0
-------------------------
Device ID: R3
Entry address(es): 
  IP address: 10.0.0.10
Platform: Cisco 2911,  Capabilities: Router
Interface: GigabitEthernet0/1,  Port ID (outgoing port): GigabitEthernet0/1
!
R2# show ip interface brief
Interface              IP-Address      OK? Method Status                Protocol
GigabitEthernet0/0     10.0.0.2        YES manual up                    up      
GigabitEthernet0/1     10.0.0.9        YES manual up                    up      
GigabitEthernet0/2     192.168.20.1    YES manual up                    up      
!
R2# show ip route
Gateway of last resort is not set
C    10.0.0.0/30 is directly connected, GigabitEthernet0/0
C    10.0.0.8/30 is directly connected, GigabitEthernet0/1
C    192.168.20.0/24 is directly connected, GigabitEthernet0/2
O    10.0.0.4/30 [110/2] via 10.0.0.1, 00:14:10, GigabitEthernet0/0
O    192.168.10.0/24 [110/2] via 10.0.0.1, 00:14:10, GigabitEthernet0/0
O    192.168.30.0/24 [110/2] via 10.0.0.10, 00:14:10, GigabitEthernet0/1
""",
        "R3.txt": """R3# show running-config
hostname R3
!
interface GigabitEthernet0/0
 description Link to R1
 ip address 10.0.0.6 255.255.255.252
!
interface GigabitEthernet0/1
 description Link to R2
 ip address 10.0.0.10 255.255.255.252
!
interface GigabitEthernet0/2
 description Branch 2 LAN
 ip address 192.168.30.1 255.255.255.0
!
router ospf 1
 network 10.0.0.4 0.0.0.3 area 0
 network 10.0.0.8 0.0.0.3 area 0
 network 192.168.30.0 0.0.0.255 area 0
!
R3# show cdp neighbors detail
-------------------------
Device ID: R1
Entry address(es): 
  IP address: 10.0.0.5
Platform: Cisco 2911,  Capabilities: Router
Interface: GigabitEthernet0/0,  Port ID (outgoing port): GigabitEthernet0/1
-------------------------
Device ID: R2
Entry address(es): 
  IP address: 10.0.0.9
Platform: Cisco 2911,  Capabilities: Router
Interface: GigabitEthernet0/1,  Port ID (outgoing port): GigabitEthernet0/1
!
R3# show ip interface brief
Interface              IP-Address      OK? Method Status                Protocol
GigabitEthernet0/0     10.0.0.6        YES manual up                    up      
GigabitEthernet0/1     10.0.0.10       YES manual up                    up      
GigabitEthernet0/2     192.168.30.1    YES manual up                    up      
!
R3# show ip route
Gateway of last resort is not set
C    10.0.0.4/30 is directly connected, GigabitEthernet0/0
C    10.0.0.8/30 is directly connected, GigabitEthernet0/1
C    192.168.30.0/24 is directly connected, GigabitEthernet0/2
O    10.0.0.0/30 [110/2] via 10.0.0.5, 00:15:20, GigabitEthernet0/0
O    192.168.10.0/24 [110/2] via 10.0.0.5, 00:15:20, GigabitEthernet0/0
O    192.168.20.0/24 [110/2] via 10.0.0.9, 00:15:20, GigabitEthernet0/1
"""
    },
    "subnet_cabling_error": {
        "R1.txt": """R1# show running-config
hostname R1
!
interface GigabitEthernet0/0
 description Link to R2
 ip address 192.168.1.1 255.255.255.0
 shutdown
!
interface GigabitEthernet0/1
 description HQ Management
 ip address 172.16.50.1 255.255.255.0
!
R1# show cdp neighbors detail
-------------------------
Device ID: R2
Entry address(es): 
  IP address: 192.168.2.2
Platform: Cisco 2911,  Capabilities: Router
Interface: GigabitEthernet0/0,  Port ID (outgoing port): GigabitEthernet0/0
!
R1# show ip interface brief
Interface              IP-Address      OK? Method Status                Protocol
GigabitEthernet0/0     192.168.1.1     YES manual administratively down down    
GigabitEthernet0/1     172.16.50.1     YES manual up                    up      
""",
        "R2.txt": """R2# show running-config
hostname R2
!
interface GigabitEthernet0/0
 description Link to R1
 ip address 192.168.2.2 255.255.255.0
!
interface GigabitEthernet0/1
 description Remote Branch Management - ACCIDENTAL DUPLICATE
 ip address 172.16.50.1 255.255.255.0
!
R2# show cdp neighbors detail
-------------------------
Device ID: R1
Entry address(es): 
  IP address: 192.168.1.1
Platform: Cisco 2911,  Capabilities: Router
Interface: GigabitEthernet0/0,  Port ID (outgoing port): GigabitEthernet0/0
!
R2# show ip interface brief
Interface              IP-Address      OK? Method Status                Protocol
GigabitEthernet0/0     192.168.2.2     YES manual up                    up      
GigabitEthernet0/1     172.16.50.1     YES manual up                    up      
"""
    },
    "vlan_trunk_mismatch": {
        "SW1.txt": """SW1# show running-config
hostname SW1
!
interface FastEthernet0/24
 description Trunk to SW2
 switchport mode trunk
 switchport trunk native vlan 1
 switchport trunk allowed vlan 10,20
!
interface FastEthernet0/1
 description PC1 Access Port
 switchport mode access
 switchport access vlan 10
!
SW1# show cdp neighbors detail
-------------------------
Device ID: SW2
Platform: cisco WS-C2960-24TT-L,  Capabilities: Switch
Interface: FastEthernet0/24,  Port ID (outgoing port): FastEthernet0/24
!
SW1# show vlan brief
VLAN Name                             Status    Ports
---- -------------------------------- --------- -------------------------------
1    default                          active    Fa0/2, Fa0/3, Fa0/4
10   Engineering                      active    Fa0/1
20   Accounting                       active    
!
SW1# show interfaces trunk
Port        Mode             Encapsulation  Status        Native vlan
Fa0/24      on               802.1q         trunking      1

Port        Vlans allowed on trunk
Fa0/24      10,20
!
SW1# show mac address-table
          Mac Address Table
-------------------------------------------
Vlan    Mac Address       Type        Ports
----    -----------       --------    -----
  10    0001.4255.1101    DYNAMIC     Fa0/1
  10    0001.4255.2201    DYNAMIC     Fa0/24
  20    0001.4255.3301    DYNAMIC     Fa0/24
""",
        "SW2.txt": """SW2# show running-config
hostname SW2
!
interface FastEthernet0/24
 description Trunk to SW1
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,99
!
interface FastEthernet0/1
 description PC2 Access Port
 switchport mode access
 switchport access vlan 20
!
SW2# show cdp neighbors detail
-------------------------
Device ID: SW1
Platform: cisco WS-C2960-24TT-L,  Capabilities: Switch
Interface: FastEthernet0/24,  Port ID (outgoing port): FastEthernet0/24
!
SW2# show vlan brief
VLAN Name                             Status    Ports
---- -------------------------------- --------- -------------------------------
1    default                          active    Fa0/2, Fa0/3
10   Engineering                      active    
20   Accounting                       active    Fa0/1
99   Management                       active    
!
SW2# show interfaces trunk
Port        Mode             Encapsulation  Status        Native vlan
Fa0/24      on               802.1q         trunking      99

Port        Vlans allowed on trunk
Fa0/24      10,20,99
!
SW2# show mac address-table
          Mac Address Table
-------------------------------------------
Vlan    Mac Address       Type        Ports
----    -----------       --------    -----
  20    0001.4255.4401    DYNAMIC     Fa0/1
  10    0001.4255.1101    DYNAMIC     Fa0/24
"""
    }
}

def network_bundle(name: str) -> dict[str, str]:
    """Return a {filename: config_text} bundle by name."""
    if name not in PRESET_FILES:
        raise ValueError(f"Unknown fixture '{name}'. Available: {list(PRESET_FILES)}")
    # Copy so a test mutating a bundle cannot affect another test.
    return dict(PRESET_FILES[name])
