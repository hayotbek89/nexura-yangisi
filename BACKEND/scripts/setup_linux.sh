#!/bin/bash
set -e

echo "==================================="
echo "  NEXURA Scanner — Linux Setup"
echo "==================================="

# 1. System packages
echo "[1/5] Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    nmap \
    nikto \
    sqlmap \
    gobuster \
    python3-pip \
    git \
    wget \
    curl \
    jq

# 2. Nuclei
echo "[2/5] Installing Nuclei..."
if ! command -v nuclei &>/dev/null; then
    wget -q https://github.com/projectdiscovery/nuclei/releases/latest/download/nuclei_linux_amd64.zip
    unzip -q nuclei_linux_amd64.zip -d /tmp/nuclei
    sudo mv /tmp/nuclei/nuclei /usr/local/bin/nuclei
    rm -rf nuclei_linux_amd64.zip /tmp/nuclei
    nuclei -update-templates 2>/dev/null || true
fi

# 3. Python dependencies
echo "[3/5] Installing Python packages..."
cd "$(dirname "$0")/BACKEND"
pip3 install -q -e .

# 4. GGUF model download
echo "[4/5] Downloading AI model..."
MODEL_DIR="LOCAL_AI_MODELS"
MODEL_PATH="$MODEL_DIR/qwen2.5-7b-instruct-q4_k_m.gguf"
mkdir -p "$MODEL_DIR"

if [ ! -f "$MODEL_PATH" ]; then
    echo "Downloading Qwen 2.5 7B Q4_K_M (~4.7 GB)..."
    pip3 install -q huggingface-hub
    python3 -c "
from huggingface_hub import hf_hub_download
hf_hub_download(
    repo_id='Qwen/Qwen2.5-7B-Instruct-GGUF',
    filename='qwen2.5-7b-instruct-q4_k_m.gguf',
    local_dir='$MODEL_DIR',
    local_dir_use_symlinks=False,
)
"
fi

# 5. Verify
echo "[5/5] Verifying installation..."
echo ""
echo "=== Tools ==="
for tool in nmap nuclei nikto sqlmap gobuster; do
    ver=$($tool --version 2>/dev/null | head -1 || echo "NOT FOUND")
    echo "  $tool: $ver"
done

echo ""
echo "=== AI Model ==="
if [ -f "$MODEL_PATH" ]; then
    size=$(du -h "$MODEL_PATH" | cut -f1)
    echo "  Model: $MODEL_PATH ($size)"
else
    echo "  Model: NOT FOUND (download manually)"
fi

echo ""
echo "=== Python ==="
python3 --version

echo ""
echo "✅ Setup complete!"
echo "Run: nexura scan 'example.com ni zaifliklarga tekshir'"
