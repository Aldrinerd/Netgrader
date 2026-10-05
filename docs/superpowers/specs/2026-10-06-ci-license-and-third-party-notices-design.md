# Design Spec: Repository Licensing, Third-Party Notices, and CI Workflow

**Date:** 2026-10-06  
**Topic:** Repository licensing, third-party intellectual property compliance, and automated GitHub Actions CI pipeline  
**Issues:** #18, #27 (PR A of Repository & CI Essentials)  
**Status:** Approved design, ready for implementation  

---

## 1. Why

The audit (#16) identified that the repository lacks automated testing on push and explicit intellectual property licensing:

1. **No repository license (#18):** As a public repository without a `LICENSE` file, all rights are reserved by default. Neither the college, instructors, students, nor outside contributors have explicit legal permission to run, modify, or redistribute the code.
2. **Third-party notices omitted (#18):** The project vendors third-party components that require copyright attribution to accompany distributions:
   - `cisco-pka-to-xml` (MIT license, upstream `jeamxn/cisco-pka-to-xml`)
   - Native Twofish cipher (`cisco-pka-to-xml/vendor/twofish/`, BSD-3-Clause)
   - Tabler Icons (`static/icons/sprite.svg`, MIT license)
   - Self-hosted web fonts Outfit and JetBrains Mono (`static/fonts/`, SIL Open Font License 1.1)
3. **No Continuous Integration (#27):** There is no `.github/workflows/` directory. Even though the codebase has 385 tests and an SOP #3 grading-engine validation harness, regressions can currently be introduced or merged unnoticed without an automated gate.
4. **Fresh checkout and cross-platform verification:** Upstream `.pkt` decryption requires a native Twofish shared library. While `pka2xml/libtwofish.dll` is committed for Windows lab PCs, Linux/macOS runners must compile `libtwofish.so` via `cisco-pka-to-xml/build_libtwofish.py` before running tests. CI must verify this flow automatically.

### Success Criteria
- Root `LICENSE` file with MIT license text.
- Comprehensive `THIRD_PARTY_NOTICES.md` documenting all bundled third-party assets and licenses.
- Font license file `static/fonts/OFL.txt` committed alongside the font binaries.
- `README.md` updated with a clear license section referencing `LICENSE` and `THIRD_PARTY_NOTICES.md`.
- Automated GitHub Actions workflow (`.github/workflows/ci.yml`) running on every push to `master` and every pull request targeting `master`.
- Matrix execution on both `windows-latest` (lab environment) and `ubuntu-latest` with Python 3.12.
- Node.js setup in CI so frontend module and unit tests (`test_frontend_modules.py`, `test_js_units.py`) execute without skipping.
- Execution of `python -m validation --json` with output captured and uploaded as a build artifact via `actions/upload-artifact@v4` with `if: always()`.
- CI exits with code 1 if any pytest test or validation mutation fails.

---

## 2. Decisions

| Question | Decision | Rationale |
|---|---|---|
| Project License | **MIT License** | Permissive, compatible with vendored MIT/BSD components and standard for academic research software. |
| Copyright Attribution | **Netgrader Contributors** | Generic attribution that covers all student and faculty contributors without conflicting with institutional IP policies. |
| Bundling Scope | **Split into PR A (#18, #27) and PR B (#28)** | PR A establishes repository standards and automated CI with zero application runtime risk. PR B (operational logging) can then be implemented with CI automatically enforcing test gates and privacy checks. |
| Branching Base | **Branch from `origin/master`** | Ensures CI is established on the root trunk so all open PRs (#40, #41) can rebase and benefit from automated checks. |
| CI OS Matrix | **`windows-latest` and `ubuntu-latest`** | Windows represents the physical lab workstation platform; Ubuntu represents standard headless CI and containerized deployment. |
| Linux Twofish Native Library | **Compile in CI before testing** | `cisco-pka-to-xml/build_libtwofish.py` compiles `vendor/twofish/twofish.c` to `pka2xml/libtwofish.so` using gcc, allowing all `.pkt` decrypt tests to run on Linux. |
| Validation Artifact Handling | **`if: always()` on artifact upload, bash shell** | Ensures the SOP #3 JSON report is preserved even when validation tests fail, and forces UTF-8 encoding across Windows and Linux runners. |

---

## 3. Specifications

### 3.1 Licensing & Attribution (#18)

#### A. Root `LICENSE`
Create `LICENSE` at the repository root containing standard MIT license text:
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

#### B. `THIRD_PARTY_NOTICES.md`
Create `THIRD_PARTY_NOTICES.md` at repository root detailing all bundled dependencies:
1. **pka2xml** (`cisco-pka-to-xml/`):
   - License: MIT License
   - Upstream: https://github.com/jeamxn/cisco-pka-to-xml
   - Copyright (c) 2024 Jean-Maximilien Cadot
2. **Twofish Native Implementation** (`cisco-pka-to-xml/vendor/twofish/`):
   - License: BSD 3-Clause License
   - Copyright (c) Keybase
3. **Tabler Icons** (`static/icons/sprite.svg`):
   - License: MIT License
   - Upstream: https://github.com/tabler/tabler-icons
   - Copyright (c) 2020-2024 Paweł Kuna
4. **Outfit Font** (`static/fonts/`):
   - License: SIL Open Font License 1.1
   - Copyright (c) 2021 On Brand Investments Pty Ltd
5. **JetBrains Mono Font** (`static/fonts/`):
   - License: SIL Open Font License 1.1
   - Copyright (c) 2020 JetBrains s.r.o.

#### C. `static/fonts/OFL.txt`
Place the SIL Open Font License 1.1 text in `static/fonts/OFL.txt` to accompany the `.woff2` font files as required by clause 2 of the OFL.

#### D. `README.md`
Append a `## License` section at the end of `README.md`:
```markdown
## License

This project is licensed under the [MIT License](LICENSE).

Third-party software, fonts, and icons included in this repository are subject to their respective licenses as detailed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
```

---

### 3.2 GitHub Actions CI Workflow (#27)

#### A. Workflow File: `.github/workflows/ci.yml`
- **Name:** `CI`
- **On:**
  - `push:` branches: `[ master ]`
  - `pull_request:` branches: `[ master ]`
- **Permissions:** `contents: read`

#### B. Job Definition: `test`
- **Runs-on:** `${{ matrix.os }}`
- **Defaults:** `run: shell: bash` (ensures identical redirection, piping, and script invocation on both Windows and Linux runners).
- **Matrix:**
  - `os`: `[ ubuntu-latest, windows-latest ]`
  - `python-version`: `[ "3.12" ]`
- **Steps:**
  1. **Checkout Code:**
     `uses: actions/checkout@v4`
  2. **Set up Node.js:**
     `uses: actions/setup-node@v4` with `node-version: 20`
     Ensures `test_frontend_modules.py` and `test_js_units.py` find `node` on `PATH` and execute rather than skipping.
  3. **Set up Python:**
     `uses: actions/setup-python@v5` with `python-version: ${{ matrix.python-version }}` and `cache: 'pip'`.
  4. **Build Native Cipher Library (Linux):**
     `if: runner.os == 'Linux'`
     `run: python cisco-pka-to-xml/build_libtwofish.py`
     Uses `gcc` (pre-installed on `ubuntu-latest`) to compile `pka2xml/libtwofish.so`.
  5. **Install Dependencies:**
     `run: |`
       `python -m pip install --upgrade pip`
       `pip install -r requirements-dev.txt`
  6. **Run Test Suite:**
     `run: python -m pytest -q -rs`
     Runs all pytest tests with `-rs` to explicitly list any skipped tests in the console.
  7. **Run Validation Harness (SOP #3):**
     `run: python -m validation --json > validation-report.json`
     Generates machine-readable results for all standard and mutated validation cases.
  8. **Upload Validation Report Artifact:**
     `uses: actions/upload-artifact@v4`
     `if: always()`
     `with:`
       `name: validation-report-${{ matrix.os }}`
       `path: validation-report.json`
       `if-no-files-found: warn`

---

## 4. Verification and Testing

### Local Verification Steps
1. **License and Notice Verification:**
   - Verify `LICENSE`, `THIRD_PARTY_NOTICES.md`, and `static/fonts/OFL.txt` exist and are well-formed.
   - Verify links from `README.md` resolve to the actual files.
2. **Local Workflow Syntax Check:**
   - Validate `.github/workflows/ci.yml` YAML syntax and structure.
3. **Local Pipeline Execution Simulation:**
   - Run `python -m pytest -q -rs`.
   - Run `python -m validation --json > validation-report.json`.
   - Verify that `validation-report.json` contains valid JSON with `reference_clean: true` and `100%` correct outcomes.

### Remote / Post-Merge Verification
1. Push branch to remote and open PR against `master`.
2. Confirm both `ubuntu-latest` and `windows-latest` jobs run and pass.
3. Confirm `validation-report-ubuntu-latest` and `validation-report-windows-latest` artifacts are attached to the workflow run.
4. Verify branch protection settings on GitHub repository (manual instructor step).
