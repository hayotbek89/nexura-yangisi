import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = BACKEND_DIR
load_dotenv(BACKEND_DIR / ".env")
MODELS_DIR = PROJECT_ROOT / "LOCAL_AI_MODELS"
REPORTS_DIR = BACKEND_DIR / "reports"

_dirs_initialized = False

def ensure_dirs():
    global _dirs_initialized
    if not _dirs_initialized:
        os.makedirs(MODELS_DIR, exist_ok=True)
        os.makedirs(REPORTS_DIR, exist_ok=True)
        _dirs_initialized = True

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")

WEB_HOST = os.getenv("NEXURA_WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("NEXURA_WEB_PORT", "8080"))

TIMEOUT = int(os.getenv("NEXURA_TIMEOUT", "300"))

SSL_VERIFY = os.getenv("NEXURA_SSL_VERIFY", "1") == "1"
SOCKET_TIMEOUT = float(os.getenv("NEXURA_SOCKET_TIMEOUT", "2.0"))

IS_PRODUCTION = os.getenv("NEXURA_PRODUCTION", "").lower() in ("1", "true", "yes")

import shutil

TOOL_PATHS = {
    "nmap":      "/usr/bin/nmap",
    "nuclei":    "/usr/local/bin/nuclei",
    "nikto":     "/usr/bin/nikto",
    "sqlmap":    "/usr/bin/sqlmap",
    "gobuster":  "/usr/bin/gobuster",
    "amass":     "/snap/bin/amass",
    "whatweb":   "/usr/bin/whatweb",
}

def is_tool_available(tool_name: str) -> bool:
    which = shutil.which(tool_name)
    if which is not None:
        return True
    if tool_name in TOOL_PATHS:
        return os.path.isfile(TOOL_PATHS[tool_name])
    return False

def get_env():
    env = os.environ.copy()
    if os.name != "nt":
        env["PATH"] = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin"
    return env
