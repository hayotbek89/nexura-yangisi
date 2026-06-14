#!/bin/bash
set -e

BACKEND_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_DIR="$(cd "$BACKEND_DIR/.." && pwd)"
ENV_FILE="$BACKEND_DIR/.env"
ENV_PROD="$BACKEND_DIR/.env.production"
LOG_FILE="$BACKEND_DIR/nexura.log"
FRONTEND_DIR="$PROJECT_DIR/FRONTEND"

echo "============================================"
echo "  NEXURA Scanner — Production Start"
echo "============================================"

# 1. Environment
if [ ! -f "$ENV_FILE" ] && [ -f "$ENV_PROD" ]; then
    cp "$ENV_PROD" "$ENV_FILE"
    echo "[!] .env created from .env.production — edit it!"
fi

# 2. Frontend build check
if [ ! -d "$FRONTEND_DIR/dist" ]; then
    echo "[1/3] Building frontend..."
    cd "$FRONTEND_DIR"
    npm ci && npm run build
    cd "$BACKEND_DIR"
fi

# 3. Reports directory
mkdir -p "$BACKEND_DIR/reports"

# 4. Start server
echo "[2/3] Starting server..."
cd "$BACKEND_DIR"
exec uvicorn nexura.web.app:app \
    --host 0.0.0.0 \
    --port 8080 \
    --workers 4 \
    --log-level info \
    --log-config - 2>&1 | tee -a "$LOG_FILE"
