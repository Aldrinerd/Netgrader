# validation/mutations.py
"""
The fault catalogue.

Each entry injects one deliberate mistake into a copy of the reference and
declares what the engine SHOULD say about it. That declaration is the ground
truth the accuracy measurement is taken against.

Two kinds of entry, and the second kind matters more:

  POSITIVE  a real fault. The engine must catch it. Measures recall -- faults
            it misses are marks a student keeps without earning them.

A fault this suite cannot measure: an attribute the reference never
configures generates no rule, so a student's change to it is not graded. The
reference is the specification, and grading what the lab did not ask for
would be inventing requirements. MTU is the case that bites -- a real config
only writes it deliberately, so an MTU mismatch breaking OSPF goes unseen
unless the instructor set MTU themselves. See
tests/test_link_agreement.py::test_an_attribute_the_reference_never_sets_is_not_graded.

  NEGATIVE  correct work that merely differs from the reference: a renamed
            device, a different but self-consistent addressing plan, a trunk
            pruned of a VLAN nobody uses. The engine must NOT flag it.
            Measures specificity -- and a false positive here takes marks away
            from a student who did the work properly, which is the worse
            failure of the two.
"""

from dataclasses import dataclass, field
from typing import Callable

from src.models import EvaluationPolicies, InterfaceData, TopologyResult

DEFAULT = EvaluationPolicies()
SECURE = EvaluationPolicies(grade_security_baseline=True)
DYNAMIC = EvaluationPolicies(allow_dynamic_subnetting=True)
CUSTOM_NAMES = EvaluationPolicies(allow_custom_hostnames=True)


@dataclass(frozen=True)
class Mutation:
    id: str
    label: str
    fault: str                              # what the student did, in plain words
    apply: Callable[[TopologyResult], None]  # mutates a copy in place
    expect_categories: frozenset = frozenset()   # empty => must still score 100%
    expect_mentions: tuple = ()             # substrings the guidance should contain
    policies: EvaluationPolicies = field(default_factory=EvaluationPolicies)

    @property
    def is_negative(self) -> bool:
        return not self.expect_categories


# --- Positive cases: real faults --------------------------------------------

def _native_vlan_mismatch(topo):
    topo.devices["SW2"].interfaces["GigabitEthernet0/2"].trunk_native_vlan = 1


def _trunk_becomes_access(topo):
    intf = topo.devices["SW2"].interfaces["GigabitEthernet0/2"]
    intf.switchport_mode = "access"
    intf.access_vlan = 10


def _prune_a_populated_vlan(topo):
    # VLAN 10 has users on both switches; pruning it here strands them.
    topo.devices["SW2"].interfaces["GigabitEthernet0/2"].trunk_allowed_vlans = [20, 99]


def _interface_left_shutdown(topo):
    intf = topo.devices["R1"].interfaces["GigabitEthernet0/0"]
    intf.admin_status = "administratively down"
    intf.line_status = "down"


def _wrong_ip_address(topo):
    topo.devices["R2"].interfaces["GigabitEthernet0/0"].ip_address = "10.0.0.6"


def _wrong_subnet_mask(topo):
    intf = topo.devices["R2"].interfaces["GigabitEthernet0/0"]
    intf.cidr = 24
    intf.subnet_mask = "255.255.255.0"
    intf.network_address = "10.0.0.0"


def _device_missing(topo):
    topo.devices.pop("PC2", None)
    topo.links = [
        l for l in topo.links
        if l.source_device != "PC2" and l.target_device != "PC2"
    ]


def _cable_unplugged(topo):
    topo.links = [
        l for l in topo.links
        if not (l.source_device == "SW1" and l.target_device == "SW2")
    ]


def _wrong_access_vlan(topo):
    topo.devices["SW2"].interfaces["FastEthernet0/1"].access_vlan = 20


def _gateway_removed(topo):
    topo.devices["PC2"].default_gateway = None


def _gateway_in_wrong_subnet(topo):
    topo.devices["PC2"].default_gateway = "192.168.77.1"


def _ospf_network_missing(topo):
    topo.devices["R2"].ospf_processes = []


def _enable_secret_removed(topo):
    topo.devices["R2"].has_enable_secret = False


def _subnet_mismatch_across_link(topo):
    intf = topo.devices["R2"].interfaces["GigabitEthernet0/0"]
    intf.ip_address = "10.9.9.2"
    intf.network_address = "10.9.9.0"


def _ospf_hello_changed_on_one_end(topo):
    topo.devices["R2"].interfaces["GigabitEthernet0/0"].ospf_hello_interval = 5


def _duplex_hardcoded_on_one_end(topo):
    topo.devices["R2"].interfaces["GigabitEthernet0/0"].duplex = "full"


# --- Negative cases: correct work that differs from the reference ------------

def _devices_renamed(topo):
    """Same network, institution-specific hostnames."""
    renames = {"R1": "EDGE-RTR", "R2": "CORE-RTR", "SW1": "ACCESS-A", "SW2": "ACCESS-B"}
    for old, new in renames.items():
        dev = topo.devices.pop(old)
        dev.hostname = new
        dev.canonical_name = new.lower()
        dev.display_name = new
        topo.devices[new] = dev
    for link in topo.links:
        link.source_device = renames.get(link.source_device, link.source_device)
        link.target_device = renames.get(link.target_device, link.target_device)


def _different_but_valid_addressing(topo):
    """A student's own /30 on the router link. Both ends move together."""
    for host, ip in (("R1", "172.16.5.1"), ("R2", "172.16.5.2")):
        intf = topo.devices[host].interfaces["GigabitEthernet0/0"]
        intf.ip_address = ip
        intf.network_address = "172.16.5.0"


def _native_vlan_changed_on_both_ends(topo):
    """999 on both ends is a working trunk, whatever the reference used."""
    for host in ("SW1", "SW2"):
        topo.devices[host].interfaces["GigabitEthernet0/2"].trunk_native_vlan = 999


def _unused_vlan_pruned(topo):
    """VLAN 20 (SALES) has no members on either switch. Pruning it is good practice."""
    for host in ("SW1", "SW2"):
        topo.devices[host].interfaces["GigabitEthernet0/2"].trunk_allowed_vlans = [10, 99]


def _ospf_timers_changed_on_both_ends(topo):
    """Faster timers on both ends form a perfectly good adjacency."""
    for host in ("R1", "R2"):
        intf = topo.devices[host].interfaces["GigabitEthernet0/0"]
        intf.ospf_hello_interval = 5
        intf.ospf_dead_interval = 20


def _extra_unrelated_interface(topo):
    """A spare loopback the lab never asked for must not cost marks."""
    topo.devices["R1"].interfaces["Loopback0"] = InterfaceData(
        name="Loopback0", ip_address="1.1.1.1", cidr=32,
        subnet_mask="255.255.255.255", network_address="1.1.1.1",
        description="Router ID",
    )


CATALOGUE: list = [
    # --- positive -----------------------------------------------------------
    Mutation(
        id="native_vlan_mismatch",
        label="Native VLAN mismatch on a trunk",
        fault="SW2's trunk uses native VLAN 1 while SW1 uses 99",
        apply=_native_vlan_mismatch,
        expect_categories=frozenset({"link_agreement"}),
        expect_mentions=("untagged",),
    ),
    Mutation(
        id="trunk_becomes_access",
        label="One end of the trunk left as an access port",
        fault="SW2 Gi0/2 configured as access instead of trunk",
        apply=_trunk_becomes_access,
        expect_categories=frozenset({"link_agreement", "vlan_trunk"}),
    ),
    Mutation(
        id="prune_populated_vlan",
        label="A VLAN with users pruned off the trunk",
        fault="VLAN 10 removed from SW2's allowed list while users sit in it",
        apply=_prune_a_populated_vlan,
        expect_categories=frozenset({"link_agreement"}),
        expect_mentions=("black hole",),
    ),
    Mutation(
        id="interface_shutdown",
        label="Interface left administratively down",
        fault="R1 Gi0/0 never enabled with 'no shutdown'",
        apply=_interface_left_shutdown,
        expect_categories=frozenset({"interface_status"}),
        expect_mentions=("shutdown",),
    ),
    Mutation(
        id="wrong_ip",
        label="Wrong host address on a point-to-point link",
        fault="R2 Gi0/0 addressed 10.0.0.6 instead of 10.0.0.2",
        apply=_wrong_ip_address,
        expect_categories=frozenset({"interface_ip"}),
    ),
    Mutation(
        id="wrong_mask",
        label="Wrong subnet mask",
        fault="R2 Gi0/0 given a /24 on a /30 point-to-point link",
        apply=_wrong_subnet_mask,
        expect_categories=frozenset({"interface_ip"}),
    ),
    Mutation(
        id="subnet_mismatch",
        label="Link endpoints in different subnets",
        fault="R2 Gi0/0 moved to 10.9.9.2 while R1 stays on 10.0.0.1",
        apply=_subnet_mismatch_across_link,
        expect_categories=frozenset({"relational_subnet"}),
        policies=DYNAMIC,
    ),
    Mutation(
        id="device_missing",
        label="A device never placed",
        fault="PC2 absent from the topology",
        apply=_device_missing,
        # A missing device legitimately fails every rule that targets it, not
        # just its presence check: its address and its gateway are gone too.
        expect_categories=frozenset({"device", "cabling", "interface_ip", "gateway"}),
    ),
    Mutation(
        id="cable_unplugged",
        label="A required link never cabled",
        fault="No cable between SW1 and SW2",
        apply=_cable_unplugged,
        expect_categories=frozenset({"cabling"}),
        expect_mentions=("cabl",),
    ),
    Mutation(
        id="wrong_access_vlan",
        label="Access port in the wrong VLAN",
        fault="SW2 Fa0/1 assigned VLAN 20 instead of VLAN 10",
        apply=_wrong_access_vlan,
        expect_categories=frozenset({"vlan_trunk"}),
    ),
    Mutation(
        id="gateway_removed",
        label="Host with no default gateway",
        fault="PC2 has no default gateway configured",
        apply=_gateway_removed,
        expect_categories=frozenset({"gateway"}),
    ),
    Mutation(
        id="gateway_wrong_subnet",
        label="Default gateway outside the host's subnet",
        fault="PC2 points at 192.168.77.1, which is not on its network",
        apply=_gateway_in_wrong_subnet,
        expect_categories=frozenset({"gateway"}),
    ),
    Mutation(
        id="ospf_missing",
        label="Routing protocol never configured",
        fault="R2 has no OSPF process at all",
        apply=_ospf_network_missing,
        expect_categories=frozenset({"routing"}),
    ),
    Mutation(
        id="enable_secret_removed",
        label="Privileged EXEC left unprotected",
        fault="R2 has no 'enable secret'",
        apply=_enable_secret_removed,
        expect_categories=frozenset({"security"}),
        policies=SECURE,
    ),
    Mutation(
        id="ospf_hello_mismatch",
        label="OSPF hello interval changed on one end",
        fault="R2 Gi0/0 uses hello 5 while R1 stays at the default 10",
        apply=_ospf_hello_changed_on_one_end,
        expect_categories=frozenset({"link_agreement"}),
        expect_mentions=("adjacency",),
    ),
    Mutation(
        id="duplex_hardcoded_one_end",
        label="Duplex hard-set on one end against auto on the other",
        fault="R2 Gi0/0 forced to full duplex while R1 auto-negotiates",
        apply=_duplex_hardcoded_on_one_end,
        expect_categories=frozenset({"link_agreement"}),
        expect_mentions=("collision",),
    ),

    # --- negative -----------------------------------------------------------
    Mutation(
        id="devices_renamed",
        label="Correct work, institution-specific hostnames",
        fault="Every device renamed; topology and configuration unchanged",
        apply=_devices_renamed,
        policies=CUSTOM_NAMES,
    ),
    Mutation(
        id="student_addressing_plan",
        label="Correct work, the student's own addressing plan",
        fault="Router link renumbered to 172.16.5.0/30 on both ends",
        apply=_different_but_valid_addressing,
        policies=DYNAMIC,
    ),
    Mutation(
        id="native_vlan_agreed",
        label="Correct work, a different native VLAN agreed by both ends",
        fault="Both trunk ends use native VLAN 999 instead of 99",
        apply=_native_vlan_changed_on_both_ends,
    ),
    Mutation(
        id="unused_vlan_pruned",
        label="Correct work, an unused VLAN pruned from the trunk",
        fault="VLAN 20 removed from both ends; nobody is in VLAN 20",
        apply=_unused_vlan_pruned,
    ),
    Mutation(
        id="ospf_timers_agreed",
        label="Correct work, non-default OSPF timers agreed by both ends",
        fault="Both ends of the R1-R2 link use hello 5 / dead 20",
        apply=_ospf_timers_changed_on_both_ends,
    ),
    Mutation(
        id="extra_loopback",
        label="Correct work, plus an interface the lab never asked for",
        fault="A spare Loopback0 added to R1",
        apply=_extra_unrelated_interface,
    ),
]


def by_id(mutation_id: str) -> Mutation:
    for mutation in CATALOGUE:
        if mutation.id == mutation_id:
            return mutation
    raise KeyError(mutation_id)
