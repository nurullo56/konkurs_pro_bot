from __future__ import annotations

from typing import Any, Dict, List, Optional
from database.repositories.base_repo import BaseRepository


class ChannelRepository(BaseRepository):
    async def add(self, chat_id: str, title: str, invite_link: Optional[str]) -> None:
        if self.db.is_postgres:
            sql = """
            INSERT INTO channels (chat_id, title, invite_link) VALUES ($1, $2, $3)
            ON CONFLICT (chat_id) DO UPDATE SET
                title = EXCLUDED.title,
                invite_link = EXCLUDED.invite_link
            """
            await self.db.execute(sql, chat_id, title, invite_link)
        else:
            sql = """
            INSERT INTO channels (chat_id, title, invite_link) VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                title = excluded.title,
                invite_link = excluded.invite_link
            """
            await self.db.execute(sql, chat_id, title, invite_link)

    async def remove(self, chat_id: str) -> bool:
        row = await self.fetchrow("SELECT 1 FROM channels WHERE chat_id = ?", chat_id)
        if not row:
            return False
        await self.execute("DELETE FROM channels WHERE chat_id = ?", chat_id)
        return True

    async def get_all(self) -> List[Dict[str, Any]]:
        return await self.fetch("SELECT * FROM channels ORDER BY id")
