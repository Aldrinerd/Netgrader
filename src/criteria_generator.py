# src/criteria_generator.py
"""
Evaluation Criteria & Lab Instructions Generation Engine.
Extracts reference rules from an instructor's Packet Tracer file or configuration bundle,
formats student lab assignment instructions (.txt), and parses them back for automated grading.
"""

import json
import re
from src.models import EvaluationCriteria, EvaluationPolicies, EvaluationRule, TopologyResult

# Rule points are stored to one decimal place, so all apportionment is done in
# tenths of a point using integers. This avoids float drift entirely.
_TENTHS = 10


def _normalize_rule_points(rules: list[EvaluationRule], target_total: float) -> None:
    """
    Rescale rule weights in place so they sum to exactly `target_total`.

    Uses largest-remainder (Hamilton) apportionment in tenths of a point.
    Every rule is guaranteed a strictly positive score whenever the target
    allows it, because a rule worth zero or fewer points corrupts grading:
    a negative weight means PASSING a checkpoint would lower a student's
    percentage.
    """
    if not rules or target_total <= 0:
        return

    total_tenths = int(round(target_total * _TENTHS))
    count = len(rules)

    # Degenerate case: fewer tenths than rules, so not every rule can be worth
    # something. Spread what exists as evenly as possible rather than going
    # negative, and let the caller's total stand.
    if total_tenths < count:
        base, remainder = divmod(total_tenths, count)
        for i, rule in enumerate(rules):
            rule.points = round((base + (1 if i < remainder else 0)) / _TENTHS, 1)
        return

    weights = [max(float(r.points), 0.0) for r in rules]
    weight_sum = sum(weights)
    if weight_sum <= 0:
        weights = [1.0] * count
        weight_sum = float(count)

    # Ideal share for each rule, floored, with a guaranteed minimum of one tenth.
    exact = [total_tenths * w / weight_sum for w in weights]
    allocation = [max(1, int(share)) for share in exact]

    # Hand out or claw back tenths until the allocation sums exactly to target.
    drift = total_tenths - sum(allocation)
    if drift > 0:
        # Largest fractional remainder gets the surplus tenths first.
        order = sorted(range(count), key=lambda i: exact[i] - int(exact[i]), reverse=True)
        for step in range(drift):
            allocation[order[step % count]] += 1
    elif drift < 0:
        # Over-allocated by the minimum floor: reclaim from the largest rules,
        # never dropping any rule below one tenth of a point.
        order = sorted(range(count), key=lambda i: allocation[i], reverse=True)
        step = 0
        while drift < 0:
            index = order[step % count]
            if allocation[index] > 1:
                allocation[index] -= 1
                drift += 1
            step += 1
            if step > count * total_tenths + count:  # safety valve
                break

    for rule, tenths in zip(rules, allocation):
        rule.points = round(tenths / _TENTHS, 1)


def generate_criteria_from_topology(
    topology: TopologyResult,
    lab_title: str = "Packet Tracer Lab Assignment",
    lab_description: str = "",
    target_total_points: float = 100.0,
    policies: EvaluationPolicies | None = None
) -> EvaluationCriteria:
    """
    Generates an EvaluationCriteria object with discrete grading rules extracted
    from an instructor's gold-standard reference topology according to evaluation policies.
    """
    if policies is None:
        policies = EvaluationPolicies()

    raw_rules: list[EvaluationRule] = []
    seen_rule_ids: set[str] = set()

    def add_rule(r: EvaluationRule):
        if r.rule_id not in seen_rule_ids:
            seen_rule_ids.add(r.rule_id)
            raw_rules.append(r)

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

        # Security Baseline Rules (if enabled)
        if policies.grade_security_baseline and dev.device_type in ("router", "switch", "l3_switch"):
            add_rule(EvaluationRule(
                rule_id=f"sec_secret_{dev.hostname.lower()}",
                category="security",
                description=f"Configure encrypted privileged EXEC password ('enable secret') on {dev_name}",
                points=4.0,
                target_device=dev.hostname,
                expected_value={"check_type": "enable_secret"}
            ))
            add_rule(EvaluationRule(
                rule_id=f"sec_pwenc_{dev.hostname.lower()}",
                category="security",
                description=f"Enable Cisco password encryption service ('service password-encryption') on {dev_name}",
                points=3.0,
                target_device=dev.hostname,
                expected_value={"check_type": "password_encryption"}
            ))
            add_rule(EvaluationRule(
                rule_id=f"sec_vty_{dev.hostname.lower()}",
                category="security",
                description=f"Secure Virtual Terminal lines with login authentication ('line vty 0 4') on {dev_name}",
                points=3.0,
                target_device=dev.hostname,
                expected_value={"check_type": "vty_login"}
            ))

        # Default Gateway Rule (if enabled). Generated independently of the
        # addressing mode so the policy is meaningful under strict addressing too.
        if policies.verify_default_gateways and dev.default_gateway and dev.device_type in ("host", "switch", "l3_switch"):
            add_rule(EvaluationRule(
                rule_id=f"gw_{dev.hostname.lower()}",
                category="gateway",
                description=f"Configure a working default gateway on {dev_name}",
                points=5.0,
                target_device=dev.hostname,
                expected_value={
                    "default_gateway": dev.default_gateway,
                    "device_type": dev.device_type,
                }
            ))

        # Routing Rules: one per OSPF area advertised by the reference device.
        # The process ID itself is only enforced when allow_flexible_process_ids is off.
        for proc in dev.ospf_processes:
            areas = {
                n.get("area") for n in proc.get("networks", [])
                if isinstance(n, dict) and n.get("area") is not None
            }
            for area in sorted(areas):
                add_rule(EvaluationRule(
                    rule_id=f"ospf_{dev.hostname.lower()}_area{area}",
                    category="routing",
                    description=f"Advertise networks into OSPF Area {area} on {dev_name}",
                    points=8.0,
                    target_device=dev.hostname,
                    expected_value={
                        "protocol": "ospf",
                        "area": area,
                        "process_id": proc.get("process_id", 1),
                    }
                ))

        # Interface Operational Status & IP / Relational Subnet Rules
        for intf_name, intf in dev.interfaces.items():
            safe_intf = intf_name.replace("/", "_").replace(" ", "_").replace(".", "_")

            # Interface Description Documentation Rule (if enabled)
            if policies.grade_interface_descriptions and (intf.ip_address or intf.switchport_mode):
                add_rule(EvaluationRule(
                    rule_id=f"desc_{dev.hostname.lower()}_{safe_intf.lower()}",
                    category="documentation",
                    description=f"Configure meaningful interface description label on {dev_name} {intf_name}",
                    points=2.0,
                    target_device=dev.hostname,
                    target_interface=intf_name,
                    expected_value={"require_description": True}
                ))

            if intf.ip_address:
                # If Dynamic Subnetting is NOT enabled, create strict IP rules
                if not policies.allow_dynamic_subnetting:
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

                # Operational status (no shutdown)
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

            # VLAN & Switchport Rules
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

    # 2. Physical Cabling & Relational Subnet Rules
    seen_link_pairs = set()
    covered_l3_interfaces = set()

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

        # Dynamic Relational Subnet Rule generation for L3 connected pairs or host connections
        if policies.allow_dynamic_subnetting:
            src_dev_obj = topology.devices.get(src)
            tgt_dev_obj = topology.devices.get(tgt)
            if src_dev_obj and tgt_dev_obj:
                src_intf_obj = src_dev_obj.interfaces.get(link.source_interface)
                tgt_intf_obj = tgt_dev_obj.interfaces.get(link.target_interface)
                has_src_ip = src_intf_obj and src_intf_obj.ip_address
                has_tgt_ip = tgt_intf_obj and tgt_intf_obj.ip_address

                if has_src_ip and has_tgt_ip:
                    covered_l3_interfaces.add((src, link.source_interface))
                    covered_l3_interfaces.add((tgt, link.target_interface))
                    expected_cidr = src_intf_obj.cidr or 30
                    add_rule(EvaluationRule(
                        rule_id=f"rel_subnet_{src.lower()}_{safe_src_intf.lower()}__to__{tgt.lower()}_{safe_tgt_intf.lower()}",
                        category="relational_subnet",
                        description=f"Dynamic Subnet: Configure valid mutual /{expected_cidr} subnet between {src} ({link.source_interface}) and {tgt} ({link.target_interface})",
                        points=12.0,
                        target_device=src,
                        target_interface=link.source_interface,
                        expected_value={
                            "source_device": src,
                            "source_interface": link.source_interface,
                            "target_device": tgt,
                            "target_interface": link.target_interface,
                            "expected_prefixlen": expected_cidr,
                            "link_type": "point_to_point" if expected_cidr == 30 else "broadcast_lan"
                        }
                    ))
                elif has_src_ip or has_tgt_ip:
                    l3_dev = src if has_src_ip else tgt
                    l3_intf = link.source_interface if has_src_ip else link.target_interface
                    l3_obj = src_intf_obj if has_src_ip else tgt_intf_obj
                    l2_dev = tgt if has_src_ip else src
                    l2_intf = link.target_interface if has_src_ip else link.source_interface
                    safe_l3_intf = l3_intf.replace("/", "_").replace(" ", "_")
                    cidr_val = l3_obj.cidr or 24

                    covered_l3_interfaces.add((l3_dev, l3_intf))
                    add_rule(EvaluationRule(
                        rule_id=f"rel_subnet_{l3_dev.lower()}_{safe_l3_intf.lower()}",
                        category="relational_subnet",
                        description=f"Dynamic Subnet: Configure valid /{cidr_val} subnet on {l3_dev} ({l3_intf}) connected to {l2_dev} ({l2_intf})",
                        points=10.0,
                        target_device=l3_dev,
                        target_interface=l3_intf,
                        expected_value={
                            "source_device": l3_dev,
                            "source_interface": l3_intf,
                            "target_device": l2_dev,
                            "target_interface": l2_intf,
                            "expected_prefixlen": cidr_val,
                            "link_type": "broadcast_lan"
                        }
                    ))

    # Also catch any standalone/unlinked L3 interfaces under dynamic subnetting
    if policies.allow_dynamic_subnetting:
        for hostname, dev in topology.devices.items():
            if dev.is_placeholder:
                continue
            for intf_name, intf in dev.interfaces.items():
                if intf.ip_address and (hostname, intf_name) not in covered_l3_interfaces:
                    covered_l3_interfaces.add((hostname, intf_name))
                    safe_intf = intf_name.replace("/", "_").replace(" ", "_").replace(".", "_")
                    cidr_val = intf.cidr or 24
                    add_rule(EvaluationRule(
                        rule_id=f"rel_subnet_{hostname.lower()}_{safe_intf.lower()}",
                        category="relational_subnet",
                        description=f"Dynamic Subnet: Configure valid /{cidr_val} IPv4 subnet on {dev.display_name or hostname} ({intf_name})",
                        points=10.0,
                        target_device=hostname,
                        target_interface=intf_name,
                        expected_value={
                            "source_device": hostname,
                            "source_interface": intf_name,
                            "expected_prefixlen": cidr_val,
                            "link_type": "point_to_point" if cidr_val == 30 else "broadcast_lan"
                        }
                    ))

    # Point Normalization so total equals target_total_points (e.g. 100.0 pts)
    if raw_rules:
        _normalize_rule_points(raw_rules, target_total_points)

    ref_summary = {
        "device_count": len([d for d in topology.devices.values() if not d.is_placeholder]),
        "link_count": len(topology.links),
        "rule_count": len(raw_rules),
        "ip_count": len([r for r in raw_rules if r.category in ("interface_ip", "relational_subnet")]),
        "policy_summary": policies.model_dump()
    }

    return EvaluationCriteria(
        lab_title=lab_title,
        lab_description=lab_description or "Configure physical cabling, IP addressing, and operational states according to instructor policies.",
        total_points=target_total_points,
        policies=policies,
        rules=raw_rules,
        reference_summary=ref_summary
    )


def format_criteria_to_instructions_txt(criteria: EvaluationCriteria) -> str:
    """
    Formats the evaluation criteria into a clean, human-readable student lab instructions document
    with policy indicators and an embedded machine-verifiable criteria schema at the end.
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

    # Instructor Policy Summary
    p = criteria.policies
    lines.append("2. INSTRUCTOR EVALUATION POLICIES")
    lines.append("-" * 80)
    lines.append(f"• Dynamic Subnetting     : {'ENABLED (Custom IP schemes permitted; relational mutual subnets checked)' if p.allow_dynamic_subnetting else 'STRICT (Exact assigned IP addresses required)'}")
    lines.append(f"• Prefix Enforcement     : {'ENABLED (Prefix lengths /30, /24 must match)' if p.enforce_prefix_length else 'FLEXIBLE'}")
    lines.append(f"• Default Gateway Check  : {'ENABLED (Host/Switch gateway must match router subnet)' if p.verify_default_gateways else 'DISABLED'}")
    lines.append(f"• Hostname Matching      : {'FLEXIBLE (Matched by topological role & degree)' if p.allow_custom_hostnames else 'STRICT (Exact hostname required)'}")
    lines.append(f"• Interface Speed Class  : {'FLEXIBLE (Equivalent ports accepted)' if not p.strict_port_matching else 'STRICT (Exact port numbering)'}")
    lines.append(f"• Cabling Media / Auto-M : {'FLEXIBLE (Auto-MDIX copper equivalence accepted)' if not p.strict_cable_type else 'STRICT (Exact cable types required)'}")
    lines.append(f"• Routing Process IDs    : {'FLEXIBLE (Locally significant IDs ignored; Area/adjacencies checked)' if p.allow_flexible_process_ids else 'STRICT'}")
    lines.append(f"• Security Baseline      : {'GRADED (enable secret, service pw-enc, vty required)' if p.grade_security_baseline else 'NOT GRADED'}")
    lines.append(f"• Interface Descriptions : {'GRADED (Descriptive interface labels required)' if p.grade_interface_descriptions else 'NOT GRADED'}")
    lines.append("")

    # Addressing Section
    if p.allow_dynamic_subnetting:
        rel_rules = [r for r in criteria.rules if r.category == "relational_subnet"]
        lines.append("3. DYNAMIC & RELATIONAL SUBNETTING POLICY")
        lines.append("-" * 80)
        lines.append("You are free to design and apply your own custom IPv4 subnetting plan subject to the following rules:")
        lines.append(" 1. Mutual Subnet: Connected device interfaces must share the same IPv4 network address.")
        lines.append(" 2. Host Uniqueness: IP addresses on each link must be unique (no IP collisions).")
        if p.enforce_prefix_length:
            lines.append(" 3. Prefix Length: Each link must use the specified CIDR prefix length (e.g. /30 for P2P links, /24 for LANs).")
        lines.append("")
        lines.append(f"{'Endpoint A':<22} | {'Endpoint B':<22} | {'Required CIDR':<15} | {'Link Type':<15}")
        lines.append("-" * 80)
        for r in rel_rules:
            exp = r.expected_value or {}
            ep_a = f"{exp.get('source_device')}:{exp.get('source_interface')}"
            ep_b = f"{exp.get('target_device')}:{exp.get('target_interface')}"
            cidr = f"/{exp.get('expected_prefixlen', 24)}"
            ltype = exp.get('link_type', 'point_to_point')
            lines.append(f"{ep_a:<22} | {ep_b:<22} | {cidr:<15} | {ltype:<15}")
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

    # Cabling Table
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

    # VLAN & Switchport Requirements
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

    # Evaluation Checklist
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

    pattern = r"--- CRITERIA SPEC START ---\s*(.*?)\s*--- CRITERIA SPEC END ---"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        spec_json = match.group(1).strip()
        try:
            data = json.loads(spec_json)
            return EvaluationCriteria(**data)
        except Exception as e:
            raise ValueError(f"Failed to parse embedded criteria specification: {e}")

    try:
        data = json.loads(content)
        return EvaluationCriteria(**data)
    except Exception:
        pass

    raise ValueError(
        "Invalid instructions file: Missing '--- CRITERIA SPEC START ---' marker. "
        "Please provide an instructions.txt file generated by the Teacher Studio."
    )
