# src/link_attributes.py
"""
Link-scoped evaluation attributes.

Every other rule in the engine targets ONE device and at most one interface,
which cannot express the question that actually decides whether a link works:
do both ends agree? This module holds the attributes compared across a link,
the predicates that compare them, and the compatibility tables for settings
whose mismatches fail silently on real hardware.

Phase 1 ships only attributes the parsers already produce, so the mechanism is
proven end to end before any parsing risk is taken on. Phase 2 adds per
interface protocol settings (OSPF timers and area, MTU, speed/duplex,
channel-group mode, clock rate) and Phase 3 adds device-level ones (EIGRP AS,
BGP peering, CHAP), together with the `exactly_one` and `reciprocal`
predicates those need. See
docs/superpowers/specs/2026-09-20-link-scoped-evaluation-rules-design.md.

Nothing here reaches a score. These functions return a verdict and wording;
src/evaluator.py decides what a verdict is worth.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from src.models import InterfaceData, ParsedDevice


@dataclass(frozen=True)
class AgreementVerdict:
    """The outcome of comparing one attribute across one link."""
    passed: bool
    actual: str          # observed state, shown in the report
    reason: str = ""     # why it failed; empty when passed


@dataclass(frozen=True)
class LinkAttribute:
    key: str
    label: str
    predicate: str                  # "equal" | "compatible" | "covers"
    points: float
    why_it_matters: str             # feeds the guidance layer
    extract: Callable[[ParsedDevice, InterfaceData], Any]
    applies: Callable[[ParsedDevice, InterfaceData, ParsedDevice, InterfaceData], bool]
    # Rendering and storage. A rule travels through instructions.txt as JSON,
    # so a value has to survive the round trip.
    render: Callable[[Any], str] = field(default=lambda v: str(v))
    serialize: Callable[[Any], Any] = field(default=lambda v: v)
    description_template: str = "{label} must match on {a} and {b}"
    # Whether "must also equal the instructor's value" is a coherent demand.
    # It is not for a coverage check: there is no single value to match.
    reference_enforceable: bool = True
    # What IOS does when the line is absent. A config that never writes
    # `duplex` is still running a duplex setting, so comparing "unset" against
    # an explicit value on the other end would report a mismatch that does not
    # exist. Supplying the default makes the comparison the one that matters:
    # effective value against effective value.
    implicit_default: Any = None


# --- Predicates -------------------------------------------------------------

def _is_trunk(intf: InterfaceData) -> bool:
    return intf.switchport_mode == "trunk"


def _both_trunk(dev_a, intf_a, dev_b, intf_b) -> bool:
    return _is_trunk(intf_a) and _is_trunk(intf_b)


def _vlans_in_use(dev: ParsedDevice) -> frozenset:
    """
    The VLANs a device actually carries: an access port assigned to one, or an
    addressed SVI acting as its gateway.

    Deliberately NOT the VLAN database. A switch can have a VLAN defined with
    no members, and demanding that a trunk carry it would fail a correctly
    pruned network. PASIC_CORE_SW holds an SVI for VLAN 20 (SALES) while
    IT_DEPARTMENT_SW has no SALES port at all -- pruning 20 on that uplink
    costs nothing, and the link pings end to end exactly as it should.
    """
    vlans = set()
    for name, intf in dev.interfaces.items():
        if intf.access_vlan:
            vlans.add(intf.access_vlan)
        svi = re.match(r"^vlan(\d+)$", name, re.IGNORECASE)
        if svi and intf.ip_address:
            vlans.add(int(svi.group(1)))
    return frozenset(vlans)


def _trunk_carrying_shared_vlans(dev_a, intf_a, dev_b, intf_b) -> bool:
    if not _both_trunk(dev_a, intf_a, dev_b, intf_b):
        return False
    return bool(_vlans_in_use(dev_a) & _vlans_in_use(dev_b))


def _both_switchports(dev_a, intf_a, dev_b, intf_b) -> bool:
    """
    Mode agreement is only meaningful between two switchports. A router or a
    PC on the far end of a switch port has no switchport mode to disagree
    with, and demanding one would fail every access link in the topology.
    """
    return bool(intf_a.is_switchport and intf_b.is_switchport)


def _is_physical(intf: InterfaceData) -> bool:
    """Excludes SVIs and loopbacks, which have no media settings to agree on."""
    return not re.match(r"^(vlan|loopback|tunnel|port-channel)", intf.name, re.IGNORECASE)


def _is_serial(intf: InterfaceData) -> bool:
    return bool(re.match(r"^se(rial)?", intf.name, re.IGNORECASE))


def _both_routed(dev_a, intf_a, dev_b, intf_b) -> bool:
    """Both ends carry an address, so OSPF could run across the link."""
    return bool(intf_a.ip_address and intf_b.ip_address)


def _either_set(field: str):
    """
    Check the attribute only when at least one end writes it explicitly.

    Two ends that both leave a setting at its default already agree, so a rule
    would be noise. One end changing it is exactly when the pair can diverge,
    and the other end's effective value is then its IOS default.
    """
    def predicate(dev_a, intf_a, dev_b, intf_b) -> bool:
        return getattr(intf_a, field, None) is not None or getattr(intf_b, field, None) is not None
    return predicate


def _routed_and_either_set(field: str):
    either = _either_set(field)

    def predicate(dev_a, intf_a, dev_b, intf_b) -> bool:
        return _both_routed(dev_a, intf_a, dev_b, intf_b) and either(dev_a, intf_a, dev_b, intf_b)
    return predicate


def _physical_and_either_set(field: str):
    either = _either_set(field)

    def predicate(dev_a, intf_a, dev_b, intf_b) -> bool:
        return (_is_physical(intf_a) and _is_physical(intf_b)
                and either(dev_a, intf_a, dev_b, intf_b))
    return predicate


def _both_serial(dev_a, intf_a, dev_b, intf_b) -> bool:
    return _is_serial(intf_a) and _is_serial(intf_b)


def _either_in_a_channel(dev_a, intf_a, dev_b, intf_b) -> bool:
    return intf_a.channel_group is not None or intf_b.channel_group is not None


# EtherChannel negotiation pairings. Unlike a mismatched IP, every one of the
# absent combinations fails SILENTLY: the channel simply never forms, or forms
# on one side only and loops. `passive` with `passive` is the one students hit
# most -- both ends wait to be asked, and nothing is logged.
_ETHERCHANNEL_COMPATIBLE: set[frozenset] = {
    frozenset(("active", "active")),
    frozenset(("active", "passive")),
    frozenset(("on", "on")),
    frozenset(("desirable", "desirable")),
    frozenset(("desirable", "auto")),
}


# Switchport / DTP pairings. A pairing that is absent is incompatible.
# `auto` + `auto` is the entry that matters: both ends wait to be asked, the
# link silently stays an access port, and nothing is logged.
_SWITCHPORT_COMPATIBLE: set[frozenset] = {
    frozenset(("trunk", "trunk")),
    frozenset(("trunk", "dynamic desirable")),
    frozenset(("trunk", "dynamic auto")),
    frozenset(("dynamic desirable", "dynamic desirable")),
    frozenset(("dynamic desirable", "dynamic auto")),
    frozenset(("access", "access")),
}


def _compare_equal(attr: LinkAttribute, value_a: Any, value_b: Any,
                   name_a: str = "one end", name_b: str = "the other end") -> AgreementVerdict:
    rendered_a = attr.render(value_a) if value_a is not None else "not set"
    rendered_b = attr.render(value_b) if value_b is not None else "not set"
    observed = f"{rendered_a} vs {rendered_b}"

    if value_a is None or value_b is None:
        return AgreementVerdict(
            passed=False,
            actual=observed,
            reason=f"{attr.label} is not configured on both ends of the link.",
        )
    if value_a == value_b:
        return AgreementVerdict(passed=True, actual=rendered_a)
    return AgreementVerdict(
        passed=False,
        actual=observed,
        reason=f"{attr.label} differs across the link ({rendered_a} against {rendered_b}).",
    )


_COMPATIBILITY_MATRICES = {
    "switchport_mode": _SWITCHPORT_COMPATIBLE,
    "channel_group_mode": _ETHERCHANNEL_COMPATIBLE,
}

# The pairings worth explaining in their own words, because each fails with no
# error message at all and a student has nothing to search for.
_SILENT_FAILURES = {
    frozenset(("dynamic auto",)): (
        "Both ends are 'dynamic auto', so neither end ever asks to trunk "
        "and the link stays an access port. No error is logged."
    ),
    frozenset(("passive",)): (
        "Both ends are LACP 'passive', so neither end ever asks to bundle "
        "and the channel never forms. No error is logged."
    ),
    frozenset(("auto",)): (
        "Both ends are PAgP 'auto', so neither end ever asks to bundle "
        "and the channel never forms. No error is logged."
    ),
}


def _compare_compatible(attr: LinkAttribute, value_a: Any, value_b: Any,
                        name_a: str = "one end", name_b: str = "the other end") -> AgreementVerdict:
    mode_a = value_a or "unset"
    mode_b = value_b or "unset"
    observed = f"{mode_a} vs {mode_b}"
    matrix = _COMPATIBILITY_MATRICES.get(attr.key, _SWITCHPORT_COMPATIBLE)

    if frozenset((mode_a, mode_b)) in matrix:
        return AgreementVerdict(passed=True, actual=observed)

    silent = _SILENT_FAILURES.get(frozenset((mode_a, mode_b)))
    if silent:
        reason = silent
    elif "unset" in (mode_a, mode_b):
        reason = f"{attr.label} is not configured on both ends of the link."
    else:
        reason = f"{attr.label} pairing '{mode_a}' with '{mode_b}' does not form a working link."

    return AgreementVerdict(passed=False, actual=observed, reason=reason)


def _compare_exactly_one(attr: LinkAttribute, value_a: Any, value_b: Any,
                         name_a: str = "one end", name_b: str = "the other end") -> AgreementVerdict:
    """
    The attribute must be set on precisely one endpoint.

    A serial link is clocked by its DCE end and only that end. Neither end
    clocking leaves the line protocol down; both ends clocking is a
    misunderstanding of which side owns the timing.
    """
    set_on = [name for name, value in ((name_a, value_a), (name_b, value_b)) if value is not None]

    if len(set_on) == 1:
        return AgreementVerdict(
            passed=True, actual=f"{attr.label} set on {set_on[0]} only")
    if not set_on:
        return AgreementVerdict(
            passed=False,
            actual=f"{attr.label} set on neither end",
            reason=(
                f"{attr.label} is not set on either end. The DCE end of a serial "
                "link supplies the timing; without it the line protocol stays down."
            ),
        )
    return AgreementVerdict(
        passed=False,
        actual=f"{attr.label} set on both ends",
        reason=(
            f"{attr.label} is set on both {name_a} and {name_b}. Only the DCE end "
            "supplies timing; the DTE end takes it from the cable."
        ),
    )


def _compare_covers(attr: LinkAttribute, value_a: Any, value_b: Any,
                    name_a: str = "one end", name_b: str = "the other end") -> AgreementVerdict:
    """
    Every VLAN in use on BOTH sides must be permitted on BOTH ends.

    Not an equality check. Two ends of a trunk have no reason to carry
    identical allowed lists: a core pruned to the VLANs it serves and an
    access switch left near-default is a working, well-configured link.
    Requiring the lists to match fails correct networks. What actually breaks
    connectivity is a VLAN that has members on both sides being pruned on one
    of them.
    """
    allowed_a, allowed_b = value_a["allowed"], value_b["allowed"]
    required = value_a["in_use"] & value_b["in_use"]

    if not required:
        return AgreementVerdict(passed=True, actual="no VLANs in common")

    # An unset allowed list means every VLAN is permitted, which is the Cisco
    # default and cannot strand anything.
    missing_a = (required - allowed_a) if allowed_a is not None else frozenset()
    missing_b = (required - allowed_b) if allowed_b is not None else frozenset()

    if not missing_a and not missing_b:
        return AgreementVerdict(
            passed=True,
            actual=f"VLAN {_render_vlan_list(sorted(required))} permitted on both ends",
        )

    stranded = sorted(missing_a | missing_b)
    ends = []
    if missing_a:
        ends.append(f"{name_a} ({_render_vlan_list(sorted(missing_a))})")
    if missing_b:
        ends.append(f"{name_b} ({_render_vlan_list(sorted(missing_b))})")

    return AgreementVerdict(
        passed=False,
        actual=f"VLAN {_render_vlan_list(stranded)} pruned on {' and '.join(ends)}",
        reason=(
            f"VLAN {_render_vlan_list(stranded)} has members on both sides of this "
            f"trunk but is not permitted on {' and '.join(ends)}, so that VLAN's "
            "traffic is dropped at the trunk while the link itself stays up."
        ),
    )


_PREDICATES = {
    "equal": _compare_equal,
    "compatible": _compare_compatible,
    "covers": _compare_covers,
    "exactly_one": _compare_exactly_one,
}


# --- Registry ---------------------------------------------------------------

def _render_vlan_list(value: Any) -> str:
    if not value:
        return "all"
    return ",".join(str(v) for v in value)


LINK_ATTRIBUTES: dict[str, LinkAttribute] = {
    "trunk_native_vlan": LinkAttribute(
        key="trunk_native_vlan",
        label="802.1Q native VLAN",
        predicate="equal",
        points=6.0,
        why_it_matters=(
            "Frames in the native VLAN cross a trunk untagged. When the two ends "
            "disagree, traffic leaving one VLAN silently arrives in another, which "
            "bridges two networks that were meant to stay separate and can form a "
            "loop. Spanning tree reports it, but connectivity looks fine until it "
            "does not."
        ),
        extract=lambda dev, intf: intf.trunk_native_vlan,
        applies=_both_trunk,
    ),
    "trunk_allowed_vlans": LinkAttribute(
        key="trunk_allowed_vlans",
        label="VLANs in use",
        predicate="covers",
        points=5.0,
        why_it_matters=(
            "A VLAN with members on both sides of a trunk, pruned on one end, is a "
            "black hole: both switches stay up, the trunk stays up, and that one "
            "VLAN's traffic disappears. Note that the two allowed lists do not have "
            "to be identical -- pruning a VLAN that has no members on either side "
            "is good practice, not a fault."
        ),
        extract=lambda dev, intf: {
            "allowed": frozenset(intf.trunk_allowed_vlans) if intf.trunk_allowed_vlans else None,
            "in_use": _vlans_in_use(dev),
        },
        applies=_trunk_carrying_shared_vlans,
        render=_render_vlan_list,
        serialize=lambda v: sorted(v["in_use"]),
        description_template=(
            "Every VLAN in use must be permitted on both ends of the trunk "
            "between {a} and {b}"
        ),
        reference_enforceable=False,
    ),
    "switchport_mode": LinkAttribute(
        key="switchport_mode",
        label="switchport mode",
        predicate="compatible",
        points=5.0,
        why_it_matters=(
            "The two ends of a link must agree on whether it is a trunk or an "
            "access port. Several of the mismatched pairings produce no error at "
            "all -- the link simply never becomes a trunk."
        ),
        extract=lambda dev, intf: intf.switchport_mode,
        applies=_both_switchports,
    ),

    # --- Phase 2: interface-level protocol settings -------------------------

    "ospf_hello_interval": LinkAttribute(
        key="ospf_hello_interval",
        label="OSPF hello interval",
        predicate="equal",
        points=6.0,
        why_it_matters=(
            "Two routers only become OSPF neighbours if their hello and dead "
            "intervals match exactly. Change one end and the adjacency never "
            "forms, so the routes never appear -- while both interfaces stay up "
            "and every ping to the directly connected address still succeeds."
        ),
        extract=lambda dev, intf: intf.ospf_hello_interval,
        applies=_routed_and_either_set("ospf_hello_interval"),
        implicit_default=10,
    ),
    "ospf_dead_interval": LinkAttribute(
        key="ospf_dead_interval",
        label="OSPF dead interval",
        predicate="equal",
        points=6.0,
        why_it_matters=(
            "The dead interval must match across the link, and conventionally "
            "runs at four times the hello. A mismatch prevents the adjacency "
            "exactly as a hello mismatch does."
        ),
        extract=lambda dev, intf: intf.ospf_dead_interval,
        applies=_routed_and_either_set("ospf_dead_interval"),
        implicit_default=40,
    ),
    "ospf_area": LinkAttribute(
        key="ospf_area",
        label="OSPF area",
        predicate="equal",
        points=7.0,
        why_it_matters=(
            "Both interfaces on a link must sit in the same OSPF area. Two "
            "routers in different areas on the same wire will not form an "
            "adjacency at all."
        ),
        extract=lambda dev, intf: intf.ospf_area,
        applies=_routed_and_either_set("ospf_area"),
    ),
    "ospf_network_type": LinkAttribute(
        key="ospf_network_type",
        label="OSPF network type",
        predicate="equal",
        points=5.0,
        why_it_matters=(
            "The network type decides whether a DR is elected and which timers "
            "apply. Two ends that disagree can stay stuck in two-way state "
            "forever, never exchanging routes."
        ),
        extract=lambda dev, intf: intf.ospf_network_type,
        applies=_routed_and_either_set("ospf_network_type"),
    ),
    "ospf_authentication": LinkAttribute(
        key="ospf_authentication",
        label="OSPF authentication",
        predicate="equal",
        points=5.0,
        why_it_matters=(
            "Authentication must be configured the same way on both ends. One "
            "end authenticating and the other not is a silent adjacency "
            "failure: the hellos are simply discarded."
        ),
        extract=lambda dev, intf: intf.ospf_authentication,
        applies=_routed_and_either_set("ospf_authentication"),
        implicit_default="none",
    ),
    "mtu": LinkAttribute(
        key="mtu",
        label="interface MTU",
        predicate="equal",
        points=6.0,
        why_it_matters=(
            "An MTU mismatch is the classic OSPF trap: the neighbours reach "
            "EXSTART and stick there, retransmitting database descriptors "
            "forever. Nothing about the interfaces looks wrong."
        ),
        extract=lambda dev, intf: intf.mtu,
        applies=_physical_and_either_set("mtu"),
        implicit_default=1500,
    ),
    "speed": LinkAttribute(
        key="speed",
        label="interface speed",
        predicate="equal",
        points=4.0,
        why_it_matters=(
            "Hard-setting speed on one end while the other auto-negotiates is "
            "how duplex mismatches happen: the link comes up, and then drops "
            "frames under load with late collisions."
        ),
        extract=lambda dev, intf: intf.speed,
        applies=_physical_and_either_set("speed"),
        implicit_default="auto",
    ),
    "duplex": LinkAttribute(
        key="duplex",
        label="interface duplex",
        predicate="equal",
        points=4.0,
        why_it_matters=(
            "A duplex mismatch does not stop the link coming up. It shows as "
            "collisions and terrible throughput under load, which is far harder "
            "to diagnose than an interface that is simply down."
        ),
        extract=lambda dev, intf: intf.duplex,
        applies=_physical_and_either_set("duplex"),
        implicit_default="auto",
    ),
    "channel_group_mode": LinkAttribute(
        key="channel_group_mode",
        label="EtherChannel mode",
        predicate="compatible",
        points=7.0,
        why_it_matters=(
            "The two ends must negotiate compatibly: LACP active with active or "
            "passive, PAgP desirable with desirable or auto, or `on` with `on`. "
            "Every other pairing fails without an error message -- passive with "
            "passive is the common one, where both ends wait to be asked and the "
            "channel never forms."
        ),
        extract=lambda dev, intf: intf.channel_group_mode,
        applies=_either_in_a_channel,
    ),
    "encapsulation": LinkAttribute(
        key="encapsulation",
        label="serial encapsulation",
        predicate="equal",
        points=5.0,
        why_it_matters=(
            "Both ends of a serial link must run the same encapsulation. PPP on "
            "one end and HDLC on the other leaves the line protocol down, even "
            "though the cable and the addressing are correct."
        ),
        extract=lambda dev, intf: intf.encapsulation,
        applies=lambda a, ia, b, ib: _both_serial(a, ia, b, ib) and _either_set("encapsulation")(a, ia, b, ib),
        implicit_default="hdlc",
    ),
    "clock_rate": LinkAttribute(
        key="clock_rate",
        label="serial clock rate",
        predicate="exactly_one",
        points=5.0,
        why_it_matters=(
            "A serial link is timed by its DCE end and only that end. With no "
            "clock the line protocol stays down; with a clock on both ends the "
            "student has misread which side of the cable they are on."
        ),
        extract=lambda dev, intf: intf.clock_rate,
        applies=_both_serial,
        description_template="Serial clock rate must be set on exactly one end of {a} and {b}",
        reference_enforceable=False,
    ),
}


def applicable_attributes(
    dev_a: ParsedDevice,
    intf_a: InterfaceData,
    dev_b: ParsedDevice,
    intf_b: InterfaceData,
) -> list[LinkAttribute]:
    """
    The attributes worth checking on this link, in registry order.

    Gating on the reference topology is what keeps the rubric proportional to
    what was taught: a lab with no trunks generates no trunk rules.
    """
    applicable = []
    for attr in LINK_ATTRIBUTES.values():
        try:
            if attr.applies(dev_a, intf_a, dev_b, intf_b):
                applicable.append(attr)
        except Exception:
            continue
    return applicable


def compare(
    attr: LinkAttribute,
    dev_a: ParsedDevice,
    intf_a: InterfaceData,
    dev_b: ParsedDevice,
    intf_b: InterfaceData,
    reference_value: Any = None,
    enforce_reference: bool = False,
) -> AgreementVerdict:
    """
    Apply one attribute's predicate across a link.

    By default only agreement is required: two ends that both use native VLAN
    999 form a working trunk whatever the instructor's own file happened to
    use, and the student is right. `enforce_reference` additionally requires
    the agreed value to equal the reference, for labs where the instructor
    dictated it.
    """
    value_a = attr.extract(dev_a, intf_a)
    value_b = attr.extract(dev_b, intf_b)

    # An absent line still has an effective value. `exactly_one` is the
    # exception: there, absence is the fact being measured.
    if attr.implicit_default is not None and attr.predicate != "exactly_one":
        value_a = attr.implicit_default if value_a is None else value_a
        value_b = attr.implicit_default if value_b is None else value_b

    predicate = _PREDICATES.get(attr.predicate, _compare_equal)
    verdict = predicate(attr, value_a, value_b, dev_a.hostname, dev_b.hostname)

    if (
        not verdict.passed
        or not enforce_reference
        or not attr.reference_enforceable
        or reference_value is None
    ):
        return verdict

    # The ends agree. Under this policy they must also match the reference.
    expected = attr.serialize(reference_value) if not isinstance(reference_value, (list, type(None))) else reference_value
    observed = attr.serialize(value_a)
    if observed == expected:
        return verdict

    return AgreementVerdict(
        passed=False,
        actual=verdict.actual,
        reason=(
            f"Both ends agree on {attr.render(value_a)}, but this lab requires "
            f"{attr.render(reference_value)}."
        ),
    )
