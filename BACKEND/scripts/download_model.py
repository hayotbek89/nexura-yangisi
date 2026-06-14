#!/usr/bin/env python3
"""GGUF model yuklab olish skripti.

Usage:
    python scripts/download_model.py
    python scripts/download_model.py --model Qwen/Qwen2.5-7B-Instruct-GGUF --file qwen2.5-7b-instruct-q4_k_m.gguf
"""
import argparse
import sys
from pathlib import Path


def download(model_id: str, filename: str, output_dir: str):
    model_path = Path(output_dir) / filename
    if model_path.exists():
        size_gb = model_path.stat().st_size / (1024**3)
        print(f"✅ Model allaqachon mavjud: {model_path} ({size_gb:.2f} GB)")
        return

    print(f"⬇️  Yuklab olinmoqda: {model_id} / {filename}")
    print(f"   Manzil: {output_dir}/")
    print()

    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("❌ huggingface-hub kutubxonasi yo'q. O'rnatish: pip install huggingface-hub")
        sys.exit(1)

    try:
        path = hf_hub_download(
            repo_id=model_id,
            filename=filename,
            local_dir=output_dir,
            local_dir_use_symlinks=False,
        )
        size_gb = Path(path).stat().st_size / (1024**3)
        print(f"✅ Yuklab olindi: {path} ({size_gb:.2f} GB)")
    except Exception as e:
        print(f"❌ Xatolik: {e}")
        print()
        print(f"Alternativ: https://huggingface.co/{model_id}/resolve/main/{filename}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="GGUF model yuklab olish")
    parser.add_argument("--model", default="QuantFactory/Qwen2.5-7B-Instruct-GGUF")
    parser.add_argument("--file", default="Qwen2.5-7B-Instruct.Q4_K_M.gguf")
    parser.add_argument("--output", default="../LOCAL_AI_MODELS")
    args = parser.parse_args()

    download(args.model, args.file, args.output)


if __name__ == "__main__":
    main()
