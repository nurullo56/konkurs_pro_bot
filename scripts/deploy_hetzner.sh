#!/usr/bin/env bash
# ==============================================================================
# Hetzner Cloud Deploy & Management Script for Konkurs Bot Pro
# Foydalanish:
#   ./deploy_hetzner.sh update      - Git dan yangilanishlarni oladi va botlarni qayta ishga tushiradi
#   ./deploy_hetzner.sh status      - Botlar holatini ko'rsatadi (PM2)
#   ./deploy_hetzner.sh restart     - Barcha botlarni qayta ishga tushiradi
#   ./deploy_hetzner.sh stop        - Barcha botlarni to'xtatadi
#   ./deploy_hetzner.sh logs [nomi] - Bot loglarini real vaqtda ko'rish
#   ./deploy_hetzner.sh backup      - Zaxira nusxa (backup) yaratadi
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$BASE_DIR/venv/bin/python"

# Ranglar
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

if [[ ! -f "$VENV_PYTHON" ]]; then
    echo -e "${RED}❌ Virtual environment topilmadi: $VENV_PYTHON${NC}"
    echo -e "Avval './scripts/setup_hetzner.sh' skriptini ishga tushiring."
    exit 1
fi

ACTION="${1:-status}"

case "$ACTION" in
    update)
        echo -e "${CYAN}🔄 Git dan oxirgi o'zgarishlar olinmoqda...${NC}"
        cd "$BASE_DIR"
        git pull origin main

        echo -e "${CYAN}📦 Kutubxonalar yangilanmoqda...${NC}"
        "$VENV_PYTHON" -m pip install -r requirements.txt

        echo -e "${CYAN}🚀 Botlar qayta ishga tushirilmoqda...${NC}"
        "$VENV_PYTHON" "$SCRIPT_DIR/deploy.py" restart-all

        if command -v pm2 &> /dev/null; then
            pm2 save || true
        fi
        echo -e "${GREEN}✅ Loyiha muvaffaqiyatli yangilandi va botlar qayta ishga tushirildi!${NC}"
        ;;

    restart)
        echo -e "${CYAN}🔄 Barcha botlar qayta ishga tushirilmoqda...${NC}"
        "$VENV_PYTHON" "$SCRIPT_DIR/deploy.py" restart-all
        if command -v pm2 &> /dev/null; then
            pm2 save || true
        fi
        ;;

    stop)
        echo -e "${YELLOW}🛑 Barcha botlar to'xtatilmoqda...${NC}"
        "$VENV_PYTHON" "$SCRIPT_DIR/deploy.py" stop-all
        ;;

    start)
        echo -e "${GREEN}🚀 Barcha botlar ishga tushirilmoqda...${NC}"
        "$VENV_PYTHON" "$SCRIPT_DIR/deploy.py" start-all
        if command -v pm2 &> /dev/null; then
            pm2 save || true
        fi
        ;;

    status)
        echo -e "${CYAN}📊 Botlar holati:${NC}"
        "$VENV_PYTHON" "$SCRIPT_DIR/deploy.py" list
        ;;

    logs)
        BOT_NAME="${2:-}"
        if command -v pm2 &> /dev/null; then
            if [[ -n "$BOT_NAME" ]]; then
                pm2 logs "bot_$BOT_NAME"
            else
                pm2 logs
            fi
        else
            if [[ -n "$BOT_NAME" && -f "$BASE_DIR/instances/$BOT_NAME/bot.log" ]]; then
                tail -f "$BASE_DIR/instances/$BOT_NAME/bot.log"
            else
                echo -e "${YELLOW}Log faylini ko'rish uchun bot nomini ko'rsating: ./deploy_hetzner.sh logs <bot_nomi>${NC}"
            fi
        fi
        ;;

    backup)
        echo -e "${CYAN}💾 Ma'lumotlar bazasi zaxira nusxasi (backup) olinmoqda...${NC}"
        "$VENV_PYTHON" "$SCRIPT_DIR/backup_db.py"
        echo -e "${GREEN}✅ Backup jarayoni yakunlandi! Fayllar: $BASE_DIR/backups/${NC}"
        ;;

    *)
        echo -e "${YELLOW}Foydalanish: $0 {update|status|start|stop|restart|logs|backup}${NC}"
        exit 1
        ;;
esac
