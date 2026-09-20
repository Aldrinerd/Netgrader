# Network Configuration Evaluation & Topology Discovery Tool

Automated, offline grading of Cisco Packet Tracer lab work for the
Cisco Networking Academy lab at First City Providential College.

An instructor uploads their own finished `.pkt` file, chooses how strict the
grading should be, and gets an `instructions.txt` rubric. Students upload their
attempt and get an itemised score with per-rule feedback. **Every score is
computed by deterministic rules — there is no AI in the grading path.**

---

## Running it on a school computer

### What you need

| | |
|---|---|
| **Python 3.10 or newer** | Check by double-clicking `start_server.py` — it will tell you if the version is too old. |
| **Administrator rights** | Not needed to run the tool. Needed only once, and only for lab sharing (see below). |
| **Command Prompt** | Not needed. The launcher runs through Python, not `cmd.exe`. |
| **Internet** | Not needed. Fonts and the Packet Tracer decoder are bundled. |

### Start it

**Double-click `start_server.py`.**

The launcher will check everything, install any missing Python packages into
your own user folder (no administrator rights required), pick a port that is
actually free, and open your browser.

It then asks one question:

```
  How should this run?
    [1] This computer only            (default)
    [2] Share with the lab network    (students open it in a browser)
```

### Option 1 — This computer only

Everything stays on the machine you started it on, at `http://127.0.0.1:8000/`.
Use this when the tool is installed on each computer individually, or when
you are just marking papers at your own desk.

### Option 2 — Share with the lab network

The tool is served to the whole lab from **one** computer. The launcher prints
the address students should type:

```
  On this computer : http://127.0.0.1:8000/
  For the lab      : http://192.168.1.2:8000/
```

Students type that second address into any browser. **Nothing is installed on
student computers.**

The first time you do this, Windows shows a
*"Allow this app to communicate on these networks?"* prompt.
Choose **Allow**. That prompt needs an administrator **once, on the serving
computer only** — if nobody can accept it, student machines will not be able
to connect.

> Some school networks also isolate computers from each other at the switch or
> access point. If the firewall is allowed and students still cannot connect,
> ask IT whether client isolation is enabled on the lab network.

### If something goes wrong

Double-click `start_server.py`, or run it with `--check`, to get a report:

```bash
python start_server.py --check
```

```
  Python           : 3.12.9
  Packages         : all present
  templates        : found
  .pkt/.pka upload : ready
  Free port        : 8000
  This computer IP : 192.168.1.2

  RESULT: ready to start.
```

### All launcher options

```bash
python start_server.py              # ask, then start
python start_server.py --local      # this computer only, no questions
python start_server.py --lan        # share with the lab, no questions
python start_server.py --port 8080  # prefer a specific port
python start_server.py --check      # diagnostics only
python start_server.py --no-browser # do not open a browser
python start_server.py --install    # install missing packages without asking
```

If the preferred port is busy, the launcher automatically moves to the next
free one and tells you which it used.

---

## No internet in the lab?

On a computer that **does** have internet, download the packages once:

```bash
python -m pip download -r requirements.txt -d vendor/wheels
```

Copy the whole project folder (including `vendor/wheels`) to the lab computer.
The launcher detects that folder and installs from it without touching the
internet.

---

## How it works

```
Upload (.pkt / .pka / .xml / .zip / .txt)
   |
   |-- binary .pkt --> pka2xml decrypt --> XML
   |     `-- src/pkt_parser.py    ground-truth cabling, cable types,
   |                              canvas positions, PC/laptop profiles
   `-- text bundle --> src/sanitizer.py --> src/parsers.py
                                  running-config, CDP, ip int brief,
                                  ip route, vlan brief, trunk, MAC table
                          |
              src/fusion_engine.py      7 signals combined by Noisy-OR
                                        into confidence-scored links
                          |
           src/conflict_detector.py     subnet mismatch, interfaces down,
                                        duplicate IPs, native VLAN mismatch,
                                        wrong cable type -- with line citations
                          |
        +-----------------+------------------+
        |                                    |
 src/criteria_generator.py            src/evaluator.py
 instructor -> instructions.txt       student -> scored report
```

### The three screens

- **Topology Discovery** — visualise any upload as a topology map with
  confidence-rated links and an evidence drawer citing exact config lines.
- **Instructor Studio** — generate a rubric from your reference file, with
  nine policy switches controlling grading strictness, plus **batch grading**
  for the whole class.
- **Student Grading** — upload `instructions.txt` plus your attempt, get a
  scorecard.

### Grading a whole class

In **Instructor Studio**, scroll to *Batch Grading & Gradebook Export*:

1. Choose the `instructions.txt` you generated for the lab.
2. Select every student submission at once. **One file per student** — the
   filename becomes the student's name, so `Dela Cruz, Juan.pkt` is graded as
   *Dela Cruz, Juan*.
3. Click **Grade All Submissions**.

You get a class average, the highest and lowest scores, a per-student table,
and a **Download Gradebook CSV** button. The CSV opens directly in Excel and
includes each student's score, percentage, letter grade, and the list of
checkpoints they missed.

A submission that fails to parse is listed as an error row and the rest of the
class still grades — one corrupt file cannot cost you the whole batch.

### The policy switches

These are what separate this tool from Packet Tracer's own Activity Wizard,
which only does exact-match grading. With the right switches on, a student who
designs a **completely different but correct** addressing scheme still scores
100%.

| Switch | Effect when enabled |
|---|---|
| `allow_dynamic_subnetting` | Verifies that link endpoints are mutually in one subnet, that IPs are unique, and that subnets are not reused — instead of matching a fixed IP string. |
| `enforce_prefix_length` | The student's own subnet must still use the required prefix (`/30` on point-to-point, `/24` on LANs). |
| `verify_default_gateways` | PCs and switches must have a gateway inside the connected router's subnet. |
| `allow_custom_hostnames` | Devices are matched by type and topological role, not by name. |
| `strict_port_matching` | When off, any interface of the same speed class is accepted. |
| `strict_cable_type` | When off, Auto-MDIX copper equivalence is tolerated (straight-through vs crossover). |
| `allow_flexible_process_ids` | Ignores locally-significant OSPF process IDs; checks areas and networks instead. |
| `grade_security_baseline` | Checks `enable secret`, `service password-encryption`, and `line vty` login. |
| `grade_interface_descriptions` | Checks that interface descriptions name the correct peer. |

---

## For developers

```bash
python -m pip install --user -r requirements-dev.txt
python -m pytest -q
```

| File | Purpose |
|---|---|
| `requirements.txt` | Core runtime. All a lab computer needs. |
| `requirements-dev.txt` | Adds pytest and HTTP clients for the test suite. |
| `requirements-collector.txt` | GUI-automation extras for `scripts/pt_collector.py` only. Do not install on lab computers. |

`tests/test_e2e_live_server.py` starts its own server on a free port, so the
test suite needs nothing running beforehand.

### Bundled third-party code

`cisco-pka-to-xml/` is a vendored copy of
[jeamxn/cisco-pka-to-xml](https://github.com/jeamxn/cisco-pka-to-xml) (MIT),
which decrypts `.pkt` / `.pka` files. It is vendored rather than installed so
that a lab computer with no internet access still has working Packet Tracer
support. `libtwofish.dll` ships prebuilt — no C compiler is required on Windows.

If `.pkt` upload ever reports as unavailable, `.txt` / `.zip` config bundle
upload continues to work.
