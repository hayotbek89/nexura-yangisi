# NEXURA Scanner — 2-Senior Audit (Deep Dive)

> Birinchi auditda tuzatilgan 33 ta muammodan keyin,
> yana 30 ta yangi topilma aniqlandi.

---

## 🔴 CRITICAL (5)

### C1. SQLMap parser JSON formatni parse qilmaydi
**Fayl:** `nexura/parsers/sqlmap.py:4-31`  
**Test:** `tests/test_parsers.py:50-58,101-103`  
**Muammo:** Parser faqat text output (`Parameter:`, `Title:`, `is vulnerable`) ni taniydi. Test `json.dumps()` orqali JSON uzatadi — test "is vulnerable" so'zi JSON value ichida borligi sababli **tasodifan** o'tadi. Haqiqiy SQLMap JSON output (`--output-format=json`) parse qilinmaydi.  
**Proof:** `json.dumps({"taskdata":...})` → single line → `"is vulnerable"` JSON value ichida topiladi → parser `vulns.append(...)` chaqiradi. JSON strukturasi parse qilinmayapti.

### C2. Amass parser NDJSON formatni parse qilmaydi
**Fayl:** `nexura/parsers/amass.py:6-53`  
**Test:** `tests/test_parsers.py:45-48,95-98`  
**Muammo:** Parser text format uchun yozilgan, ammo test NDJSON (JSON lines) uzatadi. Regex `r"^([a-zA-Z0-9][a-zA-Z0-9._-]+\.[a-zA-Z]{2,})\s+"` `{"name": "sub.example.com"...}` qatoriga match **qilmaydi** (qator `{` bilan boshlanadi). Test `"subdomain" in result.summary` orqali **tasodifan** o'tadi, chunki summary hardcoded `f"{len(vulns)} ta subdomain topildi"` — 0 ta bo'lsa ham "subdomain" so'zi bor.

### C3. Nmap parser regex noto'g'ri — `filtered` portlarni xato parse qiladi
**Fayl:** `nexura/parsers/nmap.py:18`  
**Muammo:** Regex `r"^(\d+)/(tcp|udp)\s+(\S+)\s+(\S+)?\s*(.*)?"`:
- `22/tcp  filtered  ssh` → guruhlar: `port=22`, `proto=tcp`, `state=filtered`, `service=None`, `version=ssh`  
  **Service "ssh" emas, "unknown" bo'lishi kerak, version `None` bo'lishi kerak**
- `8080/tcp closed  http-alt` → guruhlar: `state=closed`, `service=http-alt`
  Bu ishlaydi, lekin `filtered` holatda buziladi

### C4. CVELookup sync/async arxitekturasi buzilgan
**Fayl:** `nexura/cve_lookup.py:70-78,80-87`  
**Muammo:** `_circl_search()` — `async def` ichida `async_req=False` bo'lganda `self._sync_client.get(url)` chaqiradi. Bu **BLOCKING** call. `_run_sync()` agar running loop bo'lsa, `run_coroutine_threadsafe()` ishlatadi. Natijada blocking call event loop thread'ida execute bo'lib, butun loopni bloklaydi.
```python
async def _circl_search(self, ..., async_req=True):
    if async_req:
        resp = await self._async_client.get(url)  # ✅ non-blocking
    else:
        resp = self._sync_client.get(url)  # ❌ BLOCKS the event loop!
```

### C5. Runner.py CVE enrichment har safar yangi CVELookup yaratadi
**Fayl:** `nexura/runner.py:104`  
**Muammo:** `_enrich_cves_sync()` har safar `CVELookup()` yaratadi → yangi `httpx.AsyncClient` + `httpx.Client`. Hech qachon `close()` qilinmaydi — client connection leak. Http client connections open file descriptors.

---

## 🟠 HIGH (10)

### H1. Nmap parser vulnerability detection primitiv
**Fayl:** `nexura/parsers/nmap.py:28-32`  
**Muammo:** `any(word in low for word in ["cve-", "cve ", "vulnerability", "vuln"])` — faqat `| ` prefiksli qatorlarda. Nmap NSE output `|_  cve-id: CVE-2024-...` formatida bo'ladi, bu yerda `|_` bilan boshlanadi, `| ` bilan emas. CVE larning ko'pchiligi topilmaydi.

### H2. ToolSelector `localhost` yoki `127.0.0.1` target validatsiyasidan o'tmaydi
**Fayl:** `nexura/tool_selector.py:43-55`  
**Test:** `tests/test_core.py:75-79`  
**Muammo:** `_validate_target("localhost")` → hostname regex **dot** talab qiladi (`\.`). `localhost` da dot yo'q — `False` qaytaradi. Ammo `_validate_target("127.0.0.1")` → IP regex orqali `True`. Bu `localhost` target ishlatilganda AI target override qiladi yoki fallback plan ishlatiladi.

### H3. Web UI agentic scan target inconsistency
**Fayl:** `nexura/web/app.py:136`  
**Muammo:** `selector.run_agentic_scan_async(req.prompt, req.target, state.runner)` — `req.target` uzatiladi, lekin `create_plan_async()` AI dan kelgan target bilan ishlaydi. Agar AI target'ni o'zgartirsa, agentic scan eski target bilan ishlaydi. `tool_selector.py:109` da `plan.target` ishlatiladi.

### H4. Config.py default model filename noto'g'ri
**Fayl:** `nexura/config.py:17`  
**Skript:** `scripts/download_model.py:48-50`  
**Muammo:** Config default: `qwen2.5-7b-instruct-q4_k_m.gguf`  
Download skript default: `Qwen2.5-7B-Instruct.Q4_K_M.gguf`  
**Ikkala fayl nomi har xil!** Model yuklab olinsa, config uni topa olmaydi.

### H5. `datetime.utcnow()` deprecated
**Fayl:** `nexura/scanners/network.py:202`  
**Muammo:** `datetime.utcnow()` Python 3.12+ da deprecated. Ishlaydi, lekin warning beradi. 
```python
now_utc = datetime.utcnow()  # ❌ deprecated
# ✅ to'g'ri: datetime.now(datetime.UTC)
```

### H6. HistoryDB stats error path incomplete
**Fayl:** `nexura/history_db.py:310-312`  
**Muammo:** Error holatida `{"total_scans": 0, "total_vulns": 0, "critical_count": 0}` qaytaradi, lekin success path `most_scanned_target`, `this_week_scans` ham qo'shadi. API consumer'lar `KeyError` olishi mumkin.

### H7. Gobuster parser JSON output formatini parse qilmaydi
**Fayl:** `nexura/parsers/gobuster.py:10-13`  
**Muammo:** Regex faqat `gobuster dir` text output formatini taniydi: `/path (Status: 200)`. JSON output (`-o json`, `-o jsonl`) parse qilinmaydi.

### H8. Nikto severity detection random
**Fayl:** `nexura/parsers/nikto.py:12-17`  
**Muammo:** `low_kw = ["info", "warning", "caution", "notice"]` — hech qanday keyword bo'lmasa, default `"medium"`. `high_kw = ["critical", "vulnerability", "exploit", "cve"]` — agar "vulnerability" so'zi bo'lsa, `"high"`. Bu hech qanday real severity'ga asoslanmagan.

### H9. Parser test'lari haqiqiy output'ni emas, balki mock output'ni test qiladi
**Test:** `tests/test_parsers.py`  
**Muammo:** Barcha test output'lari manual yozilgan va real tool output'laridan farq qiladi:
- Nmap: real output XML format, test text format  
- Nuclei: real output JSON lines, test `[severity]` text format  
- Gobuster: real output `Progress: ...` lines qo'shib yuboradi  
- Amass: real NDJSON, parser text format kutadi

### H10. `run_agentic_scan_async` thread safety
**Fayl:** `nexura/tool_selector.py:106-171`  
**Muammo:** Agentic loop `used_tools` set'ini o'zgartirmoqda, har bir iteration `all_results.append()`. Bu method bir vaqtning o'zida bir necha marta chaqirilsa (e.g., web UI multiple requests) — race condition.

---

## 🟡 MEDIUM (9)

### M1. Parser'lar `raw.splitlines()` ishlatadi — JSON single line bo'lsa ishlamaydi
**Barcha parser'lar:** `nuclei.py`, `nikto.py`, `sqlmap.py`, `gobuster.py`, `amass.py`  
**Muammo:** `raw.splitlines()` JSON/JSONL output'da faqat bitta yoki bir necha qator qaytaradi. Parser'lar har bir qatorni alohida parse qiladi, lekin JSON strukturani parse qilmaydi.

### M2. SQLite `datetime('now')` vs ISO string comparison
**Fayl:** `nexura/history_db.py:291-294`  
**Muammo:** `scan_date` string formatda saqlanadi (`datetime.now().isoformat()` → `"2026-05-31T12:00:00"`). Keyin `WHERE scan_date >= datetime('now', '-7 days')` bilan solishtiriladi. SQLite `datetime()` UTC formatda qaytaradi, ISO string bilan solishtirish timezone farqi sababli to'g'ri ishlamasligi mumkin.

### M3. ReportGenerator JSON'da `technologies` yo'qoladi
**Fayl:** `nexura/report/generator.py:39`  
**Muammo:** `report.model_dump(mode="json", exclude_none=True)` — `technologies=None` bo'lsa, JSON faylga yozilmaydi. HTML template `technologies` dict'ini tekshiradi, lekin JSON faylda bu field yo'q.

### M4. AI Engine `import concurrent.futures` redundant
**Fayl:** `nexura/ai_engine.py:61,76`  
**Muammo:** `ask()` va `ask_with_timeout()` ichida `import concurrent.futures` qilingan. Yuqorida `from concurrent.futures import ThreadPoolExecutor` import qilingan. Bu redundant import.

### M5. Web terminal `cwd` locking vs `cd` command
**Fayl:** `nexura/web/app.py:352,386`  
**Muammo:** `cd` command path validation `new_path.relative_to(config.BASE_DIR)` qiladi, lekin terminal `_run_terminal_cmd` da `cwd` parametri umuman ishlatilmaydi — PowerShell command'ining o'zida `Set-Location` qilinmaydi. CWD o'zgaradi, lekin keyingi command'lar eski CWD da ishlaydi.

### M6. `ALLOWED_TERMINAL_COMMANDS` da `findstr` / `find`
**Fayl:** `nexura/web/app.py:338`  
**Muammo:** `"findstr"` va `"find"` allowlist'da. `find` Windows'da `find /i "text" file.txt` bilan ishlatiladi, `findstr` esa `findstr /s "text" *` bilan. Bu xavfli emas, lekin White hat uchun foydali emas.

### M7. Frontend static files mounting hardcoded path
**Fayl:** `nexura/web/app.py:32,37`  
**Muammo:** `FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"` — Frontend built bo'lmasa, `/assets` mount qilinmaydi. Frontend built bo'lsa ham, faqat `/assets` path'i mount qilinadi, `/` esa alohida route.

### M8. `__main__.py` faqat CLI ishlatadi
**Fayl:** `nexura/__main__.py`  
**Muammo:** `python -m nexura` → `cli()` chaqiradi. Web UI ishlatish uchun `python -m nexura web` kerak. Lekin `start.bat` `python -m nexura web` ni chaqiradi. Bu to'g'ri, lekin `__main__.py` buni dokumentatsiyada ko'rsatmaydi.

### M9. Service mapping `port_by_service_name` ambiguous
**Fayl:** `nexura/models/services.py:30-38`  
**Muammo:** `"http" in name_lower` → "http" "https" dagi substring. `best_len` comparison bilan ishlaydi, lekin `"smtp" in "smtps"` → True. `"smtps"` mapping'da yo'q, shuning uchun `smtp` qaytaradi (25). Agar kelajakda `smtps` qo'shilsa, bug bo'lishi mumkin.

---

## 🟢 LOW (6)

### L1. Testda amass parser summary tekshiruvi tasodifiy
**Fayl:** `tests/test_parsers.py:97-98`  
**Muammo:** `"subdomain" in result.summary.lower()` — parser 0 ta subdomain topsa ham summary `"0 ta subdomain topildi"` qaytaradi, test o'tadi.

### L2. `_validate_target` URL `http://localhost:8080` formatida ishlamaydi
**Fayl:** `nexura/tool_selector.py:52`  
**Muammo:** URL regex `localhost` hostname'ni talab qiladi, lekin `http://localhost:8080/path` da `8080` port raqami bor. Port raqami URL ning bir qismi emas, regex buni tushunmaydi.

### L3. Report generator `save` return type chigal
**Fayl:** `nexura/report/generator.py:31,49`  
**Muammo:** `save()` → `fmt="json"` bo'lsa `str(json_path)` qaytaradi, `fmt="html"` bo'lsa `str(html_path)`, `fmt="both"` bo'lsa `str(html_path)`. `fmt="json"` holatda `Path.with_suffix()` `Path` object qaytaradi. `str()` ishlatilgan, lekin `base.with_suffix(".json")` da `json_path` allaqachon `Path`. Bu noto'g'ri emas, lekin confusing.

### L4. Scanner `WELL_KNOWN_SERVICES` prefiks
**Fayl:** `nexura/scanners/network.py` (import)  
**Muammo:** `from nexura.models.services import DEFAULT_PORTS, WELL_KNOWN_SERVICES` — imported lekin `WELL_KNOWN_SERVICES` ishlatilmaydi (to'g'ridan-to'g'ri dict subscript orqali). Scanner ichida `WELL_KNOWN_SERVICES.get(port, "unknown")` ishlatilgan, bu to'g'ri.

### L5. `start.bat` da `venv\Scripts\python.exe` hardcode
**Fayl:** `start.bat:4`  
**Muammo:** `"venv\Scripts\python.exe"` — path hardcode qilingan. Agar Python venv boshqa nomda bo'lsa (e.g., `.venv`) yoki boshqa joyda bo'lsa, ishlamaydi.

### L6. `conftest.py` yo'q, pytest fixtures takrorlanadi
**Test fayllari:** `test_history_db.py`, `test_integration.py`  
**Muammo:** `tmp_path` fixture bir necha faylda ishlatilgan, lekin umumiy `conftest.py` yo'q. Helper function'lar `test_history_db.py:8` da `_get_test_db` har bir test faylida qayta yozilgan.

---

## Audit Comparison

| | 1-audit | 2-audit |
|---|---|---|
| CRITICAL | 4 | 5 |
| HIGH | 7 | 10 |
| MEDIUM | 8 | 9 |
| LOW | 8 | 6 |
| INFO | 6 | — |
| **Total** | **33** | **30** |

**2-audit fokus:** Parser real output formatlari bilan ishlash qobiliyati, sync/async arxitekturasi, thread safety, va test coverage sifati.
