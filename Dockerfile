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

RUN pip install --no-cache-dir \
    llama-cpp-python

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

RUN wget -q https://github.com/projectdiscovery/nuclei/releases/latest/download/nuclei_linux_amd64.zip \
    && unzip -q nuclei_linux_amd64.zip -d /tmp/nuclei \
    && mv /tmp/nuclei/nuclei /usr/local/bin/nuclei \
    && rm -rf nuclei_linux_amd64.zip /tmp/nuclei

RUN wget -q https://github.com/OJ/gobuster/releases/latest/download/gobuster_linux_amd64.tar.gz \
    && tar -xzf gobuster_linux_amd64.tar.gz -C /tmp/gobuster \
    && mv /tmp/gobuster/gobuster /usr/local/bin/gobuster \
    && rm -rf gobuster_linux_amd64.tar.gz /tmp/gobuster

RUN git clone --depth 1 https://github.com/sullo/nikto /opt/nikto \
    && ln -s /opt/nikto/program/nikto.pl /usr/local/bin/nikto

RUN git clone --depth 1 https://github.com/sqlmapproject/sqlmap /opt/sqlmap \
    && ln -s /opt/sqlmap/sqlmap.py /usr/local/bin/sqlmap

RUN gem install whatweb

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
