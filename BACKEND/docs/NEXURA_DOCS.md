# NEXURA Scanner — To'liq Hujjat

> **Versiya:** 2.0.0 (Web API: 2.0.0)  
> **Litsenziya:** MIT (METATRON dan ilhomlangan)  
> **Til:** Python 3.10+, React 19  
> **Yaratilgan:** 2026

---

## Mundarija

1. [Nima bu Nexura?](#1-nima-bu-nexura)
2. [Arxitektura](#2-arxitektura)
3. [Texnologiyalar](#3-texnologiyalar)
4. [Qanday ishlaydi?](#4-qanday-ishlaydi)
5. [Modullar tavsifi](#5-modullar-tavsifi)
6. [Mavjud vositalar (Tool'lar)](#6-mavjud-vositalar-tooltar)
7. [API endpointlar](#7-api-endpointlar)
8. [Frontend (UI)](#8-frontend-ui)
9. [Ma'lumotlar bazasi](#9-malumotlar-bazasi)
10. [Hozirgi holat](#10-hozingi-holat)
11. [Loyiha tartiblash](#11-loyiha-tartiblash-2026-06-12)
12. [Ishga tushirish](#12-ishga-tushirish)
13. [Qo'llaniladigan buyruqlar](#13-qollaniladigan-buyruqlar)

---

## 1. Nima bu Nexura?

**Nexura Scanner** — bu **AI yordamida ishlaydigan zaiflik skaneri**. Tabiiy tilda (o'zbek/ingliz) berilgan buyruqlarni tahlil qilib, tegishli xavfsizlik vositalarini avtomatik tanlab ishga tushiradi.

**Asosiy imkoniyatlar:**
- Tabiiy til buyruqlarini tushunadi ("example.com ni zaifliklarga tekshir")
- AI orqali eng mos vositalarni tanlaydi
- Agentic rejimda AI o'zi natijalarga qarab qo'shimcha skanerlash vositalarini tanlaydi
- Web UI, CLI va REST API orqali ishlatish mumkin
- Offline AI (local GGUF model)
- To'liq O'zbek tilida interfeys
- Avtomatik hisobot yaratish (HTML + JSON)
- CVE ma'lumotlar bazasi bilan boyitish
- Scan tarixi va statistikasi

---

## 2. Arxitektura

```
nexura_scanner/
├── FRONTEND/                      # React SPA
│   ├── src/
│   │   ├── App.jsx                # Root (tema, routing)
│   │   ├── ScannerContext.jsx     # Global state
│   │   └── components/
│   │       ├── Scanner.jsx        # Asosiy skaner sahifasi
│   │       ├── Sidebar.jsx        # Navigatsiya
│   │       ├── History.jsx        # Tarix
│   │       ├── Reports.jsx        # Hisobotlar
│   │       └── Settings.jsx       # Sozlamalar
│   └── dist/                      # Vite build
│
├── BACKEND/
│   ├── nexura/                    # Asosiy Python backend
│   │   ├── __main__.py            # CLI entry point
│   │   ├── cli.py                 # Click buyruqlar
│   │   ├── config.py              # Sozlamalar (.env + env vars)
│   │   ├── ai_engine.py           # Local AI (llama-cpp-python)
│   │   ├── tool_selector.py       # AI tool tanlash + agentic loop
│   │   ├── runner.py              # Scanlarni bajarish
│   │   ├── cve_lookup.py          # CVE qidirish (CIRCL API)
│   │   ├── history_db.py          # SQLite ma'lumotlar bazasi
│   │   ├── models/
│   │   │   ├── schemas.py         # Pydantic modellar
│   │   │   └── services.py        # Port/service mapping
│   │   ├── scanners/
│   │   │   └── network.py         # Built-in TCP skaner
│   │   ├── parsers/               # 8 ta parser
│   │   │   ├── nmap.py, nuclei.py, nikto.py, sqlmap.py
│   │   │   ├── gobuster.py, amass.py, whatweb.py, network.py
│   │   ├── report/
│   │   │   ├── generator.py       # Hisobot generator
│   │   │   └── templates/report.html
│   │   └── prompts/
│   │       └── system.txt         # AI system prompt
│   │
│   ├── tests/                     # Testlar (59 ta)
│   │   ├── test_api.py            # Web API testlari (14 ta)
│   │   ├── test_core.py           # Core modul testlari
│   │   ├── test_parsers.py        # Parser testlari
│   │   ├── test_schemas.py        # Schema testlari
│   │   ├── test_integration.py    # Integratsion testlar
│   │   ├── test_scanners.py       # Scanner testlari
│   │   ├── test_cve_lookup.py     # CVE testlari
│   │   └── test_history_db.py     # DB testlari
│   │
│   ├── scripts/                   # Skriptlar
│   ├── reports/                   # Hisobot fayllari
│   ├── docs/                      # Hujjatlar
│   ├── start.bat                  # Ishga tushirish
│   ├── pyproject.toml             # Python dependency
│   └── config.json                # Qo'shimcha konfig
│
├── LOCAL_AI_MODELS/               # AI model fayllari
├── SCANNING_TOOLS/                # Nmap skriptlar
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
├── .gitignore
└── README.md
```

---

## 3. Texnologiyalar

### Backend (Python)
| Texnologiya | Versiya | Vazifasi |
|-------------|---------|----------|
| Python | >=3.10 | Asosiy til |
| FastAPI | >=0.100 | REST API framework |
| Click | >=8.1 | CLI buyruqlar |
| Pydantic | >=2.0 | Ma'lumot validatsiyasi |
| llama-cpp-python | >=0.2 | Local AI (GGUF) |
| httpx | >=0.24 | HTTP so'rovlar (CVE API) |
| Jinja2 | >=3.1 | HTML report template |
| Rich | >=13.0 | CLI chiroyli output |
| Uvicorn | >=0.20 | ASGI server |
| SQLite | — | Ma'lumotlar bazasi |
| python-dotenv | >=1.0 | .env fayl supporti |

### Frontend (React)
| Texnologiya | Versiya | Vazifasi |
|-------------|---------|----------|
| React | ^19.2.6 | UI library |
| Vite | ^8.0.12 | Build tool |
| @tabler/icons-react | — | Ikonkalar |
| CSS Custom Properties | — | Dark/light tema |

### Tashqi vositalar (skaner tool'lar)
| Tool | Vazifasi | Status |
|------|----------|--------|
| nmap | Port va service skanerlash | Majburiy |
| nuclei | Zaiflik skanerlash | Majburiy |
| nikto | Web server tekshiruvi | Majburiy |
| sqlmap | SQL injection test | Majburiy |
| gobuster | Directory brute-force | Majburiy |
| amass | Subdomain discovery | Majburiy |
| whatweb | Technology fingerprint | Majburiy |

---

## 4. Qanday ishlaydi?

### 4.1. Umumiy ishlash jarayoni

```
Foydalanuvchi buyrug'i
        │
        ▼
┌──────────────────┐
│   AI Engine      │  ← System prompt + user prompt
│  (Qwen2.5-7B)   │
└────────┬─────────┘
         │ JSON: {target, intent, tools, reasoning}
         ▼
┌──────────────────┐
│  Tool Selector   │  ← JSON validatsiya + plan yaratish
└────────┬─────────┘
         │ ScanPlan(target, intent, tools[])
         ▼
┌──────────────────┐
│   Scan Runner    │  ← Har bir toolni ishga tushiradi
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌──────┐  ┌──────┐      ┌──────────┐
│nmap  │  │nuclei│  ...  │  Parser  │
└──┬───┘  └──┬───┘      └────┬─────┘
   │         │               │
   └─────────┴───────────────┘
         │ ScanResult (ports + vulns)
         ▼
┌──────────────────┐
│  CVE Enrichment  │  ← CIRCL API orqali
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Report Generator │  ← HTML + JSON hisobot
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  History DB      │  ← SQLite ga saqlash
└──────────────────┘
```

### 4.2. AI Agentic Loop

```
1-bosqich: AI plan bo'yicha tool'larni ishga tushirish
2-bosqich: Natijalarni AI ga yuborish
3-bosqich: AI "continue: true" bo'lsa, qo'shimcha tool tanlaydi
4-bosqich: Maksimal 3 marta takrorlanadi
5-bosqich: Bir xil tool+args takrorlanmaydi
```

### 4.3. Fallback mexanizmi

Agar AI ishlamasa yoki model mavjud bo'lmasa:
- Avtomatik ravishda `nmap + nuclei` ishga tushadi
- Standart portlar (22,80,443,8080) skanerlanadi
- Foydalanuvchi hech qanday xatolik ko'rmaydi

---

## 5. Modullar tavsifi

### 5.1. `config.py` — Sozlamalar
- Environment variable'lar orqali barcha sozlamalar
- `.env` faylni avtomatik yuklaydi
- Direktoriyalarni avtomatik yaratadi

**Muhim o'zgaruvchilar:**
| O'zgaruvchi | Default | Vazifasi |
|-------------|---------|----------|
| `NEXURA_MODEL` | `LOCAL_AI_MODELS/qwen2.5-7b...` | AI model yo'li |
| `NEXURA_CTX_SIZE` | 4096 | AI kontekst hajmi |
| `NEXURA_GPU_LAYERS` | 0 | GPU qatlamlari |
| `NEXURA_TEMP` | 0.1 | AI harorati |
| `NEXURA_WEB_HOST` | 0.0.0.0 | Web server host |
| `NEXURA_WEB_PORT` | 8080 | Web server port |
| `NEXURA_TIMEOUT` | 300 | Scan timeout (s) |
| `NEXURA_API_KEY` | — | API kalit |
| `NEXURA_SCANNER_WORKERS` | auto | Ishchi threadlar |

### 5.2. `ai_engine.py` — AI Engine
- Qwen2.5-7B-Instruct modelini `llama-cpp-python` orqali yuklaydi
- Singleton pattern (bir marta yuklanadi)
- `ask()` — sync AI chaqiruv
- `ask_async()` — async AI chaqiruv
- `ask_structured()` — JSON javobni avtomatik parse qiladi
- `_call_llm()` — core LLM chaqiruv (DRY)
- ThreadPoolExecutor (4 workers) orqali ishlaydi

### 5.3. `tool_selector.py` — Tool Selector
- AI dan JSON formatida plan so'raydi
- Target validatsiyasi (regex: hostname, IP, URL)
- Fallback plan (AI ishlamasa nmap+nuclei)
- Agentic loop (3 iteratsiyagacha)
- Bir xil tool takrorlanmasligi kafolatlanadi

### 5.4. `runner.py` — Scan Runner
- Har bir toolni `subprocess` orqali ishga tushiradi
- Outputni parser orqali o'qiladigan formatga o'tkazadi
- CVE enrichment (topilgan service'lar bo'yicha)
- NETWORK tool uchun built-in skaner

### 5.5. `cve_lookup.py` — CVE Lookup
- CIRCL API orqali CVE ma'lumotlarini qidiradi
- In-memory caching (LRU, 3600s TTL)
- Async va sync metodlar
- CVSS score -> Severity conversion

### 5.6. `scanners/network.py` — Built-in TCP Scanner
- Python socket orqali TCP port skanerlash
- 50 ta parallel worker
- **SSRF prevention** (private IP bloklanadi)
- DNSCache (LRU, 1000 entries)
- SSL sertifikat tekshiruvi
- WAF detection
- Technology detection (whatweb + HTTP headers)

### 5.7. `history_db.py` — SQLite Database
- 4 ta jadval: `sessions`, `vulnerabilities`, `ports`, `ai_analysis`
- WAL mode (performance)
- Thread-safe (`threading.local()`)
- Transaction-based (BEGIN/COMMIT/ROLLBACK)
- CASCADE DELETE
- Statistika funksiyalari

### 5.8. Parsers (8 ta)

| Parser | JSON | Text | Vazifasi |
|--------|------|------|----------|
| `nmap.py` | XML | Regex | Port va service ma'lumotlari |
| `nuclei.py` | — | Regex | Zaiflik ro'yxati |
| `nikto.py` | JSON | Regex | Web xatoliklar |
| `sqlmap.py` | JSON | Regex | SQL injection natijalari |
| `gobuster.py` | NDJSON | Regex | Topilgan direktorilar |
| `amass.py` | NDJSON | Regex | Subdomain ro'yxati |
| `whatweb.py` | JSON | Regex | CMS/technologies |
| `network.py` | — | netstat/ss/lsof | Lokal port monitoring |

---

## 6. Mavjud vositalar (Tool'lar)

| Tool | Enum | CLI argument | Parser | Binary |
|------|------|-------------|--------|--------|
| nmap | `ToolType.NMAP` | `nmap` | `parsers/nmap.py` | `nmap` |
| nuclei | `ToolType.NUCLEI` | `nuclei` | `parsers/nuclei.py` | `nuclei` |
| nikto | `ToolType.NIKTO` | `nikto` | `parsers/nikto.py` | `nikto` |
| sqlmap | `ToolType.SQLMAP` | `sqlmap` | `parsers/sqlmap.py` | `sqlmap` |
| gobuster | `ToolType.GOBUSTER` | `gobuster` | `parsers/gobuster.py` | `gobuster` |
| amass | `ToolType.AMASS` | `amass` | `parsers/amass.py` | `amass` |
| whatweb | `ToolType.WHATWEB` | `whatweb` | `parsers/whatweb.py` | `whatweb` |
| network | `ToolType.NETWORK` | `network` | `parsers/network.py` | Built-in |

---

## 7. API endpointlar

### REST API (FastAPI)

| Endpoint | HTTP | Vazifasi | Kirish |
|----------|------|----------|--------|
| `/` | GET | Frontend SPA | Ochiq |
| `/api/host` | GET | Server manzili | Ochiq |
| `/api/scan` | POST | AI orqali skanerlash | Ochiq |
| `/api/quick-scan` | POST | Tezkor port skaner | Ochiq |
| `/api/status` | GET | Server holati | Ochiq |
| `/api/history` | GET | Scan tarixi | Ochiq |
| `/api/history/{id}` | GET | Session ma'lumotlari | Ochiq |
| `/api/history/{id}` | DELETE | Session o'chirish | Ochiq |
| `/api/stats` | GET | Statistika | Ochiq |
| `/api/report/{id}` | GET | Hisobot fayli | Ochiq |
| `/api/terminal` | POST | Terminal emulator | API Key |
| `/docs` | GET | FastAPI hujjatlari | Ochiq |

### `/api/scan` request formati:
```json
{
  "prompt": "example.com ni zaifliklarga tekshir",
  "target": "example.com",
  "agentic": false
}
```

### `/api/scan` response formati:
```json
{
  "id": "abc123def456",
  "target": "example.com",
  "intent": "...",
  "tools": ["nmap", "nuclei"],
  "results": [
    {
      "tool": "nmap",
      "target": "example.com",
      "success": true,
      "ports": [{"port": 80, "state": "open", "service": "HTTP"}],
      "vulnerabilities": [...]
    }
  ],
  "technologies": {"server": "nginx", "cms": null},
  "report_html": "reports/..."
}
```

---

## 8. Frontend (UI)

### 5 sahifa:

| Sahifa | Fayl | Vazifasi |
|--------|------|----------|
| **Scanner** | `Scanner.jsx` | Asosiy skaner — URL kiritish, AI prompt, real-time natijalar |
| **Tarix** | `History.jsx` | O'tgan scan'lar ro'yxati, qidirish, o'chirish |
| **Hisobotlar** | `Reports.jsx` | Statistika, eng ko'p ishlatilgan vositalar |
| **Sozlamalar** | `Settings.jsx` | Tool holati, tema, til |
| **Sidebar** | `Sidebar.jsx` | Navigatsiya menyusi |

### Xususiyatlari:
- Dark va light tema (localStorage saqlanadi)
- Agentic mode (AI chuqur tahlil)
- Tool status indicator (idle, running, done, error)
- Real-time findings counter
- Chat-style AI prompt interface
- Responsive design

---

## 9. Ma'lumotlar bazasi

**Fayl:** `BACKEND/nexura_history.db` (SQLite)

### Jadval: `sessions`
| Ustun | Turi | Izoh |
|-------|------|------|
| id | TEXT | UUID (12 belgi) |
| target | TEXT | Skanerlangan manzil |
| intent | TEXT | Foydalanuvchi maqsadi |
| scan_date | TEXT | Sana va vaqt |
| status | TEXT | running/completed/failed |
| tool_count | INTEGER | Ishlatilgan tool'lar soni |
| duration_seconds | INTEGER | Davomiyligi |
| technologies | TEXT | JSON texnologiyalar |

### Jadval: `vulnerabilities`
| Ustun | Turi | Izoh |
|-------|------|------|
| id | INTEGER | Auto-increment |
| session_id | TEXT | Session FK |
| name | TEXT | Zaiflik nomi |
| severity | TEXT | CRITICAL/HIGH/MEDIUM/LOW/INFO |
| cve | TEXT | CVE identifikatori |
| cvss_score | REAL | CVSS ball (0-10) |
| tool_source | TEXT | Qaysi tool topgan |

### Jadval: `ports`
| Ustun | Turi | Izoh |
|-------|------|------|
| id | INTEGER | Auto-increment |
| session_id | TEXT | Session FK |
| port | INTEGER | Port raqami |
| state | TEXT | open/closed/filtered |
| service | TEXT | Service nomi |
| version | TEXT | Versiya |

### Jadval: `ai_analysis`
| Ustun | Turi | Izoh |
|-------|------|------|
| id | INTEGER | Auto-increment |
| session_id | TEXT | Session FK |
| analysis_text | TEXT | AI tahlili |
| recommendations | TEXT | JSON tavsiyalar |

---

## 10. Hozirgi holat

### Ishlab chiqarish holati: ✅ Ishlashga tayyor

### Test natijalari: **59/59 — Barcha testlar o'tdi**

| Test fayli | Testlar soni | Status |
|------------|:---:|:------:|
| `test_api.py` | 14 | ✅ |
| `test_core.py` | 11 | ✅ |
| `test_cve_lookup.py` | 7 | ✅ |
| `test_history_db.py` | 4 | ✅ |
| `test_integration.py` | 5 | ✅ |
| `test_parsers.py` | 8 | ✅ |
| `test_scanners.py` | 5 | ✅ |
| `test_schemas.py` | 5 | ✅ |
| **Jami** | **59** | **✅ 100%** |

### Kuchli tomonlari (8/10):
- AI agentic loop — kam uchraydigan professional feature
- SSRF prevention, terminal sandbox — xavfsizlik
- Har bir tool uchun ikkilamchi parser (JSON + text)
- Uzbek tilida to'liq interfeys
- Fallback plan — AI ishlamasa ham ishlaydi
- In-memory CVE caching
- `.env` fayl supporti
- Web API testlari (14 ta)
- Kod takrorlanishi minimallashtirilgan

### Kamchiliklari:
- Rate limiting yo'q
- HTTPS natively yo'q (http orqali)
- Frontend testlari yo'q
- CI/CD pipeline yo'q

### Web platform xususiyatlari:
- `NEXURA_CORS_ORIGINS=*` orqali barcha manzillardan ulanish mumkin
- `/api/host` endpointi — server manzilini avtomatik aniqlaydi
- Global exception handler — barcha xatoliklar JSON formatda qaytariladi
- Mobile responsive UI (sidebar mobil'da yopiladi)
- ErrorBoundary — frontend xatoliklarida qayta yuklash tugmasi
- Loading spinner — skanerlash jarayonida aylanma indikator
- Server xatoliklari UI'da chiroyli ko'rsatiladi
- FastAPI docs (`/docs`) — API hujjatlari brauzerda ochiq

---

## 11. Loyiha tartiblash (2026-06-12)

### 4 ta asosiy papkaga ajratish

Dastlabki loyiha barcha fayllar loyiha ildizida edi. Quyidagi tartiblash amalga oshirildi:

```
OLD STRUCTURE:                           NEW STRUCTURE:
                                         
nexura_scanner/                          nexura_scanner/
├── nexura/               ──►             ├── BACKEND/nexura/
├── frontend/             ──►             ├── FRONTEND/
├── gguf_models/          ──►             ├── LOCAL_AI_MODELS/
├── nmap/                 ──►             ├── SCANNING_TOOLS/
├── tests/                ──►             ├── BACKEND/tests/
├── scripts/              ──►             ├── BACKEND/scripts/
├── reports/              ──►             ├── BACKEND/reports/
├── prompts/              ──►             ├── BACKEND/nexura/prompts/ (birlashtirildi)
├── templates/            ──►             ❌ (o'chirildi — eskirgan)
├── static/               ──►             ❌ (o'chirildi — bo'sh)
├── conftest.py           ──►             ├── BACKEND/tests/conftest.py
├── test_imports.py       ──►             ├── BACKEND/scripts/test_imports.py
├── .env.production       ──►             ├── BACKEND/.env.production
├── config.json           ──►             ├── BACKEND/config.json
├── pyproject.toml        ──►             ├── BACKEND/pyproject.toml
├── requirements.txt      ──►             ├── BACKEND/requirements.txt
├── start.bat             ──►             ├── BACKEND/start.bat
├── Dockerfile            ──►             ├── Dockerfile (root — build context uchun)
├── docker-compose.yml    ──►             ├── docker-compose.yml (root)
├── nginx.conf            ──►             ├── nginx.conf (root)
├── *.txt, *.md (docs)    ──►             ├── BACKEND/docs/
└── setup_*.sh            ──►             └── BACKEND/scripts/
```

### O'zgartirilgan kod fayllari:

| Fayl | O'zgarish |
|------|-----------|
| `BACKEND/nexura/config.py` | `BASE_DIR` → `BACKEND/` (2 parent), `PROJECT_ROOT` (3 parent), `MODELS_DIR` → `LOCAL_AI_MODELS/`, `load_dotenv` path yangilandi |
| `BACKEND/nexura/web/app.py` | `FRONTEND_DIST = config.PROJECT_ROOT / "FRONTEND" / "dist"` |
| `BACKEND/nexura/history_db.py` | `DEFAULT_DB_PATH = config.BASE_DIR / "nexura_history.db"` (avtomatik ishlaydi) |
| `BACKEND/nexura/ai_engine.py` | Xabar matnida `gguf_models/` → `LOCAL_AI_MODELS/` |
| `BACKEND/conftest.py` (→ tests/) | `sys.path.insert(0, ...parent.parent)` (2 level up) |
| `BACKEND/scripts/test_imports.py` | `sys.path.insert(0, ...parent.parent)` qo'shildi |
| `BACKEND/start.bat` | Frontend build `..\FRONTEND\`, python `..\venv\` |
| `BACKEND/pyproject.toml` | Ruff exclude `nmap` olib tashlandi |
| `BACKEND/scripts/download_model.py` | Default output `../LOCAL_AI_MODELS` |
| `BACKEND/scripts/start_production.sh` | `FRONTEND_DIR` qo'shildi |
| `BACKEND/scripts/setup_linux.sh` | `cd BACKEND`, `MODEL_DIR="LOCAL_AI_MODELS"` |
| `BACKEND/scripts/setup_docker.sh` | Yangi Dockerfile yo'liga moslashtirildi |
| `Dockerfile` | `COPY BACKEND/nexura/ ./BACKEND/nexura/`, `WORKDIR /app/BACKEND` |
| `docker-compose.yml` | Volume `models:/app/LOCAL_AI_MODELS`, env `./.env.production:/app/BACKEND/.env` |
| `nginx.conf` | Frontend path `/app/FRONTEND/dist/assets/` |
| `.dockerignore` | Eski `frontend/` → `FRONTEND/`, `nmap/` → `SCANNING_TOOLS/` |
| `.gitignore` | Eski patternlar yangilandi, yangi papkalar qo'shildi |
| `README.md` | Barcha path'lar yangilandi |

### O'chirilgan fayllar:

| Fayl | Sabab |
|------|-------|
| Root `start.bat` | `BACKEND/start.bat` bilan dublikat |
| `BACKEND/prompts/` | `BACKEND/nexura/prompts/system.txt` bilan dublikat |
| `BACKEND/templates/index.html` | Hech qanday kod ishlatmaydi (eskirgan) |
| `BACKEND/static/` | Bo'sh papka |
| `BACKEND/nexura/web/static/` | Bo'sh papka |
| `FRONTEND/src/assets/` | Bo'sh papka |
| `app.py.bak`, `web_app.py.bak` | Zaxira nusxalar |

### Ko'chirilgan fayllar:

| Eski joy | Yangi joy |
|----------|-----------|
| `bugs.md` | `BACKEND/docs/bugs.md` |
| `README_BUGFIXES.txt` | `BACKEND/docs/README_BUGFIXES.txt` |
| `setup_docker.sh` | `BACKEND/scripts/setup_docker.sh` |
| `setup_linux.sh` | `BACKEND/scripts/setup_linux.sh` |
| `conftest.py` | `BACKEND/tests/conftest.py` |
| `test_imports.py` | `BACKEND/scripts/test_imports.py` |
| Barcha analiz fayllari (`*.txt`, `*.md`) | `BACKEND/docs/` |

### Yakuniy struktura:

```
nexura_scanner/
├── FRONTEND/               # React UI ilovasi
│   ├── src/components/     # Scanner, History, Reports, Settings, Sidebar
│   ├── dist/               # Vite build natijasi
│   └── package.json
├── BACKEND/                # Python backend
│   ├── nexura/             # Asosiy kod (8 modul)
│   ├── tests/              # 59 test
│   ├── scripts/            # Yordamchi skriptlar
│   ├── reports/            # Skaner hisobotlari
│   ├── docs/               # Hujjatlar
│   ├── start.bat           # Ishga tushirish
│   └── pyproject.toml
├── LOCAL_AI_MODELS/        # GGUF AI modellar
├── SCANNING_TOOLS/         # Nmap vositalari
├── Dockerfile              # Multi-stage build
├── docker-compose.yml
├── nginx.conf
└── README.md
```

---

## 12. Ishga tushirish

### Talablar:
- Python 3.10+
- Node.js 18+ (frontend build uchun)
- Tashqi tool'lar: nmap, nuclei, nikto, sqlmap, gobuster, amass, whatweb

### 1. Python muhiti:
```bash
git clone <repo>
cd nexura_scanner
python -m venv venv
venv\Scripts\activate    # Windows
pip install -e .
```

### 2. AI modeli (ixtiyoriy):
4.7 GB GGUF faylni `LOCAL_AI_MODELS/` ga joylashtiring:
- `qwen2.5-7b-instruct-q4_k_m.gguf` (tavsiya)

AIsiz ishlatish: `nexura quick example.com`

### 3. Frontend build:
```bash
cd FRONTEND
npm install
npm run build
cd ..
```

### 4. Sozlamalar:
```bash
cp BACKEND/.env.example BACKEND/.env
# BACKEND/.env faylni o'zgartiring
```

### 5. Ishga tushirish:
```bash
# Web UI (BACKEND/ papkasida)
cd BACKEND
nexura web
# Yoki
python -m nexura web

# CLI
nexura scan "example.com ni zaifliklarga tekshir"
nexura quick example.com
nexura list-tools
```

---

## 13. Qo'llaniladigan buyruqlar

### CLI (nexura)

| Buyruq | Izoh |
|--------|------|
| `nexura web` | Web UI (http://localhost:8080) |
| `nexura scan "..."` | AI orqali to'liq skanerlash |
| `nexura scan "..." -t example.com` | Target bilan skanerlash |
| `nexura scan "..." -o hisobot.html` | Hisobot faylini belgilash |
| `nexura scan "..." -f html` | Faqat HTML hisobot |
| `nexura scan "..." --deep` | Chuqur skanerlash |
| `nexura scan "..." -y` | Tasdiqlashni so'ramaslik |
| `nexura quick example.com` | Tezkor port skaner (AIsiz) |
| `nexura quick example.com --ports 80,443` | Portlarni belgilash |
| `nexura list-models` | GGUF modellar ro'yxati |
| `nexura list-tools` | Mavjud vositalar ro'yxati |

### Web UI'da:
- URL kiritib "Scan boshlash" tugmasi
- Tabiiy tilda prompt yozish (AI buyruq)
- Agentic mode (AI chuqur tahlil)
- Tarix, hisobotlar, sozlamalar
- Terminal emulator (/api/terminal)
