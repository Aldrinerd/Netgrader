# Repository Licensing, Third-Party Notices, and CI Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish formal repository licensing (MIT), comprehensive third-party copyright notices, font licensing, and a multi-platform GitHub Actions CI workflow (Windows and Ubuntu) running test suites and the SOP #3 validation harness.

**Architecture:** Provide legal and compliance files at repository root and in `static/fonts/`, update documentation to link to them, and add `.github/workflows/ci.yml` matrix testing across `windows-latest` and `ubuntu-latest` on Python 3.12 with Node 20. The Linux runner automatically compiles the native Twofish cipher shared library (`libtwofish.so`) prior to testing so that `.pkt` decryption tests run seamlessly.

**Tech Stack:** GitHub Actions, Python 3.12, pytest, PyYAML, SIL Open Font License 1.1, MIT License, BSD 3-Clause License.

## Global Constraints

- Root `LICENSE` must use the standard MIT License text with copyright assigned to `Netgrader Contributors`.
- All bundled third-party assets (`cisco-pka-to-xml`, Twofish native cipher, Tabler Icons, Outfit, and JetBrains Mono) must be documented in `THIRD_PARTY_NOTICES.md`.
- `static/fonts/OFL.txt` must contain the full SIL Open Font License 1.1 text.
- `README.md` must contain a `## License` section linking to `LICENSE` and `THIRD_PARTY_NOTICES.md`.
- CI workflow must trigger on `push` and `pull_request` targeting the `master` branch.
- CI matrix must include `ubuntu-latest` and `windows-latest` running Python 3.12.
- CI must configure Node.js (version 20) via `actions/setup-node@v4` so that `test_frontend_modules.py` and `test_js_units.py` execute without skipping.
- On Linux runners, CI must execute `python cisco-pka-to-xml/build_libtwofish.py` before running tests.
- CI must run `python -m pytest -q -rs`.
- CI must execute `python -m validation --json > validation-report.json` with `shell: bash` across all matrix platforms.
- The validation report artifact must be uploaded with `if: always()` using `actions/upload-artifact@v4`.

---

### Task 1: Add Repository License, Third-Party Notices, Font License, and Documentation (#18)

**Files:**
- Create: `LICENSE`
- Create: `THIRD_PARTY_NOTICES.md`
- Create: `static/fonts/OFL.txt`
- Modify: `README.md:290-305`
- Test: `tests/test_license_and_notices.py`

**Interfaces:**
- Consumes: Existing bundled assets in `cisco-pka-to-xml/`, `static/icons/`, and `static/fonts/`.
- Produces: Legal files (`LICENSE`, `THIRD_PARTY_NOTICES.md`, `static/fonts/OFL.txt`) and documentation links.

- [ ] **Step 1: Write the failing test**

Create `tests/test_license_and_notices.py`:
```python
"""Tests for repository licensing and third-party notices (Issue #18)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_root_license_exists():
    license_file = ROOT / "LICENSE"
    assert license_file.is_file(), "LICENSE file must exist at repo root"
    content = license_file.read_text(encoding="utf-8")
    assert "MIT License" in content
    assert "Copyright (c) 2026 Netgrader Contributors" in content


def test_third_party_notices_exists():
    notices_file = ROOT / "THIRD_PARTY_NOTICES.md"
    assert notices_file.is_file(), "THIRD_PARTY_NOTICES.md must exist at repo root"
    content = notices_file.read_text(encoding="utf-8")
    assert "pka2xml" in content
    assert "Twofish" in content
    assert "Tabler Icons" in content
    assert "Outfit" in content
    assert "JetBrains Mono" in content
    assert "SIL Open Font License" in content
    assert "BSD 3-Clause" in content


def test_font_ofl_notice_exists():
    ofl_file = ROOT / "static" / "fonts" / "OFL.txt"
    assert ofl_file.is_file(), "static/fonts/OFL.txt must exist alongside web fonts"
    content = ofl_file.read_text(encoding="utf-8")
    assert "SIL OPEN FONT LICENSE Version 1.1" in content


def test_readme_references_license():
    readme_file = ROOT / "README.md"
    assert readme_file.is_file(), "README.md must exist"
    content = readme_file.read_text(encoding="utf-8")
    assert "## License" in content
    assert "[MIT License](LICENSE)" in content
    assert "[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_license_and_notices.py -v`  
Expected: FAIL with `AssertionError: LICENSE file must exist at repo root`

- [ ] **Step 3: Create LICENSE**

Create `LICENSE`:
```
MIT License

Copyright (c) 2026 Netgrader Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 4: Create THIRD_PARTY_NOTICES.md**

Create `THIRD_PARTY_NOTICES.md`:
```markdown
# Third-Party Software and Asset Notices

Netgrader bundles and vendors several third-party libraries, fonts, and assets.
This file lists each third-party component, its origin, and its licensing terms.

---

## 1. pka2xml (Packet Tracer Decoder)
- **Path:** `cisco-pka-to-xml/`
- **Origin:** https://github.com/jeamxn/cisco-pka-to-xml
- **Copyright:** (c) 2024 Jean-Maximilien Cadot
- **License:** MIT License

```
MIT License

Copyright (c) 2024 Jean-Maximilien Cadot

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 2. Twofish Native Cipher Implementation
- **Path:** `cisco-pka-to-xml/vendor/twofish/`
- **Origin:** Keybase / Bruce Schneier et al.
- **License:** BSD 3-Clause License

```
Copyright (c) Keybase
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name of Keybase nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

---

## 3. Tabler Icons
- **Path:** `static/icons/sprite.svg`, `static/icons/LICENSE-tabler.txt`
- **Origin:** https://github.com/tabler/tabler-icons
- **Copyright:** (c) 2020-2024 Paweł Kuna
- **License:** MIT License

```
MIT License

Copyright (c) 2020-2024 Paweł Kuna

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 4. Web Fonts: Outfit & JetBrains Mono
- **Path:** `static/fonts/`, `static/fonts/OFL.txt`
- **Outfit Copyright:** Copyright (c) 2021 On Brand Investments Pty Ltd
- **JetBrains Mono Copyright:** Copyright (c) 2020 JetBrains s.r.o.
- **License:** SIL Open Font License 1.1

See `static/fonts/OFL.txt` for full SIL Open Font License 1.1 text.
```

- [ ] **Step 5: Create static/fonts/OFL.txt**

Create `static/fonts/OFL.txt`:
```
SIL OPEN FONT LICENSE Version 1.1 - 26 February 2007

PREAMBLE
The goals of the Open Font License (OFL) are to stimulate worldwide
development of collaborative font projects, to support the font creation
efforts of academic and linguistic communities, and to provide a free and
open framework in which fonts may be shared and improved in partnership
with others.

The OFL allows the licensed fonts to be used, studied, modified and
redistributed freely as long as they are not sold by themselves. The
fonts, including any derivative works, can be bundled, embedded, 
redistributed and/or sold with any software provided that any reserved
names are not used by derivative works. The fonts and derivatives,
however, cannot be released under any other type of license. The
requirement for fonts to remain under this license does not apply
to any document created using the fonts or their derivatives.

DEFINITIONS
"Font Software" refers to the set of files released by the Copyright
Holder(s) under this license and clearly marked as such. This may
include source files, build scripts and documentation.

"Reserved Font Name" refers to any names specified as such after the
copyright statement(s).

"Original Version" refers to the collection of Font Software components as
distributed by the Copyright Holder(s).

"Modified Version" refers to any derivative made by adding to, deleting,
or substituting -- in part or in whole -- any of the components of the
Original Version, by changing formats or by porting the Font Software to a
new environment.

"Author" refers to any designer, engineer, programmer, technical
writer or other person who contributed to the Font Software.

PERMISSION & CONDITIONS
Permission is hereby granted, free of charge, to any person obtaining
a copy of the Font Software, to use, study, copy, merge, embed, modify,
redistribute, and sell modified and unmodified copies of the Font
Software, subject to the following conditions:

1) Neither the Font Software nor any of its individual components,
in Original or Modified Versions, may be sold by itself.

2) Original or Modified Versions of the Font Software may be bundled,
redistributed and/or sold with any software, provided that each copy
contains the above copyright notice and this license. These can be
included either as a stand-alone text file, a human-readable header or
in the appropriate machine-readable metadata fields within text or
binary files as long as those fields can be easily viewed by the user.

3) No Modified Version of the Font Software may use the Reserved Font
Name(s) unless prominent written permission is granted by the corresponding
Copyright Holder. This restriction only applies to the primary font name as
presented to the users.

4) The name(s) of the Copyright Holder(s) or the Author(s) of the Font
Software shall not be used to promote, endorse or advertise any
Modified Version, except to acknowledge the contribution(s) of the
Copyright Holder(s) and the Author(s) or with their explicit written
permission.

5) The Font Software, modified or unmodified, in part or in whole,
must be distributed entirely under this license, and must not be
distributed under any other license. The requirement for fonts to
remain under this license does not apply to any document created
using the Font Software.

TERMINATION
This license becomes null and void if any of the above conditions are
not met.

DISCLAIMER
THE FONT SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT
OF COPYRIGHT, PATENT, TRADEMARK, OR OTHER RIGHT. IN NO EVENT SHALL THE
COPYRIGHT HOLDER BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
INCLUDING ANY GENERAL, SPECIAL, INDIRECT, INCIDENTAL, OR CONSEQUENTIAL
DAMAGES, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE USE OR INABILITY TO USE THE
FONT SOFTWARE OR FROM OTHER DEALINGS IN THE FONT SOFTWARE.
```

- [ ] **Step 6: Update README.md**

Append to `README.md`:
```markdown
## License

This project is licensed under the [MIT License](LICENSE).

Third-party software, fonts, and icons included in this repository are subject to their respective licenses as detailed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
```

- [ ] **Step 7: Run test to verify it passes**

Run: `python -m pytest tests/test_license_and_notices.py -v`  
Expected: PASS (4 passed)

- [ ] **Step 8: Commit**

```bash
git add LICENSE THIRD_PARTY_NOTICES.md static/fonts/OFL.txt README.md tests/test_license_and_notices.py
git commit -m "feat(docs): add repository license, third-party notices, and font licensing"
```

---

### Task 2: GitHub Actions CI Workflow Setup (#27)

**Files:**
- Create: `.github/workflows/ci.yml`
- Test: `tests/test_ci_workflow.py`

**Interfaces:**
- Consumes: Test suite in `tests/`, validation harness in `validation/`, and `requirements-dev.txt`.
- Produces: GitHub Actions CI workflow gating `push` and `pull_request` on `master`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_ci_workflow.py`:
```python
"""Tests for GitHub Actions CI workflow configuration (Issue #27)."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent


def test_ci_workflow_structure():
    workflow_file = ROOT / ".github" / "workflows" / "ci.yml"
    assert workflow_file.is_file(), ".github/workflows/ci.yml must exist"
    
    with open(workflow_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    # Check trigger rules
    triggers = data.get("on") or data.get(True)  # YAML 'on' can parse as boolean True
    assert triggers is not None
    assert "push" in triggers
    assert "pull_request" in triggers
    assert "master" in triggers["push"]["branches"]
    assert "master" in triggers["pull_request"]["branches"]
    
    # Check job definition
    jobs = data.get("jobs", {})
    assert "test" in jobs
    job = jobs["test"]
    
    # Check matrix
    strategy = job.get("strategy", {})
    matrix = strategy.get("matrix", {})
    os_list = matrix.get("os", [])
    assert "ubuntu-latest" in os_list
    assert "windows-latest" in os_list
    py_list = matrix.get("python-version", [])
    assert "3.12" in py_list
    
    # Check defaults
    defaults = job.get("defaults", {})
    assert defaults.get("run", {}).get("shell") == "bash"
    
    # Check steps
    steps = job.get("steps", [])
    step_uses = [s.get("uses", "") for s in steps]
    step_runs = [s.get("run", "") for s in steps]
    
    # Checkout
    assert any("actions/checkout" in u for u in step_uses)
    # Node setup
    assert any("actions/setup-node" in u for u in step_uses)
    # Python setup
    assert any("actions/setup-python" in u for u in step_uses)
    # Twofish compile on Linux
    assert any("build_libtwofish.py" in r for r in step_runs)
    # Pip install
    assert any("pip install -r requirements-dev.txt" in r for r in step_runs)
    # Pytest with -rs
    assert any("pytest -q -rs" in r for r in step_runs)
    # Validation JSON output
    assert any("python -m validation --json" in r and "validation-report.json" in r for r in step_runs)
    # Artifact upload with if: always()
    upload_steps = [s for s in steps if "actions/upload-artifact" in s.get("uses", "")]
    assert len(upload_steps) == 1
    assert upload_steps[0].get("if") == "always()"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ci_workflow.py -v`  
Expected: FAIL with `AssertionError: .github/workflows/ci.yml must exist`

- [ ] **Step 3: Create .github/workflows/ci.yml**

Create `.github/workflows/ci.yml`:
```yaml
name: CI

on:
  push:
    branches: [ master ]
  pull_request:
    branches: [ master ]

permissions:
  contents: read

jobs:
  test:
    name: Test (${{ matrix.os }}, Py ${{ matrix.python-version }})
    runs-on: ${{ matrix.os }}
    defaults:
      run:
        shell: bash
    strategy:
      fail-fast: false
      matrix:
        os: [ ubuntu-latest, windows-latest ]
        python-version: [ "3.12" ]

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Node.js 20
        uses: actions/setup-node@v4
        with:
          node-version: 20

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'

      - name: Build Twofish native cipher library (Linux)
        if: runner.os == 'Linux'
        run: python cisco-pka-to-xml/build_libtwofish.py

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt

      - name: Run test suite
        run: python -m pytest -q -rs

      - name: Run SOP #3 grading validation harness
        run: python -m validation --json > validation-report.json

      - name: Upload validation report artifact
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: validation-report-${{ matrix.os }}
          path: validation-report.json
          if-no-files-found: warn
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ci_workflow.py -v`  
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ci.yml tests/test_ci_workflow.py
git commit -m "feat(ci): add GitHub Actions workflow for pytest and validation harness"
```

---

### Task 3: Local Simulation and Pipeline Gate

**Files:**
- Execute local simulation of steps defined in `.github/workflows/ci.yml`.

- [ ] **Step 1: Run full pytest suite with -rs**

Run: `python -m pytest -q -rs`  
Expected: All tests pass, any skipped tests enumerated with reasons.

- [ ] **Step 2: Run validation harness with bash redirect**

Run: `bash -c "python -m validation --json > validation-report.json"`  
Expected: Exits with returncode 0.

- [ ] **Step 3: Validate generated JSON artifact**

Run: `python -c "import json, sys; d = json.load(open('validation-report.json')); sys.exit(0 if d['reference_clean'] and all(c['correct'] for c in d['cases']) else 1)"`  
Expected: Returncode 0.

- [ ] **Step 4: Clean up validation report artifact**

Run: `rm validation-report.json`

- [ ] **Step 5: Verify clean git status and commit history**

Run: `git status`  
Expected: Clean working tree on branch `infra/ci-and-license`.
