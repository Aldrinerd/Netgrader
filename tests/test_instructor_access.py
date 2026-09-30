# tests/test_instructor_access.py
"""
Instructor-only access and the per-student batch review.

The instructor runs the server on their own PC and students connect over the
lab network, so "instructor" means "a request from the machine running the
server". Lab computers must not see the Instructor Studio tab, and -- the part
that actually matters -- must be refused by the endpoints behind it.
"""
import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from src.app import app, process_bundle_dict
from src.criteria_generator import format_criteria_to_instructions_txt, generate_criteria_from_topology
from src.models import EvaluationPolicies
from tests.fixtures import network_bundle

instructor = TestClient(app, client=("127.0.0.1", 50000))
instructor_ipv6 = TestClient(app, client=("::1", 50000))
lab_pc = TestClient(app, client=("192.168.1.23", 50000))


def _zip_bytes(bundle: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, text in bundle.items():
            archive.writestr(name, text)
    return buffer.getvalue()


@pytest.fixture(scope="module")
def instructions_txt():
    reference = process_bundle_dict(network_bundle("ospf_clean"))
    criteria = generate_criteria_from_topology(
        reference, lab_title="OSPF Ring Lab", policies=EvaluationPolicies()
    )
    return format_criteria_to_instructions_txt(criteria)


def _batch_files(instructions_txt, submissions):
    files = [("instructions_file", ("instructions.txt", instructions_txt.encode("utf-8"), "text/plain"))]
    for filename, payload in submissions:
        files.append(("student_files", (filename, payload, "application/zip")))
    return files


# --- The tab --------------------------------------------------------------

@pytest.mark.parametrize("client", [instructor, instructor_ipv6])
def test_instructor_sees_the_instructor_studio(client):
    html = client.get("/").text
    assert 'id="nav-mode-teacher"' in html
    assert 'id="panel-mode-teacher"' in html


def test_lab_pc_does_not_receive_the_instructor_studio():
    html = lab_pc.get("/").text
    # Not hidden -- absent. Nothing to un-hide with the browser's dev tools.
    assert 'id="nav-mode-teacher"' not in html
    assert 'id="panel-mode-teacher"' not in html
    assert 'id="batch-grade-btn"' not in html
    # Everything a student needs is still there.
    assert 'id="nav-mode-student"' in html
    assert 'id="nav-mode-visualizer"' in html


# --- The endpoints --------------------------------------------------------

def test_lab_pc_cannot_generate_a_rubric():
    bundle = network_bundle("ospf_clean")
    files = [("files", (name, text.encode("utf-8"), "text/plain")) for name, text in bundle.items()]
    response = lab_pc.post("/api/criteria/generate", files=files)
    assert response.status_code == 403
    assert "instructor" in response.json()["detail"].lower()


def test_lab_pc_cannot_batch_grade(instructions_txt):
    files = _batch_files(instructions_txt, [("a.zip", _zip_bytes(network_bundle("ospf_clean")))])
    assert lab_pc.post("/api/evaluate/batch", files=files).status_code == 403


def test_lab_pc_cannot_request_a_class_briefing():
    response = lab_pc.post("/api/class/briefing", json={"categories_per_student": [["routing"]]})
    assert response.status_code == 403


def test_students_can_still_grade_their_own_work(instructions_txt):
    files = [("instructions_file", ("instructions.txt", instructions_txt.encode("utf-8"), "text/plain"))]
    for name, text in network_bundle("ospf_clean").items():
        files.append(("student_files", (name, text.encode("utf-8"), "text/plain")))
    assert lab_pc.post("/api/evaluate", files=files).status_code == 200

    parse = lab_pc.post(
        "/api/criteria/parse",
        files={"instructions_file": ("instructions.txt", instructions_txt.encode("utf-8"), "text/plain")},
    )
    assert parse.status_code == 200


def test_instructor_browsing_to_the_lan_address_is_still_the_instructor():
    """
    Browsing to http://192.168.x.y:8000 on the server's own PC arrives from the
    LAN address, not 127.0.0.1. The client and server addresses then match.
    """
    from starlette.requests import Request
    from src.app import is_instructor

    def request(client_ip, server_ip):
        return Request({"type": "http", "client": (client_ip, 51000), "server": (server_ip, 8000), "headers": []})

    assert is_instructor(request("192.168.1.10", "192.168.1.10"))
    assert is_instructor(request("::ffff:127.0.0.1", "0.0.0.0"))
    assert not is_instructor(request("192.168.1.23", "192.168.1.10"))
    assert not is_instructor(request("not-an-ip", "192.168.1.10"))


# --- Per-student review data ----------------------------------------------

def test_batch_rows_carry_each_students_full_report(instructions_txt):
    """The batch table's Review button needs every checkpoint, not just a count."""
    files = _batch_files(instructions_txt, [
        ("Santos, Maria.zip", _zip_bytes(network_bundle("subnet_cabling_error"))),
        ("broken.zip", b"this is not a zip file"),
    ])
    data = instructor.post("/api/evaluate/batch", files=files).json()
    rows = {row["student"]: row for row in data["results"]}

    report = rows["Santos, Maria"]["report"]
    assert report is not None
    missed = [r for r in report["results"] if not r["passed"]]
    assert len(missed) == rows["Santos, Maria"]["failed_count"] > 0
    # Enough to say *where* and *why*: the device, the feedback, and the fix.
    for result in missed:
        assert result["target_device"]
        assert result["feedback"]
    assert report["topology"]["devices"]

    # A submission that could not be graded has nothing to review.
    assert rows["broken"]["report"] is None
