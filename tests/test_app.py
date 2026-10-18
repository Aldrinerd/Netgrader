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
    sample_xml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests", "fixtures", "sample_topology.xml")
    with open(sample_xml_path, "rb") as f:
        xml_content = f.read()
    
    response = client.post(
        "/api/analyze",
        files=[("files", ("sample_topology.xml", xml_content, "application/xml"))]
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["links"]) >= 10


def test_api_criteria_generate_and_evaluate_flow():
    import os
    sample_xml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests", "fixtures", "sample_topology.xml")
    with open(sample_xml_path, "rb") as f:
        xml_content = f.read()

    # 1. Teacher generates criteria
    gen_res = client.post(
        "/api/criteria/generate",
        files=[("files", ("sample_topology.xml", xml_content, "application/xml"))],
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
    assert eval_data["passed_count"] > 0
    assert eval_data["failed_count"] == 0


def test_api_generate_criteria_with_policy_form_data():
    import os
    sample_xml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests", "fixtures", "sample_topology.xml")
    with open(sample_xml_path, "rb") as f:
        xml_content = f.read()

    response = client.post(
        "/api/criteria/generate",
        files=[("files", ("sample_topology.xml", xml_content, "application/xml"))],
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


import json  # noqa: E402

from src.topics.weights import largest_remainder  # noqa: E402


def _static_chain_files():
    bundle = network_bundle("static_chain")
    return [("files", (name, text.encode("utf-8"), "text/plain")) for name, text in bundle.items()]


def _generate(**data):
    return client.post("/api/criteria/generate", files=_static_chain_files(), data=data)


def test_generate_returns_topics_and_warnings():
    data = _generate(lab_title="Static Lab").json()
    topics = {t["key"]: t for t in data["topics"]}
    static = topics["static_routing"]
    assert static["gradeable"] is True
    assert static["checkpoints"] == 3
    assert static["devices"] == ["R1", "R2", "R3"]
    assert static["percent"] == static["default_percent"]
    assert sum(t["percent"] for t in data["topics"] if t["gradeable"]) == pytest.approx(100.0)
    assert data["reference_warnings"] == []


def test_generate_lists_detected_only_topics_last():
    import os
    sample = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests", "fixtures", "sample_topology.xml")
    with open(sample, "rb") as f:
        xml = f.read()
    data = client.post("/api/criteria/generate",
                       files=[("files", ("sample_topology.xml", xml, "application/xml"))]).json()
    flags = [t["gradeable"] for t in data["topics"]]
    assert flags == sorted(flags, reverse=True)
    ssh = next(t for t in data["topics"] if t["key"] == "ssh")
    assert ssh["gradeable"] is False and ssh["percent"] is None and ssh["devices"]


def test_generate_applies_topic_weights():
    defaults = {t["key"]: t["default_percent"] for t in _generate().json()["topics"] if t["gradeable"]}
    others = [k for k in defaults if k != "static_routing"]
    units = largest_remainder([defaults[k] for k in others], 500)
    weights = {k: u / 10 for k, u in zip(others, units)}
    weights["static_routing"] = 50.0
    res = _generate(topic_weights=json.dumps(weights))
    assert res.status_code == 200
    data = res.json()
    static = next(t for t in data["topics"] if t["key"] == "static_routing")
    assert static["percent"] == 50.0 and static["points"] == 50.0
    assert "GRADING WEIGHTS" in data["instructions_txt"]


@pytest.mark.parametrize("raw,fragment", [
    ("not json", "JSON object of topic -> percent"),
    ('{"stp": 100}', "not graded yet"),
    ('{"static_routing": 100}', "Missing a weight"),
])
def test_generate_rejects_bad_weights(raw, fragment):
    res = _generate(topic_weights=raw)
    assert res.status_code == 400
    assert fragment in res.json()["detail"]


def test_generate_rejects_weights_that_grade_only_device_presence():
    weights = {t["key"]: 0 for t in _generate().json()["topics"] if t["gradeable"]}
    weights["devices"] = 100
    res = _generate(topic_weights=json.dumps(weights))
    assert res.status_code == 400
    assert "At least one topic other than Device Presence" in res.json()["detail"]
