from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Windows PowerShell cp1251 muammosini hal qilish — emoji to'g'ri chiqadi
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# deploy.py scripts/ papkasida yoki root'da bo'lishi mumkin.
_here = Path(__file__).resolve().parent
if _here.name == "scripts":
    BASE_DIR = _here.parent
else:
    BASE_DIR = _here

INSTANCES_DIR = BASE_DIR / "instances"
BOT_SCRIPT = BASE_DIR / "bot.py"


def ensure_instances_dir() -> None:
    """instances/ papkasini yaratadi (agar mavjud bo'lmasa)."""
    INSTANCES_DIR.mkdir(exist_ok=True)


def is_pm2_available() -> bool:
    """pm2 buyrugi mavjudligini tekshiradi."""
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


def add_instance() -> None:
    """Yangi bot instance qo'shadi: sozlamalarni so'rab .env yaratadi va ishga tushiradi."""
    ensure_instances_dir()
    print("\n➕ --- YANGI MIJOZ BOTINI QO'SHISH ---\n")
    name = input("Mijoz nomi/ID (masalan: client_1, store_uz): ").strip()
    if not name:
        print("❌ Mijoz nomi kiritilmadi!")
        return

    inst_dir = get_instance_dir(name)
    if inst_dir.exists():
        print(f"❌ '{name}' nomli mijoz bot mavjud!")
        return

    bot_token = input("Bot Token (Telegram BotFather'dan): ").strip()
    admin_ids = input("Admin ID lari (vergul bilan) [7867633335]: ").strip() or "7867633335"
    contest_name = input("Konkurs nomi [Konkurs]: ").strip() or "Konkurs"
    prize_text = input("Sovrin matni [2 000 000 so'm]: ").strip() or "2 000 000 so'm"
    top_n = input("Top g'oliblar soni TOP_N [10]: ").strip() or "10"
    start_points = input("Boshlang'ich ball [5]: ").strip() or "5"
    referral_points = input("Referral ball [1]: ").strip() or "1"

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
        f"USE_WEBHOOK=false\n"
        f"REDIS_URL=\n"
    )

    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)

    print(f"\n✅ '{name}' uchun sozlamalar saqlandi: {env_path}")
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
            # Hali ishlayaptimi?
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {old_pid}", "/NH"],
                capture_output=True, text=True
            )
            if str(old_pid) in result.stdout:
                print(f"⚠️ '{name}' allaqachon ishlayapti (PID: {old_pid}). Avval stop qiling.")
                return
        except Exception:
            pass

    log_file = inst_dir / "bot.log"

    # .env fayldan barcha o'zgaruvchilarni o'qib, to'g'ridan-to'g'ri env ga qo'shamiz.
    # Bu ENV_FILE mexanizmiga tayanmaydi — ishonchli va universal yechim.
    env = os.environ.copy()
    env_vars = parse_env_file(env_path)
    env.update(env_vars)
    # ENV_FILE ham qo'shib qo'yamiz (settings.py load_dotenv uchun, agar kerak bo'lsa)
    env["ENV_FILE"] = str(env_path)
    env["LOG_FILE"] = str(log_file)
    env["PYTHONUNBUFFERED"] = "1"   # log ni darhol yozish uchun
    env["PYTHONIOENCODING"] = "utf-8"

    # Windows: pythonw.exe — konsolsiz, ota jarayondan to'liq mustaqil ishlaydi.
    # Log faylga yozish uchun bot.py LOG_FILE env ni ishlatadi (FileHandler).
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

    pid = int(pid_file.read_text().strip())
    try:
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
    """Barcha bot instance'larni ro'yxatini ko'rsatadi."""
    ensure_instances_dir()
    dirs = [d for d in INSTANCES_DIR.iterdir() if d.is_dir()]
    if not dirs:
        print("📂 Hali hech qanday mijoz boti yaratilmagan.")
        return

    print("\n📋 --- MIJOZ BOTLARI RO'YXATI ---\n")
    if is_pm2_available():
        subprocess.run(["pm2", "list"])
    else:
        for d in sorted(dirs):
            pid_file = d / "bot.pid"
            status = "🔴 To'xtatilgan"
            if pid_file.exists():
                try:
                    pid = pid_file.read_text().strip()
                    result = subprocess.run(
                        ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                        capture_output=True, text=True
                    )
                    if pid in result.stdout:
                        status = f"🟢 Ishlamoqda (PID: {pid})"
                    else:
                        status = f"🔴 To'xtatilgan (eski PID: {pid})"
                except Exception:
                    status = f"🟡 Noaniq"
            print(f"  • {d.name}: {status}")
    print()


def remove_instance(name: str) -> None:
    """Bot instance'ni to'xtatib, papkasini o'chiradi."""
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


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Multi-Bot Manager / Deployer Script")
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
        ],
        help="Amal",
    )
    parser.add_argument("name", nargs="?", help="Mijoz bot nomi (yoki 'all')")

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
