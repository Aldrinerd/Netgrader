# src/app.py
import io
import os
import zipfile
from typing import Annotated
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.conflict_detector import detect_conflicts
from src.fusion_engine import infer_topology_links
from src.models import DiscoveredLink, ParsedDevice, TopologyResult
from src.parsers import parse_device_bundle
from src.pkt_parser import parse_pkt_file
from src.presets import get_available_presets, load_preset

app = FastAPI(
    title="Network Configuration Evaluation & Topology Discovery Tool",
    description="Multi-signal network topology discovery and relational configuration validator",
    version="1.0.0"
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

@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    presets = get_available_presets()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"presets": presets}
    )

@app.get("/api/presets")
async def api_get_presets():
    return get_available_presets()

@app.get("/api/presets/{preset_id}", response_model=TopologyResult)
async def api_load_preset(preset_id: str):
    try:
        files_dict = load_preset(preset_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    return process_bundle_dict(files_dict)

@app.post("/api/analyze", response_model=TopologyResult)
async def api_analyze_upload(files: list[UploadFile] = File(...)):
    files_dict: dict[str, str] = {}
    pkt_files: list[tuple[str, bytes]] = []

    for upload in files:
        filename = upload.filename or "unknown.txt"
        contents = await upload.read()
        lower_name = filename.lower()

        # Check for Packet Tracer file formats (.pkt, .pka, .xml or XML content)
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
                all_devices.update(devs)
                all_links.extend(lnks)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error parsing Packet Tracer file '{fname}': {e}")

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

