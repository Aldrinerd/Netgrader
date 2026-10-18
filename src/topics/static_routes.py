# src/topics/static_routes.py
"""
Static-route grading.

One rule per reference device that has static routes. The rule lists every
route the reference configures, resolved to two things a student's network
can be compared on:

  destination  the network the route reaches. Under dynamic subnetting the
               student picks their own addresses, so the destination is also
               recorded as the reference interface that owns that network
               (dest_device / dest_interface) and compared through the
               student's counterpart of that interface.
  neighbor     the device the route hands traffic to (via_device), from the
               next-hop IP or from the far end of the exit interface's link.

A student's route satisfies a requirement when it reaches the destination
and hands traffic to the counterpart of the same neighbor. Partial coverage
earns proportional credit but does not pass, as for OSPF.

A reference route whose neighbor cannot be resolved is skipped and reported
as a warning: a rule the instructor's own file fails would put 100% out of
reach for the whole class.
"""
import ipaddress

from src.models import (
    DiscoveredLink,
    EvaluationPolicies,
    EvaluationRule,
    InterfaceData,
    ParsedDevice,
    RouteEntry,
    TopologyResult,
)
from src.parsers import normalize_interface_name
from src.topics import EvalContext, RuleOutcome

BASE_POINTS = 8.0
DEFAULT_ROUTE = ipaddress.ip_network("0.0.0.0/0")


def is_static(route: RouteEntry) -> bool:
    """`ip route` lines parse as "S"; `show ip route` marks the default "S*"."""
    return route.protocol.rstrip("*").upper() == "S"


def destination_label(route: dict, dynamic: bool) -> str:
    """How a required route's destination is named to students."""
    if route.get("is_default"):
        return "default route (0.0.0.0/0)"
    if dynamic and route.get("dest_device"):
        return f"the LAN on {route['dest_device']} {route['dest_interface']}"
    return f"{route['network']}/{route['cidr']}"


def _network_of(intf: InterfaceData | None) -> ipaddress.IPv4Network | None:
    if intf is None or not intf.ip_address:
        return None
    prefix = intf.cidr if intf.cidr is not None else intf.subnet_mask
    if prefix is None:
        return None
    try:
        return ipaddress.ip_interface(f"{intf.ip_address}/{prefix}").network
    except ValueError:
        return None


def _route_network(route: RouteEntry) -> ipaddress.IPv4Network | None:
    try:
        return ipaddress.ip_network(f"{route.network}/{route.cidr}", strict=False)
    except ValueError:
        return None


def _same_interface(a: str, b: str) -> bool:
    return normalize_interface_name(a).lower() == normalize_interface_name(b).lower()


def _ip_owner(devices: dict[str, ParsedDevice], ip: str) -> tuple[str, str] | None:
    """(hostname, interface) that carries `ip`, ignoring placeholders."""
    for hostname, dev in devices.items():
        if dev.is_placeholder:
            continue
        for name, intf in dev.interfaces.items():
            if intf.ip_address == ip:
                return hostname, name
    return None


def _far_end(links: list[DiscoveredLink], device: str, interface: str) -> tuple[str, str] | None:
    """The (device, interface) at the other end of the link on `interface`."""
    for link in links:
        if link.source_device == device and _same_interface(link.source_interface, interface):
            return link.target_device, link.target_interface
        if link.target_device == device and _same_interface(link.target_interface, interface):
            return link.source_device, link.source_interface
    return None


def _destination_owner(topology: TopologyResult, network: ipaddress.IPv4Network,
                       routing_device: str) -> tuple[str, str] | None:
    """
    The reference interface whose network is the route's destination.
    Prefers a router or L3 switch interface (the LAN's gateway) over a host
    on the same LAN, and never picks the routing device itself.
    """
    candidates = []
    for hostname, dev in topology.devices.items():
        if dev.is_placeholder or hostname == routing_device:
            continue
        for name, intf in dev.interfaces.items():
            if _network_of(intf) == network:
                rank = 0 if dev.device_type in ("router", "l3_switch") else 1
                candidates.append((rank, hostname, name))
    if not candidates:
        return None
    _, hostname, name = min(candidates)
    return hostname, name


def _resolve_neighbor(topology: TopologyResult, hostname: str,
                      route: RouteEntry) -> tuple[str, str, str] | str:
    """(via_device, via_interface, style), or the reason the route cannot be graded."""
    if route.next_hop:
        try:
            hop = ipaddress.ip_address(route.next_hop)
        except ValueError:
            return f"next hop {route.next_hop} is not a valid address"
        owner = _ip_owner(topology.devices, route.next_hop)
        if owner is None:
            return f"next hop {route.next_hop} belongs to no device"
        if owner[0] == hostname:
            return f"next hop {route.next_hop} is one of {hostname}'s own addresses"
        # A recursive next hop would fail the grader's directly-connected
        # check for an identical student, so it cannot become a requirement.
        device = topology.devices[hostname]
        if not any(net is not None and hop in net for net in map(_network_of, device.interfaces.values())):
            return f"next hop {route.next_hop} is not on a network directly connected to {hostname}"
        return owner[0], owner[1], "next_hop"
    if route.outgoing_interface:
        far = _far_end(topology.links, hostname, route.outgoing_interface)
        if far is None:
            return f"exit interface {route.outgoing_interface} has no link"
        far_dev = topology.devices.get(far[0])
        if far_dev is None or far_dev.is_placeholder:
            return f"exit interface {route.outgoing_interface} leads to an unidentified device"
        return far[0], far[1], "exit_interface"
    return "it has no next hop or exit interface"


def generate_rules(topology: TopologyResult,
                   policies: EvaluationPolicies) -> tuple[list[EvaluationRule], list[str]]:
    """
    One static_route rule per reference device with static routes, plus a
    warning for each reference route that could not be graded. `policies` is
    unused here (destinations are mapped at grading time); every grader
    module takes it so the registry can call them all the same way.
    """
    rules: list[EvaluationRule] = []
    warnings: list[str] = []
    for hostname, dev in topology.devices.items():
        if dev.is_placeholder:
            continue
        required: list[dict] = []
        seen: set[tuple[str, str]] = set()
        for route in dev.routes:
            if not is_static(route):
                continue
            network = _route_network(route)
            if network is None:
                continue
            resolved = _resolve_neighbor(topology, hostname, route)
            if isinstance(resolved, str):
                warnings.append(f"{hostname}: static route to {network} was not graded because {resolved}.")
                continue
            via_device, via_interface, style = resolved
            key = (str(network), via_device)
            if key in seen:
                continue   # `ip route` and `show ip route` both list it
            seen.add(key)
            is_default = network == DEFAULT_ROUTE
            dest = None if is_default else _destination_owner(topology, network, hostname)
            required.append({
                "network": str(network.network_address),
                "cidr": network.prefixlen,
                "is_default": is_default,
                "dest_device": dest[0] if dest else None,
                "dest_interface": dest[1] if dest else None,
                "via_device": via_device,
                "via_interface": via_interface,
                "style": style,
            })
        if not required:
            continue
        name = dev.display_name or hostname
        count = len(required)
        rules.append(EvaluationRule(
            rule_id=f"static_{hostname.lower()}",
            category="static_route",
            description=f"Configure static routes on {name} ({count} destination{'s' if count != 1 else ''})",
            points=BASE_POINTS,
            target_device=hostname,
            expected_value={"device_type": dev.device_type, "routes": required},
        ))
    return rules, warnings


def _expected_destination(req: dict, ctx: EvalContext) -> tuple[ipaddress.IPv4Network | None, str | None]:
    """(network the student's route must reach, or None for any; a problem to report, or None)."""
    if req.get("is_default"):
        return DEFAULT_ROUTE, None
    if not ctx.policies.allow_dynamic_subnetting:
        return ipaddress.ip_network(f"{req['network']}/{req['cidr']}"), None
    if not req.get("dest_device"):
        return None, None   # a summary that matches no interface: only the neighbor is checked
    dest_dev = ctx.find_device(req["dest_device"])
    if dest_dev is None or dest_dev.is_placeholder:
        return None, (f"the destination network on {req['dest_device']} cannot be checked "
                      f"because {req['dest_device']} is missing")
    network = _network_of(ctx.find_interface(dest_dev, req["dest_interface"]))
    if network is None:
        return None, f"the destination LAN on {req['dest_device']} {req['dest_interface']} has no address"
    return network, None


def _wrong_neighbor(route: RouteEntry, dev: ParsedDevice, neighbor: ParsedDevice,
                    ctx: EvalContext, subject: str, via: str) -> str | None:
    """None when `route` hands traffic to `neighbor`, else what is wrong with it."""
    if route.next_hop:
        try:
            hop = ipaddress.ip_address(route.next_hop)
        except ValueError:
            return f"{subject} has an invalid next hop {route.next_hop}"
        if not any(net is not None and hop in net for net in map(_network_of, dev.interfaces.values())):
            return f"next hop {route.next_hop} is not on a network directly connected to {dev.hostname}"
        owner = _ip_owner(ctx.devices, route.next_hop)
        if owner and ctx.devices.get(owner[0]) is neighbor:
            return None
        target = owner[0] if owner else f"{route.next_hop}, which belongs to no device"
        return f"{subject} points at {target}, it should go via {via}"
    if route.outgoing_interface:
        far = _far_end(ctx.links, dev.hostname, route.outgoing_interface)
        if far and ctx.devices.get(far[0]) is neighbor:
            return None
        toward = far[0] if far else "no linked device"
        return f"{subject} leaves {route.outgoing_interface} toward {toward}, it should go via {via}"
    return f"{subject} has no next hop or exit interface"


def _check_route(req: dict, dev: ParsedDevice, candidates: list[RouteEntry], ctx: EvalContext) -> str | None:
    """None when one of the student's routes satisfies `req`, else the problem."""
    label = destination_label(req, ctx.policies.allow_dynamic_subnetting)
    subject = label if req.get("is_default") else f"route to {label}"
    target, problem = _expected_destination(req, ctx)
    if problem:
        return problem
    matches = [r for r in candidates if target is None or _route_network(r) == target]
    if not matches:
        return f"no {label}" if req.get("is_default") else f"no static route to {label}"
    neighbor = ctx.find_device(req["via_device"])
    if neighbor is None or neighbor.is_placeholder:
        return f"{subject} must go via {req['via_device']}, which is missing"
    reasons = [_wrong_neighbor(r, dev, neighbor, ctx, subject, req["via_device"]) for r in matches]
    if any(reason is None for reason in reasons):
        return None
    return reasons[0]


def evaluate(rule: EvaluationRule, ctx: EvalContext) -> RuleOutcome:
    pts = float(rule.points)
    dev = ctx.find_device(rule.target_device)
    if dev is None or dev.is_placeholder:
        return RuleOutcome(0.0, False, f"Device '{rule.target_device}' missing",
                           f"Cannot evaluate static routes: device '{rule.target_device}' missing.")
    required = (rule.expected_value or {}).get("routes") or []
    if not required:
        return RuleOutcome(pts, True, "No static routes required",
                           "No static routes are required on this device.")
    candidates = [r for r in dev.routes if is_static(r)]
    problems = [p for p in (_check_route(req, dev, candidates, ctx) for req in required) if p]
    satisfied = len(required) - len(problems)
    actual = f"{satisfied} of {len(required)} static routes correct"
    if not problems:
        return RuleOutcome(pts, True, actual,
                           f"All {len(required)} required static routes on {rule.target_device} "
                           "reach the right destination through the right neighbor.")
    return RuleOutcome(round(pts * satisfied / len(required), 1), False, actual,
                       f"Static routing on {rule.target_device}: " + "; ".join(problems) + ".")
