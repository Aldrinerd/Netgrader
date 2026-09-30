# scripts/pt_collector_core.py
import datetime
import os
import re
import zipfile

COMMAND_SETS: dict[str, list[str]] = {
    "router": [
        "show run | include hostname",
        "show run | include interface|ip address|ipv6 address|description|switchport",
        "show run | include router |network |neighbor |ip route|ipv6 route|ip routing",
        "show cdp neighbors detail",
        "show ip interface brief",
        "show ip route",
    ],
    "switch": [
        "show run | include hostname",
        "show run | include interface|ip address|ipv6 address|description|switchport",
        "show cdp neighbors detail",
        "show ip interface brief",
        "show vlan brief",
        "show interfaces trunk",
        "show mac address-table",
    ],
    "mls": [
        "show run | include hostname",
        "show run | include interface|ip address|ipv6 address|description|switchport",
        "show run | include router |network |neighbor |ip route|ipv6 route|ip routing",
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
