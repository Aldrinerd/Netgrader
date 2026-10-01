# tests/test_js_units.py
"""Runs the JavaScript unit tests in tests/js with Node's built-in runner."""
import glob
import os
import shutil
import subprocess

import pytest

JS_TESTS = os.path.join(os.path.dirname(__file__), "js")


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_unit_tests_pass():
    files = sorted(glob.glob(os.path.join(JS_TESTS, "*.test.mjs")))
    if not files:
        pytest.skip("no JS unit tests yet")
    result = subprocess.run(["node", "--test", *files], capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stdout + result.stderr
