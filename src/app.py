# src/app.py
import csv
import io
import os
import zipfile
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.conflict_detector import detect_conflicts
from src.criteria_generator import (
    format_criteria_to_instructions_txt,
    generate_criteria_from_topology,
    parse_instructions_txt,
)
from src.evaluator import evaluate_student_submission
from src.fusion_engine import infer_topology_links
from src.models import (
    DiscoveredLink,
    EvaluationReport,
    ParsedDevice,
    TopologyResult,
)
from src.parsers import parse_device_bundle
from src.pkt_parser import parse_pkt_file

app = FastAPI(
    title="Network Configuration Evaluation & Topology Discovery Tool",
    description="Multi-signal network topology discovery, criteria generation, and automated student lab evaluation engine",
    version="2.0.0"
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "css"), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "js"), exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def process_bundle_dict(files_dict: dict[str, str]) -> TopologyResult:
    """Parses a dictionary of {filename: text_content} into a TopologyResult."""
    if not files_dict:
        return TopologyResult(devices={}, links=[], conflicts=[])
    
    parsed_devices = {}
    for filename, content in files_dict.items():
        if content.strip():
            dev = parse_device_bundle(content, filename)
            parsed_devices[dev.hostname] = dev
            
    discovered_links = infer_topology_links(parsed_devices)
    detected_conflicts = detect_conflicts(parsed_devices, discovered_links)
    
    return TopologyResult(
        devices=parsed_devices,
        links=discovered_links,
        conflicts=detected_conflicts
    )


async def parse_uploaded_files_to_topology(files: list[UploadFile]) -> TopologyResult:
    """Helper that parses a list of UploadFile objects (.pkt, .xml, .zip, .txt) into a TopologyResult."""
    files_dict: dict[str, str] = {}
    pkt_files: list[tuple[str, bytes]] = []

    for upload in files:
        filename = upload.filename or "unknown.txt"
        contents = await upload.read()
        lower_name = filename.lower()

        # Check for Packet Tracer file formats (.pkt, .pka, .xml)
        if lower_name.endswith((".pkt", ".pka", ".xml")):
            pkt_files.append((filename, contents))
            continue

        # If ZIP file, extract and inspect contents
        if lower_name.endswith(".zip"):
            try:
                with zipfile.ZipFile(io.BytesIO(contents)) as z:
                    for z_name in z.namelist():
                        if not z_name.endswith("/") and not z_name.startswith("__MACOSX"):
                            with z.open(z_name) as z_file:
                                z_bytes = z_file.read()
                                if z_name.lower().endswith((".pkt", ".pka", ".xml")):
                                    pkt_files.append((os.path.basename(z_name), z_bytes))
                                else:
                                    files_dict[os.path.basename(z_name)] = z_bytes.decode("utf-8", errors="replace")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to extract zip file {filename}: {str(e)}")
        else:
            files_dict[filename] = contents.decode("utf-8", errors="replace")

    # If Packet Tracer files uploaded, parse them
    if pkt_files:
        all_devices: dict[str, ParsedDevice] = {}
        all_links: list[DiscoveredLink] = []

        for fname, fbytes in pkt_files:
            try:
                devs, lnks = parse_pkt_file(fbytes, filename=fname)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error parsing Packet Tracer file '{fname}': {e}")

            # A file that decrypts and parses but contains no devices is almost
            # always a Packet Tracer version this decoder does not understand.
            # Reporting that beats handing back a silent empty topology.
            if not devs:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"'{fname}' was read successfully, but no devices could be extracted from it "
                        f"({len(fbytes):,} bytes). This usually means the file was saved by a newer "
                        "Packet Tracer version than this tool supports. Try 'File > Save As' in Packet "
                        "Tracer, or upload a .zip of each device's 'show running-config' output instead."
                    ),
                )

            all_devices.update(devs)
            all_links.extend(lnks)

        # If supplementary text files were also included, parse and merge them
        if files_dict:
            for fname, content in files_dict.items():
                if content.strip():
                    dev = parse_device_bundle(content, fname)
                    if dev.hostname not in all_devices:
                        all_devices[dev.hostname] = dev
                    else:
                        all_devices[dev.hostname].interfaces.update(dev.interfaces)

        detected_conflicts = detect_conflicts(all_devices, all_links)
        return TopologyResult(
            devices=all_devices,
            links=all_links,
            conflicts=detected_conflicts
        )

    # Otherwise fallback to standard text bundle processor
    return process_bundle_dict(files_dict)


def _asset_version() -> str:
    """
    Cache-busting token derived from the static assets themselves.

    The template used to hard-code "?v=3.2", so browsers kept serving a stale
    app.js after the tool was updated -- meaning an instructor could deploy a
    fix and students would never receive it. Deriving the token from file
    modification times makes every edit reach the browser automatically.
    """
    newest = 0.0
    for folder in (os.path.join(STATIC_DIR, "css"), os.path.join(STATIC_DIR, "js")):
        if not os.path.isdir(folder):
            continue
        for name in os.listdir(folder):
            try:
                newest = max(newest, os.path.getmtime(os.path.join(folder, name)))
            except OSError:
                continue
    return str(int(newest))


@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"asset_version": _asset_version()},
    )




@app.post("/api/analyze", response_model=TopologyResult)
async def api_analyze_upload(files: list[UploadFile] = File(...)):
    return await parse_uploaded_files_to_topology(files)


# --- Teacher Mode: Criteria & Instructions Generator Endpoints ---

@app.post("/api/criteria/generate")
async def api_generate_criteria(
    files: list[UploadFile] = File(...),
    lab_title: str = Form("Packet Tracer Lab Assignment"),
    lab_description: str = Form(""),
    total_points: float = Form(100.0),
    allow_dynamic_subnetting: bool = Form(False),
    enforce_prefix_length: bool = Form(True),
    verify_default_gateways: bool = Form(True),
    allow_custom_hostnames: bool = Form(False),
    strict_port_matching: bool = Form(True),
    strict_cable_type: bool = Form(True),
    allow_flexible_process_ids: bool = Form(True),
    grade_security_baseline: bool = Form(False),
    grade_interface_descriptions: bool = Form(False)
):
    """
    Teacher Studio: Ingests an instructor's reference Packet Tracer file (.pkt/.xml)
    or gold-standard configuration bundle, extracts grading rules, and generates instructions.txt.
    """
    topology = await parse_uploaded_files_to_topology(files)
    if not topology.devices:
        raise HTTPException(status_code=400, detail="No valid device configurations or topology discovered from reference file.")

    from src.models import EvaluationPolicies
    policies = EvaluationPolicies(
        allow_dynamic_subnetting=allow_dynamic_subnetting,
        enforce_prefix_length=enforce_prefix_length,
        verify_default_gateways=verify_default_gateways,
        allow_custom_hostnames=allow_custom_hostnames,
        strict_port_matching=strict_port_matching,
        strict_cable_type=strict_cable_type,
        allow_flexible_process_ids=allow_flexible_process_ids,
        grade_security_baseline=grade_security_baseline,
        grade_interface_descriptions=grade_interface_descriptions
    )

    criteria = generate_criteria_from_topology(
        topology=topology,
        lab_title=lab_title,
        lab_description=lab_description,
        target_total_points=total_points,
        policies=policies
    )
    # Guard against a reference file that parses but carries nothing gradeable.
    # A plain text file produces one device named after the filename and a
    # single "this device must exist" rule -- a rubric that looks valid and is
    # worthless. Better to refuse it than to let an instructor hand it out.
    gradeable_rules = [r for r in criteria.rules if r.category != "device"]
    if not gradeable_rules:
        device_names = ", ".join(sorted(topology.devices)) or "none"
        raise HTTPException(
            status_code=400,
            detail=(
                "This reference file contains nothing that can be graded. "
                f"Devices found: {device_names}. No IP addressing, switchport, "
                "cabling or routing configuration was detected. "
                "Upload a saved Packet Tracer file (.pkt/.pka/.xml), or a .zip/.txt "
                "bundle of 'show running-config' output from each device."
            ),
        )

    instructions_txt = format_criteria_to_instructions_txt(criteria)

    return {
        "criteria": criteria,
        "instructions_txt": instructions_txt,
        "topology": topology
    }


@app.post("/api/criteria/parse")
async def api_parse_criteria(instructions_file: UploadFile = File(...)):
    """
    Parses a student-provided instructions.txt or criteria file to extract rubric specification.
    """
    content_bytes = await instructions_file.read()
    content = content_bytes.decode("utf-8", errors="replace")
    try:
        criteria = parse_instructions_txt(content)
        return {
            "criteria": criteria,
            "raw_text": content
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Student Mode: Automated Evaluation Endpoint ---

@app.post("/api/evaluate", response_model=EvaluationReport)
async def api_evaluate_student_submission(
    instructions_file: UploadFile = File(...),
    student_files: list[UploadFile] = File(...)
):
    """
    Student Portal: Evaluates student's Packet Tracer file or configuration files against
    the instructor's instructions.txt / criteria rubric.
    """
    # 1. Parse instructions.txt
    inst_bytes = await instructions_file.read()
    inst_content = inst_bytes.decode("utf-8", errors="replace")
    try:
        criteria = parse_instructions_txt(inst_content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid Instructions File: {str(e)}")

    # 2. Parse student submission
    student_topology = await parse_uploaded_files_to_topology(student_files)
    if not student_topology.devices:
        raise HTTPException(status_code=400, detail="No device configurations or topology found in student submission files.")

    # 3. Run automated grading
    report = evaluate_student_submission(criteria, student_topology)
    return report


# --- Instructor Mode: Batch Grading & Gradebook Export ---

def _student_name_from_filename(filename: str) -> str:
    """
    Derive a student identifier from an uploaded filename.

    'Dela Cruz, Juan.pkt'      -> 'Dela Cruz, Juan'
    'lab3_2021-00123.zip'      -> 'lab3_2021-00123'
    """
    base = os.path.basename(filename or "submission")
    stem, _, _ = base.rpartition(".")
    return (stem or base).strip() or base


def _build_gradebook_csv(lab_title: str, rows: list[dict]) -> str:
    """
    Render batch results as CSV for direct import into a gradebook spreadsheet.

    Chapter I frames the problem as manual checking of large batches, so results
    have to leave the screen in a form Excel opens without any conversion step.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow([
        "Student", "Lab", "Score", "Max Score", "Percentage", "Grade",
        "Checkpoints Passed", "Checkpoints Failed", "Missed Checkpoints", "Status",
    ])
    for row in rows:
        writer.writerow([
            row["student"],
            lab_title,
            row.get("total_score", ""),
            row.get("max_score", ""),
            row.get("percentage", ""),
            row.get("grade_letter", ""),
            row.get("passed_count", ""),
            row.get("failed_count", ""),
            "; ".join(row.get("missed", [])),
            row.get("status", "graded"),
        ])
    return buffer.getvalue()


@app.post("/api/evaluate/batch")
async def api_evaluate_batch(
    instructions_file: UploadFile = File(...),
    student_files: list[UploadFile] = File(...)
):
    """
    Instructor batch grading: grade a whole class against one rubric in a single
    pass and return both a per-student summary and a gradebook-ready CSV.

    Each uploaded file is treated as ONE student's submission. A submission that
    fails to parse is recorded as an error row rather than aborting the batch,
    so one corrupt file cannot cost an instructor the entire run.
    """
    inst_bytes = await instructions_file.read()
    inst_content = inst_bytes.decode("utf-8", errors="replace")
    try:
        criteria = parse_instructions_txt(inst_content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid Instructions File: {str(e)}")

    if not student_files:
        raise HTTPException(status_code=400, detail="No student submissions were uploaded.")

    rows: list[dict] = []
    for upload in student_files:
        student = _student_name_from_filename(upload.filename or "")
        try:
            topology = await parse_uploaded_files_to_topology([upload])
            if not topology.devices:
                raise ValueError("No device configurations or topology found in this submission.")
            report = evaluate_student_submission(criteria, topology)
            rows.append({
                "student": student,
                "filename": upload.filename,
                "total_score": round(report.total_score, 1),
                "max_score": round(report.max_score, 1),
                "percentage": report.percentage,
                "grade_letter": report.grade_letter,
                "passed_count": report.passed_count,
                "failed_count": report.failed_count,
                "missed": [r.description for r in report.results if not r.passed],
                # Categories only -- feeds the class briefing without exposing
                # any configuration text or identifying detail.
                "failed_categories": sorted({r.category for r in report.results if not r.passed}),
                "status": "graded",
            })
        except Exception as e:
            rows.append({
                "student": student,
                "filename": upload.filename,
                "total_score": 0.0,
                "max_score": round(sum(r.points for r in criteria.rules), 1),
                "percentage": 0.0,
                "grade_letter": "-",
                "passed_count": 0,
                "failed_count": len(criteria.rules),
                "missed": [],
                "failed_categories": [],
                "status": f"ERROR: {e}",
            })

    graded = [r for r in rows if r["status"] == "graded"]
    percentages = [r["percentage"] for r in graded]
    summary = {
        "submissions": len(rows),
        "graded": len(graded),
        "errors": len(rows) - len(graded),
        "average_percentage": round(sum(percentages) / len(percentages), 1) if percentages else 0.0,
        "highest_percentage": max(percentages) if percentages else 0.0,
        "lowest_percentage": min(percentages) if percentages else 0.0,
    }

    return {
        "lab_title": criteria.lab_title,
        "summary": summary,
        "results": rows,
        "csv": _build_gradebook_csv(criteria.lab_title, rows),
    }


# --- Narrative Layer (Phase B): the only endpoints that touch a model ---

@app.get("/api/llm/status")
async def api_llm_status():
    """
    Report whether the local model layer is usable.

    Lets the UI say "model ready" or "using built-in guidance" honestly,
    instead of silently implying an AI wrote text that a template produced.
    """
    from src import llm
    return llm.status()


@app.post("/api/report/narrative")
async def api_report_narrative(report: EvaluationReport):
    """
    Produce one "what to study next" paragraph for a graded report.

    Deliberately a SEPARATE request from /api/evaluate. The student's score is
    computed, returned and rendered before this is ever called, which makes
    "the model cannot affect the grade" a property of the request flow and not
    just a claim in the architecture document.
    """
    from src.narrative import student_summary
    return student_summary(report)


@app.post("/api/class/briefing")
async def api_class_briefing(payload: dict):
    """
    Instructor briefing for a whole class (Statement of the Problem #4).

    Expects {"categories_per_student": [["interface_ip", "routing"], ...]} --
    failed rule categories only. No student names, no configuration text and
    no scores are accepted or needed, which keeps the aggregate compliant with
    R.A. 10173.
    """
    from src.narrative import class_briefing

    categories = payload.get("categories_per_student")
    if not isinstance(categories, list) or not categories:
        raise HTTPException(
            status_code=400,
            detail="Provide 'categories_per_student': a list of failed rule categories per submission.",
        )
    cleaned = [
        [str(c) for c in entry if isinstance(c, str)]
        for entry in categories
        if isinstance(entry, list)
    ]
    if not cleaned:
        raise HTTPException(status_code=400, detail="No usable submission entries were provided.")
    return class_briefing(cleaned)
