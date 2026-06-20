# ---- Frontend build ----
FROM node:20-alpine AS frontend
WORKDIR /app
COPY FRONTEND/package*.json ./
RUN npm ci
COPY FRONTEND/ .
RUN npm run build

# ---- Python dependencies (includes AI engine) ----
FROM python:3.11-slim AS python-deps
WORKDIR /app

RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

COPY BACKEND/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir google-generativeai

# ---- Runtime ----
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
    nmap \
    curl \
    wget \
    unzip \
    git \
    ruby \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fL https://github.com/projectdiscovery/nuclei/releases/download/v3.9.0/nuclei_3.9.0_linux_amd64.zip -o /tmp/nuclei.zip \
    && unzip -q /tmp/nuclei.zip -d /tmp/nuclei \
    && mv /tmp/nuclei/nuclei /usr/local/bin/nuclei \
    && rm -rf /tmp/nuclei.zip /tmp/nuclei

RUN curl -fL https://github.com/OJ/gobuster/releases/download/v3.8.2/gobuster_Linux_x86_64.tar.gz -o /tmp/gobuster.tar.gz \
    && mkdir -p /tmp/gobuster \
    && tar -xzf /tmp/gobuster.tar.gz -C /tmp/gobuster \
    && mv /tmp/gobuster/gobuster /usr/local/bin/gobuster \
    && rm -rf /tmp/gobuster.tar.gz /tmp/gobuster

RUN git clone --depth 1 https://github.com/sullo/nikto /opt/nikto \
    && ln -s /opt/nikto/program/nikto.pl /usr/local/bin/nikto

RUN git clone --depth 1 https://github.com/sqlmapproject/sqlmap /opt/sqlmap \
    && ln -s /opt/sqlmap/sqlmap.py /usr/local/bin/sqlmap

RUN git clone --depth 1 https://github.com/urbanadventurer/WhatWeb /opt/whatweb \
    && ln -s /opt/whatweb/whatweb /usr/local/bin/whatweb

COPY --from=python-deps /usr/local /usr/local

COPY --from=frontend /app/dist ./FRONTEND/dist

COPY BACKEND/nexura/ ./BACKEND/nexura/
COPY BACKEND/scripts/ ./BACKEND/scripts/

RUN mkdir -p /app/reports /app/LOCAL_AI_MODELS /app/BACKEND/reports

RUN useradd -m -u 1000 nexura && chown -R nexura:nexura /app
USER nexura

ENV NEXURA_WEB_HOST=0.0.0.0
ENV NEXURA_WEB_PORT=8080
ENV PYTHONPATH=/app/BACKEND

EXPOSE 8080

VOLUME ["/app/BACKEND/reports", "/app/LOCAL_AI_MODELS"]

WORKDIR /app/BACKEND
CMD ["uvicorn", "nexura.web.app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]
