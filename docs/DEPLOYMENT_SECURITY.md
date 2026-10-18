# Deployment Security Brief

*For the school IT office. It covers what the tool needs on one instructor PC
per lab room, what data it handles, and how you can verify each claim yourself.*

Every claim below links to the code, test or command that backs it. Items
marked **(planned)** are not built yet; each links to its tracking issue.

## 1. Architecture and data flow

```
 Student PC (browser only)          Instructor PC                       Same PC, loopback only
 ─────────────────────────          ───────────────────────────         ──────────────────────
 http://<instructor-ip>:8000  ───▶  start_server.py → FastAPI app  ───▶ Ollama 127.0.0.1:11434
   uploads .pkt / .txt                parse → grade → feedback             local llama3.2:3b
   reads results, asks chat           (all in memory)                      (no internet)
```

- **Student PCs need nothing installed.** They only open a browser.
- **One process to approve**, started by the instructor with
  `python start_server.py --lan`. It binds to `0.0.0.0` only in `--lan`
  mode, and to `127.0.0.1` otherwise
  ([start_server.py:268](../start_server.py#L268)).
- **The AI model is local.** The app only calls `http://127.0.0.1:11434`
  ([src/llm.py:32](../src/llm.py#L32)). Grading itself never uses the model
  ([SYSTEM.md §7](SYSTEM.md#7-the-ai-boundary)).
- **No database, and nothing written to disk.** Uploads are read into memory,
  graded and discarded. `src/` opens no files for writing and creates no
  temp files. To check, run `findstr /s /n "open( tempfile" src\*.py`: the only
  hits are a ZIP read in memory and the loopback model calls. The gradebook CSV
  is built in memory and downloaded by the browser
  ([src/app.py `_build_gradebook_csv`](../src/app.py)).
- **No internet connection is used at run time.**

## 2. What IT must allow (instructor PC only)

| Item | Detail |
|---|---|
| Python 3.10 or newer | Runs `start_server.py`. A packaged `.exe` for labs that block Python is **(planned, [#47](https://github.com/Aldrinerd/Netgrader/issues/47))**. |
| One inbound firewall rule | TCP on the tool's port, limited to the lab subnet. Start with `--port 8000` so the port does not change; the launcher otherwise moves to the next free port ([start_server.py:269](../start_server.py#L269)). |
| Ollama | Installed and bound to loopback (Ollama's default `OLLAMA_HOST=127.0.0.1:11434`). Optional: without it, grading and feedback still work and the chat says it is unavailable. |
| No outbound internet | Install the dependencies once from `requirements.txt`. An offline wheel folder is **(planned)**. |

The firewall rule to review (adjust the subnet and the path to `python.exe`):

```powershell
New-NetFirewallRule -DisplayName "NetGrader lab (TCP 8000)" -Direction Inbound `
  -Protocol TCP -LocalPort 8000 -RemoteAddress 192.168.10.0/24 `
  -Profile Domain,Private -Action Allow `
  -Program "C:\Program Files\Python312\python.exe"
```

## 3. Data handled

- **Student files** are processed in memory and discarded when the request
  ends. Nothing is kept between requests.
- **Student names** come only from batch-upload filenames. They reach the AI
  model only in the instructor-only class chat, which runs on this PC
  ([src/app.py `api_chat_class`](../src/app.py), anonymity tested in
  [tests/test_chat.py](../tests/test_chat.py)). The student chat and the class
  briefing carry no names.
- **R.A. 10173 (Data Privacy Act).** Nothing is sent to a third party, nothing
  is stored, and processing is limited to grading the lab
  ([SYSTEM.md §7](SYSTEM.md#7-the-ai-boundary)).

## 4. Access model

- **The instructor is whoever is at the serving PC.** The check is a loopback
  address or the server's own address ([src/app.py:197](../src/app.py#L197)).
  A lab PC cannot fake it: its packets carry its own IP.
- **Instructor routes return `403` to every other machine**
  ([src/app.py:228](../src/app.py#L228); tested in
  [tests/test_instructor_access.py](../tests/test_instructor_access.py)).
- **Student chat safeguards.** Questions are screened before the model is
  called, forged report text and forged history are rejected by a server-side
  signature, and long configuration blocks are cut from replies
  ([src/chat_guard.py](../src/chat_guard.py), [src/integrity.py](../src/integrity.py);
  red-team tests in [tests/test_chat_safeguards.py](../tests/test_chat_safeguards.py)).
- A subnet allowlist as a second layer behind the firewall is **(planned,
  [#43](https://github.com/Aldrinerd/Netgrader/issues/43))**.

## 5. Known trade-offs, stated up front

- **Plain HTTP** on the closed lab LAN. HTTPS is **(planned,
  [#26](https://github.com/Aldrinerd/Netgrader/issues/26))**, once logins exist.
- **Anyone at the instructor PC counts as the instructor.** Lock the screen
  whenever the PC is unattended.
- **Students can edit `instructions.txt`** to change their own self-check
  grade until rubrics are held on the server
  ([#8](https://github.com/Aldrinerd/Netgrader/issues/8)). Batch grading by the
  instructor uses the instructor's own copy, so recorded grades are unaffected.
- **API docs pages** (`/docs`, `/redoc`, `/openapi.json`) are still served.
  Turning them off for lab use is **(planned,
  [#42](https://github.com/Aldrinerd/Netgrader/issues/42))**.
- **No rate limit on the chat yet** ([#20](https://github.com/Aldrinerd/Netgrader/issues/20)).
  The model only runs on the instructor PC, so the cost of abuse is a slow
  chat, not data exposure.
- **The `.pkt` format is reverse-engineered.** Decryption uses a vendored
  Twofish library ([cisco-pka-to-xml/VENDORED.md](../cisco-pka-to-xml/VENDORED.md)).
  Published SHA-256 hashes for the DLL are **(planned,
  [#45](https://github.com/Aldrinerd/Netgrader/issues/45))**.

## 6. How IT can verify this themselves

| Check | Expected result |
|---|---|
| `netstat -ano \| findstr "8000 11434"` while running | `8000` on `0.0.0.0` (lan mode) or `127.0.0.1`; `11434` on `127.0.0.1` **only** |
| Block outbound internet on the PC, then grade a lab and use the chat | Everything still works |
| From a student PC, open `http://<ip>:8000/` and try Instructor Studio | The tab is absent; its API calls return `403` |
| `python -m pytest -q` | All tests pass (also run on every push, see [.github/workflows/ci.yml](../.github/workflows/ci.yml)) |
| `python -m validation` | Grading-accuracy harness: 100% recall and specificity |
| `pip install pip-audit` then `pip-audit -r requirements.txt` | No known-vulnerable dependencies |
| `python start_server.py --check` | Dependency and Packet Tracer support diagnostics |
| `python start_server.py --security-report` | **(planned, [#44](https://github.com/Aldrinerd/Netgrader/issues/44))** one-page report of the above |
| `SHA256SUMS.txt` for releases | **(planned, [#45](https://github.com/Aldrinerd/Netgrader/issues/45))** |

## 7. Pilot proposal

- **One lab room**, with the firewall rule limited to that room's subnet.
- **A fixed period**, for example four weeks, after which the rule is
  removed unless renewed.
- **Review at the end.** An access log for that review is **(planned,
  [#28](https://github.com/Aldrinerd/Netgrader/issues/28))**. Until it
  exists, the launcher logs warnings and errors only
  ([start_server.py:308](../start_server.py#L308)), so the pilot review relies on
  the instructor's account and the Windows Firewall log for the rule.
