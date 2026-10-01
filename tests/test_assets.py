# tests/test_assets.py
"""
Modules are served from /assets/<version>/js/<path>. Relative imports between
them inherit the version, so a deployed fix reaches every browser. These tests
pin the route's safety and the version's sensitivity to nested files.
"""
import os
import time

import pytest
from fastapi.testclient import TestClient

from src import app as app_module
from src.app import app

client = TestClient(app)
JS_DIR = os.path.join(app_module.STATIC_DIR, "js")


@pytest.fixture
def nested_module():
    folder = os.path.join(JS_DIR, "zz_test_nested")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "probe.js")
    with open(path, "w", encoding="utf-8") as f:
        f.write("export const probe = 1;\n")
    other = os.path.join(folder, "notes.txt")
    with open(other, "w", encoding="utf-8") as f:
        f.write("not a module\n")
    yield path
    os.remove(path)
    os.remove(other)
    os.rmdir(folder)


def test_serves_a_module_with_javascript_type(nested_module):
    res = client.get("/assets/123/js/zz_test_nested/probe.js")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/javascript")
    assert "export const probe" in res.text


def test_versioned_modules_are_cached_long_term(nested_module):
    res = client.get("/assets/123/js/zz_test_nested/probe.js")
    assert "immutable" in res.headers["cache-control"]


@pytest.mark.parametrize("path", [
    "../../src/app.py",
    "..%2F..%2Fsrc%2Fapp.py",
    "%2e%2e/%2e%2e/src/app.py",
    "..\\..\\src\\app.py",
    "/etc/passwd",
    "C:/Windows/win.ini",
])
def test_rejects_paths_outside_the_js_folder(path):
    res = client.get(f"/assets/1/js/{path}")
    assert res.status_code == 404


def test_rejects_non_javascript_files_inside_the_js_folder(nested_module):
    assert client.get("/assets/1/js/zz_test_nested/notes.txt").status_code == 404


def test_missing_module_is_404():
    assert client.get("/assets/1/js/does/not/exist.js").status_code == 404


def test_asset_version_sees_nested_files(nested_module):
    before = app_module._asset_version()
    future = time.time() + 120
    os.utime(nested_module, (future, future))
    assert app_module._asset_version() != before
