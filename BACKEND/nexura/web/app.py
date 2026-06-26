from __future__ import annotations

from contextlib import asynccontextmanager
import asyncio
import base64
import json
import uuid
import logging
import os
import shutil
import sys
import threading
import shlex
import subprocess
from datetime import datetime
from pathlib import Path

import socket

import re

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field

from nexura import config
from nexura.ai_engine import AIEngine
from nexura.cve_lookup import CVELookup
from nexura.ollama_client import ask_ollama
from nexura.github_client import create_repo_from_findings, scan_repo
from nexura.history_db import HistoryDB
from nexura.models.schemas import ScanResult, Vulnerability
from nexura.report.generator import ReportGenerator
from nexura.runner import ScanRunner
from nexura.scanners.network import NetworkScanner
from nexura.tool_selector import ToolSelector
from nexura.verification import DomainVerification, extract_domain, is_private_target

# In-memory stores
_chat_sessions: dict[str, list] = {}
_verifier = DomainVerification()

# Async scan job store: scan_id -> { status, output, error, tool, target }
_scan_jobs: dict[str, dict] = {}

# Tool names for intent parsing
_AVAILABLE_TOOLS = {"nmap", "nuclei", "nikto", "sqlmap", "amass", "whatweb", "gobuster", "wpscan"}


def _parse_scan_intent(user_msg: str, ai_response: str) -> dict | None:
    """Try to extract {tool, target} from user message or AI response.
    Returns None if no clear tool+target pair is found.
    """
    combined = (ai_response + " " + user_msg).lower()

    # Pick the best tool match (priority to tools mentioned in ai_response)
    response_lower = ai_response.lower()
    matched_tool = None
    for t in _AVAILABLE_TOOLS:
        if t in response_lower:
            matched_tool = t
            break
    if not matched_tool:
        for t in _AVAILABLE_TOOLS:
            if t in combined:
                matched_tool = t
                break
    if not matched_tool:
        return None

    # Extract target from user_msg (prefer URL, then domain, then IP)
    target = None
    url_m = re.search(r'(https?://[^\s]+)', user_msg)
    if url_m:
        target = url_m.group(1).rstrip("/")
    if not target:
        domain_m = re.search(r'([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}', user_msg)
        if domain_m:
            target = domain_m.group(0)
    if not target:
        ip_m = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', user_msg)
        if ip_m:
            target = ip_m.group(1)

    if not target:
        # Try AI response for target
        url_m = re.search(r'(https?://[^\s]+)', ai_response)
        if url_m:
            target = url_m.group(1).rstrip("/")
        if not target:
            domain_m = re.search(r'([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}', ai_response)
            if domain_m:
                target = domain_m.group(0)

    if not target:
        return None

    return {"tool": matched_tool, "target": target}

logger = logging.getLogger(__name__)

FRONTEND_DIST = config.PROJECT_ROOT / "FRONTEND" / "dist"

_IS_PRODUCTION = config.IS_PRODUCTION

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not hasattr(app.state, "runner"):
        app.state.runner = ScanRunner()
        app.state.reporter = ReportGenerator()
        app.state.scanner = NetworkScanner()
        app.state.history_db = HistoryDB()
        app.state.cve_lookup = CVELookup()
    yield
    if hasattr(app.state, "cve_lookup"):
        await app.state.cve_lookup.close()
    if hasattr(app.state, "runner"):
        app.state.runner.close()


app = FastAPI(
    title="Nexura Scanner",
    version="2.0.0",
    docs_url=None if _IS_PRODUCTION else "/docs",
    redoc_url=None if _IS_PRODUCTION else "/redoc",
    lifespan=lifespan,
)

app.mount("/reports", StaticFiles(directory=str(config.REPORTS_DIR)), name="reports")

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

_cors_env = os.getenv("NEXURA_CORS_ORIGINS", "").strip()
if _cors_env == "*":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "Authorization", "X-API-Key"],
    )
elif _cors_env:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in _cors_env.split(",")],
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "Authorization", "X-API-Key"],
    )
else:
    _ALLOWED_ORIGINS = [
        "http://127.0.0.1:5000", "http://localhost:5000",
        "http://127.0.0.1:8080", "http://localhost:8080",
        "http://127.0.0.1:5173", "http://localhost:5173",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "Authorization", "X-API-Key"],
    )


@app.middleware("http")
async def _add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if _IS_PRODUCTION:
        response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response


config.ensure_dirs()

_API_KEY = os.getenv("NEXURA_API_KEY", "")
if _API_KEY:
    if _API_KEY == "change-me-to-a-random-secret-key":
        logger.critical("NEXURA_API_KEY default qiymat bilan ishlayapti! Uni o'zgartiring!")
    else:
        logger.warning("API key configured. Server is running over HTTP вЂ” key is sent in cleartext. Set up HTTPS.")


def _verify_token(request: Request):
    if not _API_KEY:
        if _IS_PRODUCTION:
            raise HTTPException(status_code=503, detail="Production rejimda NEXURA_API_KEY majburiy.")
        return True
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer ") and auth[7:] == _API_KEY:
        return True
    if request.headers.get("X-API-Key", "") == _API_KEY:
        return True
    raise HTTPException(status_code=401, detail="Unauthorized. Set NEXURA_API_KEY env var or pass Bearer token.")


# Lifespan managed startup/shutdown


@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Server xatoligi"},
    )


@app.exception_handler(RequestValidationError)
async def _validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": "Noto'g'ri so'rov", "detail": exc.errors()},
    )


def _get_host_url(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-Host", "")
    if forwarded:
        scheme = request.headers.get("X-Forwarded-Proto", "http")
        return f"{scheme}://{forwarded.split(',')[0].strip()}"
    host = request.headers.get("Host", f"{config.WEB_HOST}:{config.WEB_PORT}")
    scheme = request.url.scheme
    return f"{scheme}://{host}"


class ScanRequest(BaseModel):
    prompt: str = Field(max_length=2000)
    target: str | None = Field(default=None, max_length=500)
    agentic: bool = False


class ChatRequest(BaseModel):
    message: str = Field(max_length=2000)
    target: str | None = Field(default=None, max_length=500)
    agentic: bool = False
    session_id: str = Field(default="default", max_length=100)


class AnalyzeRequest(BaseModel):
    scan_output: str = Field(max_length=50000)
    tool: str = Field(max_length=50)
    target: str = Field(max_length=500)
    session_id: str = Field(default="default", max_length=100)


class QuickScanRequest(BaseModel):
    target: str = Field(max_length=500)


class TerminalRequest(BaseModel):
    cmd: str = Field(max_length=1000)

class ScanSelectRequest(BaseModel):
    target: str = Field(min_length=1, max_length=255)
    tool: str = Field(min_length=1, max_length=50)

class VerifyRequest(BaseModel):
    domain: str = Field(max_length=500)

class VerifyCheckRequest(BaseModel):
    domain: str = Field(max_length=500)

class TosAcceptRequest(BaseModel):
    user_identifier: str = Field(default="default", max_length=100)
    tos_version: str = Field(default="1.0", max_length=20)


def _get_selector(request: Request) -> ToolSelector | None:
    return getattr(request.app.state, "selector", None)


async def _enrich_report_with_cms_cves(state, report, target: str) -> None:
    if not report.technologies or not report.technologies.get("cms"):
        return
    cms = report.technologies["cms"]
    try:
        cve_results = await state.cve_lookup.lookup_by_service(cms, "")
        if not report.results:
            report.results.append(
                ScanResult(tool="cve", target=target, start_time=datetime.now(), success=True)
            )
        for cv in cve_results:
            if not any(v.cve == cv.cve_id for r in report.results for v in r.vulnerabilities):
                report.results[0].vulnerabilities.append(Vulnerability(
                    name=f"CVE: {cv.cve_id} вЂ” {cv.description[:100]}",
                    severity=cv.severity,
                    cve=cv.cve_id,
                    cvss=cv.cvss_score,
                    url=cv.url,
                ))
    except Exception as e:
        logger.warning("CVE enrichment failed for %s: %s", cms, e, exc_info=True)


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = FRONTEND_DIST / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Nexura Scanner</h1><p>Frontend not built. Run: cd frontend && npm run build</p>")


@app.post("/api/scan")
async def start_scan(req: ScanRequest, request: Request, _=Depends(_verify_token)):
    state = request.app.state

    target = req.target
    if not target:
        domain_match = re.search(r'([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}', req.prompt)
        ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', req.prompt)
        url_match = re.search(r'(https?://[^\s]+)', req.prompt)
        if url_match:
            target = url_match.group(1)
        elif domain_match:
            target = domain_match.group(0)
        elif ip_match:
            target = ip_match.group(1)

    await verify_scan_permission(target, request)
    await _log_scan_start(state, target or "unknown", request)

    selector = _get_selector(request)
    if selector is None:
        selector = ToolSelector(None)
        state.selector = selector

    plan = await selector.create_plan_async(req.prompt, target)

    if plan.target in (None, "unknown", ""):
        return JSONResponse(status_code=400, content={"error": "Target aniqlanmadi. Iltimos, sayt manzilini kiriting."})

    report = state.reporter.create_report(plan.target, plan.intent)

    if req.agentic:
        results = await selector.run_agentic_scan_async(req.prompt, plan.target, state.runner)
        report.results = results
    else:
        for tc in plan.tools:
            result = await state.runner.run_async(tc, plan.target)
            report.results.append(result)

    report.end_time = datetime.now()
    report.status = "completed"

    try:
        tech_url = plan.target if "://" in plan.target else f"https://{plan.target}"
        report.technologies = state.scanner.detect_technologies(tech_url)
    except Exception as e:
        logger.warning("Technology detection failed for %s: %s", plan.target, e, exc_info=True)

    await _enrich_report_with_cms_cves(state, report, plan.target)

    html_path = state.reporter.save(report, fmt="both")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, state.history_db.save_session, report, report.technologies)

    total_vulns = sum(len(r.vulnerabilities) for r in report.results)
    await _log_scan_end(state, plan.target, request, f"{total_vulns} vulns found")

    relative_report_html = f"/reports/{Path(html_path).name}" if html_path else None
    return {
        "id": report.id,
        "target": report.target,
        "intent": plan.intent,
        "tools": [t.tool for t in plan.tools],
        "results": [r.model_dump(mode="json", exclude_none=True) for r in report.results],
        "report_html": relative_report_html,
        "technologies": report.technologies,
    }


@app.post("/api/quick-scan")
async def quick_scan(req: QuickScanRequest, request: Request, _=Depends(_verify_token)):
    await verify_scan_permission(req.target, request)
    await _log_scan_start(request.app.state, req.target, request)
    result = request.app.state.scanner.quick_scan(req.target)

    if result.ports:
        cve = request.app.state.cve_lookup
        seen = set()
        for port in result.ports:
            if port.service and port.service != "unknown":
                cve_results = await cve.lookup_by_service(port.service, port.version or "")
                for cv in cve_results:
                    if cv.cve_id not in seen:
                        seen.add(cv.cve_id)
                        result.vulnerabilities.append(Vulnerability(
                            name=f"CVE: {cv.cve_id} вЂ” {cv.description[:100]}",
                            severity=cv.severity,
                            cve=cv.cve_id,
                            cvss=cv.cvss_score,
                            url=cv.url,
                        ))

    return result.model_dump(mode="json", exclude_none=True)


@app.get("/api/status")
async def status(request: Request):
    ollama_url = config.OLLAMA_BASE_URL or ""
    ai_ready = bool(ollama_url)
    return {
        "name": "Nexura Scanner",
        "version": "2.0.0",
        "ai_ready": ai_ready,
        "model_loaded": ai_ready,
        "ai_backend": f"ollama/{config.OLLAMA_MODEL}" if ai_ready else "none",
        "ollama_url": ollama_url,
        "ollama_model": config.OLLAMA_MODEL,
        "tools": _check_tools(),
    }


@app.get("/api/host")
async def host_info(request: Request):
    host_url = _get_host_url(request)
    return {
        "host": host_url,
        "api": f"{host_url}/api",
        "docs": f"{host_url}/docs",
    }


@app.get("/api/history")
async def get_history(request: Request, _=Depends(_verify_token)):
    try:
        loop = asyncio.get_event_loop()
        sessions = await loop.run_in_executor(None, request.app.state.history_db.get_all_sessions, 50)
        return {"reports": sessions}
    except Exception as e:
        logger.warning("History DB failed, falling back to file-based: %s", e)
        return _get_history_from_files()


def _validate_id(entity_id: str):
    if not re.match(r'^[a-zA-Z0-9_-]+$', entity_id):
        raise HTTPException(status_code=400, detail="Noto'g'ri ID formati")


@app.get("/api/history/{session_id}")
async def get_session(session_id: str, request: Request, _=Depends(_verify_token)):
    _validate_id(session_id)
    loop = asyncio.get_event_loop()
    session = await loop.run_in_executor(None, request.app.state.history_db.get_session, session_id)
    if session:
        return session
    return JSONResponse(status_code=404, content={"error": "Session topilmadi"})


@app.delete("/api/history/{session_id}")
async def delete_session(session_id: str, request: Request, _=Depends(_verify_token)):
    _validate_id(session_id)
    loop = asyncio.get_event_loop()
    ok = await loop.run_in_executor(None, request.app.state.history_db.delete_session, session_id)
    if ok:
        return {"status": "deleted", "id": session_id}
    return JSONResponse(status_code=404, content={"error": "Session topilmadi"})


@app.get("/api/stats")
async def get_stats(request: Request, _=Depends(_verify_token)):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, request.app.state.history_db.get_stats)


@app.get("/api/report/{report_id}")
async def get_report(report_id: str, request: Request, _=Depends(_verify_token)):
    if not re.match(r'^[a-zA-Z0-9_-]+$', report_id):
        return JSONResponse(status_code=400, content={"error": "Noto'g'ri hisobot ID"})
    state = request.app.state
    loop = asyncio.get_event_loop()
    session = await loop.run_in_executor(None, state.history_db.get_session, report_id)
    if session:
        return session
    reports_dir = config.REPORTS_DIR
    report_file = reports_dir / f"{report_id}.json"
    if report_file.exists():
        data = json.loads(report_file.read_text(encoding="utf-8"))
        return data
    return JSONResponse(status_code=404, content={"error": "Hisobot topilmadi"})


def _get_history_from_files() -> dict:
    reports_dir = config.REPORTS_DIR
    if not reports_dir.exists():
        return {"reports": []}
    reports = []
    for f in sorted(reports_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            total_vulns = sum(len(r.get("vulnerabilities", [])) for r in data.get("results", []))
            severities = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
            for r in data.get("results", []):
                for v in r.get("vulnerabilities", []):
                    sev = v.get("severity", "").upper()
                    if sev in severities:
                        severities[sev] += 1
            reports.append({
                "id": data.get("id", ""),
                "target": data.get("target", ""),
                "intent": data.get("intent", ""),
                "date": data.get("start_time", ""),
                "status": data.get("status", ""),
                "total_vulns": total_vulns,
                "severities": severities,
                "tools": list(set(r.get("tool", "") for r in data.get("results", []))),
                "filename": f.stem,
            })
        except (json.JSONDecodeError, KeyError):
            continue
    return {"reports": reports}

def _check_tools() -> dict:
    tools = ["nmap", "nuclei", "nikto", "sqlmap", "gobuster", "amass", "whatweb"]
    result = {}
    for t in tools:
        result[t] = {"available": config.is_tool_available(t)}
    return result


TOOLS_META = [
    {"name": "nmap",     "label": "Nmap",     "description": "Port skanerlash va xizmatlarni aniqlash"},
    {"name": "nuclei",   "label": "Nuclei",   "description": "Zaiflik skaneri (CVE asosida)"},
    {"name": "nikto",    "label": "Nikto",    "description": "Web server zaifliklarini tekshirish"},
    {"name": "sqlmap",   "label": "SQLMap",   "description": "SQL injection zaifliklarini aniqlash"},
    {"name": "gobuster", "label": "Gobuster", "description": "Katalog va fayllarni topish"},
    {"name": "whatweb",  "label": "WhatWeb",  "description": "Texnologiyalarni aniqlash"},
    {"name": "amass",    "label": "Amass",    "description": "Subdomain va domen ma'lumotlarini yig'ish"},
]

import re as _re

def _validate_target(target: str) -> str | None:
    if _INTERNAL_RE.search(target):
        return "Xavfsizlik: serverning o'zini skanerlash mumkin emas"
    return None


def _clean_target(target: str, tool: str) -> str:
    # Strip URL scheme
    host = _re.sub(r'^https?://', '', target)
    # Strip path/query/fragment
    host = _re.sub(r'[/?#].*$', '', host)
    if tool in ("nmap", "amass"):
        return host  # just hostname/IP
    if tool in ("nuclei", "nikto", "whatweb"):
        scheme = "https://" if target.startswith("https://") else ("http://" if target.startswith("http://") else "https://")
        return scheme + host
    if tool == "gobuster":
        scheme = "https://" if target.startswith("https://") else ("http://" if target.startswith("http://") else "https://")
        return scheme + host
    if tool == "sqlmap":
        return target  # full URL with path
    return host

TOOL_TEMPLATES = {
    "nmap":     "nmap -sV -sC -O -T4 {host}",
    "nuclei":   "nuclei -u {target} -severity low,medium,high,critical",
    "nikto":    "nikto -h {target}",
    "sqlmap":   "sqlmap -u {target} --batch --random-agent",
    "gobuster": "gobuster dir -u {target} -w /usr/share/wordlists/dirb/common.txt -t 50",
    "whatweb":  "whatweb {target}",
    "amass":    "amass enum -d {host}",
}

@app.get("/api/tools")
async def list_tools(_=Depends(_verify_token)):
    result = []
    for t in TOOLS_META:
        info = dict(t)
        info["available"] = config.is_tool_available(t["name"])
        result.append(info)
    return {"tools": result}


@app.post("/api/scan/select")
async def scan_with_selected_tool(req: ScanSelectRequest, request: Request, _=Depends(_verify_token)):
    tool = req.tool.strip().lower()
    target = req.target.strip()

    valid_err = _validate_target(target)
    if valid_err:
        return JSONResponse(status_code=400, content={"error": valid_err})

    if not config.is_tool_available(tool):
        return JSONResponse(status_code=400, content={"error": f"'{tool}' dasturi serverda topilmadi"})
    
    # Use template command directly (tool already selected by user)
    host = _clean_target(target, tool)
    template = TOOL_TEMPLATES.get(tool)
    if template:
        command = template.format(target=target, host=host)
    else:
        command = f"{tool} {host}"
    
    # Try n8n to generate a smarter command, validate response starts with tool name
    try:
        prompt = (
            f"Foydalanuvchi '{target}' manzilini '{tool}' vositasi bilan tekshirmoqchi. "
            f"Aynan shu vosita uchun to'g'ri terminal buyrug'ini yoz. "
            f"Javobda FAQAT buyruq matni bo'lsin, boshqa hech narsa qo'shma."
        )
        ai_result = await ask_ollama(prompt)
        resp = ai_result.get("response", "").strip().strip("`").strip()
        if resp and resp.lower().startswith(tool.lower()):
            command = resp
    except Exception:
        pass
    
    # Execute the command (reuse terminal logic)
    try:
        cmd_args = shlex.split(command)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"Noto'g'ri buyruq: {e}"})
    
    binary = cmd_args[0]
    binary_clean = binary.lower().lstrip(".").rstrip(".exe")
    
    if binary_clean not in ALLOWED_TERMINAL_COMMANDS:
        return JSONResponse(status_code=400, content={"error": f"'{binary}' ruxsat etilmagan buyruq"})
    
    binary_path = config.TOOL_PATHS.get(binary_clean) or shutil.which(binary)
    if not binary_path:
        return JSONResponse(status_code=400, content={"error": f"'{binary}' serverda topilmadi"})
    
    try:
        proc = await asyncio.create_subprocess_exec(
            binary_path, *cmd_args[1:],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(config.BASE_DIR),
            env=config.get_env(),
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=config.TIMEOUT)
    except asyncio.TimeoutError:
        proc.kill()
        return {"command": command, "output": "", "error_log": "Buyruq vaqt chegarasidan oshdi", "code": -1, "generated_by": "template"}
    
    output = stdout.decode("utf-8", errors="replace").strip()
    error_log = stderr.decode("utf-8", errors="replace").strip()
    
    return {
        "command": command,
        "output": output,
        "error_log": error_log,
        "code": proc.returncode,
        "generated_by": "n8n" if not n8n_error else "template",
    }


@app.get("/api/reports")
async def list_reports(request: Request, _=Depends(_verify_token)):
    reports_dir = config.REPORTS_DIR
    if not reports_dir.exists():
        return {"files": []}
    files = []
    for f in sorted(reports_dir.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True):
        files.append({
            "name": f.name,
            "path": f"/reports/{f.name}",
            "size": f"{round(f.stat().st_size / 1024, 1)} KB",
            "date": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        })
    return {"files": files}


@app.delete("/api/reports/{filename}")
async def delete_report(filename: str, request: Request, _=Depends(_verify_token)):
    if not re.match(r'^[a-zA-Z0-9_.-]+\.html$', filename):
        raise HTTPException(status_code=400, detail="Noto'g'ri fayl nomi")
    reports_dir = config.REPORTS_DIR
    filepath = reports_dir / filename
    if filepath.exists() and filepath.is_file():
        filepath.unlink()
        return {"status": "deleted", "filename": filename}
    return JSONResponse(status_code=404, content={"error": "Fayl topilmadi"})


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest, request: Request, _=Depends(_verify_token)):
    sid = req.session_id
    db = request.app.state.history_db

    # Extract target from message for convenience
    target = req.target
    if not target:
        url_match = re.search(r'(https?://[^\s]+)', req.message)
        domain_match = re.search(r'([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}', req.message)
        ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', req.message)
        if url_match:
            target = url_match.group(1)
        elif domain_match:
            target = domain_match.group(0)
        elif ip_match:
            target = ip_match.group(1)

    # Send to local Ollama Phi-3 mini
    ai_result = await ask_ollama(req.message.strip())
    ai_backend = "ollama"
    response_text = ai_result["response"]

    # Save to persistent DB
    db.save_chat_message(sid, "user", req.message.strip(), ai_backend)
    db.save_chat_message(sid, "assistant", response_text, ai_backend)

    # Try to extract automatic scan action from user msg + AI response
    scan_action = None
    if not ai_result.get("error"):
        parsed = _parse_scan_intent(req.message.strip(), response_text)
        if parsed:
            scan_action = parsed

    # Audit log
    await _log_scan_start(request.app.state, target or "unknown", request, f"{ai_backend} chat")

    return {
        "response": response_text,
        "scan_data": None,
        "scan_action": scan_action,
    }


# ── Async scan job worker ──
async def _run_scan_job(scan_id: str, target: str, tool: str, cmd: str):
    """Background worker: execute tool command, then send to n8n for analysis."""
    _scan_jobs[scan_id] = {"status": "running", "output": "", "error": "", "tool": tool, "target": target}
    try:
        cmd_args = shlex.split(cmd)
        binary = cmd_args[0]
        binary_path = config.TOOL_PATHS.get(binary) or shutil.which(binary)
        if not binary_path:
            _scan_jobs[scan_id] = {**_scan_jobs[scan_id], "status": "error", "error": f"'{binary}' topilmadi"}
            return
        proc = await asyncio.create_subprocess_exec(
            binary_path, *cmd_args[1:],
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            env=config.get_env(),
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=config.TIMEOUT)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            _scan_jobs[scan_id] = {**_scan_jobs[scan_id], "status": "error", "error": f"Timeout ({config.TIMEOUT}s)"}
            return

        raw_output = stdout.decode("utf-8", errors="replace") if stdout else ""
        raw_err = stderr.decode("utf-8", errors="replace") if stderr else ""
        _scan_jobs[scan_id]["output"] = raw_output
        _scan_jobs[scan_id]["error_log"] = raw_err

        # Send raw output to n8n Claude for analysis
        analysis_prompt = (
            f"Sen cybersecurity eksperti. Terminal natijasini tahlil qil va oddiy tilda tushuntir. "
            f"Xavfli zaifliklarni ajratib ko'rsat. Tavsiyalar ber. O'zbek tilida javob ber.\n\n"
            f"Vosita: {tool.upper()}\nNishon: {target}\n\nNatija:\n{raw_output[:30000]}"
        )
        ai_result = await ask_ollama(analysis_prompt)
        analysis = ai_result.get("response", "Tahlil olinmadi")
        _scan_jobs[scan_id]["analysis"] = f"🔍 **{tool.upper()} skanerlash tahlili — {target}**\n\n{analysis}"
        _scan_jobs[scan_id]["status"] = "completed"
    except Exception as e:
        _scan_jobs[scan_id] = {**_scan_jobs[scan_id], "status": "error", "error": str(e)}


@app.post("/api/analyze/start")
async def start_scan_analysis(req: AnalyzeRequest, request: Request, _=Depends(_verify_token)):
    """Start a scan job and return immediately with scan_id. Frontend polls /api/analyze/status/{scan_id}."""
    target = req.target
    tool = req.tool

    valid_err = _validate_target(target)
    if valid_err:
        return JSONResponse(status_code=400, content={"error": valid_err})

    # Build command from template
    template = TOOL_TEMPLATES.get(tool)
    if not template:
        return JSONResponse(status_code=400, content={"error": f"'{tool}' uchun buyruq shabloni yo'q"})
    clean = _clean_target(target, tool)
    cmd = template.format(target=target, host=clean)

    scan_id = str(uuid.uuid4())[:8]
    _scan_jobs[scan_id] = {"status": "queued", "output": "", "error": "", "tool": tool, "target": target}

    asyncio.create_task(_run_scan_job(scan_id, target, tool, cmd))

    return {"scan_id": scan_id, "status": "queued", "tool": tool, "target": target}


@app.get("/api/analyze/status/{scan_id}")
async def get_scan_analysis_status(scan_id: str, _=Depends(_verify_token)):
    """Poll this endpoint to get scan progress and final analysis."""
    job = _scan_jobs.get(scan_id)
    if not job:
        return JSONResponse(status_code=404, content={"error": "Scan job topilmadi"})
    resp = {"scan_id": scan_id, "status": job.get("status"), "tool": job.get("tool"), "target": job.get("target")}
    if job["status"] == "completed":
        resp["analysis"] = job.get("analysis", "")
        resp["output"] = job.get("output", "")
    elif job["status"] == "error":
        resp["error"] = job.get("error", "")
    return resp


# ── GitHub Integration ──

class GitHubExportRequest(BaseModel):
    token: str = Field(max_length=200)
    repo_name: str = Field(max_length=100)
    session_id: str = Field(default="", max_length=100)


class GitHubScanRequest(BaseModel):
    token: str = Field(max_length=200)
    repo_url: str = Field(max_length=500)


@app.post("/api/github/export")
async def github_export(req: GitHubExportRequest, request: Request, _=Depends(_verify_token)):
    findings = []
    target = "unknown"
    tool = "nmap"
    if req.session_id:
        loop = asyncio.get_event_loop()
        session = await loop.run_in_executor(None, request.app.state.history_db.get_session, req.session_id)
        if session:
            target = session.get("target", target)
            findings = session.get("vulnerabilities", []) or session.get("ai_analysis", [])
            tools = session.get("tools", [])
            if tools:
                tool = tools[0] if isinstance(tools[0], str) else tools[0].get("tool", tool)
    if not findings:
        return JSONResponse(status_code=400, content={"error": "Eksport qilish uchun zaifliklar topilmadi"})
    result = await create_repo_from_findings(req.token, req.repo_name, findings, target, tool)
    return result


@app.post("/api/github/scan-repo")
async def github_scan_repo(req: GitHubScanRequest, _=Depends(_verify_token)):
    result = await scan_repo(req.token, req.repo_url)
    return result


@app.get("/api/chat/history")
async def get_chat_history(session_id: str = "default", request: Request = None, _=Depends(_verify_token)):
    loop = asyncio.get_event_loop()
    messages = await loop.run_in_executor(None, request.app.state.history_db.get_chat_history, session_id, 100)
    return {"session_id": session_id, "messages": messages}


@app.delete("/api/chat/history")
async def delete_chat_history(session_id: str = "default", request: Request = None, _=Depends(_verify_token)):
    loop = asyncio.get_event_loop()
    ok = await loop.run_in_executor(None, request.app.state.history_db.delete_chat_session, session_id)
    return {"deleted": ok, "session_id": session_id}


@app.get("/api/chat/sessions")
async def list_chat_sessions(request: Request = None, _=Depends(_verify_token)):
    loop = asyncio.get_event_loop()
    sessions = await loop.run_in_executor(None, request.app.state.history_db.get_all_chat_sessions)
    return {"sessions": sessions}


# ⚠️ DIQQAT: TOS VA DOMAIN VERIFICATION VAQTINCHA O'CHIRILGAN
# Sabab: Investor demo/sinov bosqichi
# Sana: 2026-06-21
# TODO: Production relizidan oldin albatta yoqish kerak!
# Qaytarish uchun: quyidagi "VAQTINCHA O'CHIRILGAN" bloklarni qayta yoqing

# ---- Scan Permission Middleware ----

async def verify_scan_permission(target: str | None, request: Request):
    if not target:
        return
    # VAQTINCHA O'CHIRILGAN - DEMO REJIMI (investor ko'rsatuvi uchun)
    # domain = extract_domain(target)
    # user_id = "default"

    # 1. ToS check — VAQTINCHA O'CHIRILGAN
    # loop = asyncio.get_event_loop()
    # tos_ok = await loop.run_in_executor(None, request.app.state.history_db.is_tos_accepted, user_id)
    # if not tos_ok:
    #     raise HTTPException(
    #         status_code=403,
    #         detail={"error": "Avval foydalanish shartlarini qabul qiling", "code": "TOS_NOT_ACCEPTED"},
    #     )

    # 2. Private target / own domain — skip verification
    # VAQTINCHA O'CHIRILGAN - DEMO REJIMI (investor ko'rsatuvi uchun)
    # if is_private_target(domain) or domain == "nexuraai.uz":
    #     return

    # 3. Domain verification check
    # VAQTINCHA O'CHIRILGAN - DEMO REJIMI (investor ko'rsatuvi uchun)
    # Production'ga chiqishdan oldin bu bloklash QAYTARILISHI SHART
    # verified = await loop.run_in_executor(None, request.app.state.history_db.is_domain_verified, domain)
    # if not verified:
    #     raise HTTPException(
    #         status_code=403,
    #         detail={
    #             "error": "Domen tasdiqlanmagan. Avval /api/verify/request orqali domeningizni tasdiqlang.",
    #             "code": "DOMAIN_NOT_VERIFIED",
    #         },
    #     )
    return


async def _log_scan_start(state, target: str, request: Request, tools_used: str | None = None):
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            state.history_db.log_audit_event,
            "default",
            request.client.host if request.client else None,
            target,
            "scan_start",
            tools_used,
            "demo_mode_skipped",
            None,
            None,
        )
    except Exception:
        logger.warning("Audit log failed (non-blocking)")


async def _log_scan_end(state, target: str, request: Request, result_summary: str | None = None):
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            state.history_db.log_audit_event,
            "default",
            request.client.host if request.client else None,
            target,
            "scan_complete",
            None,
            None,
            None,
            result_summary,
        )
    except Exception:
        logger.warning("Audit log failed (non-blocking)")


# ---- Domain Verification Endpoints ----

@app.post("/api/verify/request")
async def verify_request(req: VerifyRequest, request: Request, _=Depends(_verify_token)):
    domain = extract_domain(req.domain)
    if is_private_target(domain):
        return JSONResponse(status_code=400, content={"error": "Localhost/private IP verification talab qilmaydi"})
    token = _verifier.generate_token()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, request.app.state.history_db.create_verification_request, domain, token)
    return {
        "domain": domain,
        "token": token,
        "instructions": f"Quyidagi TXT recordni domeningizga qo'shing: nexura-verify={token}",
        "expires_in": "24 soat",
    }


@app.post("/api/verify/check")
async def verify_check(req: VerifyCheckRequest, request: Request, _=Depends(_verify_token)):
    domain = extract_domain(req.domain)
    if is_private_target(domain):
        return {"verified": True, "domain": domain, "skip": True}
    loop = asyncio.get_event_loop()
    token = await loop.run_in_executor(None, request.app.state.history_db.get_verification_token, domain)
    if not token:
        return JSONResponse(status_code=400, content={"error": "Bu domen uchun verification so'rovi topilmadi. Avval /api/verify/request ni chaqiring."})
    verified = _verifier.check_txt_record(domain, token)
    if verified:
        await loop.run_in_executor(None, request.app.state.history_db.mark_domain_verified, domain)
    return {"verified": verified, "domain": domain}


# ---- ToS Endpoints ----

@app.post("/api/tos/accept")
async def tos_accept(req: TosAcceptRequest, request: Request, _=Depends(_verify_token)):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        request.app.state.history_db.accept_tos,
        req.user_identifier,
        req.tos_version,
        request.client.host if request.client else None,
    )
    return {"accepted": True, "version": req.tos_version}


@app.get("/api/tos/status")
async def tos_status(request: Request):
    loop = asyncio.get_event_loop()
    accepted = await loop.run_in_executor(None, request.app.state.history_db.is_tos_accepted, "default")
    return {"accepted": accepted, "version": "1.0"}


# ---- Audit Endpoint ----

@app.get("/api/audit")
async def get_audit_log(request: Request, limit: int = 100, _=Depends(_verify_token)):
    loop = asyncio.get_event_loop()
    entries = await loop.run_in_executor(None, request.app.state.history_db.get_audit_log, limit)
    return {"entries": entries}


# ---- n8n Webhook API ----
import uuid

_scan_jobs: dict[str, dict] = {}

class WebhookScanRequest(BaseModel):
    prompt: str = Field(max_length=2000)
    target: str | None = Field(default=None, max_length=500)
    agentic: bool = False

@app.post("/api/webhook/scan")
async def webhook_scan(req: WebhookScanRequest, request: Request, _=Depends(_verify_token)):
    state = request.app.state
    await verify_scan_permission(req.target, request)
    await _log_scan_start(state, req.target or req.prompt, request)

    selector = _get_selector(request)
    if selector is None:
        selector = ToolSelector(None)
        state.selector = selector

    plan = await selector.create_plan_async(req.prompt, req.target)
    if plan.target in (None, "unknown", ""):
        return JSONResponse(status_code=400, content={"error": "Target aniqlanmadi"})
    if not plan.tools:
        return JSONResponse(status_code=400, content={"error": f"Skanerlash rejasi tuzilmadi: {plan.reasoning}"})

    report = state.reporter.create_report(plan.target, plan.intent)
    for tc in plan.tools:
        result = await state.runner.run_async(tc, plan.target)
        report.results.append(result)

    report.end_time = datetime.now()
    report.status = "completed"

    try:
        tech_url = plan.target if "://" in plan.target else f"https://{plan.target}"
        report.technologies = state.scanner.detect_technologies(tech_url)
    except Exception:
        pass

    html_path = state.reporter.save(report, fmt="both")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, state.history_db.save_session, report, report.technologies)

    total_vulns = sum(len(r.vulnerabilities) for r in report.results)
    await _log_scan_end(state, plan.target, request, f"{total_vulns} vulns found")

    return {
        "job_id": report.id,
        "target": report.target,
        "status": "completed",
        "tools": [t.tool.value for t in plan.tools],
        "total_ports": sum(len(r.ports) for r in report.results),
        "total_vulnerabilities": sum(len(r.vulnerabilities) for r in report.results),
        "vulnerabilities": [
            {
                "tool": r.tool,
                "name": v.name,
                "severity": v.severity,
                "port": v.port,
                "cve": v.cve,
                "cvss": v.cvss,
            }
            for r in report.results for v in r.vulnerabilities
        ],
        "report_url": f"/reports/{Path(html_path).name}" if html_path else None,
        "technologies": report.technologies,
    }


@app.post("/api/webhook/scan/async")
async def webhook_scan_async(req: WebhookScanRequest, request: Request, _=Depends(_verify_token)):
    state = request.app.state
    await verify_scan_permission(req.target, request)
    await _log_scan_start(state, req.target or req.prompt, request)

    selector = _get_selector(request)
    if selector is None:
        selector = ToolSelector(None)
        state.selector = selector

    plan = await selector.create_plan_async(req.prompt, req.target)
    if plan.target in (None, "unknown", ""):
        return JSONResponse(status_code=400, content={"error": "Target aniqlanmadi"})
    if not plan.tools:
        return JSONResponse(status_code=400, content={"error": f"Skanerlash rejasi tuzilmadi: {plan.reasoning}"})

    job_id = str(uuid.uuid4())[:8]
    _scan_jobs[job_id] = {
        "status": "running",
        "target": plan.target,
        "intent": plan.intent,
        "tools": [t.tool.value for t in plan.tools],
        "start_time": datetime.now().isoformat(),
        "results": None,
        "error": None,
    }

    client_ip = request.client.host if request.client else None

    async def run_job():
        try:
            report = state.reporter.create_report(plan.target, plan.intent)
            for tc in plan.tools:
                result = await state.runner.run_async(tc, plan.target)
                report.results.append(result)
            report.end_time = datetime.now()
            report.status = "completed"

            try:
                tech_url = plan.target if "://" in plan.target else f"https://{plan.target}"
                report.technologies = state.scanner.detect_technologies(tech_url)
            except Exception:
                pass

            html_path = state.reporter.save(report, fmt="both")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, state.history_db.save_session, report, report.technologies)

            total_vulns = sum(len(r.vulnerabilities) for r in report.results)
            await loop.run_in_executor(
                None,
                state.history_db.log_audit_event,
                "default",
                client_ip,
                plan.target,
                "scan_complete",
                None,
                None,
                None,
                f"{total_vulns} vulns found",
            )

            _scan_jobs[job_id].update({
                "status": "completed",
                "results": {
                    "total_ports": sum(len(r.ports) for r in report.results),
                    "total_vulnerabilities": sum(len(r.vulnerabilities) for r in report.results),
                    "vulnerabilities": [
                        {"tool": r.tool, "name": v.name, "severity": v.severity, "port": v.port, "cve": v.cve, "cvss": v.cvss}
                        for r in report.results for v in r.vulnerabilities
                    ],
                    "report_url": f"/reports/{Path(html_path).name}" if html_path else None,
                    "technologies": report.technologies,
                },
            })
        except Exception as e:
            _scan_jobs[job_id].update({"status": "failed", "error": str(e)})

    asyncio.create_task(run_job())

    return {"job_id": job_id, "status": "running", "target": plan.target, "tools": [t.tool.value for t in plan.tools]}


@app.get("/api/webhook/scan/{job_id}/status")
async def webhook_scan_status(job_id: str, _=Depends(_verify_token)):
    job = _scan_jobs.get(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"error": "Job topilmadi"})
    return {
        "job_id": job_id,
        "status": job["status"],
        "target": job.get("target"),
        "start_time": job.get("start_time"),
        "tools": job.get("tools"),
    }


@app.get("/api/webhook/scan/{job_id}/results")
async def webhook_scan_results(job_id: str, _=Depends(_verify_token)):
    job = _scan_jobs.get(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"error": "Job topilmadi"})
    if job["status"] == "running":
        return JSONResponse(status_code=202, content={"status": "running", "message": "Skanerlash davom etmoqda"})
    if job["status"] == "failed":
        return {"job_id": job_id, "status": "failed", "error": job["error"]}
    return {"job_id": job_id, "status": "completed", **job["results"]}


ALLOWED_TERMINAL_COMMANDS = frozenset({
    "nmap", "nuclei", "nikto", "sqlmap", "gobuster", "amass", "whatweb",
    "ping", "nslookup", "dig", "traceroute", "tracert", "ls", "dir", "pwd"
})

# ── Security filters ──

VPS_IPS = {"127.0.0.1", "localhost", "0.0.0.0", "185.191.141.247", "::1"}
RATE_LIMIT_STORE: dict[str, list[float]] = {}
RATE_LIMIT_MAX = 10
RATE_LIMIT_WINDOW = 60


def _rate_limit(ip: str) -> str | None:
    now = __import__("time").time()
    window = RATE_LIMIT_STORE.setdefault(ip, [])
    window[:] = [t for t in window if now - t < RATE_LIMIT_WINDOW]
    if len(window) >= RATE_LIMIT_MAX:
        return f"Juda ko'p so'rov ({RATE_LIMIT_MAX} ta / {RATE_LIMIT_WINDOW} soniya). Keyinroq urinib ko'ring."
    window.append(now)
    return None


_INTERNAL_RE = re.compile(
    r"(?i)\b(127\.\d{1,3}\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|localhost|::1|0\.0\.0\.0|185\.191\.141\.247)\b"
)

_DANGEROUS_NMAP_FLAGS = re.compile(r"--script\b|--script-args\b|-oA\b|-oN\b|-oX\b|-oS\b|-oG\b|--datadir\b|--servicedb\b|--versiondb\b|--iflist\b|--resume\b|-\s*e\b")
_DANGEROUS_NUCLEI_FLAGS = re.compile(r"--template\b|-t\b|--system-templates\b|--update-templates\b|--code\b|--json-export\b|--markdown-export\b")


def _validate_cmd_safety(binary_clean: str, cmd_args: list[str], full_cmd: str) -> str | None:
    full_lower = full_cmd.lower()

    # 1. Block targeting internal/VPS IPs
    if _INTERNAL_RE.search(full_cmd):
        return "Xavfsizlik: serverning o'zini skanerlash mumkin emas"

    # 2. Block dangerous nmap flags
    if binary_clean == "nmap" and _DANGEROUS_NMAP_FLAGS.search(full_lower):
        return "Xavfsizlik: nmap --script va boshqa xavfli flag'lar bloklangan"

    # 3. Block dangerous nuclei flags
    if binary_clean == "nuclei" and _DANGEROUS_NUCLEI_FLAGS.search(full_lower):
        return "Xavfsizlik: nuclei custom template'lar bloklangan"

    # 4. Limit nslookup/dig count (max 2 targets)
    if binary_clean in ("nslookup", "dig") and len(cmd_args) > 3:
        return "Xavfsizlik: nslookup/dig faqat bitta nishon bilan cheklangan"

    # 5. Block massive port ranges in nmap
    if binary_clean == "nmap":
        for arg in cmd_args:
            if arg.startswith("-p") and arg != "-p-":
                parts = arg.lstrip("-p")
                if "-" in parts:
                    start, end = parts.split("-", 1)
                    if start.isdigit() and end.isdigit():
                        if int(end) - int(start) > 10000:
                            return "Xavfsizlik: port diapazoni 10000 dan oshmasligi kerak"

    return None


@app.post("/api/terminal")
async def run_terminal(req: TerminalRequest, request: Request, _=Depends(_verify_token)):
    # Rate limit
    ip = request.client.host if request.client else "unknown"
    rate_err = _rate_limit(ip)
    if rate_err:
        return {"output": "", "error": rate_err, "code": -1}

    cmd = req.cmd.strip()
    if not cmd:
        return {"output": "", "error": "Bo'sh buyruq", "code": -1}

    # Option C: /scan <tool> <target> handler
    if cmd.lower().startswith("/scan "):
        parts = cmd.split(maxsplit=2)
        if len(parts) < 3:
            return {"output": "", "error": "/scan <vosita> <nishon> — masalan: /scan nmap example.com", "code": -1}
        scan_tool = parts[1].strip().lower()
        scan_target = parts[2].strip()
        if not config.is_tool_available(scan_tool):
            return {"output": "", "error": f"'{scan_tool}' dasturi serverda mavjud emas", "code": 1}
        template = TOOL_TEMPLATES.get(scan_tool)
        if not template:
            return {"output": "", "error": f"'{scan_tool}' uchun buyruq shabloni yo'q", "code": 1}
        clean = _clean_target(scan_target, scan_tool)
        cmd = template.format(target=scan_target, host=clean)
        # Re-split with the new command
        try:
            cmd_args = shlex.split(cmd)
        except Exception as e:
            return {"output": "", "error": f"Buyruq formatida xatolik: {e}", "code": -1}
        if not cmd_args:
            return {"output": "", "error": "Bo'sh buyruq", "code": -1}
        binary = cmd_args[0]
        binary_clean = binary.lower().lstrip(".").rstrip(".exe")
    else:
        try:
            cmd_args = shlex.split(cmd)
        except Exception as e:
            return {"output": "", "error": f"Buyruq formatida xatolik: {e}", "code": -1}
        if not cmd_args:
            return {"output": "", "error": "Bo'sh buyruq", "code": -1}
        binary = cmd_args[0]
        binary_clean = binary.lower().lstrip(".").rstrip(".exe")

    # Safety validation
    safety_err = _validate_cmd_safety(binary_clean, cmd_args, cmd)
    if safety_err:
        return {"output": "", "error": safety_err, "code": 1}

    if binary_clean not in ALLOWED_TERMINAL_COMMANDS:
        return {
            "output": "",
            "error": f"Xavfsizlik cheklovi: '{binary}' buyrug'i ruxsat etilmagan. Faqat skanerlash (nmap, nuclei, nikto, sqlmap, gobuster, amass, whatweb) va diagnostika (ping, nslookup, dig, traceroute) buyruqlaridan foydalaning.",
            "code": 1
        }

    binary_path = config.TOOL_PATHS.get(binary_clean) or shutil.which(binary)
    if not binary_path and sys.platform == "win32":
        extra = {
            "nmap": r"C:\Program Files\nmap\nmap.exe",
            "nuclei": os.path.expanduser(r"~\nuclei\nuclei.exe"),
            "whatweb": os.path.expanduser(r"~\whatweb\whatweb.exe"),
        }
        if binary_clean in extra and os.path.exists(extra[binary_clean]):
            binary_path = extra[binary_clean]

    if not binary_path and binary_clean not in ("dir", "pwd", "ls"):
        return {"output": "", "error": f"Dastur topilmadi: '{binary}'. Serverga o'rnatilganligini tekshiring.", "code": 1}

    try:
        if binary_clean == "pwd" or (binary_clean == "ls" and sys.platform != "win32"):
            proc = await asyncio.create_subprocess_exec(
                binary_clean, *cmd_args[1:],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(config.BASE_DIR),
                env=config.get_env(),
            )
        elif binary_clean == "dir" or (binary_clean == "ls" and sys.platform == "win32"):
            proc = await asyncio.create_subprocess_exec(
                "cmd", "/c", "dir", *cmd_args[1:],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(config.BASE_DIR),
                env=config.get_env(),
            )
        else:
            proc = await asyncio.create_subprocess_exec(
                binary_path, *cmd_args[1:],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(config.BASE_DIR),
                env=config.get_env(),
            )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=config.TIMEOUT)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {"output": "", "error": f"Buyruq bajarilishi {config.TIMEOUT} soniyadan oshib ketdi va bekor qilindi.", "code": -1}

        output = stdout.decode("utf-8", errors="replace") if stdout else ""
        error = stderr.decode("utf-8", errors="replace") if stderr else ""
        return {"output": output, "error_log": error, "code": proc.returncode or 0}

    except Exception as e:
        return {"output": "", "error": f"Xatolik yuz berdi: {e}", "code": -1}
