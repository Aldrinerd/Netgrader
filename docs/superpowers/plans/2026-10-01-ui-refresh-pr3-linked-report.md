# UI Refresh PR 3: Linked Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Grading screen's scorecard with the linked report: missed checkpoints in the list column, the student's topology on the map with the selected checkpoint highlighted, and the checkpoint's detail under the map. The report survives a refresh.

**Architecture:** The backend adds presentational fields to `RuleResult` after scoring. These are what the rubric expected (in words), which of the student's devices a checkpoint is about, the other end of a link-scoped check, the `show` commands to verify with, and the study topic. No score changes. The frontend gains a `report/` folder: `checkpoints.js` holds the data rules as pure functions (unit tested under Node), and `loss-bar.js`, `checkpoint-list.js`, `checkpoint-detail.js` and `linked-report.js` build DOM with a new `el()` helper, never `innerHTML`. The map gets a focus API (`setFocus`) whose rules live in a pure `map/highlight.js`. `core/store.js` keeps the report, selection and screen in `sessionStorage` and mirrors screen and selection to the URL hash. `legacy/app.js` wires it all into the Grading screen.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, pytest; browser-native ES modules (no build step); Node 24 `node --test` on developer machines.

**Spec:** `docs/superpowers/specs/2026-10-01-ui-refresh-design.md` (sections 5, 8.2, 9.1, 9.2, 10 PR 3). Closes #23, #29.

**Branch:** `feature/ui-refresh-3`, created from `feature/ui-refresh-2` (commit `33a4fce` or later). Open the PR against `feature/ui-refresh-2`, or against `master` once that has merged.

**Refinements to the spec, decided while planning:**
- **Two more additive `RuleResult` fields.** The first is `matched_device`, the student's hostname the checkpoint resolved to (null when the device is missing). The spec's `peer_device` is "after device mapping", but `target_device` is the rubric's name. Under custom hostnames that name is not a node on the student's map, so the highlight needs the mapped name too. The second is `topic`, the study-topic label per checkpoint, so "group by topic" uses the server's labels instead of a second copy in JavaScript.
- **(?) is not a tab stop.** It sits inside a listbox option, and a focusable button inside an option is invalid ARIA (axe `nested-interactive`). The listbox is the tab stop, Enter opens the detail, and (?) is a pointer shortcut for the same thing. PR 5 adds the narrow-layout popover (spec 7.1) and revisits this.
- **Responsive tiers wait for PR 5.** In this PR the detail sits under the map at every width.
- **"What to study next" cards are replaced** by the points-lost bar and its legend, which carry the same topics and points. The topic explanations still appear in each checkpoint's "Why it matters".
- **The context bar** gets file chips, **Grade again** and **Clear** on the Grading screen once a report exists. The score lives in the list column's header, not the bar.
- **Grade again** appears only while the uploaded files are still in memory. After a refresh the files are gone, so only Clear shows.

## Global Constraints

- No build step, no bundler, no new runtime dependency. Lab PCs install nothing new. Works fully offline.
- Browser floor stays at Chrome 80 / Firefox 74 / Safari 13.1. Do not use `structuredClone`, `Array.prototype.at`, `Object.hasOwn`, `replaceChildren` or top-level `await` in modules.
- Every value from an uploaded file or filename reaches the page only through `escapeHtml()` or `textContent` (issue #31). Modules outside `static/js/legacy/` and `static/js/core/dom.js` must not assign `innerHTML`, `outerHTML`, `insertAdjacentHTML` or `document.write`.
- `sessionStorage` is touched only by `static/js/core/store.js`; `localStorage` only by `core/storage.js` and `display-boot.js` (existing test).
- Colours only from `tokens.css`; font sizes in `rem`, never below `0.75rem` (existing tests, extended to `static/css/components/`).
- The new `RuleResult` fields are presentational. `python -m validation` stays at 100% and no `points_earned`, `passed`, `total_score` or `percentage` changes.
- Jinja's `{% if is_instructor %}` gating stays. A lab PC receives no instructor markup.
- No emoji in `templates/` or `static/js/`. Icons come only from the existing sprite (`info`, `check`, `x`, `ai` and the rest already in `static/icons/sprite.svg`).
- `python -m pytest -q` and `python -m validation` pass after every task.
- Commit messages: conventional prefix, a body explaining why, ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **A report stored by an older build** (no `matched_device`, `verify_commands` or `topic`): the list renders, no row says "Not found in your file", the map shows no badges, and nothing throws. Tested in Task 4 (`checkpoints.test.mjs`, "report without the new fields").
2. **Storage full or blocked:** a large topology overflows `sessionStorage`, or a private window refuses it. Grading still shows the report, a toast says it won't survive a refresh, and nothing throws. Tested in Task 3 (`store.test.mjs`).
3. **A hash that no longer matches:** `#grading/<id>` naming a checkpoint that passed after Grade again, a malformed escape like `#grading/%E0%A4%A`, or `#instructor` on a lab PC. Each falls back to the first missed checkpoint or the current screen. Tested in Task 3 (`parseHash`) and Task 4 (`resolveSelection`); `#instructor` on a lab PC is checked in the Task 7 walkthrough.
4. **Custom hostnames:** the student named R3 "Core3" under `allow_custom_hostnames`. The highlight must land on Core3's node. Tested in Task 2 (`test_matched_device_follows_custom_hostname_mapping`).
5. **Markup in a device name or description** (`<img src=x onerror=alert(1)>` as a hostname). It must appear as text in the list, the detail and the file chips. Tested in Task 3 (`el()` string child stays text) and enforced for every module by `test_frontend_escaping.py` and the innerHTML boundary test.

---

## File Structure

| Path | Status | Responsibility |
|---|---|---|
| `src/models.py` | Modify | `RuleResult`: `expected_text`, `matched_device`, `peer_device`, `peer_interface`, `verify_commands`, `topic` |
| `src/feedback.py` | Modify | `_VERIFY_COMMANDS`, `_LINK_AGREEMENT_COMMANDS`, `verify_commands()`, `topic_for()`; `attach_guidance` fills them |
| `src/report_fields.py` | Create | `expected_text(rule, policies)`: the rubric's expectation in words |
| `src/evaluator.py` | Modify | Fills `expected_text`, `matched_device`, `peer_device`, `peer_interface` |
| `static/js/core/dom.js` | Modify | `el(tag, attrs, children)`: builds nodes without parsing HTML |
| `static/js/core/store.js` | Create | `saveSession`, `loadSession`, `clearSession`, `parseHash`, `formatHash` |
| `static/js/map/highlight.js` | Create | Pure focus rules: `NO_FOCUS`, `linkJoins`, `nodeEmphasis`, `linkEmphasis`, `badgeCount` |
| `static/js/map/svg-shapes.js` | Modify | `createCountBadge(x, y, count)` |
| `static/js/map/topology.js` | Modify | `setFocus(focus)`; draws badges, focus ring, dimming |
| `static/js/report/checkpoints.js` | Create | Pure report rules: grouping, order, selection, badges, focus, loss segments |
| `static/js/report/loss-bar.js` | Create | Points-lost-by-topic bar and legend |
| `static/js/report/checkpoint-list.js` | Create | Listbox of missed checkpoints |
| `static/js/report/checkpoint-detail.js` | Create | Expected / Found / Points lost / Why / Check with / Ask |
| `static/js/report/linked-report.js` | Create | List column + detail + map focus; selection state |
| `static/js/legacy/app.js` | Modify | Wires the linked report, persistence, hash, context actions; drops the old scorecard |
| `static/css/components/report.css` | Create | Linked report, detail panel, map focus styles |
| `static/css/layouts/shell.css` | Modify | Context-bar actions and file chips |
| `templates/base.html` | Modify | Links `components/report.css` |
| `templates/partials/panel_grading.html` | Modify | Report card becomes the linked-report host |
| `templates/partials/visualizer.html` | Modify | `#checkpoint-detail` region under the map |
| `templates/partials/context_bar.html` | Modify | `#context-actions`: file chips, Grade again, Clear |
| `tests/test_report_fields.py` | Create | Backend fields |
| `tests/test_linked_report_markup.py` | Create | Hosts exist for both roles; old scorecard ids gone |
| `tests/test_frontend_modules.py` | Modify | `sessionStorage` confinement |
| `tests/test_styles.py` | Modify | Also scans `static/css/components/` |
| `tests/js/core.test.mjs` | Modify | `el()` |
| `tests/js/store.test.mjs` | Create | Session storage and hash |
| `tests/js/highlight.test.mjs` | Create | Focus rules |
| `tests/js/checkpoints.test.mjs` | Create | Report rules |
| `docs/SYSTEM.md` | Modify | Grading screen, report fields, persistence |

---

### Task 1: Verify commands and topics on each checkpoint

**Files:**
- Modify: `src/models.py` (`RuleResult`)
- Modify: `src/feedback.py`
- Test: `tests/test_report_fields.py` (create)

**Interfaces:**
- Produces: `RuleResult.expected_text: str | None`, `.matched_device: str | None`, `.peer_device: str | None`, `.peer_interface: str | None`, `.verify_commands: list[str]`, `.topic: str | None` (all defaulted). Produces `feedback.verify_commands(result: RuleResult) -> list[str]` and `feedback.topic_for(category: str) -> str`. After `attach_guidance`, every result has `topic`, and every failed result has `verify_commands`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_report_fields.py`:

```python
# tests/test_report_fields.py
"""
Presentational fields on each checkpoint for the linked report (spec 5.5).
They describe what the evaluator already decided and never move a score.
"""
import re
import typing

import pytest

from src.feedback import (
    _LINK_AGREEMENT_COMMANDS, attach_guidance, explain, topic_for, verify_commands,
)
from src.link_attributes import LINK_ATTRIBUTES
from src.models import EvaluationRule, RuleResult

CATEGORIES = typing.get_args(EvaluationRule.model_fields["category"].annotation)


def _result(category, passed=False, rule_id="r", **overrides):
    fields = dict(
        rule_id=rule_id, category=category, description="d",
        points_possible=10.0, points_earned=10.0 if passed else 0.0, passed=passed,
        actual_value="x", feedback="f",
        target_device="R1", target_interface="GigabitEthernet0/0",
    )
    fields.update(overrides)
    return RuleResult(**fields)


@pytest.mark.parametrize("category", CATEGORIES)
def test_every_category_has_commands_to_check_with(category):
    assert verify_commands(_result(category))


def test_every_link_attribute_has_its_own_commands():
    assert set(LINK_ATTRIBUTES) <= set(_LINK_AGREEMENT_COMMANDS)


def test_link_agreement_commands_follow_the_attribute():
    result = _result("link_agreement", rule_id="linkagree_ospf_hello_interval_r1_g0_0__r2_g0_0")
    assert verify_commands(result) == ["show ip ospf interface"]
    trunk = _result("link_agreement", rule_id="linkagree_trunk_native_vlan_s1_g0_1__s2_g0_1")
    assert verify_commands(trunk) == ["show interfaces trunk"]


# One failing result per guidance sentence that names a command.
SENTENCES = [
    ("device", {}),
    ("interface_ip", {"actual_value": "No IP configured (Unassigned)"}),
    ("interface_ip", {"actual_value": "10.0.0.9/24"}),
    ("interface_status", {"actual_value": "administratively down"}),
    ("cabling", {"actual_value": "Disconnected / Uncabled"}),
    ("vlan_trunk", {"feedback": "Expected 802.1Q trunk port, but interface is configured as 'access'."}),
    ("vlan_trunk", {"feedback": "Expected Access VLAN 10, but port is assigned to VLAN 1."}),
    ("routing", {}),
]


@pytest.mark.parametrize("category,overrides", SENTENCES)
def test_commands_named_in_guidance_are_listed_as_data(category, overrides):
    result = _result(category, **overrides)
    named = set(re.findall(r"'(show [^']+)'", explain(result)))
    assert named, "sample should exercise a sentence that names a command"
    assert named <= set(verify_commands(result))


def test_attach_guidance_sets_topic_on_every_result_and_commands_on_failures(make_report):
    report = make_report([_result("cabling", passed=True), _result("routing", passed=False)])
    before = [(r.points_earned, r.passed) for r in report.results]
    attach_guidance(report)
    assert [r.topic for r in report.results] == [topic_for("cabling"), topic_for("routing")]
    assert report.results[0].verify_commands == []
    assert report.results[1].verify_commands == verify_commands(report.results[1])
    assert [(r.points_earned, r.passed) for r in report.results] == before


def test_unknown_category_falls_back_to_the_generic_topic():
    assert topic_for("not_a_category") == "Lab requirements"
    assert verify_commands(_result("not_a_category")) == []


@pytest.fixture
def make_report():
    from src.models import EvaluationReport, TopologyResult

    def build(results):
        return EvaluationReport(
            lab_title="t", total_score=0, max_score=0, percentage=0,
            passed_count=0, failed_count=0, grade_letter="F",
            results=results, topology=TopologyResult(),
        )
    return build
```

(`_result("not_a_category")` works because `RuleResult.category` is a plain `str`, unlike `EvaluationRule.category`.)

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/test_report_fields.py -q`
Expected: FAIL at import with `ImportError: cannot import name '_LINK_AGREEMENT_COMMANDS'`.

- [ ] **Step 3: Add the fields to `RuleResult`**

In `src/models.py`, after `guidance: str | None = None` in `RuleResult`, add:

```python
    # Presentational fields for the linked report (spec 5.5). Filled after the
    # score is decided, from what the evaluator already resolved; none of them
    # is read by scoring. Defaults keep reports from older builds valid.
    expected_text: str | None = None          # the rubric's expectation, in words
    matched_device: str | None = None         # the student's device this is about; None when missing
    peer_device: str | None = None            # other end of a link-scoped check, after mapping
    peer_interface: str | None = None
    verify_commands: list[str] = Field(default_factory=list)
    topic: str | None = None                  # study topic label, as in study_topics
```

- [ ] **Step 4: Add commands and topics to `src/feedback.py`**

After `_FALLBACK_TOPIC`, add:

```python
# Commands a student can run to check each category, as data for the report's
# "Check with" chips. The guidance sentences below still name them in context;
# tests/test_report_fields.py keeps the two in step.
_VERIFY_COMMANDS: dict[str, list[str]] = {
    "device": ["show running-config | include hostname"],
    "interface_ip": ["show ip interface brief"],
    "relational_subnet": ["show ip interface brief"],
    "interface_status": ["show ip interface brief"],
    "cabling": ["show cdp neighbors"],
    "vlan_trunk": ["show interfaces trunk", "show vlan brief"],
    "routing": ["show ip protocols", "show ip ospf neighbor", "show ip route ospf"],
    "link_agreement": ["show running-config"],
    "gateway": ["show running-config | include default-gateway", "ipconfig"],
    "security": ["show running-config"],
    "documentation": ["show interfaces description"],
}

# A link agreement check names one setting; the command that shows it depends
# on which. Keyed like LINK_ATTRIBUTES.
_LINK_AGREEMENT_COMMANDS: dict[str, list[str]] = {
    "trunk_native_vlan": ["show interfaces trunk"],
    "trunk_allowed_vlans": ["show interfaces trunk"],
    "switchport_mode": ["show interfaces switchport"],
    "ospf_hello_interval": ["show ip ospf interface"],
    "ospf_dead_interval": ["show ip ospf interface"],
    "ospf_area": ["show ip ospf interface"],
    "ospf_network_type": ["show ip ospf interface"],
    "ospf_authentication": ["show ip ospf interface"],
    "mtu": ["show interfaces"],
    "speed": ["show interfaces"],
    "duplex": ["show interfaces"],
    "channel_group_mode": ["show etherchannel summary"],
    "encapsulation": ["show interfaces"],
    "clock_rate": ["show controllers"],
}


def topic_for(category: str) -> str:
    """The study-topic label for a rule category."""
    return _TOPICS.get(category, _FALLBACK_TOPIC)[0]


def verify_commands(result: RuleResult) -> list[str]:
    """Commands to check this checkpoint with. A fresh list each call."""
    if result.category == "link_agreement":
        for key, commands in _LINK_AGREEMENT_COMMANDS.items():
            if result.rule_id.startswith(f"linkagree_{key}_"):
                return list(commands)
    return list(_VERIFY_COMMANDS.get(result.category, []))
```

Replace the loop in `attach_guidance` with:

```python
    for result in report.results:
        result.guidance = explain(result)
        result.topic = topic_for(result.category)
        result.verify_commands = [] if result.passed else verify_commands(result)
```

and extend its docstring's first line to: `Populate guidance, topics, verify commands and study topics on a finished report.`

- [ ] **Step 5: Run the tests**

Run: `python -m pytest tests/test_report_fields.py tests/test_feedback.py -q`
Expected: PASS.

- [ ] **Step 6: Full suite and validation**

Run: `python -m pytest -q` then `python -m validation`
Expected: all pass; validation reports 100%.

- [ ] **Step 7: Commit**

```bash
git add src/models.py src/feedback.py tests/test_report_fields.py
git commit -m "feat(report): verify commands and study topic on each checkpoint" -m "The linked report shows 'Check with' chips and groups missed checkpoints by topic. Both come from the deterministic feedback layer as data, so the frontend never parses guidance text for commands. Added after scoring; no score field is touched." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Expected text and where each checkpoint lives

**Files:**
- Create: `src/report_fields.py`
- Modify: `src/evaluator.py`
- Test: `tests/test_report_fields.py` (append)

**Interfaces:**
- Consumes: the Task 1 fields on `RuleResult`.
- Produces: `report_fields.expected_text(rule: EvaluationRule, policies: EvaluationPolicies) -> str | None` (never raises). Every `RuleResult` from `evaluate_student_submission` now carries `expected_text`, `matched_device` (the student's hostname, which equals its key in `topology.devices`, or `None`), and `peer_device`/`peer_interface` for `cabling`, `relational_subnet` with a target, and `link_agreement` (`None` when the peer is missing or the rule has no peer).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_report_fields.py`:

```python
# --- expected_text and location (Task 2) ------------------------------------

from src.app import process_bundle_dict
from src.criteria_generator import generate_criteria_from_topology
from src.evaluator import evaluate_student_submission
from src.models import EvaluationPolicies
from src.report_fields import expected_text
from tests.fixtures import network_bundle


def _rule(category, expected, **kw):
    return EvaluationRule(
        rule_id="r", category=category, description="d",
        target_device=kw.pop("target_device", "R1"),
        target_interface=kw.pop("target_interface", "GigabitEthernet0/0"),
        expected_value=expected, **kw,
    )


STRICT = EvaluationPolicies()


def test_expected_ip():
    assert expected_text(_rule("interface_ip", {"ip_address": "10.0.0.1", "cidr": 30}), STRICT) == "10.0.0.1/30"


def test_expected_cable_names_the_cable_only_when_cable_type_is_graded():
    rule = _rule("cabling", {
        "source_device": "R1", "source_interface": "GigabitEthernet0/0",
        "target_device": "R2", "target_interface": "GigabitEthernet0/1",
        "cable_type": "eCrossOver",
    })
    assert expected_text(rule, STRICT) == "A cable from R1 GigabitEthernet0/0 to R2 GigabitEthernet0/1 (crossover)"
    assert expected_text(rule, EvaluationPolicies(strict_cable_type=False)) == \
        "A cable from R1 GigabitEthernet0/0 to R2 GigabitEthernet0/1"


def test_expected_link_agreement_shows_the_value_only_when_dictated():
    rule = _rule("link_agreement", {
        "peer_device": "R2", "peer_interface": "GigabitEthernet0/1",
        "attribute": "ospf_hello_interval", "reference_value": 10,
    })
    assert expected_text(rule, STRICT) == "Both ends agree on the OSPF hello interval"
    assert expected_text(rule, EvaluationPolicies(enforce_reference_link_values=True)) == \
        "Both ends agree on the OSPF hello interval: 10"


def test_expected_routing_mentions_process_id_only_when_graded():
    rule = _rule("routing", {"protocol": "ospf", "area": 0, "process_id": 10}, target_interface=None)
    assert expected_text(rule, STRICT) == "OSPF advertising networks into area 0"
    assert expected_text(rule, EvaluationPolicies(allow_flexible_process_ids=False)) == \
        "OSPF advertising networks into area 0, process ID 10"


def test_expected_text_never_raises():
    assert expected_text(_rule("link_agreement", {"attribute": "no_such_attr"}), STRICT) is None
    assert expected_text(_rule("interface_ip", "not a dict"), STRICT) is None
    assert expected_text(_rule("security", {"check_type": "unknown"}), STRICT) is None


def test_every_generated_rule_gets_expected_text():
    ref = process_bundle_dict(network_bundle("ospf_clean"))
    criteria = generate_criteria_from_topology(ref, lab_title="t")
    report = evaluate_student_submission(criteria, ref)
    assert all(r.expected_text for r in report.results)


def test_location_fields_on_a_flawed_submission():
    ref = process_bundle_dict(network_bundle("ospf_clean"))
    criteria = generate_criteria_from_topology(ref, lab_title="t")
    report = evaluate_student_submission(criteria, process_bundle_dict(network_bundle("subnet_cabling_error")))

    on_r3 = [r for r in report.results if r.target_device == "R3"]
    assert on_r3 and all(r.matched_device is None for r in on_r3)

    r1_r2 = [r for r in report.results if r.category == "cabling"
             and {r.target_device, (criteria_rule(criteria, r).expected_value or {}).get("target_device")} == {"R1", "R2"}]
    assert r1_r2
    for r in r1_r2:
        assert r.matched_device in ("R1", "R2") and r.peer_device in ("R1", "R2")
        assert r.peer_device != r.matched_device and r.peer_interface

    r1_r3 = [r for r in report.results if r.category == "cabling"
             and {r.target_device, (criteria_rule(criteria, r).expected_value or {}).get("target_device")} == {"R1", "R3"}]
    assert r1_r3 and all(r.peer_device is None and r.peer_interface is None for r in r1_r3
                         if r.target_device == "R1")

    device_only = [r for r in report.results if r.category in ("device", "routing", "interface_ip")]
    assert all(r.peer_device is None for r in device_only)


def criteria_rule(criteria, result):
    return next(rule for rule in criteria.rules if rule.rule_id == result.rule_id)


def test_matched_device_follows_custom_hostname_mapping():
    ref = process_bundle_dict(network_bundle("ospf_clean"))
    criteria = generate_criteria_from_topology(
        ref, lab_title="t", policies=EvaluationPolicies(allow_custom_hostnames=True))

    student = ref.model_copy(deep=True)
    dev = student.devices.pop("R3")
    dev.hostname = dev.display_name = "Core3"
    dev.canonical_name = "core3"
    student.devices["Core3"] = dev
    for link in student.links:
        if link.source_device == "R3":
            link.source_device = "Core3"
        if link.target_device == "R3":
            link.target_device = "Core3"

    report = evaluate_student_submission(criteria, student)
    on_r3 = [r for r in report.results if r.target_device == "R3"]
    assert on_r3 and all(r.matched_device == "Core3" for r in on_r3)
    peers = {r.peer_device for r in report.results if r.peer_device}
    assert "Core3" in peers and "R3" not in peers
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/test_report_fields.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.report_fields'`.

- [ ] **Step 3: Write `src/report_fields.py`**

```python
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
```

- [ ] **Step 4: Fill the fields in the evaluator**

In `src/evaluator.py`, add `from src.report_fields import expected_text` with the other `src.` imports.

After `host_iface_name` (before `_evaluate_relational_subnet`), add:

```python
def _peer_endpoint(rule: EvaluationRule) -> tuple[str | None, str | None]:
    """The other end of a link-scoped checkpoint, as the rubric names it."""
    exp = rule.expected_value if isinstance(rule.expected_value, dict) else {}
    if rule.category == "link_agreement":
        return exp.get("peer_device") or None, exp.get("peer_interface") or None
    if rule.category in ("cabling", "relational_subnet"):
        return exp.get("target_device") or None, exp.get("target_interface") or None
    return None, None


def _student_hostname(devices: dict, name: str | None, device_mapping: dict[str, str]) -> str | None:
    """The student's device a rubric name resolved to, or None when it is absent."""
    if not name:
        return None
    dev = _find_student_device(devices, name, device_mapping)
    if dev is None or dev.is_placeholder:
        return None
    return dev.hostname
```

Replace the `rule_results.append(RuleResult(...))` call with:

```python
        # Where in the student's network this checkpoint lives, for the
        # linked report's map highlight. Read-only: computed after the score.
        peer_name, peer_intf = _peer_endpoint(rule)
        peer_device = _student_hostname(devices, peer_name, device_mapping)

        rule_results.append(RuleResult(
            rule_id=rule.rule_id,
            category=rule.category,
            description=rule.description,
            points_possible=pts_possible,
            points_earned=pts_earned,
            passed=passed,
            actual_value=actual,
            feedback=feedback,
            target_device=rule.target_device,
            target_interface=rule.target_interface,
            expected_text=expected_text(rule, policies),
            matched_device=_student_hostname(devices, rule.target_device, device_mapping),
            peer_device=peer_device,
            peer_interface=peer_intf if peer_device else None,
        ))
```

- [ ] **Step 5: Run the tests**

Run: `python -m pytest tests/test_report_fields.py tests/test_evaluator.py tests/test_link_agreement.py -q`
Expected: PASS.

- [ ] **Step 6: Full suite and validation**

Run: `python -m pytest -q` then `python -m validation`
Expected: all pass; validation reports 100%.

- [ ] **Step 7: Commit**

```bash
git add src/report_fields.py src/evaluator.py tests/test_report_fields.py
git commit -m "feat(report): expected text and student-side location per checkpoint" -m "The linked report shows what the rubric expected next to what was found, and highlights the checkpoint on the student's map. Rubric names are not always the student's hostnames under custom hostnames, so the evaluator reports the device it resolved each name to, and the peer for link-scoped checks. Read-only, after scoring." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `el()` and the session store

**Files:**
- Modify: `static/js/core/dom.js`
- Create: `static/js/core/store.js`
- Modify: `tests/js/core.test.mjs`, `tests/test_frontend_modules.py`
- Create: `tests/js/store.test.mjs`

**Interfaces:**
- Produces: `el(tag: string, attrs?: object, children?: Node|string|Array) -> HTMLElement`. `attrs.className` sets `className`, `attrs.text` sets `textContent`, `null`/`false` values are skipped, `true` gives an empty attribute, and anything else becomes a string attribute. String children become text nodes.
- Produces: `saveSession(key, value) -> boolean`, `loadSession(key) -> any|null`, `clearSession(key)`, `parseHash(hash) -> { screen: 'discovery'|'instructor'|'grading'|null, selection: string|null }`, `formatHash(screen, selection?) -> string`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/js/core.test.mjs` (add `el` to the existing `dom.js` import):

```js
function fakeDocument() {
    class FakeNode {
        constructor(tag) { this.tagName = tag; this.attributes = {}; this.childNodes = []; this.className = ''; this.textContent = ''; }
        setAttribute(k, v) { this.attributes[k] = v; }
        appendChild(c) { this.childNodes.push(c); return c; }
    }
    return { createElement: (t) => new FakeNode(t), createTextNode: (t) => ({ nodeType: 3, data: t }) };
}

test('el sets className, text and attributes, skipping null and false', () => {
    globalThis.document = fakeDocument();
    const node = el('button', { className: 'btn', text: 'Go', type: 'button', hidden: true, title: null, disabled: false, tabindex: 0 });
    assert.equal(node.className, 'btn');
    assert.equal(node.textContent, 'Go');
    assert.deepEqual(node.attributes, { type: 'button', hidden: '', tabindex: '0' });
    delete globalThis.document;
});

test('el turns string children into text nodes, never markup', () => {
    globalThis.document = fakeDocument();
    const child = el('span');
    const node = el('li', {}, ['<img src=x onerror=alert(1)>', null, child]);
    assert.equal(node.childNodes.length, 2);
    assert.deepEqual(node.childNodes[0], { nodeType: 3, data: '<img src=x onerror=alert(1)>' });
    assert.equal(node.childNodes[1], child);
    delete globalThis.document;
});
```

Create `tests/js/store.test.mjs`:

```js
// tests/js/store.test.mjs
import { test, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { saveSession, loadSession, clearSession, parseHash, formatHash } from '../../static/js/core/store.js';

afterEach(() => { delete globalThis.sessionStorage; });

function memoryStorage() {
    const m = new Map();
    return {
        getItem: (k) => (m.has(k) ? m.get(k) : null),
        setItem: (k, v) => m.set(k, String(v)),
        removeItem: (k) => m.delete(k),
        _map: m,
    };
}

test('round-trips JSON under a namespaced key', () => {
    globalThis.sessionStorage = memoryStorage();
    assert.equal(saveSession('grading', { a: [1, 2] }), true);
    assert.deepEqual(loadSession('grading'), { a: [1, 2] });
    assert.ok(globalThis.sessionStorage._map.has('netgrader:grading'));
    clearSession('grading');
    assert.equal(loadSession('grading'), null);
});

test('no sessionStorage, a throwing getter, or a full quota never throws', () => {
    delete globalThis.sessionStorage;     // newer Node versions ship a global one
    assert.equal(saveSession('k', 1), false);
    assert.equal(loadSession('k'), null);
    assert.doesNotThrow(() => clearSession('k'));

    Object.defineProperty(globalThis, 'sessionStorage', {
        configurable: true,
        get() { throw new DOMException('denied', 'SecurityError'); },
    });
    assert.equal(saveSession('k', 1), false);
    assert.equal(loadSession('k'), null);
    delete globalThis.sessionStorage;

    globalThis.sessionStorage = { setItem() { throw new DOMException('full', 'QuotaExceededError'); }, getItem: () => null, removeItem() {} };
    assert.equal(saveSession('k', { big: 'x' }), false);
});

test('a stored value that is not JSON reads as nothing', () => {
    globalThis.sessionStorage = memoryStorage();
    globalThis.sessionStorage.setItem('netgrader:k', '{not json');
    assert.equal(loadSession('k'), null);
});

test('parseHash reads screen and selection', () => {
    assert.deepEqual(parseHash('#grading/ip_r1_g0_0'), { screen: 'grading', selection: 'ip_r1_g0_0' });
    assert.deepEqual(parseHash('#discovery'), { screen: 'discovery', selection: null });
    assert.deepEqual(parseHash('#grading/'), { screen: 'grading', selection: null });
    assert.deepEqual(parseHash(''), { screen: null, selection: null });
    assert.deepEqual(parseHash('#somewhere-else'), { screen: null, selection: null });
});

test('parseHash survives a malformed escape', () => {
    assert.deepEqual(parseHash('#grading/%E0%A4%A'), { screen: 'grading', selection: null });
});

test('formatHash encodes the selection and round-trips', () => {
    assert.equal(formatHash('grading', 'a b/c'), '#grading/a%20b%2Fc');
    assert.equal(formatHash('discovery'), '#discovery');
    assert.deepEqual(parseHash(formatHash('grading', 'a b/c')), { screen: 'grading', selection: 'a b/c' });
});
```

In `tests/test_frontend_modules.py`, after `test_local_storage_is_only_touched_by_the_guarded_helpers`, add:

```python
def test_session_storage_is_only_touched_by_the_store():
    users = sorted(rel for rel, path in js_files() if "sessionStorage" in _read(path))
    assert users == ["core/store.js"], users
```

- [ ] **Step 2: Run to verify they fail**

Run: `node --test tests/js/core.test.mjs tests/js/store.test.mjs`
Expected: FAIL. `el` is not exported, and `store.js` does not exist.

- [ ] **Step 3: Add `el()` to `static/js/core/dom.js`**

Append:

```js
// Builds an element without parsing HTML, so values from a file can never
// become markup. attrs: className, text (textContent), and any other key as
// an attribute -- null/false skipped, true as an empty attribute. Children
// are nodes or strings; strings become text nodes.
export function el(tag, attrs = {}, children = []) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs)) {
        if (value == null || value === false) continue;
        if (key === 'className') node.className = value;
        else if (key === 'text') node.textContent = value;
        else node.setAttribute(key, value === true ? '' : String(value));
    }
    for (const child of [].concat(children)) {
        if (child == null || child === false) continue;
        node.appendChild(typeof child === 'string' ? document.createTextNode(child) : child);
    }
    return node;
}
```

Update the file's header comment to: `The only module allowed to build markup from strings, and the home of el(), which builds nodes without any.`

- [ ] **Step 4: Create `static/js/core/store.js`**

```js
// static/js/core/store.js
// The last report, selection and screen, kept for this browser tab (issue #29).
// sessionStorage, so it is gone when the browser closes. Never throws: a
// private window, blocked site data or a full quota means nothing is kept.

const PREFIX = 'netgrader:';
const SCREENS = ['discovery', 'instructor', 'grading'];

// Returns false when the value could not be kept (unavailable or too large).
export function saveSession(key, value) {
    try {
        sessionStorage.setItem(PREFIX + key, JSON.stringify(value));
        return true;
    } catch (e) {
        return false;
    }
}

export function loadSession(key) {
    try {
        const raw = sessionStorage.getItem(PREFIX + key);
        return raw == null ? null : JSON.parse(raw);
    } catch (e) {
        return null;
    }
}

export function clearSession(key) {
    try {
        sessionStorage.removeItem(PREFIX + key);
    } catch (e) {
        // Nothing was kept, so there is nothing to clear.
    }
}

// "#grading/ip_r1_g0_0" -> { screen: 'grading', selection: 'ip_r1_g0_0' }.
// Anything unrecognised reads as no screen, so the caller keeps its own.
export function parseHash(hash) {
    const body = String(hash || '').replace(/^#/, '');
    const slash = body.indexOf('/');
    const screen = slash < 0 ? body : body.slice(0, slash);
    if (SCREENS.indexOf(screen) < 0) return { screen: null, selection: null };
    let selection = null;
    if (slash >= 0 && body.length > slash + 1) {
        try {
            selection = decodeURIComponent(body.slice(slash + 1));
        } catch (e) {
            selection = null;
        }
    }
    return { screen, selection };
}

export function formatHash(screen, selection) {
    return selection ? `#${screen}/${encodeURIComponent(selection)}` : `#${screen}`;
}
```

- [ ] **Step 5: Run the tests**

Run: `node --test tests/js/*.test.mjs` then `python -m pytest tests/test_frontend_modules.py tests/test_js_units.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add static/js/core/dom.js static/js/core/store.js tests/js/core.test.mjs tests/js/store.test.mjs tests/test_frontend_modules.py
git commit -m "feat(core): el() node builder and a session store with hash state" -m "The report modules build DOM with el(), which never parses HTML, so the #31 boundary holds structurally. store.js is the single place that touches sessionStorage and the URL hash format; it never throws, so a private window or full quota only means the report is not kept." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Report rules and map focus rules (pure)

**Files:**
- Create: `static/js/report/checkpoints.js`, `static/js/map/highlight.js`
- Create: `tests/js/checkpoints.test.mjs`, `tests/js/highlight.test.mjs`

**Interfaces:**
- Produces (`map/highlight.js`): `NO_FOCUS = { badges: {}, devices: [], link: null }`; `linkJoins(link, a, b) -> boolean`; `nodeEmphasis(hostname, focus) -> 'none'|'focus'|'dim'`; `linkEmphasis(link, focus) -> 'none'|'focus'|'dim'`; `badgeCount(hostname, focus) -> number`. A focus is `{ badges: {[hostname]: count}, devices: string[], link: [string, string] | null }`.
- Produces (`report/checkpoints.js`): `missedOf(report)`, `pointsLost(result)`, `groupMissed(missed, by: 'device'|'topic') -> [{key, label, items}]`, `displayOrder(groups) -> result[]`, `badgesFor(missed) -> {[hostname]: count}`, `focusFor(result|null, badges) -> focus`, `resolveSelection(order, id) -> result|null`, `step(order, id, delta) -> result|null`, `missedOnDevice(missed, hostname) -> result[]`, `lossSegments(studyTopics) -> [{topic, points, share, shade}]`, `lossLabel(segments) -> string`.

- [ ] **Step 1: Write the failing tests**

Create `tests/js/highlight.test.mjs`:

```js
// tests/js/highlight.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { NO_FOCUS, linkJoins, nodeEmphasis, linkEmphasis, badgeCount } from '../../static/js/map/highlight.js';

const link = { source_device: 'R1', target_device: 'R2' };

test('a link joins its two devices in either direction', () => {
    assert.equal(linkJoins(link, 'R1', 'R2'), true);
    assert.equal(linkJoins(link, 'R2', 'R1'), true);
    assert.equal(linkJoins(link, 'R1', 'R3'), false);
});

test('with nothing selected, nothing is emphasised or dimmed', () => {
    assert.equal(nodeEmphasis('R1', NO_FOCUS), 'none');
    assert.equal(linkEmphasis(link, NO_FOCUS), 'none');
});

test('a device checkpoint focuses its device and dims the rest, links included', () => {
    const focus = { badges: {}, devices: ['R1'], link: null };
    assert.equal(nodeEmphasis('R1', focus), 'focus');
    assert.equal(nodeEmphasis('R2', focus), 'dim');
    assert.equal(linkEmphasis(link, focus), 'dim');
});

test('a link checkpoint focuses both ends and the link between them', () => {
    const focus = { badges: {}, devices: ['R2', 'R1'], link: ['R2', 'R1'] };
    assert.equal(nodeEmphasis('R1', focus), 'focus');
    assert.equal(nodeEmphasis('R2', focus), 'focus');
    assert.equal(linkEmphasis(link, focus), 'focus');
    assert.equal(linkEmphasis({ source_device: 'R2', target_device: 'R3' }, focus), 'dim');
});

test('badge counts are positive integers or zero', () => {
    const focus = { badges: { R1: 3, R2: 0, R3: 'x' }, devices: [], link: null };
    assert.equal(badgeCount('R1', focus), 3);
    assert.equal(badgeCount('R2', focus), 0);
    assert.equal(badgeCount('R3', focus), 0);
    assert.equal(badgeCount('R9', focus), 0);
});
```

Create `tests/js/checkpoints.test.mjs`:

```js
// tests/js/checkpoints.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
    missedOf, pointsLost, groupMissed, displayOrder, badgesFor, focusFor,
    resolveSelection, step, missedOnDevice, lossSegments, lossLabel,
} from '../../static/js/report/checkpoints.js';

const r = (id, over = {}) => ({
    rule_id: id, passed: false, points_possible: 10, points_earned: 0,
    target_device: 'R1', target_interface: null, topic: 'Cabling',
    matched_device: 'R1', peer_device: null, ...over,
});

const report = {
    results: [
        r('a'),
        r('b', { passed: true, points_earned: 10 }),
        r('c', { target_device: 'R2', matched_device: 'R2', topic: 'Routing' }),
        r('d', { topic: 'Routing', points_earned: 4 }),
        r('e', { target_device: 'R3', matched_device: null }),
    ],
};

test('missed checkpoints are the failed ones, in rubric order', () => {
    assert.deepEqual(missedOf(report).map(x => x.rule_id), ['a', 'c', 'd', 'e']);
    assert.deepEqual(missedOf({}), []);
});

test('points lost never goes negative', () => {
    assert.equal(pointsLost(r('x', { points_earned: 4 })), 6);
    assert.equal(pointsLost(r('x', { points_earned: 12 })), 0);
});

test('grouping by device keeps first-appearance order', () => {
    const groups = groupMissed(missedOf(report), 'device');
    assert.deepEqual(groups.map(g => g.label), ['R1', 'R2', 'R3']);
    assert.deepEqual(displayOrder(groups).map(x => x.rule_id), ['a', 'd', 'c', 'e']);
});

test('grouping by topic uses the server label, with a fallback', () => {
    const missed = [...missedOf(report), r('f', { topic: null })];
    const groups = groupMissed(missed, 'topic');
    assert.deepEqual(groups.map(g => g.label), ['Cabling', 'Routing', 'Other']);
});

test('badges count missed checkpoints on devices that exist', () => {
    assert.deepEqual(badgesFor(missedOf(report)), { R1: 2, R2: 1 });
});

test('focus: device check, link check, missing device, nothing selected', () => {
    const badges = { R1: 1 };
    assert.deepEqual(focusFor(r('a'), badges), { badges, devices: ['R1'], link: null });
    assert.deepEqual(focusFor(r('l', { peer_device: 'R2' }), badges), { badges, devices: ['R1', 'R2'], link: ['R1', 'R2'] });
    assert.deepEqual(focusFor(r('m', { matched_device: null }), badges), { badges, devices: [], link: null });
    assert.deepEqual(focusFor(null, badges), { badges, devices: [], link: null });
});

test('a report without the new fields renders with no focus and no badges', () => {
    const old = { rule_id: 'x', passed: false, points_possible: 5, points_earned: 0, target_device: 'R1' };
    assert.deepEqual(badgesFor([old]), {});
    assert.deepEqual(focusFor(old, {}), { badges: {}, devices: [], link: null });
    assert.deepEqual(groupMissed([old], 'topic').map(g => g.label), ['Other']);
});

test('selection falls back to the first missed checkpoint', () => {
    const order = displayOrder(groupMissed(missedOf(report), 'device'));
    assert.equal(resolveSelection(order, 'c').rule_id, 'c');
    assert.equal(resolveSelection(order, 'b').rule_id, 'a');        // passed after Grade again
    assert.equal(resolveSelection(order, null).rule_id, 'a');
    assert.equal(resolveSelection([], 'a'), null);
});

test('arrow steps clamp at both ends', () => {
    const order = displayOrder(groupMissed(missedOf(report), 'device'));
    assert.equal(step(order, 'a', -1).rule_id, 'a');
    assert.equal(step(order, 'a', 1).rule_id, 'd');
    assert.equal(step(order, 'e', 1).rule_id, 'e');
    assert.equal(step(order, 'zzz', 1).rule_id, 'a');
});

test('missed on a device includes checks where it is the peer', () => {
    const missed = [r('a'), r('l', { matched_device: 'R2', peer_device: 'R1' }), r('c', { matched_device: 'R2' })];
    assert.deepEqual(missedOnDevice(missed, 'R1').map(x => x.rule_id), ['a', 'l']);
    assert.deepEqual(missedOnDevice(missed, 'R9'), []);
});

test('loss segments share the total and cap the shade at 5', () => {
    const topics = [
        { topic: 'A', points_lost: 6 }, { topic: 'B', points_lost: 2 }, { topic: 'Z', points_lost: 0 },
        { topic: 'C', points_lost: 1 }, { topic: 'D', points_lost: 0.5 }, { topic: 'E', points_lost: 0.25 }, { topic: 'F', points_lost: 0.25 },
    ];
    const segs = lossSegments(topics);
    assert.deepEqual(segs.map(s => s.topic), ['A', 'B', 'C', 'D', 'E', 'F']);
    assert.equal(segs[0].share, 0.6);
    assert.deepEqual(segs.map(s => s.shade), [1, 2, 3, 4, 5, 5]);
    assert.equal(lossLabel(segs.slice(0, 2)), 'Points lost by topic: A, 6 points; B, 2 points');
    assert.deepEqual(lossSegments(undefined), []);
    assert.equal(lossLabel([]), 'No points lost');
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `node --test tests/js/highlight.test.mjs tests/js/checkpoints.test.mjs`
Expected: FAIL with `ERR_MODULE_NOT_FOUND`.

- [ ] **Step 3: Create `static/js/map/highlight.js`**

```js
// static/js/map/highlight.js
// What the map emphasises for the linked report: a count badge on each device
// with missed checkpoints, and for the selected checkpoint its device -- or,
// for a link-scoped check, the link and both ends -- while the rest dims.
// Pure functions over plain data, so they are tested without a browser.
//
// focus = { badges: { [hostname]: count }, devices: [hostname], link: [a, b] | null }

export const NO_FOCUS = Object.freeze({ badges: Object.freeze({}), devices: Object.freeze([]), link: null });

export function linkJoins(link, a, b) {
    return (link.source_device === a && link.target_device === b)
        || (link.source_device === b && link.target_device === a);
}

// 'focus' = part of the selection, 'dim' = something else is selected,
// 'none' = nothing is selected.
export function nodeEmphasis(hostname, focus) {
    if (!focus.devices.length) return 'none';
    return focus.devices.indexOf(hostname) >= 0 ? 'focus' : 'dim';
}

export function linkEmphasis(link, focus) {
    if (!focus.devices.length) return 'none';
    if (focus.link && linkJoins(link, focus.link[0], focus.link[1])) return 'focus';
    return 'dim';
}

export function badgeCount(hostname, focus) {
    const n = focus.badges[hostname];
    return Number.isInteger(n) && n > 0 ? n : 0;
}
```

- [ ] **Step 4: Create `static/js/report/checkpoints.js`**

```js
// static/js/report/checkpoints.js
// The linked report's data rules, free of the DOM so they are unit tested:
// which checkpoints were missed, how they group and order, what is selected,
// and what the map should show. Fields added by the server in PR 3 may be
// absent from a report stored by an older build; every rule tolerates that.

export function missedOf(report) {
    return ((report && report.results) || []).filter(r => !r.passed);
}

export function pointsLost(result) {
    return Math.max(0, (result.points_possible || 0) - (result.points_earned || 0));
}

// Groups in first-appearance order, so the list follows the rubric.
export function groupMissed(missed, by) {
    const groups = new Map();
    for (const r of missed) {
        const key = by === 'topic' ? (r.topic || 'Other') : r.target_device;
        if (!groups.has(key)) groups.set(key, { key, label: key, items: [] });
        groups.get(key).items.push(r);
    }
    return Array.from(groups.values());
}

// What arrow keys walk through: the groups' items, in display order.
export function displayOrder(groups) {
    return groups.reduce((all, g) => all.concat(g.items), []);
}

export function badgesFor(missed) {
    const badges = {};
    for (const r of missed) {
        if (r.matched_device) badges[r.matched_device] = (badges[r.matched_device] || 0) + 1;
    }
    return badges;
}

// The map focus for the selected checkpoint (see map/highlight.js). A device
// missing from the attempt has nothing to highlight.
export function focusFor(result, badges) {
    if (!result || !result.matched_device) return { badges, devices: [], link: null };
    if (result.peer_device) {
        return { badges, devices: [result.matched_device, result.peer_device], link: [result.matched_device, result.peer_device] };
    }
    return { badges, devices: [result.matched_device], link: null };
}

// The requested checkpoint if it is still in the list, else the first.
export function resolveSelection(order, requestedId) {
    if (!order.length) return null;
    return order.find(r => r.rule_id === requestedId) || order[0];
}

// Next or previous in display order; listbox arrows stop at the ends.
export function step(order, currentId, delta) {
    const i = order.findIndex(r => r.rule_id === currentId);
    if (i < 0) return order[0] || null;
    return order[Math.max(0, Math.min(order.length - 1, i + delta))];
}

// Missed checkpoints touching one of the student's devices, as either end.
export function missedOnDevice(missed, hostname) {
    return missed.filter(r => r.matched_device === hostname || r.peer_device === hostname);
}

// The points-lost bar: each study topic's share of the points lost. Shades
// 1-5 step down in strength; topics past the fifth share the last shade.
export function lossSegments(studyTopics) {
    const topics = (studyTopics || []).filter(t => t.points_lost > 0);
    const total = topics.reduce((sum, t) => sum + t.points_lost, 0);
    return topics.map((t, i) => ({
        topic: t.topic,
        points: t.points_lost,
        share: total ? t.points_lost / total : 0,
        shade: Math.min(i, 4) + 1,
    }));
}

export function lossLabel(segments) {
    if (!segments.length) return 'No points lost';
    return 'Points lost by topic: ' + segments.map(s => `${s.topic}, ${s.points} points`).join('; ');
}
```

- [ ] **Step 5: Run the tests**

Run: `node --test tests/js/*.test.mjs` then `python -m pytest tests/test_frontend_modules.py tests/test_frontend_escaping.py tests/test_styles.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add static/js/map/highlight.js static/js/report/checkpoints.js tests/js/highlight.test.mjs tests/js/checkpoints.test.mjs
git commit -m "feat(report): pure rules for the linked report and map focus" -m "Grouping, selection, badges, focus and the points-lost bar are plain functions over the report JSON, so every rule is tested under Node without a browser. They tolerate reports stored before the new server fields existed." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Map focus: badges, rings, dimming

**Files:**
- Modify: `static/js/map/svg-shapes.js`, `static/js/map/topology.js`
- Create: `static/css/components/report.css` (map part; Task 6 appends the rest)
- Modify: `templates/base.html`, `tests/test_styles.py`

**Interfaces:**
- Consumes: `NO_FOCUS`, `nodeEmphasis`, `linkEmphasis`, `badgeCount` from Task 4.
- Produces: `map.setFocus(focus)` on the object `createTopologyMap` returns. It redraws with badges, a focus ring on focused devices, a thicker focused link, and `is-dimmed` on everything else. `render()` and `reset()` clear the focus. Produces `createCountBadge(x, y, count) -> SVGGElement` in `svg-shapes.js`.

- [ ] **Step 1: Make the style tests cover component CSS**

In `tests/test_styles.py`, `_styled_files()`, add after the layouts line:

```python
    files += glob.glob(os.path.join(ROOT, "static", "css", "components", "*.css"))
```

- [ ] **Step 2: Add the count badge to `svg-shapes.js`**

Append:

```js
// "N missed checkpoints on this device": a small circle with a number.
// Colours come from report.css classes, so every theme applies.
export function createCountBadge(x, y, count) {
    const ns = 'http://www.w3.org/2000/svg';
    const group = document.createElementNS(ns, 'g');
    group.classList.add('node-miss-badge');
    const circle = document.createElementNS(ns, 'circle');
    circle.setAttribute('cx', x);
    circle.setAttribute('cy', y);
    circle.setAttribute('r', '9');
    group.appendChild(circle);
    const label = document.createElementNS(ns, 'text');
    label.setAttribute('x', x);
    label.setAttribute('y', y + 3.5);
    label.setAttribute('text-anchor', 'middle');
    label.textContent = count > 9 ? '9+' : String(count);
    group.appendChild(label);
    return group;
}
```

- [ ] **Step 3: Wire focus into `topology.js`**

Change the import line to:

```js
import { createSvgBadge, createDeviceIcon, createCountBadge, shortInterfaceName, paint } from './svg-shapes.js';
import { NO_FOCUS, nodeEmphasis, linkEmphasis, badgeCount } from './highlight.js';
```

Add `let focus = NO_FOCUS;` after `let highlighted = new Set();`.

In `render()`, after `highlighted = new Set(highlightDevices);`, add `focus = NO_FOCUS;`. In `reset()`, after `highlighted = new Set();`, add `focus = NO_FOCUS;`.

In the link loop, after `lineGroup.style.cursor = 'pointer';`, add:

```js
            const emphasis = linkEmphasis(link, focus);
            if (emphasis === 'focus') lineGroup.classList.add('is-focus');
            if (emphasis === 'dim') lineGroup.classList.add('is-dimmed');
```

and replace `line.setAttribute('stroke-width', hasConflict ? '3.5' : '2.5');` with:

```js
            line.setAttribute('stroke-width', emphasis === 'focus' ? '4.5' : (hasConflict ? '3.5' : '2.5'));
```

In the node loop, after `nodeGroup.style.cursor = 'grab';`, add:

```js
            const emphasis = nodeEmphasis(dev.hostname, focus);
            if (emphasis === 'dim') nodeGroup.classList.add('is-dimmed');
```

After the `if (highlighted.has(dev.hostname)) { ... }` block, add:

```js
            if (emphasis === 'focus') {
                const ring = document.createElementNS(SVG_NS, 'circle');
                ring.setAttribute('cx', node.x);
                ring.setAttribute('cy', node.y);
                ring.setAttribute('r', '33');
                ring.classList.add('node-focus-ring');
                nodeGroup.appendChild(ring);
            }
```

After `nodeGroup.appendChild(label);`, add:

```js
            const misses = badgeCount(dev.hostname, focus);
            if (misses) nodeGroup.appendChild(createCountBadge(node.x + 22, node.y - 22, misses));
```

Add the API function before `// Interactive mouse zoom, pan and node drag.`:

```js
    // The linked report's emphasis (map/highlight.js). Cleared by render/reset.
    function setFocus(next) {
        focus = { ...NO_FOCUS, ...next };
        draw();
    }
```

and add `setFocus,` to the returned object.

- [ ] **Step 4: Create `static/css/components/report.css` with the map styles**

```css
/* static/css/components/report.css
   The linked report (spec section 5): list column, detail panel, and the
   map's emphasis for the selected checkpoint. Tokens only. */

/* --- Map focus --- */
.graph-link-group, .graph-node-group { transition: opacity 0.15s ease; }
.graph-link-group.is-dimmed, .graph-node-group.is-dimmed { opacity: 0.25; }

.node-focus-ring {
    fill: none;
    stroke: var(--focus-ring);
    stroke-width: 3;
}
:root[data-contrast="high"] .node-focus-ring { stroke-width: 4; }

.node-miss-badge circle { fill: var(--status-bad); }
.node-miss-badge text {
    fill: var(--surface-base);
    font-family: var(--font-mono);
    font-size: 0.75rem;
    font-weight: 700;
}
```

In `templates/base.html`, after the `layouts/shell.css` link, add:

```html
    <link rel="stylesheet" href="/static/css/components/report.css?v={{ asset_version }}">
```

- [ ] **Step 5: Run the tests**

Run: `python -m pytest tests/test_styles.py tests/test_frontend_modules.py tests/test_js_units.py tests/test_theme_tokens.py -q`
Expected: PASS.

- [ ] **Step 6: Check it in the browser**

Start the `neteval` preview and load the Discovery screen with any topology. With the browser tool's `javascript_tool`, the map object is not global, so this check only confirms nothing broke: the map draws, links and labels look as before, and the console shows no errors. The focus itself is exercised in Task 7.

- [ ] **Step 7: Commit**

```bash
git add static/js/map/svg-shapes.js static/js/map/topology.js static/css/components/report.css templates/base.html tests/test_styles.py
git commit -m "feat(map): focus API for badges, selection ring and dimming" -m "The linked report needs the map to show where each missed checkpoint is: a count badge per device, a ring on the selected checkpoint's device, the link and both ends for link-scoped checks, and everything else dimmed. Emphasis rules live in highlight.js; topology.js only draws them." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Report components and markup

**Files:**
- Create: `static/js/report/loss-bar.js`, `static/js/report/checkpoint-list.js`, `static/js/report/checkpoint-detail.js`, `static/js/report/linked-report.js`
- Modify: `static/css/components/report.css` (append), `static/css/layouts/shell.css`
- Modify: `templates/partials/panel_grading.html`, `templates/partials/visualizer.html`, `templates/partials/context_bar.html`
- Create: `tests/test_linked_report_markup.py`

**Interfaces:**
- Consumes: `el` (Task 3), `icon` (`core/icons.js`), everything in `report/checkpoints.js` (Task 4), `map.setFocus` (Task 5).
- Produces: `createLinkedReport({ listHost, detailHost, map, onSelectionChange(id, {push}), onAsk(result) })` returning `{ show(report, {selectedId}), select(id, {push=false, notify=true}), showDevice(hostname) -> boolean, clear(), applyFocus(), setAskAvailable(boolean), getSelectedId() -> string|null, focusList() }`.
- Produces markup ids: `#linked-report-list` (grading panel), `#checkpoint-detail` (under the map), `#context-actions`, `#context-file-chips`, `#grade-again-btn`, `#clear-report-btn` (context bar). Removes `#report-grade-letter`, `#report-earned-score`, `#report-max-score`, `#report-progress-fill`, `#report-passed-tag`, `#report-failed-tag`, `#filter-count-all`, `#filter-count-failed`, `#filter-count-passed`, `#report-study-topics`, `#report-results-list` and the `.filter-chip` buttons.

> **Ordering note:** The template edits here remove ids that `legacy/app.js` still looks up, so `test_every_element_the_js_looks_up_exists_*` fails until Task 7 removes those lookups. Tasks 6 and 7 are committed together at the end of Task 7. Do not commit at the end of this task.

- [ ] **Step 1: Write the failing markup test**

Create `tests/test_linked_report_markup.py`:

```python
# tests/test_linked_report_markup.py
"""The Grading screen's linked-report hosts exist for both roles (spec 5)."""
import re

import pytest

from tests.test_frontend_modules import render_page


@pytest.mark.parametrize("instructor", [True, False])
def test_linked_report_hosts_exist(instructor):
    html = render_page(instructor)
    assert 'id="linked-report-list"' in html
    assert re.search(
        r'<section id="checkpoint-detail" class="checkpoint-detail" role="region" '
        r'aria-label="Checkpoint detail" tabindex="-1" hidden>', html)
    assert re.search(r'<div class="context-actions" id="context-actions" hidden>', html)
    for element_id in ("context-file-chips", "grade-again-btn", "clear-report-btn"):
        assert f'id="{element_id}"' in html


def test_old_scorecard_is_gone():
    html = render_page(False)
    for gone in ("report-results-list", "filter-count-all", "report-study-topics",
                 "report-grade-letter", "report-progress-fill"):
        assert f'id="{gone}"' not in html
    assert 'class="filter-chip' not in html
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_linked_report_markup.py -q`
Expected: FAIL (hosts missing).

- [ ] **Step 3: Update the templates**

In `templates/partials/panel_grading.html`, replace the whole `<!-- Evaluation Scorecard Report -->` card (from `<div class="panel-card student-report-card" ...>` to its closing `</div>`, lines 61-108) with:

```html
                    <!-- Linked report: list column (spec 5.1). Filled by report/linked-report.js. -->
                    <div class="panel-card student-report-card" id="student-report-card" style="display: none;">
                        <div id="linked-report-list" class="linked-report-list"></div>

                        <div id="report-narrative" class="report-narrative" style="display:none;"></div>

                        <!-- Follow-up questions about this report, answered by the local model -->
                        <div id="report-chat" class="ai-chat" style="display:none;"></div>

                        <button id="student-download-report-btn" class="btn btn-outline btn-block" style="margin-top: 12px;">
                            <span><svg class="icon" aria-hidden="true"><use href="/static/icons/sprite.svg?v={{ asset_version }}#download"></use></svg> Download Grade Report (.txt)</span>
                        </button>
                    </div>
```

In `templates/partials/visualizer.html`, after the closing `</div>` of `#canvas-viewport` (before `<!-- Diagnostic & Evidence Drawer -->`), add:

```html
                <!-- Selected checkpoint (spec 5.3). Shown on the Grading screen only; filled by report/checkpoint-detail.js. -->
                <section id="checkpoint-detail" class="checkpoint-detail" role="region" aria-label="Checkpoint detail" tabindex="-1" hidden></section>
```

Replace `templates/partials/context_bar.html` with:

```html
<header class="context-bar">
    <h1 class="context-title" id="context-title">Topology Discovery</h1>
    <!-- Grading screen, once a report exists: what was graded, and what to do next. -->
    <div class="context-actions" id="context-actions" hidden>
        <ul class="file-chips" id="context-file-chips" aria-label="Graded files"></ul>
        <button type="button" id="grade-again-btn" class="btn btn-sm btn-outline">Grade again</button>
        <button type="button" id="clear-report-btn" class="btn btn-sm btn-outline">Clear</button>
    </div>
</header>
```

- [ ] **Step 4: Create `static/js/report/loss-bar.js`**

```js
// static/js/report/loss-bar.js
// Points lost by topic (spec 5.1): one bar, one segment per study topic, and a
// legend. The bar's accessible name lists every topic and its points.
import { el } from '../core/dom.js';
import { lossSegments, lossLabel } from './checkpoints.js';

export function buildLossBar(studyTopics) {
    const segments = lossSegments(studyTopics);
    if (!segments.length) return null;

    const bar = el('div', { className: 'loss-bar', role: 'img', 'aria-label': lossLabel(segments) });
    segments.forEach(s => {
        const seg = el('span', { className: `loss-seg loss-shade-${s.shade}` });
        seg.style.width = `${(s.share * 100).toFixed(2)}%`;
        bar.appendChild(seg);
    });

    const legend = el('ul', { className: 'loss-legend', 'aria-hidden': 'true' }, segments.map(s =>
        el('li', {}, [
            el('span', { className: `loss-swatch loss-shade-${s.shade}` }),
            el('span', { className: 'loss-topic', text: s.topic }),
            el('span', { className: 'loss-points', text: `-${s.points}` }),
        ])));

    return el('section', { className: 'loss-section' }, [
        el('h3', { className: 'report-subhead', text: 'Points lost by topic' }), bar, legend,
    ]);
}
```

- [ ] **Step 5: Create `static/js/report/checkpoint-list.js`**

```js
// static/js/report/checkpoint-list.js
// Missed checkpoints as one listbox (spec 5.1, 7.1). Focus stays on the
// listbox; aria-activedescendant names the selected row. Arrow keys, Home and
// End move the selection; Enter opens the detail. (?) is a pointer shortcut
// for the same thing and not a tab stop: a button inside an option is invalid.
import { el } from '../core/dom.js';
import { icon } from '../core/icons.js';
import { displayOrder, pointsLost, step } from './checkpoints.js';

function where(result) {
    return [result.target_device, result.target_interface].filter(Boolean).join(' ');
}

export function createCheckpointList(host, { onSelect, onOpen }) {
    const box = el('ul', {
        className: 'cp-list', role: 'listbox', tabindex: '0', 'aria-labelledby': 'lr-missed-heading',
    });
    host.appendChild(box);
    let order = [];
    let selectedId = null;

    box.addEventListener('keydown', (e) => {
        let next = null;
        if (e.key === 'ArrowDown') next = step(order, selectedId, 1);
        else if (e.key === 'ArrowUp') next = step(order, selectedId, -1);
        else if (e.key === 'Home') next = order[0];
        else if (e.key === 'End') next = order[order.length - 1];
        else if (e.key === 'Enter') { e.preventDefault(); onOpen(); return; }
        else return;
        e.preventDefault();
        if (next) onSelect(next.rule_id, { push: false });
    });

    function helpButton(result) {
        const help = el('span', { className: 'cp-help', 'aria-hidden': 'true', title: 'Explain this checkpoint' }, [icon('info')]);
        help.addEventListener('click', (e) => {
            e.stopPropagation();
            onSelect(result.rule_id, { push: true });
            onOpen();
        });
        return help;
    }

    function row(result, index) {
        const option = el('li', {
            className: 'cp-row', role: 'option', id: `cp-option-${index}`,
            'aria-selected': String(result.rule_id === selectedId),
        }, [
            el('span', { className: 'cp-loc', text: where(result) }),
            el('span', { className: 'cp-desc', text: result.description }),
            // null, not undefined: a report from an older build has no such field.
            result.matched_device === null ? el('span', { className: 'cp-missing', text: 'Not found in your file' }) : null,
            el('span', { className: 'cp-pts', text: `-${pointsLost(result).toFixed(1)}` }),
            helpButton(result),
        ]);
        option.addEventListener('click', () => onSelect(result.rule_id, { push: true }));
        return option;
    }

    return {
        render({ groups, selectedId: id }) {
            selectedId = id;
            order = displayOrder(groups);
            box.textContent = '';
            let index = 0;
            groups.forEach((group, g) => {
                const labelId = `cp-group-${g}`;
                const items = group.items.map(r => row(r, index++));
                box.appendChild(el('li', { role: 'presentation', className: 'cp-group' }, [
                    el('div', { className: 'cp-group-label', id: labelId, text: group.label }),
                    el('ul', { role: 'group', 'aria-labelledby': labelId }, items),
                ]));
            });
            const current = order.findIndex(r => r.rule_id === selectedId);
            if (current >= 0) {
                box.setAttribute('aria-activedescendant', `cp-option-${current}`);
                const node = box.querySelector(`#cp-option-${current}`);
                if (node && node.scrollIntoView) node.scrollIntoView({ block: 'nearest' });
            } else {
                box.removeAttribute('aria-activedescendant');
            }
        },
        focus() { box.focus(); },
    };
}
```

- [ ] **Step 6: Create `static/js/report/checkpoint-detail.js`**

```js
// static/js/report/checkpoint-detail.js
// The selected checkpoint (spec 5.3): Expected, Found, Points lost, Why it
// matters, Check with, and Ask about this when the local model is available.
// Every value is set as text. Esc hands focus back to the list.
import { el } from '../core/dom.js';
import { icon } from '../core/icons.js';
import { pointsLost } from './checkpoints.js';

export function createCheckpointDetail(host, { onAsk, onBack }) {
    let current = null;
    let askAvailable = false;

    host.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') { e.preventDefault(); onBack(); }
    });

    function field(label, value, className) {
        if (value == null || value === '') return [];
        return [el('dt', { text: label }), el('dd', { className: className || null, text: value })];
    }

    function render() {
        host.textContent = '';
        if (!current) { host.hidden = true; return; }
        host.hidden = false;
        const r = current;
        const where = [r.target_device, r.target_interface].filter(Boolean).join(' ');
        const peer = r.peer_device ? [r.peer_device, r.peer_interface].filter(Boolean).join(' ') : '';
        const found = r.matched_device === null
            ? r.target_device + ' was not found in your file'
            : r.actual_value;

        host.appendChild(el('h2', { className: 'cpd-title', text: r.description }));
        host.appendChild(el('p', { className: 'cpd-where', text: peer ? where + ' to ' + peer : where }));
        host.appendChild(el('dl', { className: 'cpd-fields' }, [
            ...field('Expected', r.expected_text),
            ...field('Found', found, 'cpd-found'),
            ...field('Points lost', `${pointsLost(r).toFixed(1)} of ${Number(r.points_possible).toFixed(1)}`),
            ...field('Why it matters', r.guidance),
        ]));

        const commands = r.verify_commands || [];
        if (commands.length) {
            host.appendChild(el('div', { className: 'cpd-commands' }, [
                el('span', { className: 'cpd-label', text: 'Check with' }),
                ...commands.map(c => el('code', { className: 'cmd-chip', text: c })),
            ]));
        }
        if (askAvailable) {
            const ask = el('button', { type: 'button', className: 'btn btn-sm btn-outline cpd-ask' }, [icon('ai'), ' Ask about this']);
            ask.addEventListener('click', () => onAsk(r));
            host.appendChild(ask);
        }
    }

    return {
        show(result) { current = result; render(); },
        clear() { current = null; render(); },
        setAskAvailable(available) { askAvailable = !!available; render(); },
        focus() { if (!host.hidden) host.focus(); },
    };
}
```

- [ ] **Step 7: Create `static/js/report/linked-report.js`**

```js
// static/js/report/linked-report.js
// The linked report (spec 5): missed checkpoints in the list column, the
// student's topology on the map, the selected checkpoint under it. Exactly one
// checkpoint is selected while any are missed; the map follows the selection.
import { el } from '../core/dom.js';
import { icon } from '../core/icons.js';
import { buildLossBar } from './loss-bar.js';
import { createCheckpointList } from './checkpoint-list.js';
import { createCheckpointDetail } from './checkpoint-detail.js';
import {
    missedOf, groupMissed, displayOrder, badgesFor, focusFor, resolveSelection, missedOnDevice,
} from './checkpoints.js';

export function createLinkedReport({ listHost, detailHost, map, onSelectionChange = () => {}, onAsk = () => {} }) {
    let report = null;
    let missed = [];
    let groupBy = 'device';
    let deviceFilter = null;
    let selectedId = null;

    const listSlot = el('div', { className: 'lr-list-slot' });
    const detail = createCheckpointDetail(detailHost, {
        onAsk: result => onAsk(result),
        onBack: () => list.focus(),
    });
    const list = createCheckpointList(listSlot, {
        onSelect: (id, { push }) => select(id, { push }),
        onOpen: () => detail.focus(),
    });

    const visible = () => (deviceFilter ? missedOnDevice(missed, deviceFilter) : missed);
    const groups = () => groupMissed(visible(), groupBy);
    const selected = () => missed.find(r => r.rule_id === selectedId) || null;

    function applyFocus() {
        if (report) map.setFocus(focusFor(selected(), badgesFor(missed)));
    }

    function select(id, { push = false, notify = true } = {}) {
        if (!report) return;
        const target = resolveSelection(displayOrder(groups()), id);
        selectedId = target ? target.rule_id : null;
        list.render({ groups: groups(), selectedId });
        if (target) detail.show(target); else detail.clear();
        applyFocus();
        if (notify && selectedId) onSelectionChange(selectedId, { push });
    }

    function scoreHeader() {
        return el('header', { className: 'lr-score' }, [
            el('span', { className: 'lr-score-pct', text: `${report.percentage}%` }),
            el('span', { className: 'lr-score-pts', text: `${Number(report.total_score).toFixed(1)} / ${Number(report.max_score).toFixed(1)}` }),
            el('span', { className: 'lr-grade', text: report.grade_letter }),
            el('p', { className: 'lr-lab', text: report.lab_title }),
        ]);
    }

    function toolbar() {
        const bar = el('div', { className: 'lr-toolbar' }, [
            el('h3', { className: 'report-subhead', id: 'lr-missed-heading', text: `Missed checkpoints (${visible().length})` }),
        ]);
        const toggle = el('div', { className: 'lr-group-toggle', role: 'group', 'aria-label': 'Group missed checkpoints by' });
        [['device', 'Device'], ['topic', 'Topic']].forEach(([key, label]) => {
            const b = el('button', { type: 'button', className: 'btn btn-sm toggle-btn', 'aria-pressed': String(groupBy === key), text: label });
            b.addEventListener('click', () => { groupBy = key; renderList(); select(selectedId); });
            toggle.appendChild(b);
        });
        bar.appendChild(toggle);
        if (deviceFilter) {
            const chip = el('button', { type: 'button', className: 'lr-filter-chip' }, [
                'Showing ' + deviceFilter + ' only. ', el('strong', { text: 'Show all' }),
            ]);
            chip.addEventListener('click', () => { deviceFilter = null; renderList(); select(selectedId); list.focus(); });
            bar.appendChild(chip);
        }
        return bar;
    }

    function passedDisclosure(passed) {
        const n = passed.length;
        return el('details', { className: 'lr-passed' }, [
            el('summary', { text: `${n} checkpoint${n === 1 ? '' : 's'} passed` }),
            el('ul', {}, passed.map(r => el('li', {}, [icon('check'), el('span', { text: r.description })]))),
        ]);
    }

    function renderList() {
        listHost.textContent = '';
        listHost.appendChild(scoreHeader());
        const loss = buildLossBar(report.study_topics);
        if (loss) listHost.appendChild(loss);
        if (!missed.length) {
            listHost.appendChild(el('p', { className: 'lr-all-passed' }, [
                icon('check'), ` All ${report.results.length} checkpoints passed`,
            ]));
            return;
        }
        listHost.appendChild(toolbar());
        listHost.appendChild(listSlot);
        const passed = report.results.filter(r => r.passed);
        if (passed.length) listHost.appendChild(passedDisclosure(passed));
    }

    return {
        show(next, { selectedId: wanted = null } = {}) {
            report = next;
            missed = missedOf(next);
            deviceFilter = null;
            selectedId = null;
            renderList();
            if (missed.length) {
                select(wanted);
            } else {
                detail.clear();
                applyFocus();
            }
        },
        select,
        // Activating a device on the map: filter to it and select its first
        // missed checkpoint. False when it has none, so the caller can fall
        // back to the device inspector.
        showDevice(hostname) {
            if (!report || !missedOnDevice(missed, hostname).length) return false;
            deviceFilter = hostname;
            renderList();
            select(null, { push: true });
            list.focus();
            return true;
        },
        clear() {
            report = null;
            missed = [];
            selectedId = null;
            deviceFilter = null;
            listHost.textContent = '';
            detail.clear();
        },
        applyFocus,
        setAskAvailable: available => detail.setAskAvailable(available),
        getSelectedId: () => selectedId,
        focusList: () => list.focus(),
    };
}
```

- [ ] **Step 8: Append the report styles to `static/css/components/report.css`**

```css
/* --- List column --- */
.lr-score { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.25rem 0.75rem; }
.lr-score-pct { font-family: var(--font-mono); font-size: var(--text-2xl); font-weight: 700; color: var(--text); }
.lr-score-pts { font-family: var(--font-mono); font-size: var(--text-sm); color: var(--text-muted); }
.lr-grade {
    font-family: var(--font-mono); font-size: var(--text-sm); font-weight: 700;
    padding: 0.125rem 0.5rem; border: 1px solid var(--line-strong); border-radius: var(--radius-sm);
}
.lr-lab { flex-basis: 100%; margin: 0; font-size: var(--text-sm); color: var(--text-muted); }

.report-subhead {
    margin: 1rem 0 0.5rem; font-size: var(--text-xs); font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-muted);
}

.loss-bar { display: flex; height: 0.5rem; overflow: hidden; border-radius: 999px; background: var(--line); }
.loss-seg { height: 100%; }
.loss-shade-1 { background: var(--status-bad); }
.loss-shade-2 { background: var(--status-bad); opacity: 0.8; }
.loss-shade-3 { background: var(--status-bad); opacity: 0.62; }
.loss-shade-4 { background: var(--status-bad); opacity: 0.46; }
.loss-shade-5 { background: var(--status-bad); opacity: 0.32; }
.loss-legend { list-style: none; margin: 0.5rem 0 0; padding: 0; display: grid; gap: 0.25rem; font-size: var(--text-sm); }
.loss-legend li { display: flex; align-items: center; gap: 0.5rem; }
.loss-swatch { width: 0.625rem; height: 0.625rem; border-radius: 2px; flex: none; }
.loss-topic { flex: 1; min-width: 0; }
.loss-points { font-family: var(--font-mono); color: var(--status-bad); }

.lr-toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; justify-content: space-between; }
.lr-toolbar .report-subhead { margin-bottom: 0; }
.lr-group-toggle { display: flex; gap: 0.25rem; }
.lr-group-toggle [aria-pressed="true"] { background: var(--tint-accent-mid); border-color: var(--accent); color: var(--text); }
.lr-filter-chip {
    flex-basis: 100%; text-align: left; padding: 0.375rem 0.5rem; font: inherit; font-size: var(--text-sm);
    color: var(--text); background: var(--tint-neutral-mid); border: 1px solid var(--line); border-radius: var(--radius-sm); cursor: pointer;
}

.cp-list { list-style: none; margin: 0.5rem 0 0; padding: 0; border: 1px solid var(--line); border-radius: var(--radius-md); }
.cp-list:focus-visible { outline: 2px solid var(--focus-ring); outline-offset: 2px; }
:root[data-contrast="high"] .cp-list:focus-visible { outline-width: 3px; }
.cp-group ul { list-style: none; margin: 0; padding: 0; }
.cp-group-label {
    padding: 0.375rem 0.75rem; font-family: var(--font-mono); font-size: var(--text-xs); font-weight: 600;
    color: var(--text-muted); background: var(--surface-sunken); border-bottom: 1px solid var(--line);
}
.cp-row {
    display: grid; grid-template-columns: 1fr auto auto; gap: 0.125rem 0.5rem; align-items: start;
    padding: 0.5rem 0.75rem; border-bottom: 1px solid var(--line); border-left: 3px solid transparent; cursor: pointer;
}
.cp-row:hover { background: var(--tint-neutral-weak); }
.cp-row[aria-selected="true"] { background: var(--tint-bad-mid); border-left-color: var(--status-bad); }
.cp-loc { grid-column: 1; font-family: var(--font-mono); font-size: var(--text-xs); color: var(--text-muted); }
.cp-desc { grid-column: 1; font-size: var(--text-sm); color: var(--text); }
.cp-missing { grid-column: 1; font-size: var(--text-xs); color: var(--status-warn); }
.cp-pts { grid-column: 2; grid-row: 1 / span 2; font-family: var(--font-mono); font-size: var(--text-sm); color: var(--status-bad); }
.cp-help { grid-column: 3; grid-row: 1 / span 2; color: var(--text-muted); display: inline-flex; padding: 0.125rem; }
.cp-help:hover { color: var(--text); }

.lr-all-passed { display: flex; align-items: center; gap: 0.5rem; margin: 1rem 0; color: var(--status-ok); font-weight: 600; }
.lr-passed { margin-top: 0.75rem; font-size: var(--text-sm); }
.lr-passed summary { cursor: pointer; color: var(--text-muted); }
.lr-passed ul { list-style: none; margin: 0.5rem 0 0; padding: 0; display: grid; gap: 0.25rem; }
.lr-passed li { display: flex; gap: 0.5rem; align-items: flex-start; }
.lr-passed .icon { color: var(--status-ok); flex: none; }

/* --- Detail under the map (Grading screen only) --- */
:root:not([data-screen="grading"]) .checkpoint-detail { display: none; }
.checkpoint-detail[hidden] { display: none; }
.checkpoint-detail {
    flex: none; max-height: 40%; overflow: auto;
    padding: 0.75rem 1rem; border-top: 1px solid var(--line); background: var(--surface); color: var(--text);
}
.checkpoint-detail:focus-visible { outline: 2px solid var(--focus-ring); outline-offset: -2px; }
.cpd-title { margin: 0; font-size: var(--text-base); font-weight: 600; }
.cpd-where { margin: 0.125rem 0 0.5rem; font-family: var(--font-mono); font-size: var(--text-xs); color: var(--text-muted); }
.cpd-fields { display: grid; grid-template-columns: max-content 1fr; gap: 0.375rem 1rem; margin: 0; font-size: var(--text-sm); }
.cpd-fields dt { color: var(--text-muted); font-weight: 600; }
.cpd-fields dd { margin: 0; }
.cpd-found { font-family: var(--font-mono); }
.cpd-commands { display: flex; flex-wrap: wrap; align-items: center; gap: 0.375rem; margin-top: 0.75rem; }
.cpd-label { font-size: var(--text-sm); color: var(--text-muted); font-weight: 600; margin-right: 0.25rem; }
.cmd-chip {
    font-family: var(--font-mono); font-size: var(--text-xs); padding: 0.125rem 0.375rem;
    background: var(--tint-neutral-mid); border: 1px solid var(--line); border-radius: var(--radius-sm);
}
.cpd-ask { margin-top: 0.75rem; }
```

- [ ] **Step 9: Add context-bar action styles to `static/css/layouts/shell.css`**

After the `.context-title` rule, add:

```css
.context-actions { display: flex; align-items: center; gap: 0.5rem; margin-left: auto; min-width: 0; }
.context-actions[hidden], .context-actions [hidden] { display: none; }
.file-chips { display: flex; gap: 0.375rem; list-style: none; margin: 0; padding: 0; min-width: 0; overflow: hidden; }
.file-chip {
    max-width: 14rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    padding: 0.125rem 0.5rem; font-family: var(--font-mono); font-size: var(--text-xs);
    color: var(--text-muted); background: var(--tint-neutral-mid); border: 1px solid var(--line); border-radius: var(--radius-sm);
}
```

- [ ] **Step 10: Run the static checks that do not depend on app.js**

Run: `python -m pytest tests/test_linked_report_markup.py tests/test_styles.py tests/test_frontend_escaping.py tests/test_no_emoji.py tests/test_icons.py -q` and `node --test tests/js/*.test.mjs`
Expected: PASS. `tests/test_frontend_modules.py` still fails on the removed ids; Task 7 fixes that. Do not commit yet.

---

### Task 7: Wire the Grading screen, persistence and history

**Files:**
- Modify: `static/js/legacy/app.js`
- Modify: `docs/SYSTEM.md`

**Interfaces:**
- Consumes: `createLinkedReport` (Task 6), `saveSession`, `loadSession`, `clearSession`, `parseHash`, `formatHash` (Task 3), `map.setFocus` (Task 5).
- Produces: `document.documentElement.dataset.screen` set to `discovery` | `instructor` | `grading` by `switchMode`, which the detail panel's CSS reads. URL hash `#<screen>` or `#grading/<rule_id>`. Session keys `netgrader:grading` (`{ report, rubricName, fileNames }`), `netgrader:selection`, `netgrader:screen`.

- [ ] **Step 1: Imports, constants and new elements**

Add to the imports at the top of `static/js/legacy/app.js`:

```js
import { createLinkedReport } from '../report/linked-report.js';
import { saveSession, loadSession, clearSession, parseHash, formatHash } from '../core/store.js';
```

Above `export function initLegacyApp() {`, add:

```js
// Hash and storage names for each legacy mode (spec 8.2).
const SCREEN_OF_MODE = { visualizer: 'discovery', teacher: 'instructor', student: 'grading' };
const MODE_OF_SCREEN = { discovery: 'visualizer', instructor: 'teacher', grading: 'student' };
```

In the `// --- Mode 3: Student Portal Elements ---` block, delete these constants: `reportGradeLetter`, `reportEarnedScore`, `reportMaxScore`, `reportProgressFill`, `reportPassedTag`, `reportFailedTag`, `filterCountAll`, `filterCountFailed`, `filterCountPassed`, `reportResultsList`, `filterChips`. Add:

```js
    const gradingSteps = document.querySelectorAll('#panel-mode-student .student-step-card');
    const contextActions = document.getElementById('context-actions');
    const contextFileChips = document.getElementById('context-file-chips');
    const gradeAgainBtn = document.getElementById('grade-again-btn');
    const clearReportBtn = document.getElementById('clear-report-btn');
```

In `// State Variables`, add:

```js
    let gradingReport = null;          // the report on the Grading screen
    let gradingFiles = { rubric: '', files: [] };
    let gradingInProgress = false;
    let reportChatBox = null;
```

- [ ] **Step 2: Create the linked report and route map clicks**

Replace the `createTopologyMap` call with:

```js
    // Function declarations below are hoisted, so the drawers exist already.
    // On the Grading screen a device with missed checkpoints opens them in the
    // linked report; anything else opens the inspector as before.
    const map = createTopologyMap(svg, {
        onNodeSelect: dev => {
            if (currentMode === 'student' && linkedReport.showDevice(dev.hostname)) return;
            openNodeDiagnosticDrawer(dev);
        },
        onLinkSelect: link => openEdgeDiagnosticDrawer(link),
    });

    const linkedReport = createLinkedReport({
        listHost: document.getElementById('linked-report-list'),
        detailHost: document.getElementById('checkpoint-detail'),
        map,
        onSelectionChange: (id, { push }) => {
            saveSession('selection', id);
            if (currentMode === 'student') writeHistory(push ? 'push' : 'replace');
        },
        onAsk: result => askAboutCheckpoint(result),
    });
```

- [ ] **Step 3: Screen changes write the hash**

Replace the whole `switchMode` function (from `function switchMode(mode) {` to its closing brace, just before `modeTabs.forEach(tab => {`) with:

```js
    // history: 'push' (a user's navigation), 'replace' (restoring), 'none' (Back/Forward).
    function switchMode(mode, { history: historyMode = 'push' } = {}) {
        if (!modePanels[mode]) return;      // e.g. #instructor on a lab PC
        currentMode = mode;
        modeTabs.forEach(t => t.classList.toggle('active', t.getAttribute('data-mode') === mode));
        modeTabs.forEach(t => t.setAttribute('aria-current', t.getAttribute('data-mode') === mode ? 'page' : 'false'));
        const titles = { visualizer: 'Topology Discovery', teacher: 'Instructor Studio', student: 'Student Grading' };
        if (contextTitle) contextTitle.textContent = titles[mode] || '';

        Object.entries(modePanels).forEach(([mKey, panel]) => {
            if (panel) panel.classList.toggle('active', mKey === mode);
        });

        if (mode === 'visualizer') {
            if (canvasMainTitle) canvasMainTitle.textContent = 'Topology Discovery';
        } else if (mode === 'teacher') {
            if (canvasMainTitle) canvasMainTitle.textContent = 'Reference Topology Studio';
        } else if (mode === 'student') {
            if (canvasMainTitle) canvasMainTitle.textContent = 'Student Evaluation View';
        }
        if (pendingOperations === 0) applyEmptyStateText(mode);

        document.documentElement.dataset.screen = SCREEN_OF_MODE[mode];
        saveSession('screen', SCREEN_OF_MODE[mode]);
        // Other screens draw their own topology on the shared map; bring the
        // student's back, with its highlight.
        if (mode === 'student' && gradingReport && map.getTopology() !== gradingReport.topology) {
            renderTopology(gradingReport.topology);
            linkedReport.applyFocus();
        }
        syncContextActions();
        writeHistory(historyMode);
    }

    function writeHistory(kind) {
        if (kind === 'none') return;
        const selection = currentMode === 'student' ? linkedReport.getSelectedId() : null;
        const hash = formatHash(SCREEN_OF_MODE[currentMode], selection);
        if (location.hash === hash) return;
        try {
            if (kind === 'push') history.pushState(null, '', hash);
            else history.replaceState(null, '', hash);
        } catch (e) {
            // A sandboxed frame can refuse; the hash is a convenience.
        }
    }
```

The tab click listener keeps calling `switchMode(mode)`, which defaults to `'push'`. `pendingOperations` is declared later with `let`, but `switchMode` only runs after initialisation finishes, as before.

- [ ] **Step 4: Replace the scorecard rendering**

Delete these functions entirely: `renderEvaluationReport`, `renderStudyTopics`, `renderFilteredResults`. Delete the `filterChips.forEach(...)` listener block. Keep `buildRuleResultCard`, because Batch review still uses it until PR 4.

Replace the body of the `studentEvaluateBtn` click listener with a call to a shared function, and add Grade again:

```js
    async function gradeSubmission() {
        if (!studentInstructionsFile) {
            alert("Step 1: Please upload the instructor's instructions.txt first.");
            return;
        }
        if (studentSubmissionFiles.length === 0) {
            alert("Step 2: Please upload your student submission (.pkt, .xml, or config files).");
            return;
        }

        const formData = new FormData();
        formData.append('instructions_file', studentInstructionsFile);
        studentSubmissionFiles.forEach(f => formData.append('student_files', f));

        gradingInProgress = true;
        try {
            showLoading("Grading submission and evaluating relational topology rules...");
            const res = await fetch('/api/evaluate', { method: 'POST', body: formData });
            if (!res.ok) {
                throw new Error(await describeFailure(res, `Evaluation failed with status ${res.status}`));
            }
            const report = await res.json();
            showGradingReport(report, {
                rubricName: studentInstructionsFile.name,
                fileNames: studentSubmissionFiles.map(f => f.name),
                selectedId: linkedReport.getSelectedId(),
            });
            showToast(`Grading Complete: Score ${report.percentage}% (${report.grade_letter})`);
        } catch (err) {
            showPanelMessage(`<div class="empty-icon">${iconMarkup('alert')}</div><h3>Grading Failed</h3>`
                + `<p class="empty-error">${escapeHtml(err.message)}</p>`);
            alert(`Evaluation Error: ${err.message}`);
        } finally {
            gradingInProgress = false;
            hideLoading();
        }
    }

    if (studentEvaluateBtn) studentEvaluateBtn.addEventListener('click', gradeSubmission);
    if (gradeAgainBtn) gradeAgainBtn.addEventListener('click', gradeSubmission);
```

Add the report functions after it:

```js
    // Shows a report on the Grading screen: the linked report in the list
    // column, the topology on the map, file chips in the context bar. The
    // upload steps collapse; Clear brings them back.
    function showGradingReport(report, { rubricName = '', fileNames = [], selectedId = null, persist = true } = {}) {
        gradingReport = report;
        latestEvaluationReport = report;
        gradingFiles = { rubric: rubricName, files: fileNames };
        if (studentReportCard) studentReportCard.style.display = 'block';
        gradingSteps.forEach(card => { card.style.display = 'none'; });
        if (report.topology) renderTopology(report.topology);
        linkedReport.show(report, { selectedId });
        renderFileChips();
        syncContextActions();
        // Fired only after the score is rendered. If it never returns, the
        // student still has a complete, final grade on screen.
        requestNarrative(report);
        reportChatBox = openReportChat(report);
        if (persist && !saveSession('grading', { report, rubricName, fileNames })) {
            showToast('This report is too large to keep after a refresh. Download it to keep a copy.', 5000);
        }
    }

    function clearGradingReport() {
        gradingReport = null;
        latestEvaluationReport = null;
        reportChatBox = null;
        gradingFiles = { rubric: '', files: [] };
        clearSession('grading');
        clearSession('selection');
        linkedReport.clear();
        if (studentReportCard) studentReportCard.style.display = 'none';
        gradingSteps.forEach(card => { card.style.display = ''; });
        renderFileChips();
        syncContextActions();
        if (currentMode === 'student') writeHistory('replace');
    }

    function renderFileChips() {
        if (!contextFileChips) return;
        contextFileChips.textContent = '';
        [gradingFiles.rubric].concat(gradingFiles.files).filter(Boolean).forEach(fileName => {
            const li = document.createElement('li');
            li.className = 'file-chip';
            li.textContent = fileName;
            li.title = fileName;
            contextFileChips.appendChild(li);
        });
    }

    // Grade again needs the uploaded files, which a refresh does not keep.
    function syncContextActions() {
        if (contextActions) contextActions.hidden = !(currentMode === 'student' && gradingReport);
        if (gradeAgainBtn) gradeAgainBtn.hidden = !(studentInstructionsFile && studentSubmissionFiles.length);
    }

    if (clearReportBtn) {
        clearReportBtn.addEventListener('click', () => {
            clearGradingReport();
            map.reset();
            if (emptyState) emptyState.style.display = 'block';
            showToast('Report cleared.');
        });
    }

    // The question goes to the chat as plain text; the chat log sets
    // textContent, so a device name in the description stays text.
    function askAboutCheckpoint(result) {
        if (!reportChatBox || !reportChatBox.available) return;
        const host = document.getElementById('report-chat');
        if (host && host.scrollIntoView) host.scrollIntoView({ block: 'nearest' });
        reportChatBox.ask('Explain this checkpoint I missed: "' + result.description + '". What was found: '
            + (result.actual_value || 'nothing') + '.');
    }
```

In the `studentSubClearBtn` listener and in `handleStudentSubFiles`, call `syncContextActions();` at the end so Grade again tracks the files. In `handleStudentInstFile`, after `studentInstructionsFile = file;`, add `syncContextActions();`.

In the `resetBtn` listener, delete the line `latestEvaluationReport = null;` (`clearGradingReport` does it) and replace `if (studentReportCard) studentReportCard.style.display = 'none';` with `clearGradingReport();`. Keep the rest of that listener, including `map.reset()`.

- [ ] **Step 5: Let the chat box report availability and accept questions**

In `createChatBox`, change the signature to `function createChatBox(host, { title, suggestions, endpoint, buildPayload, readyNote, onAvailability })`. In the returned `box` object, add `ask,` and `get available() { return available; },` and at the end of `setAvailability`, after `syncControls();`, add:

```js
                if (onAvailability) onAvailability(available);
```

In `openReportChat`, change `createChatBox(host, {` to `return createChatBox(host, {`, add `onAvailability: available => linkedReport.setAskAvailable(available),` to its options, and change the early return to `if (!host) return null;`.

- [ ] **Step 6: Restore on load, Back/Forward, and the leave-page warning**

At the very end of `initLegacyApp` (before its closing `}`), add:

```js
    // --- Keeping results across a refresh (issue #29, spec 8.2) ---
    document.documentElement.dataset.screen = SCREEN_OF_MODE[currentMode];
    const hashState = parseHash(location.hash);
    const stored = loadSession('grading');
    if (stored && stored.report && Array.isArray(stored.report.results)) {
        showGradingReport(stored.report, {
            rubricName: stored.rubricName || '',
            fileNames: Array.isArray(stored.fileNames) ? stored.fileNames : [],
            selectedId: hashState.selection || loadSession('selection'),
            persist: false,
        });
    }
    const startScreen = hashState.screen || loadSession('screen');
    if (startScreen && MODE_OF_SCREEN[startScreen]) {
        switchMode(MODE_OF_SCREEN[startScreen], { history: 'replace' });
    }

    window.addEventListener('popstate', () => {
        const state = parseHash(location.hash);
        if (state.screen && MODE_OF_SCREEN[state.screen]) switchMode(MODE_OF_SCREEN[state.screen], { history: 'none' });
        if (state.screen === 'grading' && gradingReport) linkedReport.select(state.selection, { notify: false });
    });

    // Only while a grade is being computed: leaving then loses the request.
    window.addEventListener('beforeunload', (e) => {
        if (!gradingInProgress) return;
        e.preventDefault();
        e.returnValue = '';
    });
```

- [ ] **Step 7: Update `docs/SYSTEM.md`**

In section 9 ("Interfaces", subsection "Screens"), replace the Grading screen's description with:

```markdown
**Grading.** Before grading, the list column holds the two upload steps. Afterwards they collapse: the context bar shows the graded files with **Grade again** and **Clear**, and the list column shows the score, points lost by topic, and the missed checkpoints, grouped by device or by topic. Passed checkpoints sit in a collapsed "N checkpoints passed". Selecting a missed checkpoint (click, arrow keys, or a device on the map) rings it on the map. A link-scoped check highlights the link and both ends, and everything else dims. Its detail appears under the map: Expected, Found, Points lost, Why it matters, the `show` commands to check with, and **Ask about this** when the local model is running. The report, the selected checkpoint and the screen are kept in `sessionStorage` and in the URL hash (`#grading/<rule id>`), so a refresh restores them and Back/Forward move between them. They are gone when the browser closes.
```

In section 6 ("Feedback"), add a paragraph:

```markdown
Each checkpoint also carries presentational fields for the linked report, filled after scoring: `expected_text` (the rubric's expectation in words, from `src/report_fields.py`), `matched_device` (the student's device the rubric name resolved to), `peer_device` and `peer_interface` (the other end of a cabling, link-agreement or relational-subnet check), `verify_commands` (the `show` commands from `feedback.py`, as data) and `topic` (the study-topic label). None of them is read by scoring; `python -m validation` is unchanged.
```

In the module map (section 2), add rows for `src/report_fields.py`, `static/js/core/store.js`, `static/js/map/highlight.js` and `static/js/report/`, each with the one-line responsibility from this plan's File Structure table.

- [ ] **Step 8: Run everything**

Run: `node --check static/js/legacy/app.js`, then `python -m pytest -q`, then `python -m validation`
Expected: all pass; validation reports 100%.

- [ ] **Step 9: Walk through it in the browser**

Start the `neteval` preview. Using the built-in browser tools:

1. Grading screen: upload a rubric generated from `tests/fixtures/sample_topology.xml` (Instructor Studio → generate → download, or `/api/criteria/generate` on the instructor PC). Then upload a copy of the same file with one link changed to `eStraightThrough` where the rubric expects `eCrossOver`, and grade.
2. Confirm: the upload steps collapse; the context bar shows both file names, Grade again and Clear. The list shows the score, the loss bar and the missed checkpoint(s) grouped by device. The first missed checkpoint is selected and the hash reads `#grading/<id>`. The map shows a count badge, the link and both ends highlighted, and the rest dimmed. The detail under the map shows Expected (with "(crossover)"), Found, Points lost, Why it matters and the `show cdp neighbors` chip.
3. Keyboard: Tab to the list, press ArrowDown and ArrowUp. The selection, map and hash follow. Enter moves focus to the detail and Esc returns to the list.
4. Click a device badge on the map. The list filters to that device and shows the "Show all" chip. Click a device with no missed checkpoints and the inspector drawer opens as before.
5. Switch to Topology Discovery. The detail disappears. Press Back: the Grading screen returns with the same selection.
6. Reload the page. The report, selection and map highlight are restored, and Grade again is hidden (the files are gone). Click Clear: the upload steps return and the hash is `#grading`. Reload again: nothing is restored.
7. Load `/#instructor` from a non-loopback client (or check that `switchMode` ignores a missing panel). The page stays on Discovery with no console error.
8. Grade a submission that passes everything. The list shows "All N checkpoints passed" and no detail panel.
9. Check `read_console_messages` for errors. Take a screenshot of step 2 for the PR description.

Fix anything that fails, re-run Step 8, and repeat the failed step.

- [ ] **Step 10: Commit Tasks 6 and 7 together**

```bash
git add static/js/report/ static/js/legacy/app.js static/css/components/report.css static/css/layouts/shell.css templates/partials/panel_grading.html templates/partials/visualizer.html templates/partials/context_bar.html tests/test_linked_report_markup.py docs/SYSTEM.md
git commit -m "feat(grading): linked report with map highlight and kept results" -m "Missed checkpoints are listed first, grouped by device or topic, with passed ones collapsed (#23). Selecting one highlights it on the student's map and shows what was expected, what was found and how to check it under the map. The report, selection and screen survive a refresh and follow Back/Forward (#29). Built with el(); nothing from a file reaches innerHTML." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Self-Review Notes

- **Spec coverage.**
  - 5.1 score header, loss bar, grouped missed list and passed disclosure: Task 6.
  - 5.2 selection by click, arrows, map device and hash: Tasks 6 and 7.
  - 5.3 badges, ring, link highlight, dimming and the detail fields: Tasks 5 and 6. "Ask about this" is Task 7, Step 5.
  - 5.4 edge cases: missing device (Tasks 2, 4, 6), all passed (Task 6), no AI (Task 7, Step 5), checkpoint with no device on the map (`focusFor` with no `matched_device`, Task 4).
  - 5.5 fields: Tasks 1 and 2.
  - 8.2 persistence, hash, Back/Forward, leave-page warning and Clear: Tasks 3 and 7. Batch persistence belongs to PR 4, with Batch Review.
  - 9.1 static checks: Tasks 3 and 5. 9.2 backend tests and validation: Tasks 1 and 2.
  - 9.3 Playwright and axe: PR 5.
- **Deferred to PR 5:** responsive tiers (8.1), the live region announcements (7.2), the map's text alternative, and the narrow-layout (?) popover.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-10-01-ui-refresh-pr3-linked-report.md`.
