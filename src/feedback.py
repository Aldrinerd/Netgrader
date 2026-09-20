# src/feedback.py
"""
Pedagogical Guidance Layer (Phase A - deterministic).

The rule engine decides WHAT a student missed. This module explains WHY the
requirement exists and HOW to investigate it, without ever touching a score.

Everything here is deterministic, instant and offline. A local LLM may later
rephrase this text (Phase B), but it can never replace it: these templates stay
as the permanent fallback that keeps the tool fully functional with no model
installed, and they are the seed corpus for any fine-tuning study.

Coverage is total by construction. EvaluationRule.category is a closed set, so
every finding the engine can produce lands on one of the handlers below.

Pedagogical stance: name the concept and the command to investigate with, but
do not hand over a paste-ready answer line. Students are told what to check and
why, not given the fix to copy.
"""

from src.models import EvaluationReport, RuleResult, StudyTopic

# Concept label and why it matters, per rule category. Used for study topics.
_TOPICS: dict[str, tuple[str, str]] = {
    "device": (
        "Device naming and topology completeness",
        "Grading, documentation and troubleshooting all rely on devices being present and named as specified.",
    ),
    "interface_ip": (
        "IPv4 addressing and subnet masks",
        "An address in the wrong subnet cannot reach its neighbour, no matter how the rest of the network is built.",
    ),
    "relational_subnet": (
        "Subnet design and VLSM",
        "Two ends of a link must sit in the same subnet, and separate network segments must not reuse one.",
    ),
    "interface_status": (
        "Interface administrative state",
        "A correctly addressed interface still forwards nothing while it is administratively down.",
    ),
    "cabling": (
        "Physical cabling and port selection",
        "The logical configuration cannot work if the cable lands on a different port than the design specifies.",
    ),
    "vlan_trunk": (
        "VLANs, access ports and 802.1Q trunking",
        "Access and trunk misconfiguration silently breaks connectivity between VLANs.",
    ),
    "routing": (
        "Dynamic routing and OSPF areas",
        "Without the correct networks advertised into the right area, remote subnets never become reachable.",
    ),
    "gateway": (
        "Default gateways",
        "A host with no valid gateway can reach its own subnet and nothing beyond it.",
    ),
    "security": (
        "Device hardening baseline",
        "Unprotected privileged access and plaintext passwords are the most commonly exploited lab-to-production habit.",
    ),
    "documentation": (
        "Interface documentation",
        "Undocumented interfaces are the leading cause of slow fault isolation in a real network.",
    ),
}

_FALLBACK_TOPIC = (
    "Lab requirements",
    "This checkpoint is part of the instructor's specification for the lab.",
)


def _lower(value: str | None) -> str:
    return (value or "").lower()


def _where(result: RuleResult) -> str:
    """Human-readable location of the failure."""
    if result.target_interface:
        return f"{result.target_device} {result.target_interface}"
    return result.target_device


def _explain_device(result: RuleResult) -> str:
    return (
        f"The rubric expects a device named '{result.target_device}' in this topology. "
        "It was not found. Either the device is missing, or its hostname differs from the "
        "one the lab specifies. Check the hostname with 'show running-config | include hostname'. "
        "If your instructor allowed custom device names, this checkpoint matches devices by "
        "their role and connections instead, which means the device's cabling may be what "
        "differs rather than its name."
    )


def _explain_interface_ip(result: RuleResult) -> str:
    actual = _lower(result.actual_value)
    where = _where(result)

    if "no ip configured" in actual or "unassigned" in actual:
        return (
            f"No IPv4 address is configured on {where}. An interface without an address cannot "
            "participate in routing at all. Enter interface configuration mode and assign the "
            "address and mask from the lab's addressing table, then verify with "
            "'show ip interface brief'."
        )
    if "missing" in actual:
        return (
            f"The interface {result.target_interface} was not found on {result.target_device}. "
            "Confirm you configured the port the addressing table names. Interface numbering "
            "differs between router models, so check 'show ip interface brief' to see which "
            "ports this device actually has."
        )
    # Address present but wrong. Distinguish a mask-only error from a wrong network.
    if "subnet mask" in _lower(result.feedback) or "prefix" in _lower(result.feedback):
        return (
            f"The address on {where} is correct but the mask is not. The mask decides how much "
            "of the address identifies the network, so the wrong mask puts this interface in a "
            "different subnet than intended even though the address digits look right. "
            "Re-read the prefix length in the addressing table and recalculate the range it covers."
        )
    return (
        f"The address configured on {where} is not the one the addressing table assigns. "
        "Compare your value against the table digit by digit, including the mask. A neighbour "
        "in a different subnet will not be reachable even when both interfaces are up. "
        "Verify with 'show ip interface brief'."
    )


def _explain_relational_subnet(result: RuleResult) -> str:
    feedback = _lower(result.feedback)
    where = _where(result)

    if "different subnets" in feedback or "subnet mismatch" in feedback:
        return (
            "Both ends of a link must be in the same subnet to communicate. These two interfaces "
            "are in different ones, so this link cannot pass traffic. Work out the network address "
            "for each end from its address and mask, and confirm they match."
        )
    if "already used" in feedback:
        return (
            "This subnet is already in use on a different network segment. Each segment needs its "
            "own distinct subnet, otherwise routing becomes ambiguous and traffic can be sent to "
            "the wrong place. Re-check your subnet plan for overlapping ranges."
        )
    if "prefix" in feedback or "cidr" in feedback:
        return (
            "The two ends agree on the subnet, but the prefix length is not the one required. "
            "A point-to-point link between two routers needs only two usable addresses, which is "
            "what a /30 provides; using a wider mask there wastes a large block of addresses. "
            "Recalculate the prefix the lab specifies for this type of link."
        )
    if "collision" in feedback or "identical ip" in feedback:
        return (
            "Both devices on this link are configured with the same IP address. Every host in a "
            "subnet needs a unique address; duplicates cause unpredictable delivery and errors. "
            "Assign each end a different usable address from the range."
        )
    if "gateway" in feedback:
        return _explain_gateway(result)
    return (
        f"The addressing on {where} does not satisfy the relational rules for this link. "
        "Your instructor allowed you to design your own scheme, so the exact address is not "
        "checked, but both ends must share a subnet, use the required prefix length, and hold "
        "unique addresses."
    )


def _explain_interface_status(result: RuleResult) -> str:
    where = _where(result)
    if "missing" in _lower(result.actual_value):
        return (
            f"The interface {result.target_interface} was not found on {result.target_device}, so "
            "its state could not be checked. Confirm you configured the port the lab specifies."
        )
    return (
        f"The interface {where} is administratively down. Cisco router interfaces start in this "
        "state and stay there until they are explicitly enabled, so a correct IP address alone is "
        "not enough to pass traffic. Enable the interface from interface configuration mode, then "
        "confirm the result with 'show ip interface brief' -- you are looking for 'up/up'."
    )


def _explain_cabling(result: RuleResult) -> str:
    actual = _lower(result.actual_value)
    if "cabling error" in actual or "cable type" in _lower(result.feedback):
        return (
            "The two devices are connected, but with the wrong cable type. Straight-through cable "
            "joins unlike devices such as a switch to a router; crossover joins like devices such "
            "as switch to switch. Modern equipment often compensates automatically with Auto-MDIX, "
            "which is why this may still appear to work in the simulator, but the lab requires the "
            "correct media to be selected."
        )
    return (
        f"The required connection involving {_where(result)} was not found. Check that the cable "
        "lands on the exact ports the topology diagram specifies. Confirm what is actually "
        "connected with 'show cdp neighbors', which lists each neighbour and the local and remote "
        "port joining you."
    )


def _explain_vlan_trunk(result: RuleResult) -> str:
    feedback = _lower(result.feedback)
    where = _where(result)
    if "trunk" in feedback or "native" in feedback:
        return (
            f"The trunking configuration on {where} does not match the specification. A trunk "
            "carries several VLANs over one link and tags them, and the native VLAN must agree on "
            "both ends or traffic in it will be dropped. Inspect the link with "
            "'show interfaces trunk' and compare both sides."
        )
    return (
        f"The switchport configuration on {where} does not match the specification. An access port "
        "belongs to exactly one VLAN, and a port left in the default VLAN is a common cause of a "
        "host that cannot reach anything. Check the assignment with 'show vlan brief'."
    )


def _explain_routing(result: RuleResult) -> str:
    return (
        f"The required OSPF configuration is missing or incomplete on {result.target_device}. "
        "A router only advertises the networks you explicitly place into an area, so a subnet that "
        "is addressed correctly can still be unreachable from elsewhere. Check which networks are "
        "advertised with 'show ip protocols', confirm neighbours have formed with "
        "'show ip ospf neighbor', and confirm the learned routes with 'show ip route ospf'. "
        "If your instructor allowed flexible process IDs, the number after 'router ospf' is not "
        "graded -- the area and the advertised networks are."
    )


def _explain_gateway(result: RuleResult) -> str:
    feedback = _lower(result.feedback)
    if "no default gateway" in feedback or "no default gateway" in _lower(result.actual_value or ""):
        return (
            f"No default gateway is configured on {result.target_device}. Without one, the device "
            "can reach hosts in its own subnet but nothing beyond it, because it has no idea where "
            "to send traffic destined elsewhere. The gateway is the address of the router interface "
            "on this device's own network."
        )
    if "outside" in feedback:
        return (
            f"The default gateway on {result.target_device} is not inside its own subnet. A gateway "
            "must be an address the device can reach directly, which means it has to fall within "
            "the range its own address and mask define. Recalculate that range and compare."
        )
    return (
        f"The default gateway on {result.target_device} does not match a router interface on its "
        "network. The gateway must be the actual address of the router serving this subnet. "
        "Compare it against the router's interface address on this segment."
    )


def _explain_security(result: RuleResult) -> str:
    feedback = _lower(result.description) + " " + _lower(result.feedback)
    if "secret" in feedback:
        return (
            f"{result.target_device} has no encrypted privileged-EXEC password. Without it anyone "
            "reaching the console gains full configuration access. Note that the 'secret' form "
            "stores a hash while the older 'password' form stores recoverable text, which is why "
            "the lab requires the former."
        )
    if "encryption" in feedback:
        return (
            f"Password encryption is not enabled on {result.target_device}. Passwords entered "
            "elsewhere in the configuration are stored as readable plaintext, so anyone who obtains "
            "a copy of the config obtains the passwords. One global service command scrambles them."
        )
    if "vty" in feedback or "virtual terminal" in feedback:
        return (
            f"The virtual terminal lines on {result.target_device} are not secured. VTY lines accept "
            "remote sessions, so leaving them without authentication exposes the device to anyone "
            "with network reachability. Configure the VTY range to require a login."
        )
    return (
        f"The security baseline on {result.target_device} is incomplete. Review the lab's hardening "
        "requirements for privileged access, password storage and remote login."
    )


def _explain_documentation(result: RuleResult) -> str:
    return (
        f"The interface {_where(result)} has no description. Descriptions name what is on the other "
        "end of a link, and in a real fault they are often the fastest way to work out what an "
        "interface does without tracing the cable. Add one from interface configuration mode."
    )


_HANDLERS = {
    "device": _explain_device,
    "interface_ip": _explain_interface_ip,
    "relational_subnet": _explain_relational_subnet,
    "interface_status": _explain_interface_status,
    "cabling": _explain_cabling,
    "vlan_trunk": _explain_vlan_trunk,
    "routing": _explain_routing,
    "gateway": _explain_gateway,
    "security": _explain_security,
    "documentation": _explain_documentation,
}


def explain(result: RuleResult) -> str | None:
    """
    Explain a failed checkpoint. Returns None for a passed one.

    Never raises: guidance is presentational, and a missing explanation must
    never interfere with a delivered grade.
    """
    if result.passed:
        return None
    handler = _HANDLERS.get(result.category)
    if handler is None:
        return (
            f"This checkpoint was not satisfied on {_where(result)}. "
            "Review the lab instructions for this requirement."
        )
    try:
        return handler(result)
    except Exception:
        return (
            f"This checkpoint was not satisfied on {_where(result)}. "
            "Review the lab instructions for this requirement."
        )


def study_topics(results: list[RuleResult]) -> list[StudyTopic]:
    """Concepts to revisit, ranked by points lost."""
    buckets: dict[str, dict] = {}
    for result in results:
        if result.passed:
            continue
        topic, why = _TOPICS.get(result.category, _FALLBACK_TOPIC)
        entry = buckets.setdefault(
            topic, {"why": why, "points": 0.0, "count": 0}
        )
        entry["points"] += max(0.0, result.points_possible - result.points_earned)
        entry["count"] += 1

    ordered = sorted(buckets.items(), key=lambda kv: kv[1]["points"], reverse=True)
    return [
        StudyTopic(
            topic=topic,
            why_it_matters=data["why"],
            points_lost=round(data["points"], 1),
            checkpoints_failed=data["count"],
        )
        for topic, data in ordered
    ]


def attach_guidance(report: EvaluationReport) -> EvaluationReport:
    """
    Populate guidance and study topics on a finished report.

    Runs strictly after scoring. It reads the report and adds explanation; it
    does not and must not alter any score field.
    """
    for result in report.results:
        result.guidance = explain(result)
    report.study_topics = study_topics(report.results)
    return report


def class_analysis(reports_missed: list[list[str]], categories: list[list[str]]) -> dict:
    """
    Aggregate failure patterns across a batch, for instructor-facing analysis.

    Deliberately takes only failure descriptions and categories: no student
    names and no configuration text. That keeps the aggregate compliant with
    R.A. 10173 and small enough for a local model to reason over (Phase B).
    """
    total = len(categories)
    counts: dict[str, int] = {}
    for student_categories in categories:
        for category in set(student_categories):
            counts[category] = counts.get(category, 0) + 1

    concepts = []
    for category, affected in sorted(counts.items(), key=lambda kv: kv[1], reverse=True):
        topic, why = _TOPICS.get(category, _FALLBACK_TOPIC)
        concepts.append({
            "topic": topic,
            "why_it_matters": why,
            "students_affected": affected,
            "share_of_class": round(affected / total, 3) if total else 0.0,
        })

    return {"submissions_analysed": total, "concepts": concepts}
