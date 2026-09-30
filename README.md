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

**Instructor Studio only appears on the serving computer.** Students connecting
from other lab computers see *Topology Discovery* and *Student Grading* only.
The Instructor Studio tab is not sent to them at all, and the server refuses
its features (rubric generation, batch grading, class briefing) from any other
machine. There is no password to set up. Just run the tool on the instructor's
own PC, and it works whether you open `http://127.0.0.1:8000/` or the lab
address on that PC.

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
  for the whole class. Only visible on the computer running the server.
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

The **Highest** and **Lowest** cards show who scored it (every name, when
students tie). Click the **Student**, **Score**, **%** or **Grade** column
headings to sort the table; click again to reverse. Scores sort lowest-first,
and files that could not be graded always stay at the bottom.

#### Seeing where a student went wrong

Each row in the table has a **Review** button, labelled with the number of
checkpoints the student missed (for example `🔍 Review (21)`). Clicking it
opens the student's mistakes directly under their row:

- every missed checkpoint, **grouped by device** (R1, R2, SW1, ...), with the
  same feedback, *Found:* value and *How to fix this* guidance the student sees
  in Student Grading;
- their **weakest areas**, ranked by points lost;
- **Show on map**, which draws that student's own topology on the right with
  the devices they got wrong ringed in red;
- **Show passed too**, to see the full checklist rather than only mistakes;
- **Report**, which downloads that one student's grade report as a text file.

**Review all** opens every student at once; **Collapse all** closes them.

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

### Optional: the local AI

Grading never uses AI. A small language model running **on the serving
computer** can add three things on top of a finished grade:

| Feature | Where | Without the model |
|---|---|---|
| "What to study next" paragraph | Student report | Built-in text (badge: *Built-in guidance*) |
| Instructional briefing | Batch Grading | Built-in text (badge: *Built-in analysis*) |
| **Follow-up chat** | Under the student report ("Ask about your results") and under the class briefing ("Ask about this class") | Disabled, with a note explaining why. It never shows a prewritten answer. |

The **AI indicator** in the top bar shows the current state:

- **AI: llama3.2:3b** (purple): the model is running, and the features above are
  written by it.
- **AI: not installed** / **AI: model missing** (amber): built-in text only, and
  chat is off. Hover over it for the reason; click it to check again.

It rechecks every minute, so installing or starting the model is picked up
without restarting the tool.

To enable it, install [Ollama](https://ollama.com) on the serving computer and
download the model once (about 2 GB):

```
ollama pull llama3.2:3b
```

Nothing is installed on student computers. On a typical lab PC's processor, a
3B model takes roughly 10–40 seconds per answer. The tool waits up to 45
seconds, and other students keep working while it waits.

About the follow-up chat:

- A **student** can ask about their own report ("Why did I lose the most
  points?", "Which show commands should I use to check my work?"). The model
  sees their missed checkpoints and is told it cannot change the grade, not to
  invent errors, and not to write out the full fix.
- The **instructor** can ask about the class, including about individual
  students ("Who got the lowest grade?", "Which students struggled with
  OSPF?", "Which topic should I reteach first?"). The model sees the results
  table with **student names** (taken from the submission filenames), scores,
  grades and missed concepts. That is safe because the model runs on this
  computer, nothing is sent anywhere else, and only the instructor's PC can use
  this chat. The student chat and the class briefing never see names.
- The tool works out rankings, ties and who missed what itself, and the model
  only reads the answer off. A small model is unreliable at comparing numbers.
  It can still word an open-ended answer loosely, so check anything that
  matters against the table.

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
