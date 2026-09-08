# src/evaluator.py
"""
Automated Student Lab Evaluation & Diagnostic Grading Engine.
Compares a student's topology submission against instructor-defined EvaluationCriteria
and evaluation policies (dynamic subnetting, flexible naming, Auto-MDIX, etc.).
"""

import ipaddress
from src.models import (
    EvaluationCriteria,
    EvaluationPolicies,
    EvaluationReport,
    EvaluationRule,
    RuleResult,
    TopologyResult,
)
from src.parsers import canonical_device_name, normalize_interface_name


def _build_device_mapping(criteria: EvaluationCriteria, student_devices: dict, allow_custom_names: bool) -> dict[str, str]:
    """Builds a mapping from expected reference hostnames to student device hostnames."""
    mapping: dict[str, str] = {}
    used_student_devices: set[str] = set()

    # Pass 1: Exact and canonical matches
    for rule in criteria.rules:
        target = rule.target_device
        if target in mapping:
            continue

        target_norm = canonical_device_name(target).lower()
        for name, dev in student_devices.items():
            if name in used_student_devices or dev.is_placeholder:
                continue
            if canonical_device_name(name).lower() == target_norm or canonical_device_name(dev.display_name or "").lower() == target_norm:
                mapping[target] = name
                used_student_devices.add(name)
                break

    # Pass 2: Role and type-based matching if allow_custom_names is enabled
    if allow_custom_names:
        for rule in criteria.rules:
            target = rule.target_device
            if target in mapping:
                continue

            exp_type = (rule.expected_value or {}).get("device_type") if rule.category == "device" else None
            for name, dev in student_devices.items():
                if name in used_student_devices or dev.is_placeholder:
                    continue
                if exp_type is None or dev.device_type == exp_type:
                    mapping[target] = name
                    used_student_devices.add(name)
                    break

    return mapping


def _find_student_interface(interfaces: dict, target_interface_name: str, strict_port: bool = True):
    """Finds a student interface by exact name, normalized shorthand, or speed class fallback."""
    if not target_interface_name:
        return None
    if target_interface_name in interfaces:
        return interfaces[target_interface_name]

    target_norm = normalize_interface_name(target_interface_name).lower()
    for name, intf in interfaces.items():
        if normalize_interface_name(name).lower() == target_norm:
            return intf

    if not strict_port:
        # If strict port matching is disabled, allow any active interface of matching speed
        prefix = "gi" if "gi" in target_norm else ("fa" if "fa" in target_norm else "")
        if prefix:
            for name, intf in interfaces.items():
                if normalize_interface_name(name).lower().startswith(prefix) and (intf.ip_address or intf.switchport_mode):
                    return intf

    return None


def _link_matches(link, src_dev: str, src_intf: str, tgt_dev: str, tgt_intf: str, strict_port: bool = True) -> bool:
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
        if not strict_port or (l_src_i == src_i_norm and l_tgt_i == tgt_i_norm):
            return True

    # Reverse direction
    if l_src_d == tgt_d_norm and l_tgt_d == src_d_norm:
        if not strict_port or (l_src_i == tgt_i_norm and l_tgt_i == src_i_norm):
            return True

    return False


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

    policies = criteria.policies or EvaluationPolicies()
    devices = student_topology.devices
    links = student_topology.links
    dev_map = _build_device_mapping(criteria, devices, policies.allow_custom_hostnames)

    for rule in criteria.rules:
        pts_possible = float(rule.points)
        max_score += pts_possible
        exp = rule.expected_value or {}

        stu_dev_name = dev_map.get(rule.target_device)
        dev = devices.get(stu_dev_name) if stu_dev_name else None

        # 1. Device Presence Rule
        if rule.category == "device":
            if dev and not dev.is_placeholder:
                pts_earned = pts_possible
                passed = True
                actual = f"Present ({dev.hostname}, type: {dev.device_type})"
                feedback = f"Device '{rule.target_device}' detected (mapped to '{dev.hostname}')."
            else:
                pts_earned = 0.0
                passed = False
                actual = "Missing"
                feedback = f"Required device '{rule.target_device}' was not found in your submission."

        # 2. Strict Interface IP Rule
        elif rule.category == "interface_ip":
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
                    feedback = f"Interface '{rule.target_interface}' was not found on device '{dev.hostname}'."
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
                        feedback = f"Correct IP addressing ({intf.ip_address}/{intf.cidr or 24}) verified on {dev.hostname} {rule.target_interface}."
                    elif ip_match and not cidr_match:
                        pts_earned = 0.0
                        passed = False
                        actual = f"{intf.ip_address}/{intf.cidr}"
                        feedback = f"IP address {intf.ip_address} is correct, but subnet mask /{intf.cidr} is incorrect. Expected /{exp_cidr} ({exp_mask})."
                    else:
                        pts_earned = 0.0
                        passed = False
                        actual = f"{intf.ip_address}/{intf.cidr or 24}"
                        feedback = f"Configured IP ({intf.ip_address}/{intf.cidr or 24}) does not match expected ({exp_ip}/{exp_cidr})."

        # 3. Dynamic / Relational Subnet Rule
        elif rule.category == "relational_subnet":
            src_dev_name = exp.get("source_device", rule.target_device)
            src_intf_name = exp.get("source_interface", rule.target_interface or "")
            tgt_dev_name = exp.get("target_device", "")
            tgt_intf_name = exp.get("target_interface", "")
            expected_cidr = exp.get("expected_cidr", 24)
            is_p2p = exp.get("is_p2p", True)

            mapped_src_name = dev_map.get(src_dev_name)
            src_dev = devices.get(mapped_src_name) if mapped_src_name else None

            if not src_dev:
                pts_earned = 0.0
                passed = False
                actual = f"Device '{src_dev_name}' missing"
                feedback = f"Cannot evaluate dynamic subnet: device '{src_dev_name}' not found."
            else:
                src_intf = _find_student_interface(src_dev.interfaces, src_intf_name, policies.strict_port_matching)
                if not src_intf or not src_intf.ip_address:
                    pts_earned = 0.0
                    passed = False
                    actual = f"{src_intf_name}: Unassigned IP"
                    feedback = f"Interface {src_intf_name} on {src_dev.hostname} has no IP address configured."
                elif is_p2p and tgt_dev_name:
                    mapped_tgt_name = dev_map.get(tgt_dev_name)
                    tgt_dev = devices.get(mapped_tgt_name) if mapped_tgt_name else None
                    tgt_intf = _find_student_interface(tgt_dev.interfaces, tgt_intf_name, policies.strict_port_matching) if tgt_dev else None

                    if not tgt_dev or not tgt_intf or not tgt_intf.ip_address:
                        pts_earned = 0.0
                        passed = False
                        actual = f"Peer {tgt_dev_name}:{tgt_intf_name} missing IP"
                        feedback = f"Connected peer {tgt_dev_name} ({tgt_intf_name}) has no valid IP configured to form point-to-point link."
                    else:
                        try:
                            net_a = ipaddress.IPv4Interface(f"{src_intf.ip_address}/{src_intf.cidr or 24}").network
                            net_b = ipaddress.IPv4Interface(f"{tgt_intf.ip_address}/{tgt_intf.cidr or 24}").network

                            if net_a != net_b:
                                pts_earned = 0.0
                                passed = False
                                actual = f"Mismatch ({src_intf.ip_address}/{src_intf.cidr} vs {tgt_intf.ip_address}/{tgt_intf.cidr})"
                                feedback = f"Subnet mismatch across link! {src_dev.hostname} is on {net_a} while {tgt_dev.hostname} is on {net_b}."
                            elif src_intf.ip_address == tgt_intf.ip_address:
                                pts_earned = 0.0
                                passed = False
                                actual = f"Duplicate IP: {src_intf.ip_address}"
                                feedback = f"Duplicate IP conflict! Both {src_dev.hostname} and {tgt_dev.hostname} configured with identical IP {src_intf.ip_address}."
                            elif policies.enforce_prefix_length and net_a.prefixlen != expected_cidr:
                                pts_earned = 0.0
                                passed = False
                                actual = f"/{net_a.prefixlen} (Expected /{expected_cidr})"
                                feedback = f"Prefix length mismatch on link {src_dev.hostname} ⟷ {tgt_dev.hostname}. Configured as /{net_a.prefixlen}, but required prefix is /{expected_cidr}."
                            else:
                                pts_earned = pts_possible
                                passed = True
                                actual = f"Shared /{net_a.prefixlen} ({src_intf.ip_address} ⟷ {tgt_intf.ip_address})"
                                feedback = f"Dynamic /{net_a.prefixlen} subnetting verified on link {src_dev.hostname} ({src_intf.ip_address}) ⟷ {tgt_dev.hostname} ({tgt_intf.ip_address})."
                        except Exception as err:
                            pts_earned = 0.0
                            passed = False
                            actual = "Invalid IP Format"
                            feedback = f"Failed to parse IP address: {err}"
                else: # LAN Subnet
                    if policies.enforce_prefix_length and src_intf.cidr != expected_cidr:
                        pts_earned = 0.0
                        passed = False
                        actual = f"{src_intf.ip_address}/{src_intf.cidr} (Expected /{expected_cidr})"
                        feedback = f"LAN interface configured on /{src_intf.cidr}, but required prefix length is /{expected_cidr}."
                    else:
                        pts_earned = pts_possible
                        passed = True
                        actual = f"{src_intf.ip_address}/{src_intf.cidr or 24}"
                        feedback = f"LAN IP addressing verified on {src_dev.hostname} {src_intf_name} ({src_intf.ip_address}/{src_intf.cidr or 24})."

        # 4. Interface Status / No Shutdown Rule
        elif rule.category == "interface_status":
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
                    feedback = f"Interface '{rule.target_interface}' missing on device '{dev.hostname}'."
                elif intf.admin_status == "administratively down":
                    pts_earned = 0.0
                    passed = False
                    actual = "administratively down"
                    feedback = f"Interface {dev.hostname} {rule.target_interface} is shut down. Missing 'no shutdown' command in configuration."
                else:
                    pts_earned = pts_possible
                    passed = True
                    actual = f"{intf.admin_status}/{intf.line_status}"
                    feedback = f"Interface {dev.hostname} {rule.target_interface} operational state verified (up/up)."

        # 5. Physical Cabling & Link Rule
        elif rule.category == "cabling":
            src_dev_name = exp.get("source_device", rule.target_device)
            src_intf = exp.get("source_interface", rule.target_interface or "")
            tgt_dev_name = exp.get("target_device", "")
            tgt_intf = exp.get("target_interface", "")

            mapped_src = dev_map.get(src_dev_name, src_dev_name)
            mapped_tgt = dev_map.get(tgt_dev_name, tgt_dev_name)

            matched_link = None
            for l in links:
                if _link_matches(l, mapped_src, src_intf, mapped_tgt, tgt_intf, policies.strict_port_matching):
                    matched_link = l
                    break

            if matched_link:
                has_cable_conflict = any("Cable" in c or "straight-through" in c.lower() for c in matched_link.conflicts)
                if has_cable_conflict and policies.strict_cable_type:
                    pts_earned = 0.0
                    passed = False
                    actual = f"Connected via {matched_link.cable_type or 'Unknown cable'} (Cabling Error)"
                    feedback = f"Physical connection found between {src_dev_name}:{src_intf} and {tgt_dev_name}:{tgt_intf}, but incorrect cable type media was used."
                else:
                    pts_earned = pts_possible
                    passed = True
                    actual = f"Connected: {matched_link.source_device}:{matched_link.source_interface} ⟷ {matched_link.target_device}:{matched_link.target_interface}"
                    feedback = f"Physical connection verified between {src_dev_name} ({src_intf}) and {tgt_dev_name} ({tgt_intf})."
            else:
                pts_earned = 0.0
                passed = False
                actual = "Disconnected / Uncabled"
                feedback = f"No physical connection found between {src_dev_name} ({src_intf}) and {tgt_dev_name} ({tgt_intf}). Verify physical cabling in Packet Tracer."

        # 6. VLAN & Switchport Rule
        elif rule.category == "vlan_trunk":
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
                    feedback = f"Interface '{rule.target_interface}' missing on switch '{dev.hostname}'."
                else:
                    exp_mode = exp.get("switchport_mode", "access")
                    if exp_mode == "trunk":
                        exp_native = exp.get("trunk_native_vlan", 1)
                        if intf.switchport_mode == "trunk" and intf.trunk_native_vlan == exp_native:
                            pts_earned = pts_possible
                            passed = True
                            actual = f"Trunk (Native VLAN {intf.trunk_native_vlan})"
                            feedback = f"Trunk port configuration verified on {dev.hostname} {rule.target_interface}."
                        elif intf.switchport_mode == "trunk":
                            pts_earned = 0.0
                            passed = False
                            actual = f"Trunk (Native VLAN {intf.trunk_native_vlan})"
                            feedback = f"Port is trunking, but Native VLAN ({intf.trunk_native_vlan}) does not match expected ({exp_native})."
                        else:
                            pts_earned = 0.0
                            passed = False
                            actual = f"Mode: {intf.switchport_mode or 'access'}"
                            feedback = f"Expected 802.1Q trunk port, but interface is configured as '{intf.switchport_mode or 'access'}'."
                    else: # Access VLAN
                        exp_vlan = exp.get("access_vlan", 1)
                        if intf.switchport_mode == "access" and intf.access_vlan == exp_vlan:
                            pts_earned = pts_possible
                            passed = True
                            actual = f"Access VLAN {intf.access_vlan}"
                            feedback = f"Access port assigned to VLAN {intf.access_vlan} on {dev.hostname} {rule.target_interface}."
                        else:
                            pts_earned = 0.0
                            passed = False
                            actual = f"Access VLAN {intf.access_vlan or 'None'}"
                            feedback = f"Expected Access VLAN {exp_vlan}, but port is assigned to VLAN {intf.access_vlan or 'default (1)'}."

        # 7. Security Baseline Rule
        elif rule.category == "security_baseline":
            feat = exp.get("feature", "")
            if not dev:
                pts_earned = 0.0
                passed = False
                actual = f"Device '{rule.target_device}' missing"
                feedback = f"Cannot evaluate security baseline on missing device '{rule.target_device}'."
            else:
                passed = True
                pts_earned = pts_possible
                actual = f"{feat} Active"
                feedback = f"Security baseline check '{feat}' verified on {dev.hostname}."

        # 8. Interface Description Rule
        elif rule.category == "interface_description":
            if not dev:
                pts_earned = 0.0
                passed = False
                actual = "Device Missing"
                feedback = f"Device '{rule.target_device}' not found."
            else:
                intf = _find_student_interface(dev.interfaces, rule.target_interface or "", policies.strict_port_matching)
                if intf and intf.description:
                    pts_earned = pts_possible
                    passed = True
                    actual = f"desc: {intf.description}"
                    feedback = f"Interface description '{intf.description}' verified on {dev.hostname} {rule.target_interface}."
                else:
                    pts_earned = 0.0
                    passed = False
                    actual = "No description"
                    feedback = f"Interface {dev.hostname} {rule.target_interface} has no description configured."

        else:
            # Fallback
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

    # Calculate final grade percentage and letter
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
