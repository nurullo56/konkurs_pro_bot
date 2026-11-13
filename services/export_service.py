from __future__ import annotations

import io
from typing import Any, Dict, List
from aiogram.types import BufferedInputFile


def _sanitize_cell(val: Any) -> Any:
    """Prepend single quote if string starts with formula characters (=, +, -, @)."""
    if isinstance(val, str) and val.startswith(("=", "+", "-", "@")):
        return f"'{val}"
    return val


def export_users_to_excel(users_data: List[Dict[str, Any]]) -> BufferedInputFile:
    """
    Exports users list to an Excel (.xlsx) file using openpyxl or pandas.
    Fallback to CSV in memory if openpyxl/pandas not available.
    """
    try:
        import openpyxl
        from openpyxl.styles import Alignment, Font, PatternFill

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Foydalanuvchilar"

        headers = [
            "User ID",
            "F.I.SH",
            "Username",
            "Telefon",
            "Ballari",
            "Referral ID",
            "Ro'yxatdan o'tgan vaqti",
            "Holati",
        ]
        ws.append(headers)

        header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for user in users_data:
            status = "🚫 Bloklangan" if user.get("is_banned") else "✅ Faol"
            ws.append([
                user.get("user_id"),
                _sanitize_cell(user.get("full_name") or ""),
                _sanitize_cell(f"@{user.get('username')}" if user.get("username") else ""),
                _sanitize_cell(user.get("phone") or ""),
                user.get("points", 0),
                user.get("referrer_id") or "",
                str(user.get("joined_at") or ""),
                status,
            ])

        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        return BufferedInputFile(buf.getvalue(), filename="users_export.xlsx")

    except ImportError:
        # Fallback to CSV if openpyxl is not installed
        import csv

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "User ID", "F.I.SH", "Username", "Telefon", "Ballari", "Referral ID", "Joined At", "Status"
        ])

        for u in users_data:
            status = "Banned" if u.get("is_banned") else "Active"
            writer.writerow([
                u.get("user_id"),
                _sanitize_cell(u.get("full_name") or ""),
                _sanitize_cell(u.get("username") or ""),
                _sanitize_cell(u.get("phone") or ""),
                u.get("points", 0),
                u.get("referrer_id") or "",
                u.get("joined_at") or "",
                status,
            ])

        buf = io.BytesIO(output.getvalue().encode("utf-8-sig"))
        return BufferedInputFile(buf.getvalue(), filename="users_export.csv")
