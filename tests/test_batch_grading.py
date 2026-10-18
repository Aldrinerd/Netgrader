# tests/test_batch_grading.py
"""
Batch grading and gradebook export.

Chapter I frames the research problem as "manual checking for large batches",
so grading a whole class in one pass -- and getting the scores out in a form a
gradebook can open -- is the feature that actually closes that loop.
"""
import csv
import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from src.app import app, process_bundle_dict
from src.criteria_generator import format_criteria_to_instructions_txt, generate_criteria_from_topology
from src.models import EvaluationPolicies
from tests.fixtures import network_bundle

# Requests come from the server's own machine, i.e. the instructor.
client = TestClient(app, client=("127.0.0.1", 50000))


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


def _post_batch(instructions_txt, submissions):
    files = [("instructions_file", ("instructions.txt", instructions_txt.encode("utf-8"), "text/plain"))]
    for filename, payload in submissions:
        files.append(("student_files", (filename, payload, "application/zip")))
    return client.post("/api/evaluate/batch", files=files)


def test_batch_grades_every_submission(instructions_txt):
    response = _post_batch(instructions_txt, [
        ("Dela Cruz, Juan.zip", _zip_bytes(network_bundle("ospf_clean"))),
        ("Santos, Maria.zip", _zip_bytes(network_bundle("subnet_cabling_error"))),
    ])
    assert response.status_code == 200
    data = response.json()

    assert data["summary"]["submissions"] == 2
    assert data["summary"]["graded"] == 2
    assert data["summary"]["errors"] == 0

    by_student = {row["student"]: row for row in data["results"]}
    # The student who submitted the reference itself must score perfectly.
    assert by_student["Dela Cruz, Juan"]["percentage"] == 100.0
    # The flawed bundle must not.
    assert by_student["Santos, Maria"]["percentage"] < 100.0


def test_student_name_comes_from_filename(instructions_txt):
    response = _post_batch(instructions_txt, [
        ("2021-00123 Reyes.zip", _zip_bytes(network_bundle("ospf_clean"))),
    ])
    assert response.json()["results"][0]["student"] == "2021-00123 Reyes"


def test_one_corrupt_file_does_not_abort_the_batch(instructions_txt):
    """An instructor must not lose a whole class run to a single bad upload."""
    response = _post_batch(instructions_txt, [
        ("Good, Student.zip", _zip_bytes(network_bundle("ospf_clean"))),
        ("Broken, Upload.zip", b"this is not a zip file"),
        ("Also Good, Student.zip", _zip_bytes(network_bundle("ospf_clean"))),
    ])
    assert response.status_code == 200
    data = response.json()

    assert data["summary"]["submissions"] == 3
    assert data["summary"]["graded"] == 2
    assert data["summary"]["errors"] == 1

    broken = next(r for r in data["results"] if r["student"] == "Broken, Upload")
    assert broken["status"].startswith("ERROR")
    assert broken["percentage"] == 0.0

    # The good submissions either side of it still graded normally.
    for name in ("Good, Student", "Also Good, Student"):
        row = next(r for r in data["results"] if r["student"] == name)
        assert row["percentage"] == 100.0


def test_csv_is_valid_and_quotes_names_with_commas(instructions_txt):
    response = _post_batch(instructions_txt, [
        ("Dela Cruz, Juan.zip", _zip_bytes(network_bundle("ospf_clean"))),
        ("Santos, Maria.zip", _zip_bytes(network_bundle("subnet_cabling_error"))),
    ])
    csv_text = response.json()["csv"]

    rows = list(csv.reader(io.StringIO(csv_text)))
    header, body = rows[0], rows[1:]

    assert header[0] == "Student"
    assert "Percentage" in header
    assert "Missed Checkpoints" in header
    assert "Grade" not in header
    assert len(body) == 2

    # A name containing a comma must survive the CSV round trip intact.
    assert body[0][0] == "Dela Cruz, Juan"
    assert body[1][0] == "Santos, Maria"

    # Every row must have exactly as many fields as the header.
    for row in body:
        assert len(row) == len(header)


def test_failed_checkpoints_are_listed_for_feedback(instructions_txt):
    response = _post_batch(instructions_txt, [
        ("Santos, Maria.zip", _zip_bytes(network_bundle("subnet_cabling_error"))),
    ])
    row = response.json()["results"][0]
    assert row["failed_count"] > 0
    assert len(row["missed"]) == row["failed_count"]


def test_batch_rejects_an_invalid_instructions_file():
    response = _post_batch("this is not a rubric", [
        ("Someone.zip", _zip_bytes(network_bundle("ospf_clean"))),
    ])
    assert response.status_code == 400
    assert "Invalid Instructions File" in response.json()["detail"]


def test_batch_requires_at_least_one_submission(instructions_txt):
    files = [("instructions_file", ("instructions.txt", instructions_txt.encode("utf-8"), "text/plain"))]
    response = client.post("/api/evaluate/batch", files=files)
    # FastAPI rejects the missing field before the handler runs.
    assert response.status_code in (400, 422)


@pytest.mark.parametrize("prefix", ["=", "+", "-", "@", "\t", "\r"])
def test_csv_neutralises_formula_prefixes(prefix):
    """
    A filename such as '=HYPERLINK(...).pkt' must not become a live formula
    when the instructor opens the gradebook in Excel (#32).
    """
    from src.app import _build_gradebook_csv
    name = f'{prefix}HYPERLINK("http://evil","Dela Cruz")'
    text = _build_gradebook_csv("Lab", [{
        "student": name,
        "missed": [f"{prefix}cmd|' /C calc'!A0"],
    }])
    header, row = list(csv.reader(io.StringIO(text)))[:2]
    assert row[0] == "'" + name
    assert row[header.index("Missed Checkpoints")].startswith("'")


def test_csv_leaves_ordinary_values_alone():
    from src.app import _build_gradebook_csv
    text = _build_gradebook_csv("Lab 3", [{
        "student": "Dela Cruz, Juan", "total_score": -0.0, "percentage": 82.5, "missed": [],
    }])
    row = list(csv.reader(io.StringIO(text)))[1]
    assert row[0] == "Dela Cruz, Juan"
    assert row[1] == "Lab 3"


def test_csv_lone_dash_is_not_prefixed():
    from src.app import _csv_safe
    assert _csv_safe("-") == "-"


def test_error_row_counts_only_graded_checkpoints():
    from src.app import process_bundle_dict
    from src.criteria_generator import format_criteria_to_instructions_txt, generate_criteria_from_topology
    from tests.fixtures import network_bundle

    defaults = generate_criteria_from_topology(process_bundle_dict(network_bundle("static_chain"))).topic_weights
    weights = dict(defaults)
    weights["static_routing"] = round(weights["static_routing"] + weights["cabling"], 1)
    weights["cabling"] = 0.0
    criteria = generate_criteria_from_topology(
        process_bundle_dict(network_bundle("static_chain")), topic_weights=weights)
    txt = format_criteria_to_instructions_txt(criteria)
    res = client.post("/api/evaluate/batch", files=[
        ("instructions_file", ("instructions.txt", txt.encode("utf-8"), "text/plain")),
        ("student_files", ("Empty Student.txt", b"   ", "text/plain")),
    ])
    assert res.status_code == 200
    row = res.json()["results"][0]
    assert row["status"].startswith("ERROR")
    assert row["failed_count"] == sum(r.graded for r in criteria.rules)
