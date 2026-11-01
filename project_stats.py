# -*- coding: utf-8 -*-
"""
Loyiha statistikasi skripti:
Fayllar, papkalar va umumiy kod qatorlarini hisoblash uchun mo'ljallangan.
"""

import os
import sys
from collections import defaultdict
from pathlib import Path

# Windows konsolida UTF-8 kodlanishini ta'minlash
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Hisobga olinmaydigan papkalar
EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    "venv",
    ".venv",
    "env",
    ".idea",
    ".vscode",
    "htmlcov",
}

# Hisobga olinmaydigan texnik / binar kengaytmalar
EXCLUDE_EXTENSIONS = {
    ".coverage",
    ".pyc",
    ".log",
    ".db",
    ".db-wal",
    ".db-shm",
    ".sqlite",
    ".sqlite3",
    ".pid",
}

# Kod va matn turlari tavsifi
EXT_LABELS = {
    ".py": "Python (kod)",
    ".sql": "SQL (baza)",
    ".json": "JSON (ma'lumot)",
    ".yml": "YAML (konfig)",
    ".yaml": "YAML (konfig)",
    ".env": "Env (sozlamalar)",
    ".example": "Env Example",
    ".md": "Markdown (hujjat)",
    ".txt": "Text (matn)",
    ".ini": "Config (INI)",
    ".sh": "Shell Script",
    ".bat": "Batch Script",
    ".conf": "Nginx/Server Conf",
    ".html": "HTML",
    ".css": "CSS",
    ".js": "JavaScript",
}


def count_lines(filepath: Path):
    """Fayldagi umumiy, bo'sh, izoh va sof kod qatorlarini hisoblaydi."""
    total = 0
    blank = 0
    comment = 0
    code = 0

    ext = filepath.suffix.lower()
    is_py = ext == ".py"
    is_sql = ext == ".sql"
    is_conf = ext in {".conf", ".ini", ".sh"}

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                total += 1
                stripped = line.strip()
                if not stripped:
                    blank += 1
                elif is_py and stripped.startswith("#"):
                    comment += 1
                elif is_sql and (stripped.startswith("--") or stripped.startswith("/*")):
                    comment += 1
                elif is_conf and (stripped.startswith("#") or stripped.startswith(";")):
                    comment += 1
                else:
                    code += 1
    except Exception:
        pass

    return total, blank, comment, code


def main():
    root_dir = Path(".").resolve()
    print("=" * 70)
    print(f"📊 LOYIHA STATISTIKASI: {root_dir.name}")
    print(f"📁 Manzil: {root_dir}")
    print("=" * 70)

    dir_count = 0
    file_count = 0

    ext_stats = defaultdict(lambda: {"files": 0, "total": 0, "blank": 0, "comment": 0, "code": 0})
    folder_stats = defaultdict(lambda: {"files": 0, "code": 0, "total": 0})
    file_ranking = []

    for root, dirs, files in os.walk(root_dir):
        # E'tiborga olinmaydigan papkalarni qoldirib ketish
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]

        rel_root = os.path.relpath(root, root_dir)
        top_folder = rel_root.split(os.sep)[0] if rel_root != "." else "Ildiz (Root)"

        if rel_root != ".":
            dir_count += 1

        for f in files:
            file_path = Path(root) / f
            ext = file_path.suffix.lower()

            # Binar yoki vaqtinchalik fayllarni o'tkazib yuborish
            if ext in EXCLUDE_EXTENSIONS or f.startswith("."):
                continue

            file_count += 1
            tot, blk, cmt, cd = count_lines(file_path)

            ext_stats[ext]["files"] += 1
            ext_stats[ext]["total"] += tot
            ext_stats[ext]["blank"] += blk
            ext_stats[ext]["comment"] += cmt
            ext_stats[ext]["code"] += cd

            folder_stats[top_folder]["files"] += 1
            folder_stats[top_folder]["code"] += cd
            folder_stats[top_folder]["total"] += tot

            if tot > 0:
                rel_file = os.path.relpath(file_path, root_dir)
                file_ranking.append((rel_file, tot, cd))

    print(f"\n📂 Umumiy papkalar soni : {dir_count} ta")
    print(f"📄 Manbali fayllar soni  : {file_count} ta\n")

    # Fayl turlari bo'yicha jadval
    print("-" * 70)
    print(f"{'Fayl turi':<20} | {'Soni':<6} | {'Sof Kod':<9} | {'Izoh':<6} | {'Bo`sh':<6} | {'Jami':<8}")
    print("-" * 70)

    grand_total = 0
    grand_blank = 0
    grand_comment = 0
    grand_code = 0

    sorted_exts = sorted(ext_stats.items(), key=lambda x: x[1]["code"], reverse=True)

    for ext, s in sorted_exts:
        label = EXT_LABELS.get(ext, ext if ext else "kengaytmasiz")
        print(f"{label:<20} | {s['files']:<6} | {s['code']:<9} | {s['comment']:<6} | {s['blank']:<6} | {s['total']:<8}")
        grand_total += s["total"]
        grand_blank += s["blank"]
        grand_comment += s["comment"]
        grand_code += s["code"]

    print("-" * 70)
    print(f"{'JAMI':<20} | {file_count:<6} | {grand_code:<9} | {grand_comment:<6} | {grand_blank:<6} | {grand_total:<8}")
    print("=" * 70)

    # Papkalar bo'yicha tahlil
    print("\n📁 PAPKALAR KESIMIDA:")
    print("-" * 70)
    print(f"{'Papka nomi':<25} | {'Fayllar':<8} | {'Sof Kod':<10} | {'Jami qatorlar':<12}")
    print("-" * 70)
    for folder, data in sorted(folder_stats.items(), key=lambda x: x[1]["code"], reverse=True):
        print(f"{folder:<25} | {data['files']:<8} | {data['code']:<10} | {data['total']:<12}")
    print("-" * 70)

    # Eng ko'p kod yozilgan fayllar Top-10
    file_ranking.sort(key=lambda x: x[2], reverse=True)
    print("\n🏆 ENG KO'P KOD YOZILGAN FAYLLAR (TOP-10):")
    print("-" * 70)
    print(f"{'Fayl nomi':<45} | {'Sof Kod':<10} | {'Jami qator':<10}")
    print("-" * 70)
    for fpath, tot, cd in file_ranking[:10]:
        print(f"{fpath:<45} | {cd:<10} | {tot:<10}")
    print("=" * 70)
    print("✨ Statistika muvaffaqiyatli hisoblandi!\n")


if __name__ == "__main__":
    main()
