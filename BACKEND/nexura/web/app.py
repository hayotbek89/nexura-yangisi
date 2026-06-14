from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import shutil
import sys
import threading
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
from nexura.history_db import HistoryDB
from nexura.models.schemas import ScanResult, Vulnerability
from nexura.report.generator import ReportGenerator
from nexura.runner import ScanRunner
from nexura.scanners.network import NetworkScanner
from nexura.tool_selector import ToolSelector

logger = logging.getLogger(__name__)

FRONTEND_DIST = config.PROJECT_ROOT / "FRONTEND" / "dist"

_IS_PRODUCTION = config.IS_PRODUCTION

app = FastAPI(
    title="Nexura Scanner",
    version="2.0.0",
    docs_url=None if _IS_PRODUCTION else "/docs",
    redoc_url=None if _IS_PRODUCTION else "/redoc",
)

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
        logger.warning("API key configured. Server is running over HTTP — key is sent in cleartext. Set up HTTPS.")


def _verify_token(request: Request):
    if not _API_KEY:
        return True
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer ") and auth[7:] == _API_KEY:
        return True
    if request.headers.get("X-API-Key", "") == _API_KEY:
        return True
    raise HTTPException(status_code=401, detail="Unauthorized. Set NEXURA_API_KEY env var or pass Bearer token.")


@app.on_event("startup")
def _init_app():
    if not hasattr(app.state, "runner"):
        app.state.runner = ScanRunner()
        app.state.reporter = ReportGenerator()
        app.state.scanner = NetworkScanner()
        app.state.history_db = HistoryDB()
        app.state.engine = AIEngine()
        app.state.selector = ToolSelector(app.state.engine) if app.state.engine.is_ready else None
        app.state.cve_lookup = CVELookup()


@app.on_event("shutdown")
async def _shutdown_app():
    if hasattr(app.state, "cve_lookup"):
        await app.state.cve_lookup.close()
    if hasattr(app.state, "engine"):
        app.state.engine.close()
    if hasattr(app.state, "runner"):
        app.state.runner.close()


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


class QuickScanRequest(BaseModel):
    target: str = Field(max_length=500)


def _get_engine(request: Request) -> AIEngine:
    return request.app.state.engine

def _get_selector(request: Request) -> ToolSelector | None:
    return request.app.state.selector


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = FRONTEND_DIST / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Nexura Scanner</h1><p>Frontend not built. Run: cd frontend && npm run build</p>")


@app.post("/api/scan")
async def start_scan(req: ScanRequest, request: Request, _=Depends(_verify_token)):
    state = request.app.state
    selector = _get_selector(request)
    if not selector:
        engine = state.engine
        if not engine.is_ready:
            return JSONResponse(
                status_code=503,
                content={"error": "AI Engine yoqilmagan. GGUF model faylini joylashtiring."},
            )
        selector = ToolSelector(engine)
        state.selector = selector

    plan = await selector.create_plan_async(req.prompt, req.target)
    report = state.reporter.create_report(plan.target, plan.intent)

    if req.agentic and selector.engine.is_ready:
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

    html_path = state.reporter.save(report, fmt="both")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, state.history_db.save_session, report, report.technologies)

    if report.technologies and report.technologies.get("cms"):
        try:
            cve_results = await state.cve_lookup.lookup_by_service(report.technologies["cms"], "")
            if not report.results:
                report.results.append(
                    ScanResult(tool="cve", target=plan.target, start_time=datetime.now(), success=True)
                )
            for cv in cve_results:
                if not any(v.cve == cv.cve_id for r in report.results for v in r.vulnerabilities):
                    report.results[0].vulnerabilities.append(Vulnerability(
                        name=f"CVE: {cv.cve_id} — {cv.description[:100]}",
                        severity=cv.severity,
                        cve=cv.cve_id,
                        cvss=cv.cvss_score,
                        url=cv.url,
                    ))
        except Exception as e:
            logger.warning("CVE enrichment failed for %s: %s", report.technologies["cms"], e, exc_info=True)

    return {
        "id": report.id,
        "target": report.target,
        "intent": plan.intent,
        "tools": [t.tool for t in plan.tools],
        "results": [r.model_dump(mode="json", exclude_none=True) for r in report.results],
        "report_html": html_path,
        "technologies": report.technologies,
    }


@app.post("/api/quick-scan")
async def quick_scan(req: QuickScanRequest, request: Request, _=Depends(_verify_token)):
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
                            name=f"CVE: {cv.cve_id} — {cv.description[:100]}",
                            severity=cv.severity,
                            cve=cv.cve_id,
                            cvss=cv.cvss_score,
                            url=cv.url,
                        ))

    return result.model_dump(mode="json", exclude_none=True)


@app.get("/api/status")
async def status(request: Request, _=Depends(_verify_token)):
    engine = _get_engine(request)
    return {
        "name": "Nexura Scanner",
        "version": "2.0.0",
        "ai_ready": engine.is_ready,
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
        path = shutil.which(t)
        if not path and sys.platform == "win32":
            extra = {
                "nmap": r"C:\Program Files\nmap\nmap.exe",
                "nuclei": os.path.expanduser(r"~\nuclei\nuclei.exe"),
                "whatweb": os.path.expanduser(r"~\whatweb\whatweb.exe"),
            }
            if t in extra and os.path.exists(extra[t]):
                path = extra[t]
        result[t] = path is not None
    return result


# Shared terminal state for /api/terminal
_terminal_cwd_lock = threading.Lock()
_terminal_cwd = str(config.BASE_DIR)
_terminal_run_lock = threading.Lock()

ALLOWED_TERMINAL_COMMANDS = frozenset({
    "nmap", "nuclei", "nikto", "gobuster", "sqlmap",
    "ping", "nslookup", "tracert", "traceroute",
    "netstat", "ipconfig", "systeminfo", "hostname", "ver",
    "dig", "arp", "route",
    "ls", "dir", "cd", "pwd", "echo", "type", "more", "cls", "clear",
    "tasklist",
    "python", "pip",
})


def _terminal_is_allowed(cmd: str) -> bool:
    cmd_name = cmd.strip().split(None, 1)[0].lower().lstrip(".")
    return cmd_name in ALLOWED_TERMINAL_COMMANDS


@app.post("/api/terminal")
async def terminal(request: Request, _=Depends(_verify_token)):
    global _terminal_cwd, _terminal_process
    data = await request.json()
    cmd = (data.get("cmd", "") or "").strip()
    confirm = data.get("confirm", False)

    if not cmd:
        return {"output": "", "error": "", "code": -1}

    if cmd.startswith("cd"):
        parts = cmd.split(None, 1)
        target = (parts[1] if len(parts) > 1 else "").strip().strip('"').strip("'")
        with _terminal_cwd_lock:
            if not target or target == "~":
                new_path = config.BASE_DIR
            else:
                base = Path(_terminal_cwd) if not Path(target).is_absolute() else Path()
                new_path = (base / target).resolve()
            try:
                new_path.relative_to(config.BASE_DIR)
            except ValueError:
                return {"output": "", "error": "Cannot go outside project directory", "code": 1}
            if new_path.exists() and new_path.is_dir():
                _terminal_cwd = str(new_path)
                return {"output": "", "error": "", "code": 0}
            else:
                return {"output": "", "error": f"Directory not found: {target}", "code": 1}

    if not _terminal_is_allowed(cmd):
        return {"danger": True, "message": "Buyruq ruxsat etilmagan", "cmd": cmd}

    return await _run_terminal_cmd(cmd)


async def _run_terminal_cmd(cmd: str) -> dict:
    global _terminal_process
    safe_cmd = cmd.replace("`", "``").replace("$", "`$")
    ps_cmd = (
        "$ProgressPreference='SilentlyContinue'; "
        "$ExecutionContext.SessionState.LanguageMode='ConstrainedLanguage'; "
        + safe_cmd
    )
    encoded = base64.b64encode(ps_cmd.encode("utf-16-le")).decode("ascii")

    with _terminal_run_lock:
        try:
            proc = await asyncio.create_subprocess_exec(
                "powershell", "-NoProfile", "-NonInteractive",
                "-ExecutionPolicy", "Bypass",
                "-EncodedCommand", encoded,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return {"output": "", "error": "Command timed out (30s)", "code": -1}

            output = stdout.decode("utf-8", errors="replace") if stdout else ""
            error = stderr.decode("utf-8", errors="replace") if stderr else ""
            return {"output": output, "error": error, "code": proc.returncode or 0}
        except Exception as e:
            return {"output": "", "error": str(e), "code": -1}
