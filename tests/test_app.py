# tests/test_app.py
import pytest
from fastapi.testclient import TestClient
from src.app import app
from tests.fixtures import network_bundle

# Requests come from the server's own machine, i.e. the instructor.
client = TestClient(app, client=("127.0.0.1", 50000))

def test_index_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "Network Configuration Evaluation" in response.text
    assert "Topology Discovery" in response.text

def test_api_analyze_reference_bundle():
    """The OSPF ring bundle must yield three verified links through the upload path."""
    bundle = network_bundle("ospf_clean")
    files = [("files", (name, text.encode("utf-8"), "text/plain")) for name, text in bundle.items()]
    response = client.post("/api/analyze", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "devices" in data
    assert "links" in data
    assert "conflicts" in data
    verified_links = [l for l in data["links"] if l["classification"] == "verified"]
    assert len(verified_links) == 3


def test_removed_preset_endpoints_are_gone():
    """The demo scenario feature was removed; its endpoints must not return data."""
    assert client.get("/api/presets").status_code == 404
    assert client.get("/api/presets/ospf_clean").status_code == 404


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
    trial_xml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests", "fixtures", "trial.xml")
    with open(trial_xml_path, "rb") as f:
        xml_content = f.read()
    
    response = client.post(
        "/api/analyze",
        files=[("files", ("trial.xml", xml_content, "application/xml"))]
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["links"]) >= 10


def test_api_criteria_generate_and_evaluate_flow():
    import os
    trial_xml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests", "fixtures", "trial.xml")
    with open(trial_xml_path, "rb") as f:
        xml_content = f.read()

    # 1. Teacher generates criteria
    gen_res = client.post(
        "/api/criteria/generate",
        files=[("files", ("trial.xml", xml_content, "application/xml"))],
        data={"lab_title": "Enterprise CCNA Lab", "total_points": 100.0}
    )
    assert gen_res.status_code == 200
    gen_data = gen_res.json()
    assert "criteria" in gen_data
    assert "instructions_txt" in gen_data
    instructions_txt = gen_data["instructions_txt"]
    assert "Enterprise CCNA Lab" in instructions_txt

    # 2. Parse criteria
    parse_res = client.post(
        "/api/criteria/parse",
        files=[("instructions_file", ("instructions.txt", instructions_txt.encode("utf-8"), "text/plain"))]
    )
    assert parse_res.status_code == 200
    assert parse_res.json()["criteria"]["lab_title"] == "Enterprise CCNA Lab"

    # 3. Student submits the same XML (perfect submission)
    eval_res = client.post(
        "/api/evaluate",
        files=[
            ("instructions_file", ("instructions.txt", instructions_txt.encode("utf-8"), "text/plain")),
            ("student_files", ("student_sub.xml", xml_content, "application/xml"))
        ]
    )
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert eval_data["percentage"] == 100.0
    assert eval_data["grade_letter"] in ("A", "A+")
    assert eval_data["passed_count"] > 0
    assert eval_data["failed_count"] == 0


def test_api_generate_criteria_with_policy_form_data():
    import os
    trial_xml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests", "fixtures", "trial.xml")
    with open(trial_xml_path, "rb") as f:
        xml_content = f.read()

    response = client.post(
        "/api/criteria/generate",
        files=[("files", ("trial.xml", xml_content, "application/xml"))],
        data={
            "lab_title": "Dynamic Subnetting Campus Lab",
            "total_points": 100.0,
            "allow_dynamic_subnetting": "true",
            "enforce_prefix_length": "true",
            "allow_custom_hostnames": "true",
            "strict_cable_type": "false",
            "grade_security_baseline": "true"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "criteria" in data
    criteria = data["criteria"]
    policies = criteria["policies"]
    assert policies["allow_dynamic_subnetting"] is True
    assert policies["allow_custom_hostnames"] is True
    assert policies["strict_cable_type"] is False
    assert policies["grade_security_baseline"] is True
    assert "DYNAMIC & RELATIONAL SUBNETTING POLICY" in data["instructions_txt"]




def test_criteria_generate_rejects_ungradeable_reference():
    """
    A file that parses but carries no configuration must be refused.

    A plain text file yields one device named after the filename and a single
    "this device must exist" rule -- a rubric that looks valid and is useless.
    """
    response = client.post(
        "/api/criteria/generate",
        files=[("files", ("notes.txt", b"just some random notes, not a config", "text/plain"))],
        data={"lab_title": "Oops"},
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "nothing that can be graded" in detail
    # The message must tell the instructor what to upload instead.
    assert ".pkt" in detail


def test_criteria_generate_accepts_a_real_reference_bundle():
    """The guard must not reject legitimate configuration bundles."""
    bundle = network_bundle("ospf_clean")
    files = [("files", (name, text.encode("utf-8"), "text/plain")) for name, text in bundle.items()]
    response = client.post("/api/criteria/generate", files=files, data={"lab_title": "Real Lab"})
    assert response.status_code == 200
    criteria = response.json()["criteria"]
    assert len([r for r in criteria["rules"] if r["category"] != "device"]) > 0
