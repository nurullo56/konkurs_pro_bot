from __future__ import annotations

from typing import Any, Dict, List, Optional
from database.repositories.base_repo import BaseRepository


class AdminRepository(BaseRepository):
    """Adminlarni ma'lumotlar bazasida boshqarish uchun repository."""

    async def add(self, user_id: int, username: Optional[str] = None, full_name: Optional[str] = None) -> None:
        """Yangi admin qo'shadi yoki mavjud bo'lsa yangilaydi."""
        if self.db.is_postgres:
            sql = """
            INSERT INTO admins (user_id, username, full_name) VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO UPDATE SET
                username = EXCLUDED.username,
                full_name = EXCLUDED.full_name
            """
            await self.db.execute(sql, user_id, username, full_name)
        else:
            sql = """
            INSERT INTO admins (user_id, username, full_name) VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name
            """
            await self.db.execute(sql, user_id, username, full_name)

    async def remove(self, user_id: int) -> bool:
        """Adminni ma'lumotlar bazasidan o'chiradi."""
        row = await self.fetchrow("SELECT 1 FROM admins WHERE user_id = ?", user_id)
        if not row:
            return False
        await self.execute("DELETE FROM admins WHERE user_id = ?", user_id)
        return True

    async def is_admin(self, user_id: int) -> bool:
        """Foydalanuvchi bazadagi adminlar ro'yxatida bor-yo'qligini tekshiradi."""
        row = await self.fetchrow("SELECT 1 FROM admins WHERE user_id = ?", user_id)
        return row is not None

    async def get_all(self) -> List[Dict[str, Any]]:
        """Barcha bazadagi adminlar ro'yxatini qaytaradi."""
        return await self.fetch("SELECT * FROM admins ORDER BY user_id")
