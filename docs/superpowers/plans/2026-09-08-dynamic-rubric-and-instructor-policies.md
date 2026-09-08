# Dynamic Rubric & Instructor Policies Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement instructor policy toggles allowing dynamic student-defined subnetting, flexible device naming, Auto-MDIX cabling tolerance, flexible routing process IDs, and baseline security verification with 100% deterministic evaluation.

**Architecture:** Extend Pydantic criteria models with `EvaluationPolicies`, adapt `criteria_generator.py` to generate policy-aware human instructions and embedded schema, update `evaluator.py` to perform relational subnet arithmetic and topological role matching, and add a policy toggle control center in the Instructor Studio UI.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, `ipaddress` (stdlib), pytest, Vanilla HTML/CSS/JS.

## Global Constraints
- All evaluations must remain 100% deterministic, offline, and reproducible.
- Subnet math must use Python's built-in `ipaddress` library with strict validation.
- All single-file `instructions.txt` files must remain backward-compatible with the delimiter format `--- CRITERIA SPEC START ---` ... `--- CRITERIA SPEC END ---`.
- UI must maintain responsive dark theme styling matching `ui-ux-pro-max` guidelines.

---

### Task 1: Policy Schema & Data Models (`src/models.py`)

**Files:**
- Modify: `src/models.py:100-160`
- Test: `tests/test_models.py`

**Interfaces:**
- Produces: `EvaluationPolicies` Pydantic model with default values and validation; updated `EvaluationCriteria` model containing `policies: EvaluationPolicies`.

- [ ] **Step 1: Write the failing tests in `tests/test_models.py`**
```python
def test_evaluation_policies_defaults():
    from src.models import EvaluationPolicies, EvaluationCriteria
    policies = EvaluationPolicies()
    assert policies.allow_dynamic_subnetting is False
    assert policies.enforce_prefix_length is True
    assert policies.verify_default_gateways is True
    assert policies.allow_custom_hostnames is False
    assert policies.strict_port_matching is True
    assert policies.strict_cable_type is True
    assert policies.allow_flexible_process_ids is True
    assert policies.grade_security_baseline is False
    assert policies.grade_interface_descriptions is False

    crit = EvaluationCriteria(lab_title="Test Lab", lab_description="Desc", policies=policies)
    assert crit.policies.allow_dynamic_subnetting is False
```

- [ ] **Step 2: Run pytest to confirm failure**
```bash
pytest tests/test_models.py
```

- [ ] **Step 3: Implement `EvaluationPolicies` in `src/models.py`**
Add the `EvaluationPolicies` class and attach `policies: EvaluationPolicies = Field(default_factory=EvaluationPolicies)` to `EvaluationCriteria`.

- [ ] **Step 4: Run tests and verify passing**
```bash
pytest tests/test_models.py
```

- [ ] **Step 5: Commit**
```bash
git commit -am "feat(models): add EvaluationPolicies schema to EvaluationCriteria"
```

---

### Task 2: Policy-Aware Criteria & Instructions Generation (`src/criteria_generator.py`)

**Files:**
- Modify: `src/criteria_generator.py`
- Test: `tests/test_criteria_generator.py`

**Interfaces:**
- Consumes: `EvaluationPolicies`, `EvaluationCriteria`, `EvaluationRule`, `TopologyResult`
- Produces: `generate_criteria_from_topology(topology, ..., policies=None) -> EvaluationCriteria`, `format_criteria_to_instructions_txt(criteria) -> str`, `parse_instructions_txt(content) -> EvaluationCriteria`

- [ ] **Step 1: Write failing tests in `tests/test_criteria_generator.py`**
Add tests verifying:
1. `generate_criteria_from_topology` with `allow_dynamic_subnetting=True` produces relational subnet descriptions and policies attached.
2. `format_criteria_to_instructions_txt` produces dynamic addressing instructions, includes policy summary section, and serializes policies in JSON block.
3. `parse_instructions_txt` restores the `policies` object accurately.
4. If `grade_security_baseline=True` or `grade_interface_descriptions=True`, respective rules are generated.

- [ ] **Step 2: Run pytest to confirm failure**
```bash
pytest tests/test_criteria_generator.py
```

- [ ] **Step 3: Implement policy-aware criteria generation & text formatting in `src/criteria_generator.py`**
- In `generate_criteria_from_topology`, accept `policies: EvaluationPolicies | None = None`.
- If `policies.allow_dynamic_subnetting`, assign `category="relational_subnet"` with expected CIDR, connected peer device/port.
- If `policies.grade_security_baseline`, extract security checkpoints (`enable secret`, `service password-encryption`).
- In `format_criteria_to_instructions_txt`, print dynamic addressing directions and an "Instructor Evaluation Policies" summary header.
- In `parse_instructions_txt`, parse `policies` from JSON spec with fallback to defaults.

- [ ] **Step 4: Run tests and verify passing**
```bash
pytest tests/test_criteria_generator.py
```

- [ ] **Step 5: Commit**
```bash
git commit -am "feat(criteria): implement policy-aware rule generator and instructions formatter"
```

---

### Task 3: Deterministic Relational Evaluator Engine (`src/evaluator.py`)

**Files:**
- Modify: `src/evaluator.py`
- Test: `tests/test_evaluator.py`

**Interfaces:**
- Consumes: `EvaluationCriteria` (with `policies`), `TopologyResult`
- Produces: `evaluate_student_submission(criteria, student_topology) -> EvaluationReport`

- [ ] **Step 1: Write failing tests in `tests/test_evaluator.py`**
Write tests for:
1. `test_dynamic_subnetting_success`: Student submission uses `10.10.10.0/30` instead of reference `192.168.1.0/30`; passes when `allow_dynamic_subnetting=True`.
2. `test_dynamic_subnetting_mismatch`: Student configures R1 on `10.10.10.1/30` and R2 on `10.10.20.2/30`; fails with explicit subnet mismatch feedback.
3. `test_dynamic_subnetting_prefix_violation`: Student configures `/24` instead of required `/30`; fails when `enforce_prefix_length=True`.
4. `test_dynamic_subnetting_duplicate_subnet`: Student uses the same `10.10.10.0/30` on two distinct physical links; fails duplicate subnet check.
5. `test_flexible_hostnames`: Student names routers `Core_Rtr` and `Branch_Rtr` instead of `R1` and `R2`; passes when `allow_custom_hostnames=True`.
6. `test_flexible_ospf_process_id`: Student uses `router ospf 100` instead of `router ospf 1`; passes when `allow_flexible_process_ids=True`.
7. `test_cable_type_tolerance`: Student uses straight-through instead of cross-over; passes when `strict_cable_type=False`.

- [ ] **Step 2: Run pytest to confirm failure**
```bash
pytest tests/test_evaluator.py
```

- [ ] **Step 3: Implement relational evaluation logic in `src/evaluator.py`**
- Implement `_evaluate_relational_subnet(rule, student_devices, student_links, policies)` using `ipaddress.IPv4Interface`.
- Implement `_find_student_device_by_role(devices, target_dev_rule, links)` for flexible hostnames.
- Implement Auto-MDIX cable equivalence for copper interfaces when `strict_cable_type=False`.
- Implement flexible OSPF process ID matching checking Area 0 and subnet coverage.

- [ ] **Step 4: Run tests and verify passing**
```bash
pytest tests/test_evaluator.py
```

- [ ] **Step 5: Commit**
```bash
git commit -am "feat(evaluator): implement deterministic relational subnet and policy evaluation"
```

---

### Task 4: API & Frontend Policy Switcher Center (`src/app.py`, `templates/index.html`, `static/css/style.css`, `static/js/app.js`)

**Files:**
- Modify: `src/app.py`
- Modify: `templates/index.html`
- Modify: `static/css/style.css`
- Modify: `static/js/app.js`
- Test: `tests/test_app.py`, `tests/test_e2e_live_server.py`

**Interfaces:**
- `POST /api/criteria/generate`: Accepts policy form fields/JSON, returns criteria with policies.
- UI: Policy switch toggles in Instructor Studio card.

- [ ] **Step 1: Write integration tests in `tests/test_app.py`**
Verify `/api/criteria/generate` accepts policy boolean flags and passes them to the generator.

- [ ] **Step 2: Update `src/app.py`**
Extract `allow_dynamic_subnetting`, `allow_custom_hostnames`, `strict_port_matching`, etc. from request and instantiate `EvaluationPolicies`.

- [ ] **Step 3: Update `templates/index.html`**
Add the policy grid inside `#panel-mode-teacher` with clean labeled switch toggles for each policy.

- [ ] **Step 4: Update `static/css/style.css`**
Add `.policy-control-grid`, `.policy-group-card`, `.switch-label`, `.policy-desc` styles.

- [ ] **Step 5: Update `static/js/app.js`**
Gather checked state of policy toggles when clicking "Generate Rubric", send to `/api/criteria/generate`, and render policies summary in the preview.

- [ ] **Step 6: Run full test suite & verify in Puppeteer**
```bash
pytest -v
```

- [ ] **Step 7: Commit**
```bash
git commit -am "feat(ui): add instructor evaluation policy switches and full end-to-end integration"
```
