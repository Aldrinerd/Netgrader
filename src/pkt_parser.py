# src/pkt_parser.py
import os
import re
import sys
import xml.etree.ElementTree as ET
from typing import Tuple

# Add vendor / cisco-pka-to-xml to sys.path if not present
PKA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cisco-pka-to-xml")
if PKA_DIR not in sys.path:
    sys.path.insert(0, PKA_DIR)

try:
    from pka2xml import decrypt_pka, PkaError
except ImportError:
    decrypt_pka = None
    PkaError = Exception

from src.models import (
    ContributingSignal,
    DiscoveredLink,
    InterfaceData,
    ParsedDevice,
)
from src.parsers import (
    canonical_device_name,
    ip_and_mask_to_network,
    normalize_interface_name,
    parse_running_config,
)

def parse_pkt_file(raw_bytes: bytes, filename: str = "topology.pkt") -> Tuple[dict[str, ParsedDevice], list[DiscoveredLink]]:
    """Decrypts a .pkt/.pka binary file or decodes XML, then parses devices and links."""
    if not raw_bytes:
        return {}, []

    # If already XML text
    stripped = raw_bytes.lstrip()
    if stripped.startswith(b"<"):
        return parse_pkt_xml(raw_bytes, filename=filename)

    # Attempt decryption via pka2xml
    if decrypt_pka is None:
        raise RuntimeError("pka2xml is not available to decrypt .pkt/.pka files.")

    try:
        xml_bytes = decrypt_pka(raw_bytes)
    except Exception as e:
        raise ValueError(f"Failed to decrypt Packet Tracer file '{filename}': {e}") from e

    return parse_pkt_xml(xml_bytes, filename=filename)

def parse_pkt_xml(xml_content: str | bytes, filename: str = "topology.xml") -> Tuple[dict[str, ParsedDevice], list[DiscoveredLink]]:
    """Parses a Packet Tracer XML string or bytes into ParsedDevice and DiscoveredLink collections."""
    if isinstance(xml_content, str):
        xml_bytes = xml_content.encode("utf-8", errors="replace")
    else:
        xml_bytes = xml_content

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise ValueError(f"Malformed Packet Tracer XML in '{filename}': {e}") from e

    # Find NETWORK node
    net_node = root.find(".//NETWORK")
    if net_node is None:
        if root.tag == "NETWORK":
            net_node = root
        else:
            return {}, []

    devices_dict: dict[str, ParsedDevice] = {}
    ref_to_dev: dict[str, str] = {}  # save_ref_id -> hostname

    devices_node = net_node.find("DEVICES")
    if devices_node is not None:
        for dev_elem in devices_node.findall("DEVICE"):
            engine = dev_elem.find("ENGINE")
            if engine is None:
                continue

            name_elem = engine.find("NAME")
            raw_name = name_elem.text.strip() if (name_elem is not None and name_elem.text) else "Unknown"
            
            type_elem = engine.find("TYPE")
            type_str = type_elem.text.strip() if (type_elem is not None and type_elem.text) else ""
            model_attr = type_elem.attrib.get("model", "") if type_elem is not None else ""

            # Coordinates from <WORKSPACE><LOGICAL><X> and <Y>
            x_coord = None
            y_coord = None
            log_elem = dev_elem.find(".//LOGICAL")
            if log_elem is not None:
                try:
                    x_txt = log_elem.find("X")
                    y_txt = log_elem.find("Y")
                    if x_txt is not None and x_txt.text:
                        x_coord = float(x_txt.text)
                    if y_txt is not None and y_txt.text:
                        y_coord = float(y_txt.text)
                except Exception:
                    pass

            # Fallback to COORD_SETTINGS if LOGICAL was not found
            if x_coord is None or y_coord is None:
                coord_elem = dev_elem.find(".//COORD_SETTINGS")
                if coord_elem is not None:
                    try:
                        x_txt = coord_elem.find("X_COORD")
                        y_txt = coord_elem.find("Y_COORD")
                        if x_txt is not None and x_txt.text:
                            x_coord = float(x_txt.text)
                        if y_txt is not None and y_txt.text:
                            y_coord = float(y_txt.text)
                    except Exception:
                        pass


            # Reference ID for links
            ref_elem = dev_elem.find(".//SAVE_REF_ID")
            ref_id = ref_elem.text.strip() if (ref_elem is not None and ref_elem.text) else None
            if ref_id:
                ref_to_dev[ref_id] = raw_name

            # Determine device role
            type_lower = type_str.lower()
            model_lower = model_attr.lower()
            if "router" in type_lower or "router" in model_lower:
                device_type = "router"
            elif "switch" in type_lower or "2960" in model_lower or "switch" in model_lower:
                device_type = "switch"
            elif any(k in type_lower for k in ["pc", "laptop", "server", "host", "workstation"]):
                device_type = "host"
            elif "power" in type_lower:
                continue  # Ignore power distribution strips
            else:
                device_type = "unknown"

            device = ParsedDevice(
                hostname=raw_name,
                canonical_name=canonical_device_name(raw_name),
                display_name=raw_name,
                device_type=device_type,
                raw_filename=filename,
                x_coord=x_coord,
                y_coord=y_coord
            )

            # 1. Parse Cisco IOS Running Config (Routers/Switches)
            rc_elem = dev_elem.find(".//RUNNINGCONFIG")
            if rc_elem is None:
                rc_elem = dev_elem.find(".//RUNNING_CONFIG")

            if rc_elem is not None and len(rc_elem) > 0:
                lines = [c.text for c in rc_elem if c.text is not None]
                if lines:
                    config_str = "\n".join(lines)
                    # Parse into a temporary object or preserve raw_name as hostname
                    parse_running_config(config_str, start_line=1, device=device)
                    # Keep Packet Tracer name as primary hostname/display_name if default/different
                    device.display_name = raw_name
                    device.hostname = raw_name
                    device.canonical_name = canonical_device_name(raw_name)
            
            # 2. Parse Host / PC / Laptop IP & Interface settings
            if device_type == "host":
                for port_elem in dev_elem.findall(".//PORT"):
                    ptype_elem = port_elem.find("TYPE")
                    ptype = ptype_elem.text.strip() if (ptype_elem is not None and ptype_elem.text) else "FastEthernet0"
                    
                    # Convert eCopperFastEthernet -> FastEthernet0
                    port_name = "FastEthernet0"
                    if "gigabit" in ptype.lower():
                        port_name = "GigabitEthernet0"
                    elif "bluetooth" in ptype.lower():
                        continue

                    ip_elem = port_elem.find("IP")
                    sub_elem = port_elem.find("SUBNET")
                    gw_elem = port_elem.find("PORT_GATEWAY")
                    
                    ip_val = ip_elem.text.strip() if (ip_elem is not None and ip_elem.text) else None
                    sub_val = sub_elem.text.strip() if (sub_elem is not None and sub_elem.text) else None
                    gw_val = gw_elem.text.strip() if (gw_elem is not None and gw_elem.text) else None

                    intf = InterfaceData(name=port_name)
                    if ip_val and sub_val:
                        ip, cidr, net_addr = ip_and_mask_to_network(ip_val, sub_val)
                        intf.ip_address = ip
                        intf.subnet_mask = sub_val
                        intf.cidr = cidr
                        intf.network_address = net_addr
                    
                    device.interfaces[port_name] = intf

            devices_dict[raw_name] = device


    # 3. Parse Links
    discovered_links: list[DiscoveredLink] = []
    links_node = net_node.find("LINKS")
    if links_node is not None:
        for link_elem in links_node.findall("LINK"):
            cable_elem = link_elem.find("CABLE")
            if cable_elem is None:
                continue

            from_ref_elem = cable_elem.find("FROM")
            to_ref_elem = cable_elem.find("TO")
            if from_ref_elem is None or to_ref_elem is None:
                continue

            from_ref = from_ref_elem.text.strip() if from_ref_elem.text else ""
            to_ref = to_ref_elem.text.strip() if to_ref_elem.text else ""

            src_dev = ref_to_dev.get(from_ref)
            tgt_dev = ref_to_dev.get(to_ref)
            if not src_dev or not tgt_dev:
                continue

            # Ports
            port_elems = cable_elem.findall("PORT")
            src_port = port_elems[0].text.strip() if len(port_elems) > 0 and port_elems[0].text else "Unspecified"
            tgt_port = port_elems[1].text.strip() if len(port_elems) > 1 and port_elems[1].text else "Unspecified"

            # Cable Type
            ctype_elem = cable_elem.find("TYPE")
            cable_type = ctype_elem.text.strip() if (ctype_elem is not None and ctype_elem.text) else None

            norm_src_port = normalize_interface_name(src_port)
            norm_tgt_port = normalize_interface_name(tgt_port)

            link = DiscoveredLink(
                source_device=src_dev,
                source_interface=norm_src_port,
                target_device=tgt_dev,
                target_interface=norm_tgt_port,
                confidence=1.00,
                classification="verified",
                cable_type=cable_type,
                signals=[
                    ContributingSignal(
                        signal_type="PACKET_TRACER_PHYSICAL_CABLE",
                        description=f"Physical cable ({cable_type or 'Standard'}) in Packet Tracer",
                        weight=1.00,
                        evidence=[f"{src_dev}:{norm_src_port} <--> {tgt_dev}:{norm_tgt_port}"]
                    )
                ]
            )
            discovered_links.append(link)

    return devices_dict, discovered_links
