# validation/reference.py
"""
The known-good network every mutation is injected into.

Built in code rather than parsed from text so that each fault can be injected
surgically and the ground truth stays unambiguous. It is deliberately small
but exercises every rule category the engine can emit:

    PC1 --- SW1 =====trunk===== SW2 --- PC2
             |
            R1 ------------- R2          (OSPF area 0, /30 point-to-point)

  device            R1, R2, SW1, SW2, PC1, PC2
  interface_ip      every routed interface
  interface_status  router interfaces up
  cabling           five links
  vlan_trunk        trunk ports and access ports
  link_agreement    native VLAN, VLAN coverage, switchport mode on the trunk
  gateway           both PCs and both switches
  routing           OSPF area 0 on R1 and R2
  security          enable secret / password-encryption / vty login
  relational_subnet under allow_dynamic_subnetting
"""

from src.models import (
    DiscoveredLink,
    InterfaceData,
    ParsedDevice,
    TopologyResult,
)


def _routed(name: str, ip: str, cidr: int, network: str) -> InterfaceData:
    mask = {30: "255.255.255.252", 24: "255.255.255.0"}[cidr]
    return InterfaceData(
        name=name, ip_address=ip, cidr=cidr, subnet_mask=mask,
        network_address=network, admin_status="up", line_status="up",
        description=f"Link via {name}",
    )


def _trunk(name: str, native: int = 99, allowed=(10, 20, 99)) -> InterfaceData:
    return InterfaceData(
        name=name, is_switchport=True, switchport_mode="trunk",
        trunk_native_vlan=native, trunk_allowed_vlans=list(allowed),
        admin_status="up", line_status="up", description="Inter-switch trunk",
    )


def _access(name: str, vlan: int) -> InterfaceData:
    return InterfaceData(
        name=name, is_switchport=True, switchport_mode="access",
        access_vlan=vlan, admin_status="up", line_status="up",
        description=f"Access port VLAN {vlan}",
    )


def _svi(name: str, ip: str) -> InterfaceData:
    return InterfaceData(
        name=name, ip_address=ip, cidr=24, subnet_mask="255.255.255.0",
        network_address="192.168.99.0", admin_status="up", line_status="up",
        description="Management SVI",
    )


def _hardened(dev: ParsedDevice) -> ParsedDevice:
    dev.has_enable_secret = True
    dev.has_password_encryption = True
    dev.has_vty_login = True
    return dev


def build_reference() -> TopologyResult:
    """A correct network. Graded against its own rubric it must score 100%."""
    r1 = _hardened(ParsedDevice(
        hostname="R1", canonical_name="r1", display_name="R1", device_type="router",
        raw_filename="R1.txt",
        interfaces={
            "GigabitEthernet0/0": _routed("GigabitEthernet0/0", "10.0.0.1", 30, "10.0.0.0"),
            "GigabitEthernet0/1": _routed("GigabitEthernet0/1", "192.168.10.1", 24, "192.168.10.0"),
        },
        ospf_processes=[{
            "process_id": 1,
            "networks": [
                {"network": "10.0.0.0", "wildcard": "0.0.0.3", "area": 0},
                {"network": "192.168.10.0", "wildcard": "0.0.0.255", "area": 0},
            ],
        }],
    ))

    r2 = _hardened(ParsedDevice(
        hostname="R2", canonical_name="r2", display_name="R2", device_type="router",
        raw_filename="R2.txt",
        interfaces={
            "GigabitEthernet0/0": _routed("GigabitEthernet0/0", "10.0.0.2", 30, "10.0.0.0"),
        },
        ospf_processes=[{
            "process_id": 1,
            "networks": [{"network": "10.0.0.0", "wildcard": "0.0.0.3", "area": 0}],
        }],
    ))

    sw1 = _hardened(ParsedDevice(
        hostname="SW1", canonical_name="sw1", display_name="SW1", device_type="switch",
        raw_filename="SW1.txt", default_gateway="192.168.99.254",
        interfaces={
            "GigabitEthernet0/1": _access("GigabitEthernet0/1", 10),
            "GigabitEthernet0/2": _trunk("GigabitEthernet0/2"),
            "FastEthernet0/1": _access("FastEthernet0/1", 10),
            "Vlan99": _svi("Vlan99", "192.168.99.1"),
        },
        vlans={10: "USERS", 20: "SALES", 99: "MANAGEMENT"},
    ))

    sw2 = _hardened(ParsedDevice(
        hostname="SW2", canonical_name="sw2", display_name="SW2", device_type="switch",
        raw_filename="SW2.txt", default_gateway="192.168.99.254",
        interfaces={
            "GigabitEthernet0/2": _trunk("GigabitEthernet0/2"),
            "FastEthernet0/1": _access("FastEthernet0/1", 10),
            "Vlan99": _svi("Vlan99", "192.168.99.2"),
        },
        vlans={10: "USERS", 20: "SALES", 99: "MANAGEMENT"},
    ))

    pc1 = ParsedDevice(
        hostname="PC1", canonical_name="pc1", display_name="PC1", device_type="host",
        raw_filename="PC1.txt", default_gateway="192.168.10.1",
        interfaces={
            "FastEthernet0": _routed("FastEthernet0", "192.168.10.11", 24, "192.168.10.0"),
        },
    )

    pc2 = ParsedDevice(
        hostname="PC2", canonical_name="pc2", display_name="PC2", device_type="host",
        raw_filename="PC2.txt", default_gateway="192.168.10.1",
        interfaces={
            "FastEthernet0": _routed("FastEthernet0", "192.168.10.12", 24, "192.168.10.0"),
        },
    )

    def link(a, ai, b, bi, cable="eStraightThrough"):
        return DiscoveredLink(
            source_device=a, source_interface=ai,
            target_device=b, target_interface=bi,
            confidence=0.99, classification="verified", cable_type=cable,
        )

    return TopologyResult(
        devices={"R1": r1, "R2": r2, "SW1": sw1, "SW2": sw2, "PC1": pc1, "PC2": pc2},
        links=[
            link("R1", "GigabitEthernet0/0", "R2", "GigabitEthernet0/0", "eCrossOver"),
            link("R1", "GigabitEthernet0/1", "SW1", "GigabitEthernet0/1"),
            link("SW1", "GigabitEthernet0/2", "SW2", "GigabitEthernet0/2", "eCrossOver"),
            link("SW1", "FastEthernet0/1", "PC1", "FastEthernet0"),
            link("SW2", "FastEthernet0/1", "PC2", "FastEthernet0"),
        ],
    )
