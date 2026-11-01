from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Loyiha asosiy papkasi
BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCES_DIR = BASE_DIR / "instances"
LOCAL_NGINX_CONF = BASE_DIR / "nginx" / "default.conf"
SYSTEM_NGINX_CONF = Path("/etc/nginx/sites-available/konkurs_bot.conf")
SYSTEM_NGINX_ENABLED = Path("/etc/nginx/sites-enabled/konkurs_bot.conf")


def parse_instance_env(env_path: Path) -> dict[str, str]:
    """Instance .env faylini o'qiydi."""
    result: dict[str, str] = {}
    if not env_path.exists():
        return result
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                result[key.strip()] = val.strip()
    return result


def get_all_webhook_bots() -> list[dict[str, str]]:
    """instances/ papkasidagi barcha webhook orqali ishlaydigan botlarni qaytaradi."""
    bots = []
    if not INSTANCES_DIR.exists():
        return bots

    for inst_dir in sorted(INSTANCES_DIR.iterdir()):
        if not inst_dir.is_dir() or inst_dir.name.startswith("__"):
            continue
        env_file = inst_dir / ".env"
        if not env_file.exists():
            continue

        env_data = parse_instance_env(env_file)
        # Webhook yoqilgan bo'lsa yoki default holatda
        use_webhook = env_data.get("USE_WEBHOOK", "true").lower() == "true"
        if use_webhook:
            path = env_data.get("WEBHOOK_PATH", f"/webhook/{inst_dir.name}")
            port = env_data.get("WEBAPP_PORT", "8001")
            bots.append({
                "name": inst_dir.name,
                "path": path,
                "port": port,
            })
    return bots


def generate_nginx_conf(domain: str, bots: list[dict[str, str]] | None = None) -> str:
    """Nginx to'liq konfiguratsiyasini yaratadi."""
    if bots is None:
        bots = get_all_webhook_bots()

    conf = f"""# ==============================================================================
# Avtomatik generatsiya qilingan Nginx konfiguratsiyasi
# Domen: {domain}
# Jami Webhook botlar: {len(bots)} ta
# ==============================================================================

server {{
    listen 80;
    listen [::]:80;
    server_name {domain};

    # Let's Encrypt / Certbot tekshiruvlari uchun
    location /.well-known/acme-challenge/ {{
        root /var/www/html;
    }}

    location / {{
        return 301 https://$host$request_uri;
    }}
}}

server {{
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name {domain};

    # SSL sertifikat yo'llari (Certbot orqali o'rnatiladi)
    ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Asosiy sahifa
    location / {{
        return 200 "Konkurs Bot Pro Webhook Server is Running!\\n";
        add_header Content-Type text/plain;
    }}

"""
    for bot in bots:
        name = bot["name"]
        path = bot["path"]
        port = bot["port"]
        conf += f"""    # Bot: {name} (Ichki port: {port})
    location ^~ {path} {{
        proxy_pass http://127.0.0.1:{port};
        proxy_set_header Host $http_host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_read_timeout 60s;
        proxy_connect_timeout 60s;
    }}

"""

    conf += "}\n"
    return conf


def sync_nginx(domain: str = "smart-tools.uk") -> bool:
    """
    Nginx konfiguratsiyasini yangilaydi va Linux serverda Nginx-ni qayta yuklaydi.
    """
    bots = get_all_webhook_bots()
    conf_content = generate_nginx_conf(domain, bots)

    # 1. Loyiha ichidagi nginx/default.conf ga yozish
    LOCAL_NGINX_CONF.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCAL_NGINX_CONF, "w", encoding="utf-8") as f:
        f.write(conf_content)
    print(f"📄 Nginx konfiguratsiyasi yangilandi ({len(bots)} ta bot): {LOCAL_NGINX_CONF}")

    # 2. Linux serverda /etc/nginx mavjud bo'lsa, tizimga o'rnatish va reload qilish
    if sys.platform != "win32" and Path("/etc/nginx").exists():
        try:
            # sites-available ga yozish
            SYSTEM_NGINX_CONF.write_text(conf_content, encoding="utf-8")

            # sites-enabled ga symlink qilish
            if not SYSTEM_NGINX_ENABLED.exists():
                try:
                    SYSTEM_NGINX_ENABLED.symlink_to(SYSTEM_NGINX_CONF)
                except Exception:
                    shutil.copy2(SYSTEM_NGINX_CONF, SYSTEM_NGINX_ENABLED)

            # Nginx sintaksisini tekshirish
            check_res = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
            if check_res.returncode == 0:
                # Nginx reload
                subprocess.run(["systemctl", "reload", "nginx"], check=True)
                print("🔄 Nginx muvaffaqiyatli qayta yuklandi (reload)!")
                return True
            else:
                print(f"⚠️ Nginx konfiguratsiyasida xatolik: {check_res.stderr}")
                return False
        except Exception as e:
            print(f"⚠️ Nginx-ni qayta yuklashda xatolik: {e}")
            return False

    return True


if __name__ == "__main__":
    cli_domain = sys.argv[1] if len(sys.argv) > 1 else "smart-tools.uk"
    sync_nginx(cli_domain)
