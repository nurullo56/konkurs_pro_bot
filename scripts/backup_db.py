import os
import shutil
import zipfile
import subprocess
from datetime import datetime
import glob

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import Config

# Konstantalar
BACKUP_DIR = os.path.join(os.path.dirname(__file__), '..', 'backups')
MAX_BACKUPS = 7  # 7 kunlik arxiv saqlanadi

def create_backup_dir():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

def clean_old_backups(prefix):
    """Faqat oxirgi MAX_BACKUPS ta arxivni saqlaydi, eskilarni o'chiradi."""
    search_pattern = os.path.join(BACKUP_DIR, f"{prefix}_*.zip")
    files = sorted(glob.glob(search_pattern), key=os.path.getmtime)
    
    if len(files) > MAX_BACKUPS:
        for f in files[:-MAX_BACKUPS]:
            os.remove(f)
            print(f"Eski backup o'chirildi: {f}")

def backup_sqlite(db_path: str):
    print(f"SQLite bazasi backup qilinmoqda: {db_path} ...")
    if not os.path.exists(db_path):
        print(f"Xato: Baza topilmadi: {db_path}")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    temp_backup = os.path.join(BACKUP_DIR, f"temp_{timestamp}.db")
    zip_path = os.path.join(BACKUP_DIR, f"sqlite_backup_{timestamp}.zip")

    # DB faylidan nusxa olish
    shutil.copy2(db_path, temp_backup)
    
    # Zip qilish
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(temp_backup, os.path.basename(db_path))
    
    # Temp faylni o'chirish
    os.remove(temp_backup)
    
    print(f"Muvaffaqiyatli saqlandi: {zip_path}")
    clean_old_backups("sqlite_backup")

def backup_postgres(dsn: str):
    print("PostgreSQL bazasi backup qilinmoqda...")
    if not dsn:
        print("Xato: POSTGRES_DSN kiritilmagan!")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    sql_backup = os.path.join(BACKUP_DIR, f"pg_backup_{timestamp}.sql")
    zip_path = os.path.join(BACKUP_DIR, f"pg_backup_{timestamp}.zip")

    try:
        # pg_dump orqali bazadan nusxa ko'chirish
        subprocess.run(["pg_dump", dsn, "-f", sql_backup], check=True)
        
        # Zip qilish
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(sql_backup, os.path.basename(sql_backup))
            
        # Asl SQL faylni o'chirish
        os.remove(sql_backup)
        
        print(f"Muvaffaqiyatli saqlandi: {zip_path}")
        clean_old_backups("pg_backup")
    except subprocess.CalledProcessError as e:
        print(f"PostgreSQL backup xatosi: {e}")
    except FileNotFoundError:
        print("Xato 'pg_dump' dasturi topilmadi! Tizimga PostgreSQL o'rnatilganiga ishonch hosil qiling.")


if __name__ == "__main__":
    create_backup_dir()
    
    config = Config.load()
    
    db_type = config.db_type.lower()
    
    if db_type in ("postgresql", "postgres", "pg"):
        backup_postgres(config.postgres_dsn)
    else:
        # SQLite
        backup_sqlite(config.db_path)
