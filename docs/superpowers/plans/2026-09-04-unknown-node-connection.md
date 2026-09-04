# Unknown Device Connection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect active connections to unparsed peers and unconnected up/up interfaces, connecting them to dedicated placeholder nodes labeled `???` in both the backend topology engine and the frontend visualizer.

**Architecture:** Extend `ParsedDevice` with placeholder metadata; update `fusion_engine.py` to synthesize unique placeholder devices for unparsed CDP/route neighbors and active standalone `up/up` interfaces; ensure `conflict_detector.py` treats placeholders safely; enhance `static/js/app.js` to render dashed `???` nodes with diagnostic drawer support.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, Pytest, Vanilla JavaScript (SVG Graph / D3-style custom physics).

## Global Constraints

- Never collapse multiple distinct unknown connections into a single shared node; each unconnected port attaches to its own unique placeholder node.
- Purely virtual interfaces (Loopback, Null) must not synthesize `???` links.
- All existing tests in `pytest` must continue to pass.

---

### Task 1: Extend Data Model with Placeholder Attributes

**Files:**
- Modify: `src/models.py:48-58`
- Test: `tests/test_models.py`

**Interfaces:**
- Produces: `ParsedDevice.is_placeholder: bool = False`, `ParsedDevice.display_name: str = ""`, `ParsedDevice.placeholder_for_device: str | None = None`, `ParsedDevice.placeholder_for_interface: str | None = None`, and `Literal["router", "switch", "l3_switch", "host", "unknown"]`.

- [ ] **Step 1: Write failing test in `tests/test_models.py`**

```python
def test_placeholder_parsed_device():
    dev = ParsedDevice(
        hostname="???",
        canonical_name="UNKNOWN_R1_Gi0/1",
        display_name="???",
        is_placeholder=True,
        device_type="unknown",
        placeholder_for_device="PLDT",
        placeholder_for_interface="GigabitEthernet0/1",
        raw_filename=""
    )
    assert dev.is_placeholder is True
    assert dev.display_name == "???"
    assert dev.device_type == "unknown"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -k test_placeholder_parsed_device`
Expected: FAIL (validation error / unknown field or invalid literal for `device_type`).

- [ ] **Step 3: Update `src/models.py`**

```python
class ParsedDevice(BaseModel):
    hostname: str
    canonical_name: str
    display_name: str = ""
    is_placeholder: bool = False
    placeholder_for_device: str | None = None
    placeholder_for_interface: str | None = None
    device_type: Literal["router", "switch", "l3_switch", "host", "unknown"] = "router"
    raw_filename: str = ""
    interfaces: dict[str, InterfaceData] = Field(default_factory=dict)
    cdp_neighbors: list[CDPNeighbor] = Field(default_factory=list)
    routes: list[RouteEntry] = Field(default_factory=list)
    mac_table: list[MACTableEntry] = Field(default_factory=list)
    vlans: dict[int, str] = Field(default_factory=dict)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py`
Expected: PASS (all tests pass).

- [ ] **Step 5: Commit changes**

```bash
git add src/models.py tests/test_models.py
git commit -m "feat(models): add placeholder fields and unknown device_type to ParsedDevice"
```

---

### Task 2: Implement Unknown Peer & Active Port Inference in `src/fusion_engine.py`

**Files:**
- Modify: `src/fusion_engine.py`
- Test: `tests/test_fusion_engine.py`

**Interfaces:**
- Consumes: `ParsedDevice`, `DiscoveredLink`, `ContributingSignal`, `SIGNAL_WEIGHTS`.
- Produces: `infer_topology_links(devices: dict[str, ParsedDevice]) -> list[DiscoveredLink]`, which mutates/augments `devices` with synthetic placeholder `ParsedDevice` entries.

- [ ] **Step 1: Write failing test in `tests/test_fusion_engine.py`**

```python
def test_infer_links_to_unknown_cdp_neighbor():
    r1_txt = """
    hostname R1
    interface GigabitEthernet0/0
     ip address 10.0.0.1 255.255.255.252
    show cdp neighbors detail
    Device ID: ISP_ROUTER
    Interface: GigabitEthernet0/0,  Port ID (outgoing port): GigabitEthernet0/1
    """
    d1 = parse_device_bundle(r1_txt, "R1.txt")
    devices = {"R1": d1}
    
    links = infer_topology_links(devices)
    # ISP_ROUTER was not uploaded; a placeholder node must be synthesized
    assert any(d.is_placeholder and d.display_name == "???" for d in devices.values())
    assert any(l.target_device.startswith("UNKNOWN_") or l.source_device.startswith("UNKNOWN_") for l in links)

def test_infer_links_to_active_unconnected_interface():
    r1_txt = """
    hostname R1
    interface GigabitEthernet0/1
     ip address 192.168.1.1 255.255.255.0
    show ip interface brief
    GigabitEthernet0/1     192.168.1.1     YES NVRAM  up                    up
    Loopback0              1.1.1.1         YES NVRAM  up                    up
    """
    d1 = parse_device_bundle(r1_txt, "R1.txt")
    devices = {"R1": d1}
    
    links = infer_topology_links(devices)
    # GigabitEthernet0/1 is up/up with no peer -> placeholder link generated
    # Loopback0 is virtual -> must NOT generate placeholder link
    carrier_links = [l for l in links if any(s.signal_type == "ACTIVE_PORT_CARRIER" for s in l.signals)]
    assert len(carrier_links) == 1
    assert carrier_links[0].source_interface == "GigabitEthernet0/1" or carrier_links[0].target_interface == "GigabitEthernet0/1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_fusion_engine.py -k "test_infer_links_to_unknown_cdp_neighbor or test_infer_links_to_active_unconnected_interface"`
Expected: FAIL.

- [ ] **Step 3: Implement unknown peer & active port synthesis in `src/fusion_engine.py`**

1. Add `"ACTIVE_PORT_CARRIER": 0.50` to `SIGNAL_WEIGHTS`.
2. In `infer_topology_links(devices: dict[str, ParsedDevice]) -> list[DiscoveredLink]`:
   - Keep track of known original devices vs placeholders.
   - For links referencing unparsed targets (target not in original `devices`):
     - Generate a unique device ID `UNKNOWN_PEER_{src_dev}_{src_intf}`.
     - Add a `ParsedDevice(hostname="???", canonical_name=dev_id, display_name="???", is_placeholder=True, device_type="unknown", placeholder_for_device=original_target, placeholder_for_interface=target_intf, raw_filename="")` to `devices[dev_id]`.
     - Update link to point to this `dev_id`.
   - Identify active interfaces on original devices where `admin_status == "up"` and `line_status == "up"`.
     - Exclude virtual interfaces: `name.lower().startswith(("loopback", "null"))` and down SVIs.
     - Check if `(dev.hostname, intf_name)` is present in any link.
     - If not:
       - Generate a unique ID `UNKNOWN_PORT_{dev.hostname}_{intf_name}`.
       - Add placeholder `ParsedDevice` to `devices`.
       - Add `DiscoveredLink` with `ACTIVE_PORT_CARRIER` signal (weight 0.50, classification `"inferred"`).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_fusion_engine.py`
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add src/fusion_engine.py tests/test_fusion_engine.py
git commit -m "feat(fusion): synthesize placeholder ??? nodes for unparsed peers and active ports"
```

---

### Task 3: Conflict Detector Safety for Placeholder Devices

**Files:**
- Modify: `src/conflict_detector.py`
- Test: `tests/test_conflict_detector.py`

**Interfaces:**
- Consumes: `devices: dict[str, ParsedDevice]`, `links: list[DiscoveredLink]`.
- Produces: `detect_conflicts(devices, links) -> list[ConflictIssue]`.

- [ ] **Step 1: Write test in `tests/test_conflict_detector.py`**

```python
def test_conflict_detector_ignores_placeholder_devices():
    # R1 connected to a placeholder ??? device
    dev = ParsedDevice(hostname="R1", canonical_name="R1", raw_filename="R1.txt")
    placeholder = ParsedDevice(
        hostname="???",
        canonical_name="UNKNOWN_R1_Gi0/0",
        display_name="???",
        is_placeholder=True,
        device_type="unknown"
    )
    devices = {"R1": dev, "UNKNOWN_R1_Gi0/0": placeholder}
    link = DiscoveredLink(
        source_device="R1",
        source_interface="GigabitEthernet0/0",
        target_device="UNKNOWN_R1_Gi0/0",
        target_interface="Unspecified",
        confidence=0.5,
        classification="inferred",
        signals=[ContributingSignal(signal_type="ACTIVE_PORT_CARRIER", description="Active port carrier", weight=0.5)]
    )
    conflicts = detect_conflicts(devices, [link])
    # Should not report subnet mismatch or crash on missing interfaces
    assert not any(c.category == "subnet_mismatch" for c in conflicts)
```

- [ ] **Step 2: Run test to verify behavior**

Run: `pytest tests/test_conflict_detector.py -k test_conflict_detector_ignores_placeholder_devices`
Expected: PASS or FAIL depending on KeyError/attribute access.

- [ ] **Step 3: Update `src/conflict_detector.py`**

In `detect_conflicts`:
```python
# In subnet mismatch check, check if either device is placeholder:
dev_a = devices.get(link.source_device)
dev_b = devices.get(link.target_device)
if not dev_a or not dev_b or dev_a.is_placeholder or dev_b.is_placeholder:
    continue
```
Apply similar safeguards to trunk mismatch and routing next-hop checks.

- [ ] **Step 4: Run full test suite**

Run: `pytest tests/test_conflict_detector.py`
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add src/conflict_detector.py tests/test_conflict_detector.py
git commit -m "fix(conflicts): safeguard conflict detection against placeholder devices"
```

---

### Task 4: Visualizer Rendering & Diagnostic Drawer for `???` Nodes

**Files:**
- Modify: `static/js/app.js`
- Test: `tests/test_app.py` & `tests/test_e2e.py`

**Interfaces:**
- Consumes: `TopologyResult` with `devices` containing placeholder `ParsedDevice` (`is_placeholder == true`, `display_name == "???"`).
- Produces: SVG nodes labeled `???` with dashed outline, icon `?`, and interactive diagnostic drawer details.

- [ ] **Step 1: Update SVG node rendering in `static/js/app.js`**

In `drawSvgGraph()`:
1. Detect placeholder nodes:
   ```javascript
   const isPlaceholder = dev.is_placeholder || dev.display_name === '???';
   const nodeColor = isPlaceholder ? '#9CA3AF' : (isSwitch ? '#10B981' : '#3B82F6');
   ```
2. For placeholder nodes:
   - Circle stroke: `stroke-dasharray="4,3"`
   - Outer glow circle fill: `rgba(156, 163, 175, 0.12)`
   - Icon text: `?`
   - Hostname label text: `???`
3. In `openNodeDiagnosticDrawer(dev)`:
   - If `dev.is_placeholder`:
     - Badge: `UNKNOWN PEER / UNCONNECTED PORT` (amber badge)
     - Title: `??? (Unknown Connected Device)`
     - Body: Displays peer hint (e.g. `placeholder_for_device` if from CDP), local interface connection, and guidance notes.

- [ ] **Step 2: Add end-to-end integration test in `tests/test_e2e.py`**

```python
def test_pasig_edge_rtr1_analysis_generates_unknown_nodes():
    with open("captures/PASIG_EDGE_RTR1.txt", "rb") as f:
        content = f.read()
    files = [("files", ("PASIG_EDGE_RTR1.txt", content, "text/plain"))]
    response = client.post("/api/analyze", files=files)
    assert response.status_code == 200
    data = response.json()
    
    # Must contain placeholder nodes labeled ???
    placeholders = [d for d in data["devices"].values() if d.get("is_placeholder")]
    assert len(placeholders) > 0
    for p in placeholders:
        assert p["display_name"] == "???"
        assert p["hostname"] == "???"
```

- [ ] **Step 3: Run end-to-end test**

Run: `pytest tests/test_e2e.py`
Expected: PASS.

- [ ] **Step 4: Commit changes**

```bash
git add static/js/app.js tests/test_e2e.py
git commit -m "feat(ui): render dashed ??? nodes and diagnostic drawer for unknown connections"
```

---

### Task 5: Full Regression Testing & Verification

**Files:**
- Test: All test suites in `tests/`
- Verify: Presets and custom capture bundles

- [ ] **Step 1: Run complete test suite**

Run: `pytest`
Expected: 100% pass across all test modules with zero regressions.

- [ ] **Step 2: Verify preset scenarios retain their existing device counts or update preset expectations cleanly**

Run: `pytest tests/test_presets.py`
Expected: PASS.

- [ ] **Step 3: Final verification commit**

```bash
git status
git commit -am "chore: verify all tests pass with unknown node support"
```
