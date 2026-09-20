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
    predicate: str                  # "equal" | "compatible"
    points: float
    why_it_matters: str             # feeds the guidance layer
    extract: Callable[[ParsedDevice, InterfaceData], Any]
    applies: Callable[[ParsedDevice, InterfaceData, ParsedDevice, InterfaceData], bool]
    # Rendering and storage. A rule travels through instructions.txt as JSON,
    # so a value has to survive the round trip.
    render: Callable[[Any], str] = field(default=lambda v: str(v))
    serialize: Callable[[Any], Any] = field(default=lambda v: v)


# --- Predicates -------------------------------------------------------------

def _is_trunk(intf: InterfaceData) -> bool:
    return intf.switchport_mode == "trunk"


def _both_trunk(dev_a, intf_a, dev_b, intf_b) -> bool:
    return _is_trunk(intf_a) and _is_trunk(intf_b)


def _both_switchports(dev_a, intf_a, dev_b, intf_b) -> bool:
    """
    Mode agreement is only meaningful between two switchports. A router or a
    PC on the far end of a switch port has no switchport mode to disagree
    with, and demanding one would fail every access link in the topology.
    """
    return bool(intf_a.is_switchport and intf_b.is_switchport)


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


def _compare_equal(attr: LinkAttribute, value_a: Any, value_b: Any) -> AgreementVerdict:
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


def _compare_compatible(attr: LinkAttribute, value_a: Any, value_b: Any) -> AgreementVerdict:
    mode_a = value_a or "unset"
    mode_b = value_b or "unset"
    observed = f"{mode_a} vs {mode_b}"

    if frozenset((mode_a, mode_b)) in _SWITCHPORT_COMPATIBLE:
        return AgreementVerdict(passed=True, actual=observed)

    if mode_a == mode_b == "dynamic auto":
        reason = (
            "Both ends are 'dynamic auto', so neither end ever asks to trunk "
            "and the link stays an access port. No error is logged."
        )
    elif "unset" in (mode_a, mode_b):
        reason = f"{attr.label} is not configured on both ends of the link."
    else:
        reason = f"{attr.label} pairing '{mode_a}' with '{mode_b}' does not form a working link."

    return AgreementVerdict(passed=False, actual=observed, reason=reason)


_PREDICATES = {
    "equal": _compare_equal,
    "compatible": _compare_compatible,
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
        label="trunk allowed VLAN list",
        predicate="equal",
        points=5.0,
        why_it_matters=(
            "A VLAN permitted on one end of a trunk and pruned on the other is a "
            "black hole: the switches stay up, the trunk stays up, and that one "
            "VLAN's traffic disappears."
        ),
        extract=lambda dev, intf: tuple(sorted(intf.trunk_allowed_vlans)) or None,
        applies=_both_trunk,
        render=_render_vlan_list,
        serialize=lambda v: list(v) if v else None,
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

    predicate = _PREDICATES.get(attr.predicate, _compare_equal)
    verdict = predicate(attr, value_a, value_b)

    if not verdict.passed or not enforce_reference or reference_value is None:
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
