# Design Spec: UI Refresh and Linked Report View

**Date:** 2026-10-01
**Topic:** Full visual refresh of the web UI, a linked list-and-map layout
used across every screen, display settings, accessibility, responsive tiers,
and keeping results across a refresh
**Issues:** #15, #23, #24, #25, #29, #30
**Status:** Awaiting review

---

## 1. Why

The audit (#16) found the interface is the weakest part of the tool for its
actual audience:

- 52 emoji act as icons and status markers (#15). They render differently on
  every machine and read as unprofessional in an institutional tool.
- Every checkpoint prints its feedback, found value and full guidance inline
  (#23). On a real lab the missed items are buried among the passed ones.
- 93 font sizes, mostly fixed pixels, many at 9.5 to 11 px (#24). Unreadable on
  a projector, and they ignore the browser's text-size setting.
- One `aria-` attribute in the whole page, no focus styles, status shown by
  colour and emoji (#25).
- A refresh loses the student's report (#29).
- One breakpoint, at 520 px (#30). A 1024x768 classroom projector gets a
  squashed layout.

The UI is also one 2,000-line `app.js` inside a single `DOMContentLoaded`
handler and one 1,800-line `style.css`. Every screen shares variables, which
is how the unescaped sinks in #31 accumulated.

### Audience and context

Instructors and students at a Cisco Networking Academy lab, on lab PCs,
1366x768 laptops and classroom projectors (often 1024x768). Offline. Many
students are first-time users of the tool.

### Success criteria

- A student sees every deduction, and where in their network it is, without
  scrolling past passed items.
- Every screen works by keyboard alone and reads correctly in NVDA.
- No layout breaks at 1024x768 or at the largest text size.
- No emoji anywhere in the UI.
- `python -m validation` still reports 100%: no score changes.

---

## 2. Decisions

| Question | Decision |
|---|---|
| Scope of visual change | Full refresh |
| Visual direction | **Console**: refined dark, one green accent, flat surfaces, no glow. Light and high-contrast themes provided. |
| Layout | **Linked list and map** on every screen. Below 1024 px it falls back to report-first with the map as a tab. |
| Instructor per-student review | Opens the same linked view as the student, with Previous / Next |
| Build approach | Native ES modules and CSS custom properties. No framework, no bundler. |
| Templating | Keep Jinja2 as a thin shell: layout, partials, import map, role check |

Mockups were reviewed in the brainstorming companion and are not stored in
the repository.

---

## 3. Stack

Nothing new is installed on lab PCs. There is still no build step.

| Layer | Before | After |
|---|---|---|
| Server | Python 3.12, FastAPI, Uvicorn, Pydantic | Unchanged |
| Page | One Jinja2 template | Jinja2 base layout plus one partial per screen |
| JavaScript | One `app.js`, plain JS | Plain JS as native ES modules, one file per feature |
| CSS | One `style.css` | `tokens.css`, `base.css`, `components/*.css`, `layouts/*.css` |
| Icons | Emoji | Tabler Icons (MIT), vendored as `static/icons/sprite.svg` |
| Fonts | Outfit, JetBrains Mono, self-hosted | Unchanged |
| Topology map | SVG renderer inside `app.js` | Same renderer in its own module, with a highlight API |
| Tests | pytest | pytest, plus Playwright and axe-core (developer machines only) |

### 3.1 Why Jinja2 stays

1. **Module cache-busting.** Modules import each other from inside JavaScript,
   where a template variable cannot reach. Jinja renders an import map so every
   import carries the asset version:

   ```html
   <script type="importmap">
   { "imports": { "netgrader/": "/static/js/{{ asset_version }}/" } }
   </script>
   ```

   A route serves `/static/js/<version>/<path>` from `static/js/<path>`, so the
   version is part of the URL and a deployed fix reaches every browser.
2. **Instructor markup is never sent to lab PCs.** `{% if is_instructor %}`
   stays. `require_instructor` remains the real guard.
3. **Login pages later (#9)** are simplest server-rendered.

Rule: Jinja decides which page you get. JavaScript decides what it does. No
data rendering or business logic in templates.

### 3.2 Module layout

```
static/js/
  main.js                  entry: boots the shell, routes to a screen
  core/
    dom.js                 el(), text(), escapeHtml(); the only way to build markup
    api.js                 fetch wrappers, error extraction
    store.js               sessionStorage persistence, URL hash state
    announce.js            single polite live region
    icons.js               icon(name) -> <svg><use></svg>
  shell/
    rail.js                navigation rail
    context-bar.js         per-screen title, file chips, primary action
    display-menu.js        text size, theme, contrast, motion
  map/
    topology.js            SVG renderer (moved from app.js)
    highlight.js           highlight(device, link), badges, dimming
    map-table.js           "Devices and links" text alternative
  report/
    linked-report.js       list + map + detail; used by Grading and Review
    loss-bar.js            points lost by topic
    checkpoint-list.js     listbox of missed checkpoints, grouping toggle
    checkpoint-detail.js   expected / found / why / check with / ask
  screens/
    discovery.js
    grading.js
    studio.js
    batch.js
  chat/
    chat.js                existing follow-up chat, moved
static/js/display-boot.js  classic script in <head>; applies settings before paint
```

`core/dom.js` is the only module allowed to create markup from strings. Every
other module builds nodes with `el()` and sets text with `textContent`. This
makes the #31 fix structural rather than a convention.

---

## 4. Shell and navigation

### 4.1 Rail

- About 72 px wide, on the left. Each destination is an icon with a text label
  under it.
- Top: **Discovery**, **Instructor** (rendered only when `is_instructor`),
  **Grading**.
- Bottom: **Display** and **AI status** (replaces the header pill).
- Brand: a small `NG` mark and "Netgrader" at the top.
- Removed: the "FCPC CAPSTONE" badge, the long title, the pulsing
  "Inference Engine: Active" dot.

### 4.2 Context bar

About 48 px across the top of each screen. Holds what is being viewed and the
one primary action, for example lab title, file chips, score, **Grade again**.
Reset View moves into the map toolbar beside zoom and fit.

### 4.3 Screens

All screens use the linked list-and-map pattern:

| Screen | List column | Map | Detail |
|---|---|---|---|
| Grading | Missed checkpoints | Student topology | Selected checkpoint |
| Instructor, Batch | Class table, then the selected student's linked view with Previous / Next | That student's topology | Selected checkpoint |
| Instructor, Studio | Rubric settings and policies | Reference topology | Generated rubric summary |
| Discovery | Detected conflicts | Uploaded topology | Selected conflict with citations |

Before grading, the Grading list column holds two upload steps (rubric,
attempt) as drop zones with real file buttons. After grading they collapse to
file chips in the context bar.

---

## 5. Linked report view

One component, `report/linked-report.js`, used by Grading and by the
instructor's batch Review.

### 5.1 List column

- **Score header:** percentage, `82.0 / 100`, lab title.
- **Points lost by topic:** segmented bar and legend from the report's existing
  `study_topics`. Has an accessible name listing each topic and points.
- **Missed checkpoints**, grouped by device (default) or by topic. Each row:
  device and interface in monospace, what was checked, deduction, and a (?)
  button.
- **Passed checkpoints:** a collapsed disclosure, "24 checkpoints passed".

### 5.2 Selection

Exactly one checkpoint is selected. It is set by clicking a row or its (?),
by arrow keys in the list, or by activating a device on the map (which selects
that device's first missed checkpoint and filters the list to the device).
Selection is mirrored to the URL hash.

### 5.3 Map and detail

- Devices with any missed checkpoint show a count badge.
- The selected checkpoint's device is ringed. For link-scoped checks
  (`cabling`, `link_agreement`, `relational_subnet` with a peer) the link and
  both endpoints are highlighted. Other elements dim.
- Detail panel under the map: **Expected**, **Found**, **Points lost**,
  **Why it matters** (existing guidance), **Check with** (command chips), and
  **Ask about this** (opens the existing chat scoped to this checkpoint;
  hidden when no model is available).

### 5.4 Edge cases

| Case | Behaviour |
|---|---|
| Device missing from the attempt | Row says so; detail reads "R3 was not found in your file"; no map highlight |
| All checkpoints passed | "All 27 checkpoints passed" and the map |
| No AI model | "Ask about this" hidden; everything else unchanged |
| Checkpoint with no device on the map | Detail shown, map unchanged |

### 5.5 Backend additions

Additive fields on `RuleResult`. They report what the evaluator already
knows and do not affect scoring.

| Field | Type | Source |
|---|---|---|
| `expected_text` | `str \| None` | Human-readable form of the rule's `expected_value` |
| `peer_device` | `str \| None` | Other endpoint for link-scoped rules, after device mapping |
| `peer_interface` | `str \| None` | Other endpoint's interface |
| `verify_commands` | `list[str]` | The `show` commands now embedded in `feedback.py` sentences, moved to a per-category list |

`feedback.py` keeps its sentences; the commands are additionally exposed as
data. Guidance text no longer needs to be parsed for commands.

---

## 6. Display settings, themes and icons

### 6.1 Display menu

| Setting | Options | Default |
|---|---|---|
| Text size | Small, Default, Large, Extra large | Default |
| Theme | Dark, Light, Follow system | Dark |
| Contrast | Standard, High | Standard |
| Motion | Follow system, Reduce | Follow system |

- Stored in `localStorage` per browser. These are preferences, not data.
- Applied by `display-boot.js`, a classic script in `<head>`, before first
  paint. External rather than inline, so a strict Content-Security-Policy
  (#26) can forbid inline script.
- The Light option is labelled as easier to read on projectors.

### 6.2 Tokens and type

- Every colour is a semantic custom property in `tokens.css`: `--surface`,
  `--surface-raised`, `--text`, `--text-muted`, `--line`, `--accent`,
  `--status-bad`, `--status-warn`, `--focus-ring`, and so on, defined for
  Dark, Light and High contrast. Component CSS uses tokens only.
- All sizes in `rem`. Text size changes the root font size. Body text is
  15 px at Default; nothing renders below 12 px equivalent.
- Fonts: Outfit for interface text, JetBrains Mono for device names,
  interfaces, addresses, commands and scores.
- High contrast: text at least 7:1, stronger borders, 3 px focus ring,
  heavier status icons.
- The map reads the same tokens.

### 6.3 Icons

- Tabler Icons, about 25 glyphs, in `static/icons/sprite.svg`, used as
  `<svg><use href="/static/icons/sprite.svg#name">`.
- Decorative icons carry `aria-hidden="true"`. Meaningful icons have a text
  label.
- Pass and fail are always icon plus text plus colour.
- All emoji are removed from templates, button labels, toasts and chips.

---

## 7. Accessibility

### 7.1 Keyboard

- A "Skip to results" link is the first focusable element.
- The missed-checkpoint list is a listbox: arrow keys move the selection,
  Enter moves focus to the detail panel, Esc returns to the list.
- Map devices are focusable in order (routers, switches, hosts). Enter selects
  a device. `+`, `-` zoom and `0` fits.
- (?) is a `<button>` with `aria-expanded`. It opens on click, tap, Enter or
  Space; never on hover alone. In the narrow fallback it opens a popover that
  closes on Esc, keeps focus inside, and is not clipped by the viewport.
- `:focus-visible` ring on every interactive element.

### 7.2 Screen readers

- Landmarks: `nav` (rail), region "Missed checkpoints", region
  "Checkpoint detail".
- One polite live region announces "Grading", the result
  ("Graded: 82 percent, 3 checkpoints missed") and errors.
- The map has a text alternative: a "Devices and links" table in the map
  toolbar.

### 7.3 Visual

- Text contrast at least 4.5:1 (Standard) and 7:1 (High contrast), both themes.
- Targets at least 32 px on desktop, 44 px in touch and narrow layouts.
- Motion limited to short fades and highlight transitions; none under Reduce.

---

## 8. Responsive layout and persistence

### 8.1 Tiers

| Width | Layout |
|---|---|
| 1280 px and up | Linked: list column about 340 px, map, detail under the map |
| 1024 to 1279 px | Linked: list about 300 px, detail as a drawer over the map |
| 768 to 1023 px | Fallback: report first, map as a tab, detail as a side inspector |
| Below 768 px | One column; rail becomes a top bar; detail as a bottom sheet |

- No horizontal page scroll at any width.
- Wide tables scroll inside their container with the student column pinned.
- The map fits to view on load and on container resize.
- Larger text sizes may move a screen to the next tier's layout. That is
  intended and tested.

### 8.2 Keeping results (#29)

- The last report, selected checkpoint and current screen are saved in
  `sessionStorage` and restored on load. Cleared when the browser closes.
- Screen and selection are also in the URL hash, so Back and Forward work.
- Batch results are saved the same way. If storage quota is exceeded, the
  summary table is kept and the screen says "Re-run the batch to restore
  per-student details".
- A leave-page warning appears only while grading is in progress.
- **Clear** in the context bar removes the stored report. A new upload or
  Grade again replaces it.

---

## 9. Testing

### 9.1 Static (pytest, no browser)

- The #31 escaping test, extended to every module; only `core/dom.js` may
  assign `innerHTML`.
- No emoji code points in `templates/` or `static/js/`.
- No raw colour values in `static/css/components/` or `layouts/`.
- Every icon referenced in markup or JS exists in the sprite.

### 9.2 Backend

- Tests for `expected_text`, `peer_device`, `peer_interface`,
  `verify_commands` across categories.
- `python -m validation` unchanged at 100%.

### 9.3 Browser (Playwright, developer machines only)

- axe-core on every screen in Dark, Light and High contrast: zero serious or
  critical violations.
- Keyboard-only flow through the linked report, asserting the map highlight.
- Viewports 1440x900, 1024x768, 800x1000, 375x812: no horizontal scroll,
  correct tier.
- Refresh restores report and selection; Clear removes them.
- The #31 XSS fixture renders as text in every new component.

`pytest-playwright` is added to `requirements-dev.txt`. Lab PCs are
unaffected. CI (#27) can run the same suite.

### 9.4 Manual

A keyboard-only and NVDA checklist in `docs/accessibility-checklist.md`,
filled in for each screen, as evidence for the paper.

---

## 10. Delivery

Five pull requests. Each leaves the application working.

| PR | Content | Closes |
|---|---|---|
| 1. Foundation | Split `app.js` into modules and `style.css` into token, base, component and layout files; Jinja partials; import map and versioned static route; icon sprite. No visible change; all existing tests pass. | |
| 2. Shell and display | Rail, context bar, Display menu, three themes, text sizes, emoji removal | #15, #24 |
| 3. Linked report | Grading screen, backend fields, persistence | #23, #29 |
| 4. Instructor and Discovery | Batch Review with Previous / Next; Studio and Discovery in the linked pattern | |
| 5. Hardening | Responsive tiers, keyboard and screen-reader polish, full Playwright and axe suite | #25, #30 |

---

## 11. Out of scope

- #14 Packet Tracer notes and shapes on the map (fits the new map module later)
- #22 Printable lab handout
- #9, #10 Accounts and stored submissions
- Any change to scoring beyond the additive report fields in 5.5
