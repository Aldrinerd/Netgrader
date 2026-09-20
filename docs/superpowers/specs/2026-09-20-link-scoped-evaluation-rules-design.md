# Design Spec: Link-Scoped Evaluation Rules

**Date:** 2026-09-20
**Topic:** A rule shape whose subject is a link rather than a device, covering
protocol agreement, mode compatibility, reciprocity and exactly-one invariants
**Status:** Ready for Plan & Implementation

---

## 1. The gap this closes

Every rule the engine can express today targets **one device and at most one
interface**:

```python
class EvaluationRule(BaseModel):
    target_device: str
    target_interface: str | None = None
```

That shape can ask *"does R1 Gi0/0 have IP 10.0.0.1/30"*. It cannot ask
*"do R1 Gi0/0 and R2 Gi0/0 agree on their OSPF hello timer"* — and the second
question is the one that decides whether the link actually works.

This matters because a large fraction of what a Cisco lab is actually testing
is agreement between two ends of a wire, not the contents of one end:

| Feature | What must agree across the link |
|---|---|
| OSPF adjacency | hello/dead timers, area ID, mask, auth, MTU, network type |
| EIGRP adjacency | AS number, K-values, auth key-chain |
| BGP session | reciprocal `neighbor` statements, `remote-as` vs peer's real AS |
| Trunking | native VLAN, allowed VLAN list, DTP mode compatibility |
| EtherChannel | LACP/PAgP mode compatibility, member port uniformity |
| PPP | encapsulation both ends, reciprocal CHAP credentials |
| Serial | clock rate on the DCE end, and **only** that end |
| Physical | speed, duplex |

A student can currently fail every one of these and lose nothing, because no
rule exists that can see them.

### 1.1 Two existing implementations argue for generalising

This shape is not new to the codebase — it has been written twice, ad hoc:

- **`relational_subnet`** ([evaluator.py](../../../src/evaluator.py)) grades
  whether two endpoints share a subnet. It carries the peer endpoint inside
  `expected_value` because there is nowhere else to put it.
- **Native VLAN mismatch** ([conflict_detector.py:100](../../../src/conflict_detector.py))
  detects trunk disagreement with full evidence citations — and **never
  grades it**. [evaluator.py:511](../../../src/evaluator.py) is the only place
  a conflict touches scoring, and it looks for cable conflicts alone.

So a native VLAN mismatch that breaks a student's entire trunk is displayed in
the Topology Discovery drawer and costs zero points. That is the cheapest
correctness win available and this spec absorbs it.

---

## 2. Design

### 2.1 The shape

A link-scoped rule keeps the existing `EvaluationRule` fields — no model
surgery, no migration of stored `instructions.txt` files — and follows the
precedent `relational_subnet` already set: endpoint A goes in the target
fields, endpoint B goes in `expected_value`.

```python
EvaluationRule(
    rule_id="link_ospf_hello_r1_gi0_0__r2_gi0_0",
    category="link_agreement",          # new value in the Literal
    description="OSPF hello interval must match on R1 Gi0/0 <-> R2 Gi0/0",
    points=6.0,
    target_device="R1",
    target_interface="GigabitEthernet0/0",
    expected_value={
        "peer_device": "R2",
        "peer_interface": "GigabitEthernet0/0",
        "attribute": "ospf_hello_interval",
        "predicate": "equal",
        "reference_value": 10,          # advisory unless policy says otherwise
    },
)
```

`RuleResult` already carries `target_device` / `target_interface`, so the
report, the gradebook CSV and the guidance layer need no changes to display
these.

### 2.2 Predicates, not just equality

"Agreement" is the common case, not the only one. The predicate is pluggable,
which is what lets one mechanism cover four of the five invariant shapes from
the survey:

| Predicate | Meaning | Covers |
|---|---|---|
| `equal` | both endpoints hold the same value | native VLAN, OSPF/EIGRP timers and AS, MTU, speed, duplex, encapsulation |
| `covers` | every VLAN in use on both sides is permitted on both ends | trunk allowed-VLAN lists |
| `compatible` | values are compatible per a named matrix | LACP/PAgP modes, DTP modes, switchport mode pairing |
| `exactly_one` | the attribute is set on precisely one endpoint | serial DCE clock rate |
| `reciprocal` | A's value names B's identity **and** B's names A's | BGP `neighbor`/`remote-as`, PPP CHAP username/password |

`compatible` needs real tables, because the failure modes are asymmetric and
silent:

```
LACP    active   passive  on      PAgP-desirable  PAgP-auto
active  OK       OK       NO      NO              NO
passive OK       NO(*)    NO      NO              NO
on      NO       NO       OK      NO              NO

(*) passive + passive never forms a channel: both ends wait to be asked.
    This is the single most common EtherChannel lab failure and it produces
    no error message at all.
```

```
DTP       trunk  desirable  auto   access
trunk     OK     OK         OK     NO
desirable OK     OK         OK     NO
auto      OK     OK         NO(*)  NO
access    NO     NO         NO     OK

(*) auto + auto stays an access port. Also silent.
```

### 2.3 The attribute registry

One table drives generation, evaluation and feedback. Adding a protocol means
adding a row, not touching the evaluator.

```python
@dataclass(frozen=True)
class LinkAttribute:
    key: str                       # "trunk_native_vlan"
    label: str                     # "802.1Q native VLAN"
    predicate: str                 # "equal" | "compatible" | ...
    extract: Callable[[ParsedDevice, InterfaceData], Any | None]
    applies_when: Callable[[ParsedDevice, InterfaceData], bool]
    points: float
    why_it_matters: str            # feeds src/feedback.py guidance
    failure_template: str
```

`applies_when` is what keeps the rubric honest. A link rule is generated only
when the attribute is *present and relevant in the instructor's reference* —
so a lab that never touches OSPF never emits OSPF adjacency rules, and the
rule count stays proportional to what was actually taught.

### 2.4 Endpoint resolution

Link rules must honour the existing policy toggles, so resolution reuses the
evaluator's current machinery rather than re-implementing it:

- `allow_custom_hostnames` → endpoints resolve through `_find_student_device`
  and the existing topological role matching.
- `strict_port_matching` → when off, an equivalent interface of the same speed
  class satisfies the endpoint.
- Endpoint order must not matter. Normalise with `normalize_edge_key()` from
  [fusion_engine.py:44](../../../src/fusion_engine.py) so that a rule written
  A→B matches a student link discovered B→A, and so `rule_id` is stable.

### 2.5 Agreement versus the reference value

`reference_value` records what the instructor's own file had. Whether it is
*binding* is a policy decision, mirroring how `allow_dynamic_subnetting`
already separates "mutually consistent" from "matches my exact IPs":

```python
# EvaluationPolicies
enforce_reference_link_values: bool = False
```

- **Off (default).** Any mutually-agreeing value passes. A student who picks
  hello 15 / dead 60 on both ends is correct, because the adjacency forms.
  This is the pedagogically right default and is consistent with the tool's
  existing stance on dynamic subnetting.
- **On.** The value must also equal the reference. For labs where the
  instructor dictated exact timers.

### 2.6 What this deliberately does not absorb

**`relational_subnet` stays as it is.** Subnet correctness is more than
pairwise agreement — it also enforces host uniqueness, prefix length, and
non-reuse of a subnet across different links. Those are set-wide properties
that a link-scoped predicate cannot express. Folding it in would lose checks.

**Conflict detection stays too.** Native VLAN mismatch continues to be
reported as a `ConflictIssue` for the Topology Discovery drawer. The link rule
is what *scores* it. To avoid double-penalising, the evaluator must not also
apply a conflict-derived deduction for any attribute that has a link rule —
see §5.

---

## 3. Phasing

The parser is the real cost, not the rule engine. Phase 1 therefore ships the
whole mechanism using **only data the parsers already produce**, which proves
the shape end-to-end at near-zero parsing risk.

### Phase 1 — mechanism, on existing data

| Attribute | Predicate | Parser work |
|---|---|---|
| `trunk_native_vlan` | `equal` | none — already parsed |
| `trunk_allowed_vlans` | `covers` | none — already parsed |
| `switchport_mode` | `compatible` | none — already parsed |

A fourth predicate, `covers`, was added during implementation. `equal` was the
wrong check for allowed-VLAN lists: two ends of a trunk have no reason to
carry identical lists, and requiring it fails a correctly pruned network. It
did exactly that on the captures in `captures/`, where the core is pruned to
the VLANs it serves and the access switch is left near-default. What actually
strands traffic is a VLAN with members on **both** sides being pruned on one
of them, so `covers` tests the intersection of VLANs in use rather than the
lists themselves. VLANs in use are derived from access-port assignments and
addressed SVIs, never from the VLAN database — a VLAN can be defined with no
members, and demanding a trunk carry it reintroduces the same false positive.

Deliverable: native VLAN mismatch becomes a graded checkpoint. The stranded
conflict-detector finding starts counting.

### Phase 2 — interface-level protocol attributes  *(shipped)*

Two design points settled during implementation:

- **Implicit defaults.** An absent line still has an effective value, so
  each attribute carries the IOS default and comparison is effective-value
  against effective-value. Without this, one end writing `duplex auto` and
  the other writing nothing would be reported as a mismatch that does not
  exist. `exactly_one` is exempt: there, absence is the fact being measured.
- **Gated on the reference.** Attributes only generate a rule when the
  instructor's file writes them. Real router configs always emit `speed`
  and `duplex`, so those are always graded; `mtu` and OSPF timers only when
  set deliberately. The reference is the specification, and grading what
  the lab did not ask for would be inventing requirements — but it means
  link agreement is only as complete as the reference.


Requires new parsing inside `interface` blocks in
[parsers.py](../../../src/parsers.py), extending `InterfaceData`:

| Attribute | Config source |
|---|---|
| `ospf_hello_interval`, `ospf_dead_interval` | `ip ospf hello-interval` / `dead-interval` |
| `ospf_area` | `ip ospf <pid> area <n>` |
| `ospf_network_type` | `ip ospf network <type>` |
| `ospf_auth` | `ip ospf authentication[-key]` / `message-digest-key` |
| `mtu` | `mtu` / `ip mtu` |
| `speed`, `duplex` | `speed` / `duplex` |
| `channel_group_mode` | `channel-group <n> mode <mode>` |
| `encapsulation` | `encapsulation ppp` / `hdlc` |
| `clock_rate` | `clock rate <n>` — predicate `exactly_one` |

### Phase 3 — device-level protocol attributes

Needs new `ParsedDevice` fields alongside `ospf_processes`:

| Attribute | Predicate | Notes |
|---|---|---|
| `eigrp_as` | `equal` | the #1 EIGRP lab failure |
| `eigrp_k_values` | `equal` | |
| `bgp_neighbor` | `reciprocal` | A peers to B's IP **and** B to A's |
| `bgp_remote_as` | `reciprocal` | must equal the peer's real local AS |
| `chap_credentials` | `reciprocal` | A's username = B's hostname, shared password |

Phase 3 also fixes a latent bug found during the survey:
[evaluator.py:637](../../../src/evaluator.py) reads `proto = exp.get("protocol", "ospf")`
and never uses it — the only occurrence in the file. The routing branch always
searches `ospf_processes` regardless of the declared protocol, so the
abstraction looks protocol-aware and is not. Either honour it or delete it.

---

## 4. Touch points

| File | Change |
|---|---|
| [src/models.py](../../../src/models.py) | add `"link_agreement"` to the `category` Literal; add `enforce_reference_link_values` to `EvaluationPolicies`; extend `InterfaceData` per phase |
| `src/link_attributes.py` *(new)* | the registry, the compatibility matrices, the predicate implementations |
| [src/parsers.py](../../../src/parsers.py) | per-phase extraction into `InterfaceData` / `ParsedDevice` |
| [src/criteria_generator.py](../../../src/criteria_generator.py) | emit one rule per (link, applicable attribute); render a new instructions section |
| [src/evaluator.py](../../../src/evaluator.py) | one `elif rule.category == "link_agreement"` branch that resolves both endpoints and applies the predicate |
| [src/feedback.py](../../../src/feedback.py) | guidance entries keyed by attribute, sourced from `why_it_matters` |
| [src/conflict_detector.py](../../../src/conflict_detector.py) | no change; §5 handles overlap |

Points flow through `_normalize_rule_points()` unchanged — it apportions
whatever rules it is handed, so a larger rule count rescales automatically.

### 4.1 Instructions rendering

A new numbered section, in the style of the existing addressing and cabling
tables:

```
6. LINK AGREEMENT REQUIREMENTS
--------------------------------------------------------------------------------
Both ends of each link below must agree on the listed settings. Where a value
is shown as "your choice", any value is accepted provided BOTH ends match.

Endpoint A              | Endpoint B              | Must agree on        | Value
--------------------------------------------------------------------------------
SW1:Gi0/1               | SW2:Gi0/1               | 802.1Q native VLAN   | your choice
SW1:Gi0/1               | SW2:Gi0/1               | allowed VLAN list    | 10,20,99
R1:Gi0/0                | R2:Gi0/0                | OSPF hello interval  | your choice
R1:Se0/0/0              | R2:Se0/0/0              | clock rate (DCE end) | exactly one end
```

---

## 5. Avoiding double penalties

Both the conflict detector and a link rule can observe the same native VLAN
mismatch. The student must lose points once.

**Rule:** the link-agreement rule is authoritative for scoring. The evaluator's
conflict handling must skip any conflict category that a link rule already
covers, matched on `(normalised link key, attribute)`.

Implement as an explicit map so the overlap is visible rather than implied:

```python
_CONFLICT_COVERED_BY_LINK_RULE = {
    "vlan_trunk_mismatch": "trunk_native_vlan",
}
```

`cabling_error` is **not** in this map — cable type is not a link-agreement
attribute and [evaluator.py:511](../../../src/evaluator.py) keeps handling it.

---

## 6. Test plan

Fixtures live in [tests/fixtures.py](../../../tests/fixtures.py); the real
captures in `captures/` are the integration cases.

**Predicate units**
- `equal`: match, mismatch, one side missing, both missing
- `compatible`: every cell of both matrices, especially `passive`+`passive`
  and `auto`+`auto`, which must fail
- `exactly_one`: zero ends set (fail), one end (pass), both ends (fail)
- `reciprocal`: symmetric (pass), one-sided (fail), crossed identities (fail)

**Endpoint resolution**
- rule written A→B matches a student link discovered B→A
- `allow_custom_hostnames` on: renamed devices still resolve by role
- `strict_port_matching` off: equivalent same-speed port satisfies the endpoint

**Generation**
- `applies_when` gating: a lab with no OSPF emits no OSPF link rules
- points still sum to exactly `total_points` after the new rules are added

**Policy**
- `enforce_reference_link_values` off: both ends hello 15 passes
- on: both ends hello 15 fails against a reference of 10

**Overlap**
- a native VLAN mismatch is scored once, not twice

**Regression**
- `PASIC_CORE_SW` (l3_switch) ↔ `IT_DEPARTMENT_SW` (switch) still produce
  trunk link rules across the layer boundary

---

## 7. Why this ordering

Shape A before HSRP, despite HSRP being the more vivid example, because:

1. **One mechanism, six topics.** OSPF, EIGRP, BGP, trunking, EtherChannel and
   PPP all reduce to link-scoped predicates. HSRP would buy one topic.
2. **It retires two ad-hoc implementations** rather than adding a third.
3. **Phase 1 needs no parser work**, so the shape is proven against real
   captures before any parsing risk is taken on.
4. **It pays immediately** — native VLAN mismatch starts counting on day one.

HSRP and STP root election are the natural follow-up: they share the
*computed election* shape (derive the winner from config, compare to intent),
and both are deterministic from configuration alone, so neither needs runtime
state and neither disturbs the no-AI-in-grading boundary.
