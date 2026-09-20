# System Documentation

**Network Configuration Evaluation and Topology Discovery Tool**
First City Providential College — Cisco Networking Academy

Last updated: 2026-09-20

---

## 1. What the system does

An instructor uploads their own finished Packet Tracer file, chooses how strict
the grading should be, and gets a rubric. Students upload their attempt and get
an itemised score with per-checkpoint feedback explaining why each requirement
exists and what to study.

Three properties define the design:

1. **Every score is computed by deterministic rules.** No language model
   participates in grading. The boundary is structural, not a promise — see §7.
2. **A correct answer that differs from the instructor's is still correct.**
   Ten policy switches control what "correct" means, so a student who designs a
   completely different but working addressing scheme can score 100%.
3. **It runs offline.** No internet, no cloud API, no per-student install.

---

## 2. Pipeline

```
Upload (.pkt / .pka / .xml / .zip / .txt)
   │
   ├── binary .pkt ──► pka2xml decrypt ──► XML
   │     └── src/pkt_parser.py      GROUND-TRUTH cabling, cable types,
   │                                canvas positions, PC/laptop profiles
   │
   └── text bundle ──► src/sanitizer.py ──► src/parsers.py
                                     running-config, CDP, ip int brief,
                                     ip route, vlan brief, trunk, MAC table
                             │
                             ├── src/fusion_engine.py   7 signals, Noisy-OR
                             │                          (text path only — see §5)
                             │
                             ▼
                  src/conflict_detector.py    diagnostics with line citations
                             │
          ┌──────────────────┴──────────────────┐
          ▼                                     ▼
  src/criteria_generator.py             src/evaluator.py
  instructor → instructions.txt         student → scored report
          │                                     │
          │                                     ▼
          │                             src/feedback.py     deterministic guidance
          │                                     │
          │                                     ▼
          └────────────────────────────► src/narrative.py   optional local LLM,
                                                            wording only
```

### Module map

| Module | Responsibility |
|---|---|
| `src/models.py` | Every data structure. Pydantic, so the shapes are enforced. |
| `src/sanitizer.py` | Strips terminal control characters, `--More--` banners, ANSI escapes; splits multi-command output into sections. |
| `src/parsers.py` | Cisco CLI → `ParsedDevice`. Running-config, CDP, `ip int brief`, `ip route`, `vlan brief`, trunk, MAC table. Also `classify_device_role()`. |
| `src/pkt_parser.py` | `.pkt`/`.pka` decrypt and XML parse. Returns devices **and ground-truth cabling**. |
| `src/fusion_engine.py` | Infers links from config evidence when no `.pkt` cabling exists. Seven signals combined by Noisy-OR. |
| `src/conflict_detector.py` | Subnet mismatch, interfaces down, duplicate IPs, native VLAN mismatch, wrong cable type — each with line citations. |
| `src/link_attributes.py` | The link-scoped rule registry: 14 attributes, 4 predicates, compatibility matrices. |
| `src/criteria_generator.py` | Reference topology → `EvaluationCriteria`; renders and re-parses `instructions.txt`. |
| `src/evaluator.py` | Student topology + criteria → `EvaluationReport`. **The score is decided here and is final.** |
| `src/feedback.py` | Deterministic per-checkpoint guidance and ranked study topics. |
| `src/llm.py` | Optional local Ollama client. Never raises, never blocks, never sees a score. |
| `src/narrative.py` | The only place a model is used. Student summary, class briefing. |
| `src/app.py` | FastAPI application and nine endpoints. |
| `validation/` | SOP #3 measurement instrument. Imported by nothing in `src/`. |

---

## 3. The grading model

### 3.1 Rule categories

A rubric is a list of `EvaluationRule`. Eleven categories exist:

| Category | Checks |
|---|---|
| `device` | The device is present, of the right type. |
| `interface_ip` | Exact address, mask, CIDR. |
| `relational_subnet` | Endpoints mutually in one subnet, IPs unique, subnets not reused, prefix enforced. Used instead of `interface_ip` under dynamic subnetting. |
| `interface_status` | Interface enabled (`no shutdown`) and line protocol up. |
| `cabling` | The two endpoints are physically connected, on the right ports, with the right media. |
| `vlan_trunk` | Trunk mode and access VLAN assignment. |
| `link_agreement` | **Both ends of a link agree.** See §4. |
| `gateway` | Hosts and switches have a gateway inside the connected router's subnet. |
| `routing` | Networks advertised into the right OSPF area. |
| `security` | `enable secret`, `service password-encryption`, `line vty` login. |
| `documentation` | Interface descriptions naming the correct peer. |

Points are apportioned across all rules by largest-remainder (Hamilton)
apportionment in tenths of a point, so a rubric always totals exactly its
target and no rule can ever be worth zero or less.

### 3.2 Policy switches

Ten switches, set by the instructor, embedded in `instructions.txt` so grading
is reproducible from the file alone.

| Switch | Effect when enabled | Default |
|---|---|---|
| `allow_dynamic_subnetting` | Grades mutual subnet membership, uniqueness and non-reuse instead of exact IP strings. | off |
| `enforce_prefix_length` | The student's own subnet must still use the required prefix. | on |
| `verify_default_gateways` | Gateway must sit in the connected router's subnet. | on |
| `allow_custom_hostnames` | Devices matched by type and topological role, not name. | off |
| `strict_port_matching` | Exact port numbering required; off accepts any port of the same speed class. | on |
| `strict_cable_type` | Exact media required; off tolerates Auto-MDIX copper equivalence. | on |
| `allow_flexible_process_ids` | Ignores locally-significant OSPF process IDs; checks areas and networks. | on |
| `grade_security_baseline` | Adds the hardening checkpoints. | off |
| `grade_interface_descriptions` | Adds the documentation checkpoints. | off |
| `enforce_reference_link_values` | A link-agreement value must equal the reference, not merely agree across the link. | off |

These are what separate the tool from Packet Tracer's own Activity Wizard,
which only does exact-match grading.

---

## 4. Link-scoped rules

Every other rule targets one device and at most one interface. That shape
cannot ask the question that decides whether a link actually works: *do both
ends agree?*

`link_agreement` rules put endpoint A in the target fields and endpoint B in
`expected_value`, then apply a named predicate. Endpoints resolve through the
same device-mapping and port-matching helpers as every other rule, so
`allow_custom_hostnames` and `strict_port_matching` still apply, and a rule
written A→B matches a link discovered B→A.

### 4.1 Predicates

| Predicate | Meaning |
|---|---|
| `equal` | Both ends hold the same effective value. |
| `compatible` | The pairing appears in a named compatibility matrix. |
| `covers` | Every VLAN in use on both sides is permitted on both ends. |
| `exactly_one` | The attribute is set on precisely one endpoint. |

### 4.2 Attributes

| Attribute | Predicate | Points | Default when unwritten |
|---|---|---|---|
| `trunk_native_vlan` | equal | 6.0 | — |
| `trunk_allowed_vlans` | covers | 5.0 | all VLANs |
| `switchport_mode` | compatible | 5.0 | — |
| `ospf_hello_interval` | equal | 6.0 | 10 |
| `ospf_dead_interval` | equal | 6.0 | 40 |
| `ospf_area` | equal | 7.0 | — |
| `ospf_network_type` | equal | 5.0 | — |
| `ospf_authentication` | equal | 5.0 | none |
| `mtu` | equal | 6.0 | 1500 |
| `speed` | equal | 4.0 | auto |
| `duplex` | equal | 4.0 | auto |
| `channel_group_mode` | compatible | 7.0 | — |
| `encapsulation` | equal | 5.0 | hdlc |
| `clock_rate` | exactly_one | 5.0 | — |

### 4.3 Three design rules that keep these honest

**Implicit defaults.** An absent config line still has an effective value. One
end writing `duplex auto` and the other writing nothing is agreement, not a
mismatch. Comparison is effective-value against effective-value.
`exactly_one` is exempt: there, absence is the fact being measured.

**Generated only from the reference.** A rule appears only when the
instructor's own file configures the attribute. A lab with no trunks emits no
trunk rules. Real router configs always emit `speed` and `duplex`, so those
are always graded; `mtu` and OSPF timers only when set deliberately.

**Never demand what the reference cannot satisfy.** Generation is gated on the
reference passing its own rule. A rule the worked answer fails would put 100%
out of reach for the entire class.

### 4.4 Why compatibility matrices exist

These pairings fail with **no error message at all**, which is why students
cannot debug them:

```
EtherChannel   active  passive  on    desirable  auto
active          OK      OK      NO      NO       NO
passive         OK      NO(*)   NO      NO       NO
on              NO      NO      OK      NO       NO
desirable       NO      NO      NO      OK       OK
auto            NO      NO      NO      OK       NO(*)

DTP            trunk  desirable  auto   access
trunk           OK      OK       OK      NO
desirable       OK      OK       OK      NO
auto            OK      OK      NO(*)    NO
access          NO      NO       NO      OK

(*) Both ends wait to be asked. Nothing forms and nothing is logged.
```

---

## 5. Topology discovery — two paths with very different accuracy

This distinction matters and is easy to miss.

### `.pkt` / `.pka` upload — ground truth

Cabling is read from the file's `LINKS` section. Nothing is inferred. On a
real 66-device lab: **92 links read, 92 correct.**

### Text/ZIP config bundle — inference

With no cabling in the file, `fusion_engine.py` infers links from seven
signals — CDP neighbours, point-to-point subnet co-membership, shared-subnet
co-membership, trunk matching, next-hop routing correlation, interface
description hints, and physical carrier state — combined by Noisy-OR into
confidence-scored edges.

Measured on the same 66-device lab, config-only:

| | |
|---|---|
| Ground-truth links | 92 |
| Inferred links | 2 803 |
| Correct | 50 |
| **Precision** | **1.8%** |
| **Recall** | **54%** |

Confidence does not separate the good from the bad: Noisy-OR saturates, and
spurious links reach the "verified" classification.

**Consequence:** the text path is usable for *visualising* a topology and for
grading device-local facts. It is **not** currently suitable for generating a
rubric, because link-derived rules would be built on fabricated links. Use
`.pkt` for grading.

---

## 6. Feedback

Two layers, both strictly downstream of scoring.

**Deterministic guidance** (`src/feedback.py`) — every failed checkpoint gets
an explanation of why the requirement exists and how to satisfy it, keyed by
rule category. Coverage is total by construction: a test fails if a category
exists without guidance. A ranked "what to study next" list is derived from
which topics cost the most points.

**Narrative layer** (`src/narrative.py`) — optional. One short paragraph per
student report, and a class briefing for the instructor.

---

## 7. The AI boundary

```
[1] PARSER           → normalised config model      deterministic
[2] NORMALISER       → semantic equivalence         deterministic
[3] TOPOLOGY BUILDER → multi-layer graph            deterministic
[4] RULE ENGINE      → SCORE + evidence citations
                       *** THE SCORE IS DECIDED HERE. FINAL. ***
[5] GUIDANCE         → templates, then local LLM: wording only
                       *** CANNOT CHANGE THE SCORE. ***
```

Enforced structurally, not by convention:

- `attach_guidance()` is the **last** call in `evaluate_student_submission()`.
  Every score is already computed and stored before any model can run.
- `src/llm.py` returns `None` on any failure — daemon down, model missing,
  timeout, malformed JSON. It never raises into a caller.
- The model receives **structured findings**, never configuration text and
  never student names. Small input, small hallucination surface, and compliant
  with R.A. 10173.
- With no model installed, output is still complete and useful. This is what
  keeps the offline claim true.

Configuration: `NCA_LLM_ENABLED`, `NCA_LLM_HOST`, `NCA_LLM_MODEL`,
`NCA_LLM_TIMEOUT`. All optional.

---

## 8. Validation — the SOP #3 instrument

`python -m validation` measures the grading engine from outside. It imports
from `src/`; nothing in `src/` imports it, and a test enforces that.

### Two preconditions, checked first

1. **The reference scores 100% against its own rubric.** A rubric the worked
   answer cannot satisfy makes every figure below meaningless.
2. **Parsed config yields the same rubric as the constructed model.** The same
   network is written twice — as objects and as Cisco CLI text — and graded
   side by side. Anything the parser drops makes them diverge and is named by
   rule id.

### Twenty-two cases

**Sixteen injected faults** measure recall: native VLAN mismatch, trunk left
as access, populated VLAN pruned, interface shutdown, wrong IP, wrong mask,
subnet mismatch, device missing, cable unplugged, wrong access VLAN, gateway
removed, gateway in wrong subnet, OSPF missing, `enable secret` removed, OSPF
hello mismatch, duplex hard-set against auto.

**Six negative cases** measure specificity — correct work that merely differs
from the reference: renamed devices, the student's own addressing plan, a
native VLAN both ends agree on, an unused VLAN pruned, non-default OSPF timers
agreed by both ends, a spare loopback.

The negative cases matter more. A grader that fails everything scores 100%
recall; only specificity distinguishes a strict grader from an accurate one.
And a false positive takes marks from a student who did the work properly,
which is the worse of the two failures.

### Metrics

```
Accuracy -- faults detected (recall)        : 100.0%  (16 faults)
Accuracy -- correct work left alone         : 100.0%  (6 cases)
Accuracy -- cases with no spurious failures : 100.0%
Consistency -- identical score on 3 runs    : 100.0%
Feedback reliability -- names the fault     : 100.0%
```

`--json` emits the metrics and every case for direct citation. Exit code is 1
on any incorrect behaviour, so it can gate a commit.

### Negative controls

`tests/test_validation.py` deliberately breaks the engine — blinds it to a
category, makes it over-strict, makes it non-deterministic, mutes its
guidance, drops OSPF networks, drops descriptions, drops a device — and
asserts the harness reports each. An instrument that always reports success is
worse than no instrument.

---

## 9. Interfaces

### Screens

- **Topology Discovery** — visualise any upload as a map with confidence-rated
  links and an evidence drawer citing exact config lines. Routers draw as a
  short cylinder, switches as a port-marked box, PCs as a monitor.
- **Instructor Studio** — generate a rubric, set the ten policy switches, and
  batch-grade a whole class to a gradebook CSV.
- **Student Grading** — upload `instructions.txt` plus an attempt, get a
  scorecard with per-checkpoint guidance.

### API

| Method | Route | Purpose |
|---|---|---|
| GET | `/` | The application. |
| POST | `/api/analyze` | Upload → `TopologyResult`. |
| POST | `/api/criteria/generate` | Reference + policies → `instructions.txt`. |
| POST | `/api/criteria/parse` | `instructions.txt` → `EvaluationCriteria`. |
| POST | `/api/evaluate` | Criteria + submission → `EvaluationReport`. |
| POST | `/api/evaluate/batch` | Whole class → per-student results + CSV. |
| GET | `/api/llm/status` | Narrative layer availability. |
| POST | `/api/report/narrative` | Student summary. |
| POST | `/api/class/briefing` | Instructor class briefing. |

---

## 10. Known limits

| Limit | Detail |
|---|---|
| Config-bundle link inference | 1.8% precision. Not suitable for rubric generation; `.pkt` is. |
| Reference-bounded grading | An attribute the instructor's file never configures produces no rule, so a student's change to it is not graded. Correct — the reference is the specification — but link agreement is only as complete as the reference. |
| Non-CLI devices | IP phones, printers, access points and TVs parse as `unknown` with no interfaces. On the 66-device lab, 13 of 66. |
| Parse-fidelity breadth | Four devices' worth of config text. A parser bug in a construct those bundles do not contain still hides. |
| Group invariants | HSRP, VRRP, GLBP, STP root election, VTP domain consistency and MST region matching are not yet expressible. They need a rule whose subject is a *set* of devices. |
| Protocol coverage | EIGRP, BGP, DHCP, NAT, ACLs, port-security and spanning-tree are not parsed or graded. |

---

## 11. Development

```bash
python -m pip install --user -r requirements-dev.txt
python -m pytest -q          # 203 tests
python -m validation         # SOP #3 metrics; exit 1 on any incorrect behaviour
```

| File | Purpose |
|---|---|
| `requirements.txt` | Core runtime. All a lab computer needs. |
| `requirements-dev.txt` | Adds pytest and HTTP clients. |
| `requirements-collector.txt` | GUI-automation extras for `scripts/pt_collector.py` only. |

`cisco-pka-to-xml/` is a vendored copy of
[jeamxn/cisco-pka-to-xml](https://github.com/jeamxn/cisco-pka-to-xml) (MIT),
which decrypts `.pkt`/`.pka` files. Vendored rather than installed so a lab
computer with no internet still has working Packet Tracer support.

Design specs live in `docs/superpowers/specs/`.
