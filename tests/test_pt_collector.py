# tests/test_pt_collector.py
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
    assert any("show run" in cmd for cmd in COMMAND_SETS["router"])
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
