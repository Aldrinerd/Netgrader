# validation/reference_text.py
"""
The same network as validation/reference.py, written as Cisco CLI output.

validation/reference.py constructs ParsedDevice objects directly, which makes
mutations surgical but leaves the parser completely unmeasured: every fact is
handed to the grading engine already extracted. That blind spot let a bug hide
in which the first sub-command of a `router ospf` block closed the block and
discarded every network statement, so OSPF went ungraded on any realistically
written config. 174 tests passed and the validation suite reported 100%.

These bundles close that gap. Parsed through the real parser they must yield
the same rubric and the same score as the constructed objects; anything the
parser drops makes the two diverge, and harness.check_fidelity() names it.

Written the way Cisco actually emits config -- sub-commands before network
statements, descriptions, `!` separators -- rather than the way that happens
to be easy to parse.

PCs are absent on purpose. A PC has no CLI and never appears in a config
bundle, so the parser is not responsible for one; the fidelity check takes
hosts and cabling from the constructed reference and compares only what
parsing is actually accountable for.
"""

CONFIG_BUNDLES: dict[str, str] = {

    "R1.txt": """R1#show running-config
Building configuration...
!
version 15.1
service password-encryption
!
hostname R1
!
enable secret 5 $1$mERr$9cTjUIEqNGurQiFU.ZeCi1
!
interface GigabitEthernet0/0
 description Link via GigabitEthernet0/0
 ip address 10.0.0.1 255.255.255.252
 ip ospf hello-interval 10
 ip ospf dead-interval 40
 duplex auto
 speed auto
!
interface GigabitEthernet0/1
 description Link via GigabitEthernet0/1
 ip address 192.168.10.1 255.255.255.0
 duplex auto
 speed auto
!
router ospf 1
 router-id 1.1.1.1
 log-adjacency-changes
 network 10.0.0.0 0.0.0.3 area 0
 network 192.168.10.0 0.0.0.255 area 0
!
line vty 0 4
 password 7 0822455D0A16
 login
!
end
""",

    "R2.txt": """R2#show running-config
Building configuration...
!
version 15.1
service password-encryption
!
hostname R2
!
enable secret 5 $1$mERr$9cTjUIEqNGurQiFU.ZeCi1
!
interface GigabitEthernet0/0
 description Link via GigabitEthernet0/0
 ip address 10.0.0.2 255.255.255.252
 ip ospf hello-interval 10
 ip ospf dead-interval 40
 duplex auto
 speed auto
!
router ospf 1
 router-id 2.2.2.2
 log-adjacency-changes
 network 10.0.0.0 0.0.0.3 area 0
!
line vty 0 4
 password 7 0822455D0A16
 login
!
end
""",

    "SW1.txt": """SW1#show running-config
Building configuration...
!
version 15.0
service password-encryption
!
hostname SW1
!
enable secret 5 $1$mERr$9cTjUIEqNGurQiFU.ZeCi1
!
interface GigabitEthernet0/1
 description Access port VLAN 10
 switchport access vlan 10
 switchport mode access
!
interface GigabitEthernet0/2
 description Inter-switch trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,99
 switchport mode trunk
!
interface FastEthernet0/1
 description Access port VLAN 10
 switchport access vlan 10
 switchport mode access
!
interface Vlan99
 description Management SVI
 ip address 192.168.99.1 255.255.255.0
!
ip default-gateway 192.168.99.254
!
line vty 0 4
 password 7 0822455D0A16
 login
!
end
SW1#show vlan brief

VLAN Name                             Status    Ports
---- -------------------------------- --------- -------------------------------
10   USERS                            active    Gig0/1, Fa0/1
20   SALES                            active
99   MANAGEMENT                       active
""",

    "SW2.txt": """SW2#show running-config
Building configuration...
!
version 15.0
service password-encryption
!
hostname SW2
!
enable secret 5 $1$mERr$9cTjUIEqNGurQiFU.ZeCi1
!
interface GigabitEthernet0/2
 description Inter-switch trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,99
 switchport mode trunk
!
interface FastEthernet0/1
 description Access port VLAN 10
 switchport access vlan 10
 switchport mode access
!
interface Vlan99
 description Management SVI
 ip address 192.168.99.2 255.255.255.0
!
ip default-gateway 192.168.99.254
!
line vty 0 4
 password 7 0822455D0A16
 login
!
end
SW2#show vlan brief

VLAN Name                             Status    Ports
---- -------------------------------- --------- -------------------------------
10   USERS                            active    Fa0/1
20   SALES                            active
99   MANAGEMENT                       active
""",
}

# Devices that have a CLI and therefore appear in a config bundle. Everything
# else in the reference topology is supplied by the constructed version.
CLI_DEVICES = ("R1", "R2", "SW1", "SW2")
