# Development Log — Network Configuration Evaluation & Topology Discovery Tool

## Session: 2026-08-31

### Step 1: Research Context & Requirements Exploration
- Reviewed research paper and technical decision documents:
  - `decisions-2026-08-23.md`: Locked technical choices (Python 3 + FastAPI, Jinja2 + Vanilla CSS/JS, stateless architecture, `.txt` bundle input).
  - `technical-answers.md`: Technical defense justifications answering R4-1, R4-2, and R4-3.
  - `topology-discovery-signals.md`: 24 Tier A signals (logical/L3) and 12 Tier B signals (bundle/L2), plus Noisy-OR confidence fusion math and conflict rules.
- Established immediate priority for tomorrow's presentation: Standalone Multi-Signal Topology Discovery & Conflict Inspector Web App.

### Step 2: Architecture & Design Specification
- Outlined 5-stage architecture:
  1. Section Tokenizer & Sanitizer (cleans terminal noise, prompts, `--More--`).
  2. Core Cisco Output Parsers (Pydantic models for interfaces, CDP, routing, VLANs, MACs).
  3. Multi-Signal Fusion Engine (Noisy-OR probabilistic graph builder).
  4. Relational Cross-Device Conflict Detector (Subnet mismatch, down links, duplicate IPs, VLAN mismatches with line-number citations).
  5. Interactive Web UI with 1-Click Demo Presets for seamless presentation defense.
- Created design document: `docs/superpowers/specs/2026-08-31-network-eval-topology-tool-design.md`.

---
*(Log will be updated after each implementation step)*

### Task 1: Environment Setup & Pydantic Data Models
- Installed fastapi, uvicorn, pydantic, pytest, python-multipart.
- Created domain models in src/models.py (InterfaceData, ParsedDevice, DiscoveredLink, ContributingSignal, ConflictIssue, TopologyResult).
- Verified with 3 automated unit tests in tests/test_models.py (all passing).

### Task 2: Section Tokenizer & Terminal Sanitizer
- Built regex command recognizer for Cisco show commands (show running-config, cdp neighbors, ip int brief, ip route, vlan brief, int trunk, mac address-table).
- Implemented terminal noise sanitizer (stripping --More--, ANSI escapes, carriage returns).
- Verified with 3 automated unit tests in tests/test_sanitizer.py (all passing).

### Task 3: Cisco Command Parsers
- Created comprehensive parsers in src/parsers.py (running-config, cdp neighbors, ip int brief, ip route, vlan brief, int trunk, mac address-table).
- Added canonical device and interface name resolvers.
- Verified with 3 automated unit tests in tests/test_parsers.py (all 9 total tests passing).

### Task 4: Multi-Signal Fusion & Topology Graph Inference Engine
- Built Noisy-OR mathematical fusion engine in src/fusion_engine.py.
- Combined Layer 2 (CDP, Trunk, MAC) and Layer 3 (Subnets, Routes, Descriptions) signals into edge confidence ratings.
- Verified with 3 automated unit tests in tests/test_fusion_engine.py (all 12 total tests passing).

### Task 5: Relational Cross-Device Conflict & Anomaly Detector
- Implemented cross-device error detectors (subnet mismatch across physical links, administratively down interfaces, duplicate IPs, trunk native VLAN mismatch).
- Generates structured citations with exact file and line numbers.
- Verified with 3 automated unit tests in tests/test_conflict_detector.py (all 15 total tests passing).

### Task 6: Built-in Demo Scenarios & Fixtures Generator
- Implemented preset catalog in src/presets.py with 3 presentation showcase scenarios (Clean OSPF Ring, Subnet Mismatch & Cabling Down Error, VLAN Trunk Native Mismatch).
- Verified with 4 automated unit tests in tests/test_presets.py (all 19 total tests passing).

### Task 7: FastAPI Web Application & Interactive Visualizer
- Built FastAPI application in src/app.py with endpoints (/, /api/presets, /api/presets/{id}, /api/analyze).
- Implemented dynamic Jinja2 template and responsive dark mode CSS (templates/index.html, static/css/style.css).
- Implemented client-side interactive SVG topology renderer with node dragging, confidence badges, and diagnostic evidence drawer in static/js/app.js.
- Verified with 4 automated unit tests in tests/test_app.py (all 23 total tests passing).

### Task 8: End-to-End Verification & Presentation Readiness
- Created e2e integration tests in tests/test_e2e.py.
- Executed full test suite: 25/25 tests passing (100%).
- Verified live FastAPI server execution at http://127.0.0.1:8000/ with automated HTTP client checks.
- Completed Phase 1 standalone topology discovery and diagnostic tool!

---

## Session: 2026-09-08 — Packet Tracer Ingest & Instructor Policies

### Direct `.pkt` / `.pka` / `.xml` Upload
- Vendored the `cisco-pka-to-xml` decoder (`pka2xml`, MIT) to decrypt Packet Tracer files in memory.
- Added `src/pkt_parser.py`: extracts ground-truth cabling, cable types, canvas coordinates, and PC/laptop profiles.
- Extended topology models with `x_coord`, `y_coord`, and `cable_type`; added physical cabling error detection.
- This largely supersedes `scripts/pt_collector.py`, the keystroke-scraping CLI collector.

### Instructor Policy Toggles & Dynamic Relational Grading
- Added the `EvaluationPolicies` model with nine grading policies.
- Taught the parsers to read the security baseline (`enable secret`, `service password-encryption`, `line vty`), OSPF router processes, and default gateways.
- Added policy-aware rule generation and the dual-format `instructions.txt` writer.
- Implemented deterministic relational subnet evaluation using Python `ipaddress` arithmetic.
- Built the Instructor Policy Control Center UI.

---

## Session: 2026-09-20 — Lab Deployment Hardening, Scoring Audit & Batch Grading

### Deployment on School Computers
- Added `start_server.py`, a double-clickable launcher. It is deliberately **not** a `.bat` file: Group Policy that restricts `cmd.exe` commonly blocks batch scripts too, and the launcher runs through `python.exe` instead.
- The launcher checks the Python version, installs missing packages with `pip --user` (no administrator rights), verifies the Packet Tracer decoder loads, selects a free port, prints the local and LAN URLs, and opens a browser. `--check` runs diagnostics only.
- **Fixed a Windows port-detection bug:** the first implementation set `SO_REUSEADDR` while probing, which on Windows permits binding a port another process is actively serving on. The probe reported occupied ports as free. It now connects first and binds without that option.
- **Removed the Google Fonts CDN dependency.** All fonts are served from `static/fonts/`, so the offline claim in the technical defence documents is now true rather than aspirational.
- **Replaced hard-coded asset versions with automatic cache-busting** derived from static file modification times. The template previously pinned `?v=3.2`, so any update to the CSS or JavaScript would never reach a browser that had already cached it.
- Split `requirements.txt` into core runtime, `requirements-dev.txt`, and `requirements-collector.txt` so lab computers no longer install the GUI-automation stack used only by the CLI collector.
- Added `.gitignore` and stopped tracking compiled `.pyc` files.

### Scoring Algorithm Audit
Three defects were found and fixed:

1. **Negative rule weights.** Point normalisation gave all rounding error to the last rule, which could make its weight negative on a large topology with a low point total — so *passing* that checkpoint lowered a student's percentage. Replaced with largest-remainder apportionment in tenths of a point. Invariants now hold across every tested configuration: weights are never negative, they sum exactly to the target, and all are strictly positive whenever the target can afford it.

2. **Correct work penalised as a duplicate subnet.** Subnet-uniqueness was keyed per interface, so a PC and its own default gateway — which are required to share a subnet — were reported as a collision. Uniqueness is now keyed by broadcast domain, computed from the cabling graph with layer 2 devices bridging their own ports. A genuine subnet reused across two separate domains is still caught.

3. **Two policies had no effect at all.** `verify_default_gateways` and `allow_flexible_process_ids` were implemented in the evaluator but no rule of the matching category was ever generated, so the OSPF branch was dead code and gateways were never checked under strict addressing. Both rule types are now generated, and OSPF is graded for the first time.

- Added `tests/test_policy_toggles.py`, which grades one mutated submission under the lenient and strict setting of each policy and asserts the lenient run scores higher. All nine policies now demonstrably change grading; previously seven did.

### Batch Grading & Gradebook Export
- Added `POST /api/evaluate/batch`: grades a whole class against one rubric in a single pass and returns per-student results plus a gradebook-ready CSV.
- A submission that fails to parse is recorded as an error row rather than aborting the run, so one corrupt upload cannot cost an instructor the entire batch.
- Added the Batch Grading panel to the Instructor Studio, with class summary statistics and a CSV download.
- This closes the loop on the Chapter I problem statement — *"manual checking for large batches"* — which until now had no corresponding feature, since results were one student at a time and on screen only.

### Demo Scenarios Removed
- Deleted `src/presets.py`, the `/api/presets` endpoints, and the Showcase Demo Scenarios panel.
- The three configuration bundles were preserved as `tests/fixtures.py`, where they remain realistic multi-device grading fixtures for the test suite.

### Verification
- Full suite: **86 tests passing**.
- Batch grading and the launcher were verified in a real browser against a live server.

## Session: 2026-09-22 — Instructor-Only Access & Per-Student Review

### Instructor Studio restricted to the serving computer
- Before this change, anyone on the lab network could open Instructor Studio and call its endpoints: generate a rubric from a reference file, batch-grade the class, or request the class briefing. Hiding the tab alone would not have fixed this, because the API was open too.
- Added `is_instructor()` / `require_instructor` to `src/app.py`. A request counts as the instructor's when it comes from a loopback address, or when its client address equals the server's own socket address (the instructor opening the LAN URL on their own PC). No accounts or passwords, which fits the one-PC-serves-the-lab deployment.
- `/api/criteria/generate`, `/api/evaluate/batch` and `/api/class/briefing` now return `403` to other machines. `/api/evaluate`, `/api/criteria/parse` and `/api/analyze` remain open, because students need them.
- `templates/index.html` renders the Instructor Studio tab and panel only when `is_instructor` is true, so lab computers never receive the markup.
- Known trade-off: the instructor cannot use Instructor Studio from a second machine. If that is needed, add a passcode printed by `start_server.py` at startup, exchanged for a signed cookie.

### Per-student review in Batch Grading
- Previously, the batch table showed a score and a count of failed checkpoints. To see *which* checkpoints a student missed, the instructor had to re-grade that student alone in Student Grading.
- `/api/evaluate/batch` now includes each student's full `EvaluationReport` in their row (`report`; `null` for an unparseable submission).
- Added a **Review** button per row (labelled with the missed-checkpoint count) that opens the student's mistakes under the row: missed checkpoints grouped by device, with feedback, *Found:* value and fix guidance, plus their weakest areas ranked by points lost.
- Inside the review: **Show on map** draws the student's topology with the devices they got wrong ringed in red; **Show passed too** toggles the full checklist; **Report** downloads that student's text report. **Review all** / **Collapse all** act on the whole class.
- The checkpoint card and text report are now shared helpers (`buildRuleResultCard`, `buildReportText`) used by both Student Grading and the batch review, so the two views cannot drift apart.
- Checkpoint descriptions, feedback and *Found:* values are now HTML-escaped. They can contain hostnames and config text from a student's file, and that text now renders on the instructor's page.
- The batch table uses a container query to drop the Status column when the left panel is narrow. The review panel is kept to the table's visible width.

### Verification
- Added `tests/test_instructor_access.py` (9 tests). It checks that the tab is absent from a lab PC's page, that the three endpoints return `403` to a lab PC, that students can still grade their own work, that the LAN-address and IPv4-mapped loopback cases work, and that batch rows carry a full report.
- Existing suites that call instructor endpoints now use a `TestClient` whose client address is `127.0.0.1`.
- Full suite: **212 tests passing**.
- Verified in a real browser against a live server: batch-graded two submissions, opened each review, used Review all, and confirmed Show on map rings the faulty routers. Also confirmed the instructor is still recognised when opening the LAN address on the serving PC.

## Session: 2026-09-22 (continued) — Local AI Audit, Status Indicator & Follow-up Chat

### Audit: is the local AI actually used?
- `src/llm.py` makes real HTTP calls to Ollama (`/api/tags` to probe, `/api/generate` to write). Prompts are built live from each report, and every response carries `source: "model"` or `"template"`.
- Checked against a stand-in Ollama server: grading made **0** model calls, while the student summary and class briefing each made one, with prompts containing that report's concepts and counts. With the server gone, both fell back to template text, labelled as such.
- **On the development machine, Ollama was not installed.** Every paragraph shown so far had been template text. The UI gave no up-front sign of this.

### Header AI indicator
- New button in the top bar, driven by `/api/llm/status`. It shows **AI: <model>** (purple), **AI: not installed** / **AI: model missing** (amber), or **AI: off**. The reason appears on hover, and clicking re-checks. It refreshes every 60 seconds.

### Follow-up chat
- Added `llm.chat()` (Ollama `/api/chat`), with the same contract as `generate()`: bounded by the timeout, never raises, returns `None` on failure.
- Added `narrative.report_chat` / `class_chat` and the endpoints `/api/chat/report` (open to students) and `/api/chat/class` (instructor-only).
- One reusable chatbox is used under the student report and under the class briefing. It has suggested questions, multi-turn history, Enter to send, and a pending indicator.
- **No template fallback for chat.** Without a model, the endpoint returns `503` with the reason and the chatbox disables itself with a note. Presenting canned text as an answer would be the "premade AI" this audit was checking for.
- Student chat context includes each missed checkpoint's *Found:* value, which is more than the summary paragraphs send. This is documented in SYSTEM.md §7. The score is never sent.

### Fixed: model calls froze the whole server
- `/api/report/narrative`, `/api/class/briefing` and `/api/llm/status` were `async def` while making blocking `urllib` calls. Each call stalled the event loop, so every student's request waited up to 45 seconds for one model answer. All model-calling endpoints are now plain `def`, which FastAPI runs in its thread pool.

### Verification
- Added `tests/test_chat.py` (14 tests). It covers: `llm.chat` hitting a real HTTP stand-in; history sanitising; an honest `503` with no model or a silent one; replies grounded in the report's findings; no score in the model's input; history reaching the model; class chat being instructor-only and aggregate-only; and a guard that model-calling endpoints are not coroutines.
- Full suite: **226 tests passing**.
- Verified in a real browser: with no model, the header reads *AI: not installed* and the chat is disabled with the reason. With a stand-in model on port 11434, the header switched to *AI: llama3.2:3b*, and both chats answered over two turns with history intact. When the stand-in was stopped, the chat disabled itself on the next status poll. A failed answer shows the error and puts the question back in the box for a retry.

## Session: 2026-09-22 (continued) — Class Chat With Names, Sortable Batch Table

### Why
- Once Ollama was installed, the instructor asked the class chat "who got the lowest grade". It correctly replied that it had no per-student data: the class chat had only been given anonymous totals. The group chose to (a) show the answer on the page and (b) give the instructor's class chat the full results table.
- **Convention recorded:** each submission file is named after the student (`Dela Cruz, Juan.pkt`), and the filename stem is the only source of student identity.

### On the page
- The **Highest** and **Lowest** stat cards now show who scored it, with every name listed on a tie.
- The batch table sorts by Student, Score, % or Grade; clicking again reverses. Scores sort lowest-first. Open review rows move with their student, and ungradeable files stay at the bottom.

### Class chat sees the results table
- `/api/chat/class` now takes `students` (`ClassChatStudent`: name, status, percentage, grade, score, missed count, missed concepts) instead of anonymous category lists. It is still instructor-only.
- `narrative._class_context` computes the ranking, lowest and highest (with ties), class average, and students per concept, so the 3B model reads answers rather than comparing numbers. Names are cleaned to one short printable line, and a test shows a crafted filename cannot forge a row.
- The class briefing and student chat remain name-free, which a test asserts. SYSTEM.md §7 now states that names reach the local model only in the instructor chat.

### Measured and fixed: follow-up questions misread the findings
- In the browser, after "who got the lowest grade", the follow-up "which students struggled with OSPF?" got "Neither student… missed any concepts related to OSPF". Both had.
- The context was correct. The model was misreading it. Across 20 two-turn runs on llama3.2:3b, findings in the system prompt were misread 7–9 times at temperature 0.3 and 0.1; findings placed next to the latest question were read correctly 20/20 at both.
- `narrative._chat` now attaches the findings to the latest user turn on every request. Through the shipped code path: class chat 20/20, student chat 10/10 on follow-up turns.
- Remaining limitation: open-ended answers can still be loosely worded (for example "all three students struggled…" before correctly excluding the student with 100%). The on-page table and cards are the reliable source for facts.

### Verification
- `tests/test_chat.py` now has 19 tests. The new ones cover ranking and tie text, the name-injection guard, the missing-table `400`, briefing and student-chat anonymity, and findings being attached only to the latest turn.
- Full suite: **231 tests passing**.
- Verified in the browser against the real local model with three submissions (two tied at 16.5%): the stat cards named both, sorting worked, and the chat answered "who got the lowest grade" → both tied, then "which students struggled with OSPF?" → both, correctly.
