# src/conflict_detector.py
import ipaddress
from src.models import (
    ConflictIssue,
    DiscoveredLink,
    ParsedDevice,
)

def detect_conflicts(devices: dict[str, ParsedDevice], links: list[DiscoveredLink]) -> list[ConflictIssue]:
    """
    Scans parsed devices and discovered topology links for cross-device
    relational inconsistencies, cabling errors, and configuration flaws.
    """
    conflicts: list[ConflictIssue] = []

    # 1. Check Subnet Mismatches on Physically Connected Links
    for link in links:
        has_cdp = any(s.signal_type == "CDP_NEIGHBOR_DETAIL" for s in link.signals)
        dev_a = devices.get(link.source_device)
        dev_b = devices.get(link.target_device)
        
        if dev_a and dev_b and link.source_interface != "Unspecified" and link.target_interface != "Unspecified":
            intf_a = dev_a.interfaces.get(link.source_interface)
            intf_b = dev_b.interfaces.get(link.target_interface)
            
            if intf_a and intf_b and intf_a.ip_address and intf_b.ip_address:
                # If physical link is confirmed via CDP, but subnets don't match
                if has_cdp and (intf_a.network_address != intf_b.network_address or intf_a.cidr != intf_b.cidr):
                    link.conflicts.append(f"Subnet Mismatch: {dev_a.hostname}:{intf_a.name} ({intf_a.ip_address}/{intf_a.cidr}) vs {dev_b.hostname}:{intf_b.name} ({intf_b.ip_address}/{intf_b.cidr})")
                    
                    line_a = intf_a.evidence_lines.get("ip", intf_a.evidence_lines.get("interface", 1))
                    line_b = intf_b.evidence_lines.get("ip", intf_b.evidence_lines.get("interface", 1))
                    
                    conflicts.append(ConflictIssue(
                        severity="error",
                        category="subnet_mismatch",
                        title=f"IP Subnet Mismatch across {dev_a.hostname} <-> {dev_b.hostname}",
                        description=f"Physical link confirmed via CDP, but {dev_a.hostname} ({intf_a.name}: {intf_a.ip_address}/{intf_a.cidr}) and {dev_b.hostname} ({intf_b.name}: {intf_b.ip_address}/{intf_b.cidr}) belong to different network subnets.",
                        involved_devices=[dev_a.hostname, dev_b.hostname],
                        involved_interfaces=[intf_a.name, intf_b.name],
                        evidence_citations=[
                            f"{dev_a.raw_filename}: line {line_a} ({intf_a.name} ip address {intf_a.ip_address})",
                            f"{dev_b.raw_filename}: line {line_b} ({intf_b.name} ip address {intf_b.ip_address})"
                        ]
                    ))

    # 2. Check Interface Down / Cabling / Admin Down Errors
    for dev in devices.values():
        for intf_name, intf in dev.interfaces.items():
            if intf.ip_address:
                if intf.admin_status == "administratively down" or intf.line_status == "down":
                    line_no = intf.evidence_lines.get("admin_status", intf.evidence_lines.get("status_protocol", intf.evidence_lines.get("interface", 1)))
                    is_admin_down = "administratively down" in intf.admin_status
                    reason = "missing 'no shutdown' (administratively down)" if is_admin_down else "link protocol is down (cabling or peer disconnect)"
                    
                    conflicts.append(ConflictIssue(
                        severity="error" if is_admin_down else "warning",
                        category="interface_down",
                        title=f"Interface Inactive on {dev.hostname} ({intf_name})",
                        description=f"Interface {intf_name} has IP address {intf_a.ip_address if 'intf_a' in locals() and intf_a else intf.ip_address} configured, but status is {intf.admin_status}/{intf.line_status} due to {reason}.",
                        involved_devices=[dev.hostname],
                        involved_interfaces=[intf_name],
                        evidence_citations=[f"{dev.raw_filename}: line {line_no} ({intf_name} is {intf.admin_status})"]
                    ))

    # 3. Check Duplicate IP Allocations Across All Devices
    ip_registry: dict[str, list[tuple[str, str, str, int]]] = {}  # ip -> [(device, intf, filename, line)]
    for dev in devices.values():
        for intf_name, intf in dev.interfaces.items():
            if intf.ip_address and intf.ip_address not in ("0.0.0.0", "127.0.0.1"):
                line_no = intf.evidence_lines.get("ip", 1)
                if intf.ip_address not in ip_registry:
                    ip_registry[intf.ip_address] = []
                ip_registry[intf.ip_address].append((dev.hostname, intf_name, dev.raw_filename, line_no))

    for ip_addr, occurrences in ip_registry.items():
        if len(occurrences) > 1:
            dev_names = [occ[0] for occ in occurrences]
            intf_names = [occ[1] for occ in occurrences]
            citations = [f"{occ[2]}: line {occ[3]} ({occ[0]}:{occ[1]} ip address {ip_addr})" for occ in occurrences]
            
            conflicts.append(ConflictIssue(
                severity="error",
                category="duplicate_ip",
                title=f"Duplicate IP Address Detected ({ip_addr})",
                description=f"The IP address {ip_addr} is configured on multiple distinct interfaces ({', '.join(f'{d}:{i}' for d, i, _, _ in occurrences)}), causing ARP collisions.",
                involved_devices=list(set(dev_names)),
                involved_interfaces=intf_names,
                evidence_citations=citations
            ))

    # 4. Check VLAN Trunk Mismatches on Switch Links
    for link in links:
        dev_a = devices.get(link.source_device)
        dev_b = devices.get(link.target_device)
        if dev_a and dev_b and dev_a.device_type == "switch" and dev_b.device_type == "switch":
            intf_a = dev_a.interfaces.get(link.source_interface)
            intf_b = dev_b.interfaces.get(link.target_interface)
            if intf_a and intf_b and intf_a.switchport_mode == "trunk" and intf_b.switchport_mode == "trunk":
                if intf_a.trunk_native_vlan != intf_b.trunk_native_vlan:
                    line_a = intf_a.evidence_lines.get("trunk_native_vlan", intf_a.evidence_lines.get("switchport_mode", 1))
                    line_b = intf_b.evidence_lines.get("trunk_native_vlan", intf_b.evidence_lines.get("switchport_mode", 1))
                    link.conflicts.append(f"Native VLAN Mismatch: {dev_a.hostname}:{intf_a.name} (VLAN {intf_a.trunk_native_vlan}) vs {dev_b.hostname}:{intf_b.name} (VLAN {intf_b.trunk_native_vlan})")
                    
                    conflicts.append(ConflictIssue(
                        severity="error",
                        category="vlan_trunk_mismatch",
                        title=f"Trunk Native VLAN Mismatch on {dev_a.hostname} <-> {dev_b.hostname}",
                        description=f"Connected trunk ports have mismatched native VLANs ({dev_a.hostname}:{intf_a.name} native {intf_a.trunk_native_vlan} vs {dev_b.hostname}:{intf_b.name} native {intf_b.trunk_native_vlan}), creating a VLAN hopping / bridging loop risk.",
                        involved_devices=[dev_a.hostname, dev_b.hostname],
                        involved_interfaces=[intf_a.name, intf_b.name],
                        evidence_citations=[
                            f"{dev_a.raw_filename}: line {line_a} ({intf_a.name} native vlan {intf_a.trunk_native_vlan})",
                            f"{dev_b.raw_filename}: line {line_b} ({intf_b.name} native vlan {intf_b.trunk_native_vlan})"
                        ]
                    ))

    return conflicts
