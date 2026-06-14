# NEXURA Scanner v2.0

AI-powered vulnerability scanner. Natural language orqali buyruq bering, AI kerakli tool'ni tanlab skanerlasin.

## Loyiha tuzilishi

```
nexura_scanner/
├── FRONTEND/               # React UI ilovasi
├── BACKEND/                # Python backend
│   ├── nexura/             # Asosiy kod
│   ├── tests/              # Testlar
│   ├── scripts/            # Yordamchi skriptlar
│   └── reports/            # Skaner hisobotlari
├── LOCAL_AI_MODELS/        # GGUF AI modellar
├── SCANNING_TOOLS/         # Nmap va boshqa vositalar
├── Dockerfile
├── docker-compose.yml
└── .gitignore
```

## Quick Start

### Linux (tavsiya)

```bash
# 1. Avtomatik o'rnatish
chmod +x BACKEND/scripts/setup_linux.sh
sudo ./BACKEND/scripts/setup_linux.sh

# 2. Skanerlash (BACKEND/ papkasida)
cd BACKEND
nexura scan "example.com ni zaifliklarga tekshir"
```

### Docker

```bash
# 1. Build (loyiha ildizida)
docker build -t nexura-scanner .

# 2. Web UI
docker run --rm -p 8080:8080 nexura-scanner web
```

### Windows

```batch
BACKEND\start.bat
```

## Model yuklab olish

AI modeli kerak (4.7 GB):

```bash
pip install huggingface-hub
python BACKEND/scripts/download_model.py
# Faylni LOCAL_AI_MODELS/ papkasiga joylashtiradi
```

AIsiz ishlatish: `nexura quick example.com` port skanerlash AIsiz ishlaydi.

## Buyruqlar

| Buyruq | Izoh |
|--------|------|
| `nexura scan "..."` | AI orqali skanerlash |
| `nexura quick example.com` | Tezkor port skanerlash (AIsiz) |
| `nexura web` | Web UI (http://localhost:8080) |
| `nexura list-models` | GGUF modellar ro'yxati |

## Tool'lar

Dastur ishlashi uchun quyidagi tool'lar kerak:
- **nmap** — port skanerlash
- **nuclei** — zaiflik skanerlash
- **nikto** — web server skanerlash
- **sqlmap** — SQL injection test
- **gobuster** — directory brute-force

`BACKEND/scripts/setup_linux.sh` ularni avtomatik o'rnatadi.
