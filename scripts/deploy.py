from __future__ import annotations

import io
import os
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Windows PowerShell cp1251 muammosini hal qilish — emoji to'g'ri chiqadi
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
_here = Path(__file__).resolve().parent
if _here.name == "scripts":
    BASE_DIR = _here.parent
else:
    BASE_DIR = _here

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

INSTANCES_DIR = BASE_DIR / "instances"
BOT_SCRIPT = BASE_DIR / "bot.py"
DEFAULT_DOMAIN = os.getenv("BASE_DOMAIN", "smart-tools.uk")


def ensure_instances_dir() -> None:
    """instances/ papkasini yaratadi (agar mavjud bo'lmasa)."""
    INSTANCES_DIR.mkdir(exist_ok=True)


def is_pm2_available() -> bool:
    """pm2 buyrug'i mavjudligini tekshiradi."""
    return shutil.which("pm2") is not None


def get_instance_dir(name: str) -> Path:
    """Bot instance papkasini qaytaradi."""
    return INSTANCES_DIR / name


def parse_env_file(env_path: Path) -> dict[str, str]:
    """
    .env faylini parse qiladi va key=value lug'atini qaytaradi.
    Bu ENV_FILE mexanizmiga tayanmay, to'g'ridan-to'g'ri env ni subprocess ga uzatish uchun.
    """
    result: dict[str, str] = {}
    if not env_path.exists():
        return result
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                result[key.strip()] = value.strip()
    return result


def get_next_available_port(start_port: int = 8001) -> int:
    """
    Mavjud botlar orasidan foydalanilmagan keyingi bo'sh portni aniqlaydi.
    """
    ensure_instances_dir()
    used_ports: set[int] = set()

    for d in INSTANCES_DIR.iterdir():
        if d.is_dir() and not d.name.startswith("__"):
            env_file = d / ".env"
            if env_file.exists():
                env_data = parse_env_file(env_file)
                port_str = env_data.get("WEBAPP_PORT", "")
                if port_str.isdigit():
                    used_ports.add(int(port_str))

    port = start_port
    while port in used_ports:
        port += 1
    return port


def sync_nginx_safe(domain: str) -> None:
    """Nginx konfiguratsiyasini yangilaydi (agar generate_nginx moduli mavjud bo'lsa)."""
    try:
        from nginx.generate_nginx import sync_nginx
        sync_nginx(domain)
    except Exception as e:
        print(f"⚠️ Nginx konfiguratsiyasini yangilashda ogohlantirish: {e}")


def add_instance() -> None:
    """
    Yangi bot instance qo'shadi:
    - Bo'sh ichki portni avtomatik ajratadi (masalan: 8001, 8002...)
    - Webhook URL va xavfsiz SECRET token yaratadi
    - Nginx konfiguratsiyasini avtomatik yangilaydi
    - Botni PM2 yoki fonda ishga tushiradi
    """
    ensure_instances_dir()
    print("\n➕ --- YANGI MIJOZ BOTINI QO'SHISH (WEBHOOK REJIMI) ---\n")
    name = input("Mijoz nomi/ID (masalan: client_1, store_uz): ").strip()
    if not name:
        print("❌ Mijoz nomi kiritilmadi!")
        return

    # Nomda noto'g'ri belgilar bo'lmasligi uchun
    clean_name = "".join(c for c in name if c.isalnum() or c in ("_", "-"))
    if clean_name != name:
        print(f"⚠️ Nom to'g'rilandi: '{name}' -> '{clean_name}'")
        name = clean_name

    inst_dir = get_instance_dir(name)
    if inst_dir.exists():
        print(f"❌ '{name}' nomli mijoz bot mavjud!")
        return

    domain_prompt = input(f"Webhook domeni [{DEFAULT_DOMAIN}]: ").strip()
    domain = domain_prompt or DEFAULT_DOMAIN

    bot_token = input("Bot Token (Telegram BotFather'dan): ").strip()
    if not bot_token:
        print("❌ Bot Token kiritilmadi!")
        return

    admin_ids = input("Admin ID lari (vergul bilan) [7867633335]: ").strip() or "7867633335"
    contest_name = input("Konkurs nomi [Konkurs]: ").strip() or "Konkurs"
    prize_text = input("Sovrin matni [2 000 000 so'm]: ").strip() or "2 000 000 so'm"
    top_n = input("Top g'oliblar soni TOP_N [10]: ").strip() or "10"
    start_points = input("Boshlang'ich ball [5]: ").strip() or "5"
    referral_points = input("Referral ball [1]: ").strip() or "1"

    # Bo'sh port va xavfsizlik tokeni generatsiyasi
    port = get_next_available_port(start_port=8001)
    webhook_secret = secrets.token_hex(16)
    webhook_path = f"/webhook/{name}"
    webhook_url = f"https://{domain}"

    inst_dir.mkdir(parents=True, exist_ok=True)
    env_path = inst_dir / ".env"
    db_path = inst_dir / "contest.db"

    env_content = (
        f"BOT_TOKEN={bot_token}\n"
        f"ADMIN_IDS={admin_ids}\n"
        f"CONTEST_NAME={contest_name}\n"
        f"PRIZE_TEXT={prize_text}\n"
        f"TOP_N={top_n}\n"
        f"START_POINTS={start_points}\n"
        f"REFERRAL_POINTS={referral_points}\n"
        f"DB_TYPE=sqlite\n"
        f"DB_PATH={db_path.as_posix()}\n"
        f"RATE_LIMIT=1.5\n"
        f"USE_WEBHOOK=true\n"
        f"WEBHOOK_URL={webhook_url}\n"
        f"WEBHOOK_PATH={webhook_path}\n"
        f"WEBAPP_HOST=127.0.0.1\n"
        f"WEBAPP_PORT={port}\n"
        f"WEBHOOK_SECRET={webhook_secret}\n"
        f"REDIS_URL=redis://127.0.0.1:6379/0\n"
    )

    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)

    print(f"\n✅ '{name}' uchun sozlamalar saqlandi: {env_path}")
    print(f"🔌 Ajratilgan port: {port}")
    print(f"🌐 Webhook manzili: {webhook_url}{webhook_path}")

    # Nginx-ni avtomatik yangilash
    sync_nginx_safe(domain)

    # Botni ishga tushirish
    start_instance(name)


def start_instance(name: str) -> None:
    """Bot instance'ni PM2 yoki subprocess orqali ishga tushiradi."""
    inst_dir = get_instance_dir(name)
    env_path = inst_dir / ".env"

    if not env_path.exists():
        print(f"❌ '{name}' bot sozlamalari topilmadi: {env_path}")
        return

    if not BOT_SCRIPT.exists():
        print(f"❌ bot.py topilmadi: {BOT_SCRIPT}")
        return

    if is_pm2_available():
        env = os.environ.copy()
        env["ENV_FILE"] = str(env_path)
        cmd = [
            "pm2", "start", str(BOT_SCRIPT),
            "--name", f"bot_{name}",
            "--interpreter", sys.executable,
            "--update-env",
        ]
        res = subprocess.run(cmd, cwd=str(BASE_DIR), env=env)
        if res.returncode == 0:
            print(f"🚀 Bot '{name}' PM2 orqali ishga tushirildi!")
        else:
            print(f"❌ PM2 orqali ishga tushirishda xatolik (return code: {res.returncode})")
        return

    # ---------- PM2 yo'q: subprocess bilan ----------
    pid_file = inst_dir / "bot.pid"
    if pid_file.exists():
        try:
            old_pid = int(pid_file.read_text().strip())
            if sys.platform == "win32":
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {old_pid}", "/NH"],
                    capture_output=True, text=True
                )
                if str(old_pid) in result.stdout:
                    print(f"⚠️ '{name}' allaqachon ishlayapti (PID: {old_pid}). Avval stop qiling.")
                    return
            else:
                try:
                    os.kill(old_pid, 0)
                    print(f"⚠️ '{name}' allaqachon ishlayapti (PID: {old_pid}). Avval stop qiling.")
                    return
                except OSError:
                    pass
        except Exception:
            pass

    log_file = inst_dir / "bot.log"

    env = os.environ.copy()
    env_vars = parse_env_file(env_path)
    env.update(env_vars)
    env["ENV_FILE"] = str(env_path)
    env["LOG_FILE"] = str(log_file)
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    if sys.platform == "win32":
        pythonw = Path(sys.executable).parent / "pythonw.exe"
        interpreter = str(pythonw) if pythonw.exists() else sys.executable
        creation_flags = 0x08000000  # CREATE_NO_WINDOW
    else:
        interpreter = sys.executable
        creation_flags = 0

    with open(log_file, "a", encoding="utf-8") as log_f:
        proc = subprocess.Popen(
            [interpreter, "-u", str(BOT_SCRIPT)],
            cwd=str(BASE_DIR),
            env=env,
            stdout=log_f,
            stderr=log_f,
            creationflags=creation_flags,
        )

    pid_file.write_text(str(proc.pid))
    print(f"🚀 Bot '{name}' fonda ishga tushirildi (PID: {proc.pid})! Log: {log_file}")


def stop_instance(name: str) -> None:
    """Bot instance'ni to'xtatadi."""
    inst_dir = get_instance_dir(name)
    if is_pm2_available():
        subprocess.run(["pm2", "stop", f"bot_{name}"])
        print(f"🛑 Bot '{name}' to'xtatildi.")
        return

    pid_file = inst_dir / "bot.pid"
    if not pid_file.exists():
        print(f"⚠️ '{name}' bot PID fayli topilmadi (allaqachon to'xtatilgandir).")
        return

    try:
        pid = int(pid_file.read_text().strip())
        if sys.platform == "win32":
            result = subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                print(f"⚠️ PID {pid} topilmadi (allaqachon to'xtatilgan bo'lishi mumkin).")
        else:
            os.kill(pid, 9)
        print(f"🛑 Bot '{name}' to'xtatildi (PID: {pid}).")
    except Exception as e:
        print(f"⚠️ Botni to'xtatishda xato: {e}")
    finally:
        if pid_file.exists():
            pid_file.unlink()


def restart_instance(name: str) -> None:
    """Bot instance'ni qayta ishga tushiradi."""
    stop_instance(name)
    time.sleep(1)
    start_instance(name)


def get_all_instance_names() -> list[str]:
    """Barcha bot instance'larining nomlarini qaytaradi."""
    ensure_instances_dir()
    return [
        d.name for d in sorted(INSTANCES_DIR.iterdir())
        if d.is_dir() and not d.name.startswith("__")
    ]


def restart_all_instances() -> None:
    """Barcha bot instance'larni qayta ishga tushiradi."""
    names = get_all_instance_names()
    if not names:
        print("📂 Hali hech qanday mijoz boti mavjud emas.")
        return

    print(f"🔄 Jami {len(names)} ta bot qayta ishga tushirilmoqda...\n")
    for name in names:
        print(f"--- '{name}' qayta ishga tushirilmoqda ---")
        restart_instance(name)
        print()
    print("✅ Barcha botlar muvaffaqiyatli qayta ishga tushirildi!")


def stop_all_instances() -> None:
    """Barcha bot instance'larni to'xtatadi."""
    names = get_all_instance_names()
    if not names:
        print("📂 Hali hech qanday mijoz boti mavjud emas.")
        return

    print(f"🛑 Jami {len(names)} ta bot to'xtatilmoqda...\n")
    for name in names:
        stop_instance(name)
    print("\n✅ Barcha botlar to'xtatildi!")


def start_all_instances() -> None:
    """Barcha bot instance'larni ishga tushiradi."""
    names = get_all_instance_names()
    if not names:
        print("📂 Hali hech qanday mijoz boti mavjud emas.")
        return

    print(f"🚀 Jami {len(names)} ta bot ishga tushirilmoqda...\n")
    for name in names:
        print(f"--- '{name}' ishga tushirilmoqda ---")
        start_instance(name)
        print()
    print("✅ Barcha botlar ishga tushirildi!")


def list_instances() -> None:
    """Barcha bot instance'lar ro'yxatini va portlarini ko'rsatadi."""
    ensure_instances_dir()
    dirs = [d for d in INSTANCES_DIR.iterdir() if d.is_dir() and not d.name.startswith("__")]
    if not dirs:
        print("📂 Hali hech qanday mijoz boti yaratilmagan.")
        return

    print("\n📋 --- MIJOZ BOTLARI RO'YXATI ---\n")
    if is_pm2_available():
        subprocess.run(["pm2", "list"])
    else:
        for d in sorted(dirs):
            env_file = d / ".env"
            env_data = parse_env_file(env_file) if env_file.exists() else {}
            mode = "Webhook" if env_data.get("USE_WEBHOOK") == "true" else "Polling"
            port = env_data.get("WEBAPP_PORT", "-")
            path = env_data.get("WEBHOOK_PATH", "-")

            pid_file = d / "bot.pid"
            status = "🔴 To'xtatilgan"
            if pid_file.exists():
                try:
                    pid = pid_file.read_text().strip()
                    if sys.platform == "win32":
                        result = subprocess.run(
                            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                            capture_output=True, text=True
                        )
                        if pid in result.stdout:
                            status = f"🟢 Ishlamoqda (PID: {pid})"
                        else:
                            status = f"🔴 To'xtatilgan"
                    else:
                        try:
                            os.kill(int(pid), 0)
                            status = f"🟢 Ishlamoqda (PID: {pid})"
                        except OSError:
                            status = "🔴 To'xtatilgan"
                except Exception:
                    status = "🟡 Noaniq"

            print(f"  • {d.name:20} [{mode} | Port: {port:5} | Path: {path:20}] -> {status}")
    print()


def remove_instance(name: str) -> None:
    """Bot instance'ni to'xtatib, papkasini o'chiradi va Nginx ni qayta yangilaydi."""
    inst_dir = get_instance_dir(name)
    if not inst_dir.exists():
        print(f"❌ '{name}' topilmadi.")
        return

    confirm = input(
        f"⚠️  '{name}' botini va barcha ma'lumotlarini o'chirishga ishonchingiz komilmi? (y/n): "
    ).strip().lower()
    if confirm == "y":
        stop_instance(name)
        if is_pm2_available():
            subprocess.run(["pm2", "delete", f"bot_{name}"])
        shutil.rmtree(inst_dir, ignore_errors=True)
        print(f"🗑️  '{name}' o'chirib tashlandi.")
        # Nginx dan ham o'chirish
        sync_nginx_safe(DEFAULT_DOMAIN)


def main() -> None:
    """CLI entry point."""
    import argparse

    if sys.platform == "win32":
        if hasattr(sys.stdout, "buffer"):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "buffer"):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Multi-Bot Webhook Manager / Deployer Script")
    parser.add_argument(
        "command",
        choices=[
            "add",
            "start",
            "stop",
            "restart",
            "list",
            "remove",
            "restart-all",
            "start-all",
            "stop-all",
            "sync-nginx",
        ],
        help="Bajariladigan amal",
    )
    parser.add_argument("name", nargs="?", help="Mijoz bot nomi (yoki 'all')")
    parser.add_argument("--domain", default=DEFAULT_DOMAIN, help="Nginx uchun domen")

    args = parser.parse_args()

    if args.command == "add":
        add_instance()
    elif args.command == "list":
        list_instances()
    elif args.command == "restart-all":
        restart_all_instances()
    elif args.command == "start-all":
        start_all_instances()
    elif args.command == "stop-all":
        stop_all_instances()
    elif args.command == "sync-nginx":
        sync_nginx_safe(args.domain)
    elif args.command in ["start", "stop", "restart", "remove"]:
        if not args.name:
            print(
                f"❌ '{args.command}' amali uchun mijoz nomini ko'rsating. "
                f"Masalan: python deploy.py {args.command} client_1 (yoki 'all')"
            )
            return

        if args.name.lower() == "all":
            if args.command == "start":
                start_all_instances()
            elif args.command == "stop":
                stop_all_instances()
            elif args.command == "restart":
                restart_all_instances()
            elif args.command == "remove":
                print("❌ Xavfsizlik yuzasidan 'remove all' ruxsat etilmagan.")
            return

        if args.command == "start":
            start_instance(args.name)
        elif args.command == "stop":
            stop_instance(args.name)
        elif args.command == "restart":
            restart_instance(args.name)
        elif args.command == "remove":
            remove_instance(args.name)


if __name__ == "__main__":
    main()
