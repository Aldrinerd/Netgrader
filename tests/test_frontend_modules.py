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
CLASSIC_SCRIPTS = {"boot-check.js", "display-boot.js"}      # classic scripts, not modules
INNERHTML_ALLOWED = ("legacy/", "core/dom.js")

# import { a, b as c } from './x.js'   |   import x from './x.js'   |   import * as x from './x.js'
IMPORT_RE = re.compile(r"import\s*(?:\{([^}]*)\}|[\w$]+|\*\s+as\s+[\w$]+)\s*from\s*['\"](\.{1,2}/[^'\"]+)['\"]")
SIDE_EFFECT_IMPORT_RE = re.compile(r"import\s*['\"](\.{1,2}/[^'\"]+)['\"]")
# export function a / export const a / export class a / export { a, b as c }
EXPORT_RE = re.compile(r"export\s+(?:async\s+)?(?:function\*?|const|let|class)\s+([A-Za-z_$][\w$]*)")
EXPORT_LIST_RE = re.compile(r"export\s*\{([^}]*)\}")
HTML_SINK_RE = re.compile(r"\.(?:innerHTML|outerHTML)\s*[+]?=(?!=)|\.insertAdjacentHTML\s*\(|document\.write(?:ln)?\s*\(")


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


def _exports_of(path):
    text = _read(path)
    exported = set(EXPORT_RE.findall(text))
    for items in EXPORT_LIST_RE.findall(text):
        for item in items.split(","):
            item = item.strip()
            if item:
                exported.add(item.split(" as ")[-1].strip())
    return exported


def test_relative_imports_resolve_to_real_exports():
    problems = []
    for rel, path in js_files():
        text = _read(path)
        for target in SIDE_EFFECT_IMPORT_RE.findall(text):
            target_path = os.path.normpath(os.path.join(os.path.dirname(path), target))
            if not os.path.isfile(target_path):
                problems.append(f"{rel}: imports missing file {target}")
        for names, target in IMPORT_RE.findall(text):
            target_path = os.path.normpath(os.path.join(os.path.dirname(path), target))
            if not os.path.isfile(target_path):
                problems.append(f"{rel}: imports missing file {target}")
                continue
            if not names:
                continue
            exported = _exports_of(target_path)
            for name in (n.strip().split(" as ")[0].strip() for n in names.split(",")):
                if name and name not in exported:
                    problems.append(f"{rel}: '{name}' is not exported by {target}")
    assert not problems, chr(10).join(problems)


def test_innerhtml_only_in_legacy_and_dom_helper():
    offenders = [
        rel for rel, path in js_files()
        if not rel.startswith(INNERHTML_ALLOWED) and HTML_SINK_RE.search(_read(path))
    ]
    assert not offenders, f"innerHTML assigned outside legacy/ and core/dom.js: {offenders}"


def render_page(instructor: bool) -> str:
    from src.app import app
    client = TestClient(app, client=("127.0.0.1", 50000) if instructor else ("10.20.30.40", 50000))
    return client.get("/").text


GET_BY_ID_RE = re.compile(r"getElementById\(\s*['\"]([\w-]+)['\"]\s*\)")
TEMPLATES = os.path.join(ROOT, "templates")


def _has_id(html: str, element_id: str) -> bool:
    return re.search(r'(?<![\w-])id="%s"' % re.escape(element_id), html) is not None


def _ids_in(path):
    return set(re.findall(r'id="([\w-]+)"', _read(path)))


def _ids_looked_up_by_js():
    found = set()
    for _rel, path in js_files():
        found |= set(GET_BY_ID_RE.findall(_read(path)))
    return found


def test_every_element_the_js_looks_up_exists_for_the_instructor():
    html = render_page(instructor=True)
    missing = sorted(i for i in _ids_looked_up_by_js() if not _has_id(html, i))
    assert not missing, f"JS looks up ids the instructor page lacks: {missing}"


def test_every_non_instructor_element_exists_for_students():
    """A lab PC gets no instructor markup; every other id the JS looks up must exist."""
    teacher_only = _ids_in(os.path.join(TEMPLATES, "partials", "panel_instructor.html")) | {"nav-mode-teacher"}
    html = render_page(instructor=False)
    missing = sorted(i for i in _ids_looked_up_by_js() - teacher_only if not _has_id(html, i))
    assert not missing, f"JS looks up ids the student page lacks: {missing}"
    assert not any(_has_id(html, i) for i in teacher_only), "instructor markup leaked to a student"


def _strip_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"(?<![:'\"])//[^\n]*", "", text)


@pytest.mark.parametrize("name", sorted(CLASSIC_SCRIPTS))
def test_classic_scripts_are_es5(name):
    code = _strip_comments(_read(os.path.join(JS_ROOT, name)))
    for pattern in (r"=>", r"`", r"\?\.", r"\.\.\.", r"\bconst\b", r"\blet\b", r"\bclass\b"):
        assert not re.search(pattern, code), f"{name} uses non-ES5 syntax: {pattern}"


def test_local_storage_is_only_touched_by_the_guarded_helpers():
    users = sorted(rel for rel, path in js_files() if "localStorage" in _read(path))
    assert users == ["core/storage.js", "display-boot.js"], users


def test_session_storage_is_only_touched_by_the_store():
    users = sorted(rel for rel, path in js_files() if "sessionStorage" in _read(path))
    assert users == ["core/store.js"], users
