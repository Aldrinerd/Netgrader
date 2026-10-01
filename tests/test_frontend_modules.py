# tests/test_frontend_modules.py
"""
Static checks over static/js. No browser needed.

- every module parses as an ES module (node --check)
- every relative import points at a file that exports the imported names
- innerHTML is assigned only in legacy/ and core/dom.js (issue #31)
"""
import os
import re
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient

ROOT = os.path.dirname(os.path.dirname(__file__))
JS_ROOT = os.path.join(ROOT, "static", "js")
CLASSIC_SCRIPTS = {"unsupported.js"}      # loaded with nomodule, not as a module
INNERHTML_ALLOWED = ("legacy/", "core/dom.js")

IMPORT_RE = re.compile(r"import\s*\{([^}]*)\}\s*from\s*['\"](\.{1,2}/[^'\"]+)['\"]")
EXPORT_RE = re.compile(r"export\s+(?:async\s+)?(?:function|const|let|class)\s+([A-Za-z_$][\w$]*)")


def js_files():
    out = []
    for root, _dirs, files in os.walk(JS_ROOT):
        for name in files:
            if name.endswith(".js"):
                full = os.path.join(root, name)
                out.append((os.path.relpath(full, JS_ROOT).replace("\\", "/"), full))
    return sorted(out)


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
@pytest.mark.parametrize("rel,path", js_files())
def test_module_parses(rel, path):
    mode = "commonjs" if rel in CLASSIC_SCRIPTS else "module"
    result = subprocess.run(
        ["node", f"--input-type={mode}", "--check"],
        input=_read(path), capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0, f"{rel}: {result.stderr}"


def test_relative_imports_resolve_to_real_exports():
    problems = []
    for rel, path in js_files():
        for names, target in IMPORT_RE.findall(_read(path)):
            target_path = os.path.normpath(os.path.join(os.path.dirname(path), target))
            if not os.path.isfile(target_path):
                problems.append(f"{rel}: imports missing file {target}")
                continue
            exported = set(EXPORT_RE.findall(_read(target_path)))
            for name in (n.strip().split(" as ")[0] for n in names.split(",")):
                if name and name not in exported:
                    problems.append(f"{rel}: '{name}' is not exported by {target}")
    assert not problems, "\n".join(problems)


def test_innerhtml_only_in_legacy_and_dom_helper():
    offenders = [
        rel for rel, path in js_files()
        if not rel.startswith(INNERHTML_ALLOWED) and re.search(r"\.innerHTML\s*[+]?=", _read(path))
    ]
    assert not offenders, f"innerHTML assigned outside legacy/ and core/dom.js: {offenders}"


def render_page(instructor: bool) -> str:
    from src.app import app
    client = TestClient(app, client=("127.0.0.1", 50000) if instructor else ("10.20.30.40", 50000))
    return client.get("/").text


GET_BY_ID_RE = re.compile(r"getElementById\(\s*['\"]([\w-]+)['\"]\s*\)")
TEMPLATES = os.path.join(ROOT, "templates")


def _ids_in(path):
    return set(re.findall(r'id="([\w-]+)"', _read(path)))


def _ids_looked_up_by_js():
    found = set()
    for _rel, path in js_files():
        found |= set(GET_BY_ID_RE.findall(_read(path)))
    return found


def test_every_element_the_js_looks_up_exists_for_the_instructor():
    html = render_page(instructor=True)
    missing = sorted(i for i in _ids_looked_up_by_js() if f'id="{i}"' not in html)
    assert not missing, f"JS looks up ids the instructor page lacks: {missing}"


def test_every_non_instructor_element_exists_for_students():
    """Review focus 1: a lab PC gets no instructor markup; everything else must exist."""
    teacher_only = _ids_in(os.path.join(TEMPLATES, "partials", "panel_instructor.html")) | {"nav-mode-teacher"}
    html = render_page(instructor=False)
    missing = sorted(i for i in _ids_looked_up_by_js() - teacher_only if f'id="{i}"' not in html)
    assert not missing, f"JS looks up ids the student page lacks: {missing}"
    assert not any(f'id="{i}"' in html for i in teacher_only), "instructor markup leaked to a student"
