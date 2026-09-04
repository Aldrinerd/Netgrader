# src/fusion_engine.py
import re
from typing import Literal
from src.models import (
    ContributingSignal,
    DiscoveredLink,
    ParsedDevice,
)

SIGNAL_WEIGHTS: dict[str, float] = {
    "CDP_NEIGHBOR_DETAIL": 1.00,
    "OSPF_NEIGHBOR_FULL": 0.95,
    "P2P_SUBNET_30_31": 0.90,
    "ROUTER_ON_A_STICK_VLAN": 0.85,
    "TRUNK_CONFIG_PAIR": 0.80,
    "NEXT_HOP_ROUTING_MATCH": 0.75,
    "MAC_TABLE_UPLINK": 0.70,
    "SHARED_SUBNET_24": 0.35,
    "DESCRIPTION_HINT": 0.25,
    "ACTIVE_PORT_CARRIER": 0.50,
}

def calculate_noisy_or(weights: list[float]) -> float:
    """Calculates combined probability using Noisy-OR formula: P = 1 - product(1 - w_i)."""
    if not weights:
        return 0.0
    prod = 1.0
    for w in weights:
        clamped_w = min(w, 0.9999)
        prod *= (1.0 - clamped_w)
    confidence = 1.0 - prod
    return max(0.0, min(1.0, confidence))

def classify_confidence(confidence: float) -> Literal["verified", "inferred", "unverified"]:
    if confidence >= 0.80:
        return "verified"
    elif confidence >= 0.40:
        return "inferred"
    return "unverified"

def normalize_edge_key(dev_a: str, intf_a: str, dev_b: str, intf_b: str) -> tuple[str, str, str, str]:
    """Returns canonical ordering for an undirected edge."""
    pair1 = (dev_a, intf_a)
    pair2 = (dev_b, intf_b)
    if pair1 <= pair2:
        return dev_a, intf_a, dev_b, intf_b
    else:
        return dev_b, intf_b, dev_a, intf_a

def infer_topology_links(devices: dict[str, ParsedDevice]) -> list[DiscoveredLink]:
    """
    Evaluates multi-signal evidence across all parsed devices and generates
    fused, deduplicated network graph edges with Noisy-OR confidence ratings.
    """
    candidate_edges: dict[tuple[str, str, str, str], dict] = {}

    def add_signal(d1: str, i1: str, d2: str, i2: str, sig_type: str, desc: str, evidence: list[str]):
        src_dev, src_intf, tgt_dev, tgt_intf = normalize_edge_key(d1, i1, d2, i2)
        key = (src_dev, src_intf, tgt_dev, tgt_intf)
        if key not in candidate_edges:
            candidate_edges[key] = {
                "source_device": src_dev,
                "source_interface": src_intf,
                "target_device": tgt_dev,
                "target_interface": tgt_intf,
                "signals": {},
                "bidirectional_checks": set(),
            }
        
        weight = SIGNAL_WEIGHTS.get(sig_type, 0.5)
        if sig_type not in candidate_edges[key]["signals"]:
            candidate_edges[key]["signals"][sig_type] = ContributingSignal(
                signal_type=sig_type,
                description=desc,
                weight=weight,
                evidence=evidence
            )
        else:
            candidate_edges[key]["signals"][sig_type].evidence.extend(evidence)
        
        candidate_edges[key]["bidirectional_checks"].add(d1)

    device_list = list(devices.values())

    # --- Signal 1: CDP Neighbors Detail (Authoritative Layer 2/Physical) ---
    for dev in device_list:
        for cdp in dev.cdp_neighbors:
            target_dev = devices.get(cdp.device_id)
            if not target_dev and "." in cdp.device_id:
                target_dev = devices.get(cdp.device_id.split(".")[0])
            
            if target_dev:
                target_hostname = target_dev.hostname
            else:
                placeholder_id = f"UNKNOWN_PEER_{dev.hostname}_{cdp.local_interface}"
                if placeholder_id not in devices:
                    devices[placeholder_id] = ParsedDevice(
                        hostname="???",
                        canonical_name=placeholder_id,
                        display_name="???",
                        is_placeholder=True,
                        placeholder_for_device=cdp.device_id,
                        placeholder_for_interface=cdp.local_interface,
                        device_type="unknown",
                        raw_filename=""
                    )
                target_hostname = placeholder_id
            
            ev = [f"{dev.raw_filename} (CDP Neighbor to {cdp.device_id} on {cdp.local_interface})"]
            add_signal(
                dev.hostname,
                cdp.local_interface,
                target_hostname,
                cdp.remote_interface,
                "CDP_NEIGHBOR_DETAIL",
                f"Direct CDP neighbor advertisement on {cdp.local_interface} <-> {cdp.remote_interface}",
                ev
            )

    # --- Signal 2 & 3: IP Subnet Co-membership (P2P /30-/31 vs Shared /24) ---
    for i in range(len(device_list)):
        for j in range(i + 1, len(device_list)):
            dev_a = device_list[i]
            dev_b = device_list[j]
            
            for intf_a_name, intf_a in dev_a.interfaces.items():
                if not intf_a.ip_address or not intf_a.network_address:
                    continue
                for intf_b_name, intf_b in dev_b.interfaces.items():
                    if not intf_b.ip_address or not intf_b.network_address:
                        continue
                    
                    if intf_a.network_address == intf_b.network_address and intf_a.cidr == intf_b.cidr:
                        if intf_a.ip_address != intf_b.ip_address:
                            if intf_a.cidr in (30, 31):
                                sig = "P2P_SUBNET_30_31"
                                desc = f"Point-to-point /{intf_a.cidr} subnet match ({intf_a.network_address}/{intf_a.cidr})"
                            else:
                                sig = "SHARED_SUBNET_24"
                                desc = f"Shared broadcast domain subnet match ({intf_a.network_address}/{intf_a.cidr})"
                            
                            ev = [
                                f"{dev_a.raw_filename}:{intf_a_name} ({intf_a.ip_address})",
                                f"{dev_b.raw_filename}:{intf_b_name} ({intf_b.ip_address})"
                            ]
                            add_signal(dev_a.hostname, intf_a_name, dev_b.hostname, intf_b_name, sig, desc, ev)

    # --- Signal 4: Switch Trunk Matching ---
    for i in range(len(device_list)):
        for j in range(i + 1, len(device_list)):
            dev_a = device_list[i]
            dev_b = device_list[j]
            if dev_a.device_type == "switch" and dev_b.device_type == "switch":
                for intf_a_name, intf_a in dev_a.interfaces.items():
                    if intf_a.switchport_mode == "trunk":
                        for intf_b_name, intf_b in dev_b.interfaces.items():
                            if intf_b.switchport_mode == "trunk":
                                if intf_a.trunk_native_vlan == intf_b.trunk_native_vlan:
                                    ev = [
                                        f"{dev_a.raw_filename}:{intf_a_name} (Trunk Native VLAN {intf_a.trunk_native_vlan})",
                                        f"{dev_b.raw_filename}:{intf_b_name} (Trunk Native VLAN {intf_b.trunk_native_vlan})"
                                    ]
                                    add_signal(
                                        dev_a.hostname,
                                        intf_a_name,
                                        dev_b.hostname,
                                        intf_b_name,
                                        "TRUNK_CONFIG_PAIR",
                                        f"Mutual switch trunk configuration with matching Native VLAN {intf_a.trunk_native_vlan}",
                                        ev
                                    )

    # --- Signal 5: Next-Hop Routing Correlation ---
    for dev_a in device_list:
        for route in dev_a.routes:
            if route.next_hop:
                for dev_b in device_list:
                    if dev_a.hostname == dev_b.hostname:
                        continue
                    for intf_b_name, intf_b in dev_b.interfaces.items():
                        if intf_b.ip_address == route.next_hop:
                            out_intf = route.outgoing_interface or "GigabitEthernet0/0"
                            ev = [f"{dev_a.raw_filename} (Route {route.network}/{route.cidr} via {route.next_hop})"]
                            add_signal(
                                dev_a.hostname,
                                out_intf,
                                dev_b.hostname,
                                intf_b_name,
                                "NEXT_HOP_ROUTING_MATCH",
                                f"Routing table next-hop {route.next_hop} points to {dev_b.hostname}:{intf_b_name}",
                                ev
                            )

    # --- Signal 6: Interface Description Hint (Merged into existing edge if present) ---
    for dev_a in device_list:
        for intf_a_name, intf_a in dev_a.interfaces.items():
            if intf_a.description:
                for dev_b in device_list:
                    if dev_a.hostname == dev_b.hostname:
                        continue
                    if re.search(r"\b" + re.escape(dev_b.hostname) + r"\b", intf_a.description, re.IGNORECASE):
                        ev = [f"{dev_a.raw_filename}:{intf_a_name} (description '{intf_a.description}')"]
                        # Check if a specific edge already exists for (dev_a, intf_a, dev_b, *)
                        matched_existing = False
                        for key in list(candidate_edges.keys()):
                            src_d, src_i, tgt_d, tgt_i = key
                            if (src_d == dev_a.hostname and src_i == intf_a_name and tgt_d == dev_b.hostname) or \
                               (tgt_d == dev_a.hostname and tgt_i == intf_a_name and src_d == dev_b.hostname):
                                add_signal(src_d, src_i, tgt_d, tgt_i, "DESCRIPTION_HINT", f"Interface description matches peer {dev_b.hostname}", ev)
                                matched_existing = True
                                break
                        if not matched_existing:
                            add_signal(
                                dev_a.hostname,
                                intf_a_name,
                                dev_b.hostname,
                                "Unspecified",
                                "DESCRIPTION_HINT",
                                f"Interface description explicitly mentions peer {dev_b.hostname}",
                                ev
                            )

    # --- Signal 7: Active Physical / Link Carrier (Unknown Endpoint) ---
    connected_ports = set()
    for key in candidate_edges.keys():
        src_d, src_i, tgt_d, tgt_i = key
        connected_ports.add((src_d, src_i))
        connected_ports.add((tgt_d, tgt_i))

    for dev in device_list:
        if dev.is_placeholder:
            continue
        for intf_name, intf in dev.interfaces.items():
            if intf.admin_status == "up" and intf.line_status == "up":
                lower_name = intf_name.lower()
                if lower_name.startswith(("loopback", "null", "vlan")):
                    continue
                if (dev.hostname, intf_name) in connected_ports:
                    continue
                
                placeholder_id = f"UNKNOWN_PORT_{dev.hostname}_{intf_name}"
                if placeholder_id not in devices:
                    devices[placeholder_id] = ParsedDevice(
                        hostname="???",
                        canonical_name=placeholder_id,
                        display_name="???",
                        is_placeholder=True,
                        placeholder_for_device=None,
                        placeholder_for_interface=intf_name,
                        device_type="unknown",
                        raw_filename=""
                    )
                
                ev = [f"{dev.raw_filename}:{intf_name} (status up/up)"]
                add_signal(
                    dev.hostname,
                    intf_name,
                    placeholder_id,
                    "Unspecified",
                    "ACTIVE_PORT_CARRIER",
                    f"Active physical/link carrier on {dev.hostname}:{intf_name} with unknown peer",
                    ev
                )
                connected_ports.add((dev.hostname, intf_name))

    # Clean up any orphaned Unspecified edges if specific edges exist or if confidence < 0.40
    filtered_edges = {}
    for key, data in candidate_edges.items():
        src_dev, src_intf, tgt_dev, tgt_intf = key
        signals_dict = data["signals"]
        weights = [sig.weight for sig in signals_dict.values()]
        confidence = calculate_noisy_or(weights)
        
        if "Unspecified" in (src_intf, tgt_intf) and confidence < 0.40:
            continue
        filtered_edges[key] = data

    # --- Build DiscoveredLink list ---
    discovered_links: list[DiscoveredLink] = []
    
    for key, data in filtered_edges.items():
        src_dev, src_intf, tgt_dev, tgt_intf = key
        signals_dict = data["signals"]
        weights = [sig.weight for sig in signals_dict.values()]
        confidence = calculate_noisy_or(weights)
        classification = classify_confidence(confidence)
        
        is_bidirectional = (len(data["bidirectional_checks"]) >= 2) or ("CDP_NEIGHBOR_DETAIL" in signals_dict)
        
        discovered_links.append(DiscoveredLink(
            source_device=src_dev,
            source_interface=src_intf,
            target_device=tgt_dev,
            target_interface=tgt_intf,
            confidence=round(confidence, 4),
            classification=classification,
            signals=list(signals_dict.values()),
            is_bidirectional=is_bidirectional
        ))
        
    return discovered_links
