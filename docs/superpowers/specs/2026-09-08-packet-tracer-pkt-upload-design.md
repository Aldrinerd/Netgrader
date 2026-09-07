# Cisco Packet Tracer (.pkt / .pka / .xml) Direct Upload & Physical Ground-Truth Discovery Design

## 1. Overview
In networking education, Cisco Packet Tracer is the standard simulation environment. Students save their lab exercises as `.pkt` (saved networks) or `.pka` (activity files). 

Previously, evaluating student work required manual CLI text exports or automated keystroke scraping via `pt_collector.py` to produce a `.zip` text bundle of `show` command outputs. While functional, this introduced friction for students and lacked visibility into end devices (PCs/laptops) and physical cable connections.

This design introduces native support for uploading `.pkt`, `.pka`, and `.xml` files directly into the web application. Using the integrated `cisco-pka-to-xml` decoder (`pka2xml`), the system decrypts Packet Tracer files in-memory and extracts:
1. **Ground-Truth Physical Topology**: Authoritative cable connections between exact ports, including cable types (`eStraightThrough`, `eCrossOver`, `eSerial`, `eRollOver`).
2. **Device Hardware & Canvas Coordinates**: Hardware models (e.g., `1841`, `2960-24TT`, `Laptop-PT`) and visual `(X, Y)` positions matching the student's Packet Tracer screen.
3. **Full Cisco IOS Running Configurations**: Extracted line-by-line from `<RUNNINGCONFIG>` and parsed with the existing configuration evaluator.
4. **End Device Profiles**: First-class support for PCs and Laptops, capturing IP addresses, subnet masks, default gateways, and MAC addresses.

---

## 2. Architecture & Data Flow

```
   ┌──────────────────────────────────────────────────────────┐
   │ Upload Input (.pkt, .pka, .xml, .zip, or .txt files)     │
   └────────────────────────────┬─────────────────────────────┘
                                │
        ┌───────────────────────┴───────────────────────┐
        ▼                                               ▼
[Binary .pkt / .pka]                               [.xml / .zip / .txt]
        │                                               │
        ▼ (pka2xml.decrypt_pka)                         │
 [XML In-Memory] ◄──────────────────────────────────────┤
        │                                               │
        ▼                                               ▼
┌───────────────────────────────┐              ┌─────────────────┐
│ src/pkt_parser.py             │              │ src/parsers.py  │
│ - Parse <DEVICES>             │              │ (Existing Text  │
│   • Routers/Switches configs  │              │  Bundle Parser) │
│   • PC/Laptop interfaces      │              └────────┬────────┘
│   • Canvas Coordinates (X, Y) │                       │
│ - Parse <LINKS> (Cables)      │                       │
└───────────────┬───────────────┘                       │
                │                                       │
                ▼                                       ▼
        ┌───────────────────────────────────────────────────────┐
        │ Parsed Devices (dict[str, ParsedDevice])              │
        │ Authoritative Links (list[DiscoveredLink])            │
        └───────────────────────┬───────────────────────────────┘
                                │
                                ▼
        ┌───────────────────────────────────────────────────────┐
        │ src/conflict_detector.py                              │
        │ - Subnet mismatches across physical links             │
        │ - Wrong cable type detection (Crossover vs Straight)  │
        │ - Inactive/misconfigured physical link detection      │
        │ - Duplicate IP detection                              │
        └───────────────────────┬───────────────────────────────┘
                                │
                                ▼
        ┌───────────────────────────────────────────────────────┐
        │ TopologyResult (JSON to Frontend Interactive UI)      │
        └───────────────────────────────────────────────────────┘
```

---

## 3. Data Model Updates (`src/models.py`)

### `ParsedDevice`
Add optional canvas coordinate fields to retain the visual layout from Packet Tracer:
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
    x_coord: float | None = None   # From <COORD_SETTINGS><X_COORD>
    y_coord: float | None = None   # From <COORD_SETTINGS><Y_COORD>
    interfaces: dict[str, InterfaceData] = Field(default_factory=dict)
    cdp_neighbors: list[CDPNeighbor] = Field(default_factory=list)
    routes: list[RouteEntry] = Field(default_factory=list)
    mac_table: list[MACTableEntry] = Field(default_factory=list)
    vlans: dict[int, str] = Field(default_factory=dict)
```

### `ContributingSignal` & `DiscoveredLink`
New signal type for physical links extracted from Packet Tracer:
- `PACKET_TRACER_PHYSICAL_CABLE` (Weight: `1.00`)
- `cable_type` attribute or evidence annotation (e.g. `eStraightThrough`, `eCrossOver`, `eSerial`, `eRollOver`).

---

## 4. Parser Implementation (`src/pkt_parser.py`)

### A. Decryption Layer
- Function `parse_pkt_bytes(raw_bytes: bytes, filename: str) -> TopologyResult`:
  - If `filename.lower().endswith(('.pkt', '.pka'))` or raw bytes start with Packet Tracer signature, call `pka2xml.decrypt_pka(raw_bytes)`.
  - If `filename.lower().endswith('.xml')` or content starts with `<PACKETTRACER`, decode as UTF-8 XML.
  - Parse XML using `xml.etree.ElementTree`.

### B. Device Traversal (`<NETWORK><DEVICES><DEVICE>`)
1. **Device Identification**:
   - Hostname: `<ENGINE><NAME>`
   - Type/Model: `<ENGINE><TYPE>` (e.g., `Router`, `Switch`, `Laptop`, `PC`) and model attribute (e.g., `model="1841"`).
   - Coordinates: `<COORD_SETTINGS><X_COORD>` and `<Y_COORD>`.
   - Internal Reference ID: `<SAVE_REF_ID>` mapped to hostname for link resolution.
2. **Cisco Routers and Switches**:
   - Extract `<RUNNINGCONFIG><LINE>` (or `<RUNNING_CONFIG><LINE>`) elements.
   - Join lines with `\n` to reconstruct standard Cisco IOS running-config text.
   - Invoke `parse_running_config(config_text, start_line=1, device=device)`.
3. **End Devices (PCs / Laptops / Servers)**:
   - Assign `device_type = "host"`.
   - Iterate `<PORT>` nodes:
     - Extract port type, `<MACADDRESS>`, `<IP>`, `<SUBNET>`, and `<PORT_GATEWAY>`.
     - Populate `InterfaceData` with IP and subnet configuration.

### C. Link Traversal (`<NETWORK><LINKS><LINK>`)
- For each `<LINK>`:
  - Extract `<CABLE>` child elements:
    - `FROM`: Reference ID -> maps to source device hostname.
    - `PORT`: Source interface name.
    - `TO`: Reference ID -> maps to target device hostname.
    - `PORT`: Target interface name.
    - `TYPE`: Cable type (`eStraightThrough`, `eCrossOver`, `eSerial`, `eRollOver`).
  - Construct `DiscoveredLink`:
    - `source_device`, `source_interface`, `target_device`, `target_interface`
    - `confidence = 1.00`, `classification = "verified"`
    - Signal: `PACKET_TRACER_PHYSICAL_CABLE` with details in evidence.

---

## 5. Enhanced Cabling Conflict Detection (`src/conflict_detector.py`)

With physical ground-truth links available, the conflict detector will evaluate:

1. **Physical Cable Medium Rules**:
   - **Router-to-Router Ethernet**: If connected via FastEthernet/Ethernet using `eStraightThrough` without auto-MDIX support, flag as `warning`/`error` ("Crossover cable required for direct Router-to-Router FastEthernet connection").
   - **Switch-to-Host / Switch-to-Router**: If connected using `eCrossOver`, flag as a cabling discrepancy.
   - **Serial Connections**: If connected without clock rate on the DCE side, flag configuration error.
2. **Physical-to-Logical Port Mismatch**:
   - Cable is physically plugged into `FastEthernet0/0`, but IP address was configured on `FastEthernet0/1` while `FastEthernet0/0` is unconfigured or administratively down.
3. **Cross-Link Subnet Inconsistencies**:
   - Validate that physically connected endpoints share the same IP subnet.

---

## 6. API & UI Integration

1. **`src/app.py` (`/api/analyze`)**:
   - Inspect uploaded files:
     - If `.pkt` / `.pka` / `.xml`: delegate to `parse_pkt_bytes()`.
     - If `.zip` / `.txt`: delegate to existing `process_bundle_dict()`.
2. **`templates/index.html` & `static/js/app.js`**:
   - Update file input to accept `.pkt,.pka,.xml,.zip,.txt`.
   - Display file types in drag-and-drop zone.
   - Graph visualization utilizes `x_coord` and `y_coord` if provided to reproduce the exact canvas topology.

---

## 7. Verification & Testing

1. **Unit Tests (`tests/test_pkt_parser.py`)**:
   - Test `trial.xml` extraction: verifies 12 devices parsed, 12 links connected, host configs extracted, running configs parsed.
   - Test error handling: malformed XML, unencrypted corrupted files.
2. **Cabling Conflict Tests**:
   - Test detection of wrong cable types and physical/logical interface mismatches.
3. **FastAPI Upload Tests (`tests/test_app.py`)**:
   - Post `trial.xml` and verify `200 OK` response returning `TopologyResult`.
