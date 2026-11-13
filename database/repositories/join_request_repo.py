from __future__ import annotations

from database.repositories.base_repo import BaseRepository


class JoinRequestRepository(BaseRepository):
    async def add(self, user_id: int, chat_id: str) -> None:
        if self.db.is_postgres:
            sql = """
            INSERT INTO join_requests (user_id, chat_id) VALUES ($1, $2)
            ON CONFLICT (user_id, chat_id) DO UPDATE SET created_at = CURRENT_TIMESTAMP
            """
            await self.db.execute(sql, user_id, chat_id)
        else:
            sql = """
            INSERT INTO join_requests (user_id, chat_id) VALUES (?, ?)
            ON CONFLICT(user_id, chat_id) DO UPDATE SET created_at = datetime('now')
            """
            await self.db.execute(sql, user_id, chat_id)

    async def has_request(self, user_id: int, chat_id: str) -> bool:
        row = await self.fetchrow(
            "SELECT 1 FROM join_requests WHERE user_id = ? AND chat_id = ?",
            user_id, chat_id
        )
        return row is not None
        