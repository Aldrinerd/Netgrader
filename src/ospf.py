# src/ospf.py
"""
One normalised view of where OSPF runs on a device.

IOS has two ways to put an interface into OSPF:

  router ospf 1                       interface GigabitEthernet0/0
   network 10.0.0.0 0.0.0.3 area 0     ip ospf 1 area 0

Both mean the same thing: "process P runs on interface I in area A". Rule
generation and grading both read this view, so a reference written in one
style and a student answer written in the other still agree (issue #2).
"""

import ipaddress

from src.models import ParsedDevice


def _wildcard_contains(network: str, wildcard: str, address: str) -> bool:
    """True when `address` matches `network` under the IOS wildcard mask."""
    try:
        net = int(ipaddress.IPv4Address(network))
        wild = int(ipaddress.IPv4Address(wildcard))
        addr = int(ipaddress.IPv4Address(address))
    except (ipaddress.AddressValueError, ValueError):
        return False
    care = ~wild & 0xFFFFFFFF
    return (net & care) == (addr & care)


def _wildcard_bits(wildcard: str) -> int:
    try:
        return bin(int(ipaddress.IPv4Address(wildcard))).count("1")
    except (ipaddress.AddressValueError, ValueError):
        return 32


def statement_covers(statement: dict, subnet: str) -> bool:
    """True when a `network ... area ...` statement covers the whole subnet.

    `network 10.0.0.0 0.0.255.255 area 0` covers 10.0.1.0/24 and 10.0.2.0/24:
    every address in the subnet must match the statement's wildcard.
    """
    try:
        net = ipaddress.IPv4Network(subnet, strict=False)
    except (ipaddress.AddressValueError, ValueError):
        return False
    network = statement.get("network", "")
    wildcard = statement.get("wildcard", "")
    if not _wildcard_contains(network, wildcard, str(net.network_address)):
        return False
    if not _wildcard_contains(network, wildcard, str(net.broadcast_address)):
        return False
    # A wildcard can be non-contiguous, so the two ends matching is not proof
    # on its own: every host bit of the subnet must be a "don't care" bit.
    host_bits = int(net.hostmask)
    wild = int(ipaddress.IPv4Address(wildcard))
    return (host_bits & ~wild) == 0


def interface_subnet(intf) -> str | None:
    """The connected subnet of an interface as CIDR text, or None."""
    if not intf.ip_address or intf.cidr is None:
        return None
    try:
        return str(ipaddress.IPv4Interface(f"{intf.ip_address}/{intf.cidr}").network)
    except (ipaddress.AddressValueError, ValueError):
        return None


def ospf_enablements(device: ParsedDevice) -> list[dict]:
    """Every interface OSPF runs on, as {process_id, interface, area, subnet}.

    Interface-mode `ip ospf P area A` wins over `network` statements, as on
    IOS. Among network statements the most specific one matching the
    interface's primary address decides the area.
    """
    statements = []
    for proc in device.ospf_processes:
        for n in proc.get("networks", []):
            if isinstance(n, dict) and n.get("area") is not None:
                statements.append((proc.get("process_id"), n))
    statements.sort(key=lambda item: _wildcard_bits(item[1].get("wildcard", "")))

    found = []
    for name, intf in device.interfaces.items():
        if not intf.ip_address:
            continue
        if intf.ospf_area is not None:
            found.append({
                "process_id": intf.ospf_process_id,
                "interface": name,
                "area": intf.ospf_area,
                "subnet": interface_subnet(intf),
            })
            continue
        for pid, statement in statements:
            if _wildcard_contains(statement.get("network", ""), statement.get("wildcard", ""),
                                  intf.ip_address):
                found.append({
                    "process_id": pid,
                    "interface": name,
                    "area": statement["area"],
                    "subnet": interface_subnet(intf),
                })
                break
    return found


def ospf_areas(device: ParsedDevice) -> set[int]:
    """Areas this device runs OSPF in, from either configuration style."""
    areas = {e["area"] for e in ospf_enablements(device)}
    # A network statement no interface matches still names an area the
    # instructor configured; keep it so the rubric doesn't silently drop it.
    for proc in device.ospf_processes:
        for n in proc.get("networks", []):
            if isinstance(n, dict) and n.get("area") is not None:
                areas.add(n["area"])
    return areas
