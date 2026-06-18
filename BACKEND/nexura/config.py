import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = BACKEND_DIR  # backward compat
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

LLAMA_MODEL_PATH = os.getenv("NEXURA_MODEL", str(MODELS_DIR / "qwen2.5-7b-instruct-q4_k_m.gguf"))
LLAMA_N_CTX = int(os.getenv("NEXURA_CTX_SIZE", "8192"))
LLAMA_N_THREADS = int(os.getenv("NEXURA_THREADS", "4"))
LLAMA_N_GPU_LAYERS = int(os.getenv("NEXURA_GPU_LAYERS", "0"))
LLAMA_TEMP = float(os.getenv("NEXURA_TEMP", "0.7"))
LLAMA_MAX_TOKENS = int(os.getenv("NEXURA_MAX_TOKENS", "4096"))

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
