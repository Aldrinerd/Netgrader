# tests/test_presets.py
import pytest
from src.presets import get_available_presets, load_preset
from src.parsers import parse_device_bundle
from src.fusion_engine import infer_topology_links
from src.conflict_detector import detect_conflicts

def test_available_presets_list():
    presets = get_available_presets()
    assert len(presets) >= 3
    ids = [p["id"] for p in presets]
    assert "ospf_clean" in ids
    assert "subnet_cabling_error" in ids
    assert "vlan_trunk_mismatch" in ids

def test_preset_ospf_clean():
    bundle_files = load_preset("ospf_clean")
    assert len(bundle_files) == 3
    assert "R1.txt" in bundle_files
    assert "R2.txt" in bundle_files
    assert "R3.txt" in bundle_files
    
    devices = {fn: parse_device_bundle(content, fn) for fn, content in bundle_files.items()}
    devices_by_name = {d.hostname: d for d in devices.values()}
    links = infer_topology_links(devices_by_name)
    conflicts = detect_conflicts(devices_by_name, links)
    
    verified_links = [l for l in links if l.classification == "verified"]
    assert len(verified_links) == 3  # Triangle topology
    assert all(l.classification == "verified" for l in verified_links)
    assert len([c for c in conflicts if c.severity == "error"]) == 0

def test_preset_subnet_cabling_error():
    bundle_files = load_preset("subnet_cabling_error")
    devices = {fn: parse_device_bundle(content, fn) for fn, content in bundle_files.items()}
    devices_by_name = {d.hostname: d for d in devices.values()}
    links = infer_topology_links(devices_by_name)
    conflicts = detect_conflicts(devices_by_name, links)
    
    assert len(conflicts) > 0
    categories = [c.category for c in conflicts]
    assert "subnet_mismatch" in categories or "interface_down" in categories

def test_preset_vlan_trunk_mismatch():
    bundle_files = load_preset("vlan_trunk_mismatch")
    devices = {fn: parse_device_bundle(content, fn) for fn, content in bundle_files.items()}
    devices_by_name = {d.hostname: d for d in devices.values()}
    links = infer_topology_links(devices_by_name)
    conflicts = detect_conflicts(devices_by_name, links)
    
    assert len(conflicts) > 0
    categories = [c.category for c in conflicts]
    assert "vlan_trunk_mismatch" in categories
