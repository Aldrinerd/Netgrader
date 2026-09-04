# Unknown Device Connection Discovery & Node Visualization Design

## 1. Overview
In enterprise and student network configurations, devices often have active connections to peers that are not part of the submitted configuration set—such as unmanaged switches, client workstations, ISP routers (e.g., PLDT, Converge), or adjacent switches where only one side was captured. 

Previously, links pointing to unparsed CDP peers had no corresponding node in `TopologyResult.devices`, and active interfaces (`up/up`) with no recognized peer produced no visual indication of a connection.

This design introduces explicit unknown placeholder nodes labeled `???` in both the backend data model and the frontend interactive graph.

---

## 2. Requirements & Scope
1. **Unparsed Discovered Neighbors:**
   - When a link is discovered via CDP, static routes, or next-hops pointing to a device whose full configuration was not uploaded, generate an unknown placeholder node labeled `???`.
2. **Active Ports with No Known Peer:**
   - Any physical or tunnel interface with operational status `admin_status == "up"` and `line_status == "up"` that does not have an established link to another known device will be connected to a dedicated placeholder node labeled `???`.
   - Purely internal/virtual interfaces (such as `Loopback` and `Null`) are excluded from automatic carrier-link synthesis.
3. **No False Multi-Port Bridging:**
   - Each unknown connection attaches to its own unique placeholder node (e.g., `UNKNOWN_<DEVICE>_<INTF>`), preventing separate interfaces from appearing bridged together on the same switch/node.
4. **Interactive Visualization & Diagnostics:**
   - The graph renders placeholder nodes with a distinct dashed visual aesthetic and label `???`.
   - Clicking an unknown node in the UI opens the diagnostic drawer with detailed connection context (local port, IP, discovered peer hostname or platform if known via CDP, and line citations).

---

## 3. Data Model Updates (`src/models.py`)

### `ParsedDevice`
```python
class ParsedDevice(BaseModel):
    hostname: str
    canonical_name: str
    display_name: str = ""                       # Set to "???" for unknown/placeholder nodes
    is_placeholder: bool = False                 # True if synthesized for an unknown peer
    placeholder_for_device: str | None = None    # Original peer name if known (e.g. "PLDT", "PASIG_CORE_SW2")
    placeholder_for_interface: str | None = None # Local interface name it connects to
    device_type: Literal["router", "switch", "l3_switch", "host", "unknown"] = "router"
    raw_filename: str = ""
    interfaces: dict[str, InterfaceData] = Field(default_factory=dict)
    cdp_neighbors: list[CDPNeighbor] = Field(default_factory=list)
    routes: list[RouteEntry] = Field(default_factory=list)
    mac_table: list[MACTableEntry] = Field(default_factory=list)
    vlans: dict[int, str] = Field(default_factory=dict)
```

---

## 4. Backend Logic (`src/fusion_engine.py` & `src/app.py`)

### New Signal Definition
Add `ACTIVE_PORT_CARRIER` to `SIGNAL_WEIGHTS`:
```python
SIGNAL_WEIGHTS = {
    ...
    "ACTIVE_PORT_CARRIER": 0.50,
}
```

### Discovery Pipeline Workflow
1. **Standard Inferences:** Run existing multi-signal evaluation (CDP, Subnet co-membership, Trunks, Next-Hop, Descriptions).
2. **Resolve External / Unparsed Peers:**
   - For every candidate link where either endpoint device is not present in `devices`:
     - Create a unique placeholder `ParsedDevice` key (e.g. `UNKNOWN_PEER_<SRC_DEV>_<SRC_INTF>`).
     - Populate its `hostname="???"`, `display_name="???"`, `device_type="unknown"`, `is_placeholder=True`, and `placeholder_for_device=original_target_name`.
     - Register the placeholder device in the returned `devices` dictionary.
     - Update the `DiscoveredLink` target/source to this key.
3. **Resolve Active Interfaces with No Peer:**
   - Iterate through all interfaces of all parsed devices.
   - Filter for active interfaces: `intf.admin_status == "up"` and `intf.line_status == "up"`.
   - Skip virtual/loopback interfaces (e.g., matching `^Loopback`, `^Null`, `^Vlan` without access port bindings).
   - If this interface has not been included in any link:
     - Generate a unique placeholder `ParsedDevice` (key `UNKNOWN_PORT_<DEV>_<INTF>`), `hostname="???"`, `display_name="???"`, `device_type="unknown"`, `is_placeholder=True`.
     - Generate a `DiscoveredLink` between the local interface and this placeholder device with signal `ACTIVE_PORT_CARRIER` (weight `0.50`, classification `"inferred"`).
     - Add to `devices` and `links`.

### Conflict Detector Safety (`src/conflict_detector.py`)
- Update cross-device conflict rules (e.g., subnet mismatch, VLAN trunk mismatch) to ensure they ignore placeholder devices (`if dev.is_placeholder: continue`) to prevent erroneous mismatch warnings or crashes.

---

## 5. Frontend Visualizer (`static/js/app.js` & `static/css/style.css`)

### SVG Graph Rendering
- Nodes with `is_placeholder === true` or `display_name === '???'`:
  - Main circle: Dashed stroke (`stroke-dasharray: 4,3`), stroke color `#9CA3AF` (neutral slate gray) or amber.
  - Icon: Centered text `?` with monospace styling.
  - Label: `???` displayed beneath the node.
- Edge styling:
  - Links to unknown devices render cleanly with confidence badge and clickability.

### Diagnostic Drawer
- Clicking a placeholder node opens the drawer:
  - Entity badge: `UNKNOWN PEER / ACTIVE CONNECTION`.
  - Title: `??? (Connected to <LOCAL_DEV> <LOCAL_INTF>)`.
  - Body: Shows the local port connection, operational status, IP address/subnet if configured, and any neighbor or carrier clues extracted from show commands.

---

## 6. Testing & Verification Plan
1. **Unit Tests (`tests/test_fusion_engine.py`):**
   - Test that unparsed CDP neighbors produce placeholder `ParsedDevice` objects labeled `???`.
   - Test that an active `up/up` interface without a peer creates a link and a distinct `???` node.
   - Test that multiple active interfaces create distinct `???` nodes, not a single shared node.
   - Test that virtual loopback interfaces do not trigger false `???` links.
2. **Conflict Detector Tests (`tests/test_conflict_detector.py`):**
   - Test that placeholder devices do not trigger spurious conflict errors.
3. **End-to-End API Tests (`tests/test_e2e.py` & `tests/test_app.py`):**
   - Test `/api/analyze` with `captures/PASIG_EDGE_RTR1.txt` confirming `???` placeholder nodes are returned in `devices` and connected in `links`.
4. **Visual UI Verification:**
   - Verify in browser that `???` nodes are displayed with dashed styling, proper labels, and interactive drawer details.
