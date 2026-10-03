# src/report_fields.py
"""
What a checkpoint expected, in words, for the linked report (spec 5.5).

Read from the rule the instructor's file produced and the policies in force,
so the text says what was actually graded: a cable type appears only when
cable types are graded, a process ID only when process IDs are. Called after
scoring; it cannot change a score. Never raises: a rubric written by a newer
build simply gets no expected text.
"""
from src.link_attributes import LINK_ATTRIBUTES
from src.models import EvaluationPolicies, EvaluationRule

_SECURITY = {
    "enable_secret": "enable secret configured",
    "password_encryption": "service password-encryption enabled",
    "vty_login": "Login required on the VTY lines",
}


def _cable_name(cable_type) -> str | None:
    # Same reduction as static/js/map/topology.js cableKind().
    t = str(cable_type or "").lower()
    if "console" in t or "rollover" in t:
        return "console"
    if "cross" in t:
        return "crossover"
    if "straight" in t:
        return "straight-through"
    return None


def _endpoint(device, interface) -> str:
    return f"{device or ''} {interface or ''}".strip()


def expected_text(rule: EvaluationRule, policies: EvaluationPolicies) -> str | None:
    try:
        return _expected_text(rule, policies)
    except Exception:
        return None


def _expected_text(rule: EvaluationRule, policies: EvaluationPolicies) -> str | None:
    if not isinstance(rule.expected_value, dict):
        return None
    exp = rule.expected_value
    category = rule.category

    if category == "device":
        return f"A device named {exp.get('display_name') or rule.target_device}"

    if category == "interface_ip":
        ip, cidr = exp.get("ip_address"), exp.get("cidr")
        if not ip:
            return None
        return f"{ip}/{cidr}" if cidr else ip

    if category == "interface_status":
        return "Enabled (no shutdown), up/up"

    if category == "cabling":
        a = _endpoint(exp.get("source_device", rule.target_device), exp.get("source_interface", rule.target_interface))
        b = _endpoint(exp.get("target_device"), exp.get("target_interface"))
        text = f"A cable from {a} to {b}"
        cable = _cable_name(exp.get("cable_type"))
        if cable and policies.strict_cable_type:
            text += f" ({cable})"
        return text

    if category == "link_agreement":
        attr = LINK_ATTRIBUTES.get(exp.get("attribute", ""))
        if attr is None:
            return None
        text = f"Both ends agree on the {attr.label}"
        reference = exp.get("reference_value")
        if policies.enforce_reference_link_values and attr.reference_enforceable and reference is not None:
            text += f": {attr.render(reference)}"
        return text

    if category == "relational_subnet":
        peer = _endpoint(exp.get("target_device"), exp.get("target_interface"))
        shared = f" shared with {peer}" if peer else ""
        prefix = exp.get("expected_prefixlen")
        if prefix is not None and policies.enforce_prefix_length:
            return f"A valid /{prefix} subnet{shared}, of your own design"
        return f"A valid subnet{shared}, of your own design"

    if category == "vlan_trunk":
        if exp.get("switchport_mode") == "trunk":
            # Native VLAN is graded here only when the instructor dictated it
            # (see the vlan_trunk branch of src/evaluator.py).
            if policies.enforce_reference_link_values:
                return f"802.1Q trunk, native VLAN {exp.get('trunk_native_vlan', 1)}"
            return "802.1Q trunk"
        return f"Access port in VLAN {exp.get('access_vlan', 1)}"

    if category == "gateway":
        return "A default gateway that is a router interface on its own subnet"

    if category == "routing":
        text = f"OSPF advertising networks into area {exp.get('area', 0)}"
        if not policies.allow_flexible_process_ids:
            text += f", process ID {exp.get('process_id', 1)}"
        return text

    if category == "security":
        return _SECURITY.get(exp.get("check_type"))

    if category == "documentation":
        return "An interface description"

    return None
