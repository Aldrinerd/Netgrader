# src/parsers.py
import ipaddress
import os
import re
from src.models import (
    CDPNeighbor,
    InterfaceData,
    MACTableEntry,
    ParsedDevice,
    RouteEntry,
)
from src.sanitizer import split_command_sections

def canonical_device_name(name: str) -> str:
    """Extracts short host name from FQDN (e.g. R2.cisco.lab -> R2)."""
    if not name:
        return ""
    clean = name.strip()
    return clean.split(".")[0]

def normalize_interface_name(name: str) -> str:
    """Normalizes interface abbreviations (e.g. Gi0/0 -> GigabitEthernet0/0, Fa0/1 -> FastEthernet0/1)."""
    if not name:
        return ""
    clean = name.strip()
    # Match patterns like Gi0/0, Fa0/1, Se0/1/0, Lo0, Vlan10, Port-channel1
    sub_map = [
        (r"^Gi(?:gabitEthernet)?", "GigabitEthernet"),
        (r"^Fa(?:stEthernet)?", "FastEthernet"),
        (r"^Eth(?:ernet)?", "Ethernet"),
        (r"^Se(?:rial)?", "Serial"),
        (r"^Lo(?:opback)?", "Loopback"),
        (r"^Vl(?:an)?", "Vlan"),
        (r"^Po(?:rt-channel)?", "Port-channel"),
        (r"^Tu(?:nnel)?", "Tunnel"),
    ]
    for pattern, replacement in sub_map:
        if re.match(pattern, clean, re.IGNORECASE):
            return re.sub(pattern, replacement, clean, flags=re.IGNORECASE)
    return clean

def ip_and_mask_to_network(ip_str: str, mask_str: str) -> tuple[str, int, str]:
    """Given IP and subnet mask, returns (ip, cidr, network_address)."""
    try:
        interface_obj = ipaddress.IPv4Interface(f"{ip_str}/{mask_str}")
        return ip_str, interface_obj.network.prefixlen, str(interface_obj.network.network_address)
    except Exception:
        return ip_str, 24, ip_str

def parse_running_config(content: str, start_line: int, device: ParsedDevice) -> None:
    lines = content.splitlines()
    current_intf: InterfaceData | None = None
    
    for idx, line in enumerate(lines):
        line_no = start_line + idx
        stripped = line.strip()
        
        # Hostname
        host_match = re.match(r"^hostname\s+([a-zA-Z0-9_\-\.]+)", stripped, re.IGNORECASE)
        if host_match:
            device.hostname = host_match.group(1).strip()
            device.canonical_name = canonical_device_name(device.hostname)
            continue
        
        # Interface block start
        intf_match = re.match(r"^interface\s+([a-zA-Z0-9_\-\./]+)", stripped, re.IGNORECASE)
        if intf_match:
            raw_intf_name = intf_match.group(1).strip()
            norm_intf_name = normalize_interface_name(raw_intf_name)
            if norm_intf_name not in device.interfaces:
                device.interfaces[norm_intf_name] = InterfaceData(name=norm_intf_name)
            current_intf = device.interfaces[norm_intf_name]
            current_intf.evidence_lines["interface"] = line_no
            continue
        
        # Exit interface block on ! or other root commands
        if not line.startswith(" ") and not line.startswith("\t") and stripped.startswith("!"):
            current_intf = None
            continue
        
        # Inside interface block
        if current_intf is not None:
            # IP Address
            ip_match = re.match(r"^ip\s+address\s+([0-9\.]+)\s+([0-9\.]+)", stripped, re.IGNORECASE)
            if ip_match:
                ip, mask = ip_match.group(1), ip_match.group(2)
                ip_addr, cidr, net_addr = ip_and_mask_to_network(ip, mask)
                current_intf.ip_address = ip_addr
                current_intf.subnet_mask = mask
                current_intf.cidr = cidr
                current_intf.network_address = net_addr
                current_intf.evidence_lines["ip"] = line_no
                continue
            
            # Description
            desc_match = re.match(r"^description\s+(.+)$", stripped, re.IGNORECASE)
            if desc_match:
                current_intf.description = desc_match.group(1).strip()
                current_intf.evidence_lines["description"] = line_no
                continue
            
            # Switchport mode
            if "switchport mode trunk" in stripped.lower():
                current_intf.is_switchport = True
                current_intf.switchport_mode = "trunk"
                device.device_type = "switch"
                current_intf.evidence_lines["switchport_mode"] = line_no
                continue
            elif "switchport mode access" in stripped.lower():
                current_intf.is_switchport = True
                current_intf.switchport_mode = "access"
                device.device_type = "switch"
                current_intf.evidence_lines["switchport_mode"] = line_no
                continue
            elif "switchport" in stripped.lower():
                current_intf.is_switchport = True
                device.device_type = "switch"
            
            # Access VLAN
            access_match = re.match(r"^switchport\s+access\s+vlan\s+(\d+)", stripped, re.IGNORECASE)
            if access_match:
                current_intf.access_vlan = int(access_match.group(1))
                current_intf.evidence_lines["access_vlan"] = line_no
                continue
            
            # Trunk Native VLAN
            native_match = re.match(r"^switchport\s+trunk\s+native\s+vlan\s+(\d+)", stripped, re.IGNORECASE)
            if native_match:
                current_intf.trunk_native_vlan = int(native_match.group(1))
                current_intf.evidence_lines["trunk_native_vlan"] = line_no
                continue
            
            # Trunk Allowed VLANs
            allowed_match = re.match(r"^switchport\s+trunk\s+allowed\s+vlan\s+(?:add\s+)?([0-9,\-\s]+)", stripped, re.IGNORECASE)
            if allowed_match:
                vlans_raw = allowed_match.group(1)
                vlans = []
                for part in vlans_raw.split(","):
                    part = part.strip()
                    if "-" in part:
                        try:
                            start_v, end_v = part.split("-")
                            vlans.extend(range(int(start_v), int(end_v) + 1))
                        except Exception:
                            pass
                    elif part.isdigit():
                        vlans.append(int(part))
                current_intf.trunk_allowed_vlans = list(sorted(set(current_intf.trunk_allowed_vlans + vlans)))
                current_intf.evidence_lines["trunk_allowed_vlans"] = line_no
                continue
            
            # Shutdown / No shutdown in config
            if re.match(r"^shutdown", stripped, re.IGNORECASE):
                current_intf.admin_status = "administratively down"
                current_intf.line_status = "down"
                current_intf.evidence_lines["admin_status"] = line_no

def parse_cdp_detail(content: str, start_line: int, device: ParsedDevice) -> None:
    # Split into neighbor blocks (typically separated by ------------------------- or Device ID:)
    blocks = re.split(r"-{10,}|(?=Device ID:)", content)
    
    for block in blocks:
        if not block.strip() or "Device ID:" not in block:
            continue
        
        dev_id_match = re.search(r"Device ID:\s*([^\r\n]+)", block, re.IGNORECASE)
        if not dev_id_match:
            continue
        
        raw_dev_id = dev_id_match.group(1).strip()
        canon_dev_id = canonical_device_name(raw_dev_id)
        
        local_intf_match = re.search(r"Interface:\s*([^,\r\n]+)", block, re.IGNORECASE)
        remote_intf_match = re.search(r"Port ID\s*(?:\(outgoing port\))?:\s*([^\r\n,]+)", block, re.IGNORECASE)
        remote_ip_match = re.search(r"IP address:\s*([0-9\.]+)", block, re.IGNORECASE)
        platform_match = re.search(r"Platform:\s*([^,\r\n]+)", block, re.IGNORECASE)
        capabilities_match = re.search(r"Capabilities:\s*([^\r\n]+)", block, re.IGNORECASE)
        
        local_intf = normalize_interface_name(local_intf_match.group(1)) if local_intf_match else ""
        remote_intf = normalize_interface_name(remote_intf_match.group(1)) if remote_intf_match else ""
        remote_ip = remote_ip_match.group(1).strip() if remote_ip_match else None
        platform = platform_match.group(1).strip() if platform_match else None
        
        caps = []
        if capabilities_match:
            caps = [c.strip() for c in capabilities_match.group(1).split() if c.strip()]
        
        cdp_entry = CDPNeighbor(
            device_id=canon_dev_id,
            local_interface=local_intf,
            remote_interface=remote_intf,
            capabilities=caps,
            remote_ip=remote_ip,
            platform=platform,
            evidence_line=start_line
        )
        device.cdp_neighbors.append(cdp_entry)

def parse_ip_int_brief(content: str, start_line: int, device: ParsedDevice) -> None:
    lines = content.splitlines()
    for idx, line in enumerate(lines):
        line_no = start_line + idx
        stripped = line.strip()
        if not stripped or stripped.lower().startswith("interface") or stripped.startswith("---"):
            continue
        
        parts = stripped.split()
        if len(parts) >= 5:
            raw_intf = parts[0]
            norm_intf = normalize_interface_name(raw_intf)
            ip_val = parts[1]
            
            # Status and Protocol usually last 2 columns
            status_val = parts[-2]
            protocol_val = parts[-1]
            # Handle "administratively down" which occupies two words
            if "administratively" in stripped.lower():
                status_val = "administratively down"
                protocol_val = "down"
            
            if norm_intf not in device.interfaces:
                device.interfaces[norm_intf] = InterfaceData(name=norm_intf)
            
            intf_obj = device.interfaces[norm_intf]
            intf_obj.admin_status = status_val.lower()
            intf_obj.line_status = protocol_val.lower()
            intf_obj.evidence_lines["status_protocol"] = line_no
            
            if ip_val.lower() not in ["unassigned", "unset"] and re.match(r"^\d+\.\d+\.\d+\.\d+$", ip_val):
                if not intf_obj.ip_address:
                    intf_obj.ip_address = ip_val
                    intf_obj.evidence_lines["ip_brief"] = line_no

def parse_ip_route(content: str, start_line: int, device: ParsedDevice) -> None:
    lines = content.splitlines()
    for idx, line in enumerate(lines):
        line_no = start_line + idx
        stripped = line.strip()
        if not stripped or stripped.startswith("Gateway") or stripped.startswith("Codes:"):
            continue
        
        # Route entry matching:
        # C 10.0.0.0/30 is directly connected, GigabitEthernet0/0
        # O 10.0.0.4/30 [110/2] via 10.0.0.2, 00:05:12, GigabitEthernet0/0
        # S 172.16.0.0/16 [1/0] via 10.0.0.2
        route_match = re.match(r"^([A-Z\*]+)\s+([0-9\.]+)(?:/(\d+))?(?:\s+\[(\d+)/(\d+)\])?(?:\s+via\s+([0-9\.]+))?(?:.*,\s*([a-zA-Z0-9_\./]+))?", stripped)
        if route_match:
            proto = route_match.group(1).strip()
            net = route_match.group(2).strip()
            cidr_str = route_match.group(3)
            cidr = int(cidr_str) if cidr_str else 24
            next_hop = route_match.group(6)
            out_intf = normalize_interface_name(route_match.group(7)) if route_match.group(7) else None
            
            device.routes.append(RouteEntry(
                network=net,
                cidr=cidr,
                protocol=proto,
                next_hop=next_hop,
                outgoing_interface=out_intf,
                evidence_line=line_no
            ))

def parse_vlan_brief(content: str, start_line: int, device: ParsedDevice) -> None:
    device.device_type = "switch"
    lines = content.splitlines()
    for idx, line in enumerate(lines):
        line_no = start_line + idx
        stripped = line.strip()
        if not stripped or stripped.lower().startswith("vlan") or stripped.startswith("----"):
            continue
        
        vlan_match = re.match(r"^(\d+)\s+([a-zA-Z0-9_\-]+)\s+([a-zA-Z]+)", stripped)
        if vlan_match:
            vlan_id = int(vlan_match.group(1))
            vlan_name = vlan_match.group(2).strip()
            device.vlans[vlan_id] = vlan_name

def parse_interfaces_trunk(content: str, start_line: int, device: ParsedDevice) -> None:
    device.device_type = "switch"
    lines = content.splitlines()
    for idx, line in enumerate(lines):
        line_no = start_line + idx
        stripped = line.strip()
        if not stripped or stripped.lower().startswith("port") or stripped.startswith("----"):
            continue
        
        # Trunk status line: Fa0/1 on 802.1q trunking 99
        trunk_match = re.match(r"^([a-zA-Z0-9_\./]+)\s+([a-zA-Z0-9]+)\s+([a-zA-Z0-9\.]+)\s+trunking\s+(\d+)", stripped, re.IGNORECASE)
        if trunk_match:
            port = normalize_interface_name(trunk_match.group(1))
            native_vlan = int(trunk_match.group(4))
            if port not in device.interfaces:
                device.interfaces[port] = InterfaceData(name=port)
            device.interfaces[port].is_switchport = True
            device.interfaces[port].switchport_mode = "trunk"
            device.interfaces[port].trunk_native_vlan = native_vlan
            device.interfaces[port].evidence_lines["trunk_status"] = line_no

def parse_mac_table(content: str, start_line: int, device: ParsedDevice) -> None:
    lines = content.splitlines()
    for idx, line in enumerate(lines):
        line_no = start_line + idx
        stripped = line.strip()
        if not stripped or stripped.lower().startswith("vlan") or stripped.startswith("----") or "Mac Address Table" in stripped:
            continue
        
        # 10 0050.7966.6801 DYNAMIC Fa0/2
        mac_match = re.match(r"^(\d+)\s+([0-9a-fA-F\.\:]+)\s+([a-zA-Z]+)\s+([a-zA-Z0-9_\./]+)", stripped)
        if mac_match:
            vlan = int(mac_match.group(1))
            mac_addr = mac_match.group(2).strip()
            entry_type = mac_match.group(3).strip().upper()
            port = normalize_interface_name(mac_match.group(4).strip())
            
            device.mac_table.append(MACTableEntry(
                vlan=vlan,
                mac_address=mac_addr,
                entry_type=entry_type,
                port=port,
                evidence_line=line_no
            ))

def parse_device_bundle(raw_text: str, filename: str) -> ParsedDevice:
    """Ingests raw multi-command output and produces a structured ParsedDevice object."""
    base_name = os.path.basename(filename).rsplit(".", 1)[0]
    device = ParsedDevice(
        hostname=base_name,
        canonical_name=canonical_device_name(base_name),
        raw_filename=filename
    )
    
    sections = split_command_sections(raw_text)
    
    # 1. Parse running-config first to establish hostname and base interfaces
    if "show running-config" in sections:
        content, start_line = sections["show running-config"]
        parse_running_config(content, start_line, device)
    
    # 2. Parse CDP
    if "show cdp neighbors detail" in sections:
        content, start_line = sections["show cdp neighbors detail"]
        parse_cdp_detail(content, start_line, device)
    
    # 3. Parse IP Int Brief
    if "show ip interface brief" in sections:
        content, start_line = sections["show ip interface brief"]
        parse_ip_int_brief(content, start_line, device)
        
    # 4. Parse IP Route
    if "show ip route" in sections:
        content, start_line = sections["show ip route"]
        parse_ip_route(content, start_line, device)
        
    # 5. Parse VLAN brief
    if "show vlan brief" in sections:
        content, start_line = sections["show vlan brief"]
        parse_vlan_brief(content, start_line, device)
        
    # 6. Parse Interfaces Trunk
    if "show interfaces trunk" in sections:
        content, start_line = sections["show interfaces trunk"]
        parse_interfaces_trunk(content, start_line, device)
        
    # 7. Parse MAC Address Table
    if "show mac address-table" in sections:
        content, start_line = sections["show mac address-table"]
        parse_mac_table(content, start_line, device)
        
    return device
