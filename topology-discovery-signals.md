# Topology Discovery — Signal Catalog

**Network Configuration Evaluation and Topology Discovery Tool**
Reference para sa Chapter III (System Design) at sa F-3 cross-device consistency rules

---

## 0. Ang core principle

Ang topology ay hindi larawan — ito ang **unit of correctness**. Ang bawat kawili-wiling
error ng estudyante ay *relational*: umiiral lang ito sa pagitan ng dalawang device.
Ang isang per-file checker ay bulag dito. Kaya ang layunin ng topology module ay hindi
"mag-drawing" — ito ay **magbigay ng relational context para sa rule engine.**

Bawat signal sa ibaba ay sinusukat sa tatlong bagay:

| Dimension | Tanong |
|---|---|
| **Source** | Kailangan ba ng `show running-config` lang, o bundle? |
| **Confidence** | Gaano kasigurado ang link kung ito lang ang ebidensya? |
| **Unlocks** | Anong error class ang nade-detect nito? |

---

## 1. ANG DESISYON NA NAGPAPALAKI SA LAHAT — input bundle

Ang audit (R4-2) ay malinaw: sa `show running-config` lang, **invisible** ang malaking
bahagi ng topology. Walang IP ang access ports. Walang running-config ang mga PC.
Hindi ma-detect ang cabling errors.

**Ipa-submit ang bundle na ito kada device — isang minuto lang na dagdag na effort:**

```
show running-config
show cdp neighbors detail
show ip interface brief
show ip route
show vlan brief            (switches)
show interfaces trunk      (switches)
show mac address-table     (switches)
show spanning-tree         (switches, optional)
```

Naming convention: `ACTIVITY_STUDENTID_DEVICENAME.txt`, o isang ZIP per student.

Ang bundle ang nagpapataas ng ceiling mula sa "L3 adjacency inference" papuntang
**tunay na topology discovery.** Ito ang pinaka-mahalagang technical decision mo.

---

## 2. SIGNAL CATALOG

### TIER A — Mula sa `running-config` lang (L3 at logical)

| # | Signal | Paano gumagana | Conf. | Unlocks |
|---|---|---|---|---|
| A1 | **Subnet co-membership** | Dalawang interface sa parehong network address. `/30` at `/31` = point-to-point by design, mataas ang tiwala. `/24` na may maraming device = mahina, shared segment. | ★★★ (`/30`)<br>★ (`/24`) | Subnet mismatch, wrong mask |
| A2 | **Serial DCE clock rate** | Ang `clock rate 64000` ay nasa DCE end lang ng serial link. Ang interface na may clock rate + ang katapat na walang clock rate sa parehong subnet = kumpirmadong serial pair. | ★★★ | Missing clock rate (klasikong lab error) |
| A3 | **PPP CHAP username** | Sa CHAP, ang `username R2 password cisco` sa R1 ay literal na pangalan ng katapat na device. Direktang deklarasyon ng peer. | ★★★ | Mismatched CHAP credentials |
| A4 | **Static route next-hop** | `ip route 192.168.5.0 255.255.255.0 10.0.0.2` — kung ang `10.0.0.2` ay pag-aari ng isang interface ng ibang device, may logical dependency. | ★★☆ | Next-hop na walang may-ari (F-4) |
| A5 | **HSRP / VRRP / GLBP group** | Dalawang router na may parehong `standby 1 ip 10.0.0.254` ay **kinakailangang** magkasama sa isang broadcast domain. Kumpirmadong L2 adjacency. | ★★★ | Group ID / virtual IP mismatch |
| A6 | **OSPF network + wildcard + area** | Ang `network 10.0.0.0 0.0.0.3 area 0` ay nagdedeklara kung aling interface ang lalahok. Dalawang device na sumasakop sa parehong subnet sa parehong area = adjacency candidate. | ★★☆ | Area mismatch, wildcard na hindi sumasaklaw sa interface |
| A7 | **Tunnel source / destination** | `tunnel destination 203.0.113.5` — eksplisitong logical link sa pagitan ng dalawang endpoint. | ★★★ | Broken tunnel endpoint |
| A8 | **`ip default-gateway` (switch)** | Tumuturo sa IP ng router interface — nag-uugnay sa management VLAN ng switch sa isang router. | ★★☆ | Gateway na walang may-ari |
| A9 | **DHCP pool `default-router`** | Ang pool statement ay nagsasabi kung sino ang gateway ng subnet na iyon. | ★★☆ | Gateway mismatch vs. aktwal na router IP |
| A10 | **`ip helper-address`** | Tumuturo sa DHCP server — logical service edge. | ★★☆ | Helper na tumuturo sa maling host |
| A11 | **Service references** (NTP, syslog, SNMP, TACACS, RADIUS) | Bawat `ntp server X` / `logging host X` ay reference sa IP ng ibang device — service-dependency edges. | ★★☆ | Service pointing sa non-existent host |
| A12 | **Router-on-a-stick subinterfaces** | `interface Gi0/0.10` + `encapsulation dot1Q 10` — nangangahulugang may trunk papunta sa isang switch na may dalang VLAN 10. | ★★★ | Missing VLAN sa switch side, encapsulation mismatch |
| A13 | **SVI (`interface Vlan10`)** | Ang switch ay may L3 presence sa VLAN 10 — nagbibigay ng IP anchor sa isang L2 domain. | ★★★ | SVI sa VLAN na wala sa VLAN database |
| A14 | **Trunk allowed-VLAN list + native VLAN** | Dalawang switch na may magkatugmang trunk config = kandidatong uplink. Ang **hindi** magkatugma ay error. | ★★☆ | Allowed-VLAN mismatch, native VLAN mismatch |
| A15 | **EtherChannel `channel-group`** | Ang mga port sa iisang channel-group ay isang logical bundle; ang katugmang bundle sa katapat = aggregated link. | ★★☆ | Mode mismatch (`active` vs `desirable`) |
| A16 | **VTP domain / mode** | Parehong VTP domain = parehong L2 administrative domain. Ang mode (`server`/`client`/`transparent`) ay nagbibigay ng hierarchy hint. | ★☆☆ | Domain name typo (napaka-karaniwan) |
| A17 | **STP root priority** | `spanning-tree vlan 1 root primary` — nagsasabi kung aling switch ang balak maging root, kaya nabubunyag ang intended hierarchy (core / distribution / access). | ★★☆ | Root bridge sa maling layer |
| A18 | **Port security static MAC** | `switchport port-security mac-address aabb.cc00.0100` — literal na MAC ng naka-attach na end device sa port na iyon. | ★★★ | Maling MAC binding |
| A19 | **Static ARP / static MAC entries** | `arp 10.0.0.5 aabb.cc00.0100 ARPA` at `mac address-table static ... interface fa0/1` — direktang binding ng host sa port. | ★★★ | Stale binding |
| A20 | **NAT inside / outside** | `ip nat inside` at `ip nat outside` ay nagmamarka kung aling router ang nasa gilid ng network — nagbibigay ng orientation sa graph. | ★★☆ | Baligtad na inside/outside (napaka-karaniwan) |
| A21 | **Interface description parsing** | Madalas sumusulat ang estudyante ng `description Link to R2 Gi0/1`. I-parse bilang hint. Mababa ang tiwala pero **libre**, at ang pagkakaroon nito ay gradeable bilang documentation best practice. | ★☆☆ | Description na salungat sa aktwal na link |
| A22 | **ACL subnet references** | Ang mga subnet na binabanggit ng ACL ay nagbubunyag ng mga network na dapat umiiral, kahit hindi direktang konektado. | ★☆☆ | ACL na tumuturo sa hindi umiiral na subnet |
| A23 | **Duplicate IP detection** | Cross-device scan: dalawang device na may parehong IP. Walang iisang device ang makakaalam nito — pure cross-file finding. | ★★★ | Duplicate IP |
| A24 | **Device role inference** | May `switchport` = switch. May `interface Serial` = router na may WIC. May `interface Vlan` + walang routing = L2 switch. | ★★☆ | Maling device type sa topology |

### TIER B — Kailangan ng bundle (dito nagbubukas ang L2 at ang cabling errors)

| # | Signal | Paano gumagana | Conf. | Unlocks |
|---|---|---|---|---|
| B1 | **`show cdp neighbors detail`** | **Ang authoritative source.** Nagbibigay ng: local interface, neighbor device ID, neighbor port, platform, capability code (R/S/H/P), at neighbor IP. Isang linya = isang kumpirmadong pisikal na link. | ★★★★ | Lahat ng missing/extra link |
| B2 | **`show ip interface brief` — status/protocol** | Ito ang **sumisira sa "cabling errors undetectable" ceiling ng R4-2.** Ang `Gi0/0 10.0.0.1 up up` vs `down down` ay nagsasabi kung may aktwal na kable. Tamang config + `down/down` = **cabling error o missing `no shutdown`** — ang pinaka-karaniwang pagkakamali ng estudyante. | ★★★★ | Cabling error, missing `no shutdown`, admin-down |
| B3 | **`show mac address-table`** | Ang port na may **maraming** natutunang MAC ay isang **uplink** papunta sa ibang switch. Ang port na may **isang** MAC ay may naka-attach na end device. Klasikong L2 topology inference (Breitbart et al. approach). | ★★★☆ | Switch-to-switch links, end-host placement |
| B4 | **`show vlan brief`** | Aktwal na VLAN-to-port assignment. Nagbubunyag kung aling access port ang nasa aling VLAN — hindi ito laging kapareho ng running-config kung may VTP. | ★★★ | Port sa maling VLAN |
| B5 | **`show interfaces trunk`** | Operational trunk state: aling VLAN ang *aktwal* na dumadaan, hindi lang kung ano ang naka-configure. Ang "allowed" vs "active" ay magkaibang column. | ★★★ | VLAN na naka-allow pero hindi umiiral |
| B6 | **`show ip route`** | Aktwal na natutunang routes. Ang route na natutunan via OSPF (`O`) ay patunay na **gumagana** ang adjacency, hindi lang naka-configure. | ★★★ | Routing na hindi nag-converge |
| B7 | **`show ip ospf neighbor`** | Direktang listahan ng mga naitatag na OSPF adjacency, kasama ang neighbor router ID, state (dapat `FULL`), at interface. Kung `INIT` o `2WAY` lang — may hello/dead timer o area mismatch. | ★★★★ | OSPF adjacency failure |
| B8 | **`show spanning-tree`** | Nagbubunyag ng aktwal na root bridge, root ports, at **blocked ports**. Ang blocked port ay isang link na **umiiral pero hindi ginagamit** — invisible ito sa L3 inference. | ★★★☆ | Redundant links, maling root bridge |
| B9 | **`show etherchannel summary`** | Aktwal na bundle status — `SU` (in use) vs `SD` (down) vs suspended. | ★★★ | EtherChannel na hindi nag-form |
| B10 | **`show arp`** | IP-to-MAC mapping kada device. I-cross-reference sa B3 para ma-place ang end hosts sa eksaktong switch port. | ★★★ | End-host placement |
| B11 | **`show standby brief`** | Aktwal na HSRP state — sino ang Active, sino ang Standby. | ★★★ | Parehong device Active (split-brain) |
| B12 | **`show version`** | Device model, IOS version, serial number — device fingerprint at capability check. | ★★☆ | Maling device model sa lab |

---

## 3. ANG ENGINE NA NAGSASAMA-SAMA — confidence-weighted edge fusion

Huwag tratuhin ang bawat signal bilang on/off. **Ito ang aktwal na algorithmic
contribution mo,** at ito ang sagot kapag tinanong kung "paano kung magkasalungat ang
mga signal?"

### 3.1 Weighted accumulation

Bawat signal ay nagbibigay ng ebidensya sa isang candidate edge:

```python
SIGNAL_WEIGHT = {
    "cdp_neighbor":      1.00,   # authoritative
    "ospf_neighbor_full":0.95,
    "p2p_subnet_30":     0.90,
    "serial_dce_pair":   0.90,
    "ppp_chap_username": 0.90,
    "hsrp_group_match":  0.85,
    "mac_table_uplink":  0.80,
    "trunk_config_pair": 0.65,
    "shared_subnet_24":  0.35,
    "description_hint":  0.25,
}

def edge_confidence(signals: list[str]) -> float:
    # noisy-OR: maraming mahihinang signal = isang malakas
    p = 1.0
    for s in signals:
        p *= (1 - SIGNAL_WEIGHT[s])
    return 1 - p
```

Threshold: `≥0.80` = **verified** (solid line). `0.40–0.79` = **inferred** (dashed).
`<0.40` = **candidate** (itinatapon, pero nila-log).

### 3.2 Bidirectional verification (mula sa RRL mo)

*"A connection between two nodes is only confirmed when both endpoints agree."*
Kung ang R1 lang ang nagdeklara at hindi ang R2, ang edge ay `unverified` — at
**ito mismo ang finding**, hindi isang bug. Ipakita as red dashed line.

### 3.3 Conflict detection — dito ang tunay na halaga

Kapag **hindi** magkasundo ang mga signal, hindi ito failure ng system —
**ito ang detected error.** Ito ang nagpapatunay na ang topology module ay
hindi dekorasyon:

| Salungatan | Ibig sabihin |
|---|---|
| CDP nagsasabing konektado, pero magkaibang subnet | IP misconfiguration sa isang dulo |
| CDP nagsasabing konektado, pero `down/down` ang isang side | Missing `no shutdown` |
| Subnet nagtutugma, pero walang CDP entry | Hindi talaga naka-kable — parehong subnet lang ng aksidente |
| OSPF configured, pero walang `FULL` neighbor | Area, timer, o authentication mismatch |
| Magkaparehong subnet pero magkaibang mask (`/30` ↔ `/24`) | Mask mismatch |
| Trunk sa isang dulo, access mode sa kabila | Mode mismatch |

### 3.4 Missing-node inference

Kung ang next-hop IP, gateway, o CDP neighbor ay **walang katumbas na device sa
submission**, dalawa lang ang posible — at pareho silang kapaki-pakinabang:

1. May kulang na file ang estudyante → **validation error**, i-flag bago mag-grade
2. Tumuturo ang estudyante sa hindi umiiral na device → **configuration error**

### 3.5 Implicit-switch resolution

Kung tatlo o higit pang device ang nasa parehong `/24` at walang CDP data,
huwag gumuhit ng full mesh — **mag-infer ng hindi-nakikitang switch** sa gitna
at ikonekta lahat dito bilang isang shared segment. Ito ay mas tapat kaysa
gumuhit ng maling adjacency.

---

## 4. MULTI-LAYER GRAPH MODEL

Huwag isang graph — **tatlong overlay** sa iisang node set. Ito ay malinis na
architecture at napaka-demo-friendly (toggle buttons sa UI):

```
Layer 1 — PHYSICAL      : CDP/LLDP adjacency, interface up/down state
Layer 2 — DATA LINK     : VLAN broadcast domains, trunks, STP tree, MAC bindings
Layer 3 — NETWORK       : IP subnets, routed adjacency, routing protocol peerings
Layer 4 — SERVICE (opt.): DHCP, NTP, syslog, AAA dependencies
```

Sa NetworkX, isang `MultiGraph` na may `layer` attribute kada edge — o tatlong
magkahiwalay na graph object na may parehong node keys.

**Bakit malakas ito sa defense:** ang bawat layer ay may sariling error class.
Ang L2 mismatch ay hindi L3 problem. Ipinapakita nito na naiintindihan mo ang
OSI model, hindi lang basta gumuguhit ng linya.

---

## 5. GRAPH-ALGORITHM LAYER (NetworkX)

Kapag nabuo na ang graph, ito ang mga analysis na maipapatong mo:

| Analysis | NetworkX | Ano ang nakikita |
|---|---|---|
| **Connected components** | `nx.connected_components()` | Nakahiwalay na device o "island" — isang buong segment na hindi naabot |
| **Reference comparison** (F-11) | `nx.is_isomorphic()`, `GraphMatcher` | Missing links, extra links, misassigned interfaces vs. answer key ng instructor |
| **Reachability analysis** (F-4) | `nx.has_path()` sa L3 layer + simulated routing table | "Kaya bang maabot ng PC-A ang PC-B?" — at kung hindi, aling statement ang kulang |
| **Redundancy check** | `nx.edge_connectivity()` | May single point of failure ba? Nagawa ba ang required redundant path? |
| **Role inference** | `nx.degree_centrality()` | Mataas na degree = core/distribution; leaf na may isang uplink = access switch |
| **Cycle detection** | `nx.cycle_basis()` | Physical loops — dapat may STP na humaharang; kung wala, broadcast storm risk |
| **Shortest path vs. actual route** | `nx.shortest_path()` vs `show ip route` | Suboptimal routing, maling metric/cost |

---

## 6. ANO ANG I-BUILD — priority order

**Kailangan para sa defense (Tier 1):**

1. Input bundle collection (§1) — ito ang nag-a-unlock ng lahat
2. A1 subnet matching + A2 serial DCE + B1 CDP + B2 interface status
3. Confidence-weighted fusion (§3.1) + bidirectional verification (§3.2)
4. **Conflict detection (§3.3)** — ito ang nagpapatunay na hindi dekorasyon ang topology
5. Cross-device consistency rules (audit F-3) na nakatayo sa graph

**Malalakas na differentiator (Tier 2):**

6. A5 HSRP, A12 router-on-a-stick, A14 trunk/native VLAN, A23 duplicate IP
7. B3 MAC-table L2 inference + B8 STP blocked ports
8. Multi-layer graph model (§4)
9. Reference-topology comparison (F-11) — ang pinaka-madaling i-demo

**Kung may oras pa (Tier 3):**

10. A3 PPP CHAP username, A18/A19 MAC bindings, A20 NAT orientation
11. Service-dependency layer (A9–A11)
12. Redundancy at cycle analysis

---

## 7. ANG LINE MO SA DEFENSE

Kapag sinabi ng panelist na *"topology discovery is useless — bakit hindi na lang SSH
troubleshooting?"*:

> "Ang topology ay hindi ang output — ito ang **precondition**. Kalahati ng mga
> pagkakamali ng estudyante ay hindi ma-detect sa pagbabasa ng isang configuration
> file, dahil ang error ay nasa **pagitan** ng dalawang file. Bumubuo kami ng graph
> mula sa labindalawang magkakaibang signal — CDP, subnet arithmetic, HSRP groups,
> serial clock rates, trunk configuration, at MAC forwarding tables — at pinagsasama
> ang mga ito gamit ang confidence weighting. Kapag **nagkasalungat** ang mga signal,
> hindi iyon failure ng system: **iyon ang na-detect na error.**"

Tapos i-demo ang subnet mismatch nang live. Siyamnapung segundo, sarado ang objection.
