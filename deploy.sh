#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# NEXURA Scanner — Serverga o'rnatish skripti
# =============================================================================
# ISHLATISH:
#   sudo bash deploy.sh
#
# Bu skript:
#   1. Docker va Docker Compose'ni o'rnatadi
#   2. Loyihani clone qiladi (yoki papkadan ishlatsangiz, skip)
#   3. .env faylini yaratadi
#   4. Nginx va Certbot (Let's Encrypt SSL) o'rnatadi
#   5. Docker container'ni ishga tushiradi
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }

if [ "$(id -u)" -ne 0 ]; then
    err "Bu skriptni sudo bilan ishga tushiring: sudo bash deploy.sh"
fi

DOMAIN=""
while [ -z "$DOMAIN" ]; do
    read -p "Domen nomini kiriting (masalan: scanner.uz): " DOMAIN
done

API_KEY=$(openssl rand -hex 32)
log "API_KEY generatsiya qilindi: $API_KEY"

# 1. Docker o'rnatish
if ! command -v docker &>/dev/null; then
    log "Docker o'rnatilmoqda..."
    curl -fsSL https://get.docker.com | bash
    systemctl enable --now docker
else
    log "Docker allaqachon o'rnatilgan"
fi

# 2. Docker Compose o'rnatish
if ! docker compose version &>/dev/null; then
    log "Docker Compose o'rnatilmoqda..."
    apt-get install -y docker-compose-plugin
fi

# 3. Nginx va Certbot o'rnatish
if ! command -v nginx &>/dev/null; then
    log "Nginx o'rnatilmoqda..."
    apt-get update -qq && apt-get install -y -qq nginx certbot python3-certbot-nginx
fi

# 4. Firewall
if command -v ufw &>/dev/null; then
    log "Firewall sozlanmoqda..."
    ufw allow 22/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw --force enable
fi

# 5. Loyiha papkasi
APP_DIR="/opt/nexura-scanner"
if [ ! -d "$APP_DIR" ]; then
    mkdir -p "$APP_DIR"
fi

if [ -f "docker-compose.yml" ]; then
    # Skript loyiha ichidan ishga tushirilgan
    cp docker-compose.yml Dockerfile .dockerignore "$APP_DIR/"
    cp -r BACKEND FRONTED "$APP_DIR/"
    log "Loyiha fayllari $APP_DIR/ ga ko'chirildi"
else
    cd "$APP_DIR"
fi

cd "$APP_DIR"

# 6. .env faylini yaratish
if [ ! -f ".env" ]; then
    cat > .env << EOF
NEXURA_API_KEY=$API_KEY
NEXURA_CORS_ORIGINS=https://$DOMAIN
EOF
    log ".env fayli yaratildi"
else
    warn ".env fayli allaqachon mavjud, o'zgartirilmadi"
fi

# 7. AI model papkasini tayyorlash
mkdir -p LOCAL_AI_MODELS
log "AI model faylini $APP_DIR/LOCAL_AI_MODELS/ ga joylashtiring"

# 8. Nginx sozlash
cat > /etc/nginx/sites-available/nexura << NGINX
limit_req_zone \$binary_remote_addr zone=api:10m rate=10r/s;

server {
    listen 80;
    server_name $DOMAIN;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5:!DH;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1h;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    client_max_body_size 100M;

    location /assets/ {
        alias $APP_DIR/FRONTEND/dist/assets/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    access_log /var/log/nginx/nexura-access.log;
    error_log  /var/log/nginx/nexura-error.log;
}
NGINX

ln -sf /etc/nginx/sites-available/nexura /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
log "Nginx sozlandi"

# 9. SSL sertifikat
log "Let's Encrypt SSL o'rnatilmoqda..."
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email "admin@$DOMAIN" || \
    warn "Certbot muvaffaqiyatsiz. Keyin qo'lda ishga tushiring: sudo certbot --nginx -d $DOMAIN"

systemctl reload nginx

# 10. Docker container
log "Docker image build qilinmoqda (birinchi marta ~15-20 daqiqa) ..."
docker compose build --pull

log "Container ishga tushirilmoqda..."
docker compose up -d

# 11. Tekshirish
sleep 5
if docker compose ps | grep -q "Up"; then
    log "NEXURA Scanner muvaffaqiyatli ishga tushdi!"
    echo ""
    echo "=============================================="
    echo "  DASHBOARD: https://$DOMAIN"
    echo "  API KEY:   $API_KEY"
    echo "=============================================="
    echo ""
    echo "AI model faylini quyidagiga joylashtiring:"
    echo "  $APP_DIR/LOCAL_AI_MODELS/"
    echo ""
    echo "Loglarni ko'rish:"
    echo "  sudo docker compose -f $APP_DIR/docker-compose.yml logs -f"
else
    err "Container ishga tushmadi. Loglarni tekshiring: docker compose logs"
fi