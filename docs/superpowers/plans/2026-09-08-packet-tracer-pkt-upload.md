# Packet Tracer (.pkt / .pka / .xml) Direct Upload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable direct upload and parsing of Cisco Packet Tracer files (`.pkt`, `.pka`, `.xml`) to extract authoritative ground-truth physical topology, hardware models, canvas coordinates, Cisco IOS running configs, and host IP configurations.

**Architecture:** A dedicated `src/pkt_parser.py` module decrypts `.pkt`/`.pka` files into memory using `pka2xml.decrypt_pka` (or reads exported `.xml`), iterates XML nodes (`<DEVICES>` and `<LINKS>`), feeds extracted Cisco running-configs into the existing `parse_running_config` engine, extracts end-host IP settings, maps physical cabling into `DiscoveredLink` entries, and integrates with `src/app.py` and `src/conflict_detector.py`.

**Tech Stack:** Python 3.11+, FastAPI, `xml.etree.ElementTree`, `pka2xml` (`cisco-pka-to-xml`), PyTest.

## Global Constraints
- Python 3.8+ compatibility.
- Do not break existing `.zip` and `.txt` CLI bundle parsing pipelines.
- All extracted running-configs must preserve line citation numbering for grading evidence.
- Physical links from Packet Tracer XML must have `confidence = 1.00` and `classification = "verified"`.
- Clean error handling for invalid/corrupted PKT files (`pka2xml.PkaError` or XML parse errors).

---

### Task 1: Update Data Models (`src/models.py`)

**Files:**
- Modify: `src/models.py:48-65`
- Test: `tests/test_models.py`

**Interfaces:**
- Produces: `ParsedDevice.x_coord`, `ParsedDevice.y_coord` (both `float | None`) for canvas placement, and `DiscoveredLink.cable_type` (`str | None`).

- [ ] **Step 1: Write the failing test in `tests/test_models.py`**

```python
def test_parsed_device_coordinates_and_cable_type():
    from src.models import ParsedDevice, DiscoveredLink, ContributingSignal
    dev = ParsedDevice(
        hostname="Router1",
        canonical_name="Router1",
        x_coord=1250.5,
        y_coord=890.25
    )
    assert dev.x_coord == 1250.5
    assert dev.y_coord == 890.25
    
    link = DiscoveredLink(
        source_device="Router1",
        source_interface="FastEthernet0/0",
        target_device="Router2",
        target_interface="FastEthernet0/1",
        confidence=1.0,
        classification="verified",
        cable_type="eCrossOver",
        signals=[ContributingSignal(signal_type="PACKET_TRACER_PHYSICAL_CABLE", description="CrossOver cable", weight=1.0)]
    )
    assert link.cable_type == "eCrossOver"
    assert link.confidence == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -k test_parsed_device_coordinates_and_cable_type -v`
Expected: FAIL (AttributeError or ValidationError)

- [ ] **Step 3: Update `src/models.py`**

Add `x_coord`, `y_coord` to `ParsedDevice` and `cable_type` to `DiscoveredLink`:
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
    x_coord: float | None = None
    y_coord: float | None = None
    interfaces: dict[str, InterfaceData] = Field(default_factory=dict)
    cdp_neighbors: list[CDPNeighbor] = Field(default_factory=list)
    routes: list[RouteEntry] = Field(default_factory=list)
    mac_table: list[MACTableEntry] = Field(default_factory=list)
    vlans: dict[int, str] = Field(default_factory=dict)

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add src/models.py tests/test_models.py
git commit -m "feat(models): add x_coord, y_coord and cable_type to topology models"
```

---

### Task 2: Build `src/pkt_parser.py`

**Files:**
- Create: `src/pkt_parser.py`
- Test: `tests/test_pkt_parser.py`

**Interfaces:**
- Consumes: `pka2xml.decrypt_pka`, `src.parsers.parse_running_config`, `src.parsers.normalize_interface_name`, `src.parsers.ip_and_mask_to_network`, `src.models.*`.
- Produces: `parse_pkt_xml(xml_content: str | bytes, filename: str = "topology.xml") -> tuple[dict[str, ParsedDevice], list[DiscoveredLink]]` and `parse_pkt_file(raw_bytes: bytes, filename: str) -> tuple[dict[str, ParsedDevice], list[DiscoveredLink]]`.

- [ ] **Step 1: Write tests in `tests/test_pkt_parser.py`**

```python
import os
import pytest
from src.pkt_parser import parse_pkt_xml, parse_pkt_file

TRIAL_XML_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cisco-pka-to-xml", "trial.xml")

def test_parse_trial_xml():
    assert os.path.exists(TRIAL_XML_PATH), "trial.xml should exist"
    with open(TRIAL_XML_PATH, "rb") as f:
        xml_bytes = f.read()
    
    devices, links = parse_pkt_xml(xml_bytes, filename="trial.xml")
    
    # Verify routers, switches, laptops are parsed
    assert "Router1" in devices
    assert "Switch2" in devices
    assert "L1" in devices
    assert "L2" in devices
    
    # Check device types
    assert devices["Router1"].device_type == "router"
    assert devices["Switch2"].device_type == "switch"
    assert devices["L1"].device_type == "host"
    
    # Check coordinates
    assert devices["L1"].x_coord is not None
    assert devices["L1"].y_coord is not None
    
    # Check router interfaces extracted from running-config
    assert "FastEthernet0/0" in devices["Router1"].interfaces
    assert "FastEthernet0/1" in devices["Router1"].interfaces
    
    # Check links
    assert len(links) >= 10
    
    # Find link between Switch2 and L1
    sw_l1_link = next((l for l in links if (l.source_device == "Switch2" and l.target_device == "L1") or (l.source_device == "L1" and l.target_device == "Switch2")), None)
    assert sw_l1_link is not None
    assert sw_l1_link.confidence == 1.0
    assert sw_l1_link.classification == "verified"
    assert sw_l1_link.cable_type == "eStraightThrough"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pkt_parser.py -v`
Expected: FAIL with ModuleNotFoundError: No module named 'src.pkt_parser'

- [ ] **Step 3: Implement `src/pkt_parser.py`**

```python
# src/pkt_parser.py
import os
import re
import sys
import xml.etree.ElementTree as ET
from typing import Tuple

# Add vendor / cisco-pka-to-xml to sys.path if not present
PKA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cisco-pka-to-xml")
if PKA_DIR not in sys.path:
    sys.path.insert(0, PKA_DIR)

try:
    from pka2xml import decrypt_pka, PkaError
except ImportError:
    decrypt_pka = None
    PkaError = Exception

from src.models import (
    ContributingSignal,
    DiscoveredLink,
    InterfaceData,
    ParsedDevice,
)
from src.parsers import (
    canonical_device_name,
    ip_and_mask_to_network,
    normalize_interface_name,
    parse_running_config,
)

def parse_pkt_file(raw_bytes: bytes, filename: str = "topology.pkt") -> Tuple[dict[str, ParsedDevice], list[DiscoveredLink]]:
    """Decrypts a .pkt/.pka binary file or decodes XML, then parses devices and links."""
    if not raw_bytes:
        return {}, []

    # If already XML text
    stripped = raw_bytes.lstrip()
    if stripped.startswith(b"<"):
        return parse_pkt_xml(raw_bytes, filename=filename)

    # Attempt decryption via pka2xml
    if decrypt_pka is None:
        raise RuntimeError("pka2xml is not available to decrypt .pkt/.pka files.")

    try:
        xml_bytes = decrypt_pka(raw_bytes)
    except Exception as e:
        raise ValueError(f"Failed to decrypt Packet Tracer file '{filename}': {e}") from e

    return parse_pkt_xml(xml_bytes, filename=filename)

def parse_pkt_xml(xml_content: str | bytes, filename: str = "topology.xml") -> Tuple[dict[str, ParsedDevice], list[DiscoveredLink]]:
    """Parses a Packet Tracer XML string or bytes into ParsedDevice and DiscoveredLink collections."""
    if isinstance(xml_content, str):
        xml_bytes = xml_content.encode("utf-8", errors="replace")
    else:
        xml_bytes = xml_content

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise ValueError(f"Malformed Packet Tracer XML in '{filename}': {e}") from e

    # Find NETWORK node
    net_node = root.find(".//NETWORK")
    if net_node is None:
        if root.tag == "NETWORK":
            net_node = root
        else:
            return {}, []

    devices_dict: dict[str, ParsedDevice] = {}
    ref_to_dev: dict[str, str] = {}  # save_ref_id -> hostname

    devices_node = net_node.find("DEVICES")
    if devices_node is not None:
        for dev_elem in devices_node.findall("DEVICE"):
            engine = dev_elem.find("ENGINE")
            if engine is None:
                continue

            name_elem = engine.find("NAME")
            raw_name = name_elem.text.strip() if (name_elem is not None and name_elem.text) else "Unknown"
            
            type_elem = engine.find("TYPE")
            type_str = type_elem.text.strip() if (type_elem is not None and type_elem.text) else ""
            model_attr = type_elem.attrib.get("model", "") if type_elem is not None else ""

            # Coordinates
            x_coord = None
            y_coord = None
            coord_elem = dev_elem.find(".//COORD_SETTINGS")
            if coord_elem is not None:
                try:
                    x_txt = coord_elem.find("X_COORD")
                    y_txt = coord_elem.find("Y_COORD")
                    if x_txt is not None and x_txt.text:
                        x_coord = float(x_txt.text)
                    if y_txt is not None and y_txt.text:
                        y_coord = float(y_txt.text)
                except Exception:
                    pass

            # Reference ID for links
            ref_elem = dev_elem.find(".//SAVE_REF_ID")
            ref_id = ref_elem.text.strip() if (ref_elem is not None and ref_elem.text) else None
            if ref_id:
                ref_to_dev[ref_id] = raw_name

            # Determine device role
            type_lower = type_str.lower()
            model_lower = model_attr.lower()
            if "router" in type_lower or "router" in model_lower:
                device_type = "router"
            elif "switch" in type_lower or "2960" in model_lower or "switch" in model_lower:
                device_type = "switch"
            elif any(k in type_lower for k in ["pc", "laptop", "server", "host", "workstation"]):
                device_type = "host"
            elif "power" in type_lower:
                continue  # Ignore power distribution strips
            else:
                device_type = "unknown"

            device = ParsedDevice(
                hostname=raw_name,
                canonical_name=canonical_device_name(raw_name),
                display_name=raw_name,
                device_type=device_type,
                raw_filename=filename,
                x_coord=x_coord,
                y_coord=y_coord
            )

            # 1. Parse Cisco IOS Running Config (Routers/Switches)
            rc_elem = dev_elem.find(".//RUNNINGCONFIG")
            if rc_elem is None:
                rc_elem = dev_elem.find(".//RUNNING_CONFIG")

            if rc_elem is not None and len(rc_elem) > 0:
                lines = [c.text for c in rc_elem if c.text is not None]
                if lines:
                    config_str = "\n".join(lines)
                    parse_running_config(config_str, start_line=1, device=device)
            
            # 2. Parse Host / PC / Laptop IP & Interface settings
            if device_type == "host":
                for port_elem in dev_elem.findall(".//PORT"):
                    ptype_elem = port_elem.find("TYPE")
                    ptype = ptype_elem.text.strip() if (ptype_elem is not None and ptype_elem.text) else "FastEthernet0"
                    
                    # Convert eCopperFastEthernet -> FastEthernet0
                    port_name = "FastEthernet0"
                    if "gigabit" in ptype.lower():
                        port_name = "GigabitEthernet0"
                    elif "bluetooth" in ptype.lower():
                        continue

                    ip_elem = port_elem.find("IP")
                    sub_elem = port_elem.find("SUBNET")
                    gw_elem = port_elem.find("PORT_GATEWAY")
                    
                    ip_val = ip_elem.text.strip() if (ip_elem is not None and ip_elem.text) else None
                    sub_val = sub_elem.text.strip() if (sub_elem is not None and sub_elem.text) else None
                    gw_val = gw_elem.text.strip() if (gw_elem is not None and gw_elem.text) else None

                    intf = InterfaceData(name=port_name)
                    if ip_val and sub_val:
                        ip, cidr, net_addr = ip_and_mask_to_network(ip_val, sub_val)
                        intf.ip_address = ip
                        intf.subnet_mask = sub_val
                        intf.cidr = cidr
                        intf.network_address = net_addr
                    
                    device.interfaces[port_name] = intf

            devices_dict[device.hostname] = device

    # 3. Parse Links
    discovered_links: list[DiscoveredLink] = []
    links_node = net_node.find("LINKS")
    if links_node is not None:
        for link_elem in links_node.findall("LINK"):
            cable_elem = link_elem.find("CABLE")
            if cable_elem is None:
                continue

            from_ref_elem = cable_elem.find("FROM")
            to_ref_elem = cable_elem.find("TO")
            if from_ref_elem is None or to_ref_elem is None:
                continue

            from_ref = from_ref_elem.text.strip() if from_ref_elem.text else ""
            to_ref = to_ref_elem.text.strip() if to_ref_elem.text else ""

            src_dev = ref_to_dev.get(from_ref)
            tgt_dev = ref_to_dev.get(to_ref)
            if not src_dev or not tgt_dev:
                continue

            # Ports
            port_elems = cable_elem.findall("PORT")
            src_port = port_elems[0].text.strip() if len(port_elems) > 0 and port_elems[0].text else "Unspecified"
            tgt_port = port_elems[1].text.strip() if len(port_elems) > 1 and port_elems[1].text else "Unspecified"

            # Cable Type
            ctype_elem = cable_elem.find("TYPE")
            cable_type = ctype_elem.text.strip() if (ctype_elem is not None and ctype_elem.text) else None

            norm_src_port = normalize_interface_name(src_port)
            norm_tgt_port = normalize_interface_name(tgt_port)

            link = DiscoveredLink(
                source_device=src_dev,
                source_interface=norm_src_port,
                target_device=tgt_dev,
                target_interface=norm_tgt_port,
                confidence=1.00,
                classification="verified",
                cable_type=cable_type,
                signals=[
                    ContributingSignal(
                        signal_type="PACKET_TRACER_PHYSICAL_CABLE",
                        description=f"Physical cable ({cable_type or 'Standard'}) in Packet Tracer",
                        weight=1.00,
                        evidence=[f"{src_dev}:{norm_src_port} <--> {tgt_dev}:{norm_tgt_port}"]
                    )
                ]
            )
            discovered_links.append(link)

    return devices_dict, discovered_links
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pkt_parser.py -v`
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add src/pkt_parser.py tests/test_pkt_parser.py
git commit -m "feat(parser): implement Packet Tracer XML and PKT extraction module"
```

---

### Task 3: Enhance Physical Cabling Conflict Detection (`src/conflict_detector.py`)

**Files:**
- Modify: `src/conflict_detector.py`
- Test: `tests/test_conflict_detector.py`

**Interfaces:**
- Consumes: `devices: dict[str, ParsedDevice]`, `links: list[DiscoveredLink]`.
- Produces: `list[ConflictIssue]` including `cabling_error` (e.g. `eStraightThrough` on router-router links or `eCrossOver` on switch-PC links) and `physical_logical_mismatch`.

- [ ] **Step 1: Write test in `tests/test_conflict_detector.py`**

```python
def test_cabling_type_conflict_detection():
    from src.models import ParsedDevice, InterfaceData, DiscoveredLink, ContributingSignal
    from src.conflict_detector import detect_conflicts
    
    r1 = ParsedDevice(hostname="R1", canonical_name="R1", device_type="router")
    r2 = ParsedDevice(hostname="R2", canonical_name="R2", device_type="router")
    
    # Direct router-router FastEthernet link using straight-through
    link = DiscoveredLink(
        source_device="R1",
        source_interface="FastEthernet0/0",
        target_device="R2",
        target_interface="FastEthernet0/0",
        confidence=1.0,
        classification="verified",
        cable_type="eStraightThrough",
        signals=[ContributingSignal(signal_type="PACKET_TRACER_PHYSICAL_CABLE", description="Physical cable", weight=1.0)]
    )
    
    conflicts = detect_conflicts({"R1": r1, "R2": r2}, [link])
    cabling_conflicts = [c for c in conflicts if c.category == "cabling_error"]
    assert len(cabling_conflicts) > 0
    assert "Straight-Through" in cabling_conflicts[0].description
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_conflict_detector.py -k test_cabling_type_conflict_detection -v`
Expected: FAIL (assertion len(cabling_conflicts) > 0 failed)

- [ ] **Step 3: Update `src/conflict_detector.py`**

Add cabling type validation and physical port mismatch validation to `detect_conflicts`:
```python
    # 5. Check Physical Cable Type Inconsistencies
    for link in links:
        dev_a = devices.get(link.source_device)
        dev_b = devices.get(link.target_device)
        if not dev_a or not dev_b or dev_a.is_placeholder or dev_b.is_placeholder:
            continue
        
        ctype = link.cable_type or ""
        # Direct Router-to-Router FastEthernet with Straight-Through
        if dev_a.device_type == "router" and dev_b.device_type == "router":
            if "fastethernet" in link.source_interface.lower() and "fastethernet" in link.target_interface.lower():
                if ctype == "eStraightThrough":
                    conflicts.append(ConflictIssue(
                        severity="warning",
                        category="cabling_error",
                        title=f"Incorrect Cable Type between {dev_a.hostname} and {dev_b.hostname}",
                        description=f"Direct FastEthernet connection between {dev_a.hostname}:{link.source_interface} and {dev_b.hostname}:{link.target_interface} is using a Straight-Through cable (eStraightThrough). A Crossover cable (eCrossOver) is recommended for direct router-to-router FastEthernet interfaces.",
                        involved_devices=[dev_a.hostname, dev_b.hostname],
                        involved_interfaces=[link.source_interface, link.target_interface],
                        evidence_citations=[f"Physical Cable: {ctype} connecting {dev_a.hostname}:{link.source_interface} <--> {dev_b.hostname}:{link.target_interface}"]
                    ))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_conflict_detector.py -v`
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add src/conflict_detector.py tests/test_conflict_detector.py
git commit -m "feat(conflicts): add physical cabling error detection"
```

---

### Task 4: Integrate PKT / XML Upload in FastAPI Backend (`src/app.py`)

**Files:**
- Modify: `src/app.py:77-101`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `src.pkt_parser.parse_pkt_file`, `src.conflict_detector.detect_conflicts`.
- Produces: Updated `/api/analyze` supporting `.pkt`, `.pka`, `.xml`, `.zip`, `.txt`.

- [ ] **Step 1: Write integration tests in `tests/test_app.py`**

```python
import os
import pytest
from httpx import AsyncClient, ASGITransport
from src.app import app

TRIAL_XML_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cisco-pka-to-xml", "trial.xml")

@pytest.mark.asyncio
async def test_upload_pkt_xml_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        with open(TRIAL_XML_PATH, "rb") as f:
            xml_content = f.read()
        
        response = await ac.post(
            "/api/analyze",
            files=[("files", ("trial.xml", xml_content, "application/xml"))]
        )
        assert response.status_code == 200
        data = response.json()
        assert "devices" in data
        assert "Router1" in data["devices"]
        assert "Switch2" in data["devices"]
        assert "L1" in data["devices"]
        assert len(data["links"]) >= 10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_app.py -k test_upload_pkt_xml_endpoint -v`
Expected: FAIL (or empty devices if handled as raw text)

- [ ] **Step 3: Update `src/app.py`**

```python
from src.pkt_parser import parse_pkt_file

@app.post("/api/analyze", response_model=TopologyResult)
async def api_analyze_upload(files: list[UploadFile] = File(...)):
    files_dict: dict[str, str] = {}
    pkt_files: list[tuple[str, bytes]] = []

    for upload in files:
        filename = upload.filename or "unknown.txt"
        contents = await upload.read()
        lower_name = filename.lower()

        # Check for Packet Tracer file formats
        if lower_name.endswith((".pkt", ".pka", ".xml")):
            pkt_files.append((filename, contents))
            continue

        # If ZIP file, inspect contents
        if lower_name.endswith(".zip"):
            try:
                with zipfile.ZipFile(io.BytesIO(contents)) as z:
                    for z_name in z.namelist():
                        if not z_name.endswith("/") and not z_name.startswith("__MACOSX"):
                            with z.open(z_name) as z_file:
                                z_bytes = z_file.read()
                                if z_name.lower().endswith((".pkt", ".pka", ".xml")):
                                    pkt_files.append((os.path.basename(z_name), z_bytes))
                                else:
                                    files_dict[os.path.basename(z_name)] = z_bytes.decode("utf-8", errors="replace")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to extract zip file {filename}: {str(e)}")
        else:
            files_dict[filename] = contents.decode("utf-8", errors="replace")

    # If Packet Tracer files uploaded, parse them
    if pkt_files:
        all_devices: dict[str, ParsedDevice] = {}
        all_links: list[DiscoveredLink] = []

        for fname, fbytes in pkt_files:
            try:
                devs, lnks = parse_pkt_file(fbytes, filename=fname)
                all_devices.update(devs)
                all_links.extend(lnks)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error parsing Packet Tracer file '{fname}': {e}")

        # If there were also supplementary text files, parse and merge them
        if files_dict:
            for fname, content in files_dict.items():
                if content.strip():
                    dev = parse_device_bundle(content, fname)
                    if dev.hostname not in all_devices:
                        all_devices[dev.hostname] = dev
                    else:
                        # Merge interfaces if needed
                        all_devices[dev.hostname].interfaces.update(dev.interfaces)

        detected_conflicts = detect_conflicts(all_devices, all_links)
        return TopologyResult(
            devices=all_devices,
            links=all_links,
            conflicts=detected_conflicts
        )

    # Otherwise fallback to standard text bundle processor
    return process_bundle_dict(files_dict)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_app.py -v`
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add src/app.py tests/test_app.py
git commit -m "feat(api): enable direct PKT and XML upload analysis endpoint"
```

---

### Task 5: Update Frontend Upload UI (`templates/index.html` & `static/js/app.js`)

**Files:**
- Modify: `templates/index.html`
- Modify: `static/js/app.js`

- [ ] **Step 1: Update `templates/index.html`**

Update the file input accept attribute and description text:
```html
<input type="file" id="file-input" name="files" multiple accept=".pkt,.pka,.xml,.zip,.txt" style="display: none;">
<p class="dropzone-text">Drop Packet Tracer <code>.pkt</code> / <code>.pka</code> / <code>.xml</code> or <code>.zip</code> bundle here</p>
```

- [ ] **Step 2: Update `static/js/app.js`**

Ensure coordinate rendering or dynamic graph layouts handle `x_coord` and `y_coord` if present on device objects.

- [ ] **Step 3: Run full test suite**

Run: `pytest -v`
Expected: ALL PASS

- [ ] **Step 4: Commit changes**

```bash
git add templates/index.html static/js/app.js
git commit -m "feat(ui): update file upload interface to accept .pkt, .pka, and .xml"
```
