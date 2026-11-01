from __future__ import annotations

import re
from typing import Any, List, Optional, Dict


class BaseRepository:
    def __init__(self, db_wrapper: Any) -> None:
        self.db = db_wrapper

    def _prepare_sql(self, sql: str) -> str:
        """Converts ? placeholders to $1, $2 for Postgres if needed."""
        if self.db.is_postgres:
            count = 0
            def replacer(match):
                nonlocal count
                count += 1
                return f"${count}"
            return re.sub(r'\?', replacer, sql)
        return sql

    async def execute(self, sql: str, *args: Any) -> None:
        prepared_sql = self._prepare_sql(sql)
        await self.db.execute(prepared_sql, *args)

    async def fetchrow(self, sql: str, *args: Any) -> Optional[Dict[str, Any]]:
        prepared_sql = self._prepare_sql(sql)
        return await self.db.fetchrow(prepared_sql, *args)

    async def fetch(self, sql: str, *args: Any) -> List[Dict[str, Any]]:
        prepared_sql = self._prepare_sql(sql)
        return await self.db.fetch(prepared_sql, *args)
