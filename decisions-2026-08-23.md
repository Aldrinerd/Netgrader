# Technical Decisions â 23 August 2026

**Network Configuration Evaluation and Topology Discovery Tool**
Group 1 â PeÃ±a, Owapin, Edem, Torres, Biglang-awa Â· First City Providential College

Ito ang talaan ng mga napagdesisyunan ngayong araw, kasama ang dahilan ng bawat isa.
Ang buong technical detail ay nasa [technical-answers.md](technical-answers.md);
ang topology signals ay nasa [topology-discovery-signals.md](topology-discovery-signals.md).

---

## Buod ng napagkasunduan

| # | Tanong | Desisyon |
|---|---|---|
| 1 | Backend | **Python 3 + FastAPI** (Uvicorn) |
| 2 | Frontend | **Jinja2 + sariling CSS + vanilla JS** â walang React/Vue |
| 3 | Database | **Wala** â stateless request-response |
| 4 | Input / parsing | **`.txt` bundle** ng show commands; **sariling parser**, hindi `.pkt` |
| 5 | Topology | **Multi-signal inference** + confidence fusion + conflict detection |
| 6 | Libraries | **Minimal** â FastAPI, Ollama, at networkx (kondisyonal) |
| 7 | Hosting | **Local lab server, buong offline** |
| â | AI | **Lokal na Llama 3.2 3B** via Ollama, few-shot; fine-tune as Phase 2 |
| â | Output | **On-screen + CSV** â walang PDF |

---

## 1. Backend â Python 3 + FastAPI

Locked ng paper: *"a web-based monitoring system that is driven by Python"* (Ch. I,
Significance). Python-exclusive din ang mga Cisco parsing tool.

**FastAPI kaysa Flask** dahil pamilyar na ang developer, at may tatlong dagdag:
Pydantic validation (maipagtatanggol bilang reliability mechanism), automatic OpenAPI
docs sa `/docs` (libreng API documentation para sa Ch. III SRS section), at
`BackgroundTasks` (async feedback generation nang walang Celery/Redis).

---

## 2. Frontend â Jinja2 + sariling CSS + vanilla JS

Walang React/Vue, walang npm, walang build step. Server-rendered Jinja2 (kasama na ng
FastAPI) para sa display pages, plain `fetch()` para sa interactive fragments.

**Dahilan:** walang real-time state ang system, at pamilyar na ang developer sa
HTML/CSS/JS. Ang React ay magdadagdag ng toolchain para sa zero benefit.

---

## 3. Database â WALA

Stateless: upload â parse in-memory â evaluate â render â CSV export. Walang accounts,
walang session storage, walang persistence.

**Dahilan:** sumusunod sa Figure 1 paradigm â isang linear na daloy. Walang aktwal na
kailangang itago; ang CSV na kinukuha ng instructor ang "storage," sa labas ng system.

**Bonus:** pinakamalinis na sagot sa RA 10173 (Data Privacy Act). Walang database =
walang data breach surface.

---

## 4. Input at parsing

### `.txt` bundle, hindi `.pkt`

Ang `.pkt` ay proprietary, compressed binary. Ang reverse-engineering nito ay nagbabago
kada Packet Tracer version â hindi matibay na foundation para sa capstone (audit R4-3).

### Ang bundle kada device

**Router:**
```
terminal length 0
show running-config
show cdp neighbors detail
show ip interface brief
show ip route
show version
```
Idagdag kung ginagamit: `show ip ospf neighbor`, `show standby brief`

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

**PC / End device** â Packet Tracer: *Desktop â Command Prompt*
```
ipconfig /all
arp -a
```

**Minimum kung kailangang paikliin (~30 segundo):** `show running-config` +
`show cdp neighbors detail` + `show ip interface brief`.

### Praktikal na detalye

- `terminal length 0` muna â kung hindi, puputulin ng `--More--` ang output
- **Huwag tanggalin ang prompt at command echo** â ito ang magiging delimiter ng parser:
  `re.compile(r"^(\S+)#(show .+)$", re.M)`
- Naming: `ACTIVITY_STUDENTID_DEVICE.txt`, o isang ZIP per estudyante
- Limitado ang scrollback buffer ng PT CLI â i-run isa-isa, i-copy agad
- May validation gate na nagre-reject ng malformed submission **bago** mag-grade â
  kailanman ay hindi silent zero (fairness, audit R4-4)

### Sariling parser, hindi `ciscoconfparse2`

Ang core nito ay indentation-based block splitting â mga 150 linya kasama ang banner
handling.

**Dahilan (hindi LOC ang pangunahin):** sabi ng audit sa F-2, ang **semantic
equivalence / normalisation engine** ang *"actual research contribution."* Kung sarili
mo ang parser, magkasama ito at ang normaliser sa iisang kontrol. At sa defense, ang
*"sumulat kami ng parser at normaliser para sa Cisco CLI"* ay mas malakas kaysa
*"tinawag namin ang ciscoconfparse2."*

Pinapaliit ng delimitation (walang BGP, multi-area OSPF, SDN) ang surface na kailangang
i-parse.

---

## 5. Topology Discovery â multi-signal inference

Hindi isang technique. Higit **tatlumpung signal**, pinagsasama sa confidence weighting.

### Mga signal na hindi halata (mula sa running-config)

| Signal | Ano ang sinasabi |
|---|---|
| **Serial DCE clock rate** | Ang `clock rate 64000` ay nasa isang dulo lang. May clock rate + katapat na wala, parehong subnet = kumpirmadong serial pair |
| **PPP CHAP username** | Ang `username R2 password cisco` sa R1 ay literal na pangalan ng katapat |
| **HSRP / VRRP group** | Parehong `standby 1 ip ...` = **kinakailangang** iisang broadcast domain. Hindi inference â physics |
| **Router-on-a-stick** | `encapsulation dot1Q 10` = may trunk papunta sa switch na may VLAN 10 |
| **Port security static MAC** | Literal na MAC ng naka-attach na end device |
| **Duplicate IP** | Walang iisang device ang makakaalam â purong cross-file finding |

### Ang tatlong sumisira sa "hard ceiling" ng R4-2

1. **`show ip interface brief`** â tamang config pero `down/down` = **cabling error o
   missing `no shutdown`.** Ito ang sagot sa *"cabling errors are undetectable."*
2. **`show mac address-table`** â port na may maraming MAC = uplink; isang MAC = end
   device. Klasikong L2 topology algorithm.
3. **`show spanning-tree`** â nagbubunyag ng **blocked ports**, mga link na umiiral pero
   hindi ginagamit. Invisible sa L3 inference.

### Confidence-weighted fusion

```python
SIGNAL_WEIGHT = {
    "cdp_neighbor": 1.00, "ospf_neighbor_full": 0.95, "p2p_subnet_30": 0.90,
    "serial_dce_pair": 0.90, "ppp_chap_username": 0.90, "hsrp_group_match": 0.85,
    "mac_table_uplink": 0.80, "trunk_config_pair": 0.65,
    "shared_subnet_24": 0.35, "description_hint": 0.25,
}

def edge_confidence(signals):
    p = 1.0
    for s in signals:                    # noisy-OR
        p *= (1 - SIGNAL_WEIGHT[s])
    return 1 - p
```

`â¥0.80` verified Â· `0.40â0.79` inferred (dashed) Â· `<0.40` itinatapon pero nila-log.

### Conflict detection â ang pinakamahalagang bahagi

Kapag **hindi** magkasundo ang mga signal, **hindi iyon failure ng system â iyon ang
detected error.** Ito ang sagot sa *"paano kung mali ang inference mo?"*

| Salungatan | Ibig sabihin |
|---|---|
| CDP: konektado, pero magkaibang subnet | IP misconfiguration |
| CDP: konektado, pero `down/down` ang isa | Missing `no shutdown` |
| Subnet tugma, pero walang CDP entry | Hindi talaga naka-kable |
| OSPF configured, pero walang `FULL` neighbor | Area o timer mismatch |

### Multi-layer graph

```
L1 PHYSICAL  : CDP adjacency, interface up/down
L2 DATA LINK : VLAN domains, trunks, STP tree, MAC bindings
L3 NETWORK   : IP subnets, routed adjacency, OSPF peerings
L4 SERVICE   : DHCP, NTP, syslog, AAA
```

---

## 6. Libraries â pinaliit

### Ang natitira

```
fastapi          # kasama na ang Jinja2 + Pydantic
uvicorn          # server
networkx         # KUNG gagawin ang F-11 â tingnan ang open items
ollama           # runtime, hindi pip package
```

Stdlib: `ipaddress`, `csv`, `re`, `json`

### Ano ang tinanggal at bakit

**matplotlib â tinanggal.** ~50MB kasama ang numpy, para sa pagguhit ng bilog at linya
sa 3â10 node. Ang SVG ay text lang:

```python
f'<line class="{cls}" x1="{l.x1}" y1="{l.y1}" x2="{l.x2}" y2="{l.y2}"/>'
f'<circle cx="{n.x}" cy="{n.y}" r="26"/>'
```

**Mas maganda pa ang resulta.** Ang matplotlib ay naglalabas ng magulong path-based SVG
na halos hindi ma-style. Ang hand-written ay may `class` at `data-host` attributes â
kaya mong i-highlight ang error links at gawing interactive gamit ang CSS/JS.

**Layout:** hindi kailangan ng `spring_layout`. Alam mo na ang device role, kaya
**tiered layout** â routers sa taas, switches sa gitna, hosts sa baba. ~8 linya,
deterministic, at mas mukhang totoong network diagram.

**ciscoconfparse2 â tinanggal.** Tingnan ang Â§4.

**WeasyPrint / PDF â tinanggal.** Walang PDF report. On-screen + CSV.

### Presyo ng desisyong ito

Mga **200â250 linya** ng dagdag na code, **3â5 araw**. Kapalit: walang version
breakage sa gitna ng defense season, mas magandang topology rendering, at ang system
ay ginawa mo talaga â hindi glue code sa paligid ng apat na library.

---

## 7. Hosting â local lab server, buong offline

LAN-only (`http://192.168.x.x:8000`). **Walang internet na kailangan kahit kailan.**

Dahil lokal ang feedback model, wala nang anumang external dependency ang sistema.
Sinasara nito nang sabay ang tatlong objection ng audit:

| Objection | Nasosolusyunan |
|---|---|
| RA 10173 â student work papuntang third-party API | Walang lumalabas na data |
| *"a lab where the network may be the thing under test"* | Buong offline |
| API cost, rate limits, model deprecation | Zero recurring cost |

**Ang linya para sa panel:** *"Ang buong pipeline â parsing, topology discovery,
scoring, at feedback generation â ay tumatakbo sa loob ng lab machine. Ang tool ay
gumagana kahit ang network mismo ang bagay na sinusuri."*

**Hardware:** isang lab PC na may 8GB RAM. Ang 3B model na Q4-quantized ay ~2GB,
kayang patakbuhin ng CPU.

---

## Ang AI layer â lokal, at hindi humahawak ng grado

### Ang hangganan (audit R4-1)

```
[1] PARSER           â normalised config model      (deterministic)
[2] NORMALISER       â semantic equivalence         (deterministic)
[3] TOPOLOGY BUILDER â multi-layer graph            (deterministic)
[4] RULE ENGINE      â SCORE + evidence line numbers
                       *** DITO NAGDEDESISYON ANG SCORE. TAPOS. ***
[5] EXPLANATION      â lokal na LLM: wording lang
                       *** HINDI KAYANG BAGUHIN ANG SCORE. ***
```

Sinasagot nito ang tatlong sub-question ng SOP #7 nang magkahiwalay: ang deterministic
rule engine para sa **accuracy** at **consistency of grading**; ang LLM layer para sa
**reliability of generated feedback.**

At sinasagot nito ang apat na objection sa pure-LLM grading: non-determinism,
hallucination, walang audit trail para sa appeals, at data privacy.

### Phase 1 â ngayon: few-shot

Llama 3.2 3B (o Qwen2.5 3B) sa **Ollama**, 15â20 halimbawa sa prompt. Ang input ay
structured JSON mula sa rule engine, hindi raw config:

```json
{"finding": "value_mismatch", "device": "R1", "line": 47,
 "expected": "ip ospf hello-interval 10", "found": "ip ospf hello-interval 30",
 "rubric_item": "OSPF-3", "points_lost": 2}
```

**Fallback:** template-based feedback kapag hindi available ang model. Deterministic,
instant, at maayos naman talaga.

### Phase 2 â nakaplano: fine-tuning

| Bagay | Detalye |
|---|---|
| Method | QLoRA via Unsloth |
| Base | Parehong 3B model |
| Dataset | 300â500 pairs â **ang few-shot examples ang simula nito** |
| Hardware | **Kaggle free tier** (2Ã T4, 30 oras/linggo) |
| Training time | **~30 minuto** (3B, 500 examples, 3 epochs) |
| Inference | Parehong Ollama â walang pagbabago sa app |

**Mahalagang hardware note:** ang **RX 6600 (`gfx1032`) ay hindi magagamit sa training**
â hindi ito nasa official ROCm support list, at CUDA-only ang Unsloth. Kaya **cloud ang
training, lokal ang inference.** Buo pa rin ang offline claim ng deployed system.

**Ang totoong timeline:** ~30 minuto ang training, pero **2â3 linggo ang paggawa ng
dataset.** Hindi GPU ang bottleneck. Kaya few-shot muna â walang nasasayang kasi ang
mga halimbawa ay training data mismo.

### Ang Chapter IV finding na binubuksan nito

Tatlong bersyon ng feedback para sa parehong findings â (a) base model, (b) fine-tuned,
(c) sulat ng instructor â irarate ng mga instructor nang **blind** sa clarity,
correctness, at pedagogical usefulness.

Ito ang **unang aktwal na paraan** para masukat ang *"reliability of generated
feedback"* na RQ. Wala pang ibang mekanismo para doon sa ngayon.

---

## Output â on-screen + CSV

Walang PDF. Ang bawat resulta ay on-screen; ang batch ay CSV via `csv` stdlib.

```python
writer.writerow([student_id, activity, score, missed_count])
```

**Dahilan:** ang problema sa Ch. I ay *"manual checking for large batches."* Kung
on-screen lang at walang maiuuwi, babalik ang mismong problema. Ang CSV ay bubuksan sa
Excel at direktang papasok sa gradebook â walang layout engine, walang bagong
dependency.

---

## Mga bukas pa â kailangang desisyunan

| # | Item | Bakit mahalaga |
|---|---|---|
| O-1 | **Gagawin ba ang F-11** (kumpara sa answer key ng instructor)? | Ito lang ang magdedesisyon kung mananatili ang **networkx**. Sabi ng audit, ito ang *"most demo-friendly artefact you will have"* |
| O-2 | **Papayag ba ang lab sa bundle submission?** | Kung `show running-config` lang, kailangang i-narrow ang claim sa **"Layer-3 adjacency inference"** at ilagay sa Delimitation |
| O-3 | **I-verify ang bawat command sa aktwal na PT version** | Ang ibang switch model ay `show mac-address-table` (may gitling); hindi lahat ay may `show standby brief` o `show etherchannel summary` |
| O-4 | Sino sa group ang may Python web experience? | Nakakaapekto sa timeline |
| O-5 | Ilan ang sabay-sabay na gagamit? | Nakakaapekto sa hardware spec sa Ch. III |

---

## Hindi pa nagagalaw mula sa audit

Ang mga desisyon sa itaas ay sumasagot sa **R4-1** (architecture contradiction),
**R4-2** (topology ceiling), at **R4-3** (input format). Ang mga sumusunod ay bukas pa:

| ID | Finding | Status |
|---|---|---|
| **C-1** | Figure 1 (LLM) vs. Chapter II (rule-based) â magkasalungat | â ï¸ Nasagot na sa arkitektura; **kailangan pang isulat sa paper** |
| **C-2** | Hindi nabanggit ang **Packet Tracer Activity Wizard / Activity Grader** â libre, Cisco-native, nasa loob mismo ng ginagamit na tool | â Bukas. Ito ang *"why does this need to exist?"* sa pinaka-mapanganib na anyo |
| **C-3** | Ang buong problem statement ay nakasandal sa isang pangungusap: *"According to local observations..."* â walang time data, walang grade variance, walang survey | â Bukas. Sabi ng audit, ito ang **highest-value work available** â puwedeng simulan ngayon |
| â | Framework naming: **"IDE"** (line 23) vs **"DIE"** (line 71) vs **"D.I.E."** (criteria.md) | â Madaling ayusin. Piliin ang **D.I.E. â Development, Implementation, Evaluation** |
| â | Scope: sinasabing qualitative pero apat na quantitative ang tanong | â Bukas |
| â | Significance section: mukhang ibang project ang inilalarawan | â Bukas |

**Sagot sa C-2** (may sagot ka, kailangan lang isulat): ang Activity Wizard ay
**exact-match grading** â bumabagsak ito sa mga configuration na *functionally correct
pero magkaibang syntax*. Iyon mismo ang gap na tinutukoy ng Chapter I mo:
*"student configuration outputs that, while functionally correct, may vary in syntax."*
Ang normalisation engine (F-2) ang tugon doon. Wala ring cross-device topology-aware
consistency checking ang Activity Wizard.
