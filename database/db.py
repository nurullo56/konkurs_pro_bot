from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, List, Optional

import aiosqlite

try:
    import asyncpg
except ImportError:
    asyncpg = None  # type: ignore[assignment]

from database.repositories import (
    AdminRepository,
    ChannelRepository,
    JoinRequestRepository,
    SettingsRepository,
    UserRepository,
)

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    full_name   TEXT NOT NULL,
    phone       TEXT,
    referrer_id INTEGER REFERENCES users(user_id),
    points      INTEGER NOT NULL DEFAULT 0,
    registered  INTEGER NOT NULL DEFAULT 0,
    is_banned   INTEGER NOT NULL DEFAULT 0,
    joined_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_users_referrer ON users(referrer_id);
CREATE INDEX IF NOT EXISTS idx_users_points ON users(points DESC);

CREATE TABLE IF NOT EXISTS channels (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id     TEXT NOT NULL UNIQUE,
    title       TEXT,
    invite_link TEXT,
    added_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS settings (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS join_requests (
    user_id     INTEGER NOT NULL,
    chat_id     TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, chat_id)
);

CREATE TABLE IF NOT EXISTS admins (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    full_name   TEXT,
    added_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id     BIGINT PRIMARY KEY,
    username    VARCHAR(255),
    full_name   VARCHAR(255) NOT NULL,
    phone       VARCHAR(50),
    referrer_id BIGINT REFERENCES users(user_id),
    points      INT NOT NULL DEFAULT 0,
    registered  INT NOT NULL DEFAULT 0,
    is_banned   INT NOT NULL DEFAULT 0,
    joined_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_users_referrer ON users(referrer_id);
CREATE INDEX IF NOT EXISTS idx_users_points ON users(points DESC);

CREATE TABLE IF NOT EXISTS channels (
    id          SERIAL PRIMARY KEY,
    chat_id     VARCHAR(255) NOT NULL UNIQUE,
    title       VARCHAR(255),
    invite_link TEXT,
    added_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    key         VARCHAR(255) PRIMARY KEY,
    value       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS join_requests (
    user_id     BIGINT NOT NULL,
    chat_id     VARCHAR(255) NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, chat_id)
);

CREATE TABLE IF NOT EXISTS admins (
    user_id     BIGINT PRIMARY KEY,
    username    VARCHAR(255),
    full_name   VARCHAR(255),
    added_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def _safe_dsn(dsn: str) -> str:
    """
    DSN dagi parolni yashiradi — log'larga xavfsiz chiqarish uchun.

    :param dsn: To'liq PostgreSQL DSN (masalan: postgresql://user:password@host/db).
    :return: Paroli yashirilgan DSN.
    """
    try:
        if "://" in dsn and "@" in dsn:
            prefix, rest = dsn.split("://", 1)
            userinfo, hostpart = rest.rsplit("@", 1)
            if ":" in userinfo:
                user, _ = userinfo.split(":", 1)
                return f"{prefix}://{user}:***@{hostpart}"
        return dsn
    except Exception:
        return "<dsn>"


class Database:
    """
    Database wrapper: PostgreSQL (asyncpg) va SQLite (aiosqlite) ni qo'llab-quvvatlaydi.
    Repository pattern orqali barcha repositorylarni birlashtiradi.
    """

    def __init__(self, db_type: str = "sqlite", dsn: str = "", path: str = "contest.db") -> None:
        """
        :param db_type: 'sqlite', 'postgresql', 'postgres' yoki 'pg'.
        :param dsn: PostgreSQL DSN (bo'sh bo'lsa SQLite ishlatiladi).
        :param path: SQLite fayl yo'li (default: 'contest.db').
        """
        import asyncio
        self.db_type = db_type.lower()
        self.dsn = dsn
        self.path = path
        self.is_postgres = self.db_type in ("postgresql", "postgres", "pg")

        self.sqlite_conn: Optional[aiosqlite.Connection] = None
        self.sqlite_lock = asyncio.Lock()
        self.pg_pool: Optional[Any] = None

        self.users: UserRepository = UserRepository(self)
        self.channels: ChannelRepository = ChannelRepository(self)
        self.settings: SettingsRepository = SettingsRepository(self)
        self.join_requests: JoinRequestRepository = JoinRequestRepository(self)
        self.admins: AdminRepository = AdminRepository(self)

    def __repr__(self) -> str:
        """Debug uchun insonxon ko'rinish."""
        if self.is_postgres:
            return f"Database(type=postgresql, dsn={_safe_dsn(self.dsn)})"
        return f"Database(type=sqlite, path={self.path})"

    def _ensure_connected(self) -> None:
        """
        Ma'lumotlar bazasiga ulanishni tekshiradi.
        Agar ulanmagan bo'lsa, RuntimeError ko'taradi.
        """
        if self.is_postgres:
            if self.pg_pool is None:
                raise RuntimeError(
                    f"PostgreSQL pool is not initialized (dsn={_safe_dsn(self.dsn)}). "
                    "Call await db.connect() before using the database."
                )
        else:
            if self.sqlite_conn is None:
                raise RuntimeError(
                    f"SQLite connection is not initialized (path={self.path}). "
                    "Call await db.connect() before using the database."
                )

    async def connect(self) -> None:
        """
        Ma'lumotlar bazasiga ulanadi va sxemani yaratadi.
        PostgreSQL muvaffaqiyatsiz bo'lsa — pg_pool yopiladi va SQLite'ga fallback.
        """
        if self.is_postgres:
            if asyncpg:
                try:
                    logging.info(f"Connecting to PostgreSQL: {_safe_dsn(self.dsn)}")
                    self.pg_pool = await asyncpg.create_pool(self.dsn)
                    async with self.pg_pool.acquire() as conn:
                        await conn.execute(POSTGRES_SCHEMA)
                    logging.info("PostgreSQL database connected and initialized.")
                    return
                except Exception as e:
                    logging.warning(
                        f"PostgreSQL connection failed ({e}), falling back to SQLite ({self.path})."
                    )
                    # FIX: pg_pool yopilmasa connection leak bo'ladi
                    if self.pg_pool is not None:
                        try:
                            await self.pg_pool.close()
                        except Exception as close_err:
                            logging.debug(f"Error closing pg_pool during fallback: {close_err}")
                        self.pg_pool = None
                    self.is_postgres = False
            else:
                logging.warning("asyncpg is not installed, falling back to SQLite.")
                self.is_postgres = False

        # SQLite Fallback yoki standart rejim
        logging.info(f"Connecting to SQLite: {self.path}")
        self.sqlite_conn = await aiosqlite.connect(self.path)
        self.sqlite_conn.row_factory = aiosqlite.Row
        await self.sqlite_conn.execute("PRAGMA journal_mode=WAL")
        await self.sqlite_conn.execute("PRAGMA busy_timeout=60000")
        await self.sqlite_conn.execute("PRAGMA synchronous=NORMAL")
        await self.sqlite_conn.execute("PRAGMA foreign_keys=ON")
        await self.sqlite_conn.executescript(SQLITE_SCHEMA)
        await self.sqlite_conn.commit()
        logging.info("SQLite database connected and initialized.")

    async def close(self) -> None:
        """
        Ma'lumotlar bazasi bilan ulanishni xavfsiz yopadi.
        Xatolar loglangani holda o'tkazib yuboriladi.
        """
        if self.pg_pool:
            try:
                await self.pg_pool.close()
                logging.info("PostgreSQL pool closed.")
            except Exception as e:
                logging.warning(f"Error closing PostgreSQL pool: {e}")
            finally:
                self.pg_pool = None
        if self.sqlite_conn:
            try:
                await self.sqlite_conn.close()
                logging.info("SQLite connection closed.")
            except Exception as e:
                logging.warning(f"Error closing SQLite connection: {e}")
            finally:
                self.sqlite_conn = None

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[Any]:
        """
        Tranzaksiya context manager.

        PostgreSQL: asyncpg native transaction.
        SQLite: BEGIN IMMEDIATE + commit/rollback.

        Ishlatish:
            async with db.transaction():
                await db.execute(...)
        """
        self._ensure_connected()  # ✅ FIX #2

        if self.is_postgres and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                async with conn.transaction():
                    yield conn
        elif self.sqlite_conn:
            async with self.sqlite_lock:
                await self.sqlite_conn.execute("BEGIN IMMEDIATE")
                try:
                    yield self.sqlite_conn
                    await self.sqlite_conn.commit()
                except Exception:
                    await self.sqlite_conn.rollback()
                    raise
        else:
            raise RuntimeError("No active database connection for transaction.")

    async def execute(self, sql: str, *args: Any, commit: bool = True) -> None:
        """
        SQL so'rovini bajaradi (INSERT, UPDATE, DELETE).

        :param sql: SQL so'rovi (? yoki $N placeholder).
        :param args: So'rov parametrlari.
        :param commit: SQLite uchun avtomatik commit (default: True).
        """
        self._ensure_connected()  # ✅ FIX #2

        if self.is_postgres and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                await conn.execute(sql, *args)
        elif self.sqlite_conn:
            async with self.sqlite_lock:
                async with self.sqlite_conn.execute(sql, args) as cur:
                    _ = cur  # cursor yopiladi (async with)
                if commit:
                    await self.sqlite_conn.commit()

    async def execute_many(self, sql: str, params_list: list[tuple]) -> None:
        """
        Bir nechta SQL so'rovlarini batch rejimda bajaradi (performance uchun).

        :param sql: SQL so'rovi shabloni.
        :param params_list: Har bir so'rov uchun parametrlar ro'yxati.
        """
        if not params_list:
            return

        self._ensure_connected()  # ✅ FIX #2 (early return'dan keyin)

        if self.is_postgres and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                await conn.executemany(sql, params_list)
        elif self.sqlite_conn:
            async with self.sqlite_lock:
                await self.sqlite_conn.executemany(sql, params_list)
                await self.sqlite_conn.commit()

    async def fetchrow(self, sql: str, *args: Any) -> Optional[Dict[str, Any]]:
        """
        Bitta qatorni qaytaradi yoki None.

        FIX: SQLite cursor async with bilan to'g'ri yopiladi.

        :param sql: SELECT SQL so'rovi.
        :param args: So'rov parametrlari.
        :return: Dict yoki None.
        """
        self._ensure_connected()  # ✅ FIX #2

        if self.is_postgres and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                row = await conn.fetchrow(sql, *args)
                return dict(row) if row else None
        elif self.sqlite_conn:
            async with self.sqlite_lock:
                async with self.sqlite_conn.execute(sql, args) as cur:
                    row = await cur.fetchone()
                    return dict(row) if row else None
        return None

    async def fetch(self, sql: str, *args: Any) -> List[Dict[str, Any]]:
        """
        Bir nechta qatorlarni qaytaradi.

        FIX: SQLite cursor async with bilan to'g'ri yopiladi.

        :param sql: SELECT SQL so'rovi.
        :param args: So'rov parametrlari.
        :return: Dict ro'yxati.
        """
        self._ensure_connected()  # ✅ FIX #2

        if self.is_postgres and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                rows = await conn.fetch(sql, *args)
                return [dict(r) for r in rows]
        elif self.sqlite_conn:
            async with self.sqlite_lock:
                async with self.sqlite_conn.execute(sql, args) as cur:
                    rows = await cur.fetchall()
                    return [dict(r) for r in rows]
        return []