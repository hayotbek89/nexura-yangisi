from __future__ import annotations

from contextlib import asynccontextmanager
import asyncio
import base64
import json
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
from nexura.history_db import HistoryDB
from nexura.models.schemas import ScanResult, Vulnerability
from nexura.report.generator import ReportGenerator
from nexura.runner import ScanRunner
from nexura.scanners.network import NetworkScanner
from nexura.tool_selector import ToolSelector
from nexura.verification import DomainVerification, extract_domain, is_private_target

# In-memory conversation store: session_id -> list of messages
_chat_sessions: dict[str, list] = {}
_verifier = DomainVerification()

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
        app.state.engine = AIEngine()
        app.state.selector = ToolSelector(app.state.engine) if app.state.engine.is_ready else None
        app.state.cve_lookup = CVELookup()
    yield
    if hasattr(app.state, "cve_lookup"):
        await app.state.cve_lookup.close()
    if hasattr(app.state, "engine"):
        app.state.engine.close()
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


class QuickScanRequest(BaseModel):
    target: str = Field(max_length=500)


class TerminalRequest(BaseModel):
    cmd: str = Field(max_length=1000)

class VerifyRequest(BaseModel):
    domain: str = Field(max_length=500)

class VerifyCheckRequest(BaseModel):
    domain: str = Field(max_length=500)

class TosAcceptRequest(BaseModel):
    user_identifier: str = Field(default="default", max_length=100)
    tos_version: str = Field(default="1.0", max_length=20)


def _get_engine(request: Request) -> AIEngine:
    return request.app.state.engine

def _get_selector(request: Request) -> ToolSelector | None:
    return request.app.state.selector


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
    if not selector:
        engine = state.engine
        if not engine.is_ready:
            return JSONResponse(
                status_code=503,
                content={"error": "AI Engine yoqilmagan. GGUF model faylini joylashtiring."},
            )
        selector = ToolSelector(engine)
        state.selector = selector

    plan = await selector.create_plan_async(req.prompt, target)

    if plan.target in (None, "unknown", ""):
        return JSONResponse(status_code=400, content={"error": "Target aniqlanmadi. Iltimos, sayt manzilini kiriting."})

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
    engine = _get_engine(request)
    is_ready = engine.is_ready
    return {
        "name": "Nexura Scanner",
        "version": "2.0.0",
        "ai_ready": is_ready,
        "model_loaded": is_ready,
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


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest, request: Request, _=Depends(_verify_token)):
    engine = request.app.state.engine
    if not engine.is_ready:
        return {"response": "AI yordamchisi sozlanmagan. GEMINI_API_KEY ni .env faylga qo'shing.", "scan_data": None}

    # Get or create conversation history for this session
    sid = req.session_id
    if sid not in _chat_sessions:
        _chat_sessions[sid] = []

    conv = _chat_sessions[sid]

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

    result = await engine.chat(req.message.strip(), conv)
    _chat_sessions[sid] = result["history"]

    # Build scan_data if tools were used
    scan_data = None
    if result["tool_calls"]:
        target_from_tools = result["tool_calls"][0].get("input", {}).get("target", target or "unknown")
        try:
            await verify_scan_permission(target_from_tools, request)
        except HTTPException as e:
            return {"response": e.detail["error"], "scan_data": None}
        await _log_scan_start(request.app.state, target_from_tools, request)
        scan_data = {
            "target": target_from_tools,
            "tools": result["tool_calls"],
            "results": [],
        }
        await _log_scan_end(request.app.state, target_from_tools, request, "AI agentic scan")

    return {
        "response": result["response"],
        "scan_data": scan_data,
    }


# ---- Scan Permission Middleware ----

async def verify_scan_permission(target: str | None, request: Request):
    if not target:
        return
    domain = extract_domain(target)
    user_id = "default"

    # 1. ToS check
    loop = asyncio.get_event_loop()
    tos_ok = await loop.run_in_executor(None, request.app.state.history_db.is_tos_accepted, user_id)
    if not tos_ok:
        raise HTTPException(
            status_code=403,
            detail={"error": "Avval foydalanish shartlarini qabul qiling", "code": "TOS_NOT_ACCEPTED"},
        )

    # 2. Private target / own domain — skip verification
    if is_private_target(domain) or domain == "nexuraai.uz":
        return

    # 3. Domain verification check
    verified = await loop.run_in_executor(None, request.app.state.history_db.is_domain_verified, domain)
    if not verified:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Domen tasdiqlanmagan. Avval /api/verify/request orqali domeningizni tasdiqlang.",
                "code": "DOMAIN_NOT_VERIFIED",
            },
        )


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
            None,
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
    if not selector:
        engine = state.engine
        if not engine.is_ready:
            return JSONResponse(status_code=503, content={"error": "AI Engine yoqilmagan"})
        selector = ToolSelector(engine)
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
    if not selector:
        engine = state.engine
        if not engine.is_ready:
            return JSONResponse(status_code=503, content={"error": "AI Engine yoqilmagan"})
        selector = ToolSelector(engine)
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

@app.post("/api/terminal")
async def run_terminal(req: TerminalRequest, request: Request, _=Depends(_verify_token)):
    cmd = req.cmd.strip()
    if not cmd:
        return {"output": "", "error": "Bo'sh buyruq", "code": -1}

    try:
        cmd_args = shlex.split(cmd)
    except Exception as e:
        return {"output": "", "error": f"Buyruq formatida xatolik: {e}", "code": -1}

    if not cmd_args:
        return {"output": "", "error": "Bo'sh buyruq", "code": -1}

    binary = cmd_args[0]
    binary_clean = binary.lower().lstrip(".").rstrip(".exe")
    
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
