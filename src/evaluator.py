# src/evaluator.py
"""
Automated Student Lab Evaluation & Diagnostic Grading Engine.
Compares a student's topology submission against instructor-defined EvaluationCriteria.
"""

import ipaddress
import re
from src.models import (
    EvaluationCriteria,
    EvaluationPolicies,
    EvaluationReport,
    EvaluationRule,
    RuleResult,
    TopologyResult,
)
from src.parsers import canonical_device_name, normalize_interface_name


def _build_device_mapping(criteria: EvaluationCriteria, student_topology: TopologyResult) -> dict[str, str]:
    """
    Builds a 1-to-1 mapping from criteria target device names to student device hostnames.
    Prioritizes exact and canonical matches, falling back to topological role matching if allow_custom_hostnames is True.
    """
    mapping: dict[str, str] = {}
    used_student_hosts: set[str] = set()
    student_devices = {k: v for k, v in student_topology.devices.items() if not v.is_placeholder}

    # Extract all distinct target devices requested by criteria rules
    ref_devices: dict[str, str] = {} # target_device -> expected device_type
    for r in criteria.rules:
        dev_name = r.target_device
        if dev_name and dev_name not in ref_devices:
            dev_type = "router"
            if r.expected_value and isinstance(r.expected_value, dict):
                dev_type = r.expected_value.get("device_type", "router")
            ref_devices[dev_name] = dev_type

    # 1. Exact Name Matches
    for ref_name in ref_devices:
        if ref_name in student_devices and ref_name not in used_student_hosts:
            mapping[ref_name] = ref_name
            used_student_hosts.add(ref_name)

    # 2. Canonical / Case-Insensitive Matches
    for ref_name in ref_devices:
        if ref_name in mapping:
            continue
        ref_norm = canonical_device_name(ref_name).lower()
        for s_name, s_dev in student_devices.items():
            if s_name in used_student_hosts:
                continue
            if canonical_device_name(s_name).lower() == ref_norm or canonical_device_name(s_dev.display_name or "").lower() == ref_norm:
                mapping[ref_name] = s_name
                used_student_hosts.add(s_name)
                break

    # 3. Role-Based Fallback (if allow_custom_hostnames is enabled)
    if criteria.policies.allow_custom_hostnames:
        for ref_name, exp_type in ref_devices.items():
            if ref_name in mapping:
                continue
            
            # Find an unmapped student device of matching type
            for s_name, s_dev in student_devices.items():
                if s_name in used_student_hosts:
                    continue
                if s_dev.device_type == exp_type or (exp_type in ("router", "l3_switch") and s_dev.device_type in ("router", "l3_switch")):
                    mapping[ref_name] = s_name
                    used_student_hosts.add(s_name)
                    break

    return mapping


def _find_student_device(devices: dict, target_hostname: str, device_mapping: dict[str, str]):
    """Finds student ParsedDevice via device mapping or direct lookup."""
    if not target_hostname:
        return None
    mapped_name = device_mapping.get(target_hostname, target_hostname)
    if mapped_name in devices:
        return devices[mapped_name]

    # Fallback to direct search
    target_norm = canonical_device_name(target_hostname).lower()
    for name, dev in devices.items():
        if canonical_device_name(name).lower() == target_norm or canonical_device_name(dev.display_name or "").lower() == target_norm:
            return dev
    return None


def _find_student_interface(interfaces: dict, target_interface_name: str, strict_ports: bool = True):
    """Finds a student interface by exact name or normalized shorthand / speed class."""
    if not target_interface_name:
        return None
    if target_interface_name in interfaces:
        return interfaces[target_interface_name]

    target_norm = normalize_interface_name(target_interface_name).lower()
    for name, intf in interfaces.items():
        if normalize_interface_name(name).lower() == target_norm:
            return intf

    if not strict_ports:
        is_gi = "gigabit" in target_norm
        is_fa = "fast" in target_norm
        is_se = "serial" in target_norm
        for name, intf in interfaces.items():
            n_lower = normalize_interface_name(name).lower()
            if is_gi and "gigabit" in n_lower:
                return intf
            elif is_fa and "fast" in n_lower:
                return intf
            elif is_se and "serial" in n_lower:
                return intf

    return None


def _link_matches(link, src_dev: str, src_intf: str, tgt_dev: str, tgt_intf: str, strict_ports: bool = True) -> bool:
    """Checks if a DiscoveredLink matches the expected endpoints in either direction."""
    src_d_norm = canonical_device_name(src_dev).lower()
    tgt_d_norm = canonical_device_name(tgt_dev).lower()
    src_i_norm = normalize_interface_name(src_intf).lower()
    tgt_i_norm = normalize_interface_name(tgt_intf).lower()

    l_src_d = canonical_device_name(link.source_device).lower()
    l_tgt_d = canonical_device_name(link.target_device).lower()
    l_src_i = normalize_interface_name(link.source_interface).lower()
    l_tgt_i = normalize_interface_name(link.target_interface).lower()

    # Forward direction
    if l_src_d == src_d_norm and l_tgt_d == tgt_d_norm:
        if strict_ports:
            if l_src_i == src_i_norm and l_tgt_i == tgt_i_norm:
                return True
        else:
            return True
    
    # Reverse direction
    if l_src_d == tgt_d_norm and l_tgt_d == src_d_norm:
        if strict_ports:
            if l_src_i == tgt_i_norm and l_tgt_i == src_i_norm:
                return True
        else:
            return True

    return False


def _evaluate_relational_subnet(
    rule: EvaluationRule,
    criteria: EvaluationCriteria,
    devices: dict,
    used_subnets: dict,
    device_mapping: dict[str, str]
) -> tuple[bool, float, str, str]:
    exp = rule.expected_value or {}
    src_dev_name = exp.get("source_device", rule.target_device)
    src_intf_name = exp.get("source_interface", rule.target_interface)
    tgt_dev_name = exp.get("target_device", "")
    tgt_intf_name = exp.get("target_interface", "")
    exp_prefix = exp.get("expected_prefixlen")

    dev_a = _find_student_device(devices, src_dev_name, device_mapping)
    dev_b = _find_student_device(devices, tgt_dev_name, device_mapping)

    if not dev_a or not dev_b:
        missing = src_dev_name if not dev_a else tgt_dev_name
        return False, 0.0, "Missing Device", f"Cannot verify dynamic subnet: Device '{missing}' is missing in submission."

    intf_a = _find_student_interface(dev_a.interfaces, src_intf_name, criteria.policies.strict_port_matching)
    intf_b = _find_student_interface(dev_b.interfaces, tgt_intf_name, criteria.policies.strict_port_matching)

    if not intf_a or not intf_b:
        missing_intf = f"{src_dev_name} {src_intf_name}" if not intf_a else f"{tgt_dev_name} {tgt_intf_name}"
        return False, 0.0, "Missing Interface", f"Cannot verify dynamic subnet: Interface '{missing_intf}' is missing."

    if not intf_a.ip_address or not intf_b.ip_address:
        unconfig = f"{src_dev_name}:{src_intf_name}" if not intf_a.ip_address else f"{tgt_dev_name}:{tgt_intf_name}"
        return False, 0.0, "Unassigned IP", f"Endpoint {unconfig} has no IPv4 address configured."

    try:
        iface_a = ipaddress.IPv4Interface(f"{intf_a.ip_address}/{intf_a.subnet_mask or intf_a.cidr or 24}")
        iface_b = ipaddress.IPv4Interface(f"{intf_b.ip_address}/{intf_b.subnet_mask or intf_b.cidr or 24}")
    except Exception as e:
        return False, 0.0, "Invalid IP Syntax", f"Malformed IPv4 configuration: {e}"

    if iface_a.network != iface_b.network:
        actual_val = f"{intf_a.ip_address}/{iface_a.network.prefixlen} vs {intf_b.ip_address}/{iface_b.network.prefixlen}"
        return False, 0.0, actual_val, f"Subnet mismatch: {src_dev_name} ({intf_a.ip_address}) and {tgt_dev_name} ({intf_b.ip_address}) are on different subnets ({iface_a.network} vs {iface_b.network})."

    if iface_a.ip == iface_b.ip:
        return False, round(rule.points * 0.3, 1), f"Duplicate IP ({iface_a.ip})", f"IP Collision: Both {src_dev_name} and {tgt_dev_name} configured with identical IP {iface_a.ip}."

    if criteria.policies.enforce_prefix_length and exp_prefix is not None:
        if iface_a.network.prefixlen != exp_prefix:
            return False, round(rule.points * 0.6, 1), f"/{iface_a.network.prefixlen}", f"Subnet matches ({iface_a.network}), but CIDR prefix /{iface_a.network.prefixlen} does not match required /{exp_prefix}."

    net_str = str(iface_a.network)
    link_key = tuple(sorted([f"{src_dev_name}:{src_intf_name}", f"{tgt_dev_name}:{tgt_intf_name}"]))
    if net_str in used_subnets and used_subnets[net_str] != link_key:
        return False, round(rule.points * 0.5, 1), f"Duplicate Subnet {net_str}", f"Subnet {net_str} is already used on another link. Point-to-point subnets must be globally unique."
    used_subnets[net_str] = link_key

    if criteria.policies.verify_default_gateways:
        for host_dev, router_dev, r_intf in [(dev_a, dev_b, intf_b), (dev_b, dev_a, intf_a)]:
            if host_dev.device_type in ("host", "switch") and host_dev.default_gateway:
                try:
                    gw_ip = ipaddress.IPv4Address(host_dev.default_gateway)
                    if gw_ip != ipaddress.IPv4Address(r_intf.ip_address):
                        return False, round(rule.points * 0.7, 1), f"Gateway {host_dev.default_gateway}", f"{host_dev.hostname} default gateway ({host_dev.default_gateway}) does not match router interface IP ({r_intf.ip_address})."
                except Exception:
                    pass

    actual_str = f"{iface_a.ip} ⟷ {iface_b.ip} ({iface_a.network})"
    feedback_str = f"Mutual subnet ({iface_a.network}) verified between {src_dev_name}:{src_intf_name} ({intf_a.ip_address}) and {tgt_dev_name}:{tgt_intf_name} ({intf_b.ip_address})."
    return True, rule.points, actual_str, feedback_str


def evaluate_student_submission(
    criteria: EvaluationCriteria,
    student_topology: TopologyResult
) -> EvaluationReport:
    """
    Evaluates a student's submission against an EvaluationCriteria specification.
    Returns a comprehensive EvaluationReport with score, letter grade, and itemized feedback.
    """
    rule_results: list[RuleResult] = []
    total_score = 0.0
    max_score = 0.0
    passed_count = 0
    failed_count = 0

    devices = student_topology.devices
    links = student_topology.links
    policies = criteria.policies
    device_mapping = _build_device_mapping(criteria, student_topology)
    used_subnets: dict[str, tuple] = {}

    for rule in criteria.rules:
        pts_possible = float(rule.points)
        max_score += pts_possible
        exp = rule.expected_value or {}

        # 1. Device Presence Rule
        if rule.category == "device":
            dev = _find_student_device(devices, rule.target_device, device_mapping)
            if dev and not dev.is_placeholder:
                pts_earned = pts_possible
                passed = True
                if dev.hostname.lower() == rule.target_device.lower():
                    actual = f"Present ({dev.hostname}, type: {dev.device_type})"
                    feedback = f"Device '{rule.target_device}' correctly detected in topology."
                else:
                    actual = f"Present as '{dev.hostname}'"
                    feedback = f"Device '{rule.target_device}' matched to '{dev.hostname}' (Matched by topological role & degree)."
            else:
                pts_earned = 0.0
                passed = False
                actual = "Missing"
                feedback = f"Required device '{rule.target_device}' was not found in your submission."

        # 2. Interface IP & Subnet Rule
        elif rule.category == "interface_ip":
            dev = _find_student_device(devices, rule.target_device, device_mapping)
            if not dev:
                pts_earned = 0.0
                passed = False
                actual = f"Device '{rule.target_device}' not found"
                feedback = f"Cannot evaluate IP address because device '{rule.target_device}' is missing."
            else:
                intf = _find_student_interface(dev.interfaces, rule.target_interface or "", policies.strict_port_matching)
                if not intf:
                    pts_earned = 0.0
                    passed = False
                    actual = f"Interface '{rule.target_interface}' missing"
                    feedback = f"Interface '{rule.target_interface}' was not found on device '{rule.target_device}'."
                elif not intf.ip_address:
                    pts_earned = 0.0
                    passed = False
                    actual = "No IP configured (Unassigned)"
                    feedback = f"Interface {rule.target_interface} has no IP address configured. Expected {exp.get('ip_address')}/{exp.get('cidr')}."
                else:
                    exp_ip = exp.get("ip_address")
                    exp_cidr = exp.get("cidr")
                    exp_mask = exp.get("subnet_mask")

                    ip_match = intf.ip_address == exp_ip
                    cidr_match = (intf.cidr == exp_cidr) if (exp_cidr and intf.cidr) else True

                    if ip_match and cidr_match:
                        pts_earned = pts_possible
                        passed = True
                        actual = f"{intf.ip_address}/{intf.cidr or 24}"
                        feedback = f"Correct IP addressing ({intf.ip_address}/{intf.cidr or 24}) verified on {rule.target_device} {rule.target_interface}."
                    elif ip_match and not cidr_match:
                        pts_earned = round(pts_possible * 0.5, 1)
                        passed = False
                        actual = f"{intf.ip_address}/{intf.cidr}"
                        feedback = f"IP address {intf.ip_address} is correct, but subnet mask /{intf.cidr} is incorrect. Expected /{exp_cidr} ({exp_mask})."
                    else:
                        pts_earned = 0.0
                        passed = False
                        actual = f"{intf.ip_address}/{intf.cidr or 24}"
                        feedback = f"Configured IP ({intf.ip_address}/{intf.cidr or 24}) does not match expected ({exp_ip}/{exp_cidr})."

        # 3. Dynamic Relational Subnet Rule
        elif rule.category == "relational_subnet":
            passed, pts_earned, actual, feedback = _evaluate_relational_subnet(
                rule=rule,
                criteria=criteria,
                devices=devices,
                used_subnets=used_subnets,
                device_mapping=device_mapping
            )

        # 4. Interface Status / No Shutdown Rule
        elif rule.category == "interface_status":
            dev = _find_student_device(devices, rule.target_device, device_mapping)
            if not dev:
                pts_earned = 0.0
                passed = False
                actual = f"Device '{rule.target_device}' missing"
                feedback = f"Cannot verify operational status: device '{rule.target_device}' missing."
            else:
                intf = _find_student_interface(dev.interfaces, rule.target_interface or "", policies.strict_port_matching)
                if not intf:
                    pts_earned = 0.0
                    passed = False
                    actual = f"Interface '{rule.target_interface}' missing"
                    feedback = f"Interface '{rule.target_interface}' missing on device '{rule.target_device}'."
                elif intf.admin_status == "administratively down":
                    pts_earned = 0.0
                    passed = False
                    actual = "administratively down"
                    feedback = f"Interface {rule.target_device} {rule.target_interface} is shut down. Missing 'no shutdown' command in configuration."
                else:
                    pts_earned = pts_possible
                    passed = True
                    actual = f"{intf.admin_status}/{intf.line_status}"
                    feedback = f"Interface {rule.target_device} {rule.target_interface} operational state verified (up/up)."

        # 5. Physical Cabling & Link Rule
        elif rule.category == "cabling":
            src_dev_orig = exp.get("source_device", rule.target_device)
            src_intf = exp.get("source_interface", rule.target_interface or "")
            tgt_dev_orig = exp.get("target_device", "")
            tgt_intf = exp.get("target_interface", "")

            src_dev = device_mapping.get(src_dev_orig, src_dev_orig)
            tgt_dev = device_mapping.get(tgt_dev_orig, tgt_dev_orig)

            matched_link = None
            for l in links:
                if _link_matches(l, src_dev, src_intf, tgt_dev, tgt_intf, policies.strict_port_matching):
                    matched_link = l
                    break

            if matched_link:
                has_cable_conflict = any("Cable" in c or "straight-through" in c.lower() for c in matched_link.conflicts)
                if has_cable_conflict and policies.strict_cable_type:
                    pts_earned = round(pts_possible * 0.4, 1)
                    passed = False
                    actual = f"Connected via {matched_link.cable_type or 'Unknown cable'} (Cabling Error)"
                    feedback = f"Physical connection found between {src_dev_orig}:{src_intf} and {tgt_dev_orig}:{tgt_intf}, but incorrect cable type media was used."
                elif has_cable_conflict and not policies.strict_cable_type:
                    pts_earned = pts_possible
                    passed = True
                    actual = f"Connected ({matched_link.cable_type} - Auto-MDIX Tolerated)"
                    feedback = f"Physical connection verified between {src_dev_orig} and {tgt_dev_orig} (Auto-MDIX copper equivalence accepted under instructor policy)."
                else:
                    pts_earned = pts_possible
                    passed = True
                    actual = f"Connected: {matched_link.source_device}:{matched_link.source_interface} ⟷ {matched_link.target_device}:{matched_link.target_interface}"
                    feedback = f"Physical connection verified between {src_dev_orig} ({src_intf}) and {tgt_dev_orig} ({tgt_intf})."
            else:
                pts_earned = 0.0
                passed = False
                actual = "Disconnected / Uncabled"
                feedback = f"No physical connection found between {src_dev_orig} ({src_intf}) and {tgt_dev_orig} ({tgt_intf}). Verify physical cabling in Packet Tracer."

        # 6. VLAN & Switchport Rule
        elif rule.category == "vlan_trunk":
            dev = _find_student_device(devices, rule.target_device, device_mapping)
            if not dev:
                pts_earned = 0.0
                passed = False
                actual = f"Device '{rule.target_device}' missing"
                feedback = f"Cannot evaluate VLAN configuration: device '{rule.target_device}' missing."
            else:
                intf = _find_student_interface(dev.interfaces, rule.target_interface or "", policies.strict_port_matching)
                if not intf:
                    pts_earned = 0.0
                    passed = False
                    actual = f"Interface '{rule.target_interface}' missing"
                    feedback = f"Interface '{rule.target_interface}' missing on switch '{rule.target_device}'."
                else:
                    exp_mode = exp.get("switchport_mode", "access")
                    if exp_mode == "trunk":
                        exp_native = exp.get("trunk_native_vlan", 1)
                        if intf.switchport_mode == "trunk" and intf.trunk_native_vlan == exp_native:
                            pts_earned = pts_possible
                            passed = True
                            actual = f"Trunk (Native VLAN {intf.trunk_native_vlan})"
                            feedback = f"Trunk port configuration verified on {rule.target_device} {rule.target_interface}."
                        elif intf.switchport_mode == "trunk":
                            pts_earned = round(pts_possible * 0.5, 1)
                            passed = False
                            actual = f"Trunk (Native VLAN {intf.trunk_native_vlan})"
                            feedback = f"Port is trunking, but Native VLAN ({intf.trunk_native_vlan}) does not match expected ({exp_native})."
                        else:
                            pts_earned = 0.0
                            passed = False
                            actual = f"Mode: {intf.switchport_mode or 'access'}"
                            feedback = f"Expected 802.1Q trunk port, but interface is configured as '{intf.switchport_mode or 'access'}'."
                    else:
                        exp_vlan = exp.get("access_vlan", 1)
                        if intf.switchport_mode == "access" and intf.access_vlan == exp_vlan:
                            pts_earned = pts_possible
                            passed = True
                            actual = f"Access VLAN {intf.access_vlan}"
                            feedback = f"Access port assigned to VLAN {intf.access_vlan} on {rule.target_device} {rule.target_interface}."
                        else:
                            pts_earned = 0.0
                            passed = False
                            actual = f"Access VLAN {intf.access_vlan or 'None'}"
                            feedback = f"Expected Access VLAN {exp_vlan}, but port is assigned to VLAN {intf.access_vlan or 'default (1)'}."

        # 7. Routing / OSPF Rule
        elif rule.category == "routing":
            dev = _find_student_device(devices, rule.target_device, device_mapping)
            if not dev:
                pts_earned = 0.0
                passed = False
                actual = f"Device '{rule.target_device}' missing"
                feedback = f"Cannot evaluate routing: device '{rule.target_device}' missing."
            else:
                proto = exp.get("protocol", "ospf")
                exp_area = exp.get("area", 0)
                exp_pid = exp.get("process_id", 1)
                
                matched_ospf = None
                for proc in dev.ospf_processes:
                    if policies.allow_flexible_process_ids or proc.get("process_id") == exp_pid:
                        for n in proc.get("networks", []):
                            if n.get("area") == exp_area:
                                matched_ospf = proc
                                break
                
                if matched_ospf:
                    pts_earned = pts_possible
                    passed = True
                    actual = f"OSPF Process {matched_ospf.get('process_id')} (Area {exp_area})"
                    feedback = f"OSPF routing verified on {rule.target_device} (Area {exp_area}, process ID {matched_ospf.get('process_id')} accepted)."
                else:
                    pts_earned = 0.0
                    passed = False
                    actual = "No matching OSPF config"
                    feedback = f"Missing OSPF routing for Area {exp_area} on {rule.target_device}."

        # 8. Security Baseline Rule
        elif rule.category == "security":
            dev = _find_student_device(devices, rule.target_device, device_mapping)
            check_type = exp.get("check_type")
            if not dev:
                pts_earned = 0.0
                passed = False
                actual = "Missing Device"
                feedback = f"Cannot verify security baseline: device '{rule.target_device}' is missing."
            elif check_type == "enable_secret":
                if dev.has_enable_secret:
                    pts_earned = pts_possible
                    passed = True
                    actual = "Configured (enable secret)"
                    feedback = f"Encrypted enable secret verified on {rule.target_device}."
                else:
                    pts_earned = 0.0
                    passed = False
                    actual = "Missing enable secret"
                    feedback = f"Missing 'enable secret' privileged password command on {rule.target_device}."
            elif check_type == "password_encryption":
                if dev.has_password_encryption:
                    pts_earned = pts_possible
                    passed = True
                    actual = "Enabled (service password-encryption)"
                    feedback = f"Password encryption service verified on {rule.target_device}."
                else:
                    pts_earned = 0.0
                    passed = False
                    actual = "Disabled"
                    feedback = f"Missing 'service password-encryption' command on {rule.target_device}."
            elif check_type == "vty_login":
                if dev.has_vty_login:
                    pts_earned = pts_possible
                    passed = True
                    actual = "Secured (line vty login)"
                    feedback = f"VTY line login authentication verified on {rule.target_device}."
                else:
                    pts_earned = 0.0
                    passed = False
                    actual = "Unsecured VTY"
                    feedback = f"Missing 'login' / password protection under 'line vty' on {rule.target_device}."
            else:
                pts_earned = pts_possible
                passed = True
                actual = "Met"
                feedback = "Security baseline met."

        # 9. Interface Documentation Rule
        elif rule.category == "documentation":
            dev = _find_student_device(devices, rule.target_device, device_mapping)
            if not dev:
                pts_earned = 0.0
                passed = False
                actual = "Missing Device"
                feedback = f"Cannot verify documentation: device '{rule.target_device}' is missing."
            else:
                intf = _find_student_interface(dev.interfaces, rule.target_interface or "", policies.strict_port_matching)
                if intf and intf.description:
                    pts_earned = pts_possible
                    passed = True
                    actual = f"'{intf.description}'"
                    feedback = f"Interface description documented on {rule.target_device} {rule.target_interface}."
                else:
                    pts_earned = 0.0
                    passed = False
                    actual = "No description"
                    feedback = f"Missing 'description' statement on {rule.target_device} {rule.target_interface}."

        else:
            pts_earned = pts_possible
            passed = True
            actual = "N/A"
            feedback = "Criterion met."

        if passed:
            passed_count += 1
        else:
            failed_count += 1

        total_score += pts_earned

        rule_results.append(RuleResult(
            rule_id=rule.rule_id,
            category=rule.category,
            description=rule.description,
            points_possible=pts_possible,
            points_earned=pts_earned,
            passed=passed,
            actual_value=actual,
            feedback=feedback,
            target_device=rule.target_device,
            target_interface=rule.target_interface
        ))

    percentage = (total_score / max_score * 100.0) if max_score > 0 else 0.0
    percentage = round(percentage, 1)
    total_score = round(total_score, 1)
    max_score = round(max_score, 1)

    if percentage >= 97.0:
        grade_letter = "A+"
    elif percentage >= 90.0:
        grade_letter = "A"
    elif percentage >= 80.0:
        grade_letter = "B"
    elif percentage >= 70.0:
        grade_letter = "C"
    elif percentage >= 60.0:
        grade_letter = "D"
    else:
        grade_letter = "F"

    return EvaluationReport(
        lab_title=criteria.lab_title,
        total_score=total_score,
        max_score=max_score,
        percentage=percentage,
        passed_count=passed_count,
        failed_count=failed_count,
        grade_letter=grade_letter,
        results=rule_results,
        topology=student_topology
    )
