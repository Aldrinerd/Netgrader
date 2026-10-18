# Topic-Weighted Rubrics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an instructor split a lab's points between configuration topics (Focus on this week's lesson, set a topic to 0%) before `instructions.txt` is issued, and grade static routes as the first new topic.

**Architecture:** A light topic registry (`src/topics/registry.py`) maps every rule category to one topic and detects twelve not-yet-graded topics deterministically from the running-config. A weights module (`src/topics/weights.py`) derives the default split from today's rubric and applies a requested split by largest-remainder apportionment. `/api/criteria/generate` takes an optional `topic_weights` and is called twice by the Teacher Studio: Generate (show topics), then Finalize (apply weights, build the sheet). Static routes are graded by `src/topics/static_routes.py` through an `EvalContext`, so the evaluator does not grow a branch per topic.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, pytest, vanilla JS (no build step), plain CSS. No new dependencies.

**Spec:** [docs/superpowers/specs/2026-10-18-topic-weighted-rubrics-design.md](../specs/2026-10-18-topic-weighted-rubrics-design.md). Read it before Task 1. Decisions D1–D8 there are settled. Do not reopen them.

## Global Constraints

- No new runtime or dev dependencies. `requirements.txt` and `requirements-dev.txt` stay unchanged.
- No `topic_weights`, or weights equal to the defaults (each within 0.001), must reproduce today's rubric point for point.
- All point and percent arithmetic is in integer tenths, using largest-remainder apportionment. Rubric totals are exact.
- Weight values: 0–100, at most one decimal place, sum 100 ± 0.05.
- Focus share: `FOCUS_SHARE = 50` (percent), a named constant in `static/js/app.js`.
- A static-route rule's base points: `8.0`.
- `ParsedDevice.config_lines` is declared with `exclude=True`, so it never appears in any serialized payload.
- File-derived text (device names, warnings) reaches `innerHTML` only through `escapeHtml()`.
- Old `instructions.txt` files parse and grade unchanged: `graded` defaults to `True`, `topic_weights` to `{}`.
- Existing `instructions.txt` section titles keep their exact wording. Tests assert `DYNAMIC & RELATIONAL SUBNETTING POLICY` and `Security Baseline      : GRADED`.
- Baseline before Task 1: **306 tests pass** and `python -m validation` reports 100% on every metric. Both must still hold after every task, apart from the counts each task deliberately adds.
- Stage files only by explicit path (`git add <path> ...`). Never `git add -A` or `git add .`. The working tree holds untracked files that are not part of this work (`system.zip`, `implementation_plan.md`).
- Every commit message ends with the line `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. A text bundle carrying both `ip route` lines and a `show ip route` section. Expected: each static route is required once, not twice. Test: Task 2, `test_routing_table_entries_count_once_and_star_means_static`.
2. A routing-table default route printed as `S*`. Expected: it counts as static, in the reference and in a student submission. Test: Task 2, same test.
3. Weight values sent as whole numbers (`50`), strings (`"50"`), booleans, or thirds (33.3/33.3/33.4). Expected: whole numbers are accepted as floats; strings and booleans are rejected with the format message; float sums within tolerance are accepted. Tests: Task 4, `INVALID` cases and `test_whole_numbers_and_float_sums_are_accepted`.
4. A reference static route whose next hop is the router's own address, or whose exit interface leads to an `UNKNOWN_PORT_…` placeholder or to no link. Expected: the route is skipped with a warning, never a crash and never a rule the reference itself fails. Test: Task 2, `test_broken_reference_routes_are_skipped_and_reported`.
5. A student topology where the routed device exists only as a placeholder. Expected: treated as missing, 0 points, no exception. Test: Task 2, `test_missing_or_placeholder_student_device_scores_zero`.

## Deviations from the spec (decided while planning)

- `EvalContext` also carries `find_device` and `find_interface` callables, built by a new `make_eval_context()` in `src/evaluator.py`. Grader modules therefore never import the evaluator, which would be a circular import (evaluator → registry → graders).
- `topic_summary()` lives in `src/topics/weights.py`.
- The repository has no browser test runner. The UI flow (Generate → Focus → Finalize → download, stale on edit) is verified in the built-in browser in Task 7. The live-server test covers the HTTP round trip.

---

## Task 0: Precondition, user action (not code)

The working tree currently holds **uncommitted work this feature builds on**: OSPF coverage, chat safeguards, letter-grade removal and the deployment brief. These are the DEVELOPMENT_LOG entries dated 2026-10-16 and 2026-10-18, plus the untracked `src/ospf.py`, `src/integrity.py`, `src/chat_guard.py`, `tests/test_ospf.py`, `tests/test_chat_safeguards.py` and `docs/DEPLOYMENT_SECURITY.md`. `src/criteria_generator.py` and `src/evaluator.py` already import `src/ospf.py`.

Tasks 1–9 edit the same files (`src/models.py`, `src/parsers.py`, `src/criteria_generator.py`, `src/evaluator.py`, `src/app.py`, `static/js/app.js`, …). Committing them now would sweep that pending work into this feature's commits.

- [ ] **Step 1:** The user commits the pending work on the branch it belongs to.
- [ ] **Step 2:** Rebase this branch onto it: `git rebase <that-branch>` while on `feature/topic-weighted-rubrics`.
- [ ] **Step 3:** Confirm the baseline. Run `git status --porcelain`. Expected: only `?? system.zip` and `?? implementation_plan.md`, or nothing. Run `python -m pytest -q`. Expected: `306 passed`.

Do not start Task 1 until all three steps hold.

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `src/topics/__init__.py` | create | Package docstring; `EvalContext` and `RuleOutcome`, the contract between grader modules and the evaluator |
| `src/topics/registry.py` | create | `Topic`, `TOPICS`, `TOPICS_BY_KEY`, `topic_for_category()`, `detect_topics()`, detectors, the "Adding a topic" checklist |
| `src/topics/static_routes.py` | create | `is_static()`, `destination_label()`, `generate_rules()`, `evaluate()` |
| `src/topics/weights.py` | create | `largest_remainder()`, `normalize_rule_points()` (moved from the generator), `rules_by_topic()`, `default_weights()`, `validate_weights()`, `same_weights()`, `apply_weights()`, `minimum_percent()`, `topic_summary()`, `TopicWeightError` |
| `src/models.py` | modify | `ParsedDevice.config_lines`, `"static_route"` category, `EvaluationRule.graded`, `EvaluationCriteria.topic_weights` |
| `src/parsers.py` | modify | `parse_running_config()` fills `config_lines` |
| `src/criteria_generator.py` | modify | Topic grader loop, reference warnings, defaults and weights, `instructions.txt` sections |
| `src/evaluator.py` | modify | `make_eval_context()`, dispatch to topic graders, skip ungraded rules |
| `src/feedback.py` | modify | `static_route` study topic and guidance |
| `src/app.py` | modify | `topic_weights` form field, 400s, `topics` and `reference_warnings` in the response, graded-only guard, batch `failed_count` |
| `templates/index.html` | modify | Weights panel markup |
| `static/js/app.js` | modify | Weights panel state machine and handlers |
| `static/css/style.css` | modify | Weights panel styles, disabled buttons |
| `validation/reference.py`, `validation/mutations.py`, `validation/harness.py` | modify | Static-routing reference and four cases |
| `tests/fixtures.py` | modify | `static_chain` bundle |
| `tests/test_topic_registry.py`, `tests/test_static_routes.py`, `tests/test_topic_weights.py` | create | New unit and integration tests |
| `tests/test_feedback.py`, `tests/test_criteria_generator.py`, `tests/test_app.py`, `tests/test_batch_grading.py`, `tests/test_e2e_live_server.py`, `tests/test_frontend_escaping.py`, `tests/test_validation.py` | modify | Extended tests |
| `docs/SYSTEM.md`, `README.md`, `docs/DEVELOPMENT_LOG.md` | modify | Documentation |

---

## Task 1: Topic registry and deterministic detection

**Files:**
- Create: `src/topics/__init__.py`, `src/topics/registry.py`, `tests/test_topic_registry.py`
- Modify: `src/models.py` (`ParsedDevice`), `src/parsers.py` (`parse_running_config`)

**Interfaces:**
- Consumes: nothing new.
- Produces:
  - `ParsedDevice.config_lines: list[str]`
  - `Topic(key, label, categories=(), gradeable=False, detect=None, generate=None, evaluate=None)`
  - `TOPICS: tuple[Topic, ...]`, `TOPICS_BY_KEY: dict[str, Topic]`
  - `topic_for_category(category: str) -> Topic`
  - `detect_topics(topology: TopologyResult) -> dict[str, list[str]]`, mapping topic key to sorted hostnames
  - In this task `static_routing` is detected-only. Task 3 makes it gradeable.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_topic_registry.py`:

```python
# tests/test_topic_registry.py
"""
The topic registry: every rule category belongs to exactly one topic, and
the detected-only topics are found from explicit configuration only.
"""
import os

import pytest
from fastapi.testclient import TestClient

from src.app import app
from src.models import EvaluationRule, ParsedDevice, TopologyResult
from src.parsers import parse_device_bundle
from src.pkt_parser import parse_pkt_file
from src.topics.registry import TOPICS, TOPICS_BY_KEY, detect_topics, topic_for_category
from tests.fixtures import network_bundle

ALL_CATEGORIES = set(EvaluationRule.model_fields["category"].annotation.__args__)
SAMPLE_XML = os.path.join(os.path.dirname(__file__), "fixtures", "sample_topology.xml")


def _device_from(config: str) -> ParsedDevice:
    return parse_device_bundle(config, "D1.txt")


def test_every_rule_category_has_exactly_one_topic():
    owners: dict[str, str] = {}
    for topic in TOPICS:
        for category in topic.categories:
            assert category not in owners, f"{category} owned by {owners[category]} and {topic.key}"
            owners[category] = topic.key
    assert set(owners) == ALL_CATEGORIES


def test_registry_entries_are_well_formed():
    keys = [t.key for t in TOPICS]
    assert len(keys) == len(set(keys))
    for topic in TOPICS:
        if topic.gradeable:
            assert topic.categories, topic.key
        else:
            assert not topic.categories and topic.detect is not None, topic.key


def test_topic_for_category():
    assert topic_for_category("routing").key == "ospf"
    assert topic_for_category("relational_subnet").key == "ip_addressing"
    assert topic_for_category("interface_ip") is TOPICS_BY_KEY["ip_addressing"]


DETECTION_CASES = [
    ("static_routing", "hostname R1\nip route 192.168.2.0 255.255.255.0 10.0.0.2\n"),
    ("stp", "hostname S1\nspanning-tree mode rapid-pvst\n"),
    ("stp", "hostname S1\nspanning-tree vlan 10 priority 4096\n"),
    ("stp", "hostname S1\ninterface FastEthernet0/1\n spanning-tree portfast\n"),
    ("etherchannel", "hostname S1\ninterface FastEthernet0/1\n channel-group 1 mode active\n"),
    ("port_security", "hostname S1\ninterface FastEthernet0/1\n switchport port-security\n"),
    ("hsrp", "hostname R1\ninterface GigabitEthernet0/0\n standby 1 ip 192.168.1.254\n"),
    ("dhcp", "hostname R1\nip dhcp pool LAN\n network 192.168.1.0 255.255.255.0\n"),
    ("dhcp", "hostname R1\ninterface GigabitEthernet0/0\n ip helper-address 10.0.0.5\n"),
    ("inter_vlan_routing", "hostname R1\ninterface GigabitEthernet0/0.10\n encapsulation dot1Q 10\n"),
    ("acl", "hostname R1\naccess-list 10 permit 192.168.1.0 0.0.0.255\n"),
    ("acl", "hostname R1\nip access-list extended BLOCK\n"),
    ("nat", "hostname R1\ninterface GigabitEthernet0/0\n ip nat inside\n"),
    ("ssh", "hostname R1\nip ssh version 2\n"),
    ("ssh", "hostname R1\nline vty 0 4\n transport input ssh\n"),
    ("eigrp", "hostname R1\nrouter eigrp 100\n"),
    ("rip", "hostname R1\nrouter rip\n version 2\n"),
    ("ipv6", "hostname R1\nipv6 unicast-routing\n"),
]


@pytest.mark.parametrize("key,config", DETECTION_CASES)
def test_detector_fires_on_explicit_config(key, config):
    assert TOPICS_BY_KEY[key].detect(_device_from(config))


FACTORY_SWITCH = """hostname Switch
!
spanning-tree mode pvst
spanning-tree extend system-id
!
interface FastEthernet0/1
!
interface Vlan1
 no ip address
 shutdown
!
line con 0
!
line vty 0 4
 login
line vty 5 15
 login
!
end
"""

FACTORY_ROUTER = """hostname Router
!
ip cef
no ipv6 cef
!
interface GigabitEthernet0/0
 no ip address
 duplex auto
 speed auto
 shutdown
!
ip classless
!
ip flow-export version 9
!
line con 0
!
line aux 0
!
line vty 0 4
 login
!
end
"""


@pytest.mark.parametrize("config", [FACTORY_SWITCH, FACTORY_ROUTER])
def test_factory_default_config_detects_nothing(config):
    device = _device_from(config)
    assert [t.key for t in TOPICS if t.detect and t.detect(device)] == []


def test_management_svi_on_layer2_switch_is_not_inter_vlan_routing():
    config = "hostname S1\ninterface Vlan99\n ip address 192.168.99.2 255.255.255.0\nip default-gateway 192.168.99.1\n"
    assert not TOPICS_BY_KEY["inter_vlan_routing"].detect(_device_from(config))


def test_routed_svis_are_inter_vlan_routing():
    config = "hostname MLS1\nip routing\ninterface Vlan10\n ip address 192.168.10.1 255.255.255.0\n"
    assert TOPICS_BY_KEY["inter_vlan_routing"].detect(_device_from(config))


def test_config_lines_are_captured_but_never_serialized():
    device = _device_from("hostname R1\n!\nrouter rip\n")
    assert device.config_lines == ["hostname R1", "!", "router rip"]
    assert "config_lines" not in device.model_dump()
    assert "config_lines" not in device.model_dump_json()


def test_pkt_upload_feeds_detection():
    with open(SAMPLE_XML, "rb") as f:
        devices, links = parse_pkt_file(f.read(), filename="sample_topology.xml")
    found = detect_topics(TopologyResult(devices=devices, links=links, conflicts=[]))
    # Every router in the sample allows `transport input telnet ssh`.
    assert any(name.startswith("Router") for name in found.get("ssh", []))


def test_analyze_response_carries_no_raw_config():
    client = TestClient(app, client=("127.0.0.1", 50000))
    bundle = network_bundle("ospf_clean")
    files = [("files", (name, text.encode("utf-8"), "text/plain")) for name, text in bundle.items()]
    data = client.post("/api/analyze", files=files).json()
    assert data["devices"]
    assert all("config_lines" not in dev for dev in data["devices"].values())
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_topic_registry.py -v`
Expected: collection ERROR, `ModuleNotFoundError: No module named 'src.topics'`.

- [ ] **Step 3: Add `config_lines` to `ParsedDevice`**

In `src/models.py`, in `class ParsedDevice`, after `vlans: dict[int, str] = Field(default_factory=dict)`, add:

```python
    # Every non-blank running-config line, stripped. Read by topic detection
    # (src/topics/registry.py) and never serialized: raw configuration text
    # must not reach API responses or the chat layers.
    config_lines: list[str] = Field(default_factory=list, exclude=True)
```

- [ ] **Step 4: Capture lines in the parser**

In `src/parsers.py`, `parse_running_config()`, directly after the line `stripped = line.strip()` inside the `for idx, line in enumerate(lines):` loop, add:

```python
        if stripped:
            device.config_lines.append(stripped)
```

- [ ] **Step 5: Create the package and the registry**

Create `src/topics/__init__.py`:

```python
# src/topics/__init__.py
"""
Configuration topics: what a lab teaches, as opposed to what a rule checks.

registry.py   which topics exist, which rule categories each owns, and how
              each is detected in a reference file
weights.py    how a lab's points are split between topics
<topic>.py    a grader for one topic (static_routes.py is the first)
"""
```

Create `src/topics/registry.py`:

```python
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


def _inter_vlan_routing(device: ParsedDevice) -> bool:
    if _config_matches(r"^encapsulation\s+dot1q\s+\d+")(device):
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
    Topic("static_routing", "Static Routing",
          detect=_config_matches(r"^ip\s+route\s+\d")),
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
```

- [ ] **Step 6: Run the new tests**

Run: `python -m pytest tests/test_topic_registry.py -v`
Expected: all PASS. If `test_pkt_upload_feeds_detection` fails, print `found` and the router hostnames, then fix the assertion's name check (the sample's routers are named `Router1`–`Router5`). Do not loosen the detector.

- [ ] **Step 7: Run the full suite**

Run: `python -m pytest -q`
Expected: `306 passed` plus the new tests, no failures.

- [ ] **Step 8: Commit**

```bash
git add src/topics/__init__.py src/topics/registry.py src/models.py src/parsers.py tests/test_topic_registry.py
git commit -m "feat(topics): add topic registry with deterministic detection" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 2: Static-route grader module

**Files:**
- Create: `src/topics/static_routes.py`, `tests/test_static_routes.py`
- Modify: `src/topics/__init__.py` (add types), `src/models.py` (category), `src/evaluator.py` (`make_eval_context`), `src/feedback.py`, `tests/test_feedback.py`, `tests/fixtures.py`

**Interfaces:**
- Consumes: `ParsedDevice`, `RouteEntry`, `EvaluationRule`, and `normalize_interface_name` from `src.parsers`.
- Produces:
  - `EvalContext(devices, links, policies, device_mapping, find_device, find_interface)` and `RuleOutcome(points_earned, passed, actual, feedback)` in `src/topics/__init__.py`
  - `make_eval_context(criteria: EvaluationCriteria, student_topology: TopologyResult) -> EvalContext` in `src/evaluator.py`
  - `is_static(route: RouteEntry) -> bool`
  - `destination_label(route: dict, dynamic: bool) -> str`
  - `generate_rules(topology, policies) -> tuple[list[EvaluationRule], list[str]]`
  - `evaluate(rule, ctx) -> RuleOutcome`
  - fixture bundle `network_bundle("static_chain")`

In this task nothing calls `generate_rules` from the generator. Task 3 wires it in. That way no `static_route` rule can reach the evaluator's catch-all `else` branch, which awards full points.

- [ ] **Step 1: Add the `static_chain` fixture**

In `tests/fixtures.py`, add to the module docstring's list:

```
  network_bundle("static_chain")          R1 routing to two branch LANs by static route
```

Add this entry to `PRESET_FILES`, after `"vlan_trunk_mismatch"`:

```python
    "static_chain": {
        "R1.txt": """R1# show running-config
hostname R1
!
interface GigabitEthernet0/0
 description Link to R2
 ip address 10.0.12.1 255.255.255.252
!
interface GigabitEthernet0/1
 description Link to R3
 ip address 10.0.13.1 255.255.255.252
!
interface GigabitEthernet0/2
 description HQ LAN
 ip address 192.168.1.1 255.255.255.0
!
ip route 192.168.2.0 255.255.255.0 10.0.12.2
ip route 192.168.3.0 255.255.255.0 GigabitEthernet0/1
!
R1# show cdp neighbors detail
-------------------------
Device ID: R2
Entry address(es): 
  IP address: 10.0.12.2
Platform: Cisco 2911,  Capabilities: Router
Interface: GigabitEthernet0/0,  Port ID (outgoing port): GigabitEthernet0/0
-------------------------
Device ID: R3
Entry address(es): 
  IP address: 10.0.13.2
Platform: Cisco 2911,  Capabilities: Router
Interface: GigabitEthernet0/1,  Port ID (outgoing port): GigabitEthernet0/0
""",
        "R2.txt": """R2# show running-config
hostname R2
!
interface GigabitEthernet0/0
 description Link to R1
 ip address 10.0.12.2 255.255.255.252
!
interface GigabitEthernet0/1
 description Branch 2 LAN
 ip address 192.168.2.1 255.255.255.0
!
ip route 0.0.0.0 0.0.0.0 10.0.12.1
!
R2# show cdp neighbors detail
-------------------------
Device ID: R1
Entry address(es): 
  IP address: 10.0.12.1
Platform: Cisco 2911,  Capabilities: Router
Interface: GigabitEthernet0/0,  Port ID (outgoing port): GigabitEthernet0/0
""",
        "R3.txt": """R3# show running-config
hostname R3
!
interface GigabitEthernet0/0
 description Link to R1
 ip address 10.0.13.2 255.255.255.252
!
interface GigabitEthernet0/1
 description Branch 3 LAN
 ip address 192.168.3.1 255.255.255.0
!
ip route 0.0.0.0 0.0.0.0 10.0.13.1
!
R3# show cdp neighbors detail
-------------------------
Device ID: R1
Entry address(es): 
  IP address: 10.0.13.1
Platform: Cisco 2911,  Capabilities: Router
Interface: GigabitEthernet0/0,  Port ID (outgoing port): GigabitEthernet0/1
""",
    },
```

This bundle was checked while planning: it yields two verified links, R1 G0/0–R2 G0/0 and R1 G0/1–R3 G0/0. Each LAN port also gets a link to an `UNKNOWN_PORT_…` placeholder device.

- [ ] **Step 2: Write the failing grader tests**

Create `tests/test_static_routes.py`:

```python
# tests/test_static_routes.py
"""
Static-route grading (src/topics/static_routes.py).

The reference is the static_chain bundle: R1 in the middle, R2 and R3 each
with a LAN, R1 routing to both LANs (one route by next hop, one by exit
interface) and R2/R3 pointing a default route back at R1.
"""
import pytest

from src.app import process_bundle_dict
from src.evaluator import make_eval_context
from src.models import EvaluationCriteria, EvaluationPolicies, RouteEntry
from src.topics.static_routes import evaluate, generate_rules, is_static
from tests.fixtures import network_bundle

STRICT = EvaluationPolicies()
DYNAMIC = EvaluationPolicies(allow_dynamic_subnetting=True)
CUSTOM_NAMES = EvaluationPolicies(allow_custom_hostnames=True)

R1_TO_R2_LAN = "ip route 192.168.2.0 255.255.255.0 10.0.12.2\n"
R1_TO_R3_LAN = "ip route 192.168.3.0 255.255.255.0 GigabitEthernet0/1\n"
R2_DEFAULT = "ip route 0.0.0.0 0.0.0.0 10.0.12.1\n"
R2_ROUTING_TABLE = """R2# show ip route
Gateway of last resort is 10.0.12.1 to network 0.0.0.0
C    10.0.12.0/30 is directly connected, GigabitEthernet0/0
C    192.168.2.0/24 is directly connected, GigabitEthernet0/1
S*   0.0.0.0/0 [1/0] via 10.0.12.1
"""


def _bundle(**edits):
    """static_chain with text edits per device: _bundle(R1=[(old, new), ...])."""
    bundle = network_bundle("static_chain")
    for device, changes in edits.items():
        name = f"{device}.txt"
        for old, new in changes:
            assert old in bundle[name], f"{old!r} not found in {name}"
            bundle[name] = bundle[name].replace(old, new, 1)
    return bundle


def _topology(**edits):
    return process_bundle_dict(_bundle(**edits))


def _grade(reference, student, policies=STRICT):
    """Grade only the static-route rules. Returns ({device: outcome}, rules, warnings)."""
    rules, warnings = generate_rules(reference, policies)
    ctx = make_eval_context(EvaluationCriteria(policies=policies, rules=rules), student)
    return {rule.target_device: evaluate(rule, ctx) for rule in rules}, rules, warnings


def test_one_rule_per_router_with_resolved_routes():
    rules, warnings = generate_rules(_topology(), STRICT)
    assert warnings == []
    by_device = {r.target_device: r for r in rules}
    assert set(by_device) == {"R1", "R2", "R3"}
    r1 = by_device["R1"]
    assert r1.category == "static_route"
    assert r1.points == 8.0
    assert r1.description == "Configure static routes on R1 (2 destinations)"
    routes = {r["network"]: r for r in r1.expected_value["routes"]}
    assert (routes["192.168.2.0"]["via_device"], routes["192.168.2.0"]["style"]) == ("R2", "next_hop")
    assert (routes["192.168.2.0"]["dest_device"], routes["192.168.2.0"]["dest_interface"]) == ("R2", "GigabitEthernet0/1")
    assert (routes["192.168.3.0"]["via_device"], routes["192.168.3.0"]["style"]) == ("R3", "exit_interface")
    default = by_device["R2"].expected_value["routes"][0]
    assert default["is_default"] is True
    assert default["dest_device"] is None
    assert default["via_device"] == "R1"


def test_identical_submission_passes_every_route():
    outcomes, _, _ = _grade(_topology(), _topology())
    assert all(o.passed and o.points_earned == 8.0 for o in outcomes.values())


def test_missing_route_earns_partial_credit():
    outcomes, _, _ = _grade(_topology(), _topology(R1=[(R1_TO_R2_LAN, "")]))
    r1 = outcomes["R1"]
    assert not r1.passed
    assert r1.points_earned == 4.0
    assert r1.actual == "1 of 2 static routes correct"
    assert "no static route to 192.168.2.0/24" in r1.feedback


def test_route_to_the_wrong_neighbor_fails():
    wrong = R1_TO_R2_LAN.replace("10.0.12.2", "10.0.13.2")
    outcomes, _, _ = _grade(_topology(), _topology(R1=[(R1_TO_R2_LAN, wrong)]))
    assert "route to 192.168.2.0/24 points at R3, it should go via R2" in outcomes["R1"].feedback


def test_next_hop_that_is_not_directly_connected_fails():
    far = R1_TO_R2_LAN.replace("10.0.12.2", "10.0.99.9")
    outcomes, _, _ = _grade(_topology(), _topology(R1=[(R1_TO_R2_LAN, far)]))
    assert "next hop 10.0.99.9 is not on a network directly connected to R1" in outcomes["R1"].feedback


def test_missing_default_route_fails():
    outcomes, _, _ = _grade(_topology(), _topology(R2=[(R2_DEFAULT, "")]))
    assert outcomes["R2"].points_earned == 0.0
    assert "no default route (0.0.0.0/0)" in outcomes["R2"].feedback


def test_exit_interface_form_is_accepted():
    by_interface = "ip route 192.168.2.0 255.255.255.0 GigabitEthernet0/0\n"
    outcomes, _, _ = _grade(_topology(), _topology(R1=[(R1_TO_R2_LAN, by_interface)]))
    assert outcomes["R1"].passed


def test_dynamic_subnetting_follows_the_students_own_lan():
    student = _topology(
        R2=[("ip address 192.168.2.1 255.255.255.0", "ip address 192.168.20.1 255.255.255.0")],
        R1=[(R1_TO_R2_LAN, "ip route 192.168.20.0 255.255.255.0 10.0.12.2\n")],
    )
    dynamic, _, _ = _grade(_topology(), student, DYNAMIC)
    strict, _, _ = _grade(_topology(), student, STRICT)
    assert dynamic["R1"].passed
    assert "no static route to 192.168.2.0/24" in strict["R1"].feedback


def test_dynamic_subnetting_reports_an_unaddressed_destination_lan():
    student = _topology(R2=[("ip address 192.168.2.1 255.255.255.0", "no ip address")])
    outcomes, _, _ = _grade(_topology(), student, DYNAMIC)
    assert "the destination LAN on R2 GigabitEthernet0/1 has no address" in outcomes["R1"].feedback


def test_unmappable_summary_checks_the_neighbor_only_under_dynamic_subnetting():
    summary = "ip route 172.16.0.0 255.240.0.0 10.0.12.2\n"
    reference = _topology(R1=[(R1_TO_R3_LAN, R1_TO_R3_LAN + summary)])
    rules, _ = generate_rules(reference, DYNAMIC)
    r1_routes = next(r for r in rules if r.target_device == "R1").expected_value["routes"]
    assert next(r for r in r1_routes if r["network"] == "172.16.0.0")["dest_device"] is None
    dynamic, _, _ = _grade(reference, _topology(), DYNAMIC)
    strict, _, _ = _grade(reference, _topology(), STRICT)
    assert dynamic["R1"].passed          # R1 still has a static route via R2
    assert "no static route to 172.16.0.0/12" in strict["R1"].feedback


@pytest.mark.parametrize("extra,reason", [
    ("ip route 10.9.0.0 255.255.0.0 10.0.12.99\n", "next hop 10.0.12.99 belongs to no device"),
    ("ip route 10.8.0.0 255.255.0.0 10.0.12.1\n", "next hop 10.0.12.1 is one of R1's own addresses"),
    ("ip route 10.7.0.0 255.255.0.0 GigabitEthernet0/2\n",
     "exit interface GigabitEthernet0/2 leads to an unidentified device"),
    ("ip route 10.6.0.0 255.255.0.0 GigabitEthernet0/3\n", "exit interface GigabitEthernet0/3 has no link"),
])
def test_broken_reference_routes_are_skipped_and_reported(extra, reason):
    reference = _topology(R1=[(R1_TO_R3_LAN, R1_TO_R3_LAN + extra)])
    outcomes, rules, warnings = _grade(reference, _topology())
    network = extra.split()[2]
    assert warnings == [f"R1: static route to {network}/16 was not graded because {reason}."]
    assert len(next(r for r in rules if r.target_device == "R1").expected_value["routes"]) == 2
    assert outcomes["R1"].passed     # the class can still reach 100%


def test_routing_table_entries_count_once_and_star_means_static():
    assert is_static(RouteEntry(network="0.0.0.0", cidr=0, protocol="S*"))
    assert is_static(RouteEntry(network="10.0.0.0", cidr=8, protocol="S"))
    assert not is_static(RouteEntry(network="10.0.0.0", cidr=8, protocol="O"))
    with_table = [("R2# show cdp neighbors detail", R2_ROUTING_TABLE + "R2# show cdp neighbors detail")]
    rules, _ = generate_rules(_topology(R2=with_table), STRICT)
    assert len(next(r for r in rules if r.target_device == "R2").expected_value["routes"]) == 1
    student = _topology(R2=[(R2_DEFAULT, "")] + with_table)
    outcomes, _, _ = _grade(_topology(), student)
    assert outcomes["R2"].passed


def test_missing_or_placeholder_student_device_scores_zero():
    gone = _topology()
    del gone.devices["R1"]
    placeholder = _topology()
    placeholder.devices["R1"].is_placeholder = True
    for student in (gone, placeholder):
        outcomes, _, _ = _grade(_topology(), student)
        assert outcomes["R1"].points_earned == 0.0
        assert outcomes["R1"].feedback == "Cannot evaluate static routes: device 'R1' missing."


def test_renamed_neighbor_is_matched_under_custom_hostnames():
    student = _topology(
        R2=[("hostname R2", "hostname BRANCH2")],
        R1=[("Device ID: R2", "Device ID: BRANCH2")],
    )
    outcomes, _, _ = _grade(_topology(), student, CUSTOM_NAMES)
    assert outcomes["R1"].passed and outcomes["R2"].passed
```

Add the guidance test to `tests/test_feedback.py`. First add `"static_route"` to `ALL_CATEGORIES`:

```python
ALL_CATEGORIES = [
    "device", "interface_ip", "interface_status", "cabling", "vlan_trunk",
    "routing", "relational_subnet", "link_agreement", "gateway", "security",
    "documentation", "static_route",
]
```

Then append:

```python
def test_static_route_failure_modes_are_distinguished():
    missing = _failed("static_route", feedback="Static routing on R1: no static route to 192.168.2.0/24.")
    wrong = _failed("static_route",
                    feedback="Static routing on R1: route to 192.168.2.0/24 points at R3, it should go via R2.")
    unreachable = _failed("static_route",
                          feedback="Static routing on R1: next hop 10.0.99.9 is not on a network directly connected to R1.")
    texts = {explain(missing), explain(wrong), explain(unreachable)}
    assert len(texts) == 3, "distinct static-route failures produced identical guidance"
    assert "wrong neighbour" in explain(wrong)
    assert "directly" in explain(unreachable)
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python -m pytest tests/test_static_routes.py tests/test_feedback.py -v`
Expected: `test_static_routes.py` fails to import (`cannot import name 'make_eval_context'` or `No module named 'src.topics.static_routes'`). `test_categories_match_the_rule_model` fails because `static_route` is not in the model yet.

- [ ] **Step 4: Add the category to the model**

In `src/models.py`, in `class EvaluationRule`, extend the `category` Literal so its last two entries read:

```python
        "security",
        "documentation",
        "static_route",
    ]
```

- [ ] **Step 5: Add the grader contract types**

Append to `src/topics/__init__.py`:

```python

# The two types below are the contract every grader module shares with the
# evaluator. They live here, not in evaluator.py, so a grader never imports
# the evaluator (which imports the registry, which imports the graders).
from dataclasses import dataclass
from typing import Callable

from src.models import DiscoveredLink, EvaluationPolicies, InterfaceData, ParsedDevice


@dataclass
class EvalContext:
    """What a grader may consult about the student's submission."""
    devices: dict[str, ParsedDevice]
    links: list[DiscoveredLink]
    policies: EvaluationPolicies
    device_mapping: dict[str, str]
    find_device: Callable[[str], ParsedDevice | None]
    find_interface: Callable[[ParsedDevice, str], InterfaceData | None]


@dataclass
class RuleOutcome:
    """A grader's verdict on one rule. The evaluator turns it into a RuleResult."""
    points_earned: float
    passed: bool
    actual: str
    feedback: str
```

- [ ] **Step 6: Add `make_eval_context` to the evaluator**

In `src/evaluator.py`, add to the imports:

```python
from src.topics import EvalContext
```

Add this function directly above `def evaluate_student_submission(`:

```python
def make_eval_context(criteria: EvaluationCriteria, student_topology: TopologyResult) -> EvalContext:
    """Everything a src/topics grader may consult about one submission."""
    devices = student_topology.devices
    policies = criteria.policies
    mapping = _build_device_mapping(criteria, student_topology)
    return EvalContext(
        devices=devices,
        links=student_topology.links,
        policies=policies,
        device_mapping=mapping,
        find_device=lambda name: _find_student_device(devices, name, mapping),
        find_interface=lambda dev, name: _find_student_interface(
            dev.interfaces, name, policies.strict_port_matching),
    )
```

In `evaluate_student_submission`, replace

```python
    device_mapping = _build_device_mapping(criteria, student_topology)
```

with

```python
    ctx = make_eval_context(criteria, student_topology)
    device_mapping = ctx.device_mapping
```

- [ ] **Step 7: Write the grader**

Create `src/topics/static_routes.py`:

```python
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
    if intf is None or not intf.ip_address or intf.cidr is None:
        return None
    try:
        return ipaddress.ip_interface(f"{intf.ip_address}/{intf.cidr}").network
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
        owner = _ip_owner(topology.devices, route.next_hop)
        if owner is None:
            return f"next hop {route.next_hop} belongs to no device"
        if owner[0] == hostname:
            return f"next hop {route.next_hop} is one of {hostname}'s own addresses"
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
```

- [ ] **Step 8: Add the study topic and guidance**

In `src/feedback.py`, add to `_TOPICS` after the `"documentation"` entry:

```python
    "static_route": (
        "Static routing and next-hop selection",
        "A static route only works if it names the right destination and hands traffic to a neighbour that can actually forward it.",
    ),
```

Add this function after `_explain_documentation`:

```python
def _explain_static_route(result: RuleResult) -> str:
    fb = _lower(result.feedback)
    if "should go via" in fb:
        return (
            f"A static route on {result.target_device} sends traffic to the wrong neighbour. "
            "The next hop (or exit interface) decides which router receives the packets, and a "
            "router with no path onward drops them or sends them back. Compare each route's next "
            "hop with the neighbour the lab names, using 'show ip route static'. The next hop is the "
            "neighbour's address on the link you share, not an address on a far-away network."
        )
    if "not on a network directly connected" in fb:
        return (
            f"A static route on {result.target_device} names a next hop it cannot reach directly. "
            "A next-hop address must sit in a subnet configured on one of this router's own "
            "interfaces, otherwise the route never becomes usable. Check the interface subnets with "
            "'show ip interface brief' and use the neighbour's address on the link between you."
        )
    return (
        f"One or more required static routes are missing on {result.target_device}. "
        "A router only knows its directly connected networks until you add a route for each remote "
        "one, so traffic to those networks is dropped. Add one 'ip route <network> <mask> <next hop>' "
        "for each destination the lab lists, then confirm them with 'show ip route static'."
    )
```

Add to `_HANDLERS`:

```python
    "static_route": _explain_static_route,
```

- [ ] **Step 9: Run the tests**

Run: `python -m pytest tests/test_static_routes.py tests/test_feedback.py -v`
Expected: all PASS.

- [ ] **Step 10: Run the full suite**

Run: `python -m pytest -q`
Expected: no failures.

- [ ] **Step 11: Commit**

```bash
git add src/topics/__init__.py src/topics/static_routes.py src/models.py src/evaluator.py src/feedback.py tests/fixtures.py tests/test_static_routes.py tests/test_feedback.py
git commit -m "feat(grading): add static-route grader (destination + correct neighbor)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 3: Wire static routes into generation and grading

**Files:**
- Modify: `src/topics/registry.py`, `src/criteria_generator.py`, `src/evaluator.py`
- Test: `tests/test_static_routes.py` (append)

**Interfaces:**
- Consumes: `static_routes.generate_rules`, `static_routes.evaluate`, `make_eval_context`, `topic_for_category`.
- Produces:
  - `TOPICS_BY_KEY["static_routing"]`, now gradeable and owning `("static_route",)`
  - `criteria.reference_summary["reference_warnings"]: list[str]`
  - The evaluator dispatches any rule whose topic has an `evaluate` hook

- [ ] **Step 1: Write the failing integration tests**

Append to `tests/test_static_routes.py`:

```python
from src.criteria_generator import generate_criteria_from_topology
from src.evaluator import evaluate_student_submission
from src.topics.registry import TOPICS_BY_KEY, topic_for_category


def test_static_routing_topic_is_gradeable():
    topic = TOPICS_BY_KEY["static_routing"]
    assert topic.gradeable and topic.categories == ("static_route",)
    assert topic_for_category("static_route") is topic


def test_generator_adds_static_rules_and_reference_warnings():
    reference = _topology(R1=[(R1_TO_R3_LAN, R1_TO_R3_LAN + "ip route 10.9.0.0 255.255.0.0 10.0.12.99\n")])
    criteria = generate_criteria_from_topology(reference, lab_title="Static Lab")
    assert {r.target_device for r in criteria.rules if r.category == "static_route"} == {"R1", "R2", "R3"}
    assert criteria.reference_summary["reference_warnings"] == [
        "R1: static route to 10.9.0.0/16 was not graded because next hop 10.0.12.99 belongs to no device."
    ]
    assert round(sum(r.points for r in criteria.rules) * 10) == 1000


def test_full_pipeline_scores_a_correct_submission_at_100():
    criteria = generate_criteria_from_topology(_topology())
    assert evaluate_student_submission(criteria, _topology()).percentage == 100.0


def test_full_pipeline_explains_a_wrong_neighbor():
    criteria = generate_criteria_from_topology(_topology())
    wrong = R1_TO_R2_LAN.replace("10.0.12.2", "10.0.13.2")
    report = evaluate_student_submission(criteria, _topology(R1=[(R1_TO_R2_LAN, wrong)]))
    failed = [r for r in report.results if not r.passed]
    assert [(r.category, r.target_device) for r in failed] == [("static_route", "R1")]
    assert "it should go via R2" in failed[0].feedback
    assert "wrong neighbour" in failed[0].guidance
    assert "Static routing and next-hop selection" in [t.topic for t in report.study_topics]
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest tests/test_static_routes.py -v -k "gradeable or generator_adds or full_pipeline"`
Expected: FAIL. `topic.gradeable` is False, there are no `static_route` rules, and `reference_warnings` raises KeyError.

- [ ] **Step 3: Make the topic gradeable**

In `src/topics/registry.py`, add below `from src.models import ParsedDevice, TopologyResult`:

```python
from src.topics import static_routes
```

Replace the `static_routing` entry with:

```python
    Topic("static_routing", "Static Routing", ("static_route",), gradeable=True,
          detect=_config_matches(r"^ip\s+route\s+\d"),
          generate=static_routes.generate_rules, evaluate=static_routes.evaluate),
```

- [ ] **Step 4: Run topic graders from the generator**

In `src/criteria_generator.py`, add to the imports:

```python
from src.topics.registry import TOPICS
```

Directly above the comment `# Point Normalization so total equals target_total_points (e.g. 100.0 pts)`, insert:

```python
    # 3. Topic graders (src/topics/): topics added after the registry existed
    # generate their own rules. Their warnings name reference configuration
    # that could not be graded, for the instructor to see.
    reference_warnings: list[str] = []
    for topic in TOPICS:
        if topic.generate is not None:
            topic_rules, topic_warnings = topic.generate(topology, policies)
            for rule in topic_rules:
                add_rule(rule)
            reference_warnings.extend(topic_warnings)
```

In the `ref_summary = {...}` dict, add the entry:

```python
        "reference_warnings": reference_warnings,
```

- [ ] **Step 5: Dispatch to topic graders in the evaluator**

In `src/evaluator.py`, add to the imports:

```python
from src.topics.registry import topic_for_category
```

In `evaluate_student_submission`, replace

```python
        # 1. Device Presence Rule
        if rule.category == "device":
```

with

```python
        # Topics graded by a module in src/topics/ (static routes, ...).
        grader = topic_for_category(rule.category).evaluate
        if grader is not None:
            outcome = grader(rule, ctx)
            pts_earned = outcome.points_earned
            passed = outcome.passed
            actual = outcome.actual
            feedback = outcome.feedback

        # 1. Device Presence Rule
        elif rule.category == "device":
```

- [ ] **Step 6: Run the tests**

Run: `python -m pytest tests/test_static_routes.py tests/test_topic_registry.py -v`
Expected: all PASS.

- [ ] **Step 7: Run the full suite and the validation harness**

Run: `python -m pytest -q`, then `python -m validation`
Expected: no failures, and 100% on every validation metric. No existing fixture or reference contains static routes, so nothing else changes.

- [ ] **Step 8: Commit**

```bash
git add src/topics/registry.py src/criteria_generator.py src/evaluator.py tests/test_static_routes.py
git commit -m "feat(grading): generate and grade static-route rules through the topic registry" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 4: Weighting engine

**Files:**
- Create: `src/topics/weights.py`, `tests/test_topic_weights.py`
- Modify: `src/models.py` (`graded`, `topic_weights`), `src/criteria_generator.py` (normalizer moved out, weights in), `src/evaluator.py` (skip ungraded)

**Interfaces:**
- Consumes: `TOPICS`, `TOPICS_BY_KEY`, `topic_for_category`.
- Produces:
  - `EvaluationRule.graded: bool = True`, `EvaluationCriteria.topic_weights: dict[str, float] = {}`
  - `largest_remainder(weights: Sequence[float], units: int) -> list[int]`
  - `normalize_rule_points(rules, target_total) -> None`, moved verbatim from the generator's `_normalize_rule_points`
  - `rules_by_topic(rules) -> dict[str, list[EvaluationRule]]`, in registry order, empty topics omitted
  - `default_weights(rules) -> dict[str, float]`
  - `validate_weights(raw: object, defaults: dict[str, float]) -> dict[str, float]`
  - `same_weights(a, b) -> bool`
  - `apply_weights(rules, base_points: dict[str, float], weights, total_points) -> None`
  - `minimum_percent(checkpoints: int, total_points: float) -> float`
  - `TopicWeightError(ValueError)`
  - `generate_criteria_from_topology(..., topic_weights: dict[str, float] | None = None)` always fills `criteria.topic_weights` and `criteria.reference_summary["default_topic_weights"]`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_topic_weights.py`:

```python
# tests/test_topic_weights.py
"""
Topic weights (src/topics/weights.py): defaults reproduce today's rubric,
a requested split is applied exactly, a 0% topic is ungraded but kept, and
every invalid request is refused with a reason that names the topic.
"""
import pytest

from src.app import process_bundle_dict
from src.criteria_generator import generate_criteria_from_topology
from src.evaluator import evaluate_student_submission
from src.models import EvaluationCriteria, EvaluationPolicies
from src.topics.weights import TopicWeightError, largest_remainder, minimum_percent, rules_by_topic
from tests.fixtures import network_bundle


def _static_chain():
    return process_bundle_dict(network_bundle("static_chain"))


def _defaults(total=100.0, policies=None):
    return generate_criteria_from_topology(
        _static_chain(), target_total_points=total, policies=policies).topic_weights


def _focus(defaults, key, share=50.0):
    """The Teacher Studio's Focus button: `key` gets `share`, the rest scale down."""
    others = [k for k in defaults if k != key]
    units = largest_remainder([defaults[k] for k in others], round((100 - share) * 10))
    weights = {k: u / 10 for k, u in zip(others, units)}
    weights[key] = share
    return weights


def _zero(defaults, key, onto="static_routing"):
    """Move `key`'s whole share onto `onto`, leaving `key` at 0%."""
    weights = dict(defaults)
    weights[onto] = round(weights[onto] + weights[key], 1)
    weights[key] = 0.0
    return weights


def _with(defaults, **overrides):
    """Defaults with overrides; ip_addressing absorbs the difference so the sum stays 100."""
    weights = dict(defaults)
    weights.update(overrides)
    weights["ip_addressing"] = round(weights["ip_addressing"] + 100 - sum(weights.values()), 1)
    return weights


@pytest.mark.parametrize("weights,units", [([1, 1, 1], 1000), ([8, 8, 8], 500), ([0.3, 0.3, 0.4], 7), ([5, 0, 5], 3)])
def test_largest_remainder_sums_exactly(weights, units):
    alloc = largest_remainder(weights, units)
    assert sum(alloc) == units
    assert all(a >= 0 for a in alloc)


def test_largest_remainder_breaks_ties_by_order_and_skips_zero_weights():
    assert largest_remainder([1, 1, 1], 1000) == [334, 333, 333]
    assert largest_remainder([5, 0, 5], 3) == [2, 0, 1]
    assert largest_remainder([0, 0], 10) == [0, 0]


def test_minimum_percent():
    assert minimum_percent(12, 100.0) == 1.2
    assert minimum_percent(7, 10.0) == 7.0
    assert minimum_percent(3, 37.0) == 0.9   # 0.3 pt of 37 is 0.81%, rounded up


@pytest.mark.parametrize("bundle", ["ospf_clean", "static_chain", "vlan_trunk_mismatch"])
def test_sending_the_defaults_reproduces_the_unweighted_rubric(bundle):
    unweighted = generate_criteria_from_topology(process_bundle_dict(network_bundle(bundle)))
    again = generate_criteria_from_topology(
        process_bundle_dict(network_bundle(bundle)), topic_weights=dict(unweighted.topic_weights))
    assert [(r.rule_id, r.points, r.graded) for r in again.rules] == \
           [(r.rule_id, r.points, r.graded) for r in unweighted.rules]
    assert again.topic_weights == unweighted.topic_weights


def test_default_percent_equals_topic_points_at_100():
    criteria = generate_criteria_from_topology(_static_chain())
    assert criteria.reference_summary["default_topic_weights"] == criteria.topic_weights
    for key, rules in rules_by_topic(criteria.rules).items():
        assert criteria.topic_weights[key] == pytest.approx(round(sum(r.points for r in rules), 1))


@pytest.mark.parametrize("total", [100.0, 50.0, 37.0, 1000.0])
def test_default_weights_sum_to_exactly_100(total):
    assert round(sum(_defaults(total).values()) * 10) == 1000


@pytest.mark.parametrize("total", [100.0, 50.0, 37.0, 1000.0])
def test_focused_rubric_totals_exactly(total):
    weights = _focus(_defaults(total), "static_routing")
    criteria = generate_criteria_from_topology(_static_chain(), target_total_points=total, topic_weights=weights)
    assert round(sum(r.points for r in criteria.rules) * 10) == round(total * 10)
    static_points = sum(r.points for r in criteria.rules if r.category == "static_route")
    assert static_points == pytest.approx(total * 0.5, abs=0.05)
    assert criteria.topic_weights == weights


def test_points_inside_a_topic_keep_base_proportions():
    defaults = generate_criteria_from_topology(process_bundle_dict(network_bundle("vlan_trunk_mismatch"))).topic_weights
    criteria = generate_criteria_from_topology(
        process_bundle_dict(network_bundle("vlan_trunk_mismatch")),
        topic_weights=_focus(defaults, "vlans_trunking"))
    vlan = [r for r in criteria.rules if r.category == "vlan_trunk"]
    trunks = [r.points for r in vlan if r.expected_value["switchport_mode"] == "trunk"]
    access = [r.points for r in vlan if r.expected_value["switchport_mode"] == "access"]
    assert trunks and access
    assert min(trunks) > max(access)   # base 8 vs 6


def test_zero_weight_topic_is_ungraded_but_kept():
    criteria = generate_criteria_from_topology(_static_chain(), topic_weights=_zero(_defaults(), "cabling"))
    cabling = [r for r in criteria.rules if r.category == "cabling"]
    assert cabling and all(not r.graded and r.points == 0.0 for r in cabling)
    assert round(sum(r.points for r in criteria.rules) * 10) == 1000


def test_evaluator_skips_ungraded_rules():
    criteria = generate_criteria_from_topology(_static_chain(), topic_weights=_zero(_defaults(), "cabling"))
    report = evaluate_student_submission(criteria, _static_chain())
    assert all(r.category != "cabling" for r in report.results)
    assert report.max_score == 100.0
    assert report.passed_count + report.failed_count == sum(r.graded for r in criteria.rules)


def test_device_mapping_survives_device_presence_at_zero():
    policies = EvaluationPolicies(allow_custom_hostnames=True)
    weights = _zero(_defaults(policies=policies), "devices")
    criteria = generate_criteria_from_topology(_static_chain(), policies=policies, topic_weights=weights)
    bundle = network_bundle("static_chain")
    bundle["R2.txt"] = bundle["R2.txt"].replace("hostname R2", "hostname BRANCH2")
    bundle["R1.txt"] = bundle["R1.txt"].replace("Device ID: R2", "Device ID: BRANCH2")
    assert evaluate_student_submission(criteria, process_bundle_dict(bundle)).percentage == 100.0


INVALID = [
    (lambda d: [], "JSON object of topic -> percent"),
    (lambda d: {**d, "static_routing": "50"}, "JSON object of topic -> percent"),
    (lambda d: {**d, "static_routing": True}, "JSON object of topic -> percent"),
    (lambda d: {**d, "routing_magic": 0}, 'Unknown topic "routing_magic"'),
    (lambda d: {**d, "stp": 0}, '"stp" cannot be weighted: it is not graded yet'),
    (lambda d: {**d, "security_baseline": 0}, '"Security Baseline" is not part of this rubric'),
    (lambda d: {k: v for k, v in d.items() if k != "cabling"}, 'Missing a weight for "Cabling"'),
    (lambda d: _with(d, cabling=-1.0), '"Cabling" must be between 0 and 100'),
    (lambda d: _with(d, cabling=10.25), '"Cabling" allows one decimal place'),
    (lambda d: {**d, "cabling": round(d["cabling"] - 2.5, 1)}, "Weights add up to 97.5%, they must add up to 100%"),
    (lambda d: {k: 0 for k in d}, "At least one topic must carry points"),
]


@pytest.mark.parametrize("build,message", INVALID)
def test_invalid_weights_are_rejected_with_a_named_reason(build, message):
    with pytest.raises(TopicWeightError) as err:
        generate_criteria_from_topology(_static_chain(), topic_weights=build(_defaults()))
    assert message in str(err.value)


def test_topic_share_too_small_for_its_checkpoints():
    weights = dict(_defaults(10.0))
    spare = round(weights["ip_addressing"] - 0.5, 1)
    weights["ip_addressing"] = 0.5
    weights["static_routing"] = round(weights["static_routing"] + spare, 1)
    with pytest.raises(TopicWeightError, match=r'"IP Addressing" needs at least 7\.0% for its 7 checkpoints'):
        generate_criteria_from_topology(_static_chain(), target_total_points=10.0, topic_weights=weights)


def test_whole_numbers_and_float_sums_are_accepted():
    weights = {k: 0 for k in _defaults()}
    weights.update(static_routing=33.3, ip_addressing=33.3, interface_status=33.4)
    criteria = generate_criteria_from_topology(_static_chain(), topic_weights=weights)
    assert criteria.topic_weights["static_routing"] == 33.3
    assert all(isinstance(v, float) for v in criteria.topic_weights.values())


def test_rubric_from_before_topic_weights_still_grades_identically():
    data = generate_criteria_from_topology(_static_chain()).model_dump()
    data.pop("topic_weights")
    for rule in data["rules"]:
        rule.pop("graded")
    old = EvaluationCriteria(**data)
    assert old.topic_weights == {} and all(r.graded for r in old.rules)
    assert evaluate_student_submission(old, _static_chain()).percentage == 100.0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_topic_weights.py -v`
Expected: collection ERROR, `No module named 'src.topics.weights'`.

- [ ] **Step 3: Add the model fields**

In `src/models.py`, at the end of `class EvaluationRule`, after `expected_value`, add:

```python
    # False when the instructor weighted this rule's topic 0%: the rule still
    # prints in instructions.txt (and still tells the evaluator which devices
    # the reference has), but earns and costs nothing.
    graded: bool = True
```

At the end of `class EvaluationCriteria`, after `reference_summary`, add:

```python
    # Topic key -> percent of total_points (src/topics/weights.py). Empty for
    # rubrics generated before topic weights existed.
    topic_weights: dict[str, float] = Field(default_factory=dict)
```

- [ ] **Step 4: Create the weights module**

Create `src/topics/weights.py`. Copy the body of `normalize_rule_points` **verbatim** from `_normalize_rule_points` in `src/criteria_generator.py`. Only the function name and the name of the tenths constant change.

```python
# src/topics/weights.py
"""
How a lab's points are split between topics.

All arithmetic is in integer tenths (of a point, or of a percent), split with
largest-remainder apportionment, so every total comes out exact.

  default_weights   the split today's rubric already has, as percentages
  validate_weights  checks an instructor's requested split (TopicWeightError)
  apply_weights     rescales rule points to a requested split; a 0% topic's
                    rules become ungraded (graded=False, points=0)
"""
import math
from typing import Sequence

from src.models import EvaluationRule
from src.topics.registry import TOPICS, TOPICS_BY_KEY, topic_for_category

TENTHS = 10
PERCENT_UNITS = 100 * TENTHS        # 100.0% in tenths of a percent
SUM_TOLERANCE = 0.05                # percent
DEFAULTS_TOLERANCE = 0.001          # percent
_FORMAT_ERROR = "topic_weights must be a JSON object of topic -> percent"


class TopicWeightError(ValueError):
    """An instructor's topic weights cannot be applied. The message names the topic."""


def largest_remainder(weights: Sequence[float], units: int) -> list[int]:
    """
    Split `units` whole units in proportion to non-negative `weights`,
    exactly. Floors every share, then hands the leftover units to the largest
    fractional remainders (earliest index first on ties). All-zero weights
    get nothing.
    """
    total = float(sum(weights))
    if units <= 0 or total <= 0:
        return [0] * len(weights)
    exact = [units * w / total for w in weights]
    alloc = [math.floor(x + 1e-9) for x in exact]
    leftover = max(0, units - sum(alloc))
    order = sorted(range(len(weights)), key=lambda i: (-(exact[i] - alloc[i]), i))
    for i in order[:leftover]:
        alloc[i] += 1
    return alloc


def normalize_rule_points(rules: list[EvaluationRule], target_total: float) -> None:
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

    total_tenths = int(round(target_total * TENTHS))
    count = len(rules)

    # Degenerate case: fewer tenths than rules, so not every rule can be worth
    # something. Spread what exists as evenly as possible rather than going
    # negative, and let the caller's total stand.
    if total_tenths < count:
        base, remainder = divmod(total_tenths, count)
        for i, rule in enumerate(rules):
            rule.points = round((base + (1 if i < remainder else 0)) / TENTHS, 1)
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
        rule.points = round(tenths / TENTHS, 1)


def rules_by_topic(rules: list[EvaluationRule]) -> dict[str, list[EvaluationRule]]:
    """Topic key -> its rules, in registry order, topics with no rules left out."""
    grouped: dict[str, list[EvaluationRule]] = {t.key: [] for t in TOPICS}
    for rule in rules:
        grouped[topic_for_category(rule.category).key].append(rule)
    return {key: topic_rules for key, topic_rules in grouped.items() if topic_rules}


def default_weights(rules: list[EvaluationRule]) -> dict[str, float]:
    """
    Each topic's share of the rules' current points, as one-decimal percents
    summing to exactly 100.0. Called on the legacy-normalized rubric, so at a
    100-point total a topic's default percent equals its points.
    """
    groups = rules_by_topic(rules)
    keys = list(groups)
    units = largest_remainder([sum(r.points for r in groups[k]) for k in keys], PERCENT_UNITS)
    return {k: u / TENTHS for k, u in zip(keys, units)}


def minimum_percent(checkpoints: int, total_points: float) -> float:
    """Smallest one-decimal percent that gives every checkpoint at least 0.1 pt."""
    return math.ceil(checkpoints * 100 / total_points - 1e-9) / TENTHS


def validate_weights(raw: object, defaults: dict[str, float]) -> dict[str, float]:
    """
    Check an instructor's requested split against the topics this rubric has.
    Returns {topic key: percent} rounded to one decimal. Raises TopicWeightError.
    """
    if not isinstance(raw, dict):
        raise TopicWeightError(_FORMAT_ERROR)
    weights: dict[str, float] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TopicWeightError(_FORMAT_ERROR)
        topic = TOPICS_BY_KEY.get(key)
        if topic is None:
            raise TopicWeightError(f'Unknown topic "{key}"')
        if not topic.gradeable:
            raise TopicWeightError(f'"{key}" cannot be weighted: it is not graded yet')
        if key not in defaults:
            raise TopicWeightError(f'"{topic.label}" is not part of this rubric')
        if not 0 <= value <= 100:
            raise TopicWeightError(f'"{topic.label}" must be between 0 and 100')
        if abs(round(value, 1) - value) > 1e-9:
            raise TopicWeightError(f'"{topic.label}" allows one decimal place')
        weights[key] = round(float(value), 1)
    for key in defaults:
        if key not in weights:
            raise TopicWeightError(f'Missing a weight for "{TOPICS_BY_KEY[key].label}"')
    if all(v == 0 for v in weights.values()):
        raise TopicWeightError("At least one topic must carry points")
    total = sum(weights.values())
    if abs(total - 100) > SUM_TOLERANCE:
        raise TopicWeightError(f"Weights add up to {total:.1f}%, they must add up to 100%")
    return weights


def same_weights(a: dict[str, float], b: dict[str, float]) -> bool:
    return a.keys() == b.keys() and all(abs(a[k] - b[k]) < DEFAULTS_TOLERANCE for k in a)


def apply_weights(rules: list[EvaluationRule], base_points: dict[str, float],
                  weights: dict[str, float], total_points: float) -> None:
    """
    Rescale rule points in place to `weights`. Topics split the total by
    percent; inside a topic the rules keep their base-point proportions.
    A 0% topic's rules become graded=False with 0 points.
    """
    groups = rules_by_topic(rules)
    keys = list(groups)
    shares = dict(zip(keys, largest_remainder([weights[k] for k in keys], round(total_points * TENTHS))))

    # Check every topic before changing any rule.
    for key, topic_rules in groups.items():
        if weights[key] > 0 and shares[key] < len(topic_rules):
            raise TopicWeightError(
                f'"{TOPICS_BY_KEY[key].label}" needs at least '
                f"{minimum_percent(len(topic_rules), total_points):.1f}% "
                f"for its {len(topic_rules)} checkpoints"
            )

    for key, topic_rules in groups.items():
        if weights[key] == 0:
            for rule in topic_rules:
                rule.graded = False
                rule.points = 0.0
            continue
        for rule in topic_rules:
            rule.points = base_points[rule.rule_id]
        normalize_rule_points(topic_rules, shares[key] / TENTHS)
```

- [ ] **Step 5: Use it in the generator**

In `src/criteria_generator.py`:

1. Delete the `_TENTHS = 10` constant, its comment, and the whole `_normalize_rule_points` function.
2. Add to the imports:

```python
from src.topics.weights import apply_weights, default_weights, normalize_rule_points, same_weights, validate_weights
```

3. Add a parameter to `generate_criteria_from_topology`. The signature's last lines become:

```python
    target_total_points: float = 100.0,
    policies: EvaluationPolicies | None = None,
    topic_weights: dict[str, float] | None = None,
) -> EvaluationCriteria:
```

Add to its docstring: `topic_weights: topic key -> percent; None (or the defaults) keeps today's split. Raises TopicWeightError for an invalid split.`

4. Replace

```python
    # Point Normalization so total equals target_total_points (e.g. 100.0 pts)
    if raw_rules:
        _normalize_rule_points(raw_rules, target_total_points)
```

with

```python
    # Point normalization. Base points first split the total across all rules
    # exactly as before topic weights existed (the "legacy" rubric). Its
    # topic split is the default the weights panel shows, so an instructor who
    # accepts the defaults gets this rubric, point for point.
    base_points = {r.rule_id: r.points for r in raw_rules}
    if raw_rules:
        normalize_rule_points(raw_rules, target_total_points)
    defaults = default_weights(raw_rules)
    applied = defaults
    if topic_weights is not None:
        requested = validate_weights(topic_weights, defaults)
        if not same_weights(requested, defaults):
            apply_weights(raw_rules, base_points, requested, target_total_points)
            applied = requested
```

5. In `ref_summary`, add `"default_topic_weights": defaults,`.
6. In the returned `EvaluationCriteria(...)`, add `topic_weights=applied,`.

- [ ] **Step 6: Skip ungraded rules in the evaluator**

In `src/evaluator.py`, replace

```python
    for rule in criteria.rules:
        pts_possible = float(rule.points)
```

with

```python
    for rule in criteria.rules:
        # A rule in a topic weighted 0% is printed for reference only. It
        # still informed the device mapping above, but it is not graded.
        if not rule.graded:
            continue
        pts_possible = float(rule.points)
```

- [ ] **Step 7: Run the tests**

Run: `python -m pytest tests/test_topic_weights.py -v`
Expected: all PASS. If `test_device_mapping_survives_device_presence_at_zero` fails, print the failed results before changing anything. The fault is either in `apply_weights` or in an evaluator branch that relies on device rules being graded. Do not weaken the test.

- [ ] **Step 8: Run the full suite and the validation harness**

Run: `python -m pytest -q`, then `python -m validation`
Expected: no failures, 100% on every metric. Rubrics generated without weights are unchanged, so every existing number holds.

- [ ] **Step 9: Commit**

```bash
git add src/topics/weights.py src/models.py src/criteria_generator.py src/evaluator.py tests/test_topic_weights.py
git commit -m "feat(grading): split rubric points by topic weight, defaulting to today's split" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 5: instructions.txt rendering

**Files:**
- Modify: `src/criteria_generator.py` (`format_criteria_to_instructions_txt`)
- Test: `tests/test_criteria_generator.py` (append)

**Interfaces:**
- Consumes: `rules_by_topic`, `TOPICS_BY_KEY`, `destination_label`, `EvaluationRule.graded`, `criteria.topic_weights`.
- Produces: the sheet layout described in spec §4.13. `parse_instructions_txt` is unchanged.

- [ ] **Step 1: Write the failing tests**

At the top of `tests/test_criteria_generator.py`, add the imports `import re` and `from src.models import EvaluationPolicies`. Then append:

```python
def _static_chain():
    return process_bundle_dict(network_bundle("static_chain"))


def _cabling_at_zero():
    defaults = generate_criteria_from_topology(_static_chain()).topic_weights
    weights = dict(defaults)
    weights["static_routing"] = round(weights["static_routing"] + weights["cabling"], 1)
    weights["cabling"] = 0.0
    return generate_criteria_from_topology(_static_chain(), topic_weights=weights)


def test_instructions_show_grading_weights():
    criteria = generate_criteria_from_topology(_static_chain(), lab_title="Static Lab")
    txt = format_criteria_to_instructions_txt(criteria)
    assert "3. GRADING WEIGHTS" in txt
    pct = criteria.topic_weights["static_routing"]
    assert re.search(rf"Static Routing\s+\|\s+{pct:.1f} %", txt)


def test_section_numbers_are_consecutive():
    txt = format_criteria_to_instructions_txt(_cabling_at_zero())
    numbers = [int(n) for n in re.findall(r"^(\d+)\. [A-Z]", txt, re.MULTILINE)]
    assert numbers == list(range(1, len(numbers) + 1))
    assert len(numbers) >= 6


def test_static_routing_section_in_both_addressing_modes():
    txt = format_criteria_to_instructions_txt(generate_criteria_from_topology(_static_chain()))
    assert "STATIC ROUTING REQUIREMENTS" in txt
    assert re.search(r"R1\s+\|\s+192\.168\.2\.0/24\s+\|\s+R2", txt)
    assert re.search(r"R2\s+\|\s+default route \(0\.0\.0\.0/0\)\s+\|\s+R1", txt)
    dynamic = format_criteria_to_instructions_txt(generate_criteria_from_topology(
        _static_chain(), policies=EvaluationPolicies(allow_dynamic_subnetting=True)))
    assert re.search(r"R1\s+\|\s+the LAN on R2 GigabitEthernet0/1 \(/24\)\s+\|\s+R2", dynamic)


def test_unmappable_summary_is_explained_under_dynamic_subnetting():
    bundle = network_bundle("static_chain")
    anchor = "ip route 192.168.3.0 255.255.255.0 GigabitEthernet0/1\n"
    bundle["R1.txt"] = bundle["R1.txt"].replace(anchor, anchor + "ip route 172.16.0.0 255.240.0.0 10.0.12.2\n")
    txt = format_criteria_to_instructions_txt(generate_criteria_from_topology(
        process_bundle_dict(bundle), policies=EvaluationPolicies(allow_dynamic_subnetting=True)))
    assert "172.16.0.0/12 summary, any static route via R2 accepted" in txt


def test_zero_weight_sections_are_marked_reference_only():
    criteria = _cabling_at_zero()
    txt = format_criteria_to_instructions_txt(criteria)
    assert "PHYSICAL CABLING & PORT CONNECTIONS (REFERENCE ONLY, NOT GRADED)" in txt
    assert re.search(r"Cabling\s+\|\s+0\.0 % \| reference only, not graded", txt)
    rubric = txt.split("RUBRIC & POINT BREAKDOWN")[1].split("DO NOT MODIFY")[0]
    graded_part, reference_part = rubric.split("REFERENCE ONLY (NOT GRADED)")
    assert "Cable connection between R1" not in graded_part
    assert "Cable connection between R1" in reference_part
    assert f"Total Checkpoints: {sum(r.graded for r in criteria.rules)} items" in txt


def test_rubric_is_grouped_by_topic_with_subtotals():
    criteria = generate_criteria_from_topology(_static_chain())
    txt = format_criteria_to_instructions_txt(criteria)
    static_points = sum(r.points for r in criteria.rules if r.category == "static_route")
    assert f"Static Routing ({static_points:.1f} pts)" in txt


def test_weights_and_graded_flags_survive_the_round_trip():
    criteria = _cabling_at_zero()
    parsed = parse_instructions_txt(format_criteria_to_instructions_txt(criteria))
    assert parsed.topic_weights == criteria.topic_weights
    assert [r.graded for r in parsed.rules] == [r.graded for r in criteria.rules]


def test_rubric_without_topic_weights_has_no_weights_section():
    criteria = generate_criteria_from_topology(_static_chain())
    criteria.topic_weights = {}
    assert "GRADING WEIGHTS" not in format_criteria_to_instructions_txt(criteria)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest tests/test_criteria_generator.py -v`
Expected: the new tests FAIL. There is no `GRADING WEIGHTS` and no `STATIC ROUTING REQUIREMENTS`, and the section numbers have gaps.

- [ ] **Step 3: Replace the formatter**

In `src/criteria_generator.py`, add to the imports:

```python
from src.topics.registry import TOPICS_BY_KEY
from src.topics.static_routes import destination_label
from src.topics.weights import rules_by_topic
```

Merge `rules_by_topic` into the `from src.topics.weights import ...` line added in Task 4, and `TOPICS_BY_KEY` into the `from src.topics.registry import TOPICS` line added in Task 3. Then replace the whole `format_criteria_to_instructions_txt` function with:

```python
_REFERENCE_ONLY = " (REFERENCE ONLY, NOT GRADED)"


def format_criteria_to_instructions_txt(criteria: EvaluationCriteria) -> str:
    """
    Formats the evaluation criteria into a clean, human-readable student lab instructions document
    with policy indicators and an embedded machine-verifiable criteria schema at the end.

    Sections are numbered in output order. A section whose topic the
    instructor weighted 0% still prints, marked reference only, because
    students still need it to build the lab.
    """
    lines: list[str] = []
    graded_rules = [r for r in criteria.rules if r.graded]
    groups = rules_by_topic(criteria.rules)
    section_number = 0

    def heading(title: str, section_rules: list[EvaluationRule] | None = None, width: int = 80) -> None:
        nonlocal section_number
        section_number += 1
        reference_only = bool(section_rules) and not any(r.graded for r in section_rules)
        lines.append(f"{section_number}. {title}{_REFERENCE_ONLY if reference_only else ''}")
        lines.append("-" * width)

    lines.append("=" * 80)
    lines.append("CISCO LAB ASSIGNMENT & INSTRUCTION SHEET")
    lines.append("=" * 80)
    lines.append(f"Assignment Title : {criteria.lab_title}")
    lines.append(f"Total Points     : {criteria.total_points:.1f} pts")
    lines.append(f"Total Checkpoints: {len(graded_rules)} items")
    lines.append("-" * 80)
    lines.append("")
    heading("LAB OVERVIEW & OBJECTIVES", width=40)
    lines.append(criteria.lab_description or "Complete the topology configuration according to the criteria below.")
    lines.append("When finished, upload your Packet Tracer file (.pkt, .pka, .xml) or configuration archive (.zip, .txt)")
    lines.append("to the automated evaluation engine for instant grading and diagnostic feedback.")
    lines.append("")

    # Instructor Policy Summary
    p = criteria.policies
    heading("INSTRUCTOR EVALUATION POLICIES")
    lines.append(f"• Dynamic Subnetting     : {'ENABLED (Custom IP schemes permitted; relational mutual subnets checked)' if p.allow_dynamic_subnetting else 'STRICT (Exact assigned IP addresses required)'}")
    lines.append(f"• Prefix Enforcement     : {'ENABLED (Prefix lengths /30, /24 must match)' if p.enforce_prefix_length else 'FLEXIBLE'}")
    lines.append(f"• Default Gateway Check  : {'ENABLED (Host/Switch gateway must match router subnet)' if p.verify_default_gateways else 'DISABLED'}")
    lines.append(f"• Hostname Matching      : {'FLEXIBLE (Matched by topological role & degree)' if p.allow_custom_hostnames else 'STRICT (Exact hostname required)'}")
    lines.append(f"• Interface Speed Class  : {'FLEXIBLE (Equivalent ports accepted)' if not p.strict_port_matching else 'STRICT (Exact port numbering)'}")
    lines.append(f"• Cabling Media / Auto-M : {'FLEXIBLE (Auto-MDIX copper equivalence accepted)' if not p.strict_cable_type else 'STRICT (Exact cable types required)'}")
    lines.append(f"• Routing Process IDs    : {'FLEXIBLE (Locally significant IDs ignored; Area/adjacencies checked)' if p.allow_flexible_process_ids else 'STRICT'}")
    lines.append(f"• Security Baseline      : {'GRADED (enable secret, service pw-enc, vty required)' if p.grade_security_baseline else 'NOT GRADED'}")
    lines.append(f"• Interface Descriptions : {'GRADED (Descriptive interface labels required)' if p.grade_interface_descriptions else 'NOT GRADED'}")
    lines.append(f"• Link Agreement Values  : {'STRICT (Agreed value must also match the reference)' if p.enforce_reference_link_values else 'FLEXIBLE (Both ends need only agree with each other)'}")
    lines.append("")

    # Grading Weights: how the instructor split the points between topics.
    if criteria.topic_weights:
        heading("GRADING WEIGHTS")
        lines.append(f"{'Topic':<25} | {'Weight':<7} | {'Points':<9} | Checkpoints")
        lines.append("-" * 80)
        for key, topic_rules in groups.items():
            label = TOPICS_BY_KEY[key].label
            percent = criteria.topic_weights.get(key, 0.0)
            if any(r.graded for r in topic_rules):
                points = sum(r.points for r in topic_rules)
                lines.append(f"{label:<25} | {percent:5.1f} % | {points:5.1f} pts | {len(topic_rules):>3}")
            else:
                lines.append(f"{label:<25} | {percent:5.1f} % | reference only, not graded")
        lines.append("")

    # Addressing Section
    if p.allow_dynamic_subnetting:
        rel_rules = [r for r in criteria.rules if r.category == "relational_subnet"]
        heading("DYNAMIC & RELATIONAL SUBNETTING POLICY", rel_rules)
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
            heading("IP ADDRESSING SPECIFICATION TABLE", ip_rules)
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
        heading("PHYSICAL CABLING & PORT CONNECTIONS", cabling_rules)
        lines.append(f"{'Source Device':<18} | {'Port':<16} | {'Target Device':<18} | {'Port':<16}")
        lines.append("-" * 80)
        for r in cabling_rules:
            exp = r.expected_value or {}
            lines.append(f"{exp.get('source_device', ''):<18} | {exp.get('source_interface', ''):<16} | {exp.get('target_device', ''):<18} | {exp.get('target_interface', ''):<16}")
        lines.append("")

    # VLAN & Switchport Requirements
    vlan_rules = [r for r in criteria.rules if r.category == "vlan_trunk"]
    if vlan_rules:
        heading("SWITCHING & VLAN SPECIFICATIONS", vlan_rules)
        for r in vlan_rules:
            exp = r.expected_value or {}
            mode = exp.get("switchport_mode", "access")
            if mode == "trunk":
                lines.append(f"• {r.target_device} on {r.target_interface}: Mode TRUNK (Native VLAN {exp.get('trunk_native_vlan', 1)})")
            else:
                lines.append(f"• {r.target_device} on {r.target_interface}: Access Port in VLAN {exp.get('access_vlan', 1)}")
        lines.append("")

    # Static Routing Requirements
    static_rules = [r for r in criteria.rules if r.category == "static_route"]
    if static_rules:
        heading("STATIC ROUTING REQUIREMENTS", static_rules)
        lines.append("Configure a static route for each destination below, through the neighbor listed.")
        lines.append("Either a next-hop address on the shared link or the exit interface toward that")
        lines.append("neighbor is accepted.")
        lines.append("")
        lines.append(f"{'Device':<12} | {'Destination':<42} | Via neighbor")
        lines.append("-" * 80)
        for r in static_rules:
            for route in (r.expected_value or {}).get("routes", []):
                dest = destination_label(route, p.allow_dynamic_subnetting)
                if p.allow_dynamic_subnetting and route.get("dest_device"):
                    dest += f" (/{route['cidr']})"
                elif p.allow_dynamic_subnetting and not route.get("is_default"):
                    dest += f" summary, any static route via {route['via_device']} accepted"
                lines.append(f"{r.target_device:<12} | {dest:<42} | {route['via_device']}")
        lines.append("")

    # Link Agreement Requirements
    link_rules = [r for r in criteria.rules if r.category == "link_agreement"]
    if link_rules:
        heading("LINK AGREEMENT REQUIREMENTS", link_rules)
        lines.append("Both ends of each link below must agree on the listed setting. Where the value")
        if p.enforce_reference_link_values:
            lines.append("is given, both ends must use exactly that value.")
        else:
            lines.append("reads 'your choice', any value is accepted provided BOTH ends match.")
        lines.append("")
        lines.append(f"{'Endpoint A':<24} | {'Endpoint B':<24} | {'Must agree on':<24} | {'Value':<12}")
        lines.append("-" * 80)
        for r in link_rules:
            exp = r.expected_value or {}
            attr = LINK_ATTRIBUTES.get(exp.get("attribute", ""))
            ep_a = f"{r.target_device}:{r.target_interface}"
            ep_b = f"{exp.get('peer_device')}:{exp.get('peer_interface')}"
            label = attr.label if attr else exp.get("attribute", "")
            if attr and not attr.reference_enforceable:
                value = "in use"
            elif p.enforce_reference_link_values and attr:
                value = attr.render(exp.get("reference_value"))
            else:
                value = "your choice"
            lines.append(f"{ep_a:<24} | {ep_b:<24} | {label:<24} | {value:<12}")
        lines.append("")

    # Evaluation Checklist, grouped by topic. Topics weighted 0% follow as
    # reference only, so checkpoints with no table of their own (OSPF,
    # gateways, ...) are still visible to students.
    heading("RUBRIC & POINT BREAKDOWN")
    number = 0
    reference_groups = []
    for key, topic_rules in groups.items():
        graded_here = [r for r in topic_rules if r.graded]
        if not graded_here:
            reference_groups.append((key, topic_rules))
            continue
        subtotal = sum(r.points for r in graded_here)
        lines.append(f"{TOPICS_BY_KEY[key].label} ({subtotal:.1f} pts)")
        for r in graded_here:
            number += 1
            lines.append(f"  [{r.points:4.1f} pts] #{number:02d}: {r.description}")
        lines.append("")
    if reference_groups:
        lines.append("REFERENCE ONLY (NOT GRADED)")
        for key, topic_rules in reference_groups:
            lines.append(TOPICS_BY_KEY[key].label)
            for r in topic_rules:
                lines.append(f"  - {r.description}")
        lines.append("")
    lines.append("=" * 80)
    lines.append("DO NOT MODIFY BELOW THIS LINE - MACHINE EVALUATION CRITERIA SPECIFICATION")
    lines.append("=" * 80)
    lines.append("--- CRITERIA SPEC START ---")
    lines.append(criteria.model_dump_json(indent=2))
    lines.append("--- CRITERIA SPEC END ---")
    lines.append("")

    return "\n".join(lines)
```

Before replacing, diff the 10 policy lines and the addressing, cabling, VLAN and link-agreement bodies above against the current function. They must be character-for-character identical apart from the `heading(...)` calls replacing the hard-coded `"N. TITLE"` lines and their separator lines. If the current file differs (for example, someone has edited a policy line since this plan was written), keep the file's wording.

- [ ] **Step 4: Run the tests**

Run: `python -m pytest tests/test_criteria_generator.py -v`
Expected: all PASS.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -q`
Expected: no failures. The tests that assert `DYNAMIC & RELATIONAL SUBNETTING POLICY` and `Security Baseline      : GRADED` still pass, because only the section numbers changed.

- [ ] **Step 6: Commit**

```bash
git add src/criteria_generator.py tests/test_criteria_generator.py
git commit -m "feat(instructions): add grading weights and static routing sections, group rubric by topic" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 6: API: weights in, topics out

**Files:**
- Modify: `src/topics/weights.py` (add `topic_summary`), `src/app.py`
- Test: `tests/test_app.py`, `tests/test_batch_grading.py`, `tests/test_e2e_live_server.py` (append)

**Interfaces:**
- Consumes: `generate_criteria_from_topology(..., topic_weights=)`, `TopicWeightError`, `detect_topics`, `rules_by_topic`.
- Produces:
  - `topic_summary(criteria: EvaluationCriteria, topology: TopologyResult) -> list[dict]`. Each row has keys `key, label, gradeable, devices, checkpoints, default_percent, percent, points`.
  - `POST /api/criteria/generate` accepts the form field `topic_weights` (JSON string; blank means none). It returns `topics` and `reference_warnings` alongside `criteria`, `instructions_txt` and `topology`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_app.py`:

```python
import json

from src.topics.weights import largest_remainder


def _static_chain_files():
    bundle = network_bundle("static_chain")
    return [("files", (name, text.encode("utf-8"), "text/plain")) for name, text in bundle.items()]


def _generate(**data):
    return client.post("/api/criteria/generate", files=_static_chain_files(), data=data)


def test_generate_returns_topics_and_warnings():
    data = _generate(lab_title="Static Lab").json()
    topics = {t["key"]: t for t in data["topics"]}
    static = topics["static_routing"]
    assert static["gradeable"] is True
    assert static["checkpoints"] == 3
    assert static["devices"] == ["R1", "R2", "R3"]
    assert static["percent"] == static["default_percent"]
    assert sum(t["percent"] for t in data["topics"] if t["gradeable"]) == pytest.approx(100.0)
    assert data["reference_warnings"] == []


def test_generate_lists_detected_only_topics_last():
    import os
    sample = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests", "fixtures", "sample_topology.xml")
    with open(sample, "rb") as f:
        xml = f.read()
    data = client.post("/api/criteria/generate",
                       files=[("files", ("sample_topology.xml", xml, "application/xml"))]).json()
    flags = [t["gradeable"] for t in data["topics"]]
    assert flags == sorted(flags, reverse=True)
    ssh = next(t for t in data["topics"] if t["key"] == "ssh")
    assert ssh["gradeable"] is False and ssh["percent"] is None and ssh["devices"]


def test_generate_applies_topic_weights():
    defaults = {t["key"]: t["default_percent"] for t in _generate().json()["topics"] if t["gradeable"]}
    others = [k for k in defaults if k != "static_routing"]
    units = largest_remainder([defaults[k] for k in others], 500)
    weights = {k: u / 10 for k, u in zip(others, units)}
    weights["static_routing"] = 50.0
    res = _generate(topic_weights=json.dumps(weights))
    assert res.status_code == 200
    data = res.json()
    static = next(t for t in data["topics"] if t["key"] == "static_routing")
    assert static["percent"] == 50.0 and static["points"] == 50.0
    assert "GRADING WEIGHTS" in data["instructions_txt"]


@pytest.mark.parametrize("raw,fragment", [
    ("not json", "JSON object of topic -> percent"),
    ('{"stp": 100}', "not graded yet"),
    ('{"static_routing": 100}', "Missing a weight"),
])
def test_generate_rejects_bad_weights(raw, fragment):
    res = _generate(topic_weights=raw)
    assert res.status_code == 400
    assert fragment in res.json()["detail"]


def test_generate_rejects_weights_that_grade_only_device_presence():
    weights = {t["key"]: 0 for t in _generate().json()["topics"] if t["gradeable"]}
    weights["devices"] = 100
    res = _generate(topic_weights=json.dumps(weights))
    assert res.status_code == 400
    assert "At least one topic other than Device Presence" in res.json()["detail"]
```

Append to `tests/test_batch_grading.py`. Add the imports it needs at the top of the file if they are missing: `from src.app import process_bundle_dict`, `from src.criteria_generator import format_criteria_to_instructions_txt, generate_criteria_from_topology`, `from tests.fixtures import network_bundle`.

```python
def test_error_row_counts_only_graded_checkpoints():
    defaults = generate_criteria_from_topology(process_bundle_dict(network_bundle("static_chain"))).topic_weights
    weights = dict(defaults)
    weights["static_routing"] = round(weights["static_routing"] + weights["cabling"], 1)
    weights["cabling"] = 0.0
    criteria = generate_criteria_from_topology(
        process_bundle_dict(network_bundle("static_chain")), topic_weights=weights)
    txt = format_criteria_to_instructions_txt(criteria)
    res = client.post("/api/evaluate/batch", files=[
        ("instructions_file", ("instructions.txt", txt.encode("utf-8"), "text/plain")),
        ("student_files", ("Empty Student.txt", b"   ", "text/plain")),
    ])
    assert res.status_code == 200
    row = res.json()["results"][0]
    assert row["status"].startswith("ERROR")
    assert row["failed_count"] == sum(r.graded for r in criteria.rules)
```

Append to `tests/test_e2e_live_server.py`. Add `import json` to its imports and, below the existing `from start_server import find_free_port` line, add `from src.topics.weights import largest_remainder  # noqa: E402`.

```python
def test_teacher_finalizes_a_weighted_rubric(live_server):
    sample_xml_path = os.path.join(PROJECT_ROOT, "tests", "fixtures", "sample_topology.xml")
    with open(sample_xml_path, "rb") as f:
        xml_bytes = f.read()
    files = [("files", ("sample_topology.xml", xml_bytes, "application/xml"))]

    first = requests.post(live_server + "/api/criteria/generate", files=files, timeout=60)
    assert first.status_code == 200
    defaults = {t["key"]: t["default_percent"] for t in first.json()["topics"] if t["gradeable"]}
    assert "ospf" in defaults

    others = [k for k in defaults if k != "ospf"]
    units = largest_remainder([defaults[k] for k in others], 500)
    weights = {k: u / 10 for k, u in zip(others, units)}
    weights["ospf"] = 50.0

    final = requests.post(live_server + "/api/criteria/generate", files=files,
                          data={"topic_weights": json.dumps(weights)}, timeout=60)
    assert final.status_code == 200
    data = final.json()
    assert "GRADING WEIGHTS" in data["instructions_txt"]
    ospf = next(t for t in data["topics"] if t["key"] == "ospf")
    assert ospf["percent"] == 50.0 and ospf["points"] == 50.0
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest tests/test_app.py tests/test_batch_grading.py tests/test_e2e_live_server.py -v -k "topics or weights or weighted or graded_checkpoints or device_presence"`
Expected: FAIL with `KeyError: 'topics'`, unexpected 200 responses, and a wrong `failed_count`.

- [ ] **Step 3: Add `topic_summary`**

In `src/topics/weights.py`, change the imports to:

```python
from src.models import EvaluationCriteria, EvaluationRule, TopologyResult
from src.topics.registry import TOPICS, TOPICS_BY_KEY, detect_topics, topic_for_category
```

Add `topic_summary     the rows the Teacher Studio's weights panel shows` to the module docstring list, then append:

```python
def topic_summary(criteria: EvaluationCriteria, topology: TopologyResult) -> list[dict]:
    """Rows for the weights panel: this rubric's gradeable topics, then detected-only ones."""
    defaults = criteria.reference_summary.get("default_topic_weights", {})
    rows = []
    for key, topic_rules in rules_by_topic(criteria.rules).items():
        rows.append({
            "key": key,
            "label": TOPICS_BY_KEY[key].label,
            "gradeable": True,
            "devices": sorted({r.target_device for r in topic_rules}),
            "checkpoints": len(topic_rules),
            "default_percent": defaults.get(key),
            "percent": criteria.topic_weights.get(key),
            "points": round(sum(r.points for r in topic_rules), 1),
        })
    detected = detect_topics(topology)
    for topic in TOPICS:
        if not topic.gradeable and topic.key in detected:
            rows.append({
                "key": topic.key,
                "label": topic.label,
                "gradeable": False,
                "devices": detected[topic.key],
                "checkpoints": 0,
                "default_percent": None,
                "percent": None,
                "points": None,
            })
    return rows
```

- [ ] **Step 4: Change the endpoint**

In `src/app.py`, add `import json` to the standard-library imports. Add:

```python
from src.topics.weights import TopicWeightError, topic_summary
```

In `api_generate_criteria`, add the parameter after `grade_interface_descriptions: bool = Form(False)`:

```python
    grade_interface_descriptions: bool = Form(False),
    topic_weights: str = Form(""),
```

Replace the `criteria = generate_criteria_from_topology(...)` call with:

```python
    requested_weights = None
    if topic_weights.strip():
        try:
            requested_weights = json.loads(topic_weights)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="topic_weights must be a JSON object of topic -> percent")

    try:
        criteria = generate_criteria_from_topology(
            topology=topology,
            lab_title=lab_title,
            lab_description=lab_description,
            target_total_points=total_points,
            policies=policies,
            topic_weights=requested_weights,
        )
    except TopicWeightError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

Replace the guard's first line and condition:

```python
    gradeable_rules = [r for r in criteria.rules if r.category != "device"]
    if not gradeable_rules:
```

with:

```python
    gradeable_rules = [r for r in criteria.rules if r.category != "device" and r.graded]
    if not gradeable_rules:
        if any(r.category != "device" for r in criteria.rules):
            raise HTTPException(
                status_code=400,
                detail=("Every configuration topic is set to 0%. At least one topic other than "
                        "Device Presence must carry points."),
            )
```

Keep the existing `device_names = ...` and `raise HTTPException(...)` lines below it unchanged.

Replace the return statement with:

```python
    return {
        "criteria": criteria,
        "instructions_txt": instructions_txt,
        "topology": topology,
        "topics": topic_summary(criteria, topology),
        "reference_warnings": criteria.reference_summary.get("reference_warnings", []),
    }
```

In `api_evaluate_batch`'s error row, replace `"failed_count": len(criteria.rules),` with:

```python
                "failed_count": sum(1 for r in criteria.rules if r.graded),
```

- [ ] **Step 5: Run the tests**

Run: `python -m pytest tests/test_app.py tests/test_batch_grading.py tests/test_e2e_live_server.py -v`
Expected: all PASS.

- [ ] **Step 6: Run the full suite**

Run: `python -m pytest -q`
Expected: no failures.

- [ ] **Step 7: Commit**

```bash
git add src/topics/weights.py src/app.py tests/test_app.py tests/test_batch_grading.py tests/test_e2e_live_server.py
git commit -m "feat(api): accept topic weights and return detected topics from rubric generation" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 7: Teacher Studio weights panel

**Files:**
- Modify: `templates/index.html` (teacher result card, generate button), `static/js/app.js`, `static/css/style.css`
- Test: `tests/test_frontend_escaping.py` (append), plus browser verification

**Interfaces:**
- Consumes: the `/api/criteria/generate` response from Task 6.
- Produces: the UI states `idle → weighting → finalized ⇄ stale` (spec §4.12).

- [ ] **Step 1: Write the failing escaping test**

Append to `tests/test_frontend_escaping.py`:

```python
def test_weights_panel_escapes_file_derived_text():
    """Topic rows carry device names and warnings taken from the reference file."""
    with open(APP_JS, encoding="utf-8") as f:
        source = f.read()
    start = source.index("function renderWeightsPanel(")
    end = source.index("\n    }\n", start)
    body = source[start:end]
    risky = [expr.strip() for expr in INTERPOLATION.findall(body)
             if re.search(r"\b(label|devices|warning|key)\b", expr)]
    assert risky, "renderWeightsPanel no longer interpolates topic fields; update this test"
    unescaped = [expr for expr in risky if not expr.startswith("escapeHtml(")]
    assert not unescaped, unescaped
```

Run: `python -m pytest tests/test_frontend_escaping.py -v`
Expected: FAIL with `ValueError: substring not found`, because `renderWeightsPanel` does not exist yet.

- [ ] **Step 2: Replace the result card markup**

In `templates/index.html`, change the generate button label from `⚡ Generate Rubric & instructions.txt` to `⚡ Generate Rubric & Detect Topics`.

Replace the whole `<div class="panel-card teacher-result-card" id="teacher-result-card" ...> ... </div>` block (from `<!-- Teacher Output & Download Card -->` to its closing `</div>`, just before `<!-- Batch Grading`) with:

```html
                    <!-- Teacher Output: grading weights, then the finalized instructions sheet -->
                    <div class="panel-card teacher-result-card" id="teacher-result-card" style="display: none;">
                        <div class="card-header">
                            <span class="card-icon">⚖️</span>
                            <h3>Grading Weights &amp; Instructions Sheet</h3>
                            <span id="teacher-rules-count-badge" class="badge badge-amber">Weights not finalized</span>
                        </div>
                        <p class="card-desc">These are the configuration topics found in your reference file. Set how much of the grade each one carries, then finalize to build <code>instructions.txt</code>. A topic at 0% is not graded, but its tables still print for students.</p>

                        <div class="weights-panel">
                            <div class="weights-header">
                                <span class="weights-title">Topic weights</span>
                                <span id="teacher-weights-total" class="weights-total">Total: 100.0%</span>
                            </div>
                            <div id="teacher-weights-rows" class="weights-rows"></div>
                            <div id="teacher-weights-detected" class="weights-detected" style="display: none;"></div>
                            <div id="teacher-weights-warnings" class="weights-warnings" style="display: none;"></div>
                            <div id="teacher-weights-error" class="weights-error" role="alert" style="display: none;"></div>
                            <div class="card-actions-row weights-actions">
                                <button id="teacher-weights-reset" type="button" class="btn btn-outline btn-sm">Reset to defaults</button>
                                <button id="teacher-weights-even" type="button" class="btn btn-outline btn-sm">Distribute evenly</button>
                                <button id="teacher-finalize-btn" type="button" class="btn btn-primary btn-sm">✅ Finalize rubric</button>
                            </div>
                        </div>

                        <div id="teacher-instructions-section" style="display: none;">
                            <div id="teacher-preview-stale" class="weights-stale" style="display: none;">Weights changed since you finalized. Finalize again to update instructions.txt.</div>
                            <div class="instructions-preview-box">
                                <pre id="teacher-instructions-preview"><code><!-- Generated instructions.txt content --></code></pre>
                            </div>
                            <div class="card-actions-row">
                                <button id="teacher-download-btn" class="btn btn-primary btn-sm">
                                    <span>📥 Download instructions.txt</span>
                                </button>
                                <button id="teacher-copy-btn" class="btn btn-outline btn-sm">
                                    <span>📋 Copy to Clipboard</span>
                                </button>
                            </div>
                        </div>
                    </div>
```

- [ ] **Step 3: Add the styles**

Append to `static/css/style.css`:

```css
/* Grading weights panel (Teacher Studio) */
.weights-panel {
    margin: 12px 0 16px;
    padding: 14px;
    background-color: var(--bg-surface-subtle);
    border: 1px solid var(--border-color);
    border-radius: 10px;
}
.weights-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.weights-title { font-weight: 600; color: var(--text-primary); }
.weights-total { font-weight: 600; font-variant-numeric: tabular-nums; color: var(--accent-green); }
.weights-total.is-off { color: var(--accent-red); }
.weights-rows { display: flex; flex-direction: column; gap: 8px; }
.weight-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 84px 120px 104px auto;
    align-items: center;
    gap: 10px;
}
.weight-row.is-zero .weight-label { color: var(--text-muted); }
.weight-topic { display: flex; flex-direction: column; min-width: 0; }
.weight-label { color: var(--text-primary); font-weight: 500; }
.weight-meta { color: var(--text-muted); font-size: 0.8rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.weight-input { width: 84px; text-align: right; font-variant-numeric: tabular-nums; }
.weight-bar { height: 6px; background-color: var(--bg-base); border-radius: 3px; overflow: hidden; }
.weight-bar-fill { display: block; height: 100%; width: 0; background-color: var(--accent-blue); transition: width 0.15s ease; }
.weight-points { color: var(--text-secondary); font-size: 0.85rem; font-variant-numeric: tabular-nums; }
.weights-detected, .weights-warnings, .weights-error { margin-top: 12px; font-size: 0.85rem; }
.weights-detected { color: var(--text-secondary); }
.weights-detected-title { color: var(--text-muted); margin-right: 4px; }
.weights-chip { display: inline-block; margin: 2px 4px 2px 0; padding: 2px 8px; border: 1px solid var(--border-highlight); border-radius: 999px; }
.weights-warnings { color: var(--accent-amber); }
.weights-error { color: var(--accent-red); }
.weights-stale { margin-bottom: 8px; padding: 8px 10px; font-size: 0.85rem; color: var(--accent-amber); background-color: var(--accent-amber-glow); border-radius: 6px; }
.weights-actions { margin-top: 14px; justify-content: flex-end; flex-wrap: wrap; }
.btn:disabled { opacity: 0.45; cursor: not-allowed; }

@media (max-width: 640px) {
    .weight-row { grid-template-columns: minmax(0, 1fr) 84px auto; }
    .weight-bar, .weight-points { display: none; }
}
```

- [ ] **Step 4: Add element references and state**

In `static/js/app.js`, after `const teacherCopyBtn = document.getElementById('teacher-copy-btn');`, add:

```js
    const teacherWeightsRows = document.getElementById('teacher-weights-rows');
    const teacherWeightsTotal = document.getElementById('teacher-weights-total');
    const teacherWeightsDetected = document.getElementById('teacher-weights-detected');
    const teacherWeightsWarnings = document.getElementById('teacher-weights-warnings');
    const teacherWeightsError = document.getElementById('teacher-weights-error');
    const teacherWeightsResetBtn = document.getElementById('teacher-weights-reset');
    const teacherWeightsEvenBtn = document.getElementById('teacher-weights-even');
    const teacherFinalizeBtn = document.getElementById('teacher-finalize-btn');
    const teacherInstructionsSection = document.getElementById('teacher-instructions-section');
    const teacherPreviewStale = document.getElementById('teacher-preview-stale');
```

After `let generatedInstructionsText = "";`, add:

```js
    // Grading weights panel (docs/superpowers/specs/2026-10-18-topic-weighted-rubrics-design.md).
    // idle -> weighting (Generate) -> finalized (Finalize) -> stale (a weight edited)
    const FOCUS_SHARE = 50;
    let teacherWeightsState = 'idle';
    let teacherTopics = [];      // gradeable topic rows from the last Generate
    let teacherWeights = {};     // topic key -> percent currently in the inputs
```

- [ ] **Step 5: Add the panel functions**

In `static/js/app.js`, directly after the `handleTeacherFiles` function, add:

```js
    // Mirrors largest_remainder() in src/topics/weights.py: split `units`
    // whole units in proportion to `weights`, exactly.
    function largestRemainder(weights, units) {
        const total = weights.reduce((a, b) => a + b, 0);
        if (units <= 0 || total <= 0) return weights.map(() => 0);
        const exact = weights.map(w => units * w / total);
        const alloc = exact.map(x => Math.floor(x + 1e-9));
        const leftover = units - alloc.reduce((a, b) => a + b, 0);
        const order = exact.map((_, i) => i)
            .sort((a, b) => ((exact[b] - alloc[b]) - (exact[a] - alloc[a])) || (a - b));
        for (let i = 0; i < leftover; i++) alloc[order[i]] += 1;
        return alloc;
    }

    function weightsTotal() {
        return Math.round(Object.values(teacherWeights).reduce((a, b) => a + b, 0) * 10) / 10;
    }

    // Focus: the topic takes FOCUS_SHARE, the others that carry weight scale
    // down to share the rest. A topic already at or above it is left alone.
    function focusWeights(key) {
        if ((teacherWeights[key] || 0) >= FOCUS_SHARE) return;
        const others = Object.keys(teacherWeights).filter(k => k !== key && teacherWeights[k] > 0);
        const next = {};
        Object.keys(teacherWeights).forEach(k => { next[k] = 0; });
        if (others.length === 0) {
            next[key] = 100;
        } else {
            next[key] = FOCUS_SHARE;
            const units = largestRemainder(others.map(k => teacherWeights[k]), (100 - FOCUS_SHARE) * 10);
            others.forEach((k, i) => { next[k] = units[i] / 10; });
        }
        teacherWeights = next;
    }

    function distributeWeightsEvenly() {
        const keys = Object.keys(teacherWeights);
        const units = largestRemainder(keys.map(() => 1), 1000);
        keys.forEach((k, i) => { teacherWeights[k] = units[i] / 10; });
    }

    function resetWeightsToDefaults() {
        teacherTopics.forEach(t => { teacherWeights[t.key] = t.default_percent; });
    }

    function renderWeightsPanel(data) {
        teacherTopics = data.topics.filter(t => t.gradeable);
        teacherWeights = {};
        teacherTopics.forEach(t => { teacherWeights[t.key] = t.percent; });

        teacherWeightsRows.innerHTML = teacherTopics.map(t => `
            <div class="weight-row" data-key="${escapeHtml(t.key)}">
                <div class="weight-topic">
                    <span class="weight-label">${escapeHtml(t.label)}</span>
                    <span class="weight-meta">${t.checkpoints} checkpoint${t.checkpoints === 1 ? '' : 's'} · ${escapeHtml(t.devices.join(', '))}</span>
                </div>
                <input type="number" class="form-input weight-input" min="0" max="100" step="0.1"
                       aria-label="${escapeHtml(t.label)} weight in percent">
                <div class="weight-bar"><span class="weight-bar-fill"></span></div>
                <span class="weight-points"></span>
                <button type="button" class="btn btn-outline btn-sm weight-focus">Focus</button>
            </div>`).join('');

        const detected = data.topics.filter(t => !t.gradeable);
        teacherWeightsDetected.style.display = detected.length ? 'block' : 'none';
        teacherWeightsDetected.innerHTML = detected.length
            ? '<span class="weights-detected-title">Detected, not graded yet:</span> ' + detected.map(t =>
                `<span class="weights-chip">${escapeHtml(t.label)} <small>(${escapeHtml(t.devices.join(', '))})</small></span>`).join(' ')
            : '';

        const warnings = data.reference_warnings || [];
        teacherWeightsWarnings.style.display = warnings.length ? 'block' : 'none';
        teacherWeightsWarnings.innerHTML = warnings.map(warning => `<div>⚠ ${escapeHtml(warning)}</div>`).join('');

        hideWeightsError();
        writeWeightInputs();
        refreshWeightsSummary();
    }

    function writeWeightInputs() {
        teacherWeightsRows.querySelectorAll('.weight-row').forEach(row => {
            row.querySelector('.weight-input').value = (teacherWeights[row.dataset.key] || 0).toFixed(1);
        });
    }

    function refreshWeightsSummary() {
        const total = weightsTotal();
        const ok = Math.abs(total - 100) <= 0.05;
        const points = teacherTotalPoints ? parseFloat(teacherTotalPoints.value) || 100 : 100;
        teacherWeightsTotal.textContent = `Total: ${total.toFixed(1)}% ${ok ? '✓' : '(must be 100%)'}`;
        teacherWeightsTotal.classList.toggle('is-off', !ok);
        teacherFinalizeBtn.disabled = !ok;
        teacherWeightsRows.querySelectorAll('.weight-row').forEach(row => {
            const pct = teacherWeights[row.dataset.key] || 0;
            row.querySelector('.weight-bar-fill').style.width = `${Math.min(Math.max(pct, 0), 100)}%`;
            row.querySelector('.weight-points').textContent = pct > 0
                ? `≈${(pct / 100 * points).toFixed(1)} pts` : 'reference only';
            row.classList.toggle('is-zero', pct === 0);
        });
    }

    function setWeightsState(state) {
        teacherWeightsState = state;
        if (teacherResultCard) teacherResultCard.style.display = state === 'idle' ? 'none' : 'block';
        const showPreview = state === 'finalized' || state === 'stale';
        if (teacherInstructionsSection) teacherInstructionsSection.style.display = showPreview ? 'block' : 'none';
        if (teacherPreviewStale) teacherPreviewStale.style.display = state === 'stale' ? 'block' : 'none';
        if (teacherDownloadBtn) teacherDownloadBtn.disabled = state !== 'finalized';
        if (teacherCopyBtn) teacherCopyBtn.disabled = state !== 'finalized';
        if (teacherRulesCountBadge && state === 'weighting') {
            teacherRulesCountBadge.textContent = 'Weights not finalized';
            teacherRulesCountBadge.className = 'badge badge-amber';
        }
    }

    function weightsEdited() {
        refreshWeightsSummary();
        if (teacherWeightsState === 'finalized') setWeightsState('stale');
    }

    // Files or policies changed: the topic list may differ, so start over.
    function invalidateWeights() {
        if (teacherWeightsState !== 'idle') setWeightsState('idle');
    }

    function showWeightsError(message) {
        teacherWeightsError.textContent = message;
        teacherWeightsError.style.display = 'block';
    }

    function hideWeightsError() {
        teacherWeightsError.textContent = '';
        teacherWeightsError.style.display = 'none';
    }

    function buildTeacherFormData(weights) {
        const formData = new FormData();
        teacherSelectedFiles.forEach(f => formData.append('files', f));
        formData.append('lab_title', teacherLabTitle ? teacherLabTitle.value.trim() || 'Packet Tracer Lab Assignment' : 'Packet Tracer Lab Assignment');
        formData.append('lab_description', teacherLabDesc ? teacherLabDesc.value.trim() : '');
        formData.append('total_points', teacherTotalPoints ? parseFloat(teacherTotalPoints.value) || 100.0 : 100.0);
        formData.append('allow_dynamic_subnetting', document.getElementById('policy-allow-dynamic-subnetting')?.checked ? 'true' : 'false');
        formData.append('enforce_prefix_length', document.getElementById('policy-enforce-prefix-length')?.checked ? 'true' : 'false');
        formData.append('verify_default_gateways', document.getElementById('policy-verify-default-gateways')?.checked ? 'true' : 'false');
        formData.append('allow_custom_hostnames', document.getElementById('policy-allow-custom-hostnames')?.checked ? 'true' : 'false');
        formData.append('strict_port_matching', document.getElementById('policy-strict-port-matching')?.checked ? 'true' : 'false');
        formData.append('strict_cable_type', document.getElementById('policy-strict-cable-type')?.checked ? 'true' : 'false');
        formData.append('allow_flexible_process_ids', document.getElementById('policy-allow-flexible-process-ids')?.checked ? 'true' : 'false');
        formData.append('grade_security_baseline', document.getElementById('policy-grade-security-baseline')?.checked ? 'true' : 'false');
        formData.append('grade_interface_descriptions', document.getElementById('policy-grade-interface-descriptions')?.checked ? 'true' : 'false');
        if (weights) formData.append('topic_weights', JSON.stringify(weights));
        return formData;
    }
```

- [ ] **Step 6: Rewire Generate, add Finalize, gate Download and Copy**

In the `teacherGenerateBtn` click handler, keep the `if (teacherSelectedFiles.length === 0) { ... }` guard. Replace everything from `const formData = new FormData();` through the end of the `try { ... }` block (before `catch`) with:

```js
            const formData = buildTeacherFormData(null);

            try {
                showLoading("Extracting reference topology & detecting configuration topics...");
                const res = await fetch('/api/criteria/generate', { method: 'POST', body: formData });
                if (!res.ok) {
                    throw new Error(await describeFailure(res, `Server error ${res.status}`));
                }
                const data = await res.json();

                generatedInstructionsText = "";
                renderWeightsPanel(data);
                setWeightsState('weighting');

                if (data.topology) {
                    renderTopology(data.topology);
                }
                showToast("Rubric generated. Review the grading weights, then finalize.");
```

Keep the existing `catch` and `finally` blocks unchanged.

After the generate handler's closing `}`, add the Finalize handler and the panel event wiring:

```js
    if (teacherFinalizeBtn) {
        teacherFinalizeBtn.addEventListener('click', async () => {
            if (teacherSelectedFiles.length === 0) {
                alert("Please upload a reference Packet Tracer (.pkt/.xml) or config bundle.");
                return;
            }
            const formData = buildTeacherFormData(teacherWeights);
            try {
                showLoading("Applying grading weights & building instructions.txt...");
                const res = await fetch('/api/criteria/generate', { method: 'POST', body: formData });
                if (!res.ok) {
                    throw new Error(await describeFailure(res, `Server error ${res.status}`));
                }
                const data = await res.json();
                hideWeightsError();
                generatedInstructionsText = data.instructions_txt;
                if (teacherInstructionsPreview) teacherInstructionsPreview.textContent = generatedInstructionsText;
                const graded = data.criteria.rules.filter(r => r.graded !== false).length;
                if (teacherRulesCountBadge) {
                    teacherRulesCountBadge.textContent = `${graded} Checkpoints (${data.criteria.total_points} pts)`;
                    teacherRulesCountBadge.className = 'badge badge-green';
                }
                setWeightsState('finalized');
                showToast("Rubric finalized. instructions.txt is ready to download.");
            } catch (err) {
                showWeightsError(err.message);
            } finally {
                hideLoading();
            }
        });
    }

    if (teacherWeightsRows) {
        teacherWeightsRows.addEventListener('input', (e) => {
            if (!e.target.classList.contains('weight-input')) return;
            const key = e.target.closest('.weight-row').dataset.key;
            const value = parseFloat(e.target.value);
            teacherWeights[key] = Number.isFinite(value) ? Math.round(value * 10) / 10 : 0;
            weightsEdited();
        });
        teacherWeightsRows.addEventListener('change', (e) => {
            if (e.target.classList.contains('weight-input')) writeWeightInputs();
        });
        teacherWeightsRows.addEventListener('click', (e) => {
            const btn = e.target.closest('.weight-focus');
            if (!btn) return;
            focusWeights(btn.closest('.weight-row').dataset.key);
            writeWeightInputs();
            weightsEdited();
        });
    }
    if (teacherWeightsResetBtn) {
        teacherWeightsResetBtn.addEventListener('click', () => { resetWeightsToDefaults(); writeWeightInputs(); weightsEdited(); });
    }
    if (teacherWeightsEvenBtn) {
        teacherWeightsEvenBtn.addEventListener('click', () => { distributeWeightsEvenly(); writeWeightInputs(); weightsEdited(); });
    }
    if (teacherTotalPoints) {
        teacherTotalPoints.addEventListener('input', () => { if (teacherWeightsState !== 'idle') refreshWeightsSummary(); });
    }
    Object.values(policyElements).forEach(el => { if (el) el.addEventListener('change', invalidateWeights); });
```

In the `teacherDownloadBtn` handler, change `if (!generatedInstructionsText) return;` to:

```js
            if (!generatedInstructionsText || teacherWeightsState !== 'finalized') return;
```

Make the same change in the `teacherCopyBtn` handler.

- [ ] **Step 7: Invalidate on file, policy and reset changes, and show graded counts to students**

- In `handleTeacherFiles(files)`, add `invalidateWeights();` directly after `teacherSelectedFiles = Array.from(files);`.
- In the `teacherClearBtn` click handler, add `invalidateWeights();` as the last line.
- In `applyPolicyValues(values, activeBtn)`, add `invalidateWeights();` as the last line. The profile buttons set `.checked` directly, which fires no `change` event.
- In the global `resetBtn` click handler, replace `if (teacherResultCard) teacherResultCard.style.display = 'none';` with `setWeightsState('idle');`.
- In the student `/api/criteria/parse` success path, replace

```js
            if (criteriaRulesTag) criteriaRulesTag.textContent = `${crit.rules.length} Checkpoints`;
```

with

```js
            if (criteriaRulesTag) criteriaRulesTag.textContent = `${crit.rules.filter(r => r.graded !== false).length} Checkpoints`;
```

- [ ] **Step 8: Run the frontend tests**

Run: `python -m pytest tests/test_frontend_escaping.py tests/test_e2e_live_server.py tests/test_instructor_access.py -v`
Expected: all PASS.

- [ ] **Step 9: Verify in the built-in browser**

1. `preview_start` with `{name: "neteval"}` (from `.claude/launch.json`, port 8765). The browser pane connects from loopback, so Instructor Studio renders.
2. Click the Instructor Studio tab (`#nav-mode-teacher`).
3. Load the reference files with `javascript_tool`: build three `File` objects from the `R1.txt`, `R2.txt` and `R3.txt` strings of the `static_chain` bundle in `tests/fixtures.py`, then attach them:

```js
const dt = new DataTransfer();
[['R1.txt', R1], ['R2.txt', R2], ['R3.txt', R3]].forEach(([name, text]) => dt.items.add(new File([text], name, { type: 'text/plain' })));
const input = document.getElementById('teacher-file-input');
input.files = dt.files;
input.dispatchEvent(new Event('change'));
```

4. Click **Generate**. Use `read_page` to confirm: five rows (Device Presence, IP Addressing, Interface Status, Cabling, Static Routing), the total reads `100.0% ✓`, and `#teacher-instructions-section` is hidden.
5. Click **Focus** on Static Routing. Confirm the input reads `50.0` and the total is still `100.0%`.
6. Type `0` into Cabling. Confirm the total turns red and Finalize is disabled. Click **Reset to defaults**, then **Focus** Static Routing again.
7. Click **Finalize**. Confirm the preview contains `GRADING WEIGHTS` and `STATIC ROUTING REQUIREMENTS`, the badge is green, and Download is enabled.
8. Change any weight. Confirm the stale banner shows and Download is disabled. Click **Finalize** again and confirm Download is re-enabled.
9. Toggle any policy checkbox. Confirm the result card hides.
10. Check `read_console_messages` with `onlyErrors: true`. Expected: none.
11. Resize to the `mobile` preset, take a screenshot, and confirm there is no horizontal scroll. Then reset to `desktop`.
12. Take a screenshot of the finalized panel for the hand-off message.

- [ ] **Step 10: Run the full suite**

Run: `python -m pytest -q`
Expected: no failures.

- [ ] **Step 11: Commit**

```bash
git add templates/index.html static/js/app.js static/css/style.css tests/test_frontend_escaping.py
git commit -m "feat(ui): add grading weights panel with focus, reset and finalize gate" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 8: Validation harness, static-routing reference and cases

**Files:**
- Modify: `validation/reference.py`, `validation/mutations.py`, `validation/harness.py`, `tests/test_validation.py`

**Interfaces:**
- Consumes: the full grading pipeline.
- Produces:
  - `build_static_reference() -> TopologyResult`
  - `Mutation.reference: str = "default"`
  - `harness.REFERENCES: dict[str, Callable[[], TopologyResult]]`
  - Four catalogue entries

- [ ] **Step 1: Write the failing tests**

In `tests/test_validation.py`, change `test_the_reference_is_a_correct_network` so it checks every reference. Replace its body with:

```python
    for build in harness.REFERENCES.values():
        for policies in {m.policies.model_dump_json() for m in CATALOGUE}:
            pol = EvaluationPolicies.model_validate_json(policies)
            report = evaluate_student_submission(
                generate_criteria_from_topology(build(), policies=pol),
                build(),
            )
            assert report.percentage == 100.0, (
                f"{build.__name__} is not clean under {pol.model_dump()}: "
                f"{[(r.rule_id, r.actual_value) for r in report.results if not r.passed]}"
            )
```

`harness` is already imported in that file as a module, since it is used by `test_every_catalogue_entry_behaves_as_declared`. If it is not, add `from validation import harness`.

Append:

```python
def test_static_reference_produces_static_route_rules():
    from validation.reference import build_static_reference
    criteria = generate_criteria_from_topology(build_static_reference())
    assert {r.target_device for r in criteria.rules if r.category == "static_route"} == {"R1", "R2"}
    assert not [r for r in criteria.rules if r.category == "routing"]


def test_static_cases_are_in_the_catalogue():
    ids = {m.id for m in CATALOGUE if m.reference == "static"}
    assert ids == {"static_route_deleted", "static_route_wrong_neighbor",
                   "static_route_exit_interface", "static_lan_renumbered"}
```

Run: `python -m pytest tests/test_validation.py -v`
Expected: FAIL with `AttributeError: module 'validation.harness' has no attribute 'REFERENCES'`, an `ImportError`, and an `AttributeError` on `reference`.

- [ ] **Step 2: Add the static reference**

In `validation/reference.py`, add `RouteEntry` to the `from src.models import (...)` list. Add this line to the module docstring's category list:

```
  static_route      build_static_reference(): the same network routed statically
```

Append:

```python
def build_static_reference() -> TopologyResult:
    """
    The reference network routed with static routes instead of OSPF. R2
    gains a LAN of its own; R1 routes to it by next hop and R2 points a
    default route back at R1. Graded against its own rubric it must score 100%.
    """
    topo = build_reference()
    r1, r2 = topo.devices["R1"], topo.devices["R2"]
    r1.ospf_processes = []
    r2.ospf_processes = []
    r2.interfaces["GigabitEthernet0/1"] = _routed("GigabitEthernet0/1", "192.168.20.1", 24, "192.168.20.0")
    r1.routes = [RouteEntry(network="192.168.20.0", cidr=24, protocol="S", next_hop="10.0.0.2")]
    r2.routes = [RouteEntry(network="0.0.0.0", cidr=0, protocol="S", next_hop="10.0.0.1")]
    return topo
```

- [ ] **Step 3: Add the mutation field and cases**

In `validation/mutations.py`, add the field at the end of `class Mutation`'s fields, after `policies`:

```python
    reference: str = "default"              # which validation/reference.py builder
```

Add these functions after `_extra_unrelated_interface`:

```python
def _static_route_deleted(topo):
    topo.devices["R1"].routes = []


def _static_route_wrong_neighbor(topo):
    """R1 hands traffic for R2's LAN to PC1 instead of R2."""
    topo.devices["R1"].routes[0].next_hop = "192.168.10.11"


def _static_route_exit_interface(topo):
    """`ip route ... GigabitEthernet0/0` instead of R2's address."""
    route = topo.devices["R1"].routes[0]
    route.next_hop = None
    route.outgoing_interface = "GigabitEthernet0/0"


def _static_lan_renumbered(topo):
    """R2's LAN on the student's own subnet, and R1's route following it."""
    lan = topo.devices["R2"].interfaces["GigabitEthernet0/1"]
    lan.ip_address, lan.network_address = "192.168.50.1", "192.168.50.0"
    topo.devices["R1"].routes[0].network = "192.168.50.0"
```

In `CATALOGUE`, add these two entries at the end of the positive block, directly above the `# --- negative ---` comment:

```python
    Mutation(
        id="static_route_deleted",
        label="Static route left out",
        fault="R1 has no route to R2's LAN",
        apply=_static_route_deleted,
        expect_categories=frozenset({"static_route"}),
        expect_mentions=("no static route",),
        reference="static",
    ),
    Mutation(
        id="static_route_wrong_neighbor",
        label="Static route aimed at the wrong neighbor",
        fault="R1 sends traffic for R2's LAN to PC1 instead of R2",
        apply=_static_route_wrong_neighbor,
        expect_categories=frozenset({"static_route"}),
        expect_mentions=("should go via R2",),
        reference="static",
    ),
```

Add these two at the end of the list, directly above the closing `]`:

```python
    Mutation(
        id="static_route_exit_interface",
        label="Static route written with an exit interface",
        fault="R1 names GigabitEthernet0/0 instead of R2's address",
        apply=_static_route_exit_interface,
        reference="static",
    ),
    Mutation(
        id="static_lan_renumbered",
        label="Static route to a student-chosen subnet",
        fault="R2's LAN uses 192.168.50.0/24 and R1's route follows it",
        apply=_static_lan_renumbered,
        policies=DYNAMIC,
        reference="static",
    ),
```

- [ ] **Step 4: Teach the harness about references**

In `validation/harness.py`, change `from validation.reference import build_reference` to:

```python
from validation.reference import build_reference, build_static_reference
```

Below the imports, add:

```python
# Each mutation names the reference it is injected into (Mutation.reference).
REFERENCES = {"default": build_reference, "static": build_static_reference}
```

Replace the body of `_check_reference` after its docstring with:

```python
    scores = [_grade(build(), build(), policies).percentage for build in REFERENCES.values()]
    return all(score == 100.0 for score in scores), min(scores)
```

In `run_mutation`, replace

```python
    reference = build_reference()
    student = build_reference()
```

with

```python
    build = REFERENCES[mutation.reference]
    reference = build()
    student = build()
```

- [ ] **Step 5: Run the tests and the harness**

Run: `python -m pytest tests/test_validation.py -v`, then `python -m validation`
Expected: all PASS. The harness reports 29 cases and 100% on every metric. If `static_lan_renumbered` fails, print its failed rules. A relational-subnet or gateway failure there means the mutation also needs to move something else, as the existing renumbering cases do. Fix the mutation, not the grader, unless the grader is wrong.

- [ ] **Step 6: Run the full suite**

Run: `python -m pytest -q`
Expected: no failures.

- [ ] **Step 7: Commit**

```bash
git add validation/reference.py validation/mutations.py validation/harness.py tests/test_validation.py
git commit -m "feat(validation): add static-routing reference and four static-route cases" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 9: Documentation

**Files:**
- Modify: `docs/SYSTEM.md`, `README.md`, `docs/DEVELOPMENT_LOG.md`

**Interfaces:** none (documentation only).

- [ ] **Step 1: `docs/SYSTEM.md` §2 module map**

Add these rows after the `src/feedback.py` row:

```markdown
| `src/topics/registry.py` | Which configuration topics exist, which rule categories each owns, and deterministic detection of each topic in a reference. |
| `src/topics/weights.py` | Splits a lab's points between topics: defaults, validation, apportionment, and the weights-panel rows. |
| `src/topics/static_routes.py` | Static-route rules and grading: destination plus correct neighbor. |
```

- [ ] **Step 2: `docs/SYSTEM.md` §3.1**

Change "Eleven categories exist:" to "Twelve categories exist:". Add this row after the `routing` row:

```markdown
| `static_route` | Each static route the reference configures exists on the student's device, reaches the same destination (the student's own subnet under dynamic subnetting; `0.0.0.0/0` for a default route) and hands traffic to the counterpart of the same neighbor, by next hop or exit interface. Partial coverage earns proportional credit but does not pass. Graded by `src/topics/static_routes.py`. |
```

Replace the paragraph starting "Points are apportioned across all rules" with:

```markdown
Points are apportioned by largest-remainder (Hamilton) apportionment in
tenths of a point, so a rubric always totals exactly its target. A graded rule
is never worth zero or less. Only a rule whose topic the instructor set to 0%
carries zero points, and that rule is not graded (§3.3).
```

- [ ] **Step 3: `docs/SYSTEM.md` new §3.3**

Add after §3.2, before the `---` that precedes §4:

```markdown
### 3.3 Topics and weights

A *topic* is what an instructor teaches ("Static Routing", "VLANs &
Trunking"). A category is what a rule checks. `src/topics/registry.py` maps
every category to exactly one topic, so points can be split by topic without
touching grading.

**Detection.** After Generate, the Teacher Studio lists every topic in the
reference: the gradeable topics that produced rules, and twelve detected-only
topics (STP, EtherChannel, port security, HSRP, DHCP, inter-VLAN routing,
ACLs, NAT, SSH, EIGRP, RIP, IPv6). The detected-only topics are found by
deterministic patterns over the running-config, kept on
`ParsedDevice.config_lines`, which is never serialized. Lines every config
prints by default (`spanning-tree mode pvst`, `no ipv6 cef`) never count.
Detected-only topics carry no points.

**Defaults.** The rubric is first normalized exactly as before topic weights
existed. Each topic's share of those points, rounded to one decimal, is its
default percent. Accepting the defaults reproduces that rubric point for
point.

**Applying weights** (`src/topics/weights.py`). The total is split across
topics by percent, then inside each topic by the rules' base points, both by
largest-remainder apportionment in tenths. A topic at 0% stays in the rubric
with `graded=False` and 0 points. `instructions.txt` still prints its tables,
marked reference only, and the evaluator still uses its rules to match
devices, but the topic neither earns nor costs anything. Weights must be
0–100 with one decimal place and sum to 100 (±0.05). A graded topic needs at
least 0.1 pt per checkpoint. The chosen split is stored in
`EvaluationCriteria.topic_weights` and printed in the sheet's Grading Weights
section.
```

- [ ] **Step 4: `docs/SYSTEM.md` §8, §9, §10**

- §8: change the heading `### Twenty-five cases` to `### Twenty-nine cases`. Add a sentence under it: "Four of them (`static_route_deleted`, `static_route_wrong_neighbor`, `static_route_exit_interface`, `static_lan_renumbered`) run against `build_static_reference()`, the same network routed statically instead of with OSPF." If §8 lists every case in a table, add the four ids in the same format, the first two as positive and the last two as negative.
- §9 Screens: append to the Instructor Studio bullet: "After Generate, a **Grading Weights** panel lists the configuration topics found in the reference with a percentage each (Focus, Reset to defaults, Distribute evenly). `instructions.txt` is offered only after **Finalize**."
- §9 API: replace the `/api/criteria/generate` row's purpose with: "Reference + policies (+ optional `topic_weights`) → `instructions.txt`, plus `topics` for the weights panel and `reference_warnings`. **Instructor only.**"
- §10: replace the `Protocol coverage` row's detail with: "EIGRP, RIP, BGP, DHCP, NAT, ACLs, HSRP, port security, spanning tree, EtherChannel (as its own topic), SSH and IPv6 are not graded. All but BGP are detected and shown to the instructor as 'not graded yet'." Add two rows:

```markdown
| Static routes | Floating static routes (administrative distance) and IPv6 static routes are not graded. Under dynamic subnetting, a summary route that matches no interface is checked by neighbor only. |
| Topic weights | Weights are per topic. One checkpoint cannot be weighted above another in the same topic. EtherChannel mode agreement stays under Link Agreement until EtherChannel has its own grader. |
```

- [ ] **Step 5: `README.md`**

Append to the Instructor Studio bullet under "### The three screens": "After generating, set how much of the grade each detected topic carries before you download `instructions.txt`."

Add a section directly before "### Grading a whole class":

```markdown
### Weighting a lab toward this week's lesson

In **Instructor Studio**, after **Generate**, the *Grading Weights* panel
lists every configuration topic found in your reference file with its share
of the grade. Type new percentages, or press **Focus** on this week's topic
(it takes 50% and the rest scale down), then click **Finalize rubric**. Only
then is `instructions.txt` offered for download. A topic at 0% is not graded,
but its tables still print so students can build the lab. Topics the tool
cannot grade yet (STP, HSRP, ACLs, ...) are listed as "not graded yet".
```

- [ ] **Step 6: `docs/DEVELOPMENT_LOG.md`**

Run `python -m pytest -q` and `python -m validation` and keep their output. Append an entry, using the date the work lands (`date +%F`) and the numbers from that output:

```markdown
## Session: <YYYY-MM-DD> — Topic-Weighted Rubrics

### Why
- Instructors could not say which topic a lab is about. Each rule had a fixed base value, so a lab with many interfaces was graded mostly on addressing and cabling, whatever the lesson was. Static routes were parsed but never graded.

### Changes
- `src/topics/registry.py`: 23 topics. 11 gradeable topics own every rule category. 12 are detected only (STP, EtherChannel, port security, HSRP, DHCP, inter-VLAN routing, ACL, NAT, SSH, EIGRP, RIP, IPv6). Detection is deterministic over `ParsedDevice.config_lines`, which is never serialized.
- `src/topics/static_routes.py`: new `static_route` category. One rule per device with static routes. Each route must reach the same destination through the counterpart of the same neighbor. Broken reference routes are skipped and reported to the instructor.
- `src/topics/weights.py`: the default split is today's rubric. A requested split is apportioned by topic, then by base points inside each topic. A 0% topic is ungraded but still printed. Accepting the defaults reproduces today's rubric exactly.
- `/api/criteria/generate` takes `topic_weights` and returns `topics` and `reference_warnings`. The Teacher Studio shows a Grading Weights panel (Focus, Reset, Distribute evenly) and offers `instructions.txt` only after Finalize.
- `instructions.txt`: Grading Weights and Static Routing sections, reference-only markers, rubric grouped by topic, computed section numbers.
- Validation: a static-routing reference and four cases (two positive, two negative).
- Decisions D1–D8: `docs/superpowers/specs/2026-10-18-topic-weighted-rubrics-design.md`.

### Results
- Full suite: **<N> tests passing** (live-server tests included). Validation harness: <metrics line from `python -m validation`> over 29 cases.
```

Replace `<YYYY-MM-DD>`, `<N>` and the metrics placeholder with the actual values before committing.

- [ ] **Step 7: Final verification**

Run: `python -m pytest -q`
Expected: no failures. The count is 306 plus the tests this plan added.

Run: `python -m validation`
Expected: 100% on every metric over 29 cases.

Run: `git status --porcelain`
Expected: only the three documentation files modified, plus the pre-existing untracked `system.zip` and `implementation_plan.md`.

- [ ] **Step 8: Commit**

```bash
git add docs/SYSTEM.md README.md docs/DEVELOPMENT_LOG.md
git commit -m "docs: document topic weights, detection and static-route grading" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
