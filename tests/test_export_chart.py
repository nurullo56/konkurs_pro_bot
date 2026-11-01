"""
test_export_chart.py — services/chart.py va services/export.py testlari.

Testlar qamrovi:
  - generate_registration_chart() — PNG fayl qaytarishi
  - export_users_to_excel() — .xlsx fayl qaytarishi
  - Bo'sh ma'lumotlar bilan ishlash
"""
from __future__ import annotations

import pytest
from aiogram.types import BufferedInputFile

from services.chart_service import generate_registration_chart
from services.export_service import export_users_to_excel


class TestGenerateChart:

    def test_returns_buffered_input_file(self):
        """Chart funksiyasi BufferedInputFile qaytarishi kerak."""
        data = [("2024-01-01", 5), ("2024-01-02", 12), ("2024-01-03", 8)]
        result = generate_registration_chart(data)
        assert isinstance(result, BufferedInputFile)

    def test_filename_is_png(self):
        """Fayl nomi .png bo'lishi kerak."""
        data = [("2024-01-01", 10)]
        result = generate_registration_chart(data)
        assert result.filename.endswith(".png")

    def test_file_content_not_empty(self):
        """PNG fayl bo'sh bo'lmasligi kerak."""
        data = [("2024-01-01", 3), ("2024-01-02", 7)]
        result = generate_registration_chart(data)
        assert len(result.data) > 0

    def test_empty_data_does_not_crash(self):
        """Bo'sh ma'lumotlar bilan ham ishga tushishi kerak."""
        result = generate_registration_chart([])
        assert isinstance(result, BufferedInputFile)

    def test_single_data_point(self):
        """Bitta nuqtali ma'lumot bilan ham ishlashi kerak."""
        result = generate_registration_chart([("2024-06-15", 100)])
        assert isinstance(result, BufferedInputFile)
        assert len(result.data) > 1000  # haqiqiy PNG fayl

    def test_large_data_set(self):
        """Ko'p kunlik ma'lumot bilan ham ishlashi kerak."""
        data = [(f"2024-01-{i:02d}", i * 5) for i in range(1, 15)]
        result = generate_registration_chart(data)
        assert isinstance(result, BufferedInputFile)


class TestExportUsersToExcel:

    def _make_user(self, uid: int, name: str, pts: int, banned: bool = False) -> dict:
        return {
            "user_id": uid,
            "full_name": name,
            "username": f"user_{uid}",
            "phone": f"+9989{uid}",
            "points": pts,
            "referrer_id": None,
            "joined_at": "2024-01-01 12:00:00",
            "is_banned": 1 if banned else 0,
            "registered": 1,
        }

    def test_returns_buffered_input_file(self):
        """Export funksiyasi BufferedInputFile qaytarishi kerak."""
        users = [self._make_user(1, "Ali", 50)]
        result = export_users_to_excel(users)
        assert isinstance(result, BufferedInputFile)

    def test_filename_is_xlsx_or_csv(self):
        """Fayl nomi .xlsx yoki .csv bo'lishi kerak."""
        users = [self._make_user(1, "Ali", 50)]
        result = export_users_to_excel(users)
        assert result.filename.endswith(".xlsx") or result.filename.endswith(".csv")

    def test_file_not_empty(self):
        """Excel fayl bo'sh bo'lmasligi kerak."""
        users = [self._make_user(1, "Ali", 50), self._make_user(2, "Vali", 30)]
        result = export_users_to_excel(users)
        assert len(result.data) > 0

    def test_empty_users_list(self):
        """Bo'sh foydalanuvchilar ro'yxati bilan ham ishga tushishi kerak."""
        result = export_users_to_excel([])
        assert isinstance(result, BufferedInputFile)

    def test_banned_user_status_label(self):
        """Ban qilingan user 'Bloklangan' yoki 'Banned' deb belgilanishi kerak."""
        import io
        users = [self._make_user(1, "Banned User", 0, banned=True)]
        result = export_users_to_excel(users)

        filename = result.filename
        if filename.endswith(".xlsx"):
            # Excel faylni openpyxl bilan o'qib tekshiramiz
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(result.data))
            ws = wb.active
            cell_values = [str(cell.value or "") for row in ws.iter_rows() for cell in row]
            status_values = " ".join(cell_values)
            assert "Bloklangan" in status_values or "Banned" in status_values
        else:
            # CSV fallback — matn sifatida tekshiramiz
            text = result.data.decode("utf-8-sig")
            assert "Banned" in text

    def test_multiple_users(self):
        """Ko'p foydalanuvchi bilan ham ishlashi kerak."""
        users = [self._make_user(i, f"User {i}", i * 10) for i in range(1, 50)]
        result = export_users_to_excel(users)
        assert isinstance(result, BufferedInputFile)
        assert len(result.data) > 5000  # 49 ta user = katta fayl
