# Dynamic Rubric & Instructor Policy Toggles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement instructor policy toggles allowing dynamic student-defined subnetting, flexible hostnames, Auto-MDIX cabling tolerance, flexible routing process IDs, and security/documentation grading with 100% deterministic offline evaluation.

**Architecture:** Extend Pydantic models with `EvaluationPolicies`; update IOS/XML parsers to capture security, default gateway, and OSPF parameters; enrich `criteria_generator.py` to support dual-format human/machine instructions with dynamic relational subnet rules; build a mathematical relational subnet and topological graph evaluator in `evaluator.py`; expose policy toggles in FastAPI and author a modern Instructor Policy Control Center in the web interface.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, `ipaddress` standard library, Pytest, Vanilla JS (ES6+), HTML5/CSS3.

## Global Constraints

- All grading logic must remain 100% deterministic, offline, and mathematically verifiable via standard library `ipaddress` arithmetic and graph topology matching (no external AI/LLM API calls during evaluation).
- Existing test suite (`pytest`) must maintain 100% pass rate without regressions.
- The instructions format must preserve backwards-compatibility with existing `--- CRITERIA SPEC START ---` JSON delimiters.
- No third-party UI framework (Vanilla CSS and Vanilla JS only).

---

### Task 1: Policy Schema & Data Model Extensions

**Files:**
- Modify: `src/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Produces: `EvaluationPolicies` class with 9 policy flags.
- Produces: `EvaluationCriteria.policies: EvaluationPolicies`.
- Produces: `ParsedDevice.default_gateway: str | None`, `ParsedDevice.has_enable_secret: bool`, `ParsedDevice.has_password_encryption: bool`, `ParsedDevice.has_vty_login: bool`, `ParsedDevice.ospf_processes: list[dict]`.
- Produces: `EvaluationRule.category` updated to include `"relational_subnet"`, `"security"`, `"documentation"`.

- [ ] **Step 1: Write failing tests in `tests/test_models.py`**

```python
# Add to tests/test_models.py
from src.models import EvaluationPolicies, EvaluationCriteria, EvaluationRule

def test_evaluation_policies_defaults():
    policies = EvaluationPolicies()
    assert policies.allow_dynamic_subnetting is False
    assert policies.enforce_prefix_length is True
    assert policies.verify_default_gateways is True
    assert policies.allow_custom_hostnames is False
    assert policies.strict_port_matching is True
    assert policies.strict_cable_type is True
    assert policies.allow_flexible_process_ids is True
    assert policies.grade_security_baseline is False
    assert policies.grade_interface_descriptions is False

def test_criteria_with_policies_and_new_categories():
    policies = EvaluationPolicies(
        allow_dynamic_subnetting=True,
        grade_security_baseline=True
    )
    rule1 = EvaluationRule(
        rule_id="rel_subnet_r1_r2",
        category="relational_subnet",
        description="Verify mutual /30 point-to-point subnet between R1 and R2",
        points=15.0,
        target_device="R1",
        target_interface="GigabitEthernet0/0",
        expected_value={
            "peer_device": "R2",
            "peer_interface": "GigabitEthernet0/0",
            "expected_prefixlen": 30,
            "link_type": "point_to_point"
        }
    )
    rule2 = EvaluationRule(
        rule_id="sec_r1_secret",
        category="security",
        description="Enable secret password configured on R1",
        points=5.0,
        target_device="R1",
        expected_value={"check_type": "enable_secret"}
    )
    criteria = EvaluationCriteria(
        lab_title="Dynamic Subnetting Lab",
        policies=policies,
        rules=[rule1, rule2]
    )
    assert criteria.policies.allow_dynamic_subnetting is True
    assert criteria.policies.grade_security_baseline is True
    assert len(criteria.rules) == 2
    assert criteria.rules[0].category == "relational_subnet"
    assert criteria.rules[1].category == "security"

def test_parsed_device_security_and_gateway_attributes():
    dev = ParsedDevice(
        hostname="R1",
        canonical_name="R1",
        device_type="router",
        default_gateway="192.168.1.1",
        has_enable_secret=True,
        has_password_encryption=True,
        has_vty_login=True,
        ospf_processes=[{"process_id": 1, "networks": [{"network": "10.0.0.0", "wildcard": "0.0.0.3", "area": 0}]}]
    )
    assert dev.default_gateway == "192.168.1.1"
    assert dev.has_enable_secret is True
    assert dev.has_password_encryption is True
    assert dev.has_vty_login is True
    assert len(dev.ospf_processes) == 1
    assert dev.ospf_processes[0]["process_id"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -k "test_evaluation_policies_defaults or test_criteria_with_policies_and_new_categories or test_parsed_device_security_and_gateway_attributes"`
Expected: FAIL with `ImportError: cannot import name 'EvaluationPolicies' from 'src.models'`

- [ ] **Step 3: Update `src/models.py`**

```python
# src/models.py
from typing import Literal
from pydantic import BaseModel, Field

class InterfaceData(BaseModel):
    name: str
    ip_address: str | None = None
    ipv6_address: str | None = None
    subnet_mask: str | None = None
    cidr: int | None = None
    network_address: str | None = None
    admin_status: str = "up"         # up / administratively down
    line_status: str = "up"          # up / down
    is_switchport: bool = False
    switchport_mode: str | None = None  # access / trunk
    access_vlan: int | None = None
    trunk_allowed_vlans: list[int] = Field(default_factory=list)
    trunk_native_vlan: int = 1
    description: str | None = None
    evidence_lines: dict[str, int] = Field(default_factory=dict)


class CDPNeighbor(BaseModel):
    device_id: str
    local_interface: str
    remote_interface: str
    capabilities: list[str] = Field(default_factory=list)
    remote_ip: str | None = None
    platform: str | None = None
    evidence_line: int | None = None

class RouteEntry(BaseModel):
    network: str
    cidr: int
    protocol: str                    # C, S, O, D, etc.
    next_hop: str | None = None
    outgoing_interface: str | None = None
    metric: int | None = None
    evidence_line: int | None = None

class MACTableEntry(BaseModel):
    vlan: int
    mac_address: str
    entry_type: str                  # DYNAMIC / STATIC
    port: str
    evidence_line: int | None = None

class ParsedDevice(BaseModel):
    hostname: str
    canonical_name: str
    display_name: str = ""
    is_placeholder: bool = False
    placeholder_for_device: str | None = None
    placeholder_for_interface: str | None = None
    device_type: Literal["router", "switch", "l3_switch", "host", "unknown"] = "router"
    raw_filename: str = ""
    x_coord: float | None = None
    y_coord: float | None = None
    default_gateway: str | None = None
    has_enable_secret: bool = False
    has_password_encryption: bool = False
    has_vty_login: bool = False
    ospf_processes: list[dict] = Field(default_factory=list)
    interfaces: dict[str, InterfaceData] = Field(default_factory=dict)
    cdp_neighbors: list[CDPNeighbor] = Field(default_factory=list)
    routes: list[RouteEntry] = Field(default_factory=list)
    mac_table: list[MACTableEntry] = Field(default_factory=list)
    vlans: dict[int, str] = Field(default_factory=dict)

class ContributingSignal(BaseModel):
    signal_type: str
    description: str
    weight: float
    evidence: list[str] = Field(default_factory=list)

class DiscoveredLink(BaseModel):
    source_device: str
    source_interface: str
    target_device: str
    target_interface: str
    confidence: float
    classification: Literal["verified", "inferred", "unverified"]
    cable_type: str | None = None
    signals: list[ContributingSignal] = Field(default_factory=list)
    is_bidirectional: bool = True
    conflicts: list[str] = Field(default_factory=list)


class ConflictIssue(BaseModel):
    severity: Literal["error", "warning", "info"]
    category: str
    title: str
    description: str
    involved_devices: list[str] = Field(default_factory=list)
    involved_interfaces: list[str] = Field(default_factory=list)
    evidence_citations: list[str] = Field(default_factory=list)

class TopologyResult(BaseModel):
    devices: dict[str, ParsedDevice] = Field(default_factory=dict)
    links: list[DiscoveredLink] = Field(default_factory=list)
    conflicts: list[ConflictIssue] = Field(default_factory=list)


# --- Evaluation & Policy Models ---
class EvaluationPolicies(BaseModel):
    # IP & Subnetting Policies
    allow_dynamic_subnetting: bool = False      # If True: verifies mutual subnet matching, CIDR & uniqueness rather than exact IP
    enforce_prefix_length: bool = True          # If True: requires student's custom subnet to match required CIDR (e.g. /30 for P2P, /24 for LAN)
    verify_default_gateways: bool = True        # If True: verifies PCs/Switches have default gateway matching connected router subnet

    # Topology & Hardware Policies
    allow_custom_hostnames: bool = False        # If True: matches devices by type, topological role, and neighbor links
    strict_port_matching: bool = True           # If False: allows equivalent interfaces of same speed class
    strict_cable_type: bool = True              # If False: allows Auto-MDIX copper equivalence (Straight-Through vs Cross-Over)

    # Routing, Security & Documentation Policies
    allow_flexible_process_ids: bool = True     # If True: ignores locally-significant OSPF/EIGRP process IDs; checks Area & networks
    grade_security_baseline: bool = False       # If True: checks 'enable secret', 'service password-encryption', 'line vty'
    grade_interface_descriptions: bool = False  # If True: checks descriptive interface labels matching peer


class EvaluationRule(BaseModel):
    rule_id: str
    category: Literal[
        "device",
        "interface_ip",
        "interface_status",
        "cabling",
        "vlan_trunk",
        "routing",
        "relational_subnet",
        "security",
        "documentation"
    ]
    description: str
    points: float = 10.0
    target_device: str
    target_interface: str | None = None
    expected_value: dict | str | int | float | None = None


class EvaluationCriteria(BaseModel):
    lab_title: str = "Packet Tracer Lab Assignment"
    lab_description: str = ""
    total_points: float = 100.0
    policies: EvaluationPolicies = Field(default_factory=EvaluationPolicies)
    rules: list[EvaluationRule] = Field(default_factory=list)
    reference_summary: dict = Field(default_factory=dict)


class RuleResult(BaseModel):
    rule_id: str
    category: str
    description: str
    points_possible: float
    points_earned: float
    passed: bool
    actual_value: str | None = None
    feedback: str
    target_device: str
    target_interface: str | None = None


class EvaluationReport(BaseModel):
    lab_title: str
    total_score: float
    max_score: float
    percentage: float
    passed_count: int
    failed_count: int
    grade_letter: str
    results: list[RuleResult] = Field(default_factory=list)
    topology: TopologyResult
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py`
Expected: PASS (all tests in `test_models.py` pass).

- [ ] **Step 5: Commit changes**

```bash
git add src/models.py tests/test_models.py
git commit -m "feat(models): add EvaluationPolicies model and extend ParsedDevice and EvaluationRule"
```

---

### Task 2: Advanced Parser Extensions for Security, OSPF & Gateways

**Files:**
- Modify: `src/parsers.py:50-190`
- Modify: `src/pkt_parser.py:165-198`
- Test: `tests/test_parsers.py`

**Interfaces:**
- Consumes: Raw configuration text or Packet Tracer XML element trees.
- Produces: `ParsedDevice.has_enable_secret`, `ParsedDevice.has_password_encryption`, `ParsedDevice.has_vty_login`, `ParsedDevice.ospf_processes`, `ParsedDevice.default_gateway`.

- [ ] **Step 1: Write failing tests in `tests/test_parsers.py`**

```python
# Add to tests/test_parsers.py
from src.parsers import parse_device_bundle

def test_parse_security_and_ospf_from_config():
    raw_config = """
    hostname CoreRouter
    service password-encryption
    enable secret 5 $1$mERr$hx5rVt7rPNoS4wqbXKX7x0
    !
    interface GigabitEthernet0/0
     description Connection_to_Dist1
     ip address 10.0.0.1 255.255.255.252
    !
    router ospf 10
     network 10.0.0.0 0.0.0.3 area 0
     network 192.168.1.0 0.0.0.255 area 0
    !
    line vty 0 4
     login
     password 7 0822455B0A0A
    !
    """
    dev = parse_device_bundle(raw_config, "CoreRouter.txt")
    assert dev.has_enable_secret is True
    assert dev.has_password_encryption is True
    assert dev.has_vty_login is True
    assert dev.interfaces["GigabitEthernet0/0"].description == "Connection_to_Dist1"
    assert len(dev.ospf_processes) == 1
    assert dev.ospf_processes[0]["process_id"] == 10
    assert len(dev.ospf_processes[0]["networks"]) == 2
    assert dev.ospf_processes[0]["networks"][0]["area"] == 0

def test_parse_switch_default_gateway():
    raw_config = """
    hostname SW1
    ip default-gateway 192.168.1.1
    """
    dev = parse_device_bundle(raw_config, "SW1.txt")
    assert dev.default_gateway == "192.168.1.1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_parsers.py -k "test_parse_security_and_ospf_from_config or test_parse_switch_default_gateway"`
Expected: FAIL (`has_enable_secret` is False or `ospf_processes` is empty).

- [ ] **Step 3: Update `src/parsers.py` and `src/pkt_parser.py`**

In `src/parsers.py`:
```python
def parse_running_config(content: str, start_line: int, device: ParsedDevice) -> None:
    lines = content.splitlines()
    current_intf: InterfaceData | None = None
    in_vty_block = False
    current_ospf: dict | None = None
    
    for idx, line in enumerate(lines):
        line_no = start_line + idx
        stripped = line.strip()
        
        # Hostname
        host_match = re.match(r"^hostname\s+([a-zA-Z0-9_\-\.]+)", stripped, re.IGNORECASE)
        if host_match:
            device.hostname = host_match.group(1).strip()
            device.canonical_name = canonical_device_name(device.hostname)
            continue
        
        # Security Baseline
        if re.match(r"^enable\s+(?:secret|password)\b", stripped, re.IGNORECASE):
            device.has_enable_secret = True
            continue

        if re.match(r"^service\s+password-encryption\b", stripped, re.IGNORECASE):
            device.has_password_encryption = True
            continue

        # Default Gateway (Switches / Hosts)
        gw_match = re.match(r"^ip\s+default-gateway\s+([0-9\.]+)", stripped, re.IGNORECASE)
        if gw_match:
            device.default_gateway = gw_match.group(1).strip()
            continue

        # Line VTY Block
        if re.match(r"^line\s+vty\b", stripped, re.IGNORECASE):
            in_vty_block = True
            current_intf = None
            current_ospf = None
            continue
        
        if in_vty_block:
            if re.match(r"^(?:login|password)\b", stripped, re.IGNORECASE):
                device.has_vty_login = True
            elif not line.startswith(" ") and not line.startswith("\t") and stripped.startswith("!"):
                in_vty_block = False
            elif re.match(r"^[a-zA-Z]", stripped) and not stripped.startswith("login") and not stripped.startswith("password"):
                in_vty_block = False

        # Router OSPF Block
        ospf_match = re.match(r"^router\s+ospf\s+(\d+)", stripped, re.IGNORECASE)
        if ospf_match:
            pid = int(ospf_match.group(1))
            current_ospf = {"process_id": pid, "networks": []}
            device.ospf_processes.append(current_ospf)
            current_intf = None
            in_vty_block = False
            continue

        if current_ospf is not None:
            net_match = re.match(r"^network\s+([0-9\.]+)\s+([0-9\.]+)\s+area\s+(\d+)", stripped, re.IGNORECASE)
            if net_match:
                current_ospf["networks"].append({
                    "network": net_match.group(1),
                    "wildcard": net_match.group(2),
                    "area": int(net_match.group(3))
                })
                continue
            elif not line.startswith(" ") and not line.startswith("\t") and stripped.startswith("!"):
                current_ospf = None
            elif re.match(r"^[a-zA-Z]", stripped) and not stripped.startswith("network"):
                current_ospf = None

        # Interface block start
        intf_match = re.match(r"^interface\s+([a-zA-Z0-9_\-\./]+)", stripped, re.IGNORECASE)
        if intf_match:
            raw_intf_name = intf_match.group(1).strip()
            norm_intf_name = normalize_interface_name(raw_intf_name)
            if norm_intf_name not in device.interfaces:
                device.interfaces[norm_intf_name] = InterfaceData(name=norm_intf_name)
            current_intf = device.interfaces[norm_intf_name]
            current_intf.evidence_lines["interface"] = line_no
            in_vty_block = False
            current_ospf = None
            continue
        
        # Exit interface block on ! or other root commands
        if not line.startswith(" ") and not line.startswith("\t") and stripped.startswith("!"):
            current_intf = None
            continue
        
        # Static routes from config
        route_match = re.match(r"^ip\s+route\s+([0-9\.]+)\s+([0-9\.]+)\s+([0-9\.]+|[a-zA-Z0-9_\-\.\/]+)", stripped, re.IGNORECASE)
        if route_match:
            net, mask, nh = route_match.group(1), route_match.group(2), route_match.group(3)
            try:
                net_obj = ipaddress.IPv4Network(f"{net}/{mask}", strict=False)
                cidr = net_obj.prefixlen
                net_addr = str(net_obj.network_address)
            except Exception:
                cidr = 24
                net_addr = net
            
            if not any(r.network == net_addr and r.cidr == cidr and r.protocol == "S" for r in device.routes):
                device.routes.append(RouteEntry(
                    network=net_addr,
                    cidr=cidr,
                    protocol="S",
                    next_hop=nh if re.match(r"^\d+\.\d+\.\d+\.\d+$", nh) else None,
                    outgoing_interface=normalize_interface_name(nh) if not re.match(r"^\d+\.\d+\.\d+\.\d+$", nh) else None,
                    evidence_line=line_no
                ))
            continue
        
        # Inside interface block
        if current_intf is not None:
            # IP Address
            ip_match = re.match(r"^ip\s+address\s+([0-9\.]+)\s+([0-9\.]+)", stripped, re.IGNORECASE)
            if ip_match:
                ip, mask = ip_match.group(1), ip_match.group(2)
                ip_addr, cidr, net_addr = ip_and_mask_to_network(ip, mask)
                current_intf.ip_address = ip_addr
                current_intf.subnet_mask = mask
                current_intf.cidr = cidr
                current_intf.network_address = net_addr
                current_intf.evidence_lines["ip"] = line_no
                continue
            
            # IPv6 Address
            ipv6_match = re.match(r"^ipv6\s+address\s+([0-9a-fA-F\:\/]+)", stripped, re.IGNORECASE)
            if ipv6_match:
                current_intf.ipv6_address = ipv6_match.group(1).strip()
                current_intf.evidence_lines["ipv6"] = line_no
                continue
            
            # Description
            desc_match = re.match(r"^description\s+(.+)$", stripped, re.IGNORECASE)
            if desc_match:
                current_intf.description = desc_match.group(1).strip()
                current_intf.evidence_lines["description"] = line_no
                continue
            
            # Switchport mode
            if "switchport mode trunk" in stripped.lower():
                current_intf.is_switchport = True
                current_intf.switchport_mode = "trunk"
                device.device_type = "switch"
                current_intf.evidence_lines["switchport_mode"] = line_no
                continue
            elif "switchport mode access" in stripped.lower():
                current_intf.is_switchport = True
                current_intf.switchport_mode = "access"
                device.device_type = "switch"
                current_intf.evidence_lines["switchport_mode"] = line_no
                continue
            elif "switchport" in stripped.lower():
                current_intf.is_switchport = True
                device.device_type = "switch"
```

In `src/pkt_parser.py`: In host port parsing section, also capture `device.default_gateway = gw_val`:
```python
                    # In src/pkt_parser.py around line 186
                    if gw_val:
                        device.default_gateway = gw_val
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_parsers.py`
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add src/parsers.py src/pkt_parser.py tests/test_parsers.py
git commit -m "feat(parsers): parse security baseline, OSPF router processes, and default gateways"
```

---

### Task 3: Policy-Aware Criteria Generation & Dual-Format Formatting

**Files:**
- Modify: `src/criteria_generator.py`
- Test: `tests/test_criteria_generator.py`

**Interfaces:**
- Consumes: `topology: TopologyResult`, `policies: EvaluationPolicies | None = None`.
- Produces: `EvaluationCriteria` with rules reflecting `policies`.
- Produces: `format_criteria_to_instructions_txt()` displaying Policy Summary & Dynamic Addressing guidance when `allow_dynamic_subnetting == True`.
- Produces: `parse_instructions_txt()` correctly instantiating `EvaluationCriteria` including `policies`.

- [ ] **Step 1: Write failing tests in `tests/test_criteria_generator.py`**

```python
# Add to tests/test_criteria_generator.py
from src.models import EvaluationPolicies
from src.criteria_generator import generate_criteria_from_topology, format_criteria_to_instructions_txt, parse_instructions_txt
from src.presets import load_preset
from src.app import process_bundle_dict

def test_generate_criteria_with_dynamic_subnetting_policy():
    bundle = load_preset("ospf_clean")
    top = process_bundle_dict(bundle)
    
    policies = EvaluationPolicies(
        allow_dynamic_subnetting=True,
        enforce_prefix_length=True,
        allow_flexible_process_ids=True
    )
    criteria = generate_criteria_from_topology(
        top,
        lab_title="Dynamic OSPF Challenge",
        policies=policies
    )
    assert criteria.policies.allow_dynamic_subnetting is True
    
    # Check that relational_subnet rules were generated instead of static interface_ip rules for connected links
    rel_rules = [r for r in criteria.rules if r.category == "relational_subnet"]
    assert len(rel_rules) > 0
    assert rel_rules[0].expected_value.get("link_type") == "point_to_point" or "expected_prefixlen" in rel_rules[0].expected_value
    
    # Format and verify instructions text
    txt = format_criteria_to_instructions_txt(criteria)
    assert "Dynamic Subnetting : ENABLED" in txt or "Dynamic Subnetting" in txt
    assert "DYNAMIC & RELATIONAL SUBNETTING POLICY" in txt or "Relational Subnet" in txt
    
    # Parse back
    parsed = parse_instructions_txt(txt)
    assert parsed.policies.allow_dynamic_subnetting is True
    assert parsed.policies.enforce_prefix_length is True
    assert len(parsed.rules) == len(criteria.rules)

def test_generate_criteria_with_security_and_description_policies():
    bundle = load_preset("ospf_clean")
    top = process_bundle_dict(bundle)
    
    policies = EvaluationPolicies(
        grade_security_baseline=True,
        grade_interface_descriptions=True
    )
    criteria = generate_criteria_from_topology(
        top,
        lab_title="Hardened OSPF Network",
        policies=policies
    )
    assert criteria.policies.grade_security_baseline is True
    assert criteria.policies.grade_interface_descriptions is True
    
    sec_rules = [r for r in criteria.rules if r.category == "security"]
    assert len(sec_rules) >= 3  # enable_secret, password_encryption, vty_login
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_criteria_generator.py -k "test_generate_criteria_with_dynamic_subnetting_policy or test_generate_criteria_with_security_and_description_policies"`
Expected: FAIL (`generate_criteria_from_topology() got an unexpected keyword argument 'policies'` or `relational_subnet` not found).

- [ ] **Step 3: Update `src/criteria_generator.py`**

```python
# src/criteria_generator.py
import json
import re
from src.models import EvaluationCriteria, EvaluationPolicies, EvaluationRule, TopologyResult


def generate_criteria_from_topology(
    topology: TopologyResult,
    lab_title: str = "Packet Tracer Lab Assignment",
    lab_description: str = "",
    target_total_points: float = 100.0,
    policies: EvaluationPolicies | None = None
) -> EvaluationCriteria:
    """
    Generates an EvaluationCriteria object with discrete grading rules extracted
    from an instructor's gold-standard reference topology according to evaluation policies.
    """
    if policies is None:
        policies = EvaluationPolicies()

    raw_rules: list[EvaluationRule] = []
    seen_rule_ids: set[str] = set()

    def add_rule(r: EvaluationRule):
        if r.rule_id not in seen_rule_ids:
            seen_rule_ids.add(r.rule_id)
            raw_rules.append(r)

    # 1. Device Presence Rules
    for hostname, dev in topology.devices.items():
        if dev.is_placeholder:
            continue
        dev_name = dev.display_name or dev.hostname
        add_rule(EvaluationRule(
            rule_id=f"dev_{dev.hostname.lower()}",
            category="device",
            description=f"Device '{dev_name}' ({dev.device_type.upper()}) must be present in topology",
            points=5.0,
            target_device=dev.hostname,
            expected_value={"device_type": dev.device_type, "hostname": dev.hostname, "display_name": dev_name}
        ))

        # Security Baseline Rules (if enabled)
        if policies.grade_security_baseline and dev.device_type in ("router", "switch", "l3_switch"):
            add_rule(EvaluationRule(
                rule_id=f"sec_secret_{dev.hostname.lower()}",
                category="security",
                description=f"Configure encrypted privileged EXEC password ('enable secret') on {dev_name}",
                points=4.0,
                target_device=dev.hostname,
                expected_value={"check_type": "enable_secret"}
            ))
            add_rule(EvaluationRule(
                rule_id=f"sec_pwenc_{dev.hostname.lower()}",
                category="security",
                description=f"Enable Cisco password encryption service ('service password-encryption') on {dev_name}",
                points=3.0,
                target_device=dev.hostname,
                expected_value={"check_type": "password_encryption"}
            ))
            add_rule(EvaluationRule(
                rule_id=f"sec_vty_{dev.hostname.lower()}",
                category="security",
                description=f"Secure Virtual Terminal lines with login authentication ('line vty 0 4') on {dev_name}",
                points=3.0,
                target_device=dev.hostname,
                expected_value={"check_type": "vty_login"}
            ))

        # Interface Operational Status & IP / Relational Subnet Rules
        for intf_name, intf in dev.interfaces.items():
            safe_intf = intf_name.replace("/", "_").replace(" ", "_").replace(".", "_")

            # Interface Description Documentation Rule (if enabled)
            if policies.grade_interface_descriptions and (intf.ip_address or intf.switchport_mode):
                add_rule(EvaluationRule(
                    rule_id=f"desc_{dev.hostname.lower()}_{safe_intf.lower()}",
                    category="documentation",
                    description=f"Configure meaningful interface description label on {dev_name} {intf_name}",
                    points=2.0,
                    target_device=dev.hostname,
                    target_interface=intf_name,
                    expected_value={"require_description": True}
                ))

            if intf.ip_address:
                # If Dynamic Subnetting is NOT enabled, create strict IP rules
                if not policies.allow_dynamic_subnetting:
                    cidr_str = f"/{intf.cidr}" if intf.cidr else ""
                    add_rule(EvaluationRule(
                        rule_id=f"ip_{dev.hostname.lower()}_{safe_intf.lower()}",
                        category="interface_ip",
                        description=f"Configure {dev_name} {intf_name} with IP {intf.ip_address}{cidr_str}",
                        points=10.0,
                        target_device=dev.hostname,
                        target_interface=intf_name,
                        expected_value={
                            "ip_address": intf.ip_address,
                            "cidr": intf.cidr,
                            "subnet_mask": intf.subnet_mask,
                            "network_address": intf.network_address
                        }
                    ))

                # Operational status (no shutdown)
                if dev.device_type in ("router", "l3_switch") and intf.admin_status == "up":
                    add_rule(EvaluationRule(
                        rule_id=f"status_{dev.hostname.lower()}_{safe_intf.lower()}",
                        category="interface_status",
                        description=f"Enable interface {dev_name} {intf_name} (operational state: no shutdown)",
                        points=5.0,
                        target_device=dev.hostname,
                        target_interface=intf_name,
                        expected_value={"admin_status": "up", "line_status": "up"}
                    ))

            # VLAN & Switchport Rules
            if intf.switchport_mode == "trunk":
                add_rule(EvaluationRule(
                    rule_id=f"trunk_{dev.hostname.lower()}_{safe_intf.lower()}",
                    category="vlan_trunk",
                    description=f"Configure {dev_name} {intf_name} as 802.1Q Trunk (Native VLAN {intf.trunk_native_vlan})",
                    points=8.0,
                    target_device=dev.hostname,
                    target_interface=intf_name,
                    expected_value={
                        "switchport_mode": "trunk",
                        "trunk_native_vlan": intf.trunk_native_vlan,
                        "trunk_allowed_vlans": intf.trunk_allowed_vlans
                    }
                ))
            elif intf.switchport_mode == "access" and intf.access_vlan:
                add_rule(EvaluationRule(
                    rule_id=f"access_{dev.hostname.lower()}_{safe_intf.lower()}",
                    category="vlan_trunk",
                    description=f"Assign {dev_name} {intf_name} to Access VLAN {intf.access_vlan}",
                    points=6.0,
                    target_device=dev.hostname,
                    target_interface=intf_name,
                    expected_value={
                        "switchport_mode": "access",
                        "access_vlan": intf.access_vlan
                    }
                ))

    # 2. Physical Cabling & Relational Subnet Rules
    seen_link_pairs = set()
    for link in topology.links:
        src = link.source_device
        tgt = link.target_device
        if not src or not tgt or src.startswith("UNKNOWN") or tgt.startswith("UNKNOWN"):
            continue

        pair_key = tuple(sorted([f"{src}:{link.source_interface}", f"{tgt}:{link.target_interface}"]))
        if pair_key in seen_link_pairs:
            continue
        seen_link_pairs.add(pair_key)

        safe_src_intf = link.source_interface.replace("/", "_").replace(" ", "_")
        safe_tgt_intf = link.target_interface.replace("/", "_").replace(" ", "_")
        link_id = f"cabling_{src.lower()}_{safe_src_intf.lower()}__to__{tgt.lower()}_{safe_tgt_intf.lower()}"

        add_rule(EvaluationRule(
            rule_id=link_id,
            category="cabling",
            description=f"Cable connection between {src} ({link.source_interface}) and {tgt} ({link.target_interface})",
            points=8.0,
            target_device=src,
            target_interface=link.source_interface,
            expected_value={
                "source_device": src,
                "source_interface": link.source_interface,
                "target_device": tgt,
                "target_interface": link.target_interface,
                "cable_type": link.cable_type
            }
        ))

        # Dynamic Relational Subnet Rule generation for L3 connected pairs
        if policies.allow_dynamic_subnetting:
            src_dev_obj = topology.devices.get(src)
            tgt_dev_obj = topology.devices.get(tgt)
            if src_dev_obj and tgt_dev_obj:
                src_intf_obj = src_dev_obj.interfaces.get(link.source_interface)
                tgt_intf_obj = tgt_dev_obj.interfaces.get(link.target_interface)
                if src_intf_obj and tgt_intf_obj and src_intf_obj.ip_address and tgt_intf_obj.ip_address:
                    expected_cidr = src_intf_obj.cidr or 30
                    add_rule(EvaluationRule(
                        rule_id=f"rel_subnet_{src.lower()}_{safe_src_intf.lower()}__to__{tgt.lower()}_{safe_tgt_intf.lower()}",
                        category="relational_subnet",
                        description=f"Dynamic Subnet: Configure valid mutual /{expected_cidr} subnet between {src} ({link.source_interface}) and {tgt} ({link.target_interface})",
                        points=12.0,
                        target_device=src,
                        target_interface=link.source_interface,
                        expected_value={
                            "source_device": src,
                            "source_interface": link.source_interface,
                            "target_device": tgt,
                            "target_interface": link.target_interface,
                            "expected_prefixlen": expected_cidr,
                            "link_type": "point_to_point" if expected_cidr == 30 else "broadcast_lan"
                        }
                    ))

    # Point Normalization so total equals target_total_points (e.g. 100.0 pts)
    if raw_rules:
        raw_total = sum(r.points for r in raw_rules)
        scale = target_total_points / raw_total if raw_total > 0 else 1.0
        allocated = 0.0
        for i, r in enumerate(raw_rules):
            if i == len(raw_rules) - 1:
                r.points = round(target_total_points - allocated, 1)
            else:
                pts = round(r.points * scale, 1)
                if pts <= 0:
                    pts = 1.0
                r.points = pts
                allocated += pts

    ref_summary = {
        "device_count": len([d for d in topology.devices.values() if not d.is_placeholder]),
        "link_count": len(topology.links),
        "rule_count": len(raw_rules),
        "ip_count": len([r for r in raw_rules if r.category in ("interface_ip", "relational_subnet")]),
        "policy_summary": policies.model_dump()
    }

    return EvaluationCriteria(
        lab_title=lab_title,
        lab_description=lab_description or "Configure physical cabling, IP addressing, and operational states according to instructor policies.",
        total_points=target_total_points,
        policies=policies,
        rules=raw_rules,
        reference_summary=ref_summary
    )


def format_criteria_to_instructions_txt(criteria: EvaluationCriteria) -> str:
    """
    Formats the evaluation criteria into a clean, human-readable student lab instructions document
    with policy indicators and an embedded machine-verifiable criteria schema at the end.
    """
    lines: list[str] = []
    lines.append("=" * 80)
    lines.append("CISCO LAB ASSIGNMENT & INSTRUCTION SHEET")
    lines.append("=" * 80)
    lines.append(f"Assignment Title : {criteria.lab_title}")
    lines.append(f"Total Points     : {criteria.total_points:.1f} pts")
    lines.append(f"Total Checkpoints: {len(criteria.rules)} items")
    lines.append("-" * 80)
    lines.append("")
    lines.append("1. LAB OVERVIEW & OBJECTIVES")
    lines.append("-" * 40)
    lines.append(criteria.lab_description or "Complete the topology configuration according to the criteria below.")
    lines.append("When finished, upload your Packet Tracer file (.pkt, .pka, .xml) or configuration archive (.zip, .txt)")
    lines.append("to the automated evaluation engine for instant grading and diagnostic feedback.")
    lines.append("")

    # Instructor Policy Summary
    p = criteria.policies
    lines.append("2. INSTRUCTOR EVALUATION POLICIES")
    lines.append("-" * 80)
    lines.append(f"• Dynamic Subnetting     : {'ENABLED (Custom IP schemes permitted; relational mutual subnets checked)' if p.allow_dynamic_subnetting else 'STRICT (Exact assigned IP addresses required)'}")
    lines.append(f"• Prefix Enforcement     : {'ENABLED (Prefix lengths /30, /24 must match)' if p.enforce_prefix_length else 'FLEXIBLE'}")
    lines.append(f"• Default Gateway Check  : {'ENABLED (Host/Switch gateway must match router subnet)' if p.verify_default_gateways else 'DISABLED'}")
    lines.append(f"• Hostname Matching      : {'FLEXIBLE (Matched by topological role & degree)' if p.allow_custom_hostnames else 'STRICT (Exact hostname required)'}")
    lines.append(f"• Interface Speed Class  : {'FLEXIBLE (Equivalent ports accepted)' if not p.strict_port_matching else 'STRICT (Exact port numbering)'}")
    lines.append(f"• Cabling Media / Auto-M : {'FLEXIBLE (Auto-MDIX copper equivalence accepted)' if not p.strict_cable_type else 'STRICT (Exact cable types required)'}")
    lines.append(f"• Routing Process IDs    : {'FLEXIBLE (Locally significant IDs ignored; Area/adjacencies checked)' if p.allow_flexible_process_ids else 'STRICT'}")
    lines.append(f"• Security Baseline      : {'GRADED (enable secret, service pw-enc, vty required)' if p.grade_security_baseline else 'NOT GRADED'}")
    lines.append(f"• Interface Descriptions : {'GRADED (Descriptive interface labels required)' if p.grade_interface_descriptions else 'NOT GRADED'}")
    lines.append("")

    # Addressing Section
    if p.allow_dynamic_subnetting:
        rel_rules = [r for r in criteria.rules if r.category == "relational_subnet"]
        lines.append("3. DYNAMIC & RELATIONAL SUBNETTING POLICY")
        lines.append("-" * 80)
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
            lines.append("3. IP ADDRESSING SPECIFICATION TABLE")
            lines.append("-" * 80)
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
        lines.append("4. PHYSICAL CABLING & PORT CONNECTIONS")
        lines.append("-" * 80)
        lines.append(f"{'Source Device':<18} | {'Port':<16} | {'Target Device':<18} | {'Port':<16}")
        lines.append("-" * 80)
        for r in cabling_rules:
            exp = r.expected_value or {}
            lines.append(f"{exp.get('source_device', ''):<18} | {exp.get('source_interface', ''):<16} | {exp.get('target_device', ''):<18} | {exp.get('target_interface', ''):<16}")
        lines.append("")

    # VLAN & Switchport Requirements
    vlan_rules = [r for r in criteria.rules if r.category == "vlan_trunk"]
    if vlan_rules:
        lines.append("5. SWITCHING & VLAN SPECIFICATIONS")
        lines.append("-" * 80)
        for r in vlan_rules:
            exp = r.expected_value or {}
            mode = exp.get("switchport_mode", "access")
            if mode == "trunk":
                lines.append(f"• {r.target_device} on {r.target_interface}: Mode TRUNK (Native VLAN {exp.get('trunk_native_vlan', 1)})")
            else:
                lines.append(f"• {r.target_device} on {r.target_interface}: Access Port in VLAN {exp.get('access_vlan', 1)}")
        lines.append("")

    # Evaluation Checklist
    lines.append("6. RUBRIC & POINT BREAKDOWN")
    lines.append("-" * 80)
    for i, r in enumerate(criteria.rules, 1):
        lines.append(f"[{r.points:4.1f} pts] #{i:02d}: {r.description}")
    lines.append("")
    lines.append("=" * 80)
    lines.append("DO NOT MODIFY BELOW THIS LINE - MACHINE EVALUATION CRITERIA SPECIFICATION")
    lines.append("=" * 80)
    lines.append("--- CRITERIA SPEC START ---")
    lines.append(criteria.model_dump_json(indent=2))
    lines.append("--- CRITERIA SPEC END ---")
    lines.append("")

    return "\n".join(lines)


def parse_instructions_txt(content: str) -> EvaluationCriteria:
    """
    Parses an instructions.txt document (or raw JSON) and returns an EvaluationCriteria object.
    """
    if not content or not content.strip():
        raise ValueError("Instructions document is empty.")

    pattern = r"--- CRITERIA SPEC START ---\s*(.*?)\s*--- CRITERIA SPEC END ---"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        spec_json = match.group(1).strip()
        try:
            data = json.loads(spec_json)
            return EvaluationCriteria(**data)
        except Exception as e:
            raise ValueError(f"Failed to parse embedded criteria specification: {e}")

    try:
        data = json.loads(content)
        return EvaluationCriteria(**data)
    except Exception:
        pass

    raise ValueError(
        "Invalid instructions file: Missing '--- CRITERIA SPEC START ---' marker. "
        "Please provide an instructions.txt file generated by the Teacher Studio."
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_criteria_generator.py`
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add src/criteria_generator.py tests/test_criteria_generator.py
git commit -m "feat(criteria_generator): add policy-aware rule generation and dynamic dual-format instructions"
```

---

### Task 4: Dynamic Relational Subnetting & Gateway Validation Engine

**Files:**
- Modify: `src/evaluator.py:1-250`
- Test: `tests/test_evaluator.py`

**Interfaces:**
- Consumes: `criteria: EvaluationCriteria` (with `policies.allow_dynamic_subnetting`, `policies.enforce_prefix_length`, `policies.verify_default_gateways`), `student_topology: TopologyResult`.
- Produces: `_evaluate_relational_subnet()` algorithm computing `ipaddress.IPv4Interface` mutual network equality, CIDR verification, host uniqueness, subnet reuse conflict resistance, and default gateway consistency.

- [ ] **Step 1: Write failing tests in `tests/test_evaluator.py`**

```python
# Add to tests/test_evaluator.py
from src.models import EvaluationPolicies
from src.criteria_generator import generate_criteria_from_topology
from src.evaluator import evaluate_student_submission
from src.presets import load_preset
from src.app import process_bundle_dict

def test_dynamic_subnetting_valid_custom_ip_scheme():
    # Instructor reference
    ref_top = process_bundle_dict(load_preset("ospf_clean"))
    policies = EvaluationPolicies(
        allow_dynamic_subnetting=True,
        enforce_prefix_length=True,
        verify_default_gateways=True
    )
    criteria = generate_criteria_from_topology(ref_top, lab_title="Dynamic Subnetting Lab", policies=policies)
    
    # Student submission uses completely different IP scheme: 172.16.0.0/30 instead of 10.0.0.0/30
    student_bundle = {
        "R1.txt": """hostname R1
interface GigabitEthernet0/0
 ip address 172.16.0.1 255.255.255.252
 no shutdown
interface GigabitEthernet0/1
 ip address 172.16.0.5 255.255.255.252
 no shutdown
show cdp neighbors detail
Device ID: R2
Interface: GigabitEthernet0/0, Port ID (outgoing port): GigabitEthernet0/0
Device ID: R3
Interface: GigabitEthernet0/1, Port ID (outgoing port): GigabitEthernet0/0
""",
        "R2.txt": """hostname R2
interface GigabitEthernet0/0
 ip address 172.16.0.2 255.255.255.252
 no shutdown
interface GigabitEthernet0/1
 ip address 172.16.0.9 255.255.255.252
 no shutdown
show cdp neighbors detail
Device ID: R1
Interface: GigabitEthernet0/0, Port ID (outgoing port): GigabitEthernet0/0
Device ID: R3
Interface: GigabitEthernet0/1, Port ID (outgoing port): GigabitEthernet0/1
""",
        "R3.txt": """hostname R3
interface GigabitEthernet0/0
 ip address 172.16.0.6 255.255.255.252
 no shutdown
interface GigabitEthernet0/1
 ip address 172.16.0.10 255.255.255.252
 no shutdown
show cdp neighbors detail
Device ID: R1
Interface: GigabitEthernet0/0, Port ID (outgoing port): GigabitEthernet0/1
Device ID: R2
Interface: GigabitEthernet0/1, Port ID (outgoing port): GigabitEthernet0/1
"""
    }
    student_top = process_bundle_dict(student_bundle)
    report = evaluate_student_submission(criteria, student_top)
    
    assert report.percentage == 100.0
    assert report.grade_letter in ("A", "A+")
    assert report.failed_count == 0
    rel_results = [r for r in report.results if r.category == "relational_subnet"]
    assert len(rel_results) > 0
    for r in rel_results:
        assert r.passed is True
        assert "Mutual subnet" in r.feedback

def test_dynamic_subnetting_mismatched_subnet_pair():
    ref_top = process_bundle_dict(load_preset("ospf_clean"))
    policies = EvaluationPolicies(allow_dynamic_subnetting=True)
    criteria = generate_criteria_from_topology(ref_top, lab_title="Dynamic Subnetting Lab", policies=policies)
    
    # R1 is on 172.16.0.1/30 and R2 is on 172.16.1.2/30 (different subnets!)
    flawed_bundle = {
        "R1.txt": """hostname R1
interface GigabitEthernet0/0
 ip address 172.16.0.1 255.255.255.252
 no shutdown
show cdp neighbors detail
Device ID: R2
Interface: GigabitEthernet0/0, Port ID (outgoing port): GigabitEthernet0/0
""",
        "R2.txt": """hostname R2
interface GigabitEthernet0/0
 ip address 172.16.1.2 255.255.255.252
 no shutdown
show cdp neighbors detail
Device ID: R1
Interface: GigabitEthernet0/0, Port ID (outgoing port): GigabitEthernet0/0
"""
    }
    student_top = process_bundle_dict(flawed_bundle)
    report = evaluate_student_submission(criteria, student_top)
    
    r1_r2_rel = [r for r in report.results if r.category == "relational_subnet" and "r1" in r.rule_id and "r2" in r.rule_id]
    assert len(r1_r2_rel) > 0
    assert r1_r2_rel[0].passed is False
    assert "different subnets" in r1_r2_rel[0].feedback.lower() or "mismatch" in r1_r2_rel[0].feedback.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_evaluator.py -k "test_dynamic_subnetting_valid_custom_ip_scheme or test_dynamic_subnetting_mismatched_subnet_pair"`
Expected: FAIL (`_evaluate_relational_subnet` not handled in `evaluate_student_submission`).

- [ ] **Step 3: Implement relational subnet evaluation in `src/evaluator.py`**

```python
# Add to src/evaluator.py
import ipaddress

def _evaluate_relational_subnet(
    rule: EvaluationRule,
    criteria: EvaluationCriteria,
    devices: dict,
    used_subnets: set
) -> tuple[bool, float, str, str]:
    """
    Validates dynamic relational subnetting between connected interfaces:
    1. Both endpoints configured with IPv4
    2. Mutual subnet equivalence (net_a == net_b)
    3. Unique host addresses (ip_a != ip_b)
    4. Enforce prefix length (if policy active)
    5. Subnet reuse collision check across distinct links
    6. Default gateway consistency (if policy active)
    """
    exp = rule.expected_value or {}
    src_dev_name = exp.get("source_device", rule.target_device)
    src_intf_name = exp.get("source_interface", rule.target_interface)
    tgt_dev_name = exp.get("target_device", "")
    tgt_intf_name = exp.get("target_interface", "")
    exp_prefix = exp.get("expected_prefixlen")

    dev_a = _find_student_device(devices, src_dev_name, criteria.policies.allow_custom_hostnames)
    dev_b = _find_student_device(devices, tgt_dev_name, criteria.policies.allow_custom_hostnames)

    if not dev_a or not dev_b:
        missing = src_dev_name if not dev_a else tgt_dev_name
        return False, 0.0, "Missing Device", f"Cannot verify dynamic subnet: Device '{missing}' is missing in submission."

    intf_a = _find_student_interface(dev_a.interfaces, src_intf_name, criteria.policies.strict_port_matching)
    intf_b = _find_student_interface(dev_b.interfaces, tgt_intf_name, criteria.policies.strict_port_matching)

    if not intf_a or not intf_b:
        missing_intf = f"{src_dev_name} {src_intf_name}" if not intf_a else f"{tgt_dev_name} {tgt_intf_name}"
        return False, 0.0, "Missing Interface", f"Cannot verify dynamic subnet: Interface '{missing_intf}' is missing."

    if not intf_a.ip_address or not intf_b.ip_address:
        unconfig = f"{src_dev_name}:{src_intf_name}" if not intf_a.ip_address else f"{tgt_dev_name}:{tgt_intf_name}"
        return False, 0.0, "Unassigned IP", f"Endpoint {unconfig} has no IPv4 address configured."

    try:
        iface_a = ipaddress.IPv4Interface(f"{intf_a.ip_address}/{intf_a.subnet_mask or intf_a.cidr or 24}")
        iface_b = ipaddress.IPv4Interface(f"{intf_b.ip_address}/{intf_b.subnet_mask or intf_b.cidr or 24}")
    except Exception as e:
        return False, 0.0, "Invalid IP Syntax", f"Malformed IPv4 configuration: {e}"

    # 1. Mutual Subnet Check
    if iface_a.network != iface_b.network:
        actual_val = f"{intf_a.ip_address}/{iface_a.network.prefixlen} vs {intf_b.ip_address}/{iface_b.network.prefixlen}"
        return False, 0.0, actual_val, f"Subnet mismatch: {src_dev_name} ({intf_a.ip_address}) and {tgt_dev_name} ({intf_b.ip_address}) are on different subnets ({iface_a.network} vs {iface_b.network})."

    # 2. Host Uniqueness (no duplicate IP)
    if iface_a.ip == iface_b.ip:
        return False, round(rule.points * 0.3, 1), f"Duplicate IP ({iface_a.ip})", f"IP Collision: Both {src_dev_name} and {tgt_dev_name} are configured with identical IP address {iface_a.ip}."

    # 3. Prefix Length Enforcement
    if criteria.policies.enforce_prefix_length and exp_prefix is not None:
        if iface_a.network.prefixlen != exp_prefix:
            return False, round(rule.points * 0.6, 1), f"/{iface_a.network.prefixlen}", f"Subnet matches ({iface_a.network}), but CIDR prefix /{iface_a.network.prefixlen} does not match required /{exp_prefix}."

    # 4. Conflict Resistance (Subnet Reuse Collision)
    net_str = str(iface_a.network)
    link_key = tuple(sorted([f"{src_dev_name}:{src_intf_name}", f"{tgt_dev_name}:{tgt_intf_name}"]))
    if net_str in used_subnets and used_subnets[net_str] != link_key:
        return False, round(rule.points * 0.5, 1), f"Duplicate Subnet {net_str}", f"Subnet {net_str} is already used on another point-to-point link. Each link must have a unique subnet."
    used_subnets[net_str] = link_key

    # 5. Default Gateway Consistency (if one is host/switch)
    if criteria.policies.verify_default_gateways:
        for host_dev, router_dev, r_intf in [(dev_a, dev_b, intf_b), (dev_b, dev_a, intf_a)]:
            if host_dev.device_type in ("host", "switch") and host_dev.default_gateway:
                try:
                    gw_ip = ipaddress.IPv4Address(host_dev.default_gateway)
                    if gw_ip != ipaddress.IPv4Address(r_intf.ip_address):
                        return False, round(rule.points * 0.7, 1), f"Gateway {host_dev.default_gateway}", f"{host_dev.hostname} default gateway ({host_dev.default_gateway}) does not match router interface IP ({r_intf.ip_address})."
                except Exception:
                    pass

    actual_str = f"{iface_a.ip} ⟷ {iface_b.ip} ({iface_a.network})"
    feedback_str = f"Mutual subnet ({iface_a.network}) verified between {src_dev_name}:{src_intf_name} ({intf_a.ip_address}) and {tgt_dev_name}:{tgt_intf_name} ({intf_b.ip_address})."
    return True, rule.points, actual_str, feedback_str
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_evaluator.py`
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add src/evaluator.py tests/test_evaluator.py
git commit -m "feat(evaluator): implement dynamic relational subnetting algorithm with mutual CIDR and gateway checks"
```

---

### Task 5: Flexible Hostnames, Port Tolerance, Auto-MDIX Cabling & Flexible Routing

**Files:**
- Modify: `src/evaluator.py`
- Test: `tests/test_evaluator.py`

**Interfaces:**
- Consumes: `criteria.policies.allow_custom_hostnames`, `criteria.policies.strict_port_matching`, `criteria.policies.strict_cable_type`, `criteria.policies.allow_flexible_process_ids`, `criteria.policies.grade_security_baseline`, `criteria.policies.grade_interface_descriptions`.
- Produces: Topological role matching for custom device names; speed-class equivalence for port numbers; Auto-MDIX copper tolerance; OSPF area/adjacency matching regardless of process ID; security baseline checks; interface documentation checks.

- [ ] **Step 1: Write failing tests in `tests/test_evaluator.py`**

```python
# Add to tests/test_evaluator.py

def test_flexible_hostnames_matching():
    ref_top = process_bundle_dict(load_preset("ospf_clean"))
    policies = EvaluationPolicies(
        allow_custom_hostnames=True,
        allow_dynamic_subnetting=True
    )
    criteria = generate_criteria_from_topology(ref_top, lab_title="Custom Hostnames Lab", policies=policies)
    
    # Student names routers 'Router_East', 'Router_Central', 'Router_West' instead of R1, R2, R3
    custom_bundle = {
        "Router_East.txt": """hostname Router_East
interface GigabitEthernet0/0
 ip address 10.0.0.1 255.255.255.252
 no shutdown
show cdp neighbors detail
Device ID: Router_Central
Interface: GigabitEthernet0/0, Port ID (outgoing port): GigabitEthernet0/0
""",
        "Router_Central.txt": """hostname Router_Central
interface GigabitEthernet0/0
 ip address 10.0.0.2 255.255.255.252
 no shutdown
show cdp neighbors detail
Device ID: Router_East
Interface: GigabitEthernet0/0, Port ID (outgoing port): GigabitEthernet0/0
"""
    }
    student_top = process_bundle_dict(custom_bundle)
    report = evaluate_student_submission(criteria, student_top)
    # R1 and R2 should match Router_East and Router_Central
    r1_dev_rule = [r for r in report.results if r.target_device == "R1" and r.category == "device"][0]
    assert r1_dev_rule.passed is True
    assert "Matched by topological role" in r1_dev_rule.feedback

def test_automdix_cabling_tolerance():
    clean_top = process_bundle_dict(load_preset("ospf_clean"))
    policies = EvaluationPolicies(strict_cable_type=False)
    criteria = generate_criteria_from_topology(clean_top, lab_title="Cabling Tolerance", policies=policies)
    
    # Create topology with a cable conflict (e.g. straight-through instead of cross-over)
    flawed_top = process_bundle_dict(load_preset("ospf_clean"))
    for l in flawed_top.links:
        l.conflicts.append("Cable type mismatch: Straight-Through used instead of Cross-Over")
    
    report = evaluate_student_submission(criteria, flawed_top)
    cabling_results = [r for r in report.results if r.category == "cabling"]
    for r in cabling_results:
        assert r.passed is True
        assert "Auto-MDIX" in r.feedback

def test_flexible_ospf_process_ids():
    ref_top = process_bundle_dict(load_preset("ospf_clean"))
    policies = EvaluationPolicies(allow_flexible_process_ids=True)
    criteria = generate_criteria_from_topology(ref_top, lab_title="OSPF Process ID Lab", policies=policies)
    
    # Add routing rule to criteria
    criteria.rules.append(EvaluationRule(
        rule_id="ospf_area0_r1",
        category="routing",
        description="Configure OSPF Area 0 routing on R1",
        points=10.0,
        target_device="R1",
        expected_value={"protocol": "ospf", "process_id": 1, "area": 0, "network": "10.0.0.0"}
    ))
    
    # Student configured router ospf 99 (process id 99 instead of 1)
    student_bundle = {
        "R1.txt": """hostname R1
interface GigabitEthernet0/0
 ip address 10.0.0.1 255.255.255.252
router ospf 99
 network 10.0.0.0 0.0.0.3 area 0
"""
    }
    student_top = process_bundle_dict(student_bundle)
    report = evaluate_student_submission(criteria, student_top)
    ospf_res = [r for r in report.results if r.rule_id == "ospf_area0_r1"][0]
    assert ospf_res.passed is True
    assert "process ID 99 accepted" in ospf_res.feedback
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_evaluator.py -k "test_flexible_hostnames_matching or test_automdix_cabling_tolerance or test_flexible_ospf_process_ids"`
Expected: FAIL.

- [ ] **Step 3: Update `src/evaluator.py`**

Complete implementation of `src/evaluator.py`:
```python
# src/evaluator.py
import ipaddress
import re
from src.models import (
    EvaluationCriteria,
    EvaluationPolicies,
    EvaluationReport,
    EvaluationRule,
    RuleResult,
    TopologyResult,
)
from src.parsers import canonical_device_name, normalize_interface_name


def _find_student_device(devices: dict, target_hostname: str, allow_custom_names: bool = False):
    """Finds a student device by exact hostname, canonical name, or topological role fallback."""
    if not target_hostname:
        return None
    if target_hostname in devices:
        return devices[target_hostname]
    
    target_norm = canonical_device_name(target_hostname).lower()
    for name, dev in devices.items():
        if canonical_device_name(name).lower() == target_norm or canonical_device_name(dev.display_name or "").lower() == target_norm:
            return dev
    
    if allow_custom_names:
        # Match by device role (e.g. if target starts with 'R' or 'Router', match candidate router)
        tgt_is_router = target_norm.startswith("r") or "router" in target_norm
        tgt_is_switch = target_norm.startswith("s") or "switch" in target_norm or "sw" in target_norm
        tgt_is_host = target_norm.startswith("pc") or "host" in target_norm
        
        for name, dev in devices.items():
            if dev.is_placeholder:
                continue
            if tgt_is_router and dev.device_type in ("router", "l3_switch"):
                return dev
            elif tgt_is_switch and dev.device_type == "switch":
                return dev
            elif tgt_is_host and dev.device_type == "host":
                return dev

    return None


def _find_student_interface(interfaces: dict, target_interface_name: str, strict_ports: bool = True):
    """Finds a student interface by exact name or normalized shorthand / speed class."""
    if not target_interface_name:
        return None
    if target_interface_name in interfaces:
        return interfaces[target_interface_name]

    target_norm = normalize_interface_name(target_interface_name).lower()
    for name, intf in interfaces.items():
        if normalize_interface_name(name).lower() == target_norm:
            return intf

    if not strict_ports:
        # Match interface of same speed class (e.g. GigabitEthernet vs GigabitEthernet)
        is_gi = "gigabit" in target_norm
        is_fa = "fast" in target_norm
        is_se = "serial" in target_norm
        for name, intf in interfaces.items():
            n_lower = normalize_interface_name(name).lower()
            if is_gi and "gigabit" in n_lower:
                return intf
            elif is_fa and "fast" in n_lower:
                return intf
            elif is_se and "serial" in n_lower:
                return intf

    return None


def _link_matches(link, src_dev: str, src_intf: str, tgt_dev: str, tgt_intf: str, strict_ports: bool = True) -> bool:
    """Checks if a DiscoveredLink matches the expected endpoints in either direction."""
    src_d_norm = canonical_device_name(src_dev).lower()
    tgt_d_norm = canonical_device_name(tgt_dev).lower()
    src_i_norm = normalize_interface_name(src_intf).lower()
    tgt_i_norm = normalize_interface_name(tgt_intf).lower()

    l_src_d = canonical_device_name(link.source_device).lower()
    l_tgt_d = canonical_device_name(link.target_device).lower()
    l_src_i = normalize_interface_name(link.source_interface).lower()
    l_tgt_i = normalize_interface_name(link.target_interface).lower()

    # Forward direction
    if l_src_d == src_d_norm and l_tgt_d == tgt_d_norm:
        if strict_ports:
            if l_src_i == src_i_norm and l_tgt_i == tgt_i_norm:
                return True
        else:
            return True
    
    # Reverse direction
    if l_src_d == tgt_d_norm and l_tgt_d == src_d_norm:
        if strict_ports:
            if l_src_i == tgt_i_norm and l_tgt_i == src_i_norm:
                return True
        else:
            return True

    return False


def _evaluate_relational_subnet(
    rule: EvaluationRule,
    criteria: EvaluationCriteria,
    devices: dict,
    used_subnets: dict
) -> tuple[bool, float, str, str]:
    exp = rule.expected_value or {}
    src_dev_name = exp.get("source_device", rule.target_device)
    src_intf_name = exp.get("source_interface", rule.target_interface)
    tgt_dev_name = exp.get("target_device", "")
    tgt_intf_name = exp.get("target_interface", "")
    exp_prefix = exp.get("expected_prefixlen")

    dev_a = _find_student_device(devices, src_dev_name, criteria.policies.allow_custom_hostnames)
    dev_b = _find_student_device(devices, tgt_dev_name, criteria.policies.allow_custom_hostnames)

    if not dev_a or not dev_b:
        missing = src_dev_name if not dev_a else tgt_dev_name
        return False, 0.0, "Missing Device", f"Cannot verify dynamic subnet: Device '{missing}' is missing in submission."

    intf_a = _find_student_interface(dev_a.interfaces, src_intf_name, criteria.policies.strict_port_matching)
    intf_b = _find_student_interface(dev_b.interfaces, tgt_intf_name, criteria.policies.strict_port_matching)

    if not intf_a or not intf_b:
        missing_intf = f"{src_dev_name} {src_intf_name}" if not intf_a else f"{tgt_dev_name} {tgt_intf_name}"
        return False, 0.0, "Missing Interface", f"Cannot verify dynamic subnet: Interface '{missing_intf}' is missing."

    if not intf_a.ip_address or not intf_b.ip_address:
        unconfig = f"{src_dev_name}:{src_intf_name}" if not intf_a.ip_address else f"{tgt_dev_name}:{tgt_intf_name}"
        return False, 0.0, "Unassigned IP", f"Endpoint {unconfig} has no IPv4 address configured."

    try:
        mask_a = intf_a.subnet_mask or (f"/{intf_a.cidr}" if intf_a.cidr else "/24")
        mask_b = intf_b.subnet_mask or (f"/{intf_b.cidr}" if intf_b.cidr else "/24")
        iface_a = ipaddress.IPv4Interface(f"{intf_a.ip_address}/{intf_a.cidr or 24}")
        iface_b = ipaddress.IPv4Interface(f"{intf_b.ip_address}/{intf_b.cidr or 24}")
    except Exception as e:
        return False, 0.0, "Invalid IP Syntax", f"Malformed IPv4 configuration: {e}"

    if iface_a.network != iface_b.network:
        actual_val = f"{intf_a.ip_address}/{iface_a.network.prefixlen} vs {intf_b.ip_address}/{iface_b.network.prefixlen}"
        return False, 0.0, actual_val, f"Subnet mismatch: {src_dev_name} ({intf_a.ip_address}) and {tgt_dev_name} ({intf_b.ip_address}) are on different subnets ({iface_a.network} vs {iface_b.network})."

    if iface_a.ip == iface_b.ip:
        return False, round(rule.points * 0.3, 1), f"Duplicate IP ({iface_a.ip})", f"IP Collision: Both {src_dev_name} and {tgt_dev_name} configured with identical IP {iface_a.ip}."

    if criteria.policies.enforce_prefix_length and exp_prefix is not None:
        if iface_a.network.prefixlen != exp_prefix:
            return False, round(rule.points * 0.6, 1), f"/{iface_a.network.prefixlen}", f"Subnet matches ({iface_a.network}), but CIDR prefix /{iface_a.network.prefixlen} does not match required /{exp_prefix}."

    net_str = str(iface_a.network)
    link_key = tuple(sorted([f"{src_dev_name}:{src_intf_name}", f"{tgt_dev_name}:{tgt_intf_name}"]))
    if net_str in used_subnets and used_subnets[net_str] != link_key:
        return False, round(rule.points * 0.5, 1), f"Duplicate Subnet {net_str}", f"Subnet {net_str} is already used on another link. Point-to-point subnets must be globally unique."
    used_subnets[net_str] = link_key

    if criteria.policies.verify_default_gateways:
        for host_dev, router_dev, r_intf in [(dev_a, dev_b, intf_b), (dev_b, dev_a, intf_a)]:
            if host_dev.device_type in ("host", "switch") and host_dev.default_gateway:
                try:
                    gw_ip = ipaddress.IPv4Address(host_dev.default_gateway)
                    if gw_ip != ipaddress.IPv4Address(r_intf.ip_address):
                        return False, round(rule.points * 0.7, 1), f"Gateway {host_dev.default_gateway}", f"{host_dev.hostname} default gateway ({host_dev.default_gateway}) does not match router interface IP ({r_intf.ip_address})."
                except Exception:
                    pass

    actual_str = f"{iface_a.ip} ⟷ {iface_b.ip} ({iface_a.network})"
    feedback_str = f"Mutual subnet ({iface_a.network}) verified between {src_dev_name}:{src_intf_name} ({intf_a.ip_address}) and {tgt_dev_name}:{tgt_intf_name} ({intf_b.ip_address})."
    return True, rule.points, actual_str, feedback_str


def evaluate_student_submission(
    criteria: EvaluationCriteria,
    student_topology: TopologyResult
) -> EvaluationReport:
    rule_results: list[RuleResult] = []
    total_score = 0.0
    max_score = 0.0
    passed_count = 0
    failed_count = 0

    devices = student_topology.devices
    links = student_topology.links
    used_subnets: dict[str, tuple] = {}
    policies = criteria.policies

    for rule in criteria.rules:
        pts_possible = float(rule.points)
        max_score += pts_possible
        exp = rule.expected_value or {}

        # 1. Device Presence Rule
        if rule.category == "device":
            dev = _find_student_device(devices, rule.target_device, policies.allow_custom_hostnames)
            if dev and not dev.is_placeholder:
                pts_earned = pts_possible
                passed = True
                if dev.hostname.lower() == rule.target_device.lower():
                    actual = f"Present ({dev.hostname}, type: {dev.device_type})"
                    feedback = f"Device '{rule.target_device}' correctly detected in topology."
                else:
                    actual = f"Present as '{dev.hostname}'"
                    feedback = f"Device '{rule.target_device}' matched to '{dev.hostname}' (Matched by topological role & degree)."
            else:
                pts_earned = 0.0
                passed = False
                actual = "Missing"
                feedback = f"Required device '{rule.target_device}' was not found in your submission."

        # 2. Interface IP & Subnet Rule
        elif rule.category == "interface_ip":
            dev = _find_student_device(devices, rule.target_device, policies.allow_custom_hostnames)
            if not dev:
                pts_earned = 0.0
                passed = False
                actual = f"Device '{rule.target_device}' not found"
                feedback = f"Cannot evaluate IP address because device '{rule.target_device}' is missing."
            else:
                intf = _find_student_interface(dev.interfaces, rule.target_interface or "", policies.strict_port_matching)
                if not intf:
                    pts_earned = 0.0
                    passed = False
                    actual = f"Interface '{rule.target_interface}' missing"
                    feedback = f"Interface '{rule.target_interface}' was not found on device '{rule.target_device}'."
                elif not intf.ip_address:
                    pts_earned = 0.0
                    passed = False
                    actual = "No IP configured (Unassigned)"
                    feedback = f"Interface {rule.target_interface} has no IP address configured. Expected {exp.get('ip_address')}/{exp.get('cidr')}."
                else:
                    exp_ip = exp.get("ip_address")
                    exp_cidr = exp.get("cidr")
                    exp_mask = exp.get("subnet_mask")

                    ip_match = intf.ip_address == exp_ip
                    cidr_match = (intf.cidr == exp_cidr) if (exp_cidr and intf.cidr) else True

                    if ip_match and cidr_match:
                        pts_earned = pts_possible
                        passed = True
                        actual = f"{intf.ip_address}/{intf.cidr or 24}"
                        feedback = f"Correct IP addressing ({intf.ip_address}/{intf.cidr or 24}) verified on {rule.target_device} {rule.target_interface}."
                    elif ip_match and not cidr_match:
                        pts_earned = round(pts_possible * 0.5, 1)
                        passed = False
                        actual = f"{intf.ip_address}/{intf.cidr}"
                        feedback = f"IP address {intf.ip_address} is correct, but subnet mask /{intf.cidr} is incorrect. Expected /{exp_cidr} ({exp_mask})."
                    else:
                        pts_earned = 0.0
                        passed = False
                        actual = f"{intf.ip_address}/{intf.cidr or 24}"
                        feedback = f"Configured IP ({intf.ip_address}/{intf.cidr or 24}) does not match expected ({exp_ip}/{exp_cidr})."

        # 3. Dynamic Relational Subnet Rule
        elif rule.category == "relational_subnet":
            passed, pts_earned, actual, feedback = _evaluate_relational_subnet(
                rule=rule,
                criteria=criteria,
                devices=devices,
                used_subnets=used_subnets
            )

        # 4. Interface Status / No Shutdown Rule
        elif rule.category == "interface_status":
            dev = _find_student_device(devices, rule.target_device, policies.allow_custom_hostnames)
            if not dev:
                pts_earned = 0.0
                passed = False
                actual = f"Device '{rule.target_device}' missing"
                feedback = f"Cannot verify operational status: device '{rule.target_device}' missing."
            else:
                intf = _find_student_interface(dev.interfaces, rule.target_interface or "", policies.strict_port_matching)
                if not intf:
                    pts_earned = 0.0
                    passed = False
                    actual = f"Interface '{rule.target_interface}' missing"
                    feedback = f"Interface '{rule.target_interface}' missing on device '{rule.target_device}'."
                elif intf.admin_status == "administratively down":
                    pts_earned = 0.0
                    passed = False
                    actual = "administratively down"
                    feedback = f"Interface {rule.target_device} {rule.target_interface} is shut down. Missing 'no shutdown' command in configuration."
                else:
                    pts_earned = pts_possible
                    passed = True
                    actual = f"{intf.admin_status}/{intf.line_status}"
                    feedback = f"Interface {rule.target_device} {rule.target_interface} operational state verified (up/up)."

        # 5. Physical Cabling & Link Rule
        elif rule.category == "cabling":
            src_dev = exp.get("source_device", rule.target_device)
            src_intf = exp.get("source_interface", rule.target_interface or "")
            tgt_dev = exp.get("target_device", "")
            tgt_intf = exp.get("target_interface", "")

            matched_link = None
            for l in links:
                if _link_matches(l, src_dev, src_intf, tgt_dev, tgt_intf, policies.strict_port_matching):
                    matched_link = l
                    break

            if matched_link:
                has_cable_conflict = any("Cable" in c or "straight-through" in c.lower() for c in matched_link.conflicts)
                if has_cable_conflict and policies.strict_cable_type:
                    pts_earned = round(pts_possible * 0.4, 1)
                    passed = False
                    actual = f"Connected via {matched_link.cable_type or 'Unknown cable'} (Cabling Error)"
                    feedback = f"Physical connection found between {src_dev}:{src_intf} and {tgt_dev}:{tgt_intf}, but incorrect cable media was used."
                elif has_cable_conflict and not policies.strict_cable_type:
                    pts_earned = pts_possible
                    passed = True
                    actual = f"Connected ({matched_link.cable_type} - Auto-MDIX Tolerated)"
                    feedback = f"Physical connection verified between {src_dev} and {tgt_dev} (Auto-MDIX copper equivalence accepted under instructor policy)."
                else:
                    pts_earned = pts_possible
                    passed = True
                    actual = f"Connected: {matched_link.source_device}:{matched_link.source_interface} ⟷ {matched_link.target_device}:{matched_link.target_interface}"
                    feedback = f"Physical connection verified between {src_dev} ({src_intf}) and {tgt_dev} ({tgt_intf})."
            else:
                pts_earned = 0.0
                passed = False
                actual = "Disconnected / Uncabled"
                feedback = f"No physical connection found between {src_dev} ({src_intf}) and {tgt_dev} ({tgt_intf}). Verify physical cabling in Packet Tracer."

        # 6. VLAN & Switchport Rule
        elif rule.category == "vlan_trunk":
            dev = _find_student_device(devices, rule.target_device, policies.allow_custom_hostnames)
            if not dev:
                pts_earned = 0.0
                passed = False
                actual = f"Device '{rule.target_device}' missing"
                feedback = f"Cannot evaluate VLAN configuration: device '{rule.target_device}' missing."
            else:
                intf = _find_student_interface(dev.interfaces, rule.target_interface or "", policies.strict_port_matching)
                if not intf:
                    pts_earned = 0.0
                    passed = False
                    actual = f"Interface '{rule.target_interface}' missing"
                    feedback = f"Interface '{rule.target_interface}' missing on switch '{rule.target_device}'."
                else:
                    exp_mode = exp.get("switchport_mode", "access")
                    if exp_mode == "trunk":
                        exp_native = exp.get("trunk_native_vlan", 1)
                        if intf.switchport_mode == "trunk" and intf.trunk_native_vlan == exp_native:
                            pts_earned = pts_possible
                            passed = True
                            actual = f"Trunk (Native VLAN {intf.trunk_native_vlan})"
                            feedback = f"Trunk port configuration verified on {rule.target_device} {rule.target_interface}."
                        elif intf.switchport_mode == "trunk":
                            pts_earned = round(pts_possible * 0.5, 1)
                            passed = False
                            actual = f"Trunk (Native VLAN {intf.trunk_native_vlan})"
                            feedback = f"Port is trunking, but Native VLAN ({intf.trunk_native_vlan}) does not match expected ({exp_native})."
                        else:
                            pts_earned = 0.0
                            passed = False
                            actual = f"Mode: {intf.switchport_mode or 'access'}"
                            feedback = f"Expected 802.1Q trunk port, but interface is configured as '{intf.switchport_mode or 'access'}'."
                    else:
                        exp_vlan = exp.get("access_vlan", 1)
                        if intf.switchport_mode == "access" and intf.access_vlan == exp_vlan:
                            pts_earned = pts_possible
                            passed = True
                            actual = f"Access VLAN {intf.access_vlan}"
                            feedback = f"Access port assigned to VLAN {intf.access_vlan} on {rule.target_device} {rule.target_interface}."
                        else:
                            pts_earned = 0.0
                            passed = False
                            actual = f"Access VLAN {intf.access_vlan or 'None'}"
                            feedback = f"Expected Access VLAN {exp_vlan}, but port is assigned to VLAN {intf.access_vlan or 'default (1)'}."

        # 7. Routing / OSPF Rule
        elif rule.category == "routing":
            dev = _find_student_device(devices, rule.target_device, policies.allow_custom_hostnames)
            if not dev:
                pts_earned = 0.0
                passed = False
                actual = f"Device '{rule.target_device}' missing"
                feedback = f"Cannot evaluate routing: device '{rule.target_device}' missing."
            else:
                proto = exp.get("protocol", "ospf")
                exp_area = exp.get("area", 0)
                exp_pid = exp.get("process_id", 1)
                
                matched_ospf = None
                for proc in dev.ospf_processes:
                    if policies.allow_flexible_process_ids or proc.get("process_id") == exp_pid:
                        for n in proc.get("networks", []):
                            if n.get("area") == exp_area:
                                matched_ospf = proc
                                break
                
                if matched_ospf:
                    pts_earned = pts_possible
                    passed = True
                    actual = f"OSPF Process {matched_ospf.get('process_id')} (Area {exp_area})"
                    feedback = f"OSPF routing verified on {rule.target_device} (Area {exp_area}, process ID {matched_ospf.get('process_id')} accepted)."
                else:
                    pts_earned = 0.0
                    passed = False
                    actual = "No matching OSPF config"
                    feedback = f"Missing OSPF routing for Area {exp_area} on {rule.target_device}."

        # 8. Security Baseline Rule
        elif rule.category == "security":
            dev = _find_student_device(devices, rule.target_device, policies.allow_custom_hostnames)
            check_type = exp.get("check_type")
            if not dev:
                pts_earned = 0.0
                passed = False
                actual = "Missing Device"
                feedback = f"Cannot verify security baseline: device '{rule.target_device}' is missing."
            elif check_type == "enable_secret":
                if dev.has_enable_secret:
                    pts_earned = pts_possible
                    passed = True
                    actual = "Configured (enable secret)"
                    feedback = f"Encrypted enable secret verified on {rule.target_device}."
                else:
                    pts_earned = 0.0
                    passed = False
                    actual = "Missing enable secret"
                    feedback = f"Missing 'enable secret' privileged password command on {rule.target_device}."
            elif check_type == "password_encryption":
                if dev.has_password_encryption:
                    pts_earned = pts_possible
                    passed = True
                    actual = "Enabled (service password-encryption)"
                    feedback = f"Password encryption service verified on {rule.target_device}."
                else:
                    pts_earned = 0.0
                    passed = False
                    actual = "Disabled"
                    feedback = f"Missing 'service password-encryption' command on {rule.target_device}."
            elif check_type == "vty_login":
                if dev.has_vty_login:
                    pts_earned = pts_possible
                    passed = True
                    actual = "Secured (line vty login)"
                    feedback = f"VTY line login authentication verified on {rule.target_device}."
                else:
                    pts_earned = 0.0
                    passed = False
                    actual = "Unsecured VTY"
                    feedback = f"Missing 'login' / password protection under 'line vty' on {rule.target_device}."
            else:
                pts_earned = pts_possible
                passed = True
                actual = "Met"
                feedback = "Security baseline met."

        # 9. Interface Documentation Rule
        elif rule.category == "documentation":
            dev = _find_student_device(devices, rule.target_device, policies.allow_custom_hostnames)
            if not dev:
                pts_earned = 0.0
                passed = False
                actual = "Missing Device"
                feedback = f"Cannot verify documentation: device '{rule.target_device}' is missing."
            else:
                intf = _find_student_interface(dev.interfaces, rule.target_interface or "", policies.strict_port_matching)
                if intf and intf.description:
                    pts_earned = pts_possible
                    passed = True
                    actual = f"'{intf.description}'"
                    feedback = f"Interface description documented on {rule.target_device} {rule.target_interface}."
                else:
                    pts_earned = 0.0
                    passed = False
                    actual = "No description"
                    feedback = f"Missing 'description' statement on {rule.target_device} {rule.target_interface}."

        else:
            pts_earned = pts_possible
            passed = True
            actual = "N/A"
            feedback = "Criterion met."

        if passed:
            passed_count += 1
        else:
            failed_count += 1

        total_score += pts_earned

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
            target_interface=rule.target_interface
        ))

    percentage = (total_score / max_score * 100.0) if max_score > 0 else 0.0
    percentage = round(percentage, 1)
    total_score = round(total_score, 1)
    max_score = round(max_score, 1)

    if percentage >= 97.0:
        grade_letter = "A+"
    elif percentage >= 90.0:
        grade_letter = "A"
    elif percentage >= 80.0:
        grade_letter = "B"
    elif percentage >= 70.0:
        grade_letter = "C"
    elif percentage >= 60.0:
        grade_letter = "D"
    else:
        grade_letter = "F"

    return EvaluationReport(
        lab_title=criteria.lab_title,
        total_score=total_score,
        max_score=max_score,
        percentage=percentage,
        passed_count=passed_count,
        failed_count=failed_count,
        grade_letter=grade_letter,
        results=rule_results,
        topology=student_topology
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_evaluator.py`
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add src/evaluator.py tests/test_evaluator.py
git commit -m "feat(evaluator): implement flexible hostnames, Auto-MDIX cabling, OSPF process ID and security grading"
```

---

### Task 6: API Policy Parameters & Criteria Endpoints Integration

**Files:**
- Modify: `src/app.py:175-205`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: HTTP POST `/api/criteria/generate` with policy form fields / JSON payload.
- Produces: JSON response with `criteria` containing instantiated `policies`.

- [ ] **Step 1: Write failing tests in `tests/test_app.py`**

```python
# Add to tests/test_app.py
def test_api_generate_criteria_with_policy_form_data():
    import os
    trial_xml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cisco-pka-to-xml", "trial.xml")
    with open(trial_xml_path, "rb") as f:
        xml_content = f.read()

    response = client.post(
        "/api/criteria/generate",
        files=[("files", ("trial.xml", xml_content, "application/xml"))],
        data={
            "lab_title": "Dynamic Subnetting Campus Lab",
            "total_points": 100.0,
            "allow_dynamic_subnetting": "true",
            "enforce_prefix_length": "true",
            "allow_custom_hostnames": "true",
            "strict_cable_type": "false",
            "grade_security_baseline": "true"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "criteria" in data
    criteria = data["criteria"]
    policies = criteria["policies"]
    assert policies["allow_dynamic_subnetting"] is True
    assert policies["allow_custom_hostnames"] is True
    assert policies["strict_cable_type"] is False
    assert policies["grade_security_baseline"] is True
    assert "DYNAMIC & RELATIONAL SUBNETTING POLICY" in data["instructions_txt"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_app.py -k test_api_generate_criteria_with_policy_form_data`
Expected: FAIL (`allow_dynamic_subnetting` ignored or not present in criteria response).

- [ ] **Step 3: Update `src/app.py`**

```python
# src/app.py around line 175
from src.models import EvaluationPolicies

@app.post("/api/criteria/generate")
async def api_generate_criteria(
    files: list[UploadFile] = File(...),
    lab_title: str = Form("Packet Tracer Lab Assignment"),
    lab_description: str = Form(""),
    total_points: float = Form(100.0),
    allow_dynamic_subnetting: bool = Form(False),
    enforce_prefix_length: bool = Form(True),
    verify_default_gateways: bool = Form(True),
    allow_custom_hostnames: bool = Form(False),
    strict_port_matching: bool = Form(True),
    strict_cable_type: bool = Form(True),
    allow_flexible_process_ids: bool = Form(True),
    grade_security_baseline: bool = Form(False),
    grade_interface_descriptions: bool = Form(False)
):
    """
    Teacher Studio: Ingests an instructor's reference Packet Tracer file (.pkt/.xml)
    or gold-standard configuration bundle, extracts grading rules according to policies, and generates instructions.txt.
    """
    topology = await parse_uploaded_files_to_topology(files)
    if not topology.devices:
        raise HTTPException(status_code=400, detail="No valid device configurations or topology discovered from reference file.")

    policies = EvaluationPolicies(
        allow_dynamic_subnetting=allow_dynamic_subnetting,
        enforce_prefix_length=enforce_prefix_length,
        verify_default_gateways=verify_default_gateways,
        allow_custom_hostnames=allow_custom_hostnames,
        strict_port_matching=strict_port_matching,
        strict_cable_type=strict_cable_type,
        allow_flexible_process_ids=allow_flexible_process_ids,
        grade_security_baseline=grade_security_baseline,
        grade_interface_descriptions=grade_interface_descriptions
    )

    criteria = generate_criteria_from_topology(
        topology=topology,
        lab_title=lab_title,
        lab_description=lab_description,
        target_total_points=total_points,
        policies=policies
    )
    instructions_txt = format_criteria_to_instructions_txt(criteria)

    return {
        "criteria": criteria,
        "instructions_txt": instructions_txt,
        "topology": topology
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_app.py`
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add src/app.py tests/test_app.py
git commit -m "feat(api): add policy parameters to criteria generate endpoint"
```

---

### Task 7: Instructor Studio UI Policy Control Center & Scorecard Updates

**Files:**
- Modify: `templates/index.html:140-165`
- Modify: `static/css/style.css`
- Modify: `static/js/app.js`

**Interfaces:**
- Produces: 3 grouped policy cards in Teacher Studio (`#panel-mode-teacher`):
  1. 🌐 IP & Subnetting Policies
  2. 🗺️ Topology & Hardware Policies
  3. ⚙️ Routing & Security Policies
- Produces: JavaScript form submission collecting all 9 policy toggles.
- Produces: Policy summary badge indicators in instructions preview and grading scorecard.

- [ ] **Step 1: Update `templates/index.html`**

Insert the Policy Control Center into `#panel-mode-teacher` before the upload dropzone:

```html
<!-- Inside templates/index.html inside #teacher-gen-form -->
<div class="policy-control-panel">
    <div class="policy-panel-header">
        <span class="policy-header-title">🛡️ Instructor Grading Strictness & Policies</span>
        <span class="policy-badge-info">Deterministic & Offline</span>
    </div>
    
    <div class="policy-grid">
        <!-- Group 1: IP & Subnetting -->
        <div class="policy-group-card">
            <div class="policy-group-title">🌐 IP & Subnetting Policies</div>
            <label class="toggle-control">
                <input type="checkbox" id="policy-allow-dynamic-subnetting">
                <span class="toggle-slider"></span>
                <span class="toggle-label">
                    <strong>Allow Dynamic Subnetting</strong>
                    <small>Permit custom IP schemes; checks mutual link subnets & host uniqueness</small>
                </span>
            </label>
            <label class="toggle-control">
                <input type="checkbox" id="policy-enforce-prefix-length" checked>
                <span class="toggle-slider"></span>
                <span class="toggle-label">
                    <strong>Enforce Prefix Length</strong>
                    <small>Requires custom subnets to match required CIDR (/30, /24)</small>
                </span>
            </label>
            <label class="toggle-control">
                <input type="checkbox" id="policy-verify-default-gateways" checked>
                <span class="toggle-slider"></span>
                <span class="toggle-label">
                    <strong>Verify Default Gateways</strong>
                    <small>Ensures PC/Switch gateway matches connected router interface</small>
                </span>
            </label>
        </div>

        <!-- Group 2: Topology & Hardware -->
        <div class="policy-group-card">
            <div class="policy-group-title">🗺️ Topology & Hardware Policies</div>
            <label class="toggle-control">
                <input type="checkbox" id="policy-allow-custom-hostnames">
                <span class="toggle-slider"></span>
                <span class="toggle-label">
                    <strong>Allow Custom Hostnames</strong>
                    <small>Matches devices by topological role & degree if name differs</small>
                </span>
            </label>
            <label class="toggle-control">
                <input type="checkbox" id="policy-strict-port-matching" checked>
                <span class="toggle-slider"></span>
                <span class="toggle-label">
                    <strong>Strict Port Matching</strong>
                    <small>Require exact interface numbers vs same speed class</small>
                </span>
            </label>
            <label class="toggle-control">
                <input type="checkbox" id="policy-strict-cable-type" checked>
                <span class="toggle-slider"></span>
                <span class="toggle-label">
                    <strong>Strict Cable Type</strong>
                    <small>Enforce exact Straight-Through vs Cross-Over vs Auto-MDIX</small>
                </span>
            </label>
        </div>

        <!-- Group 3: Routing & Security -->
        <div class="policy-group-card">
            <div class="policy-group-title">⚙️ Routing & Security Policies</div>
            <label class="toggle-control">
                <input type="checkbox" id="policy-allow-flexible-process-ids" checked>
                <span class="toggle-slider"></span>
                <span class="toggle-label">
                    <strong>Flexible OSPF Process IDs</strong>
                    <small>Accept any local process ID if Area 0 & networks match</small>
                </span>
            </label>
            <label class="toggle-control">
                <input type="checkbox" id="policy-grade-security-baseline">
                <span class="toggle-slider"></span>
                <span class="toggle-label">
                    <strong>Grade Security Baseline</strong>
                    <small>Verify enable secret, service password-encryption, line vty</small>
                </span>
            </label>
            <label class="toggle-control">
                <input type="checkbox" id="policy-grade-interface-descriptions">
                <span class="toggle-slider"></span>
                <span class="toggle-label">
                    <strong>Grade Interface Descriptions</strong>
                    <small>Require descriptive labels on active links</small>
                </span>
            </label>
        </div>
    </div>
</div>
```

- [ ] **Step 2: Add styling to `static/css/style.css`**

```css
/* Policy Control Center Styling */
.policy-control-panel {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 14px;
    margin-bottom: 16px;
}
.policy-panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border-color);
}
.policy-header-title {
    font-weight: 600;
    font-size: 0.95rem;
    color: var(--text-primary);
}
.policy-badge-info {
    font-size: 0.72rem;
    background: rgba(34, 197, 94, 0.15);
    color: #22c55e;
    padding: 2px 8px;
    border-radius: 12px;
    font-weight: 500;
}
.policy-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 12px;
}
.policy-group-card {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    padding: 10px;
    display: flex;
    flex-direction: column;
    gap: 8px;
}
.policy-group-title {
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}
.toggle-control {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    cursor: pointer;
    font-size: 0.85rem;
    user-select: none;
}
.toggle-control input {
    display: none;
}
.toggle-slider {
    position: relative;
    width: 34px;
    height: 18px;
    background-color: #4b5563;
    border-radius: 20px;
    transition: 0.2s;
    flex-shrink: 0;
    margin-top: 2px;
}
.toggle-slider:before {
    position: absolute;
    content: "";
    height: 12px;
    width: 12px;
    left: 3px;
    bottom: 3px;
    background-color: white;
    border-radius: 50%;
    transition: 0.2s;
}
.toggle-control input:checked + .toggle-slider {
    background-color: #3b82f6;
}
.toggle-control input:checked + .toggle-slider:before {
    transform: translateX(16px);
}
.toggle-label {
    display: flex;
    flex-direction: column;
    line-height: 1.25;
}
.toggle-label strong {
    font-size: 0.82rem;
    color: var(--text-primary);
}
.toggle-label small {
    font-size: 0.72rem;
    color: var(--text-secondary);
    margin-top: 2px;
}
```

- [ ] **Step 3: Update `static/js/app.js`**

In `static/js/app.js`, when gathering data in `#teacher-generate-btn` handler, read the policy toggles and append them to FormData:

```javascript
// In static/js/app.js inside handleTeacherGenerate()
formData.append("allow_dynamic_subnetting", document.getElementById("policy-allow-dynamic-subnetting")?.checked ? "true" : "false");
formData.append("enforce_prefix_length", document.getElementById("policy-enforce-prefix-length")?.checked ? "true" : "false");
formData.append("verify_default_gateways", document.getElementById("policy-verify-default-gateways")?.checked ? "true" : "false");
formData.append("allow_custom_hostnames", document.getElementById("policy-allow-custom-hostnames")?.checked ? "true" : "false");
formData.append("strict_port_matching", document.getElementById("policy-strict-port-matching")?.checked ? "true" : "false");
formData.append("strict_cable_type", document.getElementById("policy-strict-cable-type")?.checked ? "true" : "false");
formData.append("allow_flexible_process_ids", document.getElementById("policy-allow-flexible-process-ids")?.checked ? "true" : "false");
formData.append("grade_security_baseline", document.getElementById("policy-grade-security-baseline")?.checked ? "true" : "false");
formData.append("grade_interface_descriptions", document.getElementById("policy-grade-interface-descriptions")?.checked ? "true" : "false");
```

- [ ] **Step 4: Commit UI changes**

```bash
git add templates/index.html static/css/style.css static/js/app.js
git commit -m "feat(ui): add responsive Instructor Policy Control Center with switches and styling"
```

---

### Task 8: Comprehensive End-to-End Regression & Live Verification

**Files:**
- Create: `tests/test_e2e_policies.py`
- Test: `tests/test_e2e_policies.py`

**Interfaces:**
- Verifies complete flow from teacher generating dynamic criteria with policies, to student submitting custom topologies, validating 100% score calculation and accurate itemized feedback.

- [ ] **Step 1: Write `tests/test_e2e_policies.py`**

```python
# tests/test_e2e_policies.py
import os
import pytest
from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)

def test_full_policy_generation_and_grading_flow():
    trial_xml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cisco-pka-to-xml", "trial.xml")
    if not os.path.exists(trial_xml_path):
        pytest.skip("trial.xml not available")

    with open(trial_xml_path, "rb") as f:
        xml_bytes = f.read()

    # 1. Instructor generates rubric with dynamic subnetting and flexible cabling enabled
    gen_res = client.post(
        "/api/criteria/generate",
        files=[("files", ("trial.xml", xml_bytes, "application/xml"))],
        data={
            "lab_title": "Advanced CCNA Dynamic Lab",
            "total_points": 100.0,
            "allow_dynamic_subnetting": "true",
            "enforce_prefix_length": "true",
            "strict_cable_type": "false"
        }
    )
    assert gen_res.status_code == 200
    gen_json = gen_res.json()
    instructions_txt = gen_json["instructions_txt"]
    assert "Dynamic Subnetting : ENABLED" in instructions_txt or "DYNAMIC & RELATIONAL SUBNETTING POLICY" in instructions_txt

    # 2. Student submits reference topology
    eval_res = client.post(
        "/api/evaluate",
        files=[
            ("instructions_file", ("instructions.txt", instructions_txt.encode("utf-8"), "text/plain")),
            ("student_files", ("student_trial.xml", xml_bytes, "application/xml"))
        ]
    )
    assert eval_res.status_code == 200
    eval_json = eval_res.json()
    assert eval_json["percentage"] == 100.0
    assert eval_json["grade_letter"] in ("A", "A+")
    assert eval_json["failed_count"] == 0

    # Ensure relational subnet results are present
    rel_results = [r for r in eval_json["results"] if r["category"] == "relational_subnet"]
    assert len(rel_results) > 0
    for r in rel_results:
        assert r["passed"] is True
```

- [ ] **Step 2: Run all tests to verify 100% pass rate**

Run: `pytest -v tests/test_models.py tests/test_parsers.py tests/test_criteria_generator.py tests/test_evaluator.py tests/test_app.py tests/test_e2e_policies.py`
Expected: PASS (all tests pass).

- [ ] **Step 3: Commit full test suite**

```bash
git add tests/test_e2e_policies.py
git commit -m "test(e2e): add comprehensive policy generation and relational grading verification test"
```

---

## Self-Review Checklist

1. **Spec Coverage**:
   - `EvaluationPolicies` 9 toggles defined in `src/models.py` (Section 2.1) -> Task 1.
   - Dual-format output and policy summary in `src/criteria_generator.py` (Section 3.2) -> Task 3.
   - Dynamic subnet validation algorithm with mutual CIDR, uniqueness, conflict resistance, and default gateway check (Section 4.1) -> Task 4.
   - Flexible hostnames, Auto-MDIX cabling, and flexible OSPF process IDs (Section 4) -> Task 5.
   - Instructor Studio Policy Control Center with 3 grouped toggle categories in UI (Section 5.1) -> Tasks 6 & 7.
   - Deterministic verification tests matching all test cases in Section 6 -> Tasks 1-5, 8.
2. **Placeholder Scan**: No `TBD`, `TODO`, or placeholder comments. Every step includes complete executable code.
3. **Type Consistency**: `EvaluationPolicies`, `EvaluationCriteria`, `EvaluationRule`, and `RuleResult` models match across all tasks.
