# Design Spec: Pedagogical Guidance & Class Analysis Layer

**Date:** 2026-09-20
**Topic:** Deterministic guidance templates, local LLM explanation, and class-wide instructional analysis
**Status:** Ready for Plan & Implementation

---

## 1. Overview & Research Background

The grading engine already answers **what** a student missed. It does not answer
**why it matters** or **how to fix it**, and it does nothing with the results of a
whole class.

This specification introduces a single AI layer with three touchpoints, built in
three phases so that every phase is independently useful and the product never
depends on a model being available.

### 1.1 The architectural boundary (audit finding R4-1)

Nothing in this layer may influence a score. The boundary from
`decisions-2026-08-23.md` is preserved exactly:

```
[1] PARSER           -> normalised config model      (deterministic)
[2] NORMALISER       -> semantic equivalence         (deterministic)
[3] TOPOLOGY BUILDER -> multi-layer graph            (deterministic)
[4] RULE ENGINE      -> SCORE + evidence citations
                        *** THE SCORE IS DECIDED HERE. FINAL. ***
[5] GUIDANCE         -> templates, then local LLM: wording only
                        *** CANNOT CHANGE THE SCORE. ***
```

Consequences that must hold in the implementation:

- The score is computed, stored and rendered **before** any model runs.
- The model receives **structured findings**, never raw configuration text.
- If the model is slow, absent or returns nonsense, the student still gets a
  complete grade and complete per-checkpoint guidance.

Layers [1] and [2] are explicitly **off limits** to the model. A hallucination
upstream of the rule engine would silently change a grade with no audit trail,
which is the exact contradiction this architecture exists to resolve.

### 1.2 Research objectives served

| Objective | Current status | Served by |
|---|---|---|
| SOP #3 — reliability of generated feedback | No instrument exists | Touchpoint 1 |
| SOP #4 — administrative recommendations and institutional guidelines | **No feature exists at all** | Touchpoint 2 |

SOP #4 is the larger gap. Batch grading produces every student's score and
missed checkpoints, then stops at a CSV. Synthesising that into instructional
recommendations is the unserved objective.

---

## 2. Touchpoints

### 2.1 Touchpoint 1 — Student guidance

Per failed checkpoint, a deterministic explanation of why the requirement
exists and how to satisfy it. Per report, one short "what to study next"
summary.

```
Checkpoint : Enable interface R1 GigabitEthernet0/0 (no shutdown)
Result     : administratively down
Guidance   : Cisco router interfaces start administratively down. Until the
             interface is enabled it will not forward traffic, even with a
             correct IP address. Enter interface configuration mode and issue
             'no shutdown', then confirm with 'show ip interface brief'.
```

### 2.2 Touchpoint 2 — Class analysis (the headline feature)

Runs on a completed batch. Aggregates failures across submissions and produces
an instructor briefing: which concepts the class missed, ranked by how many
students they affected, with suggested instructional action.

Input is the aggregate failure pattern only — **no student names, no raw
configurations** — which keeps it compliant with R.A. 10173 and small enough for
a 3B model to reason over reliably.

### 2.3 Touchpoint 3 — Natural-language lab authoring (optional)

An instructor describes a lab in prose; the model proposes the nine policy
toggle settings and a lab description. It configures the **rubric**, never a
grade, and the instructor reviews every setting before publishing. This also
removes today's requirement to already own a finished reference `.pkt` before
any authoring can happen.

---

## 3. Phasing

| Phase | Deliverable | Depends on a model? |
|---|---|---|
| **A** | Deterministic guidance templates + study summary | No |
| **B** | Local LLM phrasing via Ollama, templates as fallback | Yes, with fallback |
| **C** | Fine-tuned variant for the blind comparison study | Yes, optional |

Phase A is not a stopgap. It is the permanent fallback that keeps the offline
claim true, it covers every finding the engine can produce, and its text is the
seed corpus for Phase C.

### 3.1 Why Phase A can be complete

`EvaluationRule.category` is a **closed set**: `device`, `interface_ip`,
`interface_status`, `cabling`, `vlan_trunk`, `routing`, `relational_subnet`,
`gateway`, `security`, `documentation`. Every possible finding belongs to one of
them, so a fixed set of explanations has total coverage by construction.

---

## 4. Phase A — Deterministic Guidance (`src/feedback.py`)

### 4.1 Responsibilities

- `explain(result: RuleResult) -> str` — why the requirement exists and how to
  satisfy it, specialised by category and by the specific failure mode.
- `study_topics(report: EvaluationReport) -> list[StudyTopic]` — the concepts to
  revisit, ranked by points lost.
- `class_analysis(rows) -> ClassAnalysis` — aggregate failure counts per concept
  across a batch, the deterministic input for Touchpoint 2.

### 4.2 Data model changes (`src/models.py`)

- `RuleResult.guidance: str | None` — populated for failed checkpoints.
- `EvaluationReport.study_topics: list[StudyTopic]`.

Both default to empty, so an `instructions.txt` or report produced before this
change still deserialises.

### 4.3 Failure-mode specialisation

Guidance keys off more than the category. For `interface_ip`, a wrong prefix on
an otherwise correct address must not produce the same text as an address in the
wrong subnet entirely, or the guidance is noise.

### 4.4 Pedagogical stance

Guidance names the concept and the command to investigate with, but does not
hand over the complete answer line. Students are told what to check and why,
not given a paste-ready fix. This is a deliberate instructional choice and
belongs in the Chapter V discussion.

---

## 5. Phase B — Local LLM Phrasing

### 5.1 Model and runtime

| | |
|---|---|
| Runtime | Ollama, local, offline after first pull |
| Model | `llama3.2:3b` (Q4_K_M, ~2.0 GB) or `qwen2.5:3b` (~1.8 GB) |
| VRAM in use | ~2.5–3.5 GB |
| Fallback | Phase A templates, always |

### 5.2 Hardware note (verified 2026-09-20)

The development machine has an RX 6600 (`gfx1032`, 8 GB VRAM), Ryzen 5 5600,
16 GB RAM.

- **Inference: viable.** `gfx1032` is not on Ollama's official ROCm list, but
  runs via `HSA_OVERRIDE_GFX_VERSION=10.3.0`, which presents it as the supported
  `gfx1030`. CPU fallback is also acceptable for this workload.
- **Training: not on this card.** Unsloth added official AMD support, but for
  RX 7000 and RX 9000 series. RDNA2 consumer cards are not included. Phase C
  therefore trains in the cloud (Kaggle free tier, 2×T4) and runs inference
  locally, exactly as `decisions-2026-08-23.md` concluded.

### 5.3 One generation per report, not per checkpoint

Per-checkpoint generation for a student with 21 failures is ~1,600 tokens
(minutes on CPU) and creates 21 independent hallucination opportunities.

Instead: **templates handle every checkpoint; the model writes one summary
paragraph per report.** A single ~150-token generation — seconds on GPU, 10–20 s
on CPU — and the hallucination surface is one paragraph that no grade depends on.

### 5.4 Prompt contract

The model receives structured JSON findings, never configuration text:

```json
{"finding": "value_mismatch", "device": "R1", "interface": "GigabitEthernet0/0",
 "expected": "10.0.0.1/30", "found": "192.168.1.1/24",
 "rubric_item": "ip_r1_gi0_0", "points_lost": 5.1}
```

---

## 6. Phase C — Fine-Tuning (conditional)

### 6.1 Decision rule

Fine-tune **only** to obtain the three-way blind comparison — base model vs.
fine-tuned vs. instructor-written, rated by instructors on clarity, correctness
and pedagogical usefulness. That comparison is the contribution and the only
instrument for the feedback-reliability RQ. If the product merely needs to work,
Phases A and B are sufficient and defensible.

### 6.2 Method

| | |
|---|---|
| Method | QLoRA via Unsloth |
| Base | The Phase B 3B model |
| Dataset | 300–500 instructor-quality pairs |
| Hardware | Kaggle free tier, 2×T4 |
| Training time | ~30 minutes |
| Adapter output | 50–200 MB; merged GGUF ~2 GB |

### 6.3 The dataset is the real cost, and the real risk

Training takes ~30 minutes; building the dataset takes weeks. More importantly:

> **If the corpus is generated from the Phase A templates, the model learns the
> templates.** The blind comparison would then show the fine-tuned variant is
> indistinguishable from the deterministic one — a null result manufactured by
> the method rather than observed in the data.

The pairs must be written or substantially edited by someone who teaches the
lab. This is the single largest threat to the validity of the Chapter IV
finding and must be stated in the methodology.

---

## 7. Storage Budget

| Item | Size |
|---|---|
| Ollama runtime | ~1.5 GB |
| `llama3.2:3b` Q4_K_M | 2.0 GB |
| `qwen2.5:3b` Q4_K_M | 1.8 GB |
| LoRA adapter (Phase C) | 50–200 MB |
| Merged fine-tuned GGUF | ~2 GB |
| Dataset, 300–500 pairs | < 1 MB |
| **Total, all phases** | **~7–8 GB** |

181 GB free on the development machine. Storage is not a constraint.

---

## 8. Verification Plan

### Phase A
- Every rule category produces non-empty, category-appropriate guidance.
- Guidance distinguishes failure modes within a category.
- Guidance never appears on a passed checkpoint.
- Study topics are ranked by points lost.
- A report produced before this change still deserialises.

### Phase B
- With Ollama unavailable, grading and guidance are unaffected and no error
  reaches the student.
- The model cannot alter `total_score`, `percentage` or any `points_earned`:
  asserted by grading one submission with the model stubbed to return
  adversarial text, and comparing the score to the deterministic run.

### Phase C
- Blind instructor rating across the three feedback variants.

---

## 9. Out of Scope

- Any model involvement in parsing, normalisation or scoring.
- Cloud model APIs. The deployment is offline by design and handles student
  data under R.A. 10173.
- Student names or raw configurations in any prompt.
