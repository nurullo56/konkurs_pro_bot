#!/usr/bin/env bash
# ==============================================================================
# Hetzner Cloud Server Setup Script for Konkurs Bot Pro
# Muallif: Antigravity & Nurulloh
# Tavsif: Hetzner Cloud (Ubuntu 22.04 / 24.04 LTS) serverida loyihani 0 dan
#         to'liq sozlash, kerakli paketlar, Redis, PM2, Python venv, Nginx va
#         avtomatik backup tizimini o'rnatish.
# ==============================================================================

set -euo pipefail

# Ranglar va belgilar
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${CYAN}ℹ️  [INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅ [SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠️  [WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}❌ [ERROR]${NC} $1"
}

# 1. Root huquqini tekshirish
if [[ $EUID -ne 0 ]]; then
   log_error "Ushbu skriptni 'root' foydalanuvchi sifatida ishga tushirish kerak (sudo ./setup_hetzner.sh)"
   exit 1
fi

PROJECT_DIR="/var/www/konkurs_bot_pro"
REPO_URL="https://github.com/nurullo56/konkurs_pro_bot.git"

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}   🚀 HETZNER CLOUD: KONKURS BOT PRO AUTO SETUP     ${NC}"
echo -e "${BLUE}====================================================${NC}"

# 2. Tizim paketlarini yangilash
log_info "1/7 Tizim paketlari yangilanmoqda (apt update & upgrade)..."
export DEBIAN_FRONTEND=noninteractive
apt update -y && apt upgrade -y

# 3. Asosiy dasturiy vositalarni o'rnatish
log_info "2/7 Kerakli dasturlar o'rnatilmoqda (Python, Git, Redis, Nginx, UFW, Matplotlib fontlari)..."
apt install -y \
    curl \
    wget \
    git \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    libpq-dev \
    redis-server \
    nginx \
    certbot \
    python3-certbot-nginx \
    fonts-dejavu-core \
    fonts-liberation \
    htop \
    ufw \
    fail2ban \
    unzip \
    sqlite3

log_success "Asosiy paketlar muvaffaqiyatli o'rnatildi!"

# 4. Redis sozlash
log_info "3/7 Redis xizmati ishga tushirilmoqda..."
systemctl enable --now redis-server
if systemctl is-active --quiet redis-server; then
    log_success "Redis server faol va ishlamoqda!"
else
    log_warn "Redis ishga tushmadi, tekshirib ko'ring."
fi

# 5. Node.js va PM2 o'rnatish (Botlarni fonda ishonchli boshqarish uchun)
log_info "4/7 Node.js LTS va PM2 o'rnatilmoqda..."
if ! command -v pm2 &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt install -y nodejs
    npm install -g pm2
    # Server qayta yoqilganda PM2 avtomatik botlarni ko'tarishi uchun
    pm2 startup systemd -u root --hp /root || true
    log_success "Node.js $(node -v) va PM2 $(pm2 -v) muvaffaqiyatli o'rnatildi!"
else
    log_success "PM2 allaqachon o'rnatilgan: $(pm2 -v)"
fi

# 6. UFW Xavfsizlik devori (Firewall) sozlash
log_info "5/7 UFW Firewall sozlanmoqda (SSH, HTTP, HTTPS ruxsat beriladi)..."
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable
log_success "UFW xavfsizlik devori yoqildi!"

# 7. Loyihani yuklab olish yoki joriy papkadan tayyorlash
log_info "6/7 Loyiha papkasi tayyorlanmoqda ($PROJECT_DIR)..."
if [[ -d "$PROJECT_DIR" ]]; then
    log_info "$PROJECT_DIR mavjud, oxirgi o'zgarishlar olinmoqda..."
    cd "$PROJECT_DIR"
    git pull origin main || true
else
    # Agar joriy papkada loyiha bo'lsa (masalan skript loyiha ichidan chaqirilsa)
    CURRENT_DIR=$(pwd)
    if [[ -f "$CURRENT_DIR/bot.py" ]]; then
        PROJECT_DIR="$CURRENT_DIR"
        log_info "Loyiha joriy papkada topildi: $PROJECT_DIR"
    else
        log_info "Git repozitoriydan klonlanmoqda ($REPO_URL)..."
        mkdir -p /var/www
        cd /var/www
        git clone "$REPO_URL" konkurs_bot_pro
        cd "$PROJECT_DIR"
    fi
fi

# 8. Python Virtual Environment (venv) va bog'liqliklar
log_info "7/7 Python Virtual Environment (venv) yaratilmoqda va kutubxonalar o'rnatilmoqda..."
if [[ ! -d "$PROJECT_DIR/venv" ]]; then
    python3 -m venv "$PROJECT_DIR/venv"
fi

"$PROJECT_DIR/venv/bin/pip" install --upgrade pip setuptools wheel
"$PROJECT_DIR/venv/bin/pip" install -r "$PROJECT_DIR/requirements.txt"

# Kerakli papkalarni yaratish
mkdir -p "$PROJECT_DIR/instances"
mkdir -p "$PROJECT_DIR/backups"
mkdir -p "$PROJECT_DIR/logs"

# Har kungi 03:00 da avtomatik backup uchun Cron job qo'shish
CRON_JOB="0 3 * * * $PROJECT_DIR/venv/bin/python $PROJECT_DIR/scripts/backup_db.py >> $PROJECT_DIR/logs/backup.log 2>&1"
(crontab -l 2>/dev/null | grep -Fv "$PROJECT_DIR/scripts/backup_db.py" ; echo "$CRON_JOB") | crontab -
log_success "Avtomatik kundalik backup (soat 03:00) crontab-ga qo'shildi!"

# Skriptlarga bajarish huquqini berish
chmod +x "$PROJECT_DIR/scripts/"*.sh 2>/dev/null || true

echo -e "\n${GREEN}====================================================${NC}"
echo -e "${GREEN}   🎉 HETZNER SERVER O'RNATILISHI YAKUNLANDI!       ${NC}"
echo -e "${GREEN}====================================================${NC}"
echo -e "Loyiha joylashuvi: ${CYAN}$PROJECT_DIR${NC}"
echo -e "Python muhiti:     ${CYAN}$PROJECT_DIR/venv${NC}"
echo -e ""
echo -e "📌 Foydali buyruqlar:"
echo -e "  1. Yangi bot qo'shish:"
echo -e "     ${YELLOW}cd $PROJECT_DIR && ./venv/bin/python scripts/deploy.py add${NC}"
echo -e ""
echo -e "  2. Barcha botlarni ko'rish va boshqarish:"
echo -e "     ${YELLOW}pm2 list${NC}   yoki   ${YELLOW}./venv/bin/python scripts/deploy.py list${NC}"
echo -e ""
echo -e "  3. Bot loglarini jonli kuzatish:"
echo -e "     ${YELLOW}pm2 logs${NC}"
echo -e ""
echo -e "  4. Loyihani yangilash:"
echo -e "     ${YELLOW}./scripts/deploy_hetzner.sh update${NC}"
echo -e "${GREEN}====================================================${NC}\n"
