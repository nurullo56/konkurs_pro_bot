from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from database.repositories.base_repo import BaseRepository


class UserRepository(BaseRepository):
    async def get_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        return await self.fetchrow("SELECT * FROM users WHERE user_id = ?", user_id)

    async def is_registered(self, user_id: int) -> bool:
        row = await self.fetchrow("SELECT 1 FROM users WHERE user_id = ? AND registered = 1", user_id)
        return row is not None

    async def register_and_credit_referrer(
        self,
        user_id: int,
        full_name: str,
        username: Optional[str],
        phone: str,
        referrer_id: Optional[int],
        start_points: int,
        referral_points: int,
    ) -> Tuple[bool, Optional[int]]:
        """
        Atomically registers a user and credits referrer points if eligible.
        Returns tuple of (is_new, valid_referrer_id).
        """
        existing = await self.get_by_id(user_id)
        if existing and existing.get("registered"):
            return False, None

        valid_referrer = referrer_id if referrer_id and referrer_id != user_id else None
        if valid_referrer and not await self.is_registered(valid_referrer):
            valid_referrer = None

        if self.db.is_postgres and self.db.pg_pool:
            async with self.db.pg_pool.acquire() as conn:
                async with conn.transaction():
                    row = await conn.fetchrow("SELECT registered FROM users WHERE user_id = $1", user_id)
                    if row and row["registered"]:
                        return False, None

                    upsert_sql = """
                    INSERT INTO users (user_id, username, full_name, phone, referrer_id, points, registered)
                    VALUES ($1, $2, $3, $4, $5, $6, 1)
                    ON CONFLICT (user_id) DO UPDATE SET
                        username  = EXCLUDED.username,
                        full_name = EXCLUDED.full_name,
                        phone     = EXCLUDED.phone,
                        registered = 1,
                        points = users.points + EXCLUDED.points
                    """
                    await conn.execute(upsert_sql, user_id, username, full_name, phone, valid_referrer, start_points)
                    if valid_referrer:
                        await conn.execute("UPDATE users SET points = points + $1 WHERE user_id = $2", referral_points, valid_referrer)
        elif self.db.sqlite_conn:
            async with self.db.sqlite_lock:
                await self.db.sqlite_conn.execute("BEGIN IMMEDIATE")
                try:
                    async with self.db.sqlite_conn.execute("SELECT registered FROM users WHERE user_id = ?", (user_id,)) as cur:
                        row = await cur.fetchone()
                        if row and row["registered"]:
                            await self.db.sqlite_conn.rollback()
                            return False, None

                    upsert_sql = """
                    INSERT INTO users (user_id, username, full_name, phone, referrer_id, points, registered)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                    ON CONFLICT(user_id) DO UPDATE SET
                        username  = excluded.username,
                        full_name = excluded.full_name,
                        phone     = excluded.phone,
                        registered = 1,
                        points = users.points + excluded.points
                    """
                    await self.db.sqlite_conn.execute(upsert_sql, (user_id, username, full_name, phone, valid_referrer, start_points))
                    if valid_referrer:
                        await self.db.sqlite_conn.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (referral_points, valid_referrer))
                    await self.db.sqlite_conn.commit()
                except Exception:
                    await self.db.sqlite_conn.rollback()
                    raise

        return True, valid_referrer

    async def set_banned(self, user_id: int, is_banned: bool) -> None:
        """Foydalanuvchini ban/unban qilish."""
        await self.execute(
            "UPDATE users SET is_banned = ? WHERE user_id = ?",
            1 if is_banned else 0,
            user_id,
        )

    async def add_points(self, user_id: int, amount: int) -> None:
        await self.execute("UPDATE users SET points = points + ? WHERE user_id = ?", amount, user_id)

    async def get_referral_count(self, user_id: int) -> int:
        row = await self.fetchrow(
            "SELECT COUNT(*) as count FROM users WHERE referrer_id = ? AND registered = 1 AND is_banned = 0",
            user_id,
        )
        return row["count"] if row else 0

    async def get_leaderboard(self, limit: int) -> List[Dict[str, Any]]:
        return await self.fetch(
            """
            SELECT user_id, full_name, points
            FROM users
            WHERE registered = 1 AND is_banned = 0
            ORDER BY points DESC
            LIMIT ?
            """,
            limit,
        )

    async def get_winners(self, limit: int) -> List[Dict[str, Any]]:
        return await self.fetch(
            """
            SELECT user_id, full_name, username, phone, points
            FROM users
            WHERE registered = 1 AND is_banned = 0
            ORDER BY points DESC
            LIMIT ?
            """,
            limit,
        )

    async def get_winners_ids(self, limit: int) -> List[int]:
        rows = await self.fetch(
            """
            SELECT user_id FROM users
            WHERE registered = 1 AND is_banned = 0
            ORDER BY points DESC
            LIMIT ?
            """,
            limit,
        )
        return [r["user_id"] for r in rows]

    async def get_user_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Combined query to get user details, referral count, and rank in a single DB roundtrip.
        """
        sql = """
            SELECT
                u.points,
                u.registered,
                (SELECT COUNT(*) FROM users r WHERE r.referrer_id = u.user_id AND r.registered = 1 AND r.is_banned = 0) as referral_count,
                (SELECT rank FROM (
                    SELECT user_id, RANK() OVER (ORDER BY points DESC) AS rank
                    FROM users
                    WHERE registered = 1 AND is_banned = 0
                ) sub WHERE sub.user_id = u.user_id) as rank
            FROM users u
            WHERE u.user_id = ?
        """
        return await self.fetchrow(sql, user_id)

    async def get_user_rank(self, user_id: int) -> Optional[int]:
        sql = """
            SELECT rank FROM (
                SELECT user_id, RANK() OVER (ORDER BY points DESC) AS rank
                FROM users
                WHERE registered = 1 AND is_banned = 0
            ) sub
            WHERE user_id = ?
        """
        row = await self.fetchrow(sql, user_id)
        return row["rank"] if row else None

    async def get_total_count(self) -> int:
        row = await self.fetchrow("SELECT COUNT(*) as count FROM users WHERE registered = 1")
        return row["count"] if row else 0

    async def get_today_count(self) -> int:
        if self.db.is_postgres:
            row = await self.fetchrow(
                "SELECT COUNT(*) as count FROM users WHERE registered = 1 AND joined_at >= CURRENT_DATE"
            )
        else:
            row = await self.fetchrow(
                "SELECT COUNT(*) as count FROM users WHERE registered = 1 AND date(joined_at) = date('now')"
            )
        return row["count"] if row else 0

    async def get_banned_count(self) -> int:
        row = await self.fetchrow("SELECT COUNT(*) as count FROM users WHERE is_banned = 1")
        return row["count"] if row else 0

    async def get_all_registered_ids(self) -> List[int]:
        rows = await self.fetch("SELECT user_id FROM users WHERE registered = 1")
        return [r["user_id"] for r in rows]

    async def get_all_users_data(self) -> List[Dict[str, Any]]:
        return await self.fetch("SELECT * FROM users ORDER BY points DESC")

    async def get_daily_registration_growth(self) -> List[Tuple[str, int]]:
        """
        Oxirgi 14 kunlik kunlik ro'yxatdan o'tish o'sishini qaytaradi.

        FIX: Subquery ishlatiladi — eng eski 14 kun emas, oxirgi 14 kun olinadi.
        """
        if self.db.is_postgres:
            sql = """
                SELECT day, count FROM (
                    SELECT TO_CHAR(joined_at, 'YYYY-MM-DD') as day, COUNT(*) as count
                    FROM users
                    WHERE registered = 1 AND joined_at >= NOW() - INTERVAL '14 days'
                    GROUP BY day ORDER BY day DESC LIMIT 14
                ) sub ORDER BY day ASC
            """
        else:
            sql = """
                SELECT day, count FROM (
                    SELECT date(joined_at) as day, COUNT(*) as count
                    FROM users
                    WHERE registered = 1 AND joined_at >= datetime('now', '-14 days')
                    GROUP BY day ORDER BY day DESC LIMIT 14
                ) sub ORDER BY day ASC
            """
        rows = await self.fetch(sql)
        return [(r["day"], r["count"]) for r in rows]
