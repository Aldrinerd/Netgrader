# UI Refresh PR 1: Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the frontend into native ES modules, Jinja partials and a token stylesheet, with **no visible change**, so PRs 2 to 5 of the UI refresh each land in one place.

**Architecture:** `static/js/app.js` becomes `static/js/legacy/app.js`, an exported `initLegacyApp()` started by `static/js/main.js`. Shared pieces move out into `core/` and `map/` modules, and the legacy file imports them. It shrinks in later PRs as screens are rewritten. Modules are served from a versioned path, `/assets/<version>/js/...`, and import each other with **relative** paths. A relative import from a versioned URL is itself versioned, so a deployed fix reaches every browser without an import map or a build step. `index.html` becomes `base.html` plus one partial per screen. `style.css` becomes `tokens.css` plus `legacy.css`.

**Tech Stack:** Python 3.12, FastAPI, Jinja2, pytest; browser-native ES modules; Node 24 (developer machines only, for `node --test` and `node --check`).

**Spec:** `docs/superpowers/specs/2026-10-01-ui-refresh-design.md` (sections 3, 9.1 and 10, PR 1)

**Refinements to the spec, decided while planning:**
- Spec 3.1 shows an import map. Relative imports from a versioned entry URL give the same cache-busting with less machinery, so no import map is used. The route is `/assets/<version>/js/<path>` rather than `/static/js/<version>/...`, because `/static` is already a Starlette mount that would shadow it.
- The Tabler icon sprite moves to PR 2, where icons are first used. Nothing in PR 1 would reference it.
- Spec 10 says PR 1 splits `style.css` into token, base, component and layout files. PR 1 splits only `tokens.css` from the rest (`legacy.css`). Base, component and layout files are created in PRs 2 to 4 as each component is restyled, since splitting rules that are about to be rewritten is wasted work.
- `chat/`, `report/`, `shell/` and `screens/` modules from spec 3.2 are created in PRs 2 to 4, when their code is rewritten. PR 1 extracts only what survives the refresh unchanged: `core/dom.js`, `core/api.js`, `core/toast.js`, `map/svg-shapes.js` and `map/topology.js`.

## Global Constraints

- No build step, no bundler, no new runtime dependency. Lab PCs install nothing new.
- Must work fully offline: no CDN, no external URL in any template, script or stylesheet.
- No visible or behavioural change in this PR. Same markup ids, same classes, same rendered pixels.
- Jinja's `{% if is_instructor %}` gating of the Instructor tab and panel is preserved exactly. `require_instructor` stays the real guard.
- Every value from an uploaded file or filename reaches the page only through `escapeHtml()` or `textContent` (issue #31). Modules outside `static/js/legacy/` and `static/js/core/dom.js` must not assign `innerHTML` at all.
- `python -m pytest -q` and `python -m validation` pass after every task.
- Commit messages: conventional prefix (`feat:`, `refactor:`, `test:`, `docs:`), body explaining why, ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **A lab PC (non-instructor) loading the page.** Its HTML has no Instructor markup, so every teacher element lookup returns `null`. The module must load and every student flow must work without a console error. Tested by the id-coverage test in Task 6 (every non-teacher id the JS looks up exists in the student page) and by a browser check in Task 8.
2. **Editing a nested module after deploy.** If `_asset_version()` only looked at the top level of `static/js/`, a change to `static/js/map/topology.js` would not change the version, and students would keep a stale map. Tested in Task 1.
3. **Path traversal on the new asset route**, for example `../`, `%2e%2e`, backslashes and absolute paths, must never serve anything outside `static/js/` or any non-`.js` file. Tested in Task 1.
4. **An old browser that cannot run ES modules** must show a readable "this browser is not supported" notice instead of a dead page. Tested in Task 3.
5. **Map interactions after extraction:** zoom, pan, node drag, the port and IP label toggles, fit, Reset View, the node and link drawers, and batch Review's red rings must behave exactly as before. Checked in the Task 8 browser walkthrough.

---

## File Structure

| Path | Status | Responsibility |
|---|---|---|
| `src/app.py` | Modify | Recursive `_asset_version()`, new `/assets/{version}/js/{path}` route |
| `templates/base.html` | Create | Document shell: head, layout grid, toast container, module script |
| `templates/partials/navbar.html` | Create | Header and mode tabs |
| `templates/partials/panel_discovery.html` | Create | Discovery control panel |
| `templates/partials/panel_instructor.html` | Create | Instructor Studio and batch grading panel |
| `templates/partials/panel_grading.html` | Create | Student grading panel |
| `templates/partials/visualizer.html` | Create | Map canvas, toolbar, diagnostic drawer |
| `templates/index.html` | Delete | Replaced by `base.html` and partials |
| `static/js/main.js` | Create | Entry point: imports and starts the app |
| `static/js/unsupported.js` | Create | Classic script, `nomodule` only: shows the old-browser notice |
| `static/js/legacy/app.js` | Create (moved) | Today's `app.js`, wrapped in `export function initLegacyApp()` |
| `static/js/app.js` | Delete | Moved |
| `static/js/core/dom.js` | Create | `escapeHtml(text)` |
| `static/js/core/api.js` | Create | `describeFailure(res, fallback)` |
| `static/js/core/toast.js` | Create | `showToast(container, msg, duration)` |
| `static/js/map/svg-shapes.js` | Create | `shortInterfaceName`, `createSvgBadge`, `createDeviceIcon` |
| `static/js/map/topology.js` | Create | `createTopologyMap(svg, callbacks)`: layout, draw, zoom, pan, drag |
| `static/css/tokens.css` | Create | The `:root` custom properties from `style.css` |
| `static/css/legacy.css` | Create (moved) | The rest of `style.css` |
| `static/css/style.css` | Delete | Split |
| `tests/test_assets.py` | Create | Asset route and version tests |
| `tests/test_frontend_modules.py` | Create | Module syntax, import graph, `innerHTML` boundary, id coverage |
| `tests/test_frontend_escaping.py` | Modify | Scan every module, not only `app.js` |
| `tests/test_js_units.py` | Create | Runs `node --test tests/js/` |
| `tests/js/core.test.mjs` | Create | Unit tests for `core/` |
| `tests/js/svg-shapes.test.mjs` | Create | Unit tests for `shortInterfaceName` |
| `docs/SYSTEM.md` | Modify | Frontend structure section |

---

### Task 1: Versioned module route and recursive asset version

**Files:**
- Modify: `src/app.py` (function `_asset_version`, new route after `index_page`)
- Test: `tests/test_assets.py`

**Interfaces:**
- Produces: `GET /assets/{version}/js/{path}` serves `static/js/{path}` as `text/javascript`. `_asset_version()` returns a string that changes when any file under `static/css/` or `static/js/`, at any depth, changes.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_assets.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_assets.py -q`
Expected: FAIL. The serve tests return 404 (no route), and `test_asset_version_sees_nested_files` fails because the scan is not recursive. The traversal tests may already pass by accident (404 from no route). That's fine: they must still pass after Step 3.

- [ ] **Step 3: Implement**

In `src/app.py`, add `FileResponse` to the existing `fastapi.responses` import:

```python
from fastapi.responses import FileResponse, HTMLResponse
```

Replace the loop inside `_asset_version()` (keep the docstring) with a recursive walk:

```python
    newest = 0.0
    for folder in (os.path.join(STATIC_DIR, "css"), os.path.join(STATIC_DIR, "js")):
        # Recursive: modules live in subfolders (core/, map/, legacy/), and a
        # change to any of them must change the version.
        for root, _dirs, files in os.walk(folder):
            for name in files:
                try:
                    newest = max(newest, os.path.getmtime(os.path.join(root, name)))
                except OSError:
                    continue
    return str(int(newest))
```

Add after the `index_page` route:

```python
JS_DIR = os.path.realpath(os.path.join(STATIC_DIR, "js"))


@app.get("/assets/{version}/js/{path:path}")
def versioned_module(version: str, path: str):
    """
    Serve a JavaScript module under a versioned URL.

    The page loads /assets/<version>/js/main.js, and every relative import
    inside it resolves under the same versioned prefix, so a new deploy
    changes every module URL at once. The version itself is not checked:
    an old page asking for an old version gets the current file, which is
    what a refresh would do anyway.
    """
    candidate = os.path.realpath(os.path.join(JS_DIR, path))
    try:
        inside = os.path.commonpath([candidate, JS_DIR]) == JS_DIR
    except ValueError:   # different drive on Windows
        inside = False
    if not inside or not candidate.endswith(".js") or not os.path.isfile(candidate):
        raise HTTPException(status_code=404)
    return FileResponse(
        candidate,
        media_type="text/javascript",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_assets.py -q`
Expected: all pass.
Run: `python -m pytest -q`
Expected: all pass (the existing suite is unaffected).

- [ ] **Step 5: Commit**

```bash
git add src/app.py tests/test_assets.py
git commit -m "feat(app): serve JS modules from a versioned path" -m "Modules import each other with relative paths, so serving the entry from /assets/<version>/js/ versions every import with no import map or build step. The asset version now walks subfolders, so editing a nested module changes it. The route refuses anything outside static/js and anything that is not a .js file." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Frontend static checks across every module

**Files:**
- Create: `tests/test_frontend_modules.py`, `tests/test_js_units.py`, `tests/js/.gitkeep`
- Modify: `tests/test_frontend_escaping.py`

**Interfaces:**
- Produces: helper `js_files()` in `tests/test_frontend_modules.py` returning every `.js` under `static/js/`. Later tasks add files and these tests cover them automatically.

- [ ] **Step 1: Generalise the escaping test to every module**

In `tests/test_frontend_escaping.py`, replace the `APP_JS` constant and the three test functions' file reads so they scan all modules. Replace:

```python
APP_JS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "js", "app.js")
```

with:

```python
JS_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "js")


def _js_sources():
    for root, _dirs, files in os.walk(JS_ROOT):
        for name in sorted(files):
            if name.endswith(".js"):
                path = os.path.join(root, name)
                with open(path, encoding="utf-8") as f:
                    yield os.path.relpath(path, JS_ROOT).replace("\\", "/"), f.read()
```

In `_unsafe_interpolations`, change the hit label from `f"app.js:{lineno}: ..."` to take a filename parameter:

```python
def _unsafe_interpolations(source: str, filename: str = "app.js") -> list[str]:
```

and inside, `hits.append(f"{filename}:{lineno}: ${{{expr}}}")`.

Replace `test_untrusted_fields_are_escaped_before_reaching_html` with:

```python
def test_untrusted_fields_are_escaped_before_reaching_html():
    hits = []
    for name, source in _js_sources():
        hits += _unsafe_interpolations(source, name)
    assert not hits, "Unescaped untrusted values in HTML templates:\n" + "\n".join(hits)
```

Replace the bodies of `test_toast_renders_text_not_html` and `test_escape_helper_covers_attribute_quotes` so they find the function in whichever module defines it:

```python
def _function_body(name: str) -> str:
    """The function's text up to its closing brace, top-level or indented once."""
    for _file, source in _js_sources():
        marker = f"function {name}"
        if marker in source:
            body = source[source.index(marker):]
            ends = [i for i in (body.find("\n}\n"), body.find("\n    }\n")) if i != -1]
            return body[:min(ends)] if ends else body
    raise AssertionError(f"{name} not found in any module")


def test_toast_renders_text_not_html():
    assert "innerHTML" not in _function_body("showToast")


def test_escape_helper_covers_attribute_quotes():
    helper = _function_body("escapeHtml")
    assert "&quot;" in helper and "&#39;" in helper
```

- [ ] **Step 2: Write the module checks**

Create `tests/test_frontend_modules.py`:

```python
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
```

Create `tests/test_js_units.py`:

```python
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
```

Create an empty `tests/js/.gitkeep`.

- [ ] **Step 3: Run the checks**

Run: `python -m pytest tests/test_frontend_modules.py tests/test_frontend_escaping.py tests/test_js_units.py -q`
Expected: everything passes except `test_innerhtml_only_in_legacy_and_dom_helper`, which fails listing `app.js`. That is correct: `app.js` is not under `legacy/` until Task 3. Add `@pytest.mark.xfail(strict=True, reason="fixed by moving app.js into legacy/ in Task 3")` above that test, rerun, and confirm it reports `xfailed`. Task 3 removes the marker.

- [ ] **Step 4: Commit**

```bash
git add tests/test_frontend_modules.py tests/test_js_units.py tests/test_frontend_escaping.py tests/js/.gitkeep
git commit -m "test(frontend): static checks across every JS module" -m "Module syntax via node --check, relative imports resolving to real exports, innerHTML confined to legacy/ and core/dom.js, and the #31 escaping scan over every file instead of only app.js." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Load the app as an ES module

**Files:**
- Create: `static/js/main.js`, `static/js/unsupported.js`, `static/js/legacy/app.js` (moved)
- Delete: `static/js/app.js`
- Modify: `templates/index.html` (script tags, notice element), `static/css/style.css` (notice style)
- Test: `tests/test_assets.py` (add page tests)

**Interfaces:**
- Produces: `export function initLegacyApp()` in `static/js/legacy/app.js`. `main.js` calls it once.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_assets.py`:

```python
def test_page_loads_the_versioned_module_entry():
    html = client.get("/").text
    version = app_module._asset_version()
    assert f'<script type="module" src="/assets/{version}/js/main.js"></script>' in html
    assert "/static/js/app.js" not in html


def test_old_browsers_get_a_notice_instead_of_a_dead_page():
    html = client.get("/").text
    assert '<script nomodule src="/static/js/unsupported.js' in html
    assert 'id="unsupported-browser"' in html


def test_entry_module_is_served():
    version = app_module._asset_version()
    res = client.get(f"/assets/{version}/js/main.js")
    assert res.status_code == 200
    assert "initLegacyApp" in res.text
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/test_assets.py -q`
Expected: the three new tests FAIL.

- [ ] **Step 3: Move and wrap the app**

```bash
mkdir -p static/js/legacy
git mv static/js/app.js static/js/legacy/app.js
```

In `static/js/legacy/app.js` replace the first two lines:

```js
// static/js/app.js
document.addEventListener('DOMContentLoaded', () => {
```

with:

```js
// static/js/legacy/app.js
// The pre-refresh UI, moved here unchanged and started by main.js. Pieces
// leave this file as the UI refresh rewrites each screen (spec 2026-10-01).
export function initLegacyApp() {
```

and replace the last line of the file, `});`, with `}`.

Create `static/js/main.js`:

```js
// static/js/main.js
// Entry point. Loaded as a module from /assets/<version>/js/main.js, so every
// relative import below is versioned too.
import { initLegacyApp } from './legacy/app.js';

initLegacyApp();
```

Modules are deferred: they run after the document is parsed, so the element lookups at the top of `initLegacyApp` find their elements, exactly as the `DOMContentLoaded` handler did.

Create `static/js/unsupported.js`:

```js
// static/js/unsupported.js
// Loaded with <script nomodule>: only browsers that cannot run ES modules
// execute it. Shows the notice instead of leaving a page that does nothing.
var notice = document.getElementById('unsupported-browser');
if (notice) { notice.hidden = false; }
```

In `templates/index.html`, replace:

```html
    <script src="/static/js/app.js?v={{ asset_version }}"></script>
```

with:

```html
    <div id="unsupported-browser" class="unsupported-browser" hidden>
        This browser is too old to run Netgrader. Please use a current version of
        Chrome, Edge or Firefox.
    </div>
    <script nomodule src="/static/js/unsupported.js?v={{ asset_version }}"></script>
    <script type="module" src="/assets/{{ asset_version }}/js/main.js"></script>
```

Append to `static/css/style.css`:

```css
/* Shown only by unsupported.js, in browsers without ES module support. */
.unsupported-browser {
    position: fixed;
    inset: auto 16px 16px 16px;
    padding: 12px 16px;
    border-radius: var(--radius-md);
    background: var(--accent-red);
    color: var(--text-primary);
    font-size: 1rem;
    z-index: 1000;
}
```

Remove the `@pytest.mark.xfail(...)` line added to `test_innerhtml_only_in_legacy_and_dom_helper` in Task 2.

- [ ] **Step 4: Run all tests**

Run: `python -m pytest -q`
Expected: all pass, including `test_module_parses[legacy/app.js-...]`, `test_module_parses[main.js-...]` and the innerHTML boundary test.

- [ ] **Step 5: Smoke-check in the browser**

Start the app with the `neteval` preview configuration in `.claude/launch.json` (`python -m uvicorn src.app:app --host 0.0.0.0 --port 8765`). Open `http://localhost:8765/`. In the browser console:
- No errors on load.
- Click each mode tab: panels switch as before.
- Upload `tests/fixtures/sample_topology.xml` in Topology Discovery and click Analyze: the map draws 12 devices.

- [ ] **Step 6: Commit**

```bash
git add static/js templates/index.html static/css/style.css tests/test_assets.py tests/test_frontend_modules.py
git commit -m "refactor(frontend): load the app as an ES module" -m "app.js moves unchanged to legacy/app.js as initLegacyApp(), started by main.js from the versioned asset path. Browsers without module support get a visible notice from a nomodule script instead of a page that silently does nothing." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Extract the core helpers

**Files:**
- Create: `static/js/core/dom.js`, `static/js/core/api.js`, `static/js/core/toast.js`, `tests/js/core.test.mjs`
- Modify: `static/js/legacy/app.js`

**Interfaces:**
- Produces:
  - `escapeHtml(text: any): string` from `core/dom.js`
  - `describeFailure(res: Response, fallback?: string): Promise<string>` from `core/api.js`
  - `showToast(container: HTMLElement | null, msg: string, duration?: number): void` from `core/toast.js`

- [ ] **Step 1: Write the failing unit tests**

Create `tests/js/core.test.mjs`:

```js
// tests/js/core.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { escapeHtml } from '../../static/js/core/dom.js';
import { describeFailure } from '../../static/js/core/api.js';

test('escapeHtml escapes the five HTML-significant characters', () => {
    assert.equal(escapeHtml(`<a href="x" title='y'>&</a>`),
        '&lt;a href=&quot;x&quot; title=&#39;y&#39;&gt;&amp;&lt;/a&gt;');
});

test('escapeHtml turns null and undefined into an empty string', () => {
    assert.equal(escapeHtml(null), '');
    assert.equal(escapeHtml(undefined), '');
});

test('escapeHtml stringifies numbers', () => {
    assert.equal(escapeHtml(82.5), '82.5');
});

const fakeResponse = (body, { json = true, status = 500, statusText = 'Server Error' } = {}) => ({
    status, statusText,
    json: async () => { if (!json) throw new SyntaxError('not json'); return body; },
});

test('describeFailure returns a string detail', async () => {
    assert.equal(await describeFailure(fakeResponse({ detail: 'bad file' })), 'bad file');
});

test('describeFailure serialises a structured detail', async () => {
    assert.equal(await describeFailure(fakeResponse({ detail: [{ loc: ['x'] }] })), '[{"loc":["x"]}]');
});

test('describeFailure falls back when the body is not JSON', async () => {
    assert.equal(await describeFailure(fakeResponse(null, { json: false }), 'Upload failed'), 'Upload failed');
    assert.equal(await describeFailure(fakeResponse(null, { json: false })), 'Server error 500 Server Error');
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `node --test tests/js/core.test.mjs`
Expected: FAIL with `ERR_MODULE_NOT_FOUND` for `core/dom.js`.

- [ ] **Step 3: Create the modules**

`static/js/core/dom.js`:

```js
// static/js/core/dom.js
// The only module allowed to build markup from strings. Anything taken from
// an uploaded file (device names, descriptions, config lines) or a filename
// must pass through escapeHtml before reaching innerHTML (issue #31).

// Escapes for both element content and quoted attribute values.
export function escapeHtml(text) {
    return (text == null ? '' : String(text))
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
```

`static/js/core/api.js`:

```js
// static/js/core/api.js

// Reads an error body that may not be JSON (a proxy or crash can return HTML).
export async function describeFailure(res, fallback) {
    try {
        const body = await res.json();
        if (body && body.detail) {
            return typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
        }
    } catch (e) { /* response was not JSON */ }
    return fallback || `Server error ${res.status} ${res.statusText}`;
}
```

`static/js/core/toast.js`:

```js
// static/js/core/toast.js

// Text only: some messages carry a student's filename.
export function showToast(container, msg, duration = 3000) {
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = 'toast';
    const icon = document.createElement('span');
    icon.textContent = '✨';
    const text = document.createElement('span');
    text.textContent = msg;
    toast.append(icon, text);
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-10px)';
        toast.style.transition = 'all 0.25s ease';
        setTimeout(() => toast.remove(), 250);
    }, duration);
}
```

(The sparkle emoji stays until PR 2 removes all emoji, keeping this PR free of visible change.)

- [ ] **Step 4: Use them from the legacy file**

At the top of `static/js/legacy/app.js`, after the header comment and before `export function initLegacyApp() {`:

```js
import { escapeHtml } from '../core/dom.js';
import { describeFailure } from '../core/api.js';
import { showToast as showToastIn } from '../core/toast.js';
```

Inside `initLegacyApp`, delete the local `escapeHtml` function (the block starting `// Escapes for both element content and quoted attribute values.`) and the local `describeFailure` function (starting `// Reads an error body that may not be JSON`).

Replace the local `showToast` function (the block starting `// Helper: Toast Notifications`) with:

```js
    // Helper: Toast Notifications
    function showToast(msg, duration = 3000) {
        showToastIn(toastContainer, msg, duration);
    }
```

The wrapper keeps every existing `showToast(msg)` call unchanged.

- [ ] **Step 5: Run all tests**

Run: `node --test tests/js/core.test.mjs`
Expected: 6 tests pass.
Run: `python -m pytest -q`
Expected: all pass. `test_relative_imports_resolve_to_real_exports` confirms the three imports, and `test_toast_renders_text_not_html` finds `showToast` in `core/toast.js`.

- [ ] **Step 6: Commit**

```bash
git add static/js/core tests/js/core.test.mjs static/js/legacy/app.js
git commit -m "refactor(frontend): extract escapeHtml, describeFailure and showToast" -m "The first shared modules. core/dom.js is the one place allowed to build markup from strings, so the #31 rule now has a home." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Extract the topology map

**Files:**
- Create: `static/js/map/svg-shapes.js`, `static/js/map/topology.js`, `tests/js/svg-shapes.test.mjs`
- Modify: `static/js/legacy/app.js`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces, from `map/topology.js`:

```
createTopologyMap(svg: SVGSVGElement, {
    onNodeSelect?: (device) => void,
    onLinkSelect?: (link) => void,
}) => {
    render(data: TopologyResult, opts?: { highlightDevices?: Iterable<string> }): void,
    fit(): void,
    redraw(): void,
    reset(): void,
    setLabels(next: { ports?: boolean, ips?: boolean }): void,
    getLabels(): { ports: boolean, ips: boolean },
    getTopology(): TopologyResult | null,
    isInteracting(): boolean,
}
```

- Produces, from `map/svg-shapes.js`: `shortInterfaceName(name)`, `createSvgBadge(x, y, text, badgeClass, isIp)`, `createDeviceIcon(x, y, color, kind)`.

- [ ] **Step 1: Write the failing unit test**

Create `tests/js/svg-shapes.test.mjs`:

```js
// tests/js/svg-shapes.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { shortInterfaceName } from '../../static/js/map/svg-shapes.js';

test('shortens the interface families shown on the map', () => {
    assert.equal(shortInterfaceName('GigabitEthernet0/1'), 'Gi0/1');
    assert.equal(shortInterfaceName('FastEthernet0'), 'Fa0');
    assert.equal(shortInterfaceName('Serial0/0/0'), 'Se0/0/0');
    assert.equal(shortInterfaceName('Port-channel1'), 'Po1');
    assert.equal(shortInterfaceName('Vlan10'), 'Vl10');
});

test('hides unknown or unspecified ports', () => {
    assert.equal(shortInterfaceName(''), '');
    assert.equal(shortInterfaceName(null), '');
    assert.equal(shortInterfaceName('Unspecified'), '');
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `node --test tests/js/svg-shapes.test.mjs`
Expected: FAIL, module not found.

- [ ] **Step 3: Create `map/svg-shapes.js`**

Move three functions out of `legacy/app.js` **verbatim**, exported:
- `shortInterfaceName` (block starting `// Helper: Short interface names`)
- `createSvgBadge` (starting `function createSvgBadge(`)
- `createDeviceIcon` (starting with the `/** Device icons drawn as silhouettes...` comment)

The file:

```js
// static/js/map/svg-shapes.js
// SVG building blocks for the topology map. Pure functions: no module state.

// Short interface names for map labels.
export function shortInterfaceName(name) {
    // body moved verbatim from legacy/app.js
}

export function createSvgBadge(x, y, text, badgeClass = 'port-label-badge', isIp = false) {
    // body moved verbatim from legacy/app.js
}

/**
 * (doc comment moved verbatim)
 */
export function createDeviceIcon(x, y, color, kind) {
    // body moved verbatim from legacy/app.js
}
```

Each `// body moved verbatim` line is replaced by the exact original body. No logic changes. Delete the three functions from `legacy/app.js`.

- [ ] **Step 4: Create `map/topology.js`**

```js
// static/js/map/topology.js
// The interactive topology map: layout, drawing, zoom, pan and node drag.
// Owns all map state; the rest of the UI talks to it through the returned API.
import { createSvgBadge, createDeviceIcon, shortInterfaceName } from './svg-shapes.js';

const SVG_NS = 'http://www.w3.org/2000/svg';

export function createTopologyMap(svg, { onNodeSelect = () => {}, onLinkSelect = () => {} } = {}) {
    let topology = null;
    let nodes = [];
    let links = [];
    let highlighted = new Set();
    let view = { x: 0, y: 0, k: 1 };
    let labels = { ports: true, ips: false };
    let draggedNode = null;
    let isPanning = false;
    let panStartX = 0;
    let panStartY = 0;

    function applyTransform() {
        const g = svg.querySelector('#graph-root');
        if (g) g.setAttribute('transform', `translate(${view.x}, ${view.y}) scale(${view.k})`);
    }

    function render(data, { highlightDevices = [] } = {}) {
        topology = data;
        highlighted = new Set(highlightDevices);
        svg.replaceChildren();

        const devEntries = Object.entries(data.devices || {});
        const hasCoordinates = devEntries.some(([_, d]) => d.x_coord !== null && d.y_coord !== null);

        if (hasCoordinates) {
            nodes = devEntries.map(([devKey, d]) => ({
                id: devKey,
                device: d,
                x: d.x_coord !== null ? d.x_coord : 400,
                y: d.y_coord !== null ? d.y_coord : 300,
            }));
        } else {
            const radius = 220;
            const centerX = 450;
            const centerY = 320;
            nodes = devEntries.map(([devKey, d], idx) => {
                const angle = (idx / devEntries.length) * 2 * Math.PI - Math.PI / 2;
                return {
                    id: devKey,
                    device: d,
                    x: centerX + radius * Math.cos(angle),
                    y: centerY + radius * Math.sin(angle),
                };
            });
        }

        links = (data.links || []).map(l => ({
            data: l,
            source: nodes.find(n => n.id === l.source_device) || { x: 200, y: 200, id: l.source_device },
            target: nodes.find(n => n.id === l.target_device) || { x: 400, y: 200, id: l.target_device },
        }));

        fit();
    }

    function fit() {
        // Body of the former fitGraphToViewport(), with these renames:
        //   simulationNodes -> nodes, viewTransform -> view, drawSvgGraph() -> draw()
    }

    function draw() {
        // Body of the former drawSvgGraph(), with these renames:
        //   svg.innerHTML = ''            -> svg.replaceChildren()
        //   simulationLinks               -> links
        //   simulationNodes               -> nodes
        //   viewTransform                 -> view
        //   showPortLabels                -> labels.ports
        //   showIpLabels                  -> labels.ips
        //   currentTopology               -> topology
        //   highlightedDevices            -> highlighted
        //   openEdgeDiagnosticDrawer(link)-> onLinkSelect(link)
        //   openNodeDiagnosticDrawer(dev) -> onNodeSelect(dev)
        //   isDraggingNode = true; draggedNode = node;  -> draggedNode = node;
        //   'http://www.w3.org/2000/svg'  -> SVG_NS
    }

    function reset() {
        topology = null;
        nodes = [];
        links = [];
        highlighted = new Set();
        view = { x: 0, y: 0, k: 1 };
        svg.replaceChildren();
    }

    function setLabels(next) {
        labels = { ...labels, ...next };
        draw();
    }

    // Zoom, pan and drag. Moved from the former "Interactive Mouse Zoom & Pan"
    // block, with the same renames, and with
    //   if (isDraggingNode && draggedNode)   -> if (draggedNode)
    //   isDraggingNode = false; draggedNode = null;  -> draggedNode = null;
    //   the two inline g.setAttribute('transform', ...) calls -> applyTransform()
    svg.addEventListener('wheel', (e) => { /* moved */ }, { passive: false });
    svg.addEventListener('mousedown', (e) => { /* moved */ });
    window.addEventListener('mousemove', (e) => { /* moved */ });
    window.addEventListener('mouseup', () => { /* moved */ });

    return {
        render,
        fit,
        redraw: draw,
        reset,
        setLabels,
        getLabels: () => ({ ...labels }),
        getTopology: () => topology,
        isInteracting: () => draggedNode !== null || isPanning,
    };
}
```

Every body marked "moved" is the exact original code from `legacy/app.js`, with only the listed renames applied. Fill each one in by copying, then applying the renames. Do not change logic. When done, search the new file for each old name (`simulationNodes`, `simulationLinks`, `viewTransform`, `showPortLabels`, `showIpLabels`, `currentTopology`, `highlightedDevices`, `isDraggingNode`, `innerHTML`, `openNodeDiagnosticDrawer`, `openEdgeDiagnosticDrawer`): **zero hits** is the acceptance check.

- [ ] **Step 5: Rewire `legacy/app.js` to use the map**

Add the import beside the others:

```js
import { createTopologyMap } from '../map/topology.js';
```

Delete these state declarations near the top of `initLegacyApp`:

```js
    let currentTopology = null;
    let simulationNodes = [];
    let simulationLinks = [];

    // Canvas Interaction State
    let isDraggingNode = false;
    let draggedNode = null;
    let isPanning = false;
    let panStartX = 0;
    let panStartY = 0;
    let viewTransform = { x: 0, y: 0, k: 1 };

    let showPortLabels = true;
    let showIpLabels = false;
```

and add, directly after `const toastContainer = ...`:

```js
    // Function declarations below are hoisted, so the drawers exist already.
    const map = createTopologyMap(svg, {
        onNodeSelect: dev => openNodeDiagnosticDrawer(dev),
        onLinkSelect: link => openEdgeDiagnosticDrawer(link),
    });
```

Replace the port and IP toggle handlers' bodies:

```js
    if (togglePortsBtn) {
        togglePortsBtn.addEventListener('click', () => {
            const next = !map.getLabels().ports;
            map.setLabels({ ports: next });
            togglePortsBtn.classList.toggle('active', next);
        });
    }

    if (toggleIpsBtn) {
        toggleIpsBtn.addEventListener('click', () => {
            const next = !map.getLabels().ips;
            map.setLabels({ ips: next });
            toggleIpsBtn.classList.toggle('active', next);
        });
    }

    if (zoomFitBtn) {
        zoomFitBtn.addEventListener('click', () => map.fit());
    }
```

In the Reset View handler, delete `currentTopology = null;`, `svg.innerHTML = '';` and `viewTransform = { x: 0, y: 0, k: 1 };`, and add `map.reset();` in their place (put it where `svg.innerHTML = '';` was).

In the sidebar resizer code, replace each of the three occurrences of

```js
if (currentTopology && typeof fitGraphToViewport === 'function') {
```

with `if (map.getTopology()) {`, and each `fitGraphToViewport()` inside them with `map.fit()`.

Replace the window resize handler with:

```js
    // Window Resize Handling
    window.addEventListener('resize', () => {
        if (map.getTopology() && !map.isInteracting()) {
            clearTimeout(window._resizeTimer);
            window._resizeTimer = setTimeout(() => map.fit(), 80);
        }
    });
```

In `hideLoading()`, replace:

```js
        const hasTopology = currentTopology && Object.keys(currentTopology.devices || {}).length > 0;
```

with:

```js
        const shown = map.getTopology();
        const hasTopology = shown && Object.keys(shown.devices || {}).length > 0;
```

Replace the whole `highlightedDevices` declaration, `renderTopology`, `fitGraphToViewport` and `drawSvgGraph` functions, and the "Interactive Mouse Zoom & Pan" listener block, with this one function:

```js
    // Draws a topology, or explains why there is nothing to draw. Empty-state
    // and conflict handling stay here; the map itself is map/topology.js.
    // highlightDevices rings devices in red; set only when an instructor opens
    // a student's mistakes from Batch Grading.
    function renderTopology(data, options = {}) {
        if (emptyState) {
            delete emptyState.dataset.panelState;
            emptyState.style.display = 'none';
        }
        if (conflictCard) {
            renderConflictSummary(data.conflicts || []);
        }
        if (Object.keys(data.devices || {}).length === 0) {
            map.reset();
            showPanelMessage(`<div class="empty-icon">⚠️</div><h3>No Devices Found</h3>`
                + `<p>The file was read, but no device configurations could be extracted from it.</p>`
                + `<p class="empty-hint">If this is a Packet Tracer file, it may have been saved by a newer version than this tool supports. `
                + `Try <strong>File &gt; Save As</strong> in Packet Tracer, or upload a .zip of each device's <code>show running-config</code> output instead.</p>`);
            return;
        }
        map.render(data, { highlightDevices: options.highlightDevices });
    }
```

If `shortInterfaceName` is still referenced anywhere in `legacy/app.js` after the moves, import it: `import { shortInterfaceName } from '../map/svg-shapes.js';`.

- [ ] **Step 6: Run all tests**

Run: `node --test tests/js/`
Expected: all JS unit tests pass.
Run: `python -m pytest -q`
Expected: all pass. The import-graph test confirms `createTopologyMap` and the shape functions are exported, and the innerHTML test confirms `map/` assigns none.
Run: `grep -nE "simulationNodes|simulationLinks|viewTransform|showPortLabels|showIpLabels|currentTopology|highlightedDevices|isDraggingNode|drawSvgGraph|fitGraphToViewport" static/js/legacy/app.js`
Expected: no output.

- [ ] **Step 7: Commit**

```bash
git add static/js/map tests/js/svg-shapes.test.mjs static/js/legacy/app.js
git commit -m "refactor(frontend): extract the topology map into map/" -m "createTopologyMap owns layout, drawing, zoom, pan and drag state behind a small API, with node and link selection as callbacks. The linked report view in PR 3 needs exactly this boundary to highlight devices from a list. Behaviour is unchanged." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Split the template into a base layout and partials

**Files:**
- Create: `templates/base.html`, `templates/partials/navbar.html`, `templates/partials/panel_discovery.html`, `templates/partials/panel_instructor.html`, `templates/partials/panel_grading.html`, `templates/partials/visualizer.html`
- Delete: `templates/index.html`
- Modify: `src/app.py` (`index_page` template name)
- Test: `tests/test_frontend_modules.py` (id coverage), golden comparison in Step 1

**Interfaces:**
- Produces: `base.html` renders identically to today's `index.html` for both roles.

- [ ] **Step 1: Capture today's rendered HTML as a golden**

Before changing anything, add to `tests/test_frontend_modules.py` a helper that renders both roles, and save the outputs for the comparison:

```python
from fastapi.testclient import TestClient


def render_page(instructor: bool) -> str:
    from src.app import app
    client = TestClient(app, client=("127.0.0.1", 50000) if instructor else ("10.20.30.40", 50000))
    return client.get("/").text
```

Run once and save to the session scratchpad (not the repo):

```bash
python -c "from tests.test_frontend_modules import render_page as r; open('<scratchpad>/golden_instructor.html','w',encoding='utf-8').write(r(True)); open('<scratchpad>/golden_student.html','w',encoding='utf-8').write(r(False))"
```

(`<scratchpad>` is the session scratchpad directory. The golden is a one-off check for this task, not a committed fixture.)

- [ ] **Step 2: Write the id-coverage test**

Append to `tests/test_frontend_modules.py`:

```python
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
```

- [ ] **Step 3: Run to verify the new tests fail**

Run: `python -m pytest tests/test_frontend_modules.py -q`
Expected: the student test errors because `templates/partials/panel_instructor.html` does not exist yet.

- [ ] **Step 4: Split the template**

Cut `templates/index.html` into files at these boundaries. Each partial is the exact original markup, indentation included.

| New file | Content of `index.html` |
|---|---|
| `partials/navbar.html` | From `<!-- Top Navigation Bar -->` through `</header>`. Keeps its `{% if is_instructor %}` around the Instructor tab. |
| `partials/panel_discovery.html` | From `<!-- MODE 1: LIVE TOPOLOGY DISCOVERY -->` through the closing `</div>` of `#panel-mode-visualizer` |
| `partials/panel_instructor.html` | From `<!-- MODE 2: INSTRUCTOR STUDIO ...` through the closing `</div>` of `#panel-mode-teacher`. **Without** the surrounding `{% if is_instructor %}` / `{% endif %}`, which stay in `base.html` |
| `partials/panel_grading.html` | From `<!-- MODE 3: STUDENT SUBMISSION & AUTOMATED GRADING -->` through the closing `</div>` of `#panel-mode-student` |
| `partials/visualizer.html` | From `<!-- Center/Right: Interactive Topology Visualizer & Diagnostic Drawer -->` through its `</section>` |

`templates/base.html` is the rest of `index.html`, with includes where the cut blocks were:

```html
        {% include "partials/navbar.html" %}

        <!-- Main Workspace -->
        <main class="workspace-grid" id="workspace-grid">
            <!-- Left Side: Dynamic Control Panels according to Mode -->
            <section class="control-panel" id="control-panel">

                {% include "partials/panel_discovery.html" %}

                {% if is_instructor %}
                {% include "partials/panel_instructor.html" %}
                {% endif %}

                {% include "partials/panel_grading.html" %}

            </section>

            <!-- Draggable Sidebar Resizer Handle -->
            ... (unchanged) ...

            {% include "partials/visualizer.html" %}
        </main>
```

(`... (unchanged) ...` here means the resizer `<div>` exactly as in `index.html`. It is three lines and stays in `base.html`.)

In `src/app.py`, change `name="index.html"` to `name="base.html"` in `index_page`.

```bash
git rm templates/index.html
```

- [ ] **Step 5: Compare with the golden**

```bash
python -c "
import re
from tests.test_frontend_modules import render_page as r
norm = lambda s: re.sub(r'\s+', ' ', s).strip()
for role, flag in (('instructor', True), ('student', False)):
    old = open(f'<scratchpad>/golden_{role}.html', encoding='utf-8').read()
    print(role, 'IDENTICAL' if norm(old) == norm(r(flag)) else 'DIFFERENT')
"
```

Expected: `instructor IDENTICAL` and `student IDENTICAL`. Whitespace-normalised equality means the markup is unchanged. If `DIFFERENT`, diff the two and fix the partial boundaries.

- [ ] **Step 6: Run all tests**

Run: `python -m pytest -q`
Expected: all pass, including `tests/test_instructor_access.py` (instructor markup present only for the server's own machine) and both id-coverage tests.

- [ ] **Step 7: Commit**

```bash
git add templates src/app.py tests/test_frontend_modules.py
git commit -m "refactor(templates): split index.html into a base layout and partials" -m "One partial per screen, so each PR in the refresh edits one file. Rendered HTML is identical for both roles (checked against a golden before the split). New tests assert that every element the JS looks up exists, and that a lab PC still receives no instructor markup." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Split the stylesheet into tokens and legacy

**Files:**
- Create: `static/css/tokens.css`, `static/css/legacy.css` (moved)
- Delete: `static/css/style.css`
- Modify: `templates/base.html`
- Test: `tests/test_assets.py`

**Interfaces:**
- Produces: `tokens.css` holds every `:root` custom property. PR 2 adds the Light and High-contrast token sets there.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_assets.py`:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_assets.py -q`
Expected: the two new tests FAIL.

- [ ] **Step 3: Split the file**

```bash
git mv static/css/style.css static/css/legacy.css
```

Cut the first `:root { ... }` block (lines 1 to 32 of the original `style.css`, from `:root {` through its closing `}`) out of `legacy.css` and paste it into a new `static/css/tokens.css` with this header:

```css
/* static/css/tokens.css
   Design tokens: every colour, font, radius and size the UI uses.
   Components read these; they never hard-code values (spec 2026-10-01, 6.2). */
```

If `legacy.css` began with a comment above `:root`, leave that comment in `legacy.css`.

In `templates/base.html`, replace:

```html
    <link rel="stylesheet" href="/static/css/style.css?v={{ asset_version }}">
```

with:

```html
    <link rel="stylesheet" href="/static/css/tokens.css?v={{ asset_version }}">
    <link rel="stylesheet" href="/static/css/legacy.css?v={{ asset_version }}">
```

- [ ] **Step 4: Run all tests**

Run: `python -m pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add static/css templates/base.html tests/test_assets.py
git commit -m "refactor(css): move design tokens into tokens.css" -m "The :root custom properties get their own file, loaded first, ready for the Light and High-contrast sets in PR 2. The remaining rules move unchanged to legacy.css." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Browser walkthrough, documentation and pull request

**Files:**
- Modify: `docs/SYSTEM.md` (module map and section 9 Screens)

- [ ] **Step 1: Walk every flow in the browser**

Start the `neteval` preview. Open `http://localhost:8765/` with the console visible. For each check, the expected result is "same as before this PR" and **no console errors**:

1. **Load:** the page renders; no errors; the Network tab shows `main.js`, `legacy/app.js`, `core/*.js` and `map/*.js` served from `/assets/<version>/js/`.
2. **Discovery:** upload `tests/fixtures/sample_topology.xml`, Analyze. 12 devices and 11 links drawn. The conflict card is hidden (the fixture has no conflicts).
3. **Map:** mouse-wheel zoom, drag the background to pan, drag a router; toggle Ports off and on, IPs on and off; Fit; Reset View clears the map and shows the empty state.
4. **Drawers:** click a router, then click a link; both drawers open with content.
5. **Instructor Studio:** upload the same fixture as the reference and generate a rubric. Download `instructions.txt` to the scratchpad.
6. **Student Grading:** upload that `instructions.txt` plus the fixture; Grade. 100%, A+.
7. **Batch:** upload `instructions.txt` plus the fixture twice under different names. Open Review on one row, then **Show on map**: the map redraws that topology.
8. **XSS regression (#31):** repeat the malicious-device-name check from #31 against Discovery and batch Review. The payload renders as text and `window.__xss` stays `0`.
9. **Lab PC view (review focus 1):** in the console, run:
   ```js
   document.querySelectorAll('#panel-mode-teacher, #nav-mode-teacher').forEach(e => e.remove());
   const v = document.querySelector('script[type=module]').src.split('/assets/')[1].split('/')[0];
   (await import(`/assets/${v}/js/legacy/app.js`)).initLegacyApp();
   ```
   No error is thrown. (This starts a second copy of the app on the same page, which is fine for an error check only. Reload afterwards.)
10. **Old browser notice (review focus 4):** in the console, `document.getElementById('unsupported-browser').hidden` is `true` in a modern browser.

Take a screenshot after step 6 and after step 7 for the PR.

- [ ] **Step 2: Update `docs/SYSTEM.md`**

In section 2's module map table, add after the `src/app.py` row:

```markdown
| `static/js/main.js` | Browser entry point, loaded as an ES module from `/assets/<version>/js/`. Relative imports inherit the version. |
| `static/js/core/` | Shared helpers. `dom.js` is the only module allowed to build markup from strings. |
| `static/js/map/` | The topology map (`createTopologyMap`) and its SVG shapes. |
| `static/js/legacy/app.js` | The pre-refresh screens, shrinking as each is rewritten (spec 2026-10-01). |
| `templates/base.html` | Page shell; one partial per screen under `templates/partials/`. |
| `static/css/tokens.css` | Design tokens. Component styles read these. |
```

In section 9, Interfaces, API table, add:

```markdown
| GET | `/assets/{version}/js/{path}` | A JavaScript module, cached long-term under its version. |
```

In section 11, Development, add a line under the test commands:

```markdown
node --test tests/js/        # JavaScript unit tests (developer machines; pytest also runs them)
```

- [ ] **Step 3: Full verification**

Run: `python -m pytest -q`
Expected: all pass (count is the previous 252 plus this PR's new tests).
Run: `python -m validation`
Expected: exit 0, all metrics 100%.

- [ ] **Step 4: Commit and open the pull request**

```bash
git add docs/SYSTEM.md
git commit -m "docs: describe the module and template structure" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin feature/ui-refresh
```

Open the PR against `hardening/lab-deployment-and-scoring-audit` while PR #39 is open (so the diff shows only this work), or against `master` once #39 has merged. Title: `UI refresh 1/5: foundation (modules, partials, tokens)`. Body: what moved where, the no-visible-change claim with the two screenshots, test and validation results, and a link to the spec. End the body with:

```
🤖 Generated with [Claude Code](https://claude.com/claude-code)
```
