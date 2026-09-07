# tests/test_app.py
import pytest
from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)

def test_index_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "Network Configuration Evaluation" in response.text
    assert "Topology Discovery" in response.text

def test_api_get_presets():
    response = client.get("/api/presets")
    assert response.status_code == 200
    presets = response.json()
    assert isinstance(presets, list)
    assert len(presets) >= 3

def test_api_load_preset():
    response = client.get("/api/presets/ospf_clean")
    assert response.status_code == 200
    data = response.json()
    assert "devices" in data
    assert "links" in data
    assert "conflicts" in data
    verified_links = [l for l in data["links"] if l["classification"] == "verified"]
    assert len(verified_links) == 3

def test_api_analyze_upload():
    r1_content = """hostname R1
interface GigabitEthernet0/0
 ip address 10.0.0.1 255.255.255.252
show cdp neighbors detail
Device ID: R2
Interface: GigabitEthernet0/0, Port ID (outgoing port): GigabitEthernet0/0
"""
    r2_content = """hostname R2
interface GigabitEthernet0/0
 ip address 10.0.0.2 255.255.255.252
show cdp neighbors detail
Device ID: R1
Interface: GigabitEthernet0/0, Port ID (outgoing port): GigabitEthernet0/0
"""
    files = [
        ("files", ("R1.txt", r1_content.encode("utf-8"), "text/plain")),
        ("files", ("R2.txt", r2_content.encode("utf-8"), "text/plain")),
    ]
    response = client.post("/api/analyze", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "R1" in data["devices"]
    assert "R2" in data["devices"]
    assert len(data["links"]) == 1
    assert data["links"][0]["confidence"] >= 0.95

def test_upload_pkt_xml_endpoint():
    import os
    trial_xml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cisco-pka-to-xml", "trial.xml")
    with open(trial_xml_path, "rb") as f:
        xml_content = f.read()
    
    response = client.post(
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

