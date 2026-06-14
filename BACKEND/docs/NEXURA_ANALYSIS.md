# Nexura Scanner — Senior-Level Comprehensive Code Audit

**Audit Date:** 2026-05-31
**Scope:** Every file in `E:\nexura_scanner\` (excluding `venv/`, `.git/`, `node_modules/`, `nmap/`)
**Total Files Analyzed:** 50+ files across Python, TypeScript, HTML, JSON, TOML
**Issues Found:** 51 (9 Critical, 13 High, 25 Medium, 4 Low)

---

## 1. PROJECT STRUCTURE OVERVIEW

```
E:\nexura_scanner/
├── nexura/                          # Core Python package
│   ├── __init__.py
│   ├── __main__.py                  # CLI entry: "python -m nexura"
│   ├── ai_engine.py                 # Local LLM (llama-cpp-python)
│   ├── cli.py                       # Click CLI with 6 commands
│   ├── config.py                    # Global config constants
│   ├── cve_lookup.py                # CVE enrichment (DuckDuckGo + CIRCL)
│   ├── history_db.py                # SQLite scan history
│   ├── runner.py                    # Scan orchestrator
│   ├── tool_selector.py             # AI-based tool selection
│   ├── models/
│   │   └── schemas.py               # Pydantic models
│   ├── parsers/
│   │   ├── amass.py, gobuster.py, network.py
│   │   ├── nikto.py, nmap.py, nuclei.py, sqlmap.py
│   │   └── __init__.py
│   ├── report/
│   │   ├── generator.py             # HTML/JSON report generator
│   │   └── templates/report.html    # Jinja2 report template
│   ├── scanners/
│   │   └── network.py               # Port scanner + tech detection
│   └── web/
│       ├── __init__.py
│       └── app.py                   # FastAPI web UI (274 lines)
├── web_app.py                       # ⚠ DUPLICATE: Flask web UI (244 lines)
├── app.py                           # ⚠ DEAD: Textual TUI (159 lines)
├── frontend/                        # React + Vite frontend
│   ├── src/                         # TypeScript source
│   ├── dist/                        # Built frontend
│   └── package.json
├── templates/
│   └── index.html                   # Flask frontend template
├── tests/                           # Sparse test coverage
├── reports/                         # Generated scan reports
├── config.json                      # API keys + settings
├── pyproject.toml                   # Python project config
└── requirements.txt                 # ⚠ DUPLICATE of pyproject.toml
```

---

## 2. 🔴 CRITICAL ISSUES (Fix Immediately)

### C1 — Command Injection: `shell=True` in Textual App
**File:** `app.py:41-43`
```python
result = subprocess.run(cmd, shell=True, ...)
```
**Risk:** User-controlled `cmd` runs via `cmd.exe /c`. `nmap; rm -rf /` executes both.
**Fix:** Remove `app.py` entirely (dead code). If kept, use `-EncodedCommand`.

### C2 — Command Injection via PowerShell (web_app.py)
**File:** `web_app.py:114-119`
```python
wrapped = "$ProgressPreference='SilentlyContinue'; " + cmd
encoded = ps_encode(wrapped)
subprocess.run(["powershell", "-EncodedCommand", encoded], ...)
```
**Risk:** Base64 encoding does NOT prevent injection. `$(Invoke-Expression "malicious")` still executes. The "dangerous keywords" guard uses substring matching (`kw in cl`) which is trivially bypassed (e.g., PowerShell's `r`+`m`+` `+`-r`+`f`).
**Fix:** Use PowerShell `-NoLanguage` / `-RestrictedLanguage` mode. Implement actual command whitelisting or parameterized execution.

### C3 — Three Separate Web Applications (Identity Crisis)
**Files:**
- `nexura/web/app.py` — FastAPI (the "real" new UI)
- `web_app.py` — Flask (launched by `start.bat`)
- `app.py` — Textual TUI (dead code)
- `frontend/` — React + Vite (separate frontend for FastAPI)

**Risk:** Duplicated logic in both Flask and FastAPI (both have chat, terminal, scan endpoints). Different dependency requirements (Flask not in pyproject.toml). Confusion about which is the "real" app. `start.bat` launches Flask, but the modern React frontend talks to FastAPI. The Flask version has no React frontend — it uses a raw HTML template.
**Fix:** Choose ONE framework (FastAPI is recommended — already has more features, async support, React frontend). Delete `web_app.py`, `app.py`, `templates/index.html`. Update `start.bat`.

### C4 — Event Loop Mismanagement (runner.py)
**File:** `nexura/runner.py:75-80`
```python
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
cve_results = loop.run_until_complete(self._enrich_with_cves(result.ports))
loop.close()
```
**Risk:** Creating a new event loop for every scan with ports. Causes "Event loop is closed" errors on some Python versions. Wastes resources.
**Fix:** Use `asyncio.run(self._enrich_with_cves(...))` or make `run()` fully async.

### C5 — Synchronous AI Engine Blocks Async Context
**File:** `nexura/ai_engine.py:40-53`, `nexura/runner.py:75-80`
```python
# ai_engine.py - synchronous llama_cpp call (10-60s)
response = self._llm(...)
```
**Risk:** Blocking the async event loop for 10-60 seconds during LLM inference. The `run_in_executor` in runner.py helps but wraps everything in a thread without bounds.
**Fix:** Make `AIEngine` fully async with `loop.run_in_executor()`. Use bounded `ThreadPoolExecutor`.

### C6 — Silent Exception Swallowing Everywhere
**Files:**
- `nexura/scanners/network.py:166` — `except Exception: pass`
- `nexura/web/app.py:105-106` — `except Exception: pass`
- `nexura/web/app.py:128-129` — `except Exception: pass`
- `nexura/scanners/network.py:189` — `except Exception: return False, 0.0`
- `nexura/scanners/network.py:238` — `except Exception: return "UNKNOWN"`
- `nexura/runner.py:90-91` — `logger.warning(...)` but still continues
- `nexura/history_db.py` — returns `[]`/`None`/`{}` on error

**Risk:** Hides `KeyboardInterrupt`, `SystemExit`, `MemoryError`, and genuine bugs. Silent data loss. Impossible to debug production issues.
**Fix:** NEVER use bare `except:`. Always: `except SpecificException as e: logger.error(..., exc_info=True)`.

### C7 — Thread-Safety Violations (web_app.py)
**File:** `web_app.py:29-31, 182-226`
```python
_conversation_history = []  # no lock
_running_process = None     # check-then-act race
```
**Risk:** Flask runs multiple threads. Concurrent requests to `chat()` and `chat_history()` can corrupt the list. `cancel_command()` has TOCTOU race on `_running_process`.
**Fix:** Protect ALL shared state with `threading.Lock()`. Use atomic operations.

### C8 — AI Parse Failure Yields Empty Scan Plan Silently
**File:** `nexura/tool_selector.py:54-65`
```python
try:
    tool_type = ToolType(tool_name)
except ValueError:
    continue  # silently skips ALL invalid tools
```
**Risk:** If AI hallucinates invalid tool names, ALL tools are skipped. Empty tool list → scan does nothing with no error.
**Fix:** If no valid tools remain, raise error or use fallback plan.

### C9 — Zero Tests for Core Scanning Logic
**Missing tests for:**
- `ScanRunner.run()` — the most critical function
- `ScanRunner._execute()` — subprocess handling
- `ToolSelector.create_plan()` — AI orchestration
- `AIEngine.ask()` / `ask_structured()`
- ALL web endpoints (both Flask and FastAPI)

---

## 3. 🔶 HIGH ISSUES

### H1 — API Key in Plaintext (config.json)
**File:** `config.json:2`
**Risk:** If committed to git or filesystem exposed, API key is compromised.
**Fix:** Use `os.getenv("OPENAI_API_KEY")` as primary source.

### H2 — Sequential Port Scanning (network.py)
**File:** `nexura/scanners/network.py:55-62`
```python
for port in ports:
    is_open, latency = self._tcp_connect(ip, port)
```
**Risk:** 25 ports × 2s timeout = 50s worst case. 65535 ports would take 36+ hours.
**Fix:** Use `ThreadPoolExecutor(max_workers=50)` or `asyncio.open_connection()`.

### H3 — Bounded Thread Pool Missing (runner.py)
**File:** `nexura/runner.py:108-110`
```python
return await loop.run_in_executor(None, self.run, command, target)
```
**Risk:** `None` uses default executor — unbounded thread creation during multi-tool scans.
**Fix:** `self._executor = ThreadPoolExecutor(max_workers=4)`.

### H4 — Global Mutable State (nexura/web/app.py)
**File:** `nexura/web/app.py:30-36`
```python
runner = ScanRunner()      # module-level singleton
reporter = ReportGenerator()
scanner = NetworkScanner()
history_db = HistoryDB()
```
**Risk:** Shared state across all requests. Concurrent requests interfere.
**Fix:** Use FastAPI `Depends()` or `app.state`.

### H5 — Module-Level Side Effects on Import (config.py)
**File:** `nexura/config.py:8-9`
```python
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)
```
**Risk:** Simply importing `nexura` creates directories. Fails in read-only environments.
**Fix:** Lazy initialization on first use.

### H6 — Subprocess Exit Codes Ignored (runner.py)
**File:** `nexura/runner.py:66-71`
```python
result.success = True  # ALWAYS True, even on crash/timeout
```
**Risk:** Failed scans (nmap on invalid target, nuclei with bad template) appear successful.
**Fix:** `result.success = (returncode == 0)`.

### H7 — Inline Imports Hiding Circular Dependencies
**Files:** `nexura/cli.py`, `nexura/runner.py`, `nexura/web/app.py`, `nexura/ai_engine.py`
**Risk:** Obscures dependency graph. Small performance overhead. Hides `ImportError` until runtime.
**Fix:** Top-level imports. Restructure to eliminate circular deps.

### H8 — Database Transaction Inconsistency (history_db.py)
**File:** `nexura/history_db.py:100-156`
```python
# DELETE vulnerabilities, DELETE ports, INSERT session
# INSERT vulns, INSERT ports — NOT in single transaction
```
**Risk:** Partial crash leaves database in inconsistent state.
**Fix:** Wrap ALL operations in `BEGIN`/`COMMIT`.

### H9 — No Rate Limiting on Any Endpoint
**Files:** All API endpoints
**Risk:** `/api/chat` calls OpenAI API — unbounded cost. `/api/scan` spawns subprocesses.
**Fix:** Add `slowapi` or `flask-limiter`.

### H10 — Test Mutates Global State (test_history_db.py)
**File:** `tests/test_history_db.py:8-13`
```python
original = hdb.DB_PATH
hdb.DB_PATH = tmp_path / "test_nexura.db"  # monkey-patches global
```
**Risk:** If test crashes, other tests use wrong DB. Not parallel-safe.
**Fix:** Add `DB_PATH` parameter to `HistoryDB.__init__()`.

### H11 — Flask Not in pyproject.toml
**File:** `web_app.py` depends on Flask
**Fix:** Add `flask>=3.0` or eliminate Flask version.

### H12 — Version Mismatch: pyproject.toml vs requirements.txt
**Risk:** Two dependency files with different versions will diverge.
**Fix:** Single source of truth in `pyproject.toml`. Remove `requirements.txt`.

### H13 — Tight Coupling, No Dependency Injection
**Risk:** `ScanRunner` directly instantiates `CVELookup()`, `NetworkScanner()`. `ToolSelector` depends on concrete `AIEngine`. Impossible to unit test without monkey-patching.
**Fix:** Abstract Base Classes / Protocols. Constructor injection.

---

## 4. 🟡 MEDIUM ISSUES

| # | File | Issue | Fix |
|---|------|-------|-----|
| M1 | `network.py:183` | 4s socket timeout too aggressive | Make configurable |
| M2 | `web_app.py:105-108` | Path traversal in `cd` — no project root restriction | Validate path is within project |
| M3 | `network.py:9` | `import random` — unused | Remove |
| M4 | `cli.py:77` | `__import__("datetime")` — code smell | `from datetime import datetime` |
| M5 | `runner.py:13` | `PARSER_MAP` mutable global | Make class-level constant |
| M6 | `history_db.py:230` | `PRAGMA foreign_keys` not in `_get_conn()` | Move to connection creation |
| M7 | `web_app.py` | Unbounded `_conversation_history` growth | Use `collections.deque(maxlen=200)` |
| M8 | `web_app.py:172-179` | `kill()` may orphan child processes | Use job object |
| M9 | `index.html:92-98` | localStorage prototype pollution | Use reviver in `JSON.parse()` |
| M10 | `cve_lookup.py:94` | Silent empty results on failure | Add warning to scan summary |
| M11 | `network.py:146-148` | `verify=False` disables SSL verification | Remove or make configurable |
| M12 | `report/generator.py:37` | String path concatenation | Use `Path.with_suffix()` |
| M13 | `web_app.py` | Multi-language error messages (Uzbek/English/Russian) | Standardize on English |
| M14 | Codebase | Inconsistent style (quotes, `Optional[str]` vs `str \| None`) | Use Black + Ruff |
| M15 | `nexura/web/app.py` | CORS not configured | Add CORSMiddleware |
| M16 | `tests/` | No mock tests | Use `unittest.mock.patch()` |
| M17 | `tool_selector.py:39-41` | No target validation before AI/subprocess | Validate hostname/IP/URL |
| M18 | `runner.py:75-80` | Event loop leak — loop not properly cleaned | Use `asyncio.run()` |
| M19 | `network.py:248-261` | DNS cache TOCTOU race | Hold lock during lookup |
| M20 | `web_app.py` | No graceful degradation for missing AI key in chat | Already has basic check |
| M21 | `config.json` | `nmap_path` still relative | Already fixed in web_app.py |
| M22 | `history_db.py:87-98` | No WAL mode for SQLite | `PRAGMA journal_mode=WAL` |
| M23 | `parsers/*.py` | All parsers return untyped `dict` | Define Pydantic models |
| M24 | All endpoints | No input length validation | `Field(max_length=...)` |
| M25 | `web_app.py:203` | API key sent over HTTP | Warn on startup |

---

## 5. 🟢 LOW ISSUES

| # | File | Issue |
|---|------|-------|
| L1 | `nexura/web/__init__.py` | Empty file |
| L2 | `nexura/report/__init__.py` | Empty file |
| L3 | `tests/__init__.py` | Empty file |
| L4 | `report/generator.py:38` | `model_dump(mode="json")` usage fine but inconsistent |

---

## 6. ARCHITECTURAL MAP

```
User
├── CLI (nexura/cli.py)
│   └── Click commands: scan, web, history, config, tools, download-model
│
├── Web (FastAPI) (nexura/web/app.py)
│   └── React Frontend (frontend/)
│       ├── /api/scan              → ScanRunner.run()
│       ├── /api/history           → HistoryDB
│       ├── /api/config            → config.py
│       └── /api/tools             → tool_selector.py
│
├── Web (Flask) (web_app.py) ⚠ DUPLICATE
│   └── Raw HTML (templates/index.html)
│       ├── /api/terminal          → subprocess
│       ├── /api/chat              → OpenAI API
│       └── /api/config            → config.json
│
└── Textual (app.py) ⚠ DEAD
    └── Terminal UI (not used)

Core Pipeline:
    ToolSelector.create_plan(prompt)
        → List[ToolCommand]
            → ScanRunner.run(tool, target)
                → subprocess(tool_binary, args)
                    → Parser.parse(raw_output)
                        → Pydantic ScanResult
                            → CVELookup.enrich(ports) [async]
                                → HistoryDB.save(report)
                                    → ReportGenerator.generate(report)
                                        → HTML/JSON files
```

---

## 7. FILE-BY-FILE ISSUE MAP

| File | Lines | Issues |
|------|-------|--------|
| `nexura/ai_engine.py` | 78 | C5, H7, H13 |
| `nexura/cli.py` | 125 | H7, M4 |
| `nexura/config.py` | 32 | H5 |
| `nexura/cve_lookup.py` | 110 | M10, M16 |
| `nexura/history_db.py` | 310 | H8, M6, M22, M23 |
| `nexura/runner.py` | 130 | C4, H3, H6, H7, H13, M5, M18 |
| `nexura/tool_selector.py` | 95 | C8, H13, M17 |
| `nexura/scanners/network.py` | 270 | C6, H2, M1, M3, M11, M19 |
| `nexura/parsers/nmap.py` | 145 | M23 |
| `nexura/parsers/*.py` | ~400 total | M23 |
| `nexura/report/generator.py` | 80 | M12, L4 |
| `nexura/web/app.py` | 274 | C3, H4, H7, M15, M24 |
| `web_app.py` | 244 | C2, C3, C7, M2, M7, M8, M9, M13, M20, M25 |
| `app.py` | 159 | C1, C3, L1 |
| `templates/index.html` | 304 | M9, M13 |
| `frontend/src/*` | ~2000 | (not deeply analyzed) |
| `tests/*.py` | ~250 | C9, H10, M16 |
| `pyproject.toml` | ~50 | H11, H12 |

---

## 8. FIX PRIORITY MATRIX

```
Priority Matrix:
                    Easy Fix                     Complex Fix
                ┌─────────────────┬──────────────────────────┐
  Critical      │ C6 (silent      │ C2 (PS injection)        │
  Security      │   exceptions)   │ C1 (shell=True)          │
                │ C8 (empty plan) │                           │
                ├─────────────────┼──────────────────────────┤
  High          │ H1 (API key)    │ C3 (3 apps → 1)          │
  Impact        │ H6 (exit code)  │ C5 (async AI)            │
                │ H11 (Flask dep) │ C4 (event loop)          │
                │ H12 (dup deps)  │ H13 (DI)                 │
                │ M1-M25 (most)   │ C7 (thread safety)       │
                └─────────────────┴──────────────────────────┘
```

**Quick Wins (fix in < 1 hour):**
1. C6 — Remove all `except: pass`, add logging
2. C8 — Validate tool list, raise error if empty
3. H1 — Add `os.getenv()` fallback for API key
4. H6 — Capture and use return code
5. H11/H12 — Consolidate dependencies
6. M1-M25 — Address all medium issues

**Architectural (fix in 1-3 days):**
1. C3 — Consolidate to FastAPI, remove Flask + Textual
2. C2 — Implement proper command sandboxing
3. C4/C5 — Async refactor of AI engine and runner
4. C7 — Thread safety for all shared state
5. H13 — Dependency injection for testability
6. C9 — Add tests for core scanning logic

---

## 9. VERDICT

**Code Health: POOR** — The project has strong foundational ideas (AI-guided scanning, multi-parser architecture, rich reporting) but suffers from:

1. **Architectural fragmentation** — 3 competing UIs, duplicated logic
2. **Security debt** — Command injection in ALL terminal paths
3. **Testing bankruptcy** — Core logic has zero tests
4. **Concurrency hazards** — Global state, thread safety ignored
5. **Error handling blindness** — Silent failures everywhere

The project needs a **2-3 day refactoring sprint** to address the Critical and High issues before it's ready for production use or sale.

**Immediate action items:**
1. Pick ONE web framework (FastAPI ✅) and delete the others
2. Fix command injection (use sandboxed execution)
3. Add rate limiting and input validation
4. Add logging to every `except` block
5. Write tests for `ScanRunner.run()`
