# Technical Defense Answers
**Network Configuration Evaluation and Topology Discovery Tool**
Group 1 — First City Providential College

> Aligned sa panel audit dated 20 August 2026. Ang mga desisyon dito ay sumasagot sa
> R4-1 (architecture contradiction), R4-2 (topology ceiling), at R4-3 (input format).

---

## 1. Backend — Python 3 + FastAPI

**Sagot:** Python 3.11+ with FastAPI, served by Uvicorn.

**Justification:** Locked ng paper — Significance of the Study: *"a web-based monitoring
system that is driven by Python."* Chapter II RRL: Mazin & Rahman (2023) — Python-based
automation. Python-exclusive ang mga Cisco parsing library (`ciscoconfparse2`, `ttp`).

**Bakit FastAPI:**

1. **Pydantic validation** — ang rubric file at ang parsed config ay parehong structured
   data. Typed models = namamatay agad ang malformed input sa boundary, hindi sa gitna
   ng grading. Maipagtatanggol ito bilang reliability mechanism (sagot sa RQ "accuracy
   of configuration checking").
2. **Automatic OpenAPI docs sa `/docs`** — libreng API documentation para sa Chapter III
   Software Requirements Specification section.
3. **`BackgroundTasks`** — instant ang rule-based score; ang LLM explanation ay tumatakbo
   sa likod nang walang Celery/Redis.

---

## 2. Frontend — Jinja2 + sariling CSS + vanilla JS

**Sagot:** Server-rendered Jinja2 templates para sa display pages, plain `fetch()` calls
sa parehong FastAPI app para sa interactive fragments. Walang React/Vue, walang build
toolchain, walang npm.

**Views:** Upload form (rubric + config bundle) → Evaluation result (score, missed
configs, evidence line numbers) → Topology view → PDF export.

---

## 3. Database — Wala

**Sagot:** Stateless request-response. Upload → parse in-memory → evaluate → render
result → (optional) download PDF. Walang accounts, walang session storage, walang
persistence layer.

**Justification:** Sumusunod ito sa Figure 1 paradigm ng paper — isang linear na daloy:
upload config → define criteria → analysis → evaluation output. Ang instructor ang
nag-e-export ng PDF papunta sa sarili niyang computer; ang PDF mismo ang "storage,"
sa labas ng system.

**Bonus sa RA 10173 (Data Privacy Act):** walang student data na natitira sa server
matapos ang request. Walang database = walang data breach surface. Pinakamalinis na
sagot ito sa privacy question ng audit (R3-3).

**Caveat:** kung sakaling may multiple instructor na gagamit, isang shared password
sa `.env` ang sapat — hindi buong user table.

---

## 4. Config Parsing — Text bundle, hindi `.pkt`

**Sagot:** Ang students ay mag-e-export ng text output kada device bilang `.txt`,
naka-batch sa isang ZIP o sa naming convention na `ACTIVITY_STUDENTID_DEVICE.txt`.

**Bakit hindi `.pkt` (audit R4-3):** proprietary, compressed binary format, hindi
documented para sa third-party parsing. Ang community reverse-engineering ay nagbabago
kada Packet Tracer version — hindi ito matibay na foundation para sa capstone.

**Parsing pipeline:**

1. **Section splitter** — hinahati ang isang device file sa mga block gamit ang command
   echo bilang delimiter:
   ```python
   SECTION_RE = re.compile(r"^(\S+)#(show .+)$", re.M)
   ```
   Kaya sinasabihan ang estudyante na **huwag tanggalin ang prompt** sa copy-paste.
2. **`ciscoconfparse2`** — hierarchical parse ng running-config blocks
   (`interface`, `router ospf`, `vlan`, `line vty`, `access-list`)
3. **Table parsers** — regex-based para sa `show ip interface brief`,
   `show cdp neighbors detail`, `show vlan brief`, `show mac address-table`
4. **Pydantic normalisation** — structured device model, in-memory
5. **Validation gate** — ang malformed submission ay ni-re-reject nang may malinaw na
   message **bago** mag-grade. Kailanman ay hindi silent zero (fairness requirement, R4-4).

---

## 5. Topology Discovery — Multi-signal inference with confidence fusion

**Sagot:** Hindi isang technique lang. Bumubuo ang system ng graph mula sa **mahigit
tatlumpung magkakaibang signal**, pinagsasama sa pamamagitan ng confidence weighting,
at ginagamit ang mga salungatan bilang error findings.

### 5.1 Ang input bundle — ito ang nagtataas ng ceiling

Sabi ng audit (R4-2): sa `show running-config` lang, invisible ang malaking bahagi ng
topology. Kaya ang kinokolekta ay bundle, hindi isang file.

**Router:**
```
terminal length 0
show running-config
show cdp neighbors detail
show ip interface brief
show ip route
show version
```
Idagdag kung ginagamit sa lab: `show ip ospf neighbor`, `show standby brief`

**Switch:**
```
terminal length 0
show running-config
show cdp neighbors detail
show ip interface brief
show vlan brief
show interfaces trunk
show mac address-table
show spanning-tree
show version
```

**PC / End device** — Packet Tracer: *Desktop tab → Command Prompt*
```
ipconfig /all
arp -a
```

Ang `ipconfig /all` ang sagot sa isang bahagi ng R4-2 ceiling. Sabi ng audit na ang end
devices ay "entirely invisible to a config-only parser" — totoo sa running-config, pero
ang `ipconfig /all` ay nagbibigay ng IP, mask, gateway, at **MAC address**. I-cross-
reference ang MAC sa `show mac address-table` ng switch = alam mo kung saang eksaktong
port nakakabit ang PC.

**Minimum kung ayaw ng mahabang submission (~30 segundo):** `show running-config` +
`show cdp neighbors detail` + `show ip interface brief`.

### 5.2 Signal catalog — bakit hindi lang subnet matching

**Mula sa running-config (Tier A):**

| Signal | Ano ang sinasabi |
|---|---|
| **Subnet co-membership** | `/30` at `/31` = point-to-point by design, mataas ang tiwala. `/24` na maraming device = mahina, shared segment. |
| **Serial DCE clock rate** | Ang `clock rate 64000` ay nasa DCE end lang. May clock rate + katapat na wala, parehong subnet = kumpirmadong serial pair. Ang *kawalan* nito ay klasikong lab error. |
| **PPP CHAP username** | Ang `username R2 password cisco` sa R1 ay literal na pangalan ng katapat. Direktang deklarasyon ng peer. |
| **HSRP / VRRP group** | Dalawang router na may parehong `standby 1 ip 10.0.0.254` ay **kinakailangang** nasa iisang broadcast domain. Hindi inference — physics. |
| **Router-on-a-stick** | `encapsulation dot1Q 10` sa subinterface = may trunk papunta sa switch na may dalang VLAN 10. |
| **Port security static MAC** | Literal na MAC ng naka-attach na end device sa port na iyon. |
| **Static route next-hop** | Kung ang next-hop IP ay pag-aari ng ibang device, may logical dependency. |
| **Trunk allowed-VLAN + native VLAN** | Magkatugmang config = kandidatong uplink. Ang **hindi** magkatugma ay error. |
| **Duplicate IP** | Walang iisang device ang makakaalam nito — purong cross-file finding. |
| **`ip default-gateway`, DHCP `default-router`, `ip helper-address`** | Bawat isa ay reference sa IP ng ibang device. |
| **Interface description** | Madalas isulat ng estudyante ang `description Link to R2 Gi0/1`. Mababa ang tiwala pero libre, at gradeable bilang documentation practice. |

**Mula sa bundle (Tier B) — dito nasisira ang ceiling:**

| Signal | Ano ang sinasabi |
|---|---|
| **`show cdp neighbors detail`** | Ang authoritative source. Local interface, neighbor device ID, neighbor port, capability code. Isang linya = isang kumpirmadong pisikal na link. |
| **`show ip interface brief`** | **Ito ang sagot sa "cabling errors are undetectable."** Tamang config pero `down/down` = walang kable o kulang ang `no shutdown` — ang pinakakaraniwang pagkakamali ng estudyante. |
| **`show mac address-table`** | Port na may **maraming** MAC = uplink papunta sa ibang switch. Port na may **isang** MAC = may naka-attach na end device. Klasikong L2 topology algorithm (Breitbart et al. approach). |
| **`show spanning-tree`** | Nagbubunyag ng **blocked ports** — mga link na umiiral pero hindi ginagamit. Literal na invisible sa L3 inference. |
| **`show ip ospf neighbor`** | Aktwal na naitatag na adjacency. `FULL` = gumagana. `INIT`/`2WAY` lang = may timer o area mismatch. |
| **`show interfaces trunk`** | Operational trunk state — aling VLAN ang *aktwal* na dumadaan, hindi lang naka-configure. |

### 5.3 Confidence-weighted fusion — ang aktwal na contribution

Hindi on/off ang bawat signal. Nag-a-accumulate sila ng ebidensya sa isang candidate edge:

```python
SIGNAL_WEIGHT = {
    "cdp_neighbor":       1.00,   # authoritative
    "ospf_neighbor_full": 0.95,
    "p2p_subnet_30":      0.90,
    "serial_dce_pair":    0.90,
    "ppp_chap_username":  0.90,
    "hsrp_group_match":   0.85,
    "mac_table_uplink":   0.80,
    "trunk_config_pair":  0.65,
    "shared_subnet_24":   0.35,
    "description_hint":   0.25,
}

def edge_confidence(signals):
    p = 1.0
    for s in signals:                    # noisy-OR
        p *= (1 - SIGNAL_WEIGHT[s])      # maraming mahina = isang malakas
    return 1 - p
```

`≥0.80` = **verified** (solid line). `0.40–0.79` = **inferred** (dashed).
`<0.40` = **candidate** (itinatapon, nila-log).

**Bidirectional verification** (mula sa RRL, Ch. II): ang link ay confirmed lang kung
parehong endpoint ang sumasang-ayon. Ang one-sided ay `unverified` — at iyon mismo ang
finding, hindi bug.

### 5.4 Conflict detection — ito ang nagpapatunay na hindi dekorasyon

Kapag **hindi** magkasundo ang mga signal, hindi iyon failure ng system — **iyon ang
detected error.** Ito ang eksaktong sagot sa "paano kung mali ang inference mo?"

| Salungatan | Ibig sabihin |
|---|---|
| CDP: konektado, pero magkaibang subnet | IP misconfiguration sa isang dulo |
| CDP: konektado, pero `down/down` ang isa | Missing `no shutdown` |
| Subnet nagtutugma, pero walang CDP entry | Hindi talaga naka-kable — nagkataon lang |
| OSPF configured, pero walang `FULL` neighbor | Area, timer, o authentication mismatch |
| Magkaparehong subnet, magkaibang mask (`/30` ↔ `/24`) | Mask mismatch |
| Trunk sa isang dulo, access mode sa kabila | Mode mismatch |
| Next-hop IP na walang may-ari sa buong submission | Kulang na file, o maling static route |

### 5.5 Multi-layer graph model

Hindi isang graph — **apat na overlay** sa iisang node set (NetworkX `MultiGraph`
na may `layer` attribute). Toggle buttons sa UI, at bawat layer ay may sariling
error class:

```
L1 PHYSICAL   : CDP adjacency, interface up/down state
L2 DATA LINK  : VLAN broadcast domains, trunks, STP tree, MAC bindings
L3 NETWORK    : IP subnets, routed adjacency, OSPF peerings
L4 SERVICE    : DHCP, NTP, syslog, AAA dependencies
```

Ipinapakita nitong naiintindihan mo ang OSI model, hindi ka lang gumuguhit ng linya.

### 5.6 Graph analysis layer (NetworkX)

| Analysis | Ano ang nakikita |
|---|---|
| `connected_components()` | Nakahiwalay na device o island |
| `GraphMatcher` vs reference | Missing links, extra links (F-11 ng audit) |
| `has_path()` + simulated routing table | "Kaya bang maabot ng PC-A ang PC-B?" (F-4) |
| `edge_connectivity()` | Nagawa ba ang required redundancy? |
| `cycle_basis()` | Physical loops na dapat may humaharang na STP |

### 5.7 Ang honest ceiling (Delimitation)

Kung sakaling `show running-config` lang ang makokolekta, ang claim ay dapat na
**"Layer-3 adjacency inference and inter-device consistency checking"** — hindi
"topology discovery." Ang paglalagay mismo ng sariling ceiling ay lakas, hindi kahinaan.
Sa bundle, ang buong "topology discovery" claim ay maipagtatanggol na.

---

## 6. Third-Party Libraries & APIs

| Purpose | Technology |
|---|---|
| Web framework | FastAPI + Uvicorn |
| Validation | Pydantic |
| Config parsing | `ciscoconfparse2` + regex table parsers |
| Subnet math | `ipaddress` (stdlib) |
| Graph engine | `networkx` |
| Topology render | Server-generated **inline SVG** (`networkx` + `matplotlib`) |
| Feedback generation | **Ollama + Llama 3.2 3B**, lokal — few-shot prompted |
| Gradebook export | `csv` (stdlib) — isang row per estudyante |
| Rubric format | YAML/JSON (rubric as data, hindi code — audit F-1) |

**Walang PDF generator.** Ang output ay on-screen, at ang batch result ay CSV na
direktang bubuksan sa Excel o ipapasok sa gradebook. Sinasagot nito ang "large batches"
na problema ng Ch. I nang walang dagdag na rendering dependency.

**Bakit inline SVG, hindi vis.js:** dahil DOM elements ang inline SVG, kaya itong
i-style at gawing interactive gamit ang plain CSS at JS — walang graph library,
walang build step.

### Ang feedback layer — lokal na model, hindi cloud API

**Desisyon:** Llama 3.2 3B (o Qwen2.5 3B) na tumatakbo sa **Ollama** sa lab machine,
gumagamit ng **few-shot prompting** — 15–20 halimbawa ng structured finding → magandang
pedagogical feedback, nakalagay sa prompt.

Ang input ay **structured JSON mula sa rule engine**, hindi raw config:

```json
{"finding": "value_mismatch", "device": "R1", "line": 47,
 "expected": "ip ospf hello-interval 10", "found": "ip ospf hello-interval 30",
 "rubric_item": "OSPF-3", "points_lost": 2}
```
→
> "Sa R1, ang OSPF hello-interval mo ay 30 samantalang 10 ang kailangan. Dahil dito,
> hindi magkakasundo ang R1 at R2 — kailangang magkatugma ang hello at dead timers
> bago mag-form ang adjacency. Balikan mo ang linya 47."

**Bakit lokal at hindi Claude API:**

| Objection ng audit | Nasosolusyunan |
|---|---|
| Data privacy (RA 10173) — student work papuntang third-party | Walang lumalabas na data |
| Internet dependency *"in a lab where the network may be the thing under test"* | Gumagana nang **buong offline** |
| Per-submission API cost, rate limits, model deprecation | Zero recurring cost |

Ang 3B model na naka-quantize sa Q4 ay ~2GB. Tumatakbo sa CPU (Ryzen 5 5600) o sa
AMD GPU via Ollama. Ilang segundo lang kada talata ng feedback — sapat na sapat.

### Phase 2 — fine-tuning (nakaplano, hindi pa sa unang bersyon)

Ang few-shot examples ay siya mismong **unang bahagi ng training dataset.** Kapag
umabot na sa 300–500 pairs, LoRA/QLoRA fine-tune ng parehong 3B base model.

| Bagay | Detalye |
|---|---|
| Method | QLoRA via Unsloth |
| Hardware | **Kaggle free tier** (2× T4, 30 oras/linggo) — CUDA-only ang training |
| Training time | **~30 minuto** para sa 3B, 500 examples, 3 epochs |
| Inference | Parehong Ollama sa lab machine — walang pagbabago sa app |

**Tandaan:** ang RX 6600 (`gfx1032`) ay hindi sinusuportahan ng ROCm nang opisyal at
CUDA-only ang Unsloth — kaya cloud ang training. Pero ang **inference ay lokal pa rin**,
kaya buo ang offline claim.

**Chapter IV finding na naibibigay nito:** tatlong bersyon ng feedback para sa parehong
findings — (a) base model, (b) fine-tuned model, (c) sulat ng instructor — irarate ng
mga instructor sa clarity, correctness, at pedagogical usefulness nang blind. Ito ang
unang aktwal na paraan ng pagsukat sa **"reliability of generated feedback"** na RQ.

### Ang hybrid architecture (audit R4-1 — asahan mong ito ang tatanungin)

```
running-config bundle
        │
        ▼
  [1] PARSER          → normalised config model (deterministic)
        │
        ▼
  [2] NORMALISER      → semantic equivalence: int g0/0 = GigabitEthernet0/0
        │
        ▼
  [3] TOPOLOGY BUILDER → multi-layer graph (§5)
        │
        ▼
  [4] RULE ENGINE     → rubric evaluated → SCORE + evidence line numbers
        │                *** DITO NAGDEDESISYON ANG SCORE. TAPOS. ***
        ▼
  [5] EXPLANATION LAYER → lokal na LLM: pinapaganda ang wording ng findings
                          *** HINDI KAYANG BAGUHIN ANG SCORE. ***
```

**Ang linyang ito ay dapat nakasulat sa paper:** ang LLM ay hindi kailanman humahawak
sa grado; pinapahayag lang nito ang feedback, at **bawat pangungusap na nabubuo nito ay
naka-ugat sa isang rule-engine finding na may line-number citation.**

Sinasagot nito ang tatlong sub-question ng SOP #7 nang magkahiwalay:

- Rule engine (deterministic, reproducible) → **accuracy** at **consistency of grading**
- LLM layer → **reliability of generated feedback**

At ito ang sagot sa apat na teknikal na objection sa pure-LLM grading: non-determinism,
hallucination, walang audit trail para sa appeals, at data privacy.

---

## 7. Deployment — Local server sa Cisco lab, **buong offline**

**Sagot:** Naka-deploy sa isang lab machine. LAN-only access (`http://192.168.x.x:8000`).
**Walang internet na kailangan kahit kailan.**

Dahil lokal ang feedback model (Ollama, §6), wala nang anumang external dependency ang
sistema. Ito ang pinakamalinis na posisyon na maaari mong dalhin sa panel:

1. **RA 10173 compliance** — walang student data na lumalabas ng institusyon, at
   stateless ang system kaya wala ring natitira matapos ang request. Walang database,
   walang API call, walang telemetry. Walang data breach surface.
2. **Delimitation alignment** — *"confined to the Cisco Networking Academy lab at First
   City Providential College."* Pisikal na ipinapatupad ng LAN-only deployment.
3. **Zero recurring cost at walang external point of failure** — walang API bill, walang
   rate limit, walang model deprecation, at hindi apektado kapag bumagsak ang internet
   ng paaralan.

**Ang linya para sa panel:** *"Ang buong pipeline — parsing, topology discovery, scoring,
at feedback generation — ay tumatakbo sa loob ng lab machine. Ang tool ay gumagana kahit
ang network mismo ang bagay na sinusuri."*

**Hardware requirement:** isang lab PC na may 8GB RAM. Ang 3B model na naka-quantize sa
Q4 ay ~2GB, at kayang patakbuhin ng CPU. Kung may discrete GPU, mas mabilis — pero hindi
ito kinakailangan.

**Output at handover:** on-screen ang bawat resulta; ang batch ay ini-export bilang CSV
na kinukuha ng instructor papunta sa sariling gradebook. Walang naiiwang kopya sa server.

---

## Quick reference — one-liner answers

1. **Backend:** Python 3 + FastAPI. "Python-driven" ang paper; Pydantic = validation layer.
2. **Frontend:** Jinja2 + sariling CSS + vanilla JS. Walang React, walang build step.
3. **Database:** Wala — stateless. Sumusunod sa Figure 1 linear flow; PDF ang output.
4. **Parsing:** Text bundle per device, `ciscoconfparse2` + table parsers. Hindi `.pkt`.
5. **Topology:** 30+ signals (CDP, subnet arithmetic, HSRP, serial DCE, PPP CHAP, MAC
   tables, STP), pinagsama sa confidence weighting. **Ang salungatan ng signals ay hindi
   bug — iyon ang detected error.**
6. **Libraries:** ciscoconfparse2, networkx, matplotlib SVG, Ollama + Llama 3.2 3B (lokal),
   CSV stdlib. Rule engine ang nagsi-score; ang LLM ay explanation lang, hindi kayang
   galawin ang grado. Walang PDF generator; walang cloud API.
7. **Hosting:** Local lab server, LAN-only, **buong offline** — walang internet na
   kailangan kahit para sa AI feedback.
