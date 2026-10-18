# src/topics/registry.py
"""
The topic registry.

A *topic* is what an instructor thinks in ("Static Routing", "VLANs &
Trunking"). A rule *category* is what the engine checks ("static_route",
"vlan_trunk"). Every category belongs to exactly one topic, which is how a
lab's points can be split by topic (weights.py) without touching grading.

Topics with gradeable=False are detected only: the Teacher Studio shows that
the reference uses them, but no rule checks them yet.

Detection is deterministic: each detector reads ParsedDevice.config_lines,
the stripped running-config. Detectors match explicit configuration only.
Lines IOS and Packet Tracer print in every config (`spanning-tree mode pvst`,
`spanning-tree extend system-id`, `no ipv6 cef`, `ip cef`) never count.

Adding a topic (each family gets its own spec):
  1. Parse what the grader needs into ParsedDevice / InterfaceData.
  2. Add the rule category to EvaluationRule.category.
  3. Write src/topics/<topic>.py with generate_rules() and evaluate().
     Handle dynamic subnetting and custom hostnames through EvalContext.
  4. In the topic's entry here: set categories, gradeable=True, generate
     and evaluate. Keep detect.
  5. Add a _TOPICS entry and a guidance handler in src/feedback.py.
  6. Add an instructions.txt section if students need a table.
  7. Add grader tests and at least one positive and one negative
     validation mutation.
  8. Update docs/SYSTEM.md sections 3.1 and 10.
"""
import re
from dataclasses import dataclass
from typing import Callable

from src.models import ParsedDevice, TopologyResult
from src.topics import static_routes

Detector = Callable[[ParsedDevice], bool]


@dataclass(frozen=True)
class Topic:
    key: str
    label: str
    categories: tuple[str, ...] = ()
    gradeable: bool = False
    detect: Detector | None = None
    # Grader hooks, set only for topics graded by a module in src/topics/.
    # Topics whose categories predate the registry are graded inline by
    # criteria_generator.py and evaluator.py and leave these as None.
    generate: Callable | None = None
    evaluate: Callable | None = None


def _config_matches(*patterns: str) -> Detector:
    compiled = [re.compile(p, re.IGNORECASE) for p in patterns]

    def detect(device: ParsedDevice) -> bool:
        return any(rx.search(line) for line in device.config_lines for rx in compiled)
    return detect


_SUBINTERFACE_DOT1Q = _config_matches(r"^encapsulation\s+dot1q\s+\d+")


def _inter_vlan_routing(device: ParsedDevice) -> bool:
    if _SUBINTERFACE_DOT1Q(device):
        return True
    # An addressed SVI routes between VLANs only when `ip routing` is on.
    # Without it, it is a layer-2 switch's management address.
    return device.has_ip_routing and any(
        re.match(r"^vlan\d+$", name, re.IGNORECASE) and intf.ip_address
        for name, intf in device.interfaces.items()
    )


TOPICS: tuple[Topic, ...] = (
    Topic("devices", "Device Presence", ("device",), gradeable=True),
    Topic("ip_addressing", "IP Addressing", ("interface_ip", "relational_subnet"), gradeable=True),
    Topic("interface_status", "Interface Status", ("interface_status",), gradeable=True),
    Topic("cabling", "Cabling", ("cabling",), gradeable=True),
    Topic("vlans_trunking", "VLANs & Trunking", ("vlan_trunk",), gradeable=True),
    Topic("ospf", "OSPF", ("routing",), gradeable=True),
    Topic("static_routing", "Static Routing", ("static_route",), gradeable=True,
          detect=_config_matches(r"^ip\s+route\s+\d"),
          generate=static_routes.generate_rules, evaluate=static_routes.evaluate),
    Topic("default_gateways", "Default Gateways", ("gateway",), gradeable=True),
    Topic("security_baseline", "Security Baseline", ("security",), gradeable=True),
    Topic("interface_descriptions", "Interface Descriptions", ("documentation",), gradeable=True),
    Topic("link_agreement", "Link Agreement", ("link_agreement",), gradeable=True),
    # --- detected only: each family below gets its own spec ---
    Topic("stp", "Spanning Tree", detect=_config_matches(
        r"^spanning-tree\s+mode\s+(rapid-pvst|mst)\b",
        r"^spanning-tree\s+vlan\s+[\d,\- ]+\s+(priority|root)\b",
        r"^spanning-tree\s+portfast\b",
        r"^spanning-tree\s+bpduguard\b")),
    Topic("etherchannel", "EtherChannel", detect=_config_matches(
        r"^channel-group\s+\d+", r"^interface\s+port-channel\s*\d+")),
    Topic("port_security", "Port Security", detect=_config_matches(
        r"^switchport\s+port-security\b")),
    Topic("hsrp", "HSRP", detect=_config_matches(
        r"^standby\s+(\d+\s+)?(ip|priority|preempt)\b")),
    Topic("dhcp", "DHCP", detect=_config_matches(
        r"^ip\s+dhcp\s+pool\b", r"^ip\s+dhcp\s+excluded-address\b", r"^ip\s+helper-address\b")),
    Topic("inter_vlan_routing", "Inter-VLAN Routing", detect=_inter_vlan_routing),
    Topic("acl", "Access Control Lists", detect=_config_matches(
        r"^access-list\s+\d+", r"^ip\s+access-list\s+(standard|extended)\b",
        r"^ip\s+access-group\b", r"^access-class\b")),
    Topic("nat", "NAT", detect=_config_matches(r"^ip\s+nat\s+(inside|outside|pool)\b")),
    Topic("ssh", "SSH", detect=_config_matches(
        r"^ip\s+ssh\s+version\b", r"^transport\s+input\s+.*\bssh\b")),
    Topic("eigrp", "EIGRP", detect=_config_matches(r"^router\s+eigrp\s+\d+")),
    Topic("rip", "RIP", detect=_config_matches(r"^router\s+rip\b")),
    Topic("ipv6", "IPv6", detect=_config_matches(
        r"^ipv6\s+unicast-routing\b", r"^ipv6\s+address\b", r"^ipv6\s+route\b", r"^ipv6\s+router\b")),
)

TOPICS_BY_KEY: dict[str, Topic] = {t.key: t for t in TOPICS}
_TOPIC_BY_CATEGORY: dict[str, Topic] = {c: t for t in TOPICS for c in t.categories}


def topic_for_category(category: str) -> Topic:
    """The topic that owns a rule category. KeyError for an unknown category."""
    return _TOPIC_BY_CATEGORY[category]


def detect_topics(topology: TopologyResult) -> dict[str, list[str]]:
    """Topic key -> sorted hostnames whose running-config shows that topic."""
    found: dict[str, list[str]] = {}
    for topic in TOPICS:
        if topic.detect is None:
            continue
        hosts = sorted(
            name for name, dev in topology.devices.items()
            if not dev.is_placeholder and topic.detect(dev)
        )
        if hosts:
            found[topic.key] = hosts
    return found
