# Network Configuration Evaluation & Topology Discovery Tool Implementation Plan

> [!NOTE]
> **Historical record — partially superseded (as of 2026-09-20).**
> This plan is kept as written for the project record. Two items no longer
> describe the shipped system:
> - **Task 6 (Built-in Demo Scenarios)** was removed. `src/presets.py`, the
>   `/api/presets` endpoints and the Showcase Demo Scenarios panel no longer
>   exist. The three configuration bundles live on as `tests/fixtures.py`.
> - The `.txt` / `.zip` bundle is no longer the only input. Packet Tracer
>   `.pkt` / `.pka` / `.xml` files can be uploaded directly
>   (see the 2026-09-08 design spec).
>
> See `docs/DEVELOPMENT_LOG.md` for the current state.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone, test-driven Python 3 + FastAPI web application that ingests Cisco command output bundles (`.txt`/`.zip`), performs multi-signal probabilistic topology discovery (Noisy-OR), detects cross-device relational conflicts with evidence line citations, and renders an interactive visual topology map with 1-click demo presets.

**Architecture:** A modular Python pipeline starting with input normalization and regex section splitting, parsing raw Cisco outputs into typed Pydantic models, fusing Layer 2 and Layer 3 evidence into confidence-rated network graph edges, running relational sanity checks, and serving interactive Canvas/SVG graph visuals via FastAPI + Jinja2 + Vanilla JS/CSS.

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, Pydantic v2, Jinja2, Pytest, Vanilla HTML5/CSS3/JavaScript (Vis.js Network).

## Global Constraints
- Python 3.11+ standard library + FastAPI + Pydantic v2 + Uvicorn + Jinja2 + pytest.
- Zero external database required (purely stateless in-memory processing).
- No frontend build steps / npm / React / Vue (pure server-rendered Jinja2 + vanilla client JS/CSS).
- All discovered links must include exact contributing signals and mathematical confidence scores.
- All detected conflicts must include file and line-number evidence citations.
- All development steps must be logged to `docs/DEVELOPMENT_LOG.md`.

---

### Task 1: Environment Setup, Dependencies & Pydantic Data Models

**Files:**
- Create: `requirements.txt`
- Create: `src/__init__.py`
- Create: `src/models.py`
- Create: `tests/__init__.py`
- Create: `tests/test_models.py`

**Interfaces:**
- Produces: `InterfaceData`, `CDPNeighbor`, `RouteEntry`, `MACTableEntry`, `ParsedDevice`, `ContributingSignal`, `DiscoveredLink`, `ConflictIssue`, `TopologyResult`

- [ ] **Step 1: Create `requirements.txt` and install dependencies**
```
fastapi>=0.110.0
uvicorn>=0.29.0
pydantic>=2.6.0
jinja2>=3.1.3
python-multipart>=0.0.9
pytest>=8.0.0
httpx>=0.27.0
```

- [ ] **Step 2: Write failing unit test for Pydantic models**
```python
# tests/test_models.py
from src.models import InterfaceData, ParsedDevice, DiscoveredLink, ContributingSignal, ConflictIssue

def test_interface_and_device_model():
    intf = InterfaceData(
        name="GigabitEthernet0/0",
        ip_address="192.168.1.1",
        subnet_mask="255.255.255.252",
        cidr=30,
        network_address="192.168.1.0",
        admin_status="up",
        line_status="up"
    )
    device = ParsedDevice(
        hostname="R1",
        canonical_name="R1",
        device_type="router",
        raw_filename="R1.txt",
        interfaces={"GigabitEthernet0/0": intf}
    )
    assert device.hostname == "R1"
    assert device.interfaces["GigabitEthernet0/0"].cidr == 30

def test_discovered_link_model():
    signal = ContributingSignal(
        signal_type="CDP_NEIGHBOR_DETAIL",
        description="Explicit CDP neighbor match",
        weight=1.0,
        evidence=["R1.txt line 45"]
    )
    link = DiscoveredLink(
        source_device="R1",
        source_interface="GigabitEthernet0/0",
        target_device="R2",
        target_interface="GigabitEthernet0/0",
        confidence=1.0,
        classification="verified",
        signals=[signal],
        is_bidirectional=True
    )
    assert link.confidence == 1.0
    assert link.classification == "verified"
```

- [ ] **Step 3: Run test to verify it fails**
Run: `pytest tests/test_models.py`
Expected: ModuleNotFoundError / ImportError.

- [ ] **Step 4: Implement `src/models.py`**
```python
# src/models.py
from typing import Literal
from pydantic import BaseModel, Field

class InterfaceData(BaseModel):
    name: str
    ip_address: str | None = None
    subnet_mask: str | None = None
    cidr: int | None = None
    network_address: str | None = None
    admin_status: str = "up"
    line_status: str = "up"
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
    protocol: str  # C, S, O, D, etc.
    next_hop: str | None = None
    outgoing_interface: str | None = None
    metric: int | None = None
    evidence_line: int | None = None

class MACTableEntry(BaseModel):
    vlan: int
    mac_address: str
    entry_type: str  # DYNAMIC / STATIC
    port: str
    evidence_line: int | None = None

class ParsedDevice(BaseModel):
    hostname: str
    canonical_name: str
    device_type: Literal["router", "switch", "l3_switch", "host"] = "router"
    raw_filename: str
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
    devices: dict[str, ParsedDevice]
    links: list[DiscoveredLink]
    conflicts: list[ConflictIssue]
```

- [ ] **Step 5: Run test to verify it passes**
Run: `pytest tests/test_models.py`
Expected: 2 passed.

- [ ] **Step 6: Commit changes and update `docs/DEVELOPMENT_LOG.md`**
```bash
git add requirements.txt src/ tests/ docs/DEVELOPMENT_LOG.md
git commit -m "feat(models): define Pydantic schemas for devices, links, signals, and conflicts"
```

---

### Task 2: Section Tokenizer & Terminal Output Sanitizer

**Files:**
- Create: `src/sanitizer.py`
- Create: `tests/test_sanitizer.py`

**Interfaces:**
- Produces: `sanitize_terminal_output(raw_text: str) -> str`, `split_command_sections(raw_text: str) -> dict[str, tuple[str, int]]`

- [ ] **Step 1: Write failing unit test for sanitizer and section splitter**
```python
# tests/test_sanitizer.py
from src.sanitizer import sanitize_terminal_output, split_command_sections

def test_sanitize_terminal_output():
    noisy = "Router# show running-config\r\nBuilding configuration...\r\n --More-- \r\nhostname R1\r\n"
    clean = sanitize_terminal_output(noisy)
    assert "--More--" not in clean
    assert "hostname R1" in clean

def test_split_command_sections():
    raw_bundle = """
    R1# show running-config
    hostname R1
    interface GigabitEthernet0/0
     ip address 10.0.0.1 255.255.255.252
    R1# show cdp neighbors detail
    Device ID: R2
    Entry address(es):
      IP address: 10.0.0.2
    Interface: GigabitEthernet0/0,  Port ID (outgoing port): GigabitEthernet0/0
    """
    sections = split_command_sections(raw_bundle)
    assert "show running-config" in sections
    assert "show cdp neighbors detail" in sections
    content, line_offset = sections["show running-config"]
    assert "hostname R1" in content
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_sanitizer.py`
Expected: FAIL.

- [ ] **Step 3: Implement `src/sanitizer.py`**
```python
# src/sanitizer.py
import re

COMMAND_PATTERNS = {
    "show running-config": re.compile(r"^(?:[a-zA-Z0-9_\-\.\(\)]+[>#]\s*)?show\s+run(?:ning-config)?.*$", re.IGNORECASE | re.MULTILINE),
    "show cdp neighbors detail": re.compile(r"^(?:[a-zA-Z0-9_\-\.\(\)]+[>#]\s*)?show\s+cdp\s+neigh(?:bors)?(?:\s+detail)?.*$", re.IGNORECASE | re.MULTILINE),
    "show ip interface brief": re.compile(r"^(?:[a-zA-Z0-9_\-\.\(\)]+[>#]\s*)?show\s+ip\s+int(?:erface)?\s+br(?:ief)?.*$", re.IGNORECASE | re.MULTILINE),
    "show ip route": re.compile(r"^(?:[a-zA-Z0-9_\-\.\(\)]+[>#]\s*)?show\s+ip\s+route.*$", re.IGNORECASE | re.MULTILINE),
    "show vlan brief": re.compile(r"^(?:[a-zA-Z0-9_\-\.\(\)]+[>#]\s*)?show\s+vlan(?:\s+br(?:ief)?)?.*$", re.IGNORECASE | re.MULTILINE),
    "show interfaces trunk": re.compile(r"^(?:[a-zA-Z0-9_\-\.\(\)]+[>#]\s*)?show\s+int(?:erfaces)?\s+trunk.*$", re.IGNORECASE | re.MULTILINE),
    "show mac address-table": re.compile(r"^(?:[a-zA-Z0-9_\-\.\(\)]+[>#]\s*)?show\s+mac(?:\s+address-table)?.*$", re.IGNORECASE | re.MULTILINE),
}

def sanitize_terminal_output(raw_text: str) -> str:
    cleaned = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"--\s*More\s*--(?:\x08|\s)*", "", cleaned)
    cleaned = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", cleaned)
    return cleaned

def split_command_sections(raw_text: str) -> dict[str, tuple[str, int]]:
    sanitized = sanitize_terminal_output(raw_text)
    lines = sanitized.splitlines()
    matches = []
    
    for idx, line in enumerate(lines, start=1):
        for cmd_name, pattern in COMMAND_PATTERNS.items():
            if pattern.match(line.strip()):
                matches.append((idx, cmd_name))
                break

    if not matches:
        # If no explicit command headers found, treat entire file as running-config
        return {"show running-config": (sanitized, 1)}

    sections = {}
    for i in range(len(matches)):
        start_line, cmd = matches[i]
        end_line = matches[i+1][0] - 1 if i + 1 < len(matches) else len(lines)
        section_content = "\n".join(lines[start_line:end_line])
        sections[cmd] = (section_content, start_line + 1)
    
    return sections
```

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_sanitizer.py`
Expected: 2 passed.

- [ ] **Step 5: Commit changes and update `docs/DEVELOPMENT_LOG.md`**

---

### Task 3: Cisco Command Parsers (Running Config, CDP, Interfaces, Routing, VLANs/Trunks, MAC)

**Files:**
- Create: `src/parsers.py`
- Create: `tests/test_parsers.py`

**Interfaces:**
- Produces: `parse_device_bundle(raw_text: str, filename: str) -> ParsedDevice`

- [ ] **Step 1: Write failing unit test for parser functions**
```python
# tests/test_parsers.py
from src.parsers import parse_device_bundle

SAMPLE_R1 = """
R1# show running-config
hostname R1
!
interface GigabitEthernet0/0
 description Link to R2
 ip address 10.0.0.1 255.255.255.252
!
interface GigabitEthernet0/1
 ip address 192.168.1.1 255.255.255.0
!
router ospf 1
 network 10.0.0.0 0.0.0.3 area 0
 network 192.168.1.0 0.0.0.255 area 0
!
R1# show cdp neighbors detail
-------------------------
Device ID: R2.lab.local
Entry address(es): 
  IP address: 10.0.0.2
Platform: Cisco 2901,  Capabilities: Router
Interface: GigabitEthernet0/0,  Port ID (outgoing port): GigabitEthernet0/0
!
R1# show ip interface brief
Interface              IP-Address      OK? Method Status                Protocol
GigabitEthernet0/0     10.0.0.1        YES manual up                    up      
GigabitEthernet0/1     192.168.1.1     YES manual up                    up      
!
R1# show ip route
Gateway of last resort is not set
C    10.0.0.0/30 is directly connected, GigabitEthernet0/0
O    10.0.0.4/30 [110/2] via 10.0.0.2, 00:05:12, GigabitEthernet0/0
"""

def test_parse_r1_bundle():
    device = parse_device_bundle(SAMPLE_R1, "R1.txt")
    assert device.hostname == "R1"
    assert device.canonical_name == "R1"
    assert device.device_type == "router"
    assert "GigabitEthernet0/0" in device.interfaces
    
    gi0 = device.interfaces["GigabitEthernet0/0"]
    assert gi0.ip_address == "10.0.0.1"
    assert gi0.cidr == 30
    assert gi0.network_address == "10.0.0.0"
    assert gi0.admin_status == "up"
    assert gi0.line_status == "up"
    
    assert len(device.cdp_neighbors) == 1
    cdp = device.cdp_neighbors[0]
    assert cdp.device_id == "R2"
    assert cdp.local_interface == "GigabitEthernet0/0"
    assert cdp.remote_interface == "GigabitEthernet0/0"
    
    assert len(device.routes) >= 2
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_parsers.py`
Expected: FAIL.

- [ ] **Step 3: Implement `src/parsers.py`**
Implement complete parser handlers:
- `parse_running_config(content: str, start_line: int, device: ParsedDevice)`
- `parse_cdp_detail(content: str, start_line: int, device: ParsedDevice)`
- `parse_ip_int_brief(content: str, start_line: int, device: ParsedDevice)`
- `parse_ip_route(content: str, start_line: int, device: ParsedDevice)`
- `parse_vlan_brief(content: str, start_line: int, device: ParsedDevice)`
- `parse_interfaces_trunk(content: str, start_line: int, device: ParsedDevice)`
- `parse_mac_table(content: str, start_line: int, device: ParsedDevice)`
- Canonical name helper (`normalize_interface_name`, `canonical_device_name`).

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_parsers.py`
Expected: PASS.

- [ ] **Step 5: Commit changes and update `docs/DEVELOPMENT_LOG.md`**

---

### Task 4: Multi-Signal Fusion & Topology Graph Inference Engine

**Files:**
- Create: `src/fusion_engine.py`
- Create: `tests/test_fusion_engine.py`

**Interfaces:**
- Produces: `infer_topology_links(devices: dict[str, ParsedDevice]) -> list[DiscoveredLink]`, `calculate_noisy_or(weights: list[float]) -> float`

- [ ] **Step 1: Write failing unit test for Noisy-OR calculation and multi-signal fusion**
```python
# tests/test_fusion_engine.py
from src.fusion_engine import calculate_noisy_or, infer_topology_links
from src.parsers import parse_device_bundle

def test_noisy_or_math():
    # Single weight
    assert calculate_noisy_or([0.90]) == 0.90
    # Two weights (0.90 and 0.80) -> 1 - (0.10 * 0.20) = 0.98
    assert round(calculate_noisy_or([0.90, 0.80]), 4) == 0.98

def test_infer_links_between_two_routers():
    r1_raw = """
    hostname R1
    interface GigabitEthernet0/0
     ip address 10.0.0.1 255.255.255.252
    show cdp neighbors detail
    Device ID: R2
    Interface: GigabitEthernet0/0,  Port ID (outgoing port): GigabitEthernet0/0
    """
    r2_raw = """
    hostname R2
    interface GigabitEthernet0/0
     ip address 10.0.0.2 255.255.255.252
    show cdp neighbors detail
    Device ID: R1
    Interface: GigabitEthernet0/0,  Port ID (outgoing port): GigabitEthernet0/0
    """
    d1 = parse_device_bundle(r1_raw, "R1.txt")
    d2 = parse_device_bundle(r2_raw, "R2.txt")
    devices = {"R1": d1, "R2": d2}
    
    links = infer_topology_links(devices)
    assert len(links) == 1
    link = links[0]
    assert link.confidence >= 0.95
    assert link.classification == "verified"
    assert any(s.signal_type == "CDP_NEIGHBOR_DETAIL" for s in link.signals)
    assert any(s.signal_type == "P2P_SUBNET_30_31" for s in link.signals)
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_fusion_engine.py`
Expected: FAIL.

- [ ] **Step 3: Implement `src/fusion_engine.py`**
Implement the multi-signal weights:
- `CDP_NEIGHBOR_DETAIL` = 1.0
- `OSPF_NEIGHBOR_FULL` = 0.95
- `P2P_SUBNET_30_31` = 0.90
- `ROUTER_ON_A_STICK_VLAN` = 0.85
- `TRUNK_CONFIG_PAIR` = 0.80
- `NEXT_HOP_ROUTING_MATCH` = 0.75
- `MAC_TABLE_UPLINK` = 0.70
- `SHARED_SUBNET_24` = 0.35
- `DESCRIPTION_HINT` = 0.25
Aggregate matching candidates and compute final link confidence and bidirectional status.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_fusion_engine.py`
Expected: PASS.

- [ ] **Step 5: Commit changes and update `docs/DEVELOPMENT_LOG.md`**

---

### Task 5: Relational Cross-Device Conflict & Anomaly Detector

**Files:**
- Create: `src/conflict_detector.py`
- Create: `tests/test_conflict_detector.py`

**Interfaces:**
- Produces: `detect_conflicts(devices: dict[str, ParsedDevice], links: list[DiscoveredLink]) -> list[ConflictIssue]`

- [ ] **Step 1: Write failing unit test for conflict detection**
```python
# tests/test_conflict_detector.py
from src.conflict_detector import detect_conflicts
from src.parsers import parse_device_bundle
from src.fusion_engine import infer_topology_links

def test_detect_subnet_mismatch_and_down_interface():
    # R1 and R2 physically linked via CDP, but R1 is 192.168.1.1/24 and R2 is 192.168.2.2/24
    r1_txt = """
    hostname R1
    interface GigabitEthernet0/0
     ip address 192.168.1.1 255.255.255.0
    show cdp neighbors detail
    Device ID: R2
    Interface: GigabitEthernet0/0,  Port ID (outgoing port): GigabitEthernet0/0
    show ip interface brief
    GigabitEthernet0/0 192.168.1.1 YES manual administratively down down
    """
    r2_txt = """
    hostname R2
    interface GigabitEthernet0/0
     ip address 192.168.2.2 255.255.255.0
    show cdp neighbors detail
    Device ID: R1
    Interface: GigabitEthernet0/0,  Port ID (outgoing port): GigabitEthernet0/0
    show ip interface brief
    GigabitEthernet0/0 192.168.2.2 YES manual up up
    """
    d1 = parse_device_bundle(r1_txt, "R1.txt")
    d2 = parse_device_bundle(r2_txt, "R2.txt")
    devices = {"R1": d1, "R2": d2}
    links = infer_topology_links(devices)
    
    conflicts = detect_conflicts(devices, links)
    categories = [c.category for c in conflicts]
    assert "subnet_mismatch" in categories
    assert "interface_down" in categories
    assert any("R1.txt" in cit for c in conflicts for cit in c.evidence_citations)
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_conflict_detector.py`
Expected: FAIL.

- [ ] **Step 3: Implement `src/conflict_detector.py`**
Implement checks for:
1. `subnet_mismatch` on connected physical interfaces.
2. `interface_down` / `admin_down` (Cabling error / missing `no shutdown`).
3. `duplicate_ip` across entire network.
4. `vlan_trunk_mismatch` (native VLAN or allowed VLAN mismatch on connected switchports).
5. `missing_route_nexthop` (static route next-hop unreachable).

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_conflict_detector.py`
Expected: PASS.

- [ ] **Step 5: Commit changes and update `docs/DEVELOPMENT_LOG.md`**

---

### Task 6: Built-in Demo Scenarios & Fixtures Generator

**Files:**
- Create: `src/presets.py`
- Create: `tests/test_presets.py`

**Interfaces:**
- Produces: `get_available_presets() -> list[dict]`, `load_preset(preset_id: str) -> dict[str, str]`

- [ ] **Step 1: Write failing unit test for demo presets**
```python
# tests/test_presets.py
from src.presets import get_available_presets, load_preset

def test_presets_exist():
    presets = get_available_presets()
    assert len(presets) >= 3
    ids = [p["id"] for p in presets]
    assert "ospf_clean" in ids
    assert "subnet_cabling_error" in ids
    assert "vlan_trunk_mismatch" in ids

def test_load_preset_content():
    files = load_preset("ospf_clean")
    assert len(files) >= 2
    assert any("hostname" in content for content in files.values())
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_presets.py`
Expected: FAIL.

- [ ] **Step 3: Implement `src/presets.py`**
Embed rich mock Cisco command bundle outputs for 3 distinct educational showcase labs:
1. `ospf_clean`: 3 Routers (R1, R2, R3) in OSPF Ring/Triangle with full convergence.
2. `subnet_cabling_error`: R1 <-> R2 with mismatched subnet masks and `administratively down` on R1 Gi0/0.
3. `vlan_trunk_mismatch`: SW1 <-> SW2 with Native VLAN mismatch (VLAN 1 vs VLAN 99) and allowed VLAN exclusions.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_presets.py`
Expected: PASS.

- [ ] **Step 5: Commit changes and update `docs/DEVELOPMENT_LOG.md`**

---

### Task 7: FastAPI Web Application & Interactive Topology Visualizer

**Files:**
- Create: `src/app.py`
- Create: `templates/index.html`
- Create: `static/css/style.css`
- Create: `static/js/app.js`
- Create: `tests/test_app.py`

**Interfaces:**
- Endpoints:
  - `GET /`: Serves main Jinja2 interface.
  - `POST /api/analyze`: Accepts multi-file upload (`.txt`/`.zip`), returns `TopologyResult` JSON.
  - `GET /api/presets`: Returns list of preset demo scenarios.
  - `GET /api/presets/{preset_id}`: Loads and runs analysis directly on preset scenario.

- [ ] **Step 1: Write failing unit test for FastAPI API endpoints**
```python
# tests/test_app.py
from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)

def test_index_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "Network Configuration Evaluation" in response.text

def test_preset_api():
    response = client.get("/api/presets")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3

def test_analyze_preset():
    response = client.get("/api/presets/ospf_clean")
    assert response.status_code == 200
    result = response.json()
    assert "devices" in result
    assert "links" in result
    assert "conflicts" in result
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_app.py`
Expected: FAIL.

- [ ] **Step 3: Implement `src/app.py`, `templates/index.html`, `static/css/style.css`, and `static/js/app.js`**
Build a polished, modern dark-mode responsive web interface:
- File dropzone with instant multi-file preview.
- Preset scenario buttons for instant 1-click loading.
- Interactive Force-Directed Canvas / Vis.js network graph with color-coded nodes (Routers = Blue, Switches = Green, Hosts = Orange) and links (Verified = Green solid, Inferred = Amber dashed, Conflict = Red pulsing).
- Side drawer: clicking any node shows device details; clicking any edge displays the exact contributing signals, confidence math, and detected conflicts with line citations.
- Conflict & Anomaly summary panel.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_app.py`
Expected: PASS.

- [ ] **Step 5: Commit changes and update `docs/DEVELOPMENT_LOG.md`**

---

### Task 8: End-to-End Verification & Presentation Readiness Check

**Files:**
- Create: `tests/test_e2e.py`
- Modify: `docs/DEVELOPMENT_LOG.md`
- Create: `walkthrough.md` (Artifact)

- [ ] **Step 1: Run complete automated test suite**
Run: `pytest -v`
Expected: 100% tests pass across models, sanitizer, parsers, fusion, conflicts, presets, and web app.

- [ ] **Step 2: Launch server and verify interactive UI in browser**
Run: `uvicorn src.app:app --port 8000`
Verify drag-and-drop file analysis and 1-click presets in browser.

- [ ] **Step 3: Update documentation and commit all deliverables**
```bash
git add .
git commit -m "feat: complete standalone network topology discovery & diagnostic visualizer"
```
