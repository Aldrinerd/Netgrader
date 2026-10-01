# tests/test_assets.py
"""
Modules are served from /assets/<version>/js/<path>. Relative imports between
them inherit the version, so a deployed fix reaches every browser. These tests
pin the route's safety and the version's sensitivity to nested files.
"""
import os
import re
import time
from unittest import mock

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


def test_page_loads_the_versioned_module_entry():
    html = client.get("/").text
    version = app_module._asset_version()
    assert f'<script type="module" src="/assets/{version}/js/main.js"></script>' in html
    assert "/static/js/app.js" not in html


def test_old_browsers_get_a_notice_instead_of_a_dead_page():
    html = client.get("/").text
    assert '<script src="/static/js/boot-check.js' in html
    assert re.search(r'<div id="unsupported-browser"[^>]*\bhidden\b', html)
    assert "unsupported.js" not in html


def test_entry_module_sets_the_booted_flag():
    with open(os.path.join(app_module.STATIC_DIR, "js", "main.js"), encoding="utf-8") as f:
        assert "window.__netgraderBooted = true" in f.read()


def test_entry_module_is_served():
    version = app_module._asset_version()
    res = client.get(f"/assets/{version}/js/main.js")
    assert res.status_code == 200
    assert "initLegacyApp" in res.text


def test_tokens_load_before_the_component_styles():
    html = client.get("/").text
    tokens = html.index("/static/css/tokens.css")
    legacy = html.index("/static/css/legacy.css")
    assert tokens < legacy
    assert "/static/css/style.css" not in html


def test_tokens_file_holds_the_custom_properties():
    with open(os.path.join(app_module.STATIC_DIR, "css", "tokens.css"), encoding="utf-8") as f:
        tokens = f.read()
    with open(os.path.join(app_module.STATIC_DIR, "css", "legacy.css"), encoding="utf-8") as f:
        legacy = f.read()
    assert ":root" in tokens and "--accent-blue" in tokens
    assert ":root {" not in legacy


@pytest.mark.parametrize("path", [
    "//attacker-host/share/x.js",
    "%5C%5Cattacker-host%5Cshare%5Cx.js",
    "C:/x.js",
    "%2E%2E/x.js",
    "a/%2E%2E/%2E%2E/x.js",
    "a//b.js",
    "%2E/main.js",   # the client would normalise a literal ./
    "%2E%2E%20/x.js",      # ".. " -- Windows strips the trailing space
    "a./x.js",             # "a."  -- Windows strips the trailing dot
    "core/dom.js.",        # ends in "." after ".js": not a .js path
])
def test_hostile_paths_never_touch_the_filesystem(path):
    # os.path.realpath on a UNC path opens it, which makes an SMB connection.
    with mock.patch("src.app.os.path.realpath", side_effect=AssertionError("touched disk")) as rp, \
         mock.patch("src.app.os.path.isfile", side_effect=AssertionError("touched disk")) as isf:
        res = client.get(f"/assets/1/js/{path}")
    assert res.status_code == 404
    rp.assert_not_called()
    isf.assert_not_called()


@pytest.fixture
def outside_js():
    path = os.path.join(app_module.STATIC_DIR, "zz_outside_probe.js")
    with open(path, "w", encoding="utf-8") as f:
        f.write("export const outside = 1;\n")
    yield path
    os.remove(path)


def test_js_outside_the_js_folder_is_not_served(outside_js):
    # %2E%2E survives the client; a literal ../ would be normalised away and
    # the test would pass on routing alone, proving nothing.
    assert client.get("/assets/1/js/%2E%2E/zz_outside_probe.js").status_code == 404


def test_legitimate_nested_modules_are_served():
    for p in ("legacy/app.js", "core/dom.js", "map/topology.js", "main.js"):
        assert client.get(f"/assets/1/js/{p}").status_code == 200, p


def test_legacy_notice_css_works_in_old_browsers():
    with open(os.path.join(app_module.STATIC_DIR, "css", "legacy.css"), encoding="utf-8") as f:
        css = f.read()
    block = re.search(r"\.unsupported-browser\s*\{(.*?)\}", css, re.S).group(1)
    assert "inset" not in block
    decls = [d.strip() for d in block.split(";") if d.strip()]
    for i, d in enumerate(decls):
        if "var(" in d:
            prop = d.split(":", 1)[0].strip()
            assert any(
                e.split(":", 1)[0].strip() == prop and "var(" not in e for e in decls[:i]
            ), f"{prop} lacks a literal fallback"


def test_display_settings_apply_before_any_stylesheet():
    html = client.get("/").text
    head = html[:html.index("</head>")]
    boot = head.index("/static/js/display-boot.js")
    first_css = head.index('rel="stylesheet"')
    assert boot < first_css
