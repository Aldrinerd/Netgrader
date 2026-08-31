# tests/test_sanitizer.py
import pytest
from src.sanitizer import sanitize_terminal_output, split_command_sections

def test_sanitize_terminal_output():
    noisy = "Router# show running-config\r\nBuilding configuration...\r\n --More-- \r\nhostname R1\r\n"
    clean = sanitize_terminal_output(noisy)
    assert "--More--" not in clean
    assert "hostname R1" in clean

def test_split_command_sections_multiple():
    raw_bundle = """
    R1# show running-config
    hostname R1
    interface GigabitEthernet0/0
     ip address 10.0.0.1 255.255.255.252
    !
    R1# show cdp neighbors detail
    -------------------------
    Device ID: R2
    Entry address(es):
      IP address: 10.0.0.2
    Interface: GigabitEthernet0/0,  Port ID (outgoing port): GigabitEthernet0/0
    !
    R1# show ip interface brief
    Interface              IP-Address      OK? Method Status                Protocol
    GigabitEthernet0/0     10.0.0.1        YES manual up                    up
    """
    sections = split_command_sections(raw_bundle)
    assert "show running-config" in sections
    assert "show cdp neighbors detail" in sections
    assert "show ip interface brief" in sections
    
    run_content, run_offset = sections["show running-config"]
    assert "hostname R1" in run_content
    
    cdp_content, cdp_offset = sections["show cdp neighbors detail"]
    assert "Device ID: R2" in cdp_content

def test_split_single_running_config_without_headers():
    raw_config = """
    hostname CoreSwitch
    vlan 10
     name Sales
    """
    sections = split_command_sections(raw_config)
    assert "show running-config" in sections
    content, offset = sections["show running-config"]
    assert "hostname CoreSwitch" in content
