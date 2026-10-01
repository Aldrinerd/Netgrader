# tests/test_e2e_live_server.py
"""
True end-to-end test against a real HTTP server.

The server is started by the test itself on a free port, so this no longer
depends on someone having already run the app on port 8000 -- which, on a
shared machine, could silently test a completely different application.
"""
import os
import subprocess
import sys
import time

import pytest
import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from start_server import find_free_port  # noqa: E402

STARTUP_TIMEOUT_SECONDS = 30


@pytest.fixture(scope="module")
def live_server():
    """Start uvicorn on a free port for the duration of this module."""
    port = find_free_port(8000)
    if port is None:
        pytest.skip("No free port available to start a test server.")

    base_url = f"http://127.0.0.1:{port}"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.app:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    deadline = time.time() + STARTUP_TIMEOUT_SECONDS
    while time.time() < deadline:
        if proc.poll() is not None:
            output = proc.stdout.read().decode("utf-8", errors="replace") if proc.stdout else ""
            pytest.fail(f"Server exited during startup:\n{output}")
        try:
            if requests.get(base_url + "/", timeout=1).status_code == 200:
                break
        except requests.RequestException:
            time.sleep(0.3)
    else:
        proc.terminate()
        pytest.fail(f"Server did not become ready within {STARTUP_TIMEOUT_SECONDS}s.")

    yield base_url

    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def test_index_page_renders(live_server):
    res = requests.get(live_server + "/", timeout=10)
    assert res.status_code == 200
    assert "Instructor Studio" in res.text
    assert '<span class="rail-label">Grading</span>' in res.text


def test_fonts_are_served_locally(live_server):
    """The tool must work with no internet access, so fonts cannot come from a CDN."""
    page = requests.get(live_server + "/", timeout=10).text
    assert "fonts.googleapis.com" not in page
    assert "fonts.gstatic.com" not in page

    css = requests.get(live_server + "/static/css/fonts.css", timeout=10)
    assert css.status_code == 200
    assert "gstatic" not in css.text


def test_teacher_generate_then_student_evaluate(live_server):
    sample_xml_path = os.path.join(PROJECT_ROOT, "tests", "fixtures", "sample_topology.xml")
    with open(sample_xml_path, "rb") as f:
        xml_bytes = f.read()

    gen_res = requests.post(
        live_server + "/api/criteria/generate",
        files=[("files", ("sample_topology.xml", xml_bytes, "application/xml"))],
        data={"lab_title": "Enterprise CCNA Campus Network", "total_points": 100.0},
        timeout=60,
    )
    assert gen_res.status_code == 200
    gen_data = gen_res.json()
    assert "criteria" in gen_data
    assert "instructions_txt" in gen_data
    instructions_txt = gen_data["instructions_txt"]
    assert "Enterprise CCNA Campus Network" in instructions_txt
    assert "--- CRITERIA SPEC START ---" in instructions_txt

    eval_res = requests.post(
        live_server + "/api/evaluate",
        files=[
            ("instructions_file", ("instructions.txt", instructions_txt.encode("utf-8"), "text/plain")),
            ("student_files", ("student_sub.xml", xml_bytes, "application/xml")),
        ],
        timeout=60,
    )
    assert eval_res.status_code == 200
    eval_data = eval_res.json()

    # The reference file graded against its own rubric must score perfectly.
    assert eval_data["percentage"] == 100.0
    assert eval_data["grade_letter"] in ("A", "A+")
    assert eval_data["passed_count"] > 0
    assert eval_data["failed_count"] == 0
