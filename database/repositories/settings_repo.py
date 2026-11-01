from __future__ import annotations

from typing import Optional
from database.repositories.base_repo import BaseRepository


class SettingsRepository(BaseRepository):
    async def get(self, key: str, default: str = "") -> str:
        row = await self.fetchrow("SELECT value FROM settings WHERE key = ?", key)
        return row["value"] if row else default

    async def set(self, key: str, value: str) -> None:
        if self.db.is_postgres:
            sql = """
            INSERT INTO settings (key, value) VALUES ($1, $2)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """
            await self.db.execute(sql, key, value)
        else:
            sql = """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """
            await self.db.execute(sql, key, value)
