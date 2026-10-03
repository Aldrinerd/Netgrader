# UI Refresh PR 2: Shell and Display Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Netgrader its new look: a left rail instead of the top tab bar, the Console palette, a Display menu (text size, Dark/Light/Follow system, high contrast, reduced motion), real icons instead of emoji, and text that scales with the user's setting.

**Architecture:** All colours become semantic tokens in `static/css/tokens.css`, defined once per theme (Dark, Light, and a high-contrast variant of each) and selected by attributes on `<html>`. Old token names (`--bg-base`, `--accent-blue`, ...) are kept as aliases, so the existing `legacy.css` themes automatically once its hard-coded colours become tokens. `static/js/display-boot.js`, a classic script in `<head>`, applies saved settings before first paint and exposes `window.NetgraderDisplay`, which the Display menu module uses. That gives one implementation, with no flash of the wrong theme. Icons come from a vendored Tabler sprite (`static/icons/sprite.svg`) built by a committed script.

**Tech Stack:** Python 3.12, FastAPI, Jinja2, pytest; browser-native ES modules; ES5 for the two classic scripts; Node 24 (developer machines) for `node --test`; npm once, to fetch Tabler Icons when building the sprite.

**Spec:** `docs/superpowers/specs/2026-10-01-ui-refresh-design.md` (sections 4.1, 4.2, 6, 9.1, 10, PR 2)

**Branch:** `feature/ui-refresh-2`, created from `feature/ui-refresh` (PR #40 is still open). Open the PR against `feature/ui-refresh`, or against `master` once #40 has merged.

**Refinements to the spec, decided while planning:**
- **Tints are precomputed tokens per theme** (`--tint-ok-weak`, ...), not `color-mix()`. `color-mix()` needs Chrome 111, and PR 1 kept the floor at Chrome 80.
- **Inline styles in `legacy/app.js` and the templates** get their colours and font sizes switched to tokens and `rem` here. Turning them into classes waits until PRs 3 and 4 rewrite those screens.
- **The context bar** in this PR holds only the screen title. File chips and the primary action arrive with the linked report in PR 3.
- **The old-browser notice** is driven by `boot-check.js`, which replaces `unsupported.js`. It shows the notice when the app never started, which also covers browsers that run modules but can't parse the app's code (a parked finding from PR 1).
- **The upload boxes** get a one-line "Accepts ..." hint. Users were dropping a `.pkt` on the rubric box, whose picker only lists `.txt` and `.json`.

## Global Constraints

- No build step, no bundler, no new runtime dependency. Lab PCs install nothing new. npm is used once on a developer machine to fetch Tabler Icons; the sprite and its licence are committed.
- Must work fully offline: no CDN, no external URL in any template, script or stylesheet.
- Browser floor stays at Chrome 80 / Firefox 74 / Safari 13.1 for the app. The two classic scripts (`display-boot.js`, `boot-check.js`) must be ES5, so they run in any browser.
- Every value from an uploaded file or filename reaches the page only through `escapeHtml()` or `textContent` (issue #31). Modules outside `static/js/legacy/` and `static/js/core/dom.js` must not assign `innerHTML`, `outerHTML`, `insertAdjacentHTML` or `document.write`.
- Jinja's `{% if is_instructor %}` gating of the Instructor tab and panel is preserved. A lab PC receives no instructor markup.
- Text contrast is at least 4.5:1 in standard contrast and 7:1 in high contrast, in both themes. Focus rings and map strokes are at least 3:1 against the page background.
- No text renders below 12 px equivalent (`0.75rem`) at the Default text size. Body text is 15 px (`0.9375rem`).
- No emoji anywhere in `templates/` or `static/js/`.
- `python -m pytest -q` and `python -m validation` pass after every task.
- Commit messages: conventional prefix, a body explaining why, ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Storage unavailable or corrupt:** private windows, blocked site data, or a stored value that isn't JSON. The page must load with default settings and no error. Tested in Task 3.
2. **"Follow system" while the page is open:** switching the computer to light mode must update the page without a reload. Tested in Task 3.
3. **Extra large text on a 1366×768 laptop:** rail labels and the context bar must not overlap or push the page sideways. Rail labels truncate with an ellipsis (Task 7 CSS); checked in the Task 9 walkthrough.
4. **A lab PC (no Instructor item):** the rail shows two items with no gap, and the Display menu works. Tested in Task 7.
5. **The map in Light and high-contrast themes:** links, devices and labels must stay visible on light backgrounds. Map colours are tokens with a 3:1 contrast test (Task 2), wired in Task 5.

---

## File Structure

| Path | Status | Responsibility |
|---|---|---|
| `src/app.py` | Modify | Asset route: also reject segments ending in `.` or space |
| `static/css/tokens.css` | Rewrite | Semantic tokens for 4 theme sets, legacy aliases, type scale, text-size and motion rules |
| `static/css/legacy.css` | Modify | Hard-coded colours become tokens, font sizes become `rem`; navbar rules removed; spinner added |
| `static/css/layouts/shell.css` | Create | Rail, context bar, Display menu, icon base styles |
| `static/js/display-boot.js` | Create | Classic ES5 in `<head>`: load, normalise, resolve and apply display settings; `window.NetgraderDisplay` |
| `static/js/boot-check.js` | Create | Classic ES5: shows the unsupported-browser notice if the app never started |
| `static/js/unsupported.js` | Delete | Replaced by `boot-check.js` |
| `static/js/main.js` | Modify | Sets the booted flag; starts the Display menu |
| `static/js/core/icons.js` | Create | `icon(name)` (element) and `iconMarkup(name)` (string) for the sprite |
| `static/js/shell/display-menu.js` | Create | Display menu popover behaviour |
| `static/js/map/svg-shapes.js` | Modify | `paint(el, props)`; colours via tokens |
| `static/js/map/topology.js` | Modify | Colours via tokens through `paint` |
| `static/js/legacy/app.js` | Modify | Emoji → icons or text; inline colours → tokens; engine-status removed; context title and `aria-current` |
| `static/icons/sprite.svg` | Create | Tabler icon symbols, generated |
| `static/icons/LICENSE-tabler.txt` | Create | Tabler MIT licence, with version |
| `scripts/build_icon_sprite.py` | Create | Builds the sprite from Tabler outline SVGs |
| `templates/base.html` | Modify | Rail and context bar layout; head scripts; icon meta |
| `templates/partials/rail.html` | Create | Left rail navigation |
| `templates/partials/context_bar.html` | Create | Screen title bar |
| `templates/partials/display_menu.html` | Create | Display settings form |
| `templates/partials/navbar.html` | Delete | Replaced by the rail |
| `templates/partials/*.html` (panels, visualizer) | Modify | Emoji → icons; inline colours → tokens; upload hints; Reset View into map toolbar |
| `tests/test_assets.py` | Modify | Route and boot-check tests |
| `tests/test_frontend_modules.py` | Modify | Stronger import/export and HTML-sink checks |
| `tests/test_theme_tokens.py` | Create | Token completeness and WCAG contrast |
| `tests/test_styles.py` | Create | No hard-coded colours, no px font sizes |
| `tests/test_icons.py` | Create | Sprite coverage and licence |
| `tests/test_shell.py` | Create | Rail, context bar, Display menu markup for both roles |
| `tests/test_no_emoji.py` | Create | No emoji in templates or JS |
| `tests/js/display-boot.test.mjs` | Create | Settings logic under Node's `vm` |
| `tests/js/icons.test.mjs` | Create | `iconMarkup` format and input check |
| `tests/js/svg-shapes.test.mjs` | Modify | `paint` |
| `docs/SYSTEM.md` | Modify | Screens and display settings |

---

### Task 1: PR 1 carry-overs

**Files:**
- Modify: `src/app.py` (`versioned_module`), `tests/test_assets.py`, `tests/test_frontend_modules.py`, `templates/base.html`, `static/js/main.js`
- Create: `static/js/boot-check.js`
- Delete: `static/js/unsupported.js`

**Interfaces:**
- Produces: `window.__netgraderBooted = true`, set by `main.js` once its imports have loaded. `boot-check.js` reads it.

- [ ] **Step 1: Write the failing route tests**

In `tests/test_assets.py`, the hostile-path test sends some paths that the HTTP client normalises before sending (`../x.js` becomes `/assets/1/x.js` and never reaches the handler). Replace those cases with percent-encoded dots, and add trailing-dot and trailing-space segments, which Windows strips. In the parametrize list of the test that patches `realpath`/`isfile` to raise, replace `"../x.js"` with `"%2E%2E/x.js"` and `"a/../../x.js"` with `"a/%2E%2E/%2E%2E/x.js"`, and add:

```python
    "%2E%2E%20/x.js",      # ".. " -- Windows strips the trailing space
    "a./x.js",             # "a."  -- Windows strips the trailing dot
    "core/dom.js.",        # ends in "." after ".js": not a .js path
```

Rewrite `test_js_outside_the_js_folder_is_not_served` so its request reaches the handler:

```python
def test_js_outside_the_js_folder_is_not_served(outside_probe):
    # %2E%2E survives the client; a literal ../ would be normalised away and
    # the test would pass on routing alone, proving nothing.
    assert client.get("/assets/1/js/%2E%2E/zz_outside_probe.js").status_code == 404
```

(Keep the existing `outside_probe` fixture. If the fixture has a different name in the file, use that name.)

Fix the line in that file where a lost line break left `as rp,             mock.patch(` on one line: put the second `mock.patch(...)` on its own line.

- [ ] **Step 2: Run to verify the new cases fail**

Run: `python -m pytest tests/test_assets.py -q`
Expected: the `.. `, `a.` cases FAIL with "touched disk" (they currently reach `realpath`).

- [ ] **Step 3: Reject segments Windows would rewrite**

In `src/app.py`, `versioned_module`, extend the segment check so a segment is rejected if it is empty, `.`, `..`, **or ends in `.` or a space**:

```python
    segments = path.split("/")
    if any(not s or s in (".", "..") or s.endswith((".", " ")) for s in segments):
        raise HTTPException(status_code=404)
```

Keep the existing order: string checks first, then `realpath`, then `commonpath`, then `isfile`.

- [ ] **Step 4: Replace the old-browser script with a boot check**

Create `static/js/boot-check.js`:

```js
// static/js/boot-check.js
// Classic ES5 script. Shows the unsupported-browser notice when the app never
// started: either the browser cannot run ES modules at all, or it runs them
// but cannot parse the app's code. main.js sets the flag once its imports
// have loaded, so a parse failure anywhere in the module graph leaves it unset.
window.addEventListener('load', function () {
    if (window.__netgraderBooted) { return; }
    var notice = document.getElementById('unsupported-browser');
    if (notice) { notice.hidden = false; }
});
```

In `static/js/main.js`, make the first statement after the imports:

```js
// Read by boot-check.js. Runs only if every import above parsed and loaded.
window.__netgraderBooted = true;
```

In `templates/base.html`, replace:

```html
    <script nomodule src="/static/js/unsupported.js?v={{ asset_version }}"></script>
```

with:

```html
    <script src="/static/js/boot-check.js?v={{ asset_version }}"></script>
```

```bash
git rm static/js/unsupported.js
```

In `tests/test_frontend_modules.py`, change `CLASSIC_SCRIPTS = {"unsupported.js"}` to `CLASSIC_SCRIPTS = {"boot-check.js", "display-boot.js"}` (Task 3 adds the second).

In `tests/test_assets.py`, update the old-browser test to expect the new script:

```python
def test_old_browsers_get_a_notice_instead_of_a_dead_page():
    html = client.get("/").text
    assert '<script src="/static/js/boot-check.js' in html
    assert re.search(r'<div id="unsupported-browser"[^>]*\bhidden\b', html)
    assert "unsupported.js" not in html


def test_entry_module_sets_the_booted_flag():
    with open(os.path.join(app_module.STATIC_DIR, "js", "main.js"), encoding="utf-8") as f:
        assert "window.__netgraderBooted = true" in f.read()
```

(Add `import re` at the top of the file if it is not already imported.)

- [ ] **Step 5: Tighten the module checks**

In `tests/test_frontend_modules.py`:

Replace `IMPORT_RE` and `EXPORT_RE`, and add a side-effect import pattern:

```python
# import { a, b as c } from './x.js'   |   import x from './x.js'   |   import * as x from './x.js'
IMPORT_RE = re.compile(r"import\s*(?:\{([^}]*)\}|[\w$]+|\*\s+as\s+[\w$]+)\s*from\s*['\"](\.{1,2}/[^'\"]+)['\"]")
SIDE_EFFECT_IMPORT_RE = re.compile(r"import\s*['\"](\.{1,2}/[^'\"]+)['\"]")
# export function a / export const a / export class a / export { a, b as c }
EXPORT_RE = re.compile(r"export\s+(?:async\s+)?(?:function\*?|const|let|class)\s+([A-Za-z_$][\w$]*)")
EXPORT_LIST_RE = re.compile(r"export\s*\{([^}]*)\}")
```

In `test_relative_imports_resolve_to_real_exports`:
- Compute `exported` as the union of `EXPORT_RE.findall(...)` and, for each `EXPORT_LIST_RE` match, the exported name of each item (the text after `as` if present, else the item).
- `IMPORT_RE.findall` now returns `(names, target)` where `names` is empty for default and namespace imports. Only check names when `names` is non-empty.
- Also check every `SIDE_EFFECT_IMPORT_RE` target exists.

Replace the innerHTML boundary regex so it covers every HTML sink:

```python
HTML_SINK_RE = re.compile(r"\.(?:innerHTML|outerHTML)\s*[+]?=(?!=)|\.insertAdjacentHTML\s*\(|document\.write(?:ln)?\s*\(")
```

and use `HTML_SINK_RE.search(...)` in `test_innerhtml_only_in_legacy_and_dom_helper`.

In the id-coverage tests, replace each `f'id="{i}"' in html` with a helper that does not match `data-id=` or similar:

```python
def _has_id(html: str, element_id: str) -> bool:
    return re.search(r'(?<![\w-])id="%s"' % re.escape(element_id), html) is not None
```

Reword the student id-coverage docstring to: `"""A lab PC gets no instructor markup; every other id the JS looks up must exist."""`

- [ ] **Step 6: Run all tests**

Run: `python -m pytest -q`
Expected: all pass.
Run: `python -m validation`
Expected: exit 0.

- [ ] **Step 7: Commit**

```bash
git add -A src/app.py static/js tests templates/base.html
git commit -m "fix: close PR 1 review carry-overs" -m "The asset route also rejects path segments ending in a dot or space, which Windows silently strips. Traversal tests now send percent-encoded dots so they reach the handler instead of passing on routing. boot-check.js replaces unsupported.js and also covers browsers that run modules but cannot parse the app. Module checks recognise default, namespace, side-effect and list exports, and every HTML sink, not only innerHTML." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Theme tokens

**Files:**
- Rewrite: `static/css/tokens.css`
- Test: `tests/test_theme_tokens.py`

**Interfaces:**
- Produces: the token names below, used by every later task. Themes are selected by `data-theme="dark|light"` and `data-contrast="standard|high"` on `<html>`. Text size is selected by `data-text-size="sm|md|lg|xl"`, and motion by `data-motion="full|reduce"`.

| Group | Tokens |
|---|---|
| Surfaces | `--surface-base`, `--surface`, `--surface-raised`, `--surface-sunken` |
| Lines | `--line`, `--line-strong` |
| Text | `--text`, `--text-muted`, `--on-accent` |
| Accent and status | `--accent`, `--accent-strong`, `--status-ok`, `--status-bad`, `--status-warn`, `--focus-ring` |
| Tints (`-weak` ≈ 8%, `-mid` ≈ 16%, `-strong` ≈ 32%) | `--tint-accent-*`, `--tint-ok-*`, `--tint-bad-*`, `--tint-warn-*`, `--tint-host-*`, `--tint-neutral-*` |
| Map | `--map-router`, `--map-switch`, `--map-host`, `--map-unknown`, `--map-device-fill`, `--map-link-ok`, `--map-link-inferred`, `--map-link-unverified`, `--map-link-bad`, `--map-badge-bg`, `--map-port`, `--map-ip`, `--map-label` |
| Elevation | `--shadow-card`, `--shadow-pop`, `--scrim` |
| Non-colour | `--font-main`, `--font-mono`, `--radius-sm`, `--radius-md`, `--radius-lg`, `--sidebar-width`, `--rail-width`, `--context-height`, `--text-xs`, `--text-sm`, `--text-base`, `--text-lg`, `--text-xl`, `--text-2xl` |

- [ ] **Step 1: Write the failing tests**

Create `tests/test_theme_tokens.py`:

```python
# tests/test_theme_tokens.py
"""
Every theme defines every colour token, and the pairs people read pass WCAG:
4.5:1 for text in standard contrast, 7:1 in high contrast, 3:1 for focus
rings and map strokes against the page background.
"""
import os
import re

import pytest

TOKENS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "css", "tokens.css")

BLOCKS = {
    "dark": ':root, :root[data-theme="dark"]',
    "light": ':root[data-theme="light"]',
    "dark-high": ':root[data-theme="dark"][data-contrast="high"]',
    "light-high": ':root[data-theme="light"][data-contrast="high"]',
}
COLOUR_TOKENS = [
    "surface-base", "surface", "surface-raised", "surface-sunken", "line", "line-strong",
    "text", "text-muted", "on-accent", "accent", "accent-strong", "status-ok", "status-bad",
    "status-warn", "focus-ring", "map-router", "map-switch", "map-host", "map-unknown",
    "map-device-fill", "map-link-ok", "map-link-inferred", "map-link-unverified", "map-link-bad",
    "map-badge-bg", "map-port", "map-ip", "map-label",
]
TINTS = [f"tint-{k}-{s}" for k in ("accent", "ok", "bad", "warn", "host", "neutral") for s in ("weak", "mid", "strong")]


def _block(css: str, selector: str) -> dict:
    start = css.index(selector + " {")
    body = css[start + len(selector) + 2: css.index("}", start)]
    return dict(re.findall(r"--([\w-]+)\s*:\s*([^;]+);", body))


@pytest.fixture(scope="module")
def themes():
    css = open(TOKENS, encoding="utf-8").read()
    dark, light = _block(css, BLOCKS["dark"]), _block(css, BLOCKS["light"])
    return {
        "dark": dark,
        "light": light,
        "dark-high": {**dark, **_block(css, BLOCKS["dark-high"])},
        "light-high": {**light, **_block(css, BLOCKS["light-high"])},
    }


def _lum(hex_colour: str) -> float:
    h = hex_colour.strip().lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _ratio(a: str, b: str) -> float:
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


@pytest.mark.parametrize("theme", list(BLOCKS))
def test_every_colour_token_is_defined(themes, theme):
    missing = [t for t in COLOUR_TOKENS + TINTS if t not in themes[theme]]
    assert not missing, f"{theme} lacks {missing}"


@pytest.mark.parametrize("theme", list(BLOCKS))
def test_text_contrast(themes, theme):
    t = themes[theme]
    need = 7.0 if theme.endswith("high") else 4.5
    fails = []
    for fg in ("text", "text-muted", "status-ok", "status-bad", "status-warn"):
        for bg in ("surface-base", "surface", "surface-raised"):
            r = _ratio(t[fg], t[bg])
            if r < need:
                fails.append(f"{fg} on {bg} = {r:.2f}")
    r = _ratio(t["on-accent"], t["accent"])
    if r < need:
        fails.append(f"on-accent on accent = {r:.2f}")
    assert not fails, f"{theme} below {need}:1: {fails}"


@pytest.mark.parametrize("theme", list(BLOCKS))
def test_focus_and_map_strokes_are_visible(themes, theme):
    t = themes[theme]
    graphic = ("focus-ring", "map-router", "map-switch", "map-host", "map-link-ok",
               "map-link-inferred", "map-link-bad", "map-label")
    fails = [f"{g} = {_ratio(t[g], t['surface-base']):.2f}" for g in graphic
             if _ratio(t[g], t["surface-base"]) < 3.0]
    assert not fails, f"{theme} graphics below 3:1 on the page background: {fails}"


def test_legacy_aliases_point_at_semantic_tokens():
    css = open(TOKENS, encoding="utf-8").read()
    for alias, target in (("bg-base", "surface-base"), ("text-primary", "text"),
                          ("accent-blue", "accent"), ("accent-red", "status-bad")):
        assert re.search(rf"--{alias}\s*:\s*var\(--{target}\)", css), alias


def test_text_sizes_scale_the_root():
    css = open(TOKENS, encoding="utf-8").read()
    for size, pct in (("sm", "87.5%"), ("md", "100%"), ("lg", "112.5%"), ("xl", "125%")):
        assert re.search(rf':root\[data-text-size="{size}"\]\s*\{{\s*font-size:\s*{re.escape(pct)}', css), size
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_theme_tokens.py -q`
Expected: FAIL, with `ValueError: substring not found` for the theme blocks.

- [ ] **Step 3: Write `static/css/tokens.css`**

```css
/* static/css/tokens.css
   Design tokens: every colour, font, radius and size the UI uses.
   Components read these; they never hard-code values (spec 2026-10-01, 6.2).
   Themes are chosen by attributes on <html>, set by display-boot.js:
     data-theme="dark|light"  data-contrast="standard|high"
     data-text-size="sm|md|lg|xl"  data-motion="full|reduce"
   Every text/background pair is tested for WCAG contrast in
   tests/test_theme_tokens.py. */

:root, :root[data-theme="dark"] {
    --surface-base: #0B0E12;
    --surface: #12171D;
    --surface-raised: #171D25;
    --surface-sunken: #0F1318;
    --line: #1F2630;
    --line-strong: #2C3541;
    --text: #E8ECF1;
    --text-muted: #8D97A6;
    --on-accent: #07120D;
    --accent: #3FB68B;
    --accent-strong: #52C99D;
    --status-ok: #3FB68B;
    --status-bad: #F2725C;
    --status-warn: #E3B341;
    --focus-ring: #58A6FF;

    --tint-accent-weak: rgba(63, 182, 139, 0.08);
    --tint-accent-mid: rgba(63, 182, 139, 0.16);
    --tint-accent-strong: rgba(63, 182, 139, 0.32);
    --tint-ok-weak: rgba(63, 182, 139, 0.08);
    --tint-ok-mid: rgba(63, 182, 139, 0.16);
    --tint-ok-strong: rgba(63, 182, 139, 0.32);
    --tint-bad-weak: rgba(242, 114, 92, 0.08);
    --tint-bad-mid: rgba(242, 114, 92, 0.16);
    --tint-bad-strong: rgba(242, 114, 92, 0.32);
    --tint-warn-weak: rgba(227, 179, 65, 0.08);
    --tint-warn-mid: rgba(227, 179, 65, 0.16);
    --tint-warn-strong: rgba(227, 179, 65, 0.32);
    --tint-host-weak: rgba(179, 146, 240, 0.08);
    --tint-host-mid: rgba(179, 146, 240, 0.16);
    --tint-host-strong: rgba(179, 146, 240, 0.32);
    --tint-neutral-weak: rgba(232, 236, 241, 0.04);
    --tint-neutral-mid: rgba(232, 236, 241, 0.08);
    --tint-neutral-strong: rgba(232, 236, 241, 0.14);

    --map-router: #58A6FF;
    --map-switch: #3FB68B;
    --map-host: #B392F0;
    --map-unknown: #8D97A6;
    --map-device-fill: #171D25;
    --map-link-ok: #3FB68B;
    --map-link-inferred: #E3B341;
    --map-link-unverified: #6B7686;
    --map-link-bad: #F2725C;
    --map-badge-bg: #0F1318;
    --map-port: #8CC4FF;
    --map-ip: #7EE2B8;
    --map-label: #C9D1DC;

    --shadow-card: 0 10px 24px rgba(0, 0, 0, 0.45);
    --shadow-pop: 0 12px 32px rgba(0, 0, 0, 0.55);
    --scrim: rgba(0, 0, 0, 0.55);

    color-scheme: dark;
}

:root[data-theme="light"] {
    --surface-base: #F3F5F8;
    --surface: #FFFFFF;
    --surface-raised: #FFFFFF;
    --surface-sunken: #EEF2F7;
    --line: #E1E6ED;
    --line-strong: #C9D1DC;
    --text: #16202E;
    --text-muted: #56626F;
    --on-accent: #FFFFFF;
    --accent: #1B7350;
    --accent-strong: #155C40;
    --status-ok: #1B7350;
    --status-bad: #B42318;
    --status-warn: #8A5A00;
    --focus-ring: #1D5FA8;

    --tint-accent-weak: rgba(27, 115, 80, 0.08);
    --tint-accent-mid: rgba(27, 115, 80, 0.14);
    --tint-accent-strong: rgba(27, 115, 80, 0.28);
    --tint-ok-weak: rgba(27, 115, 80, 0.08);
    --tint-ok-mid: rgba(27, 115, 80, 0.14);
    --tint-ok-strong: rgba(27, 115, 80, 0.28);
    --tint-bad-weak: rgba(180, 35, 24, 0.07);
    --tint-bad-mid: rgba(180, 35, 24, 0.13);
    --tint-bad-strong: rgba(180, 35, 24, 0.26);
    --tint-warn-weak: rgba(138, 90, 0, 0.08);
    --tint-warn-mid: rgba(138, 90, 0, 0.14);
    --tint-warn-strong: rgba(138, 90, 0, 0.28);
    --tint-host-weak: rgba(110, 69, 201, 0.07);
    --tint-host-mid: rgba(110, 69, 201, 0.13);
    --tint-host-strong: rgba(110, 69, 201, 0.26);
    --tint-neutral-weak: rgba(22, 32, 46, 0.04);
    --tint-neutral-mid: rgba(22, 32, 46, 0.07);
    --tint-neutral-strong: rgba(22, 32, 46, 0.12);

    --map-router: #1D5FA8;
    --map-switch: #1B7350;
    --map-host: #6E45C9;
    --map-unknown: #56626F;
    --map-device-fill: #FFFFFF;
    --map-link-ok: #1B7350;
    --map-link-inferred: #8A5A00;
    --map-link-unverified: #8C97A6;
    --map-link-bad: #B42318;
    --map-badge-bg: #FFFFFF;
    --map-port: #1D5FA8;
    --map-ip: #1B7350;
    --map-label: #16202E;

    --shadow-card: 0 8px 20px rgba(19, 41, 75, 0.10);
    --shadow-pop: 0 12px 28px rgba(19, 41, 75, 0.16);
    --scrim: rgba(19, 41, 75, 0.35);

    color-scheme: light;
}

:root[data-theme="dark"][data-contrast="high"] {
    --surface-base: #05070A;
    --surface: #0B0E12;
    --surface-raised: #10151B;
    --surface-sunken: #05070A;
    --line: #6B7686;
    --line-strong: #9AA5B4;
    --text: #F5F7FA;
    --text-muted: #C9D1DC;
    --on-accent: #03120C;
    --accent: #5FE0B0;
    --accent-strong: #7FEAC2;
    --status-ok: #5FE0B0;
    --status-bad: #FF9B8A;
    --status-warn: #FFD166;
    --focus-ring: #FFD166;
    --map-router: #8CC4FF;
    --map-switch: #5FE0B0;
    --map-host: #D2BBFF;
    --map-link-ok: #5FE0B0;
    --map-link-inferred: #FFD166;
    --map-link-bad: #FF9B8A;
    --map-label: #F5F7FA;
}

:root[data-theme="light"][data-contrast="high"] {
    --surface-base: #FFFFFF;
    --surface: #FFFFFF;
    --surface-raised: #F6F8FA;
    --line: #6B7686;
    --line-strong: #2E3846;
    --text: #0B0F14;
    --text-muted: #2E3846;
    --accent: #0E5A3C;
    --accent-strong: #0A4430;
    --status-ok: #0E5A3C;
    --status-bad: #8F1A10;
    --status-warn: #5C3B00;
    --focus-ring: #0B4A8C;
    --map-router: #0B4A8C;
    --map-switch: #0E5A3C;
    --map-host: #4B2A9E;
    --map-link-ok: #0E5A3C;
    --map-link-inferred: #5C3B00;
    --map-link-bad: #8F1A10;
    --map-label: #0B0F14;
}

:root {
    --font-main: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-mono: 'JetBrains Mono', monospace;
    --radius-sm: 6px;
    --radius-md: 8px;
    --radius-lg: 12px;
    --sidebar-width: 440px;
    --rail-width: 76px;
    --context-height: 3rem;

    --text-xs: 0.75rem;
    --text-sm: 0.8125rem;
    --text-base: 0.9375rem;
    --text-lg: 1.125rem;
    --text-xl: 1.5rem;
    --text-2xl: 2rem;

    /* Legacy names used by legacy.css. Each points at a semantic token so the
       old rules follow the theme; they disappear as screens are rewritten. */
    --bg-base: var(--surface-base);
    --bg-surface: var(--surface);
    --bg-surface-hover: var(--surface-raised);
    --bg-surface-subtle: var(--surface-sunken);
    --border-color: var(--line);
    --border-highlight: var(--line-strong);
    --text-primary: var(--text);
    --text-secondary: var(--text-muted);
    --accent-blue: var(--accent);
    --accent-blue-hover: var(--accent-strong);
    --accent-blue-glow: var(--tint-accent-mid);
    --accent-green: var(--status-ok);
    --accent-green-glow: var(--tint-ok-mid);
    --accent-amber: var(--status-warn);
    --accent-amber-glow: var(--tint-warn-mid);
    --accent-red: var(--status-bad);
    --accent-red-glow: var(--tint-bad-mid);
    --accent-purple: var(--map-host);
}

:root[data-text-size="sm"] { font-size: 87.5%; }
:root[data-text-size="md"] { font-size: 100%; }
:root[data-text-size="lg"] { font-size: 112.5%; }
:root[data-text-size="xl"] { font-size: 125%; }

:root[data-motion="reduce"] *,
:root[data-motion="reduce"] *::before,
:root[data-motion="reduce"] *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
}
```

Note: `--text-muted` was previously a different, darker grey than `--text-secondary`. Both now map to one muted token, which is intended: a single muted text colour.

- [ ] **Step 4: Run the tests**

Run: `python -m pytest tests/test_theme_tokens.py -q`
Expected: all pass.
Run: `python -m pytest -q`
Expected: all pass. `test_tokens_file_holds_the_custom_properties` (from PR 1) still finds `:root` and `--accent-blue` in `tokens.css`.

- [ ] **Step 5: Commit**

```bash
git add static/css/tokens.css tests/test_theme_tokens.py
git commit -m "feat(theme): semantic tokens for Dark, Light and high contrast" -m "One token set per theme, selected by attributes on <html>, with the old token names kept as aliases so legacy.css follows the theme. Tints are precomputed per theme instead of color-mix(), which would raise the browser floor to Chrome 111. Every text pair is tested at 4.5:1 (7:1 high contrast), and focus rings and map strokes at 3:1." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Display settings boot script

**Files:**
- Create: `static/js/display-boot.js`, `tests/js/display-boot.test.mjs`
- Modify: `templates/base.html` (`<head>`), `tests/test_assets.py`

**Interfaces:**
- Produces `window.NetgraderDisplay` with:
  - `KEY: string` (`'netgrader.display'`)
  - `DEFAULTS: { textSize: 'md', theme: 'dark', contrast: 'standard', motion: 'system' }`
  - `normalize(raw: any) -> Settings` (every field valid; unknown values fall back to defaults)
  - `resolve(settings, env: { prefersLight: boolean, prefersReducedMotion: boolean }) -> { theme: 'dark'|'light', contrast, textSize, motion: 'full'|'reduce' }`
  - `load() -> Settings`
  - `save(settings) -> void`
  - `apply(settings) -> resolved` (sets the four `data-*` attributes on `<html>`)

- [ ] **Step 1: Write the failing Node test**

Create `tests/js/display-boot.test.mjs`:

```js
// tests/js/display-boot.test.mjs
// display-boot.js is a classic script, so it is loaded into a fake browser
// with Node's vm module rather than imported.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const SRC = readFileSync(new URL('../../static/js/display-boot.js', import.meta.url), 'utf8');

function boot({ stored, storageThrows = false, prefersLight = false, reduced = false } = {}) {
    const attrs = {};
    const listeners = [];
    const media = {
        '(prefers-color-scheme: light)': { matches: prefersLight },
        '(prefers-reduced-motion: reduce)': { matches: reduced },
    };
    const store = new Map(stored === undefined ? [] : [['netgrader.display', stored]]);
    const localStorage = {
        getItem: k => { if (storageThrows) throw new Error('blocked'); return store.has(k) ? store.get(k) : null; },
        setItem: (k, v) => { if (storageThrows) throw new Error('blocked'); store.set(k, v); },
    };
    const window = {
        matchMedia: q => ({
            get matches() { return media[q].matches; },
            addEventListener: (_t, fn) => listeners.push({ q, fn }),
        }),
    };
    Object.defineProperty(window, 'localStorage', {
        get() { if (storageThrows) throw new Error('SecurityError'); return localStorage; },
    });
    const document = { documentElement: { setAttribute: (k, v) => { attrs[k] = v; } } };
    vm.runInNewContext(SRC, { window, document });
    return { api: window.NetgraderDisplay, attrs, store, media, listeners };
}

test('applies defaults when nothing is stored', () => {
    const { attrs } = boot();
    assert.deepEqual(attrs, { 'data-theme': 'dark', 'data-contrast': 'standard', 'data-text-size': 'md', 'data-motion': 'full' });
});

test('applies stored settings before the page draws', () => {
    const { attrs } = boot({ stored: JSON.stringify({ theme: 'light', contrast: 'high', textSize: 'xl', motion: 'reduce' }) });
    assert.deepEqual(attrs, { 'data-theme': 'light', 'data-contrast': 'high', 'data-text-size': 'xl', 'data-motion': 'reduce' });
});

test('corrupt or hostile stored values fall back to defaults', () => {
    for (const stored of ['not json', '[]', '"x"', JSON.stringify({ theme: 'neon', textSize: 99, contrast: null })]) {
        const { attrs } = boot({ stored });
        assert.equal(attrs['data-theme'], 'dark');
        assert.equal(attrs['data-text-size'], 'md');
        assert.equal(attrs['data-contrast'], 'standard');
    }
});

test('blocked storage still loads with defaults and saving does not throw', () => {
    const { api, attrs } = boot({ storageThrows: true });
    assert.equal(attrs['data-theme'], 'dark');
    assert.doesNotThrow(() => api.save({ theme: 'light' }));
});

test('follow system resolves from the media query', () => {
    const { attrs } = boot({ stored: JSON.stringify({ theme: 'system' }), prefersLight: true, reduced: true });
    assert.equal(attrs['data-theme'], 'light');
    assert.equal(attrs['data-motion'], 'reduce');
});

test('follow system updates live when the computer switches theme', () => {
    const { attrs, media, listeners } = boot({ stored: JSON.stringify({ theme: 'system' }) });
    assert.equal(attrs['data-theme'], 'dark');
    media['(prefers-color-scheme: light)'].matches = true;
    listeners.filter(l => l.q === '(prefers-color-scheme: light)').forEach(l => l.fn());
    assert.equal(attrs['data-theme'], 'light');
});

test('save then load round-trips through storage', () => {
    const { api, store } = boot();
    api.save({ theme: 'light', textSize: 'lg', contrast: 'standard', motion: 'system' });
    assert.equal(JSON.parse(store.get('netgrader.display')).textSize, 'lg');
    assert.equal(api.load().theme, 'light');
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `node --test tests/js/display-boot.test.mjs`
Expected: FAIL with `ENOENT` for `display-boot.js`.

- [ ] **Step 3: Write `static/js/display-boot.js`**

```js
// static/js/display-boot.js
// Classic ES5 script, loaded in <head> before any stylesheet paints. Applies
// the saved display settings as attributes on <html> so the first frame is
// already in the right theme and size, and exposes window.NetgraderDisplay for
// the Display menu (static/js/shell/display-menu.js). Settings are personal
// preferences, kept per browser in localStorage; any storage failure falls
// back to defaults.
(function (w, d) {
    var KEY = 'netgrader.display';
    var DEFAULTS = { textSize: 'md', theme: 'dark', contrast: 'standard', motion: 'system' };
    var ALLOWED = {
        textSize: ['sm', 'md', 'lg', 'xl'],
        theme: ['dark', 'light', 'system'],
        contrast: ['standard', 'high'],
        motion: ['system', 'reduce']
    };

    function normalize(raw) {
        var out = {};
        var source = (raw && typeof raw === 'object' && !(raw instanceof Array)) ? raw : {};
        for (var key in DEFAULTS) {
            if (!DEFAULTS.hasOwnProperty(key)) { continue; }
            var value = source[key];
            out[key] = ALLOWED[key].indexOf(value) !== -1 ? value : DEFAULTS[key];
        }
        return out;
    }

    function resolve(settings, env) {
        var s = normalize(settings);
        return {
            theme: s.theme === 'system' ? (env.prefersLight ? 'light' : 'dark') : s.theme,
            contrast: s.contrast,
            textSize: s.textSize,
            motion: (s.motion === 'reduce' || (s.motion === 'system' && env.prefersReducedMotion)) ? 'reduce' : 'full'
        };
    }

    function storage() {
        try { return w.localStorage || null; } catch (e) { return null; }
    }

    function load() {
        var store = storage();
        if (!store) { return normalize({}); }
        try { return normalize(JSON.parse(store.getItem(KEY) || '{}')); } catch (e) { return normalize({}); }
    }

    function save(settings) {
        var store = storage();
        if (!store) { return; }
        try { store.setItem(KEY, JSON.stringify(normalize(settings))); } catch (e) { /* storage full or blocked */ }
    }

    function query(q) {
        return !!(w.matchMedia && w.matchMedia(q).matches);
    }

    function apply(settings) {
        var r = resolve(settings, {
            prefersLight: query('(prefers-color-scheme: light)'),
            prefersReducedMotion: query('(prefers-reduced-motion: reduce)')
        });
        var el = d.documentElement;
        el.setAttribute('data-theme', r.theme);
        el.setAttribute('data-contrast', r.contrast);
        el.setAttribute('data-text-size', r.textSize);
        el.setAttribute('data-motion', r.motion);
        return r;
    }

    var api = { KEY: KEY, DEFAULTS: DEFAULTS, normalize: normalize, resolve: resolve, load: load, save: save, apply: apply };
    w.NetgraderDisplay = api;
    apply(load());

    // "Follow system" must track the computer's setting while the page is open.
    if (w.matchMedia) {
        var queries = ['(prefers-color-scheme: light)', '(prefers-reduced-motion: reduce)'];
        for (var i = 0; i < queries.length; i++) {
            var mql = w.matchMedia(queries[i]);
            var onChange = function () { apply(load()); };
            if (mql.addEventListener) { mql.addEventListener('change', onChange); }
            else if (mql.addListener) { mql.addListener(onChange); }
        }
    }
})(window, document);
```

- [ ] **Step 4: Load it in `<head>`, and test that**

In `templates/base.html`, add as the **first** element inside `<head>` after the `<meta charset>` and `<meta name="viewport">` lines:

```html
    <!-- Applies saved display settings before anything paints (no theme flash). -->
    <script src="/static/js/display-boot.js?v={{ asset_version }}"></script>
```

Append to `tests/test_assets.py`:

```python
def test_display_settings_apply_before_any_stylesheet():
    html = client.get("/").text
    head = html[:html.index("</head>")]
    boot = head.index("/static/js/display-boot.js")
    first_css = head.index('rel="stylesheet"')
    assert boot < first_css
```

- [ ] **Step 5: Run all tests**

Run: `node --test tests/js/display-boot.test.mjs`
Expected: 7 pass.
Run: `python -m pytest -q`
Expected: all pass. `test_module_parses` checks `display-boot.js` as a classic script (Task 1 added it to `CLASSIC_SCRIPTS`).

- [ ] **Step 6: Commit**

```bash
git add static/js/display-boot.js tests/js/display-boot.test.mjs templates/base.html tests/test_assets.py
git commit -m "feat(display): apply saved display settings before first paint" -m "A classic ES5 script in <head> reads the saved text size, theme, contrast and motion settings and sets them as attributes on <html>, so there is no flash of the wrong theme. Blocked or corrupt storage falls back to defaults, and Follow system tracks the computer's setting live. The Display menu reuses window.NetgraderDisplay, so there is one implementation." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Replace hard-coded colours and pixel font sizes

**Files:**
- Modify: `static/css/legacy.css`, `static/js/legacy/app.js` (inline styles only), `templates/partials/*.html` and `templates/base.html` (inline styles only)
- Test: `tests/test_styles.py`

**Interfaces:**
- Consumes: the tokens from Task 2.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_styles.py`:

```python
# tests/test_styles.py
"""
Colours come only from tokens.css, so every theme reaches every element, and
font sizes are in rem, so the text-size setting reaches every element.
Static checks, no browser.
"""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(__file__))
COLOUR_RE = re.compile(r"#[0-9A-Fa-f]{3,8}\b|rgba?\(")
PX_FONT_RE = re.compile(r"font-size\s*:\s*[0-9.]+px")
REM_FONT_RE = re.compile(r"font-size\s*:\s*([0-9.]+)rem")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _css_without_comments(text):
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def _styled_files():
    files = [os.path.join(ROOT, "static", "css", "legacy.css")]
    files += glob.glob(os.path.join(ROOT, "static", "css", "layouts", "*.css"))
    files += glob.glob(os.path.join(ROOT, "templates", "**", "*.html"), recursive=True)
    files += [os.path.join(ROOT, "static", "js", "legacy", "app.js")]
    return files


def test_no_hard_coded_colours_outside_tokens():
    hits = []
    for path in _styled_files():
        text = _css_without_comments(_read(path)) if path.endswith(".css") else _read(path)
        for lineno, line in enumerate(text.splitlines(), 1):
            if COLOUR_RE.search(line):
                hits.append(f"{os.path.relpath(path, ROOT)}:{lineno}: {line.strip()[:90]}")
    assert not hits, "Use a token from tokens.css:\n" + "\n".join(hits)


def test_font_sizes_are_rem_and_at_least_12px():
    hits = []
    for path in _styled_files():
        text = _read(path)
        for lineno, line in enumerate(text.splitlines(), 1):
            if PX_FONT_RE.search(line):
                hits.append(f"{os.path.relpath(path, ROOT)}:{lineno}: px font size")
            for value in REM_FONT_RE.findall(line):
                if float(value) < 0.75:
                    hits.append(f"{os.path.relpath(path, ROOT)}:{lineno}: {value}rem is below 12px")
    assert not hits, "\n".join(hits)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_styles.py -q`
Expected: FAIL, listing about 190 colour hits and about 60 px font sizes.

- [ ] **Step 3: Replace colours using this mapping**

Apply to every hit in `legacy.css`, and to inline `style="..."` colours in the templates and `legacy/app.js`. Decide by colour family, then by the property it is used for.

| Colour family | Property | Token |
|---|---|---|
| Light greys and whites (`#FFFFFF`, `#FFF`, `#F9FAFB`, `#E2E8F0`, `#E6EDF5`) | `color` / `fill` | `--text`; but `--on-accent` when the same rule (or its parent button) has an accent/blue background |
| Mid greys (`#8B98A9`, `#B9C4D2`, `#9CA3AF`) | `color` | `--text-muted` |
| Mid greys | `background` | `--line-strong` |
| Dark greys (`#0B0F19`, `#0F172A`, `#131922`, `#131B2E`, `#1A2130`, `rgba(15,23,42,…)`, `rgba(30,41,59,…)`) | background | `--surface-sunken` (darkest), `--surface` or `--surface-raised` (lightest), by lightness |
| `#374151`, `#4B5563` | background / border | `--line-strong` |
| `#2A3441`, `#222B38` | border | `--line` |
| `rgba(255,255,255,a)` | background or border | `--tint-neutral-weak` (a ≤ 0.04), `-mid` (≤ 0.08), `-strong` (> 0.08) |
| `rgba(0,0,0,a)` | background | `--scrim` |
| `rgba(0,0,0,a)` | box-shadow | `--shadow-card` (the whole shadow value) |
| Blues (`#2563EB`, `#1D4ED8`, `#3B82F6`, `#4DA3FF`, `#60A5FA`) | solid | `--accent`; `--accent-strong` on `:hover` or `:active` rules |
| Blue rgba (`rgba(59,130,246,a)`, `rgba(77,163,255,a)`) | tint | `--tint-accent-weak` (a ≤ 0.1), `-mid` (≤ 0.2), `-strong` (> 0.2) |
| Greens (`#10B981`, `#059669`, `#3DDC97`, `#6EE7B7`) | solid | `--status-ok` |
| Green rgba (`rgba(16,185,129,a)`, `rgba(61,220,151,a)`) | tint | `--tint-ok-*` by the same alpha rule |
| Reds (`#EF4444`, `#DC2626`, `#FF6B6B`, `#FCA5A5`, `#FF9D9D`, `#FF8F8F`) | solid | `--status-bad` |
| Red rgba (`rgba(239,68,68,a)`, `rgba(255,107,107,a)`) | tint | `--tint-bad-*` |
| Ambers (`#D97706`, `#FCD34D`, `#FFC861`) | solid | `--status-warn` |
| Amber rgba (`rgba(245,158,11,a)`, `rgba(255,200,97,a)`) | tint | `--tint-warn-*` |
| Purples (`#C9A8FF`, `#A78BFA`) | solid | `--map-host` |
| Purple rgba (`rgba(170,130,255,a)`) | tint | `--tint-host-*` |
| Grey rgba (`rgba(139,152,169,a)`, `rgba(156,163,175,a)`) | tint | `--tint-neutral-*` |
| SVG badge colours in CSS (`#93C5FD`, `#6EE7B7` text; `#0F172A`, `#064E3B` fill) | fill | `--map-port`, `--map-ip`, `--map-badge-bg` |
| Glow box-shadows using green, blue or red rgba (pulse keyframes, `0 0 0 Npx rgba(...)`) | box-shadow | remove the glow (`box-shadow: none`). No glows in the Console style. |

Rules:
- Replace a whole `background: linear-gradient(...)` built from these colours with the single token of its dominant colour. The Console style is flat.
- Leave `transparent`, `currentColor` and `inherit` as they are.
- Do not change any selector, layout property or spacing. This task changes only colour values and font sizes.

- [ ] **Step 4: Convert font sizes**

First, set the body text size from the type scale (spec 6.2: 15 px at Default). In the `html, body` (or `body`) rule in `legacy.css`, set `font-size: var(--text-base);`, adding the declaration if the rule has none. Then every `font-size: Npx` becomes `font-size: Mrem` where `M = max(N / 16, 0.75)`, written with up to 4 decimals, trailing zeros dropped (for example `11px` → `0.75rem`, `13px` → `0.8125rem`, `22px` → `1.375rem`). Existing `rem` values below `0.75` become `0.75rem`. Apply this in `legacy.css`, inline styles in the templates, and inline styles in `legacy/app.js`. Leave SVG `font-size` attributes set from JavaScript in `static/js/map/` alone; Task 5 owns the map.

- [ ] **Step 5: Run all tests**

Run: `python -m pytest tests/test_styles.py -q`
Expected: pass.
Run: `python -m pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add static/css/legacy.css static/js/legacy/app.js templates
git commit -m "refactor(theme): colours from tokens, font sizes in rem" -m "Every hard-coded colour in legacy.css, the templates and legacy/app.js inline styles maps to a semantic token, so Light and high-contrast themes reach every element. Glows and gradients are removed for the flat Console style. Font sizes are rem with a 12px floor, so the text-size setting scales everything." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Map colours from tokens

**Files:**
- Modify: `static/js/map/svg-shapes.js`, `static/js/map/topology.js`, `tests/js/svg-shapes.test.mjs`, `tests/test_styles.py`

**Interfaces:**
- Produces: `paint(el: Element, props: Record<string,string>): Element` from `map/svg-shapes.js`. It sets each prop with `el.style.setProperty(kebab(name), value)`. SVG presentation attributes don't accept `var()`, but the `style` property does.

- [ ] **Step 1: Write the failing tests**

Append to `tests/js/svg-shapes.test.mjs`:

```js
import { paint } from '../../static/js/map/svg-shapes.js';

test('paint sets CSS properties so var() tokens work on SVG', () => {
    const calls = [];
    const el = { style: { setProperty: (k, v) => calls.push([k, v]) } };
    assert.equal(paint(el, { fill: 'var(--map-router)', strokeWidth: '2', fillOpacity: '0.15' }), el);
    assert.deepEqual(calls, [['fill', 'var(--map-router)'], ['stroke-width', '2'], ['fill-opacity', '0.15']]);
});
```

(Merge the `import` into the existing import line at the top of the file.)

Append to `tests/test_styles.py`:

```python
def test_map_has_no_hard_coded_colours():
    hits = []
    for path in glob.glob(os.path.join(ROOT, "static", "js", "map", "*.js")):
        for lineno, line in enumerate(_read(path).splitlines(), 1):
            if COLOUR_RE.search(line):
                hits.append(f"{os.path.relpath(path, ROOT)}:{lineno}: {line.strip()[:90]}")
    assert not hits, "Map colours must be var(--map-...) tokens:\n" + "\n".join(hits)
```

- [ ] **Step 2: Run to verify they fail**

Run: `node --test tests/js/svg-shapes.test.mjs` → FAIL, `paint` is not exported.
Run: `python -m pytest tests/test_styles.py -q` → FAIL, about 20 map colour hits.

- [ ] **Step 3: Add `paint` and use tokens**

In `static/js/map/svg-shapes.js`, add:

```js
// Sets presentation values through the style property. SVG attributes such as
// fill="..." do not resolve var(--token); inline style properties do.
export function paint(el, props) {
    for (const [name, value] of Object.entries(props)) {
        el.style.setProperty(name.replace(/[A-Z]/g, c => '-' + c.toLowerCase()), value);
    }
    return el;
}
```

Then replace every colour in `map/svg-shapes.js` and `map/topology.js`:

| Where | Before | After |
|---|---|---|
| `createSvgBadge` rect fill | `isIp ? '#064E3B' : '#0F172A'` | `paint(rectElem, { fill: 'var(--map-badge-bg)', stroke: isIp ? 'var(--map-ip)' : 'var(--map-port)' })` (and remove the `setAttribute('fill'/'stroke', …)` calls) |
| `createSvgBadge` text fill | `isIp ? '#6EE7B7' : '#93C5FD'` | `paint(textElem, { fill: isIp ? 'var(--map-ip)' : 'var(--map-port)' })` |
| `createDeviceIcon` default `fill: '#1F2937'` | attribute | `var(--map-device-fill)`, applied through `paint` for `fill` and `stroke` (`shape()` keeps `setAttribute` for geometry and uses `paint` for `fill`, `stroke`, `fill-opacity`) |
| `draw()` link colours | `'#10B981'`, `'#EF4444'`, `'#F59E0B'`, `'#6B7280'` | `'var(--map-link-ok)'`, `'var(--map-link-bad)'`, `'var(--map-link-inferred)'`, `'var(--map-link-unverified)'`, applied with `paint(line, { stroke: strokeColor })` |
| `draw()` link badge bg `'#111827'` | attribute | `paint(badgeBg, { fill: 'var(--map-badge-bg)', stroke: strokeColor })`; `paint(badgeLabel, { fill: strokeColor })` |
| `draw()` node colours | `'#3B82F6'`, `'#9CA3AF'`, `'#10B981'`, `'#8B5CF6'` | `'var(--map-router)'`, `'var(--map-unknown)'`, `'var(--map-switch)'`, `'var(--map-host)'` |
| `draw()` glow circle fill (four `rgba(...)`) | attribute | `paint(glowCircle, { fill: nodeColor, fillOpacity: '0.15' })` |
| Fonts set via attributes (`font-family`, `font-size`) | attributes | leave as is (not colours) |

Device caption text (`caption()` in `createDeviceIcon`) uses `paint(el, { fill: color })`.

- [ ] **Step 4: Run all tests**

Run: `node --test tests/js/*.test.mjs` → all pass.
Run: `python -m pytest -q` → all pass.

- [ ] **Step 5: Commit**

```bash
git add static/js/map tests/js/svg-shapes.test.mjs tests/test_styles.py
git commit -m "feat(map): draw the topology with theme tokens" -m "Devices, links and badges take their colours from --map-* tokens through inline style properties, since SVG attributes do not resolve var(). The map now follows Dark, Light and high contrast, with every stroke tested at 3:1 against the page." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Icon sprite

**Files:**
- Create: `scripts/build_icon_sprite.py`, `static/icons/sprite.svg`, `static/icons/LICENSE-tabler.txt`, `static/js/core/icons.js`, `tests/test_icons.py`, `tests/js/icons.test.mjs`
- Modify: `templates/base.html` (one `<meta>`)

**Interfaces:**
- Produces:
  - sprite symbol ids (semantic names, not Tabler names): `topology`, `instructor`, `grading`, `display`, `ai`, `upload`, `file`, `folder`, `alert`, `check`, `x`, `download`, `copy`, `send`, `report`, `shield`, `network`, `map`, `settings`, `chart`, `search`, `tag`, `pin`, `info`, `generate`, `refresh`, `fit`
  - `icon(name: string, { label?: string } = {}) -> SVGSVGElement` from `core/icons.js`
  - `iconMarkup(name: string) -> string` from `core/icons.js`. `name` must be a sprite id literal, never user data.
  - `<meta name="netgrader-icons" content="/static/icons/sprite.svg?v=...">` in `<head>`

- [ ] **Step 1: Write the build script**

Create `scripts/build_icon_sprite.py`:

```python
# scripts/build_icon_sprite.py
"""
Build static/icons/sprite.svg from Tabler Icons (MIT), outline style.

Run once on a developer machine with internet access, then commit the output:

    npm pack @tabler/icons@3        # downloads tabler-icons-<version>.tgz
    tar -xzf tabler-icons-*.tgz     # extracts ./package/icons/outline/*.svg
    python scripts/build_icon_sprite.py package/icons/outline <version>

Lab PCs only ever load the committed sprite.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "static", "icons", "sprite.svg")

# Sprite id (what the UI asks for) -> Tabler outline icon file name.
ICONS = {
    "topology": "topology-star-3",
    "instructor": "school",
    "grading": "checklist",
    "display": "typography",
    "ai": "cpu",
    "upload": "upload",
    "file": "file-text",
    "folder": "folder-open",
    "alert": "alert-triangle",
    "check": "circle-check",
    "x": "circle-x",
    "download": "download",
    "copy": "copy",
    "send": "send",
    "report": "report-analytics",
    "shield": "shield-check",
    "network": "network",
    "map": "map",
    "settings": "settings",
    "chart": "chart-bar",
    "search": "search",
    "tag": "tag",
    "pin": "map-pin",
    "info": "info-circle",
    "generate": "file-plus",
    "refresh": "refresh",
    "fit": "arrows-maximize",
}

BOUNDING_BOX = re.compile(r'<path\s+stroke="none"\s+d="M0 0h24v24H0z"\s+fill="none"\s*/>')


def main(src_dir: str, version: str) -> None:
    symbols = []
    for sprite_id, tabler in sorted(ICONS.items()):
        path = os.path.join(src_dir, f"{tabler}.svg")
        if not os.path.isfile(path):
            sys.exit(f"missing Tabler icon '{tabler}' (for '{sprite_id}') in {src_dir}")
        svg = open(path, encoding="utf-8").read()
        inner = re.search(r"<svg[^>]*>(.*)</svg>", svg, re.S).group(1)
        inner = BOUNDING_BOX.sub("", inner).strip()
        inner = re.sub(r"\s+", " ", inner)
        symbols.append(
            f'  <symbol id="{sprite_id}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">{inner}</symbol>'
        )
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"<!-- Tabler Icons {version} (MIT), outline. Built by scripts/build_icon_sprite.py -->\n")
        f.write('<svg xmlns="http://www.w3.org/2000/svg">\n' + "\n".join(symbols) + "\n</svg>\n")
    print(f"wrote {OUT}: {len(symbols)} icons")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: build_icon_sprite.py <tabler outline dir> <version>")
    main(sys.argv[1], sys.argv[2])
```

- [ ] **Step 2: Fetch Tabler Icons and build the sprite**

Run in the session scratchpad (not the repo):

```bash
npm pack @tabler/icons@3
tar -xzf tabler-icons-*.tgz
python <repo>/scripts/build_icon_sprite.py package/icons/outline <exact version from the tgz name>
```

Expected: `wrote .../static/icons/sprite.svg: 27 icons`. If an icon is missing in that version, the script exits naming it. Pick the closest Tabler icon by name, update `ICONS`, and say so in the report.

Copy the package's `LICENSE` file to `static/icons/LICENSE-tabler.txt`, and add as its first line: `Tabler Icons <version> -- https://github.com/tabler/tabler-icons`.

- [ ] **Step 3: Write `core/icons.js`**

```js
// static/js/core/icons.js
// Icons from the vendored Tabler sprite (static/icons/sprite.svg). Names are
// sprite ids from scripts/build_icon_sprite.py -- always literals in code,
// never data from a file or the server.
const SVG_NS = 'http://www.w3.org/2000/svg';

function spriteUrl() {
    const meta = document.querySelector('meta[name="netgrader-icons"]');
    return meta ? meta.content : '/static/icons/sprite.svg';
}

// A decorative icon is hidden from screen readers; pass a label when the icon
// is the only thing that says what something means.
export function icon(name, { label } = {}) {
    const svg = document.createElementNS(SVG_NS, 'svg');
    svg.setAttribute('class', 'icon');
    if (label) {
        svg.setAttribute('role', 'img');
        svg.setAttribute('aria-label', label);
    } else {
        svg.setAttribute('aria-hidden', 'true');
    }
    const use = document.createElementNS(SVG_NS, 'use');
    use.setAttribute('href', `${spriteUrl()}#${name}`);
    svg.appendChild(use);
    return svg;
}

// For legacy/app.js templates that still build markup strings.
export function iconMarkup(name) {
    if (!/^[a-z-]+$/.test(name)) throw new Error(`invalid icon name: ${name}`);
    return `<svg class="icon" aria-hidden="true"><use href="${spriteUrl()}#${name}"></use></svg>`;
}
```

In `templates/base.html` `<head>`, add:

```html
    <meta name="netgrader-icons" content="/static/icons/sprite.svg?v={{ asset_version }}">
```

- [ ] **Step 4: Write the tests**

Create `tests/test_icons.py`:

```python
# tests/test_icons.py
"""Every icon the UI asks for exists in the vendored sprite, and the licence ships with it."""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(__file__))
SPRITE = os.path.join(ROOT, "static", "icons", "sprite.svg")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _sprite_ids():
    return set(re.findall(r'<symbol id="([a-z-]+)"', _read(SPRITE)))


def _requested_ids():
    found = set()
    for path in glob.glob(os.path.join(ROOT, "templates", "**", "*.html"), recursive=True):
        found |= set(re.findall(r"sprite\.svg[^#\"']*#([a-z-]+)", _read(path)))
    for path in glob.glob(os.path.join(ROOT, "static", "js", "**", "*.js"), recursive=True):
        found |= set(re.findall(r"\bicon(?:Markup)?\(\s*['\"]([a-z-]+)['\"]", _read(path)))
    return found


def test_every_requested_icon_is_in_the_sprite():
    missing = sorted(_requested_ids() - _sprite_ids())
    assert not missing, f"icons used but not in sprite.svg: {missing}"


def test_sprite_matches_the_build_script():
    from scripts.build_icon_sprite import ICONS
    assert _sprite_ids() == set(ICONS)


def test_tabler_licence_ships_with_the_sprite():
    licence = _read(os.path.join(ROOT, "static", "icons", "LICENSE-tabler.txt"))
    assert "MIT" in licence and "Tabler Icons" in licence.splitlines()[0]


def test_sprite_is_self_contained():
    sprite = _read(SPRITE)
    assert "http://" not in sprite.replace('xmlns="http://www.w3.org/2000/svg"', "")
    assert "<script" not in sprite
```

Create `tests/js/icons.test.mjs`:

```js
// tests/js/icons.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';

globalThis.document = { querySelector: () => ({ content: '/static/icons/sprite.svg?v=7' }) };
const { iconMarkup } = await import('../../static/js/core/icons.js');

test('iconMarkup points at the versioned sprite', () => {
    assert.equal(iconMarkup('check'),
        '<svg class="icon" aria-hidden="true"><use href="/static/icons/sprite.svg?v=7#check"></use></svg>');
});

test('iconMarkup refuses anything that is not a plain icon id', () => {
    for (const bad of ['"><img src=x>', 'Check', 'a b', '']) {
        assert.throws(() => iconMarkup(bad));
    }
});
```

- [ ] **Step 5: Run all tests**

Run: `node --test tests/js/*.test.mjs` → all pass.
Run: `python -m pytest -q` → all pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/build_icon_sprite.py static/icons static/js/core/icons.js tests/test_icons.py tests/js/icons.test.mjs templates/base.html
git commit -m "feat(icons): vendored Tabler icon sprite" -m "27 Tabler outline icons (MIT) in one committed sprite, built by scripts/build_icon_sprite.py with semantic ids, so lab PCs load them offline. core/icons.js renders them as elements or, for legacy templates, as a fixed-format string that rejects anything but a plain id." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Rail, context bar and Display menu

**Files:**
- Create: `templates/partials/rail.html`, `templates/partials/context_bar.html`, `templates/partials/display_menu.html`, `static/css/layouts/shell.css`, `static/js/shell/display-menu.js`, `tests/test_shell.py`
- Modify: `templates/base.html`, `templates/partials/visualizer.html` (Reset View), `static/css/legacy.css` (remove navbar rules, add spinner), `static/js/legacy/app.js` (`switchMode`, engine status, spinner), `static/js/main.js`
- Delete: `templates/partials/navbar.html`

**Interfaces:**
- Consumes: `window.NetgraderDisplay` (Task 3); sprite ids `topology`, `instructor`, `grading`, `display`, `ai` (Task 6).
- Produces: `initDisplayMenu(button: HTMLElement, panel: HTMLElement, display = window.NetgraderDisplay): void` from `shell/display-menu.js`. Element ids `display-menu-btn`, `display-menu`, `context-title`.
- Keeps: element ids `nav-mode-visualizer`, `nav-mode-teacher`, `nav-mode-student`, `ai-status`, `ai-status-label`, `reset-btn`, and the class `mode-tab-btn` plus `data-mode` on rail items. Legacy mode switching keeps working unchanged.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_shell.py`:

```python
# tests/test_shell.py
"""The rail, context bar and Display menu, for the instructor and for a lab PC."""
import re

from tests.test_frontend_modules import render_page


def test_rail_is_the_main_navigation():
    html = render_page(instructor=True)
    assert re.search(r'<nav class="rail" aria-label="Main">', html)
    assert 'class="navbar"' not in html
    items = re.findall(r'data-mode="(\w+)"', html)
    assert items == ["visualizer", "teacher", "student"]


def test_lab_pc_rail_has_no_instructor_item():
    html = render_page(instructor=False)
    assert re.findall(r'data-mode="(\w+)"', html) == ["visualizer", "student"]


def test_rail_items_have_visible_labels():
    html = render_page(instructor=True)
    for label in ("Discovery", "Instructor", "Grading", "Display"):
        assert re.search(rf'<span class="rail-label">{label}</span>', html), label


def test_context_bar_names_the_screen():
    html = render_page(instructor=True)
    assert re.search(r'<h1 class="context-title" id="context-title">Topology Discovery</h1>', html)


def test_display_menu_offers_every_setting():
    html = render_page(instructor=False)
    assert re.search(r'id="display-menu"[^>]*role="dialog"[^>]*hidden', html)
    expected = {
        "textSize": ["sm", "md", "lg", "xl"],
        "theme": ["dark", "light", "system"],
        "contrast": ["standard", "high"],
        "motion": ["system", "reduce"],
    }
    for name, values in expected.items():
        assert re.findall(rf'name="{name}" value="(\w+)"', html) == values, name
    assert "easier to read on projectors" in html


def test_display_button_controls_the_menu():
    html = render_page(instructor=True)
    assert re.search(r'id="display-menu-btn"[^>]*aria-controls="display-menu"[^>]*aria-expanded="false"', html)


def test_reset_view_lives_in_the_map_toolbar():
    html = render_page(instructor=True)
    toolbar_start = html.index('class="canvas-actions"')
    canvas_start = html.index('id="canvas-viewport"')
    assert toolbar_start < html.index('id="reset-btn"') < canvas_start
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/test_shell.py -q`
Expected: FAIL, no rail.

- [ ] **Step 3: Write the partials**

`templates/partials/rail.html`:

```html
<nav class="rail" aria-label="Main">
    <div class="rail-brand">
        <span class="rail-mark" aria-hidden="true">NG</span>
        <span class="rail-brand-name">Netgrader</span>
    </div>
    <div class="rail-items">
        <button type="button" id="nav-mode-visualizer" class="rail-item mode-tab-btn active" data-mode="visualizer" aria-current="page">
            <svg class="icon" aria-hidden="true"><use href="/static/icons/sprite.svg?v={{ asset_version }}#topology"></use></svg>
            <span class="rail-label">Discovery</span>
        </button>
        {% if is_instructor %}
        <!-- Rendered only for the computer running the server (see is_instructor in src/app.py). -->
        <button type="button" id="nav-mode-teacher" class="rail-item mode-tab-btn" data-mode="teacher" aria-current="false">
            <svg class="icon" aria-hidden="true"><use href="/static/icons/sprite.svg?v={{ asset_version }}#instructor"></use></svg>
            <span class="rail-label">Instructor</span>
        </button>
        {% endif %}
        <button type="button" id="nav-mode-student" class="rail-item mode-tab-btn" data-mode="student" aria-current="false">
            <svg class="icon" aria-hidden="true"><use href="/static/icons/sprite.svg?v={{ asset_version }}#grading"></use></svg>
            <span class="rail-label">Grading</span>
        </button>
    </div>
    <div class="rail-footer">
        <button type="button" id="display-menu-btn" class="rail-item" aria-haspopup="dialog" aria-controls="display-menu" aria-expanded="false">
            <svg class="icon" aria-hidden="true"><use href="/static/icons/sprite.svg?v={{ asset_version }}#display"></use></svg>
            <span class="rail-label">Display</span>
        </button>
        <!-- Whether the local AI model is reachable. Filled by legacy/app.js from /api/llm/status. -->
        <button type="button" id="ai-status" class="rail-item ai-status-indicator" data-state="checking" title="Checking the local AI model...">
            <span class="ai-status-dot" aria-hidden="true"></span>
            <span class="rail-label" id="ai-status-label">AI: checking</span>
        </button>
    </div>
    {% include "partials/display_menu.html" %}
</nav>
```

`templates/partials/context_bar.html`:

```html
<header class="context-bar">
    <h1 class="context-title" id="context-title">Topology Discovery</h1>
</header>
```

`templates/partials/display_menu.html`:

```html
<div class="display-menu" id="display-menu" role="dialog" aria-label="Display settings" hidden>
    <fieldset>
        <legend>Text size</legend>
        <label><input type="radio" name="textSize" value="sm"> Small</label>
        <label><input type="radio" name="textSize" value="md"> Default</label>
        <label><input type="radio" name="textSize" value="lg"> Large</label>
        <label><input type="radio" name="textSize" value="xl"> Extra large</label>
    </fieldset>
    <fieldset>
        <legend>Theme</legend>
        <label><input type="radio" name="theme" value="dark"> Dark</label>
        <label><input type="radio" name="theme" value="light"> Light <span class="display-hint">easier to read on projectors</span></label>
        <label><input type="radio" name="theme" value="system"> Follow system</label>
    </fieldset>
    <fieldset>
        <legend>Contrast</legend>
        <label><input type="radio" name="contrast" value="standard"> Standard</label>
        <label><input type="radio" name="contrast" value="high"> High</label>
    </fieldset>
    <fieldset>
        <legend>Motion</legend>
        <label><input type="radio" name="motion" value="system"> Follow system</label>
        <label><input type="radio" name="motion" value="reduce"> Reduce</label>
    </fieldset>
</div>
```

- [ ] **Step 4: Recompose `base.html`**

Replace `{% include "partials/navbar.html" %}` and wrap the workspace so the layout is rail + main column:

```html
    <div class="app-layout">
        {% include "partials/rail.html" %}
        <div class="app-main">
            {% include "partials/context_bar.html" %}

            <!-- Main Workspace -->
            <main class="workspace-grid" id="workspace-grid">
                ... (the existing control panel, resizer and visualizer include, unchanged) ...
            </main>
        </div>
    </div>
```

(`... (the existing ...) ...` means: keep the current contents of `<main>` exactly; only its parent changes.)

Add, after the `tokens.css` link and before `legacy.css`:

```html
    <link rel="stylesheet" href="/static/css/layouts/shell.css?v={{ asset_version }}">
```

`git rm templates/partials/navbar.html`.

In `templates/partials/visualizer.html`, move the Reset View button into `.canvas-actions`, after the Fit View button:

```html
                        <button id="reset-btn" class="btn btn-sm btn-outline" title="Clear current workspace">Reset View</button>
```

- [ ] **Step 5: Write `static/css/layouts/shell.css`**

```css
/* static/css/layouts/shell.css -- rail, context bar, Display menu, icon base. */

.icon { width: 1.125rem; height: 1.125rem; flex: none; vertical-align: -0.2em; }

.app-layout {
    display: grid;
    grid-template-columns: var(--rail-width) minmax(0, 1fr);
    height: 100vh;
    background: var(--surface-base);
    color: var(--text);
}
.app-main {
    display: grid;
    grid-template-rows: var(--context-height) minmax(0, 1fr);
    min-width: 0;
    min-height: 0;
}

.rail {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    padding: 0.75rem 0.5rem;
    background: var(--surface-sunken);
    border-right: 1px solid var(--line);
    min-height: 0;
}
.rail-brand { display: flex; flex-direction: column; align-items: center; gap: 0.25rem; margin-bottom: 0.75rem; }
.rail-mark {
    width: 2rem; height: 2rem; border-radius: var(--radius-sm);
    display: grid; place-items: center;
    background: var(--accent); color: var(--on-accent);
    font: 600 var(--text-xs) var(--font-mono);
}
.rail-brand-name { font-size: var(--text-xs); font-weight: 600; color: var(--text-muted); }
.rail-items { display: flex; flex-direction: column; gap: 0.25rem; }
.rail-footer { margin-top: auto; display: flex; flex-direction: column; gap: 0.25rem; }
.rail-item {
    display: flex; flex-direction: column; align-items: center; gap: 0.25rem;
    width: 100%; min-height: 3.25rem; padding: 0.5rem 0.25rem;
    border: 0; border-radius: var(--radius-md);
    background: transparent; color: var(--text-muted);
    font: 500 var(--text-xs) var(--font-main);
    cursor: pointer;
}
.rail-item .icon { width: 1.25rem; height: 1.25rem; }
.rail-item:hover { background: var(--tint-neutral-mid); color: var(--text); }
.rail-item.active { background: var(--surface-raised); color: var(--text); box-shadow: inset 2px 0 0 var(--accent); }
.rail-item:focus-visible, .display-menu input:focus-visible { outline: 2px solid var(--focus-ring); outline-offset: 2px; }
:root[data-contrast="high"] .rail-item:focus-visible { outline-width: 3px; }
.rail-label { max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.context-bar {
    display: flex; align-items: center; gap: 1rem;
    padding: 0 1rem;
    border-bottom: 1px solid var(--line);
    background: var(--surface);
    min-width: 0;
}
.context-title {
    margin: 0; font-size: var(--text-lg); font-weight: 600;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.display-menu {
    position: absolute;
    left: calc(100% + 0.5rem);
    bottom: 0.75rem;
    z-index: 50;
    width: 16rem;
    padding: 0.75rem;
    background: var(--surface-raised);
    border: 1px solid var(--line-strong);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-pop);
    color: var(--text);
}
.display-menu[hidden] { display: none; }
.display-menu fieldset { border: 0; margin: 0 0 0.75rem; padding: 0; }
.display-menu fieldset:last-child { margin-bottom: 0; }
.display-menu legend { font-size: var(--text-xs); font-weight: 600; color: var(--text-muted); margin-bottom: 0.25rem; }
.display-menu label { display: flex; align-items: center; gap: 0.5rem; padding: 0.25rem 0; font-size: var(--text-sm); cursor: pointer; }
.display-hint { color: var(--text-muted); font-size: var(--text-xs); }
```

In `legacy.css`, delete the rules whose selectors start with `.navbar`, `.brand-section`, `.brand-badge`, `.app-title`, `.main-mode-switcher`, `.mode-tab-btn`, `.mode-icon`, `.mode-text`, `.nav-controls`, `.system-status-indicator` and `.status-dot`, plus the `.app-layout` rule (now in `shell.css`), and any `@keyframes` only those rules used. Add the loading spinner that replaces the pulsing dot:

```css
.loading-spinner {
    width: 1.5rem; height: 1.5rem; margin: 0 auto 0.75rem;
    border: 2px solid var(--line-strong);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
```

- [ ] **Step 6: Wire the JS**

`static/js/shell/display-menu.js`:

```js
// static/js/shell/display-menu.js
// The Display settings popover in the rail. Settings logic lives in
// display-boot.js (window.NetgraderDisplay); this only drives the form.
export function initDisplayMenu(button, panel, display = window.NetgraderDisplay) {
    if (!button || !panel || !display) return;

    const sync = () => {
        const settings = display.load();
        for (const [name, value] of Object.entries(settings)) {
            const input = panel.querySelector(`input[name="${name}"][value="${value}"]`);
            if (input) input.checked = true;
        }
    };
    const open = () => {
        sync();
        panel.hidden = false;
        button.setAttribute('aria-expanded', 'true');
        (panel.querySelector('input:checked') || panel.querySelector('input'))?.focus();
    };
    const close = (returnFocus = true) => {
        panel.hidden = true;
        button.setAttribute('aria-expanded', 'false');
        if (returnFocus) button.focus();
    };

    button.addEventListener('click', () => (panel.hidden ? open() : close()));
    panel.addEventListener('change', (event) => {
        const input = event.target;
        if (!(input instanceof HTMLInputElement) || input.type !== 'radio') return;
        const next = { ...display.load(), [input.name]: input.value };
        display.save(next);
        display.apply(next);
    });
    panel.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') { event.stopPropagation(); close(); }
    });
    document.addEventListener('click', (event) => {
        if (!panel.hidden && !panel.contains(event.target) && !button.contains(event.target)) close(false);
    });
}
```

`static/js/main.js` becomes:

```js
// static/js/main.js
// Entry point. Loaded as a module from /assets/<version>/js/main.js, so every
// relative import below is versioned too.
import { initLegacyApp } from './legacy/app.js';
import { initDisplayMenu } from './shell/display-menu.js';

// Read by boot-check.js. Runs only if every import above parsed and loaded.
window.__netgraderBooted = true;

initLegacyApp();
initDisplayMenu(document.getElementById('display-menu-btn'), document.getElementById('display-menu'));
```

In `static/js/legacy/app.js`:
- Delete `const engineStatusLabel = document.getElementById('engine-status-label');` and every `if (engineStatusLabel) engineStatusLabel.textContent = ...;` line in `switchMode`.
- Add `const contextTitle = document.getElementById('context-title');` beside `canvasMainTitle`.
- In `switchMode`, after toggling `.active`, also set `aria-current`, and set the context title:

```js
        modeTabs.forEach(t => t.setAttribute('aria-current', t.getAttribute('data-mode') === mode ? 'page' : 'false'));
        const titles = { visualizer: 'Topology Discovery', teacher: 'Instructor Studio', student: 'Student Grading' };
        if (contextTitle) contextTitle.textContent = titles[mode] || '';
```

- In `showLoading`, replace the pulsing-dot markup `<div class="status-dot pulsing" style="...">` with `<div class="loading-spinner" aria-hidden="true"></div>`.

- [ ] **Step 7: Run all tests**

Run: `python -m pytest -q`
Expected: all pass, including `test_shell.py`, the id-coverage tests (`engine-status-label` is no longer looked up) and `test_instructor_access.py`.

- [ ] **Step 8: Commit**

```bash
git add -A templates static tests/test_shell.py
git commit -m "feat(shell): left rail, context bar and Display menu" -m "The top tab bar becomes a labelled left rail (Discovery, Instructor, Grading, then Display and AI status), with the screen name in a context bar. The Display menu sets text size, theme, contrast and motion through window.NetgraderDisplay. Reset View moves into the map toolbar, and the pulsing status dot is gone. Mode switching is unchanged: rail items keep the mode-tab-btn class and data-mode." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

The Display menu's behaviour (open, Esc, outside click, live theme change) is verified in the Task 9 browser walkthrough rather than with a DOM-less unit test.

---

### Task 8: Remove every emoji

**Files:**
- Modify: `templates/partials/panel_discovery.html`, `panel_grading.html`, `panel_instructor.html`, `visualizer.html`; `static/js/legacy/app.js`; `static/js/core/toast.js`
- Create: `tests/test_no_emoji.py`

**Interfaces:**
- Consumes: `icon`, `iconMarkup` (Task 6); sprite ids listed in Task 6.

- [ ] **Step 1: Write the failing test**

Create `tests/test_no_emoji.py`:

```python
# tests/test_no_emoji.py
"""No emoji in the UI (issue #15). Icons come from the Tabler sprite."""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(__file__))
EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF☀-➿⬀-⯿⌀-⏿️⃣]"
)


def test_no_emoji_in_templates_or_scripts():
    hits = []
    files = glob.glob(os.path.join(ROOT, "templates", "**", "*.html"), recursive=True)
    files += glob.glob(os.path.join(ROOT, "static", "js", "**", "*.js"), recursive=True)
    for path in files:
        with open(path, encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                for ch in EMOJI_RE.findall(line):
                    hits.append(f"{os.path.relpath(path, ROOT)}:{lineno}: U+{ord(ch):04X}")
    assert not hits, "\n".join(hits)


def test_upload_boxes_say_what_they_accept():
    with open(os.path.join(ROOT, "templates", "partials", "panel_grading.html"), encoding="utf-8") as f:
        grading = f.read()
    assert "Accepts .txt or .json" in grading
    assert "Accepts .pkt, .pka, .xml, .zip or .txt" in grading
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_no_emoji.py -q`
Expected: FAIL, about 50 hits.

- [ ] **Step 3: Replace each emoji**

Templates: an icon is `<svg class="icon" aria-hidden="true"><use href="/static/icons/sprite.svg?v={{ asset_version }}#ID"></use></svg>`.

| File | Emoji (context) | Replacement |
|---|---|---|
| `panel_discovery.html` | 📂 card icon | icon `folder` (keep the `card-icon` wrapper span) |
| `panel_discovery.html` | 📥 upload icon | icon `upload` inside the `upload-icon` div |
| `panel_discovery.html` | ⚠️ conflicts card icon | icon `alert` |
| `panel_grading.html` | 1️⃣ / 2️⃣ step card icons (keycaps) | `<span class="step-number">1</span>` / `2` |
| `panel_grading.html` | 📄 rubric upload icon | icon `file` |
| `panel_grading.html` | 📥 submission upload icon | icon `upload` |
| `panel_grading.html` | 🚀 in "Submit & Evaluate Lab Assignment" | icon `send` before the text |
| `panel_grading.html` | 🏆 report card icon | icon `report` |
| `panel_grading.html` | ✅ "10 Passed" / ❌ "2 Failed" placeholders | text only: `10 Passed` / `2 Failed` (JS fills these) |
| `panel_grading.html` | 📥 "Download Grade Report (.txt)" | icon `download` before the text |
| `panel_instructor.html` | 👨‍🏫 card icon | icon `instructor` |
| `panel_instructor.html` | 🛡️ policies title | icon `shield` |
| `panel_instructor.html` | 🌐 / 🗺️ / ⚙️ policy group titles | icons `network` / `map` / `settings` |
| `panel_instructor.html` | 📑 reference upload icon | icon `upload` |
| `panel_instructor.html` | ⚡ "Generate Rubric & instructions.txt" | icon `generate` |
| `panel_instructor.html` | ✅ result card icon | icon `check` |
| `panel_instructor.html` | 📥 "Download instructions.txt" / 📋 "Copy to Clipboard" | icons `download` / `copy` |
| `panel_instructor.html` | 📊 batch card icon | icon `chart` |
| `panel_instructor.html` | ⚡ "Grade All Submissions" | icon `send` |
| `panel_instructor.html` | 🔍 "Review all" | icon `search` |
| `panel_instructor.html` | 📥 "Download Gradebook CSV" | icon `download` |
| `visualizer.html` | 🏷️ Ports toggle / 🌐 IP toggle | icons `tag` / `network` |
| `visualizer.html` | 🌐 empty-state icon | icon `topology` |

Add the upload hints under the drop-zone hint line in each box:
- Student Step 1: `<span class="dropzone-accepts">Accepts .txt or .json (the rubric file from your instructor)</span>`
- Student Step 2: `<span class="dropzone-accepts">Accepts .pkt, .pka, .xml, .zip or .txt</span>`
- Discovery: `<span class="dropzone-accepts">Accepts .pkt, .pka, .xml, .zip, .txt or .log</span>`
- Instructor reference: `<span class="dropzone-accepts">Accepts .pkt, .pka, .xml, .zip or .txt</span>`

and in `legacy.css`: `.dropzone-accepts { display: block; margin-top: 0.25rem; font-size: var(--text-xs); color: var(--text-muted); }`.

JavaScript (add `import { icon, iconMarkup } from '../core/icons.js';` to `legacy/app.js`):

| Where | Before | After |
|---|---|---|
| `showPanelMessage` calls (4×) | `<div class="empty-icon">⚠️</div>` | `<div class="empty-icon">${iconMarkup('alert')}</div>` |
| rubric status | `'✅ Verified'` / `'❌ Error'` | `'Verified'` / `'Error'` |
| report tags | `` `✅ ${n} Passed` `` / `` `❌ ${n} Failed` `` | `` `${n} Passed` `` / `` `${n} Failed` `` |
| `buildRuleResultCard` | `${res.passed ? '✅' : '❌'}` | `${iconMarkup(res.passed ? 'check' : 'x')}` |
| evidence tags (2×) | `📍 ${escapeHtml(...)}` | `${iconMarkup('pin')} ${escapeHtml(...)}` |
| batch review button | `` `🔍 Review (${n})` `` / `'✅ Review'` | `` `Review (${n})` `` / `'Review'` |
| batch review title | `❌ ${missed.length} checkpoint…` / `✅ Every checkpoint passed` | `${iconMarkup('x')} ${missed.length} checkpoint…` / `${iconMarkup('check')} Every checkpoint passed` |
| review buttons | `'🗺️ Show on map'` / `'📥 Report'` | `'Show on map'` / `'Download report'` |

`core/toast.js`: replace the ✨ span with an icon element:

```js
import { icon } from './icons.js';
...
    toast.append(icon('info'), text);
```

(remove the `const icon = document.createElement('span'); icon.textContent = ...` lines and rename nothing else).

- [ ] **Step 4: Run all tests**

Run: `python -m pytest -q`
Expected: all pass, including `test_icons.py` (every new icon id exists) and the escaping scan.

- [ ] **Step 5: Commit**

```bash
git add templates static/js static/css/legacy.css tests/test_no_emoji.py
git commit -m "feat(ui): replace every emoji with icons or plain text" -m "Emoji rendered differently on every lab PC and read as unprofessional (#15). Icons come from the Tabler sprite; pass and fail are shown as icon plus text. Each upload box now says which files it accepts, after users dropped a .pkt on the rubric box, whose picker only lists text files." -m "Closes #15" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Browser walkthrough, documentation and pull request

**Files:**
- Modify: `docs/SYSTEM.md`

- [ ] **Step 1: Walk every theme and size in the browser**

Start the `neteval` preview **fresh** (stop any running one first; it does not reload code). For each check: no console errors.

1. **Dark, Default:** Discovery with `tests/fixtures/sample_topology.xml`; Student grading end to end; Instructor rubric and batch with Review → Show on map. Rail switches screens; the context title follows.
2. **Display menu:** opens from the rail; Esc closes and returns focus to the Display button; a click outside closes it; settings survive a reload.
3. **Light:** every screen readable; the map's links, devices and labels visible; no dark leftovers.
4. **High contrast,** in Dark and in Light: focus ring visible on rail items (Tab through).
5. **Follow system:** switch the emulated colour scheme (`resize_window` with `colorScheme`); the page follows without a reload.
6. **Extra large text at 1366×768:** rail labels truncate rather than overlap; no horizontal page scroll; the context bar is still one line.
7. **Lab PC:** with `#nav-mode-teacher` and `#panel-mode-teacher` removed, the rail has two items with no gap.
8. **Emoji:** none visible anywhere.
9. **XSS (#31):** the malicious-device-name and filename checks from PR 1 still render as text, with `window.__xss === 0`.

Take screenshots of Grading in Dark, Light and Light + High contrast for the PR.

- [ ] **Step 2: Update `docs/SYSTEM.md`**

In section 9, Screens, add before the screen list:

```markdown
Navigation is a left rail: **Discovery**, **Instructor** (instructor's machine only) and **Grading**, with **Display** and **AI status** at the bottom. The **Display** menu sets text size (Small to Extra large), theme (Dark, Light, Follow system), contrast (Standard, High) and motion (Follow system, Reduce). Settings are saved per browser and applied before the page draws (`static/js/display-boot.js`). Colours come only from `static/css/tokens.css`, whose contrast is tested in `tests/test_theme_tokens.py`. Icons are Tabler (MIT), vendored as `static/icons/sprite.svg` and rebuilt with `scripts/build_icon_sprite.py`.
```

In section 2's module map, add rows:

```markdown
| `static/js/display-boot.js` | Classic script in `<head>`: applies saved display settings before first paint; `window.NetgraderDisplay`. |
| `static/js/boot-check.js` | Classic script: shows the old-browser notice if the app never started. |
| `static/js/shell/` | The rail's Display menu. |
| `static/js/core/icons.js` | Icons from the vendored Tabler sprite. |
```

and remove the `unsupported.js` row.

- [ ] **Step 3: Full verification**

Run: `python -m pytest -q` → all pass.
Run: `node --test tests/js/*.test.mjs` → all pass.
Run: `python -m validation` → exit 0.

- [ ] **Step 4: Commit**

```bash
git add docs/SYSTEM.md
git commit -m "docs: describe the rail, display settings, tokens and icons" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

The push and PR are done with the user at the finishing step. Title: `UI refresh 2/5: shell and display (rail, themes, text size, icons)`. Body: before and after screenshots in three themes, test and validation results, and `Closes #15`, `Closes #24`.
