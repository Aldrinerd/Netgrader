# Design Specification: Cisco Packet Tracer Automated CLI Collector

> [!NOTE]
> **Historical record — largely superseded (as of 2026-09-08).**
> Direct Packet Tracer file upload replaced clipboard scraping as the normal
> input path. See `docs/superpowers/specs/2026-09-08-packet-tracer-pkt-upload-design.md`.

**Date:** 2026-09-01  
**Target Utility:** `scripts/pt_collector.py`  
**Purpose:** Automate typing Cisco `show` commands into Packet Tracer device CLI windows, paginate through `--More--` banners, capture output, detect hostnames, and bundle `.txt` files into `.zip` archives for the Topology Discovery web app.

---

## 1. Problem Context & Packet Tracer CLI Constraints

In Cisco Packet Tracer:
- Command outputs cannot be extracted via SSH/Telnet because Packet Tracer lacks an open network socket API in standard mode.
- Users must manually open each device's CLI tab, type multiple `show` commands, manually press spacebar for every `--More--` prompt, and copy-paste the text.
- **Critical CLI Keystroke Constraint:** In Cisco IOS CLI, `Ctrl+C` does **not** copy text—it sends a break signal (`SIGINT`). Copying in Packet Tracer is performed via the GUI **Copy** button at the bottom of the CLI tab, or via right-click / selection.
- `terminal length 0` is unsupported in Packet Tracer, requiring spacebar paging.

---

## 2. Architecture & Workflow

### 2.1 Workflow Pipeline

```
[Interactive Terminal Menu]
        │
        ▼ (Select 1: Router, 2: Switch, 3: MLS, 4: Custom)
[Countdown: 3s to Focus PT CLI Tab]
        │
        ▼
[Automated Keystroke Injection (PyAutoGUI)]
  - Type command (e.g. `show run`, `show cdp neigh detail`)
  - Pulse Spacebar (20-30 pulses @ 40ms) to clear `--More--`
  - Repeat for all commands in role
        │
        ▼
[Output Extraction Engine]
  - Primary: Auto-detects clipboard after user clicks "Copy" in PT CLI (or script clicks Copy)
  - Fallback: Direct clipboard listener with instantaneous feedback
        │
        ▼
[Sanitization & Device Identification]
  - Regex extract hostname from `hostname <name>` or CLI prompt `(\w+)[>#]`
  - Save to `captures/<Hostname>.txt`
        │
        ▼
[1-Click Bundler]
  - Option [Z] zips all `captures/*.txt` into `captures/topology_bundle.zip`
```

---

## 3. Command Profiles by Device Role

| Role | Commands Executed |
| :--- | :--- |
| **Router (L3)** | `show running-config`<br>`show cdp neighbors detail`<br>`show ip interface brief`<br>`show ip route` |
| **Switch (L2)** | `show running-config`<br>`show cdp neighbors detail`<br>`show ip interface brief`<br>`show vlan brief`<br>`show interfaces trunk`<br>`show mac address-table` |
| **Multi-Layer Switch (MLS)** | Complete combined suite (Router + Switch commands) |

---

## 4. Technical Implementation Details

1. **`scripts/pt_collector.py`:**
   - Standalone CLI utility with clean formatted terminal outputs.
   - Dependencies: `pyautogui`, `pyperclip`.
   - `pyautogui.FAILSAFE = True` for emergency abort (move mouse to corner).
   - Smart Space Paging: Automatically sends space bursts after `show run`, `show cdp`, `show mac`, and `show ip route` to guarantee prompt return.
   - Clipboard Monitor: Listens for fresh clipboard content, confirms valid Cisco syntax, and writes to `captures/<hostname>.txt`.
   - ZIP Bundler: Generates `captures/topology_bundle.zip` with standardized naming.

2. **Error Handling & Edge Cases:**
   - Empty clipboard detection: Informs the user and waits for "Copy" click.
   - Missing hostname fallback: Prompts the user for a manual device name.
   - Overwrite confirmation: Warns if `<hostname>.txt` already exists before overwriting.

---

## 5. Verification Plan

1. **Unit & Module Testing (`tests/test_pt_collector.py`):**
   - Test command profile generator for Router, Switch, MLS profiles.
   - Test hostname extraction logic from sample Packet Tracer outputs.
   - Test ZIP bundle creation.
2. **Interactive Manual Testing:**
   - Run collector against a live Packet Tracer CLI window, test typing, spacebar paging, clipboard detection, and file output.
