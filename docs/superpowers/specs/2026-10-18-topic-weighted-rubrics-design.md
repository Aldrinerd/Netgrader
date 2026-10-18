# Design Spec: Topic-Weighted Rubrics

**Date:** 2026-10-18
**Topic:** Let the instructor decide how a lab's points are split between
configuration topics (static routing, VLANs, IP addressing, ...) before the
instructions sheet is issued, and add static-route grading as the first new
topic on that framework
**Status:** Approved in brainstorming, awaiting written-spec review

---

## 1. The problem

An instructor teaching static routing this week wants static routing to carry
most of the grade. Today they cannot say so. Two things stand in the way.

### 1.1 The point split is implicit

[`generate_criteria_from_topology`](../../../src/criteria_generator.py) gives
every rule a hard-coded base value and then rescales all rules together to the
lab total ([`_normalize_rule_points`](../../../src/criteria_generator.py)):

| Category | Base points per rule |
|---|---|
| `device` | 5 |
| `interface_ip` | 10 |
| `relational_subnet` | 12 (router link) / 10 (LAN or standalone) |
| `interface_status` | 5 |
| `cabling` | 8 |
| `vlan_trunk` | 8 (trunk) / 6 (access) |
| `routing` (OSPF) | 8 |
| `link_agreement` | per attribute, from [`link_attributes.py`](../../../src/link_attributes.py) |
| `gateway` | 5 |
| `security` | 4 / 3 / 3 |
| `documentation` | 2 |

So the share each topic gets is decided by how many rules it produces, not by
what the lesson was about. A lab with many interfaces is graded mostly on IP
addresses and cabling, whatever the lesson was.

### 1.2 The motivating topic is not graded at all

`ip route` lines are parsed into `ParsedDevice.routes` with protocol `"S"`
([parsers.py:166](../../../src/parsers.py)), but no rule is ever generated from
them. The only routing rule is OSPF. "Static routing" cannot be weighted until
it can be graded.

### 1.3 What grading already gets right

The evaluator does not care how points were chosen. It adds up each rule's
`points` ([evaluator.py:393](../../../src/evaluator.py)), and those points
travel inside `instructions.txt` in the embedded criteria JSON. **Weighting is
therefore a rubric-generation concern.** Grading needs exactly one change:
skip rules the instructor turned off (section 4.3).

---

## 2. Goals and non-goals

### Goals

1. After **Generate**, the instructor sees every configuration topic found in
   the reference file, each with a percentage next to it.
2. The instructor can change the percentages, use a **Focus** shortcut, or set
   a topic to 0% to stop grading it.
3. `instructions.txt` is only offered for download after the instructor
   **finalizes** the weights.
4. Accepting the default percentages reproduces today's rubric exactly, point
   for point.
5. Static routes are graded (destination + correct neighbor).
6. Topics the engine cannot grade yet (STP, HSRP, ACLs, ...) are still
   detected and shown, so the instructor knows the lab contains them.
7. Adding a grader for a new topic later is a self-contained change: one
   registry entry plus one module.

### Non-goals

- Grading STP, EtherChannel, port security, HSRP, DHCP, inter-VLAN routing,
  ACLs, NAT, SSH, EIGRP, RIP or IPv6. They are detected only. Each family
  gets its own spec (section 10).
- AI-assisted detection or AI-suggested weights. See decision D1.
- Per-checkpoint point overrides. Weights are per topic.
- Per-topic subtotals in the student grade report.
- Floating static routes (administrative distance is not parsed) and IPv6
  static routes.

---

## 3. Decisions taken in brainstorming

| # | Decision | Why |
|---|---|---|
| D1 | Detection is deterministic: regex/structural checks over the parsed config. No AI. | Rule categories are a closed set derived from parsed config. An LLM would detect nothing the parser cannot, and would make the topic list vary between runs. |
| D2 | One spec, two parts: the weighting framework, and static-route grading as the first new topic. | Static routing is the instructor's own example. Building it alongside proves a new topic plugs in cleanly. |
| D3 | All twelve not-yet-graded topic families are detected now and shown as "not graded yet". | The instructor sees the full picture, and each later spec only has to add a grader. |
| D4 | A 0% topic is **ungraded but still shown** in the instructions. | Students still need the IP table and cabling table to build the lab, even when the lesson grades only routing. |
| D5 | Default percentages reproduce today's split, plus a **Focus** button per topic. | No surprise for instructors who accept the defaults. Focus covers the common "this week's lesson" case in one click. |
| D6 | Static routes are checked by **destination + same neighbor**, mapped to the student's own subnets under dynamic subnetting. | Catches routes aimed at the wrong router without demanding the reference's exact next-hop IP. |
| D7 | Flow is **regenerate with weights**: one endpoint, optional `topic_weights`, files re-sent on Finalize. | Stateless, one code path, the server always computes points, and calls without weights behave exactly as today. |
| D8 | **Light** topic registry. Existing categories keep their current code. New graders live in `src/topics/<topic>.py`. | No rewrite of working code, and `evaluator.py` (900 lines) does not grow by one branch per future topic. |

---

## 4. Design

### 4.1 The topic registry

New module [`src/topics/registry.py`](../../../src/topics/registry.py). One
entry per topic:

```python
@dataclass(frozen=True)
class Topic:
    key: str                          # "static_routing"
    label: str                        # "Static Routing"
    categories: tuple[str, ...]       # rule categories this topic owns
    detect: Callable[[ParsedDevice], bool] | None   # detected-only topics
    gradeable: bool
```

**Gradeable topics (11).** They own every value of `EvaluationRule.category`:

| Key | Label | Owns categories |
|---|---|---|
| `devices` | Device Presence | `device` |
| `ip_addressing` | IP Addressing | `interface_ip`, `relational_subnet` |
| `interface_status` | Interface Status | `interface_status` |
| `cabling` | Cabling | `cabling` |
| `vlans_trunking` | VLANs & Trunking | `vlan_trunk` |
| `ospf` | OSPF | `routing` |
| `static_routing` | Static Routing | `static_route` *(new)* |
| `default_gateways` | Default Gateways | `gateway` |
| `security_baseline` | Security Baseline | `security` |
| `interface_descriptions` | Interface Descriptions | `documentation` |
| `link_agreement` | Link Agreement | `link_agreement` |

The `routing` category keeps its name (stored `instructions.txt` files use
it) and means OSPF. Future routing protocols get their own categories
(`eigrp`, `rip`, ...), never `routing`.

**Invariant:** every category in `EvaluationRule.category` is owned by exactly
one topic. A test enforces this, so a new category cannot ship without a
topic.

**Detected-only topics (12).** `gradeable=False`, `categories=()`, and a
`detect` function:

| Key | Label | Detected when the running-config contains |
|---|---|---|
| `stp` | Spanning Tree | `spanning-tree mode rapid-pvst`, `spanning-tree vlan N priority/root`, `spanning-tree portfast`, `spanning-tree bpduguard` |
| `etherchannel` | EtherChannel | `channel-group N`, `interface Port-channelN` |
| `port_security` | Port Security | `switchport port-security` |
| `hsrp` | HSRP | `standby [N] ip`, `standby [N] priority`, `standby [N] preempt` |
| `dhcp` | DHCP | `ip dhcp pool`, `ip dhcp excluded-address`, `ip helper-address` |
| `inter_vlan_routing` | Inter-VLAN Routing | `encapsulation dot1Q N` on a subinterface, **or** an addressed `interface VlanN` on a device with `ip routing` |
| `acl` | Access Control Lists | `access-list N`, `ip access-list standard/extended`, `ip access-group`, `access-class` |
| `nat` | NAT | `ip nat inside`, `ip nat outside`, `ip nat pool`, `ip nat inside source` |
| `ssh` | SSH | `ip ssh version`, `transport input ssh` |
| `eigrp` | EIGRP | `router eigrp N` |
| `rip` | RIP | `router rip` |
| `ipv6` | IPv6 | `ipv6 unicast-routing`, `ipv6 address`, `ipv6 route`, `ipv6 router` |

**Defaults must not count as detections.** Packet Tracer and IOS print some
lines in every running-config whether or not anyone configured anything:
`spanning-tree mode pvst`, `spanning-tree extend system-id`, `no ipv6 cef`,
`ip cef`. Each detector matches only the patterns above, which are all
explicit configuration. A test feeds a factory-default switch and router
config to every detector and expects no detections.

Detectors are functions of `ParsedDevice`, not bare regexes, because some
need structure. Inter-VLAN routing needs `has_ip_routing`, so a management
SVI on a layer-2 switch is not mistaken for routing.

### 4.2 Detection input: `ParsedDevice.config_lines`

The parser keeps no raw config today. Add:

```python
config_lines: list[str] = Field(default_factory=list, exclude=True)
```

`parse_running_config` appends each stripped line. Both ingestion paths
already go through it: `.pkt`/`.pka`/`.xml` via
[pkt_parser.py:153](../../../src/pkt_parser.py), and `.zip`/`.txt` bundles via
the `show running-config` section of [parsers.py](../../../src/parsers.py). So
detection works for every upload type.

`exclude=True` keeps the lines out of every serialized payload: the
`/api/analyze` and `/api/criteria/generate` topology, `EvaluationReport.topology`,
and anything sent to the chat layers. That matters for response size, and
for the existing rule that raw configuration text never reaches the student
chat.

**When a topic appears on the panel:**

- A **gradeable** topic appears when it produced at least one rule. Policy
  toggles still decide that. Security Baseline appears only when
  `grade_security_baseline` is on, as today.
- A **detected-only** topic appears when its `detect` returns true for at
  least one non-placeholder device in the reference.

For each topic, `devices` lists where it was found: the distinct
`target_device` values of its rules, or the devices whose detector fired.

**EtherChannel overlap.** Link agreement already checks the EtherChannel
*mode* on both ends of a link (`channel_group` attribute). In this spec those
checks stay under Link Agreement, and EtherChannel shows as detected-only.
The EtherChannel spec will move those rules into its own topic.

### 4.3 Data model changes ([models.py](../../../src/models.py))

All new fields default to today's behavior, so existing `instructions.txt`
files parse and grade exactly as before.

```python
class EvaluationRule(BaseModel):
    ...
    category: Literal[..., "static_route"]   # new value
    graded: bool = True                       # False => topic set to 0%

class EvaluationCriteria(BaseModel):
    ...
    topic_weights: dict[str, float] = Field(default_factory=dict)  # topic key -> percent
```

Rules in a 0% topic stay in `criteria.rules` with `graded=False` and
`points=0.0`. They stay because:

- the instructions sheet still renders their tables (D4), and
- the evaluator's device mapping (`_build_device_mapping`) reads **every**
  rule to learn the reference's devices and their types. Removing device
  rules would break hostname matching.

### 4.4 Default percentages

1. Generate rules as today, and run today's global normalization
   (`_normalize_rule_points(all_rules, total)`). Call these the *legacy
   points*.
2. For each gradeable topic that appears, sum its legacy points.
3. Convert to percent of `total_points` and round to tenths with
   largest-remainder apportionment so the percentages sum to exactly 100.0.

Defaults are derived from the *normalized* points, not the base points, so
that at the common total of 100 the default percent equals the topic's actual
points.

### 4.5 Applying weights

Given validated `topic_weights` (section 4.7) that differ from the defaults:

1. **Topic split.** Convert `total_points` to tenths. Split those tenths across
   topics in proportion to their percent, using largest-remainder
   apportionment. Topic totals sum to exactly `total_points`.
2. **0% topics.** Every rule gets `graded=False` and `points=0.0`.
3. **Within a topic.** Reset each rule to its **base points** (a copy taken
   before the legacy normalization in section 4.4), then call the existing
   `_normalize_rule_points(topic_rules, topic_total)`. This keeps today's
   relative weighting inside the topic. Link-agreement attributes worth
   different amounts stay different, and a trunk rule stays worth more than
   an access rule.
4. Record the weights in `criteria.topic_weights`.

**Worked example.** Total 100. Static Routing has 3 rules (base 8 each), and
the instructor presses Focus on it. Static Routing gets 50.0 pts, so its rules
are 16.7 + 16.7 + 16.6. The other topics share the remaining 50.0 in
proportion to their defaults.

### 4.6 Exact backward compatibility

If the request carries **no** `topic_weights`, or weights equal to the
defaults (each value within 0.001), the generator uses today's global
normalization unchanged and records the defaults in `topic_weights`.

Splitting by topic and then within topics can differ from global
normalization by ±0.1 on a few rules because of rounding. This rule makes
"accept the defaults" reproduce today's rubric point for point. It also keeps
every existing test and the validation harness numbers unchanged.

### 4.7 Validation of `topic_weights`

Rejected with HTTP 400 and a message that names the topic:

| Condition | Example message |
|---|---|
| Not valid JSON, or not an object of numbers | `topic_weights must be a JSON object of topic -> percent` |
| Unknown key, or a detected-only topic | `"stp" cannot be weighted: it is not graded yet` |
| A gradeable topic that appears is missing | `Missing a weight for "Cabling"` |
| Value below 0 or above 100 | `"Cabling" must be between 0 and 100` |
| More than one decimal place | `"Cabling" allows one decimal place` |
| Sum not 100 (tolerance ±0.05) | `Weights add up to 97.5%, they must add up to 100%` |
| Every topic at 0% | `At least one topic must carry points` |
| Topic share too small for its checkpoints (under 0.1 pt each after the topic split) | `"Cabling" needs at least 1.2% for its 12 checkpoints` |

The last check exists because a graded rule worth 0 points would be a
pass/fail line that changes nothing. The minimum shown is the smallest
one-decimal percent that gives every checkpoint at least 0.1 pt at the
current total.

### 4.8 Browser-side shortcuts

These only change the numbers in the inputs. The server still validates and
computes everything.

- **Focus (topic T):** set T to 50.0%. The other gradeable topics that carry
  weight scale proportionally to share the remaining 50.0%, rounded to tenths
  with largest remainder so the sum is 100.0. A topic at 0% stays at 0%. If T
  is already at or above 50%, Focus leaves the numbers unchanged. Pressing
  Focus on another topic moves the focus there.
- **Reset to defaults:** restore `default_percent` for every topic.
- **Distribute evenly:** every gradeable topic gets `100 / n`, rounded to
  tenths with largest remainder.

The 50% focus share is a named constant in `app.js` (`FOCUS_SHARE = 50`).

### 4.9 Static-route grader ([`src/topics/static_routes.py`](../../../src/topics/static_routes.py))

```python
def generate_rules(topology: TopologyResult, policies: EvaluationPolicies) -> tuple[list[EvaluationRule], list[str]]
    # -> (rules, reference_warnings)

def evaluate(rule: EvaluationRule, ctx: EvalContext) -> RuleOutcome
```

`EvalContext` is a small dataclass holding what the inline evaluator branches
already use: the student `devices`, `links`, `policies` and `device_mapping`.
`RuleOutcome` holds `points_earned`, `passed`, `actual` and `feedback`. These
two types live in `src/topics/__init__.py` so every future grader shares them.

#### Rule generation

One rule per non-placeholder reference device with at least one static route
(protocol `"S"` in `device.routes`), base **8.0** points, matching OSPF.

- `rule_id`: `static_<hostname-lower>`
- `description`: `Configure static routes on R1 (3 destinations)`

For each static route the generator resolves:

| Field | How |
|---|---|
| `network`, `cidr` | from the route |
| `is_default` | `0.0.0.0/0` |
| `dest_device`, `dest_interface` | the reference interface whose network equals the destination. `null` if the route is a default route or matches no interface, for example a summary route ("unmappable"). |
| `via_device`, `via_interface` | next-hop IP form: the reference device and interface that own that IP. Exit-interface form: the device at the far end of the link on that interface. |
| `style` | `"next_hop"` or `"exit_interface"` |

```python
expected_value = {"routes": [
    {"network": "192.168.2.0", "cidr": 24, "is_default": False,
     "dest_device": "R2", "dest_interface": "GigabitEthernet0/1",
     "via_device": "R2", "via_interface": "Serial0/0/0", "style": "next_hop"},
    ...
]}
```

**Broken reference routes are skipped.** If the neighbor cannot be resolved
(the next hop belongs to no device, or the exit interface has no link), the
route is left out and a line is added to
`criteria.reference_summary["reference_warnings"]`, for example
`R1: static route to 10.9.0.0/16 via 10.0.0.99 points at no device, so it was not graded`.
This follows the link-agreement rule: never grade a requirement the
instructor's own file fails, because it would put 100% out of reach for the
whole class. A device whose routes are all skipped gets no rule.

#### Evaluation

The student device is found through the existing `_find_student_device` and
device mapping. Candidate routes are the student device's protocol `"S"`
entries in `device.routes`. These come from `ip route` lines, or from
`show ip route` in a text bundle.

For each required route:

1. **Expected destination**
   - default route: `0.0.0.0/0`
   - exact addressing (`allow_dynamic_subnetting` off): the reference
     `network`/`cidr`
   - dynamic subnetting, mappable: the network of the student's counterpart
     of `dest_interface` on the student's counterpart of `dest_device`
     (`_find_student_interface`, honoring `strict_port_matching`). If that
     interface has no address, the route fails with
     `destination LAN on R2 G0/1 has no address`.
   - dynamic subnetting, unmappable: no destination check. Only the
     neighbor is checked, and the instructions sheet says so.
2. **Correct neighbor:** the student's counterpart of `via_device` is N. A
   candidate route satisfies the requirement when either:
   - its next-hop IP lies inside a subnet of one of the student device's own
     addressed interfaces (directly connected) **and** belongs to an
     interface on N, or
   - its exit interface is linked, in the student topology, to any interface
     on N.

**Scoring:** points × satisfied / required, rounded to one decimal. Passed
only when every required route is satisfied. This is the same partial-credit
model as OSPF (issue #1).

**Feedback** names each unmet route and its reason:

- `no static route to 192.168.2.0/24`
- `route to 192.168.2.0/24 points at R3, it should go via R2`
- `next hop 10.0.0.9 is not on a network directly connected to R1`

#### Guidance and study topic ([feedback.py](../../../src/feedback.py))

- `_TOPICS["static_route"]`: "Static routing and next-hop selection". Why it
  matters: a static route only works if it names the right destination and
  hands traffic to a neighbor that can actually forward it.
- `_HANDLERS["static_route"]`: `_explain_static_route`, with separate
  guidance for a missing destination, the wrong neighbor, and a next hop that
  is not directly connected. This matches the existing
  `test_guidance_distinguishes_failure_modes_within_a_category` pattern.

### 4.10 API ([app.py](../../../src/app.py))

`POST /api/criteria/generate` gains one form field:

```
topic_weights: str = Form("")      # JSON object, e.g. {"static_routing": 50, "ip_addressing": 18.2, ...}
```

The response gains `topics`:

```json
"topics": [
  {"key": "static_routing", "label": "Static Routing", "gradeable": true,
   "devices": ["R1", "R2", "R3"], "checkpoints": 3,
   "default_percent": 7.4, "percent": 50.0, "points": 50.0},
  {"key": "stp", "label": "Spanning Tree", "gradeable": false,
   "devices": ["S1", "S2"], "checkpoints": 0,
   "default_percent": null, "percent": null, "points": null}
]
```

- `percent` is the weight applied: the defaults when none were sent.
- `points` is the actual subtotal of the topic's rules.
- Order: gradeable topics in registry order, then detected-only topics in
  registry order.
- The response still always includes `instructions_txt` and `criteria`, so
  scripts and existing tests are unaffected. The finalize gate is a UI rule.
- The response also gains a top-level `reference_warnings: list[str]`, a
  copy of `criteria.reference_summary["reference_warnings"]` (empty list when
  there are none).

The "nothing gradeable" guard ([app.py:308](../../../src/app.py)) counts only
**graded** non-device rules after weighting. A request that zeroes everything
except Device Presence is rejected for the same reason the guard exists.

**Batch grading** ([app.py:493](../../../src/app.py)): on a parse error,
`failed_count` counts graded rules (`sum(r.graded for r in criteria.rules)`).
`max_score` is already right, because ungraded rules carry 0 points.

### 4.11 Evaluator ([evaluator.py](../../../src/evaluator.py))

- `_build_device_mapping` is unchanged and still reads every rule.
- The main loop skips `graded=False` rules first: no result row, nothing added
  to `max_score`, `passed_count` or `failed_count`.
- Dispatch: a rule whose category belongs to a registry grader module
  (`static_route` today) is passed to that module's `evaluate`. The existing
  inline branches stay as they are.

### 4.12 UI flow ([index.html](../../../templates/index.html), [app.js](../../../static/js/app.js), [style.css](../../../static/css/style.css))

A **Grading weights** panel is added to the Teacher Studio result card,
above the instructions preview:

```
Grading weights                                     Total: 100.0% ✓
 Static Routing     3 checkpts  R1,R2,R3   [ 50.0]% ▓▓▓▓▓   ≈50.0 pts  [Focus]
 IP Addressing     14 checkpts             [ 18.2]% ▓▓      ≈18.2 pts  [Focus]
 Cabling           12 checkpts             [  0.0]% ░   reference only [Focus]
 ...
 Detected, not graded yet:  Spanning Tree (S1, S2) · HSRP (R1, R2) · DHCP (R1)
 ⚠ R1: static route to 10.9.0.0/16 via 10.0.0.99 points at no device, so it was not graded
                       [Reset to defaults]  [Distribute evenly]  [Finalize rubric]
```

**States:**

| State | Entered by | Panel | Preview, Download, Copy |
|---|---|---|---|
| `idle` | page load, Clear | hidden | hidden |
| `weighting` | Generate succeeds | shown, editable | hidden |
| `finalized` | Finalize succeeds | shown, editable | shown and enabled |
| `stale` | any weight edit while `finalized` | shown, editable | preview marked "out of date", Download and Copy disabled |

**Behavior:**

- **Generate** sends the form with no `topic_weights` and fills the panel from
  `topics`.
- **Finalize** is enabled only when the inputs sum to 100.0% (±0.05). It sends
  the same files and form fields plus `topic_weights`. On success it shows the
  returned `instructions_txt` and updates the rules badge to show graded
  checkpoints. On a 400 it shows the server's message next to the panel and
  stays in its current state.
- The total indicator turns red, and Finalize is disabled, whenever the sum
  is off.
- **Changing files or any policy toggle** after Generate returns to `idle`,
  because the topic list may change. Changing the title or description does
  not.
- **Changing total points** recomputes the "≈ pts" previews and does not
  invalidate the panel, because weights are percentages.
- Topic labels, device names and warning text are inserted with
  `escapeHtml`, following the file-derived-text escaping fix (8cdd300).
- The student view's checkpoint count after `/api/criteria/parse`
  ([app.js:647](../../../static/js/app.js)) counts graded rules only.

### 4.13 instructions.txt ([criteria_generator.py](../../../src/criteria_generator.py))

**Section numbering is computed** in output order instead of hard-coded.
Sections are already skipped when empty, which leaves gaps today. Order:

1. Lab Overview & Objectives
2. Instructor Evaluation Policies
3. **Grading Weights** *(new)*
4. IP Addressing (or Dynamic & Relational Subnetting)
5. Physical Cabling & Port Connections
6. Switching & VLAN Specifications
7. **Static Routing Requirements** *(new)*
8. Link Agreement Requirements
9. Rubric & Point Breakdown

**Grading Weights section:**

```
3. GRADING WEIGHTS
--------------------------------------------------------------------------------
Topic                     | Weight  | Points   | Checkpoints
--------------------------------------------------------------------------------
Static Routing            |  50.0 % |  50.0 pts|  3
IP Addressing             |  18.2 % |  18.2 pts| 14
Cabling                   |   0.0 % | reference only, not graded
```

The table lists the gradeable topics that appear, in registry order.
Detected-only topics are instructor information and are not printed in the
student sheet.

**Reference-only sections.** A section whose topic is at 0% still prints in
full, with `(REFERENCE ONLY, NOT GRADED)` appended to its heading.

**Static Routing Requirements section:**

```
Device   | Destination                        | Via neighbor
R1       | 192.168.2.0/24                     | R2
R1       | default route (0.0.0.0/0)          | R2
```

Under dynamic subnetting, the destination is written as
`LAN on R2 GigabitEthernet0/1 (/24)`. An unmappable destination is written as
`10.0.0.0/8 summary, any static route via R2 accepted`.

**Rubric & Point Breakdown** is grouped by topic, each with a subtotal line.
Graded topics come first, in registry order. 0% topics follow under
`REFERENCE ONLY (NOT GRADED)`, listing their checkpoint descriptions without
points. That way topics with no table section of their own, such as OSPF or
default gateways, are still visible to students (D4).

**Header:** `Total Checkpoints` counts graded rules.

**Embedded criteria JSON** carries `topic_weights` and each rule's `graded`.
`parse_instructions_txt` needs no change, because both fields have defaults.

---

## 5. Touch points

| File | Change |
|---|---|
| `src/topics/__init__.py` | new: `EvalContext`, `RuleOutcome` |
| `src/topics/registry.py` | new: `Topic`, `TOPICS`, detectors, `topic_for_category()` |
| `src/topics/static_routes.py` | new: `generate_rules`, `evaluate` |
| `src/models.py` | `static_route` category, `EvaluationRule.graded`, `EvaluationCriteria.topic_weights`, `ParsedDevice.config_lines` |
| `src/parsers.py` | `parse_running_config` fills `config_lines` |
| `src/criteria_generator.py` | static-route rules, topic summary, default percentages, weight application, legacy path, instructions sections and numbering |
| `src/evaluator.py` | skip ungraded rules, dispatch to registry graders |
| `src/feedback.py` | `static_route` topic and guidance handler |
| `src/app.py` | `topic_weights` field, validation, `topics` and warnings in response, graded-only guard, batch `failed_count` |
| `templates/index.html` | weights panel markup |
| `static/js/app.js` | panel rendering, state machine, Focus / Reset / Distribute, Finalize, escaping, graded checkpoint count |
| `static/css/style.css` | panel styles, light and dark |
| `validation/reference.py`, `validation/mutations.py`, `validation/harness.py` | static-route reference and mutations (section 7) |
| `docs/SYSTEM.md`, `README.md`, `docs/DEVELOPMENT_LOG.md` | documentation (section 8) |

---

## 6. Error handling

| Situation | Behavior |
|---|---|
| Invalid `topic_weights` | 400 with a topic-specific message (section 4.7). The UI shows it next to the panel and stays in its current state. |
| Weights that leave no graded non-device rule | 400 via the existing "nothing gradeable" guard |
| Reference static route with an unresolvable neighbor | skipped and listed in `reference_warnings`. Generation still succeeds. |
| Student device missing for a static-route rule | 0 points, `Cannot evaluate static routes: device 'R1' missing`, the same pattern as OSPF |
| Old `instructions.txt` without `graded` or `topic_weights` | parses with defaults (`graded=True`, `{}`) and grades exactly as before |
| Instructions with a `static_route` rule given to an older server | rejected by the old category Literal. Expected, and documented in the release note. |

---

## 7. Testing plan

All tests are new unless marked. TDD order follows the implementation plan.

**Weighting math** (`tests/test_topic_weights.py`)

- Topic totals and rule points sum exactly to `total_points` for totals 100,
  50, 37 and 1000.
- The split within a topic is proportional to today's base weights.
- No weights, and weights equal to the defaults, both produce output
  identical to today, rule for rule.
- Default percentages sum to exactly 100.0.
- A 0% topic produces `graded=False` and `points=0.0` for every rule.
- Every validation row in section 4.7 returns 400 with its message.
- The minimum-share message gives the correct minimum percent.

**Registry and detection** (`tests/test_topic_registry.py`)

- Every `EvaluationRule.category` value is owned by exactly one topic.
- Each detector fires on a fixture config line for its topic.
- A factory-default switch config and router config produce zero
  detections, including `spanning-tree mode pvst` and `no ipv6 cef`.
- A management SVI on an L2 switch is not detected as inter-VLAN routing.
- `config_lines` is filled on both the `.pkt` path and the bundle path, and
  is absent from `model_dump()`.

**Static routes** (`tests/test_static_routes.py`)

- Pass, partial credit and fail.
- A route pointing at the wrong neighbor fails with "should go via".
- A next hop that is not directly connected fails.
- The default route.
- The exit-interface form.
- Mapping to the student's own subnets under dynamic subnetting.
- An unmappable summary destination under dynamic subnetting (neighbor-only
  check).
- A broken reference route is skipped and reported.
- A missing student device.
- Renamed devices under `allow_custom_hostnames`.

**Feedback** (`tests/test_feedback.py`, extended): the existing coverage
tests pick up `static_route` automatically. Add one test for its failure
modes.

**Instructions** (`tests/test_criteria_generator.py`, extended)

- The Grading Weights section.
- Reference-only headings.
- The Static Routing section in both addressing modes.
- Topic-grouped rubric with subtotals.
- Consecutive section numbers.
- Round-trip through `parse_instructions_txt` keeps `graded` and
  `topic_weights`.

**Evaluator and API** (`tests/test_evaluator.py`, `tests/test_app.py`,
`tests/test_batch_grading.py`, extended)

- Ungraded rules are absent from results and counts, but device mapping
  still works when Device Presence is at 0%.
- `topics` in the response.
- A weighted generate.
- A 400 for each bad-weights class.
- Batch `failed_count` counts graded rules.

**Frontend**

- `tests/test_frontend_escaping.py` (extended): topic labels, device names
  and warnings are escaped.
- `tests/test_e2e_live_server.py` (extended): generate, Focus, Finalize,
  download enabled. A weight edit after finalize disables download.

**Validation harness.** A separate static-routing reference is added in
`validation/reference.py` rather than editing the existing one, so the 25
existing cases and their numbers stay unchanged. `Mutation` gains
`reference: str = "default"`, and the harness grades each mutation against
its named reference. New cases:

- *positive*: a static route deleted; a static route pointed at the wrong
  neighbor
- *negative*: a valid static route using the exit-interface form instead of
  a next hop; different but self-consistent addressing under dynamic
  subnetting

---

## 8. Documentation updates (part of the implementation, not a follow-up)

| Document | Update |
|---|---|
| [`docs/SYSTEM.md`](../../SYSTEM.md) §2 Module map | add `src/topics/` |
| §3 The grading model | new subsection "Topics and weights": the registry, defaults, the weighting algorithm, 0% semantics and the legacy path. Add `static_route` to the §3.1 category table. |
| §9 Interfaces | the weights panel and its states; `topic_weights` and `topics` on `/api/criteria/generate` |
| §10 Known limits | detected-only topics; floating and IPv6 static routes not graded; EtherChannel mode still under Link Agreement |
| [`README.md`](../../../README.md) | Teacher Studio walkthrough: Generate, adjust weights, Finalize, Download |
| [`docs/DEVELOPMENT_LOG.md`](../../DEVELOPMENT_LOG.md) | dated entry describing the feature and decisions D1–D8 |
| Code | docstrings on every new public function. The module docstring of `registry.py` contains the "Adding a topic" checklist in section 10. |

---

## 9. Out of scope and known limits

- **Detected-only topics carry no points.** An instructor who wants STP
  graded this term has to wait for that family's spec.
- **Detection runs on the reference only.** The student's config is not
  scanned for extra topics.
- **Floating static routes.** Administrative distance is not parsed, so a
  primary route and its floating backup to the same destination via
  different neighbors are graded as two independent requirements.
- **IPv6 static routes** belong to the IPv6 family spec.
- **Weights are per topic.** An instructor cannot make one checkpoint worth
  more than another within a topic.

---

## 10. Follow-up specs and the "Adding a topic" checklist

Each family below gets its own spec → plan → implementation cycle. Each turns
one or more detected-only topics into gradeable ones:

1. STP / EtherChannel / Port Security (EtherChannel takes over the
   `channel_group` link-agreement rules)
2. HSRP / DHCP / Inter-VLAN Routing
3. ACL / NAT / SSH
4. EIGRP / RIP / IPv6

**Adding a topic** (copied into the `registry.py` docstring):

1. Parse what the grader needs into `ParsedDevice` / `InterfaceData`.
2. Add the rule category to `EvaluationRule.category`.
3. Write `src/topics/<topic>.py` with `generate_rules` and `evaluate`.
   Handle dynamic subnetting and custom hostnames through `EvalContext`.
4. In the registry entry, set `categories` and `gradeable=True`. Keep
   `detect` for completeness.
5. Add a `_TOPICS` entry and a guidance handler in `feedback.py`.
6. Add an instructions section if students need a table.
7. Add tests for the grader, plus at least one positive and one negative
   validation mutation.
8. Update `docs/SYSTEM.md` §3.1 and §10.
