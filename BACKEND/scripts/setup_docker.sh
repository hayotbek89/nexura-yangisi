#!/bin/bash
# NEXURA Scanner — Docker image build
set -e

docker build -t nexura-scanner -f Dockerfile .

echo "✅ Docker image yaratildi: nexura-scanner"
echo ""
echo "Ishga tushirish:"
echo "  docker run --rm -p 8080:8080 nexura-scanner web"
echo "  docker run --rm nexura-scanner scan 'example.com ni zaifliklarga tekshir'"
