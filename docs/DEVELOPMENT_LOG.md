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
