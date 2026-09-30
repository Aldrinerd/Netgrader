# Cisco Packet Tracer Automated CLI Collector Implementation Plan

> [!NOTE]
> **Historical record — largely superseded (as of 2026-09-08).**
> `scripts/pt_collector.py` types `show` commands into Packet Tracer and scrapes
> the CLI through the clipboard. Direct `.pkt` / `.pka` / `.xml` upload replaced
> it as the normal path, so the collector is now a fallback. Its `pyautogui` and
> `pyperclip` dependencies moved to `requirements-collector.txt` and are **not**
> installed on lab computers.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone, test-driven Python CLI automation utility (`scripts/pt_collector.py`) that types Cisco `show` commands into Packet Tracer device CLI windows, automatically exhausts `--More--` paginations, captures output from the clipboard, extracts hostnames, saves `.txt` files per device, and bundles them into `.zip` archives for the Topology Discovery web app.

**Architecture:** A modular architecture separating core data structures, command sets, sanitizers, and bundle generators (`scripts/pt_collector_core.py`) from the OS-level keystroke / clipboard loop and interactive CLI interface (`scripts/pt_collector.py`).

**Tech Stack:** Python 3.12+, `pyautogui`, `pyperclip`, `pytest`, `zipfile`.

## Global Constraints

- Must work reliably on Windows with Cisco Packet Tracer CLI windows.
- Must never rely on `Ctrl+C` for copying (as Cisco IOS treats `Ctrl+C` as a break interrupt).
- Must automatically handle multi-page output with spacebar bursts.
- Must produce standard `.txt` files compatible with `src/parsers.py`.

---

### Task 1: Environment & Dependencies Setup

**Files:**
- Modify: `requirements.txt`

**Interfaces:**
- Produces: `pyautogui`, `pyperclip` available in Python environment.

- [ ] **Step 1: Add dependencies to `requirements.txt`**

```text
fastapi>=0.110.0
uvicorn>=0.28.0
pydantic>=2.6.0
jinja2>=3.1.3
python-multipart>=0.0.9
pytest>=8.0.0
httpx>=0.27.0
pyautogui>=0.9.54
pyperclip>=1.8.2
```

- [ ] **Step 2: Install dependencies**

Run: `pip install pyautogui pyperclip`
Expected: Successfully installed or already satisfied.

---

### Task 2: Collector Core Engine & Unit Tests

**Files:**
- Create: `scripts/pt_collector_core.py`
- Test: `tests/test_pt_collector.py`

**Interfaces:**
- Produces:
  - `COMMAND_SETS: dict[str, list[str]]`
  - `extract_device_name(raw_text: str, fallback_prefix: str = "Device") -> str`
  - `create_topology_zip(source_dir: str, output_zip_path: str) -> int`

- [ ] **Step 1: Write the failing tests in `tests/test_pt_collector.py`**

```python
import os
import zipfile
import pytest
from scripts.pt_collector_core import (
    COMMAND_SETS,
    extract_device_name,
    create_topology_zip
)

def test_command_sets_defined():
    assert "router" in COMMAND_SETS
    assert "switch" in COMMAND_SETS
    assert "mls" in COMMAND_SETS
    assert "show running-config" in COMMAND_SETS["router"]
    assert "show cdp neighbors detail" in COMMAND_SETS["router"]
    assert "show vlan brief" in COMMAND_SETS["switch"]
    assert "show interfaces trunk" in COMMAND_SETS["switch"]
    assert len(COMMAND_SETS["mls"]) >= len(COMMAND_SETS["router"])

def test_extract_device_name_from_hostname_cmd():
    sample_text = """
    R1# show running-config
    Building configuration...
    hostname PASIG_CORE_RTR1
    !
    interface GigabitEthernet0/0
    """
    assert extract_device_name(sample_text) == "PASIG_CORE_RTR1"

def test_extract_device_name_from_prompt():
    sample_text = """
    Switch_Floor2# show ip int br
    Interface IP-Address OK? Method Status Protocol
    """
    assert extract_device_name(sample_text) == "Switch_Floor2"

def test_extract_device_name_fallback():
    sample_text = "Some random unparseable text without prompt or hostname"
    name = extract_device_name(sample_text, fallback_prefix="TestDev")
    assert name.startswith("TestDev_")

def test_create_topology_zip(tmp_path):
    src_dir = tmp_path / "captures"
    src_dir.mkdir()
    (src_dir / "R1.txt").write_text("hostname R1\n!", encoding="utf-8")
    (src_dir / "SW1.txt").write_text("hostname SW1\n!", encoding="utf-8")
    
    out_zip = tmp_path / "bundle.zip"
    count = create_topology_zip(str(src_dir), str(out_zip))
    assert count == 2
    assert os.path.exists(out_zip)
    
    with zipfile.ZipFile(out_zip, 'r') as z:
        namelist = z.namelist()
        assert "R1.txt" in namelist
        assert "SW1.txt" in namelist
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_pt_collector.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'scripts.pt_collector_core')

- [ ] **Step 3: Implement `scripts/pt_collector_core.py`**

```python
# scripts/pt_collector_core.py
import datetime
import os
import re
import zipfile

COMMAND_SETS: dict[str, list[str]] = {
    "router": [
        "show running-config",
        "show cdp neighbors detail",
        "show ip interface brief",
        "show ip route",
    ],
    "switch": [
        "show running-config",
        "show cdp neighbors detail",
        "show ip interface brief",
        "show vlan brief",
        "show interfaces trunk",
        "show mac address-table",
    ],
    "mls": [
        "show running-config",
        "show cdp neighbors detail",
        "show ip interface brief",
        "show ip route",
        "show vlan brief",
        "show interfaces trunk",
        "show mac address-table",
    ],
}

def extract_device_name(raw_text: str, fallback_prefix: str = "Device") -> str:
    """Extracts hostname from running-config or CLI prompt string."""
    if not raw_text:
        ts = datetime.datetime.now().strftime("%H%M%S")
        return f"{fallback_prefix}_{ts}"

    # 1. Try hostname directive in running-config
    host_match = re.search(r"^\s*hostname\s+([a-zA-Z0-9_\-\.]+)", raw_text, re.IGNORECASE | re.MULTILINE)
    if host_match:
        return host_match.group(1).strip().split(".")[0]

    # 2. Try CLI prompt e.g. "Router#", "PASIG_SW1(config)#"
    prompt_match = re.search(r"^\s*([a-zA-Z0-9_\-]+)(?:\([a-zA-Z0-9_\-]+\))?[>#]", raw_text, re.MULTILINE)
    if prompt_match:
        return prompt_match.group(1).strip()

    ts = datetime.datetime.now().strftime("%H%M%S")
    return f"{fallback_prefix}_{ts}"

def create_topology_zip(source_dir: str, output_zip_path: str) -> int:
    """Compresses all .txt files in source_dir into output_zip_path."""
    if not os.path.exists(source_dir):
        return 0

    txt_files = [f for f in os.listdir(source_dir) if f.lower().endswith(".txt")]
    if not txt_files:
        return 0

    os.makedirs(os.path.dirname(os.path.abspath(output_zip_path)), exist_ok=True)
    with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for fname in txt_files:
            file_path = os.path.join(source_dir, fname)
            z.write(file_path, arcname=fname)

    return len(txt_files)
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_pt_collector.py -v`
Expected: 4 passed.

---

### Task 3: Interactive CLI Automation Utility

**Files:**
- Create: `scripts/pt_collector.py`

**Interfaces:**
- Consumes: `COMMAND_SETS`, `extract_device_name`, `create_topology_zip` from `scripts.pt_collector_core`.
- Produces: Runnable CLI tool with countdown, keystroke injection, space paging, clipboard detection, and menu loop.

- [ ] **Step 1: Implement `scripts/pt_collector.py`**

```python
# scripts/pt_collector.py
import os
import sys
import time
import pyautogui
import pyperclip

from scripts.pt_collector_core import (
    COMMAND_SETS,
    create_topology_zip,
    extract_device_name,
)

CAPTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "captures")
pyautogui.FAILSAFE = True

def print_banner():
    print("\n" + "=" * 62)
    print("   CISCO PACKET TRACER AUTOMATED TOPOLOGY COLLECTOR")
    print("=" * 62)
    os.makedirs(CAPTURES_DIR, exist_ok=True)
    existing = [f for f in os.listdir(CAPTURES_DIR) if f.endswith(".txt")]
    print(f" Captured Devices: {len(existing)} in {CAPTURES_DIR}")
    if existing:
        print("   -> " + ", ".join(existing))
    print("=" * 62)

def countdown(seconds: int = 3):
    print("\n[!] Please click and focus the Packet Tracer CLI window now!")
    for i in range(seconds, 0, -1):
        print(f"    Starting in {i}...", flush=True)
        time.sleep(1)
    print("    >>> EXECUTING COMMANDS... (Do not touch keyboard/mouse) <<<\n")

def execute_commands_in_pt(commands: list[str]):
    """Types commands and pulses spacebar to clear pagination."""
    # Send an initial enter to ensure CLI prompt is active
    pyautogui.press("enter")
    time.sleep(0.2)

    for cmd in commands:
        print(f"  [+] Typing: {cmd}")
        pyautogui.write(cmd, interval=0.01)
        pyautogui.press("enter")
        time.sleep(0.3)

        # Pulse spacebar 25 times with small delays to clear --More-- banners
        for _ in range(25):
            pyautogui.press("space")
            time.sleep(0.04)

        time.sleep(0.2)
        pyautogui.press("enter")

def capture_session(role: str):
    commands = COMMAND_SETS.get(role)
    if not commands:
        print(f"Unknown role: {role}")
        return

    # Clear clipboard before run
    pyperclip.copy("")

    countdown(3)
    execute_commands_in_pt(commands)

    print("\n[✓] Commands executed successfully!")
    print("[*] In Packet Tracer's CLI window, click the 'Copy' button (bottom right) or select all.")
    print("    Waiting for clipboard copy...")

    # Wait up to 15 seconds for user to click Copy or auto-read
    captured_text = ""
    for _ in range(30):
        clip = pyperclip.paste()
        if clip and len(clip.strip()) > 20:
            captured_text = clip
            break
        time.sleep(0.5)

    if not captured_text:
        print("[!] No clipboard data detected. You can paste the output manually below, or press Enter to cancel.")
        captured_text = input("Paste output here: ").strip()

    if not captured_text:
        print("[-] Capture aborted.")
        return

    dev_name = extract_device_name(captured_text)
    user_name = input(f"\nDevice hostname detected as '{dev_name}'. Press Enter to keep, or type new name: ").strip()
    if user_name:
        dev_name = user_name

    out_file = os.path.join(CAPTURES_DIR, f"{dev_name}.txt")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(captured_text)

    line_count = len(captured_text.splitlines())
    print(f"\n[✓] SUCCESS: Saved {line_count} lines to {out_file}")

def bundle_zip():
    out_zip = os.path.join(CAPTURES_DIR, "topology_bundle.zip")
    count = create_topology_zip(CAPTURES_DIR, out_zip)
    if count == 0:
        print("\n[-] No .txt capture files found in captures/ to bundle.")
    else:
        print(f"\n[✓] BUNDLE CREATED: {out_zip} ({count} devices included)")
        print("    You can now upload this ZIP directly to http://127.0.0.1:8000/")

def clear_captures():
    confirm = input("\n[?] Are you sure you want to delete all .txt files in captures/? (y/N): ").strip().lower()
    if confirm == "y":
        for f in os.listdir(CAPTURES_DIR):
            if f.endswith(".txt") or f.endswith(".zip"):
                os.remove(os.path.join(CAPTURES_DIR, f))
        print("[✓] Captures folder cleared.")

def main():
    while True:
        print_banner()
        print("\nSelect an action:")
        print("  [1] Capture Router (show run, cdp, ip int br, ip route)")
        print("  [2] Capture Switch (show run, cdp, ip int br, vlan br, int trunk, mac)")
        print("  [3] Capture Multi-Layer Switch (MLS full suite)")
        print("  --------------------------------------------------")
        print("  [Z] Build ZIP Bundle (captures/topology_bundle.zip)")
        print("  [C] Clear Captured Files")
        print("  [Q] Exit")

        choice = input("\nEnter choice [1-3, Z, C, Q]: ").strip().lower()
        if choice == "1":
            capture_session("router")
        elif choice == "2":
            capture_session("switch")
        elif choice == "3":
            capture_session("mls")
        elif choice == "z":
            bundle_zip()
        elif choice == "c":
            clear_captures()
        elif choice == "q":
            print("\nExiting. Happy analyzing!\n")
            sys.exit(0)
        else:
            print("Invalid selection.")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify dry run syntax and importability**

Run: `python -c "import scripts.pt_collector; print('pt_collector syntax valid')"`
Expected: `pt_collector syntax valid`

---

### Task 4: Full Suite Verification

**Files:**
- Test: `tests/test_pt_collector.py`
- Test: `tests/test_e2e.py`

- [ ] **Step 1: Run all unit and integration tests**

Run: `pytest`
Expected: 29 passed (25 existing + 4 new).

- [ ] **Step 2: Commit changes**

```bash
git add requirements.txt scripts/ tests/test_pt_collector.py docs/
git commit -m "feat: add automated Cisco Packet Tracer CLI topology collector"
```
