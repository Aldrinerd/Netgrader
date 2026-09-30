# tests/test_e2e_policies.py
import os
import pytest
from fastapi.testclient import TestClient
from src.app import app

# Requests come from the server's own machine, i.e. the instructor.
client = TestClient(app, client=("127.0.0.1", 50000))

def test_full_policy_generation_and_grading_flow_xml():
    sample_xml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests", "fixtures", "sample_topology.xml")
    if not os.path.exists(sample_xml_path):
        pytest.skip("sample_topology.xml not available")

    with open(sample_xml_path, "rb") as f:
        xml_bytes = f.read()

    # 1. Instructor generates rubric with flexible cabling enabled
    gen_res = client.post(
        "/api/criteria/generate",
        files=[("files", ("sample_topology.xml", xml_bytes, "application/xml"))],
        data={
            "lab_title": "Advanced CCNA Campus Network",
            "total_points": 100.0,
            "strict_cable_type": "false"
        }
    )
    assert gen_res.status_code == 200
    gen_json = gen_res.json()
    instructions_txt = gen_json["instructions_txt"]
    assert "Advanced CCNA Campus Network" in instructions_txt
    assert "--- CRITERIA SPEC START ---" in instructions_txt

    # 2. Student submits reference topology
    eval_res = client.post(
        "/api/evaluate",
        files=[
            ("instructions_file", ("instructions.txt", instructions_txt.encode("utf-8"), "text/plain")),
            ("student_files", ("student_sample_topology.xml", xml_bytes, "application/xml"))
        ]
    )
    assert eval_res.status_code == 200
    eval_json = eval_res.json()
    assert eval_json["percentage"] == 100.0
    assert eval_json["grade_letter"] in ("A", "A+")
    assert eval_json["failed_count"] == 0


def test_full_policy_dynamic_subnetting_and_security_flow():
    r1_cfg = """hostname R1
service password-encryption
enable secret 5 $1$mERr$hx5rVt7rPNoS4wqbXKX7x0
interface GigabitEthernet0/0
 description Link_to_R2
 ip address 10.0.0.1 255.255.255.252
 no shutdown
line vty 0 4
 login
 password 7 0822455B0A0A
show cdp neighbors detail
Device ID: R2
Interface: GigabitEthernet0/0, Port ID (outgoing port): GigabitEthernet0/0
"""
    r2_cfg = """hostname R2
service password-encryption
enable secret 5 $1$mERr$hx5rVt7rPNoS4wqbXKX7x0
interface GigabitEthernet0/0
 description Link_to_R1
 ip address 10.0.0.2 255.255.255.252
 no shutdown
line vty 0 4
 login
 password 7 0822455B0A0A
show cdp neighbors detail
Device ID: R1
Interface: GigabitEthernet0/0, Port ID (outgoing port): GigabitEthernet0/0
"""

    # 1. Teacher generates criteria with dynamic subnetting & security baseline enabled
    gen_res = client.post(
        "/api/criteria/generate",
        files=[
            ("files", ("R1.txt", r1_cfg.encode("utf-8"), "text/plain")),
            ("files", ("R2.txt", r2_cfg.encode("utf-8"), "text/plain")),
        ],
        data={
            "lab_title": "Dynamic Subnetting & Hardening Lab",
            "total_points": 100.0,
            "allow_dynamic_subnetting": "true",
            "enforce_prefix_length": "true",
            "grade_security_baseline": "true",
            "grade_interface_descriptions": "true"
        }
    )
    assert gen_res.status_code == 200
    gen_json = gen_res.json()
    instructions_txt = gen_json["instructions_txt"]
    assert "DYNAMIC & RELATIONAL SUBNETTING POLICY" in instructions_txt
    assert "Security Baseline      : GRADED" in instructions_txt

    # 2. Student submits valid custom scheme with security configured
    r1_student = """hostname R1
service password-encryption
enable secret 5 $1$customsecret
interface GigabitEthernet0/0
 description To_R2_Peer
 ip address 172.16.50.1 255.255.255.252
 no shutdown
line vty 0 4
 login
 password 7 0822455B0A0A
show cdp neighbors detail
Device ID: R2
Interface: GigabitEthernet0/0, Port ID (outgoing port): GigabitEthernet0/0
"""
    r2_student = """hostname R2
service password-encryption
enable secret 5 $1$customsecret
interface GigabitEthernet0/0
 description To_R1_Peer
 ip address 172.16.50.2 255.255.255.252
 no shutdown
line vty 0 4
 login
 password 7 0822455B0A0A
show cdp neighbors detail
Device ID: R1
Interface: GigabitEthernet0/0, Port ID (outgoing port): GigabitEthernet0/0
"""
    eval_res = client.post(
        "/api/evaluate",
        files=[
            ("instructions_file", ("instructions.txt", instructions_txt.encode("utf-8"), "text/plain")),
            ("student_files", ("R1.txt", r1_student.encode("utf-8"), "text/plain")),
            ("student_files", ("R2.txt", r2_student.encode("utf-8"), "text/plain")),
        ]
    )
    assert eval_res.status_code == 200
    eval_json = eval_res.json()
    assert eval_json["percentage"] == 100.0
    assert eval_json["grade_letter"] in ("A", "A+")
    assert eval_json["failed_count"] == 0

    rel_results = [r for r in eval_json["results"] if r["category"] == "relational_subnet"]
    assert len(rel_results) > 0
    for r in rel_results:
        assert r["passed"] is True
