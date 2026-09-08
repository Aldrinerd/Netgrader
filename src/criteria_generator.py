# src/criteria_generator.py
"""
Evaluation Criteria & Lab Instructions Generation Engine.
Extracts reference rules from an instructor's Packet Tracer file or configuration bundle,
formats student lab assignment instructions (.txt), and parses them back for automated grading.
"""

import json
import re
from src.models import EvaluationCriteria, EvaluationPolicies, EvaluationRule, TopologyResult


def generate_criteria_from_topology(
    topology: TopologyResult,
    lab_title: str = "Packet Tracer Lab Assignment",
    lab_description: str = "",
    target_total_points: float = 100.0,
    policies: EvaluationPolicies | None = None
) -> EvaluationCriteria:
    """
    Generates an EvaluationCriteria object with discrete grading rules extracted
    from an instructor's gold-standard reference topology and specified instructor policies.
    """
    if policies is None:
        policies = EvaluationPolicies()

    raw_rules: list[EvaluationRule] = []
    seen_rule_ids: set[str] = set()

    def add_rule(r: EvaluationRule):
        if r.rule_id not in seen_rule_ids:
            seen_rule_ids.add(r.rule_id)
            raw_rules.append(r)

    # Build a lookup for connected links to find peer interfaces
    link_peer_map: dict[tuple[str, str], tuple[str, str]] = {}
    for link in topology.links:
        src = link.source_device
        tgt = link.target_device
        if src and tgt and not src.startswith("UNKNOWN") and not tgt.startswith("UNKNOWN"):
            link_peer_map[(src, link.source_interface)] = (tgt, link.target_interface)
            link_peer_map[(tgt, link.target_interface)] = (src, link.source_interface)

    # 1. Device Presence Rules
    for hostname, dev in topology.devices.items():
        if dev.is_placeholder:
            continue
        dev_name = dev.display_name or dev.hostname
        add_rule(EvaluationRule(
            rule_id=f"dev_{dev.hostname.lower()}",
            category="device",
            description=f"Device '{dev_name}' ({dev.device_type.upper()}) must be present in topology",
            points=5.0,
            target_device=dev.hostname,
            expected_value={"device_type": dev.device_type, "hostname": dev.hostname, "display_name": dev_name}
        ))

        # Baseline Security Rules (if enabled)
        if policies.grade_security_baseline and dev.device_type in ("router", "switch", "l3_switch"):
            add_rule(EvaluationRule(
                rule_id=f"sec_secret_{dev.hostname.lower()}",
                category="security_baseline",
                description=f"Configure encrypted privileged access password ('enable secret') on {dev_name}",
                points=5.0,
                target_device=dev.hostname,
                expected_value={"feature": "enable_secret"}
            ))
            add_rule(EvaluationRule(
                rule_id=f"sec_enc_{dev.hostname.lower()}",
                category="security_baseline",
                description=f"Enable global service password encryption ('service password-encryption') on {dev_name}",
                points=5.0,
                target_device=dev.hostname,
                expected_value={"feature": "service_password_encryption"}
            ))

        # 2. Interface IP Addressing & Status Rules
        for intf_name, intf in dev.interfaces.items():
            safe_intf = intf_name.replace("/", "_").replace(" ", "_").replace(".", "_")

            # Documentation practice (if enabled)
            if policies.grade_interface_descriptions and intf.description:
                add_rule(EvaluationRule(
                    rule_id=f"desc_{dev.hostname.lower()}_{safe_intf.lower()}",
                    category="interface_description",
                    description=f"Configure descriptive interface label on {dev_name} {intf_name}",
                    points=4.0,
                    target_device=dev.hostname,
                    target_interface=intf_name,
                    expected_value={"description": intf.description}
                ))

            if intf.ip_address:
                cidr_val = intf.cidr or 24
                peer_info = link_peer_map.get((dev.hostname, intf_name))

                if policies.allow_dynamic_subnetting:
                    # Dynamic / Relational Subnet Checkpoint
                    if peer_info:
                        peer_dev, peer_intf = peer_info
                        rule_id = f"dyn_sub_{dev.hostname.lower()}_{safe_intf.lower()}"
                        add_rule(EvaluationRule(
                            rule_id=rule_id,
                            category="relational_subnet",
                            description=f"Configure dynamic /{cidr_val} subnet on link {dev_name} ({intf_name}) ⟷ {peer_dev} ({peer_intf}) (Must share matching subnet with peer)",
                            points=10.0,
                            target_device=dev.hostname,
                            target_interface=intf_name,
                            expected_value={
                                "source_device": dev.hostname,
                                "source_interface": intf_name,
                                "target_device": peer_dev,
                                "target_interface": peer_intf,
                                "expected_cidr": cidr_val,
                                "is_p2p": True
                            }
                        ))
                    else:
                        rule_id = f"dyn_lan_{dev.hostname.lower()}_{safe_intf.lower()}"
                        add_rule(EvaluationRule(
                            rule_id=rule_id,
                            category="relational_subnet",
                            description=f"Configure LAN /{cidr_val} subnet on {dev_name} {intf_name} (Must match connected LAN default gateways)",
                            points=10.0,
                            target_device=dev.hostname,
                            target_interface=intf_name,
                            expected_value={
                                "target_device": dev.hostname,
                                "target_interface": intf_name,
                                "expected_cidr": cidr_val,
                                "is_p2p": False
                            }
                        ))
                else:
                    # Strict IP Matching Checkpoint
                    cidr_str = f"/{intf.cidr}" if intf.cidr else ""
                    add_rule(EvaluationRule(
                        rule_id=f"ip_{dev.hostname.lower()}_{safe_intf.lower()}",
                        category="interface_ip",
                        description=f"Configure {dev_name} {intf_name} with IP {intf.ip_address}{cidr_str}",
                        points=10.0,
                        target_device=dev.hostname,
                        target_interface=intf_name,
                        expected_value={
                            "ip_address": intf.ip_address,
                            "cidr": intf.cidr,
                            "subnet_mask": intf.subnet_mask,
                            "network_address": intf.network_address
                        }
                    ))

                # If router/L3 switch interface is configured, check no shutdown (admin status up)
                if dev.device_type in ("router", "l3_switch") and intf.admin_status == "up":
                    add_rule(EvaluationRule(
                        rule_id=f"status_{dev.hostname.lower()}_{safe_intf.lower()}",
                        category="interface_status",
                        description=f"Enable interface {dev_name} {intf_name} (operational state: no shutdown)",
                        points=5.0,
                        target_device=dev.hostname,
                        target_interface=intf_name,
                        expected_value={"admin_status": "up", "line_status": "up"}
                    ))

            # 3. VLAN & Switchport Rules
            if intf.switchport_mode == "trunk":
                add_rule(EvaluationRule(
                    rule_id=f"trunk_{dev.hostname.lower()}_{safe_intf.lower()}",
                    category="vlan_trunk",
                    description=f"Configure {dev_name} {intf_name} as 802.1Q Trunk (Native VLAN {intf.trunk_native_vlan})",
                    points=8.0,
                    target_device=dev.hostname,
                    target_interface=intf_name,
                    expected_value={
                        "switchport_mode": "trunk",
                        "trunk_native_vlan": intf.trunk_native_vlan,
                        "trunk_allowed_vlans": intf.trunk_allowed_vlans
                    }
                ))
            elif intf.switchport_mode == "access" and intf.access_vlan:
                add_rule(EvaluationRule(
                    rule_id=f"access_{dev.hostname.lower()}_{safe_intf.lower()}",
                    category="vlan_trunk",
                    description=f"Assign {dev_name} {intf_name} to Access VLAN {intf.access_vlan}",
                    points=6.0,
                    target_device=dev.hostname,
                    target_interface=intf_name,
                    expected_value={
                        "switchport_mode": "access",
                        "access_vlan": intf.access_vlan
                    }
                ))

    # 4. Physical Cabling & Connectivity Rules
    seen_link_pairs = set()
    for link in topology.links:
        src = link.source_device
        tgt = link.target_device
        if not src or not tgt or src.startswith("UNKNOWN") or tgt.startswith("UNKNOWN"):
            continue

        pair_key = tuple(sorted([f"{src}:{link.source_interface}", f"{tgt}:{link.target_interface}"]))
        if pair_key in seen_link_pairs:
            continue
        seen_link_pairs.add(pair_key)

        safe_src_intf = link.source_interface.replace("/", "_").replace(" ", "_")
        safe_tgt_intf = link.target_interface.replace("/", "_").replace(" ", "_")
        link_id = f"cabling_{src.lower()}_{safe_src_intf.lower()}__to__{tgt.lower()}_{safe_tgt_intf.lower()}"

        cable_desc = link.cable_type or "cabling"
        add_rule(EvaluationRule(
            rule_id=link_id,
            category="cabling",
            description=f"Cable connection between {src} ({link.source_interface}) and {tgt} ({link.target_interface})",
            points=8.0,
            target_device=src,
            target_interface=link.source_interface,
            expected_value={
                "source_device": src,
                "source_interface": link.source_interface,
                "target_device": tgt,
                "target_interface": link.target_interface,
                "cable_type": link.cable_type
            }
        ))

    # Point Normalization so total equals target_total_points (e.g. 100.0 pts)
    if raw_rules:
        raw_total = sum(r.points for r in raw_rules)
        scale = target_total_points / raw_total if raw_total > 0 else 1.0
        allocated = 0.0
        for i, r in enumerate(raw_rules):
            if i == len(raw_rules) - 1:
                # Last rule takes remainder to ensure exact target sum
                r.points = round(target_total_points - allocated, 1)
            else:
                pts = round(r.points * scale, 1)
                if pts <= 0:
                    pts = 1.0
                r.points = pts
                allocated += pts

    ref_summary = {
        "device_count": len([d for d in topology.devices.values() if not d.is_placeholder]),
        "link_count": len(topology.links),
        "rule_count": len(raw_rules),
        "ip_count": len([r for r in raw_rules if r.category in ("interface_ip", "relational_subnet")]),
    }

    return EvaluationCriteria(
        lab_title=lab_title,
        lab_description=lab_description or "Configure physical cabling, IP addressing, and interface operational states as specified.",
        total_points=target_total_points,
        policies=policies,
        rules=raw_rules,
        reference_summary=ref_summary
    )


def format_criteria_to_instructions_txt(criteria: EvaluationCriteria) -> str:
    """
    Formats the evaluation criteria into a clean, human-readable student lab instructions document
    with an embedded machine-verifiable criteria schema at the end.
    """
    lines: list[str] = []
    lines.append("=" * 80)
    lines.append("CISCO LAB ASSIGNMENT & INSTRUCTION SHEET")
    lines.append("=" * 80)
    lines.append(f"Assignment Title : {criteria.lab_title}")
    lines.append(f"Total Points     : {criteria.total_points:.1f} pts")
    lines.append(f"Total Checkpoints: {len(criteria.rules)} items")
    lines.append("-" * 80)
    lines.append("")
    lines.append("1. LAB OVERVIEW & OBJECTIVES")
    lines.append("-" * 40)
    lines.append(criteria.lab_description or "Complete the topology configuration according to the criteria below.")
    lines.append("When finished, upload your Packet Tracer file (.pkt, .pka, .xml) or configuration archive (.zip, .txt)")
    lines.append("to the automated evaluation engine for instant grading and diagnostic feedback.")
    lines.append("")

    # Section 2: Policy Directives
    lines.append("2. INSTRUCTOR EVALUATION POLICIES & CONSTRAINTS")
    lines.append("-" * 80)
    pol = criteria.policies
    lines.append(f"• Dynamic Subnetting  : {'[ENABLED] Student-designed IP addressing permitted (mutual link matching enforced)' if pol.allow_dynamic_subnetting else '[DISABLED] Exact IP address matching enforced'}")
    lines.append(f"• Device Naming       : {'[FLEXIBLE] Custom hostnames allowed (matched by topological role)' if pol.allow_custom_hostnames else '[STRICT] Exact hostnames required'}")
    lines.append(f"• Physical Port Match : {'[STRICT] Exact interface numbers required' if pol.strict_port_matching else '[FLEXIBLE] Equivalent ports of same class allowed'}")
    lines.append(f"• Cable Medium Match  : {'[STRICT] Exact cable type required' if pol.strict_cable_type else '[FLEXIBLE] Auto-MDIX copper link equivalence permitted'}")
    lines.append(f"• Routing Process IDs : {'[FLEXIBLE] Any locally-significant OSPF process ID permitted' if pol.allow_flexible_process_ids else '[STRICT] Exact process ID required'}")
    lines.append("")

    # Section 3: IP Addressing Specification (Strict vs Dynamic)
    if pol.allow_dynamic_subnetting:
        dyn_rules = [r for r in criteria.rules if r.category == "relational_subnet"]
        if dyn_rules:
            lines.append("3. DYNAMIC IP SUBNETTING REQUIREMENTS")
            lines.append("-" * 80)
            lines.append(f"{'Device':<18} | {'Interface':<20} | {'Req. Prefix':<14} | {'Addressing Guideline':<30}")
            lines.append("-" * 80)
            for r in dyn_rules:
                exp = r.expected_value or {}
                cidr_str = f"/{exp.get('expected_cidr', 24)}"
                if exp.get("is_p2p"):
                    guideline = f"Custom {cidr_str} subnet (must match {exp.get('target_device')} {exp.get('target_interface')})"
                else:
                    guideline = f"Custom {cidr_str} LAN subnet (must match connected host gateway)"
                lines.append(f"{r.target_device:<18} | {r.target_interface or '':<20} | {cidr_str:<14} | {guideline:<30}")
            lines.append("")
    else:
        ip_rules = [r for r in criteria.rules if r.category == "interface_ip"]
        if ip_rules:
            lines.append("3. IP ADDRESSING SPECIFICATION TABLE")
            lines.append("-" * 80)
            lines.append(f"{'Device':<18} | {'Interface':<20} | {'IP Address / CIDR':<22} | {'Subnet Mask':<16}")
            lines.append("-" * 80)
            for r in ip_rules:
                exp = r.expected_value or {}
                ip_cidr = f"{exp.get('ip_address', '')}/{exp.get('cidr', '')}" if exp.get('ip_address') else "Unassigned"
                mask = exp.get("subnet_mask", "") or "N/A"
                lines.append(f"{r.target_device:<18} | {r.target_interface or '':<20} | {ip_cidr:<22} | {mask:<16}")
            lines.append("")

    # Section 4: Cabling Table
    cabling_rules = [r for r in criteria.rules if r.category == "cabling"]
    if cabling_rules:
        lines.append("4. PHYSICAL CABLING & PORT CONNECTIONS")
        lines.append("-" * 80)
        lines.append(f"{'Source Device':<18} | {'Port':<16} | {'Target Device':<18} | {'Port':<16}")
        lines.append("-" * 80)
        for r in cabling_rules:
            exp = r.expected_value or {}
            lines.append(f"{exp.get('source_device', ''):<18} | {exp.get('source_interface', ''):<16} | {exp.get('target_device', ''):<18} | {exp.get('target_interface', ''):<16}")
        lines.append("")

    # Section 5: VLAN & Switchport Requirements
    vlan_rules = [r for r in criteria.rules if r.category == "vlan_trunk"]
    if vlan_rules:
        lines.append("5. SWITCHING & VLAN SPECIFICATIONS")
        lines.append("-" * 80)
        for r in vlan_rules:
            exp = r.expected_value or {}
            mode = exp.get("switchport_mode", "access")
            if mode == "trunk":
                lines.append(f"• {r.target_device} on {r.target_interface}: Mode TRUNK (Native VLAN {exp.get('trunk_native_vlan', 1)})")
            else:
                lines.append(f"• {r.target_device} on {r.target_interface}: Access Port in VLAN {exp.get('access_vlan', 1)}")
        lines.append("")

    # Section 6: Evaluation Checklist
    lines.append("6. RUBRIC & POINT BREAKDOWN")
    lines.append("-" * 80)
    for i, r in enumerate(criteria.rules, 1):
        lines.append(f"[{r.points:4.1f} pts] #{i:02d}: {r.description}")
    lines.append("")
    lines.append("=" * 80)
    lines.append("DO NOT MODIFY BELOW THIS LINE - MACHINE EVALUATION CRITERIA SPECIFICATION")
    lines.append("=" * 80)
    lines.append("--- CRITERIA SPEC START ---")
    lines.append(criteria.model_dump_json(indent=2))
    lines.append("--- CRITERIA SPEC END ---")
    lines.append("")

    return "\n".join(lines)


def parse_instructions_txt(content: str) -> EvaluationCriteria:
    """
    Parses an instructions.txt document (or raw JSON) and returns an EvaluationCriteria object.
    """
    if not content or not content.strip():
        raise ValueError("Instructions document is empty.")

    # Check for embedded specification block
    pattern = r"--- CRITERIA SPEC START ---\s*(.*?)\s*--- CRITERIA SPEC END ---"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        spec_json = match.group(1).strip()
        try:
            data = json.loads(spec_json)
            return EvaluationCriteria(**data)
        except Exception as e:
            raise ValueError(f"Failed to parse embedded criteria specification: {e}")

    # Fallback: Check if the entire file is valid JSON
    try:
        data = json.loads(content)
        return EvaluationCriteria(**data)
    except Exception:
        pass

    raise ValueError(
        "Invalid instructions file: Missing '--- CRITERIA SPEC START ---' marker. "
        "Please provide an instructions.txt file generated by the Teacher Studio."
    )
