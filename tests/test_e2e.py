# tests/test_e2e.py
import pytest
from fastapi.testclient import TestClient
from src.app import app
from src.presets import get_available_presets

client = TestClient(app)

def test_full_pipeline_all_presets():
    presets = get_available_presets()
    for preset in presets:
        p_id = preset["id"]
        response = client.get(f"/api/presets/{p_id}")
        assert response.status_code == 200, f"Preset {p_id} failed"
        data = response.json()
        
        # Verify schema integrity
        assert "devices" in data
        assert "links" in data
        assert "conflicts" in data
        primary_devices = [d for d in data["devices"].values() if not d.get("is_placeholder")]
        assert len(primary_devices) == preset["device_count"]
        
        # Ensure all links have valid confidence and classification
        for link in data["links"]:
            assert 0.0 <= link["confidence"] <= 1.0
            assert link["classification"] in ("verified", "inferred", "unverified")
            assert len(link["signals"]) > 0

def test_end_to_end_custom_upload():
    sw1 = """
    hostname CoreSW1
    interface GigabitEthernet0/1
     switchport mode trunk
     switchport trunk native vlan 10
    show cdp neighbors detail
    Device ID: CoreSW2
    Interface: GigabitEthernet0/1, Port ID: GigabitEthernet0/1
    """
    sw2 = """
    hostname CoreSW2
    interface GigabitEthernet0/1
     switchport mode trunk
     switchport trunk native vlan 20
    show cdp neighbors detail
    Device ID: CoreSW1
    Interface: GigabitEthernet0/1, Port ID: GigabitEthernet0/1
    """
    files = [
        ("files", ("CoreSW1.txt", sw1.encode("utf-8"), "text/plain")),
        ("files", ("CoreSW2.txt", sw2.encode("utf-8"), "text/plain")),
    ]
    response = client.post("/api/analyze", files=files)
    assert response.status_code == 200
    data = response.json()
    assert len(data["devices"]) == 2
    assert len(data["links"]) == 1
    assert len(data["conflicts"]) >= 1
    assert any(c["category"] == "vlan_trunk_mismatch" for c in data["conflicts"])

def test_pasig_edge_rtr1_analysis_generates_unknown_nodes():
    with open("captures/PASIG_EDGE_RTR1.txt", "rb") as f:
        content = f.read()
    files = [("files", ("PASIG_EDGE_RTR1.txt", content, "text/plain"))]
    response = client.post("/api/analyze", files=files)
    assert response.status_code == 200
    data = response.json()
    
    placeholders = [d for d in data["devices"].values() if d.get("is_placeholder")]
    assert len(placeholders) > 0
    for p in placeholders:
        assert p["display_name"] == "???"
        assert p["hostname"] == "???"
        assert p["device_type"] == "unknown"

