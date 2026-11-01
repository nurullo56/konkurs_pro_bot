"""
test_services.py — Services qatlamidagi testlar.

Testlar qamrovi:
  - referral.complete_registration() — yangi va takroriy ro'yxat
  - leaderboard.format_leaderboard() — matn formatlash
  - leaderboard.format_user_stats() — foydalanuvchi statistikasi
  - AntiFloodMiddleware — rate limiting (in-memory rejim)
"""
from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from database import Database
from middlewares.antiflood import AntiFloodMiddleware
from services import referral_service as referral
from services.leaderboard_service import format_leaderboard, format_user_stats
from tests.conftest import SAMPLE_REFERRER, SAMPLE_USER


# ─── Referral Service ─────────────────────────────────────────────────────────

class TestReferralService:
    """services/referral.py uchun testlar."""

    async def test_complete_registration_new_user(self, db: Database):
        """Yangi foydalanuvchi ro'yxatidan to'g'ri natija qaytishi kerak."""
        result = await referral.complete_registration(
            db.users,
            user_id=SAMPLE_USER["user_id"],
            full_name=SAMPLE_USER["full_name"],
            username=SAMPLE_USER["username"],
            phone=SAMPLE_USER["phone"],
            referrer_id=None,
            start_points=5,
            referral_points=1,
        )

        assert result.is_new is True
        assert result.points == 5
        assert result.referrer_id is None

    async def test_complete_registration_with_valid_referrer(self, db: Database):
        """Referrer bilan ro'yxat — referrer_id to'g'ri qaytishi kerak."""
        # Avval referrerni ro'yxatdan o'tkazamiz
        await referral.complete_registration(
            db.users,
            user_id=SAMPLE_REFERRER["user_id"],
            full_name=SAMPLE_REFERRER["full_name"],
            username=None,
            phone=SAMPLE_REFERRER["phone"],
            referrer_id=None,
            start_points=5,
            referral_points=1,
        )

        result = await referral.complete_registration(
            db.users,
            user_id=SAMPLE_USER["user_id"],
            full_name=SAMPLE_USER["full_name"],
            username=None,
            phone=SAMPLE_USER["phone"],
            referrer_id=SAMPLE_REFERRER["user_id"],
            start_points=5,
            referral_points=1,
        )

        assert result.is_new is True
        assert result.referrer_id == SAMPLE_REFERRER["user_id"]

    async def test_complete_registration_existing_user(self, db: Database):
        """Mavjud foydalanuvchi uchun is_new=False qaytishi kerak."""
        kwargs = dict(
            user_id=SAMPLE_USER["user_id"],
            full_name=SAMPLE_USER["full_name"],
            username=None,
            phone=SAMPLE_USER["phone"],
            referrer_id=None,
            start_points=5,
            referral_points=1,
        )
        await referral.complete_registration(db.users, **kwargs)
        result = await referral.complete_registration(db.users, **kwargs)

        assert result.is_new is False
        assert result.referrer_id is None
        assert result.points == 5  # DB dagi hozirgi qiymati


# ─── Leaderboard Service ──────────────────────────────────────────────────────

class TestLeaderboardService:
    """services/leaderboard.py uchun testlar."""

    async def _register(self, db: Database, uid: int, name: str, pts: int):
        await db.users.register_and_credit_referrer(
            user_id=uid, full_name=name, username=None,
            phone=f"+9989{uid}", referrer_id=None,
            start_points=pts, referral_points=1,
        )

    async def test_format_leaderboard_empty(self, db: Database):
        """Bo'sh leaderboard uchun to'g'ri xabar qaytishi kerak."""
        text = await format_leaderboard(db.users, limit=10)
        assert "yo'q" in text.lower()

    async def test_format_leaderboard_with_users(self, db: Database):
        """Leaderboard matnida medal emoji va ismlar bo'lishi kerak."""
        await self._register(db, 111, "Aziz", 50)
        await self._register(db, 222, "Bobur", 30)
        await self._register(db, 333, "Jasur", 80)

        text = await format_leaderboard(db.users, limit=10)

        assert "🥇" in text  # birinchi o'rin
        assert "🥈" in text  # ikkinchi o'rin
        assert "🥉" in text  # uchinchi o'rin
        assert "Jasur" in text
        assert "Aziz" in text

    async def test_format_leaderboard_order(self, db: Database):
        """Leaderboard matnida birinchi qator eng yuqori ballga ega bo'lishi kerak."""
        await self._register(db, 111, "Aziz", 50)
        await self._register(db, 222, "Champion", 200)

        text = await format_leaderboard(db.users, limit=10)
        lines = text.strip().split("\n")

        assert "Champion" in lines[0]  # birinchi qatorda champion bo'lishi kerak

    async def test_format_user_stats_not_registered(self, db: Database):
        """Ro'yxatdan o'tmagan user uchun ko'rsatma xabar qaytishi kerak."""
        text = await format_user_stats(db.users, user_id=99999)
        assert "/start" in text or "o'tmagansiz" in text.lower()

    async def test_format_user_stats_registered(self, db: Database):
        """Ro'yxatdan o'tgan user uchun ballar va o'rin ko'rsatilishi kerak."""
        await self._register(db, SAMPLE_USER["user_id"], SAMPLE_USER["full_name"], 25)

        text = await format_user_stats(db.users, user_id=SAMPLE_USER["user_id"])

        assert "25" in text    # ball soni
        assert "1" in text     # 1-o'rin (yagona ishtirokchi)


# ─── AntiFlood Middleware ─────────────────────────────────────────────────────

class TestAntiFloodMiddleware:
    """middlewares/antiflood.py uchun testlar (in-memory rejim)."""

    def _make_message_event(self, user_id: int) -> MagicMock:
        """Fake Message event yaratadi."""
        from aiogram.types import Message
        msg = MagicMock(spec=Message)
        msg.from_user = MagicMock()
        msg.from_user.id = user_id
        msg.answer = AsyncMock()
        return msg

    def _make_callback_event(self, user_id: int) -> MagicMock:
        """Fake CallbackQuery event yaratadi."""
        from aiogram.types import CallbackQuery
        cb = MagicMock(spec=CallbackQuery)
        cb.from_user = MagicMock()
        cb.from_user.id = user_id
        cb.answer = AsyncMock()
        return cb

    async def test_first_message_passes(self):
        """Birinchi xabar to'siqsiz o'tishi kerak."""
        middleware = AntiFloodMiddleware(rate_limit=1.0, redis_client=None)
        handler = AsyncMock(return_value="ok")
        event = self._make_message_event(user_id=12345)

        result = await middleware(handler, event, {})

        assert result == "ok"
        handler.assert_called_once()

    async def test_rapid_messages_blocked(self):
        """Tezkor ikkinchi xabar bloklanishi kerak."""
        middleware = AntiFloodMiddleware(rate_limit=2.0, redis_client=None)
        handler = AsyncMock(return_value="ok")
        event = self._make_message_event(user_id=12345)

        # Birinchi xabar — o'tadi
        await middleware(handler, event, {})
        # Ikkinchi xabar — bloklanadi
        result = await middleware(handler, event, {})

        assert result is None  # bloklanganida None qaytadi
        assert handler.call_count == 1  # faqat birinchi marta chaqirildi
        event.answer.assert_called_once()  # ogohlantirish xabari yuborildi

    async def test_after_rate_limit_passes_again(self):
        """Rate limit vaqtidan keyin xabar yana o'tishi kerak."""
        middleware = AntiFloodMiddleware(rate_limit=0.05, redis_client=None)
        handler = AsyncMock(return_value="ok")
        event = self._make_message_event(user_id=99999)

        # Birinchi xabar
        await middleware(handler, event, {})
        # 0.1 soniya kutish (rate limit 0.05s)
        await asyncio.sleep(0.1)
        # Ikkinchi xabar — endi o'tishi kerak
        result = await middleware(handler, event, {})

        assert result == "ok"
        assert handler.call_count == 2

    async def test_different_users_independent(self):
        """Turli foydalanuvchilar bir-birini bloklamasligi kerak."""
        middleware = AntiFloodMiddleware(rate_limit=2.0, redis_client=None)
        handler = AsyncMock(return_value="ok")

        event_user1 = self._make_message_event(user_id=111)
        event_user2 = self._make_message_event(user_id=222)

        # Ikkala foydalanuvchi birinchi marta yuboryapti — ikkalasi ham o'tishi kerak
        result1 = await middleware(handler, event_user1, {})
        result2 = await middleware(handler, event_user2, {})

        assert result1 == "ok"
        assert result2 == "ok"
        assert handler.call_count == 2

    async def test_callback_blocked(self):
        """Tez bosilgan callback ham bloklanishi kerak."""
        middleware = AntiFloodMiddleware(rate_limit=2.0, redis_client=None)
        handler = AsyncMock(return_value="ok")
        event = self._make_callback_event(user_id=55555)

        await middleware(handler, event, {})
        result = await middleware(handler, event, {})

        assert result is None
        event.answer.assert_called_once()

    async def test_no_user_event_passes_through(self):
        """from_user yo'q bo'lgan event to'g'ridan-to'g'ri o'tishi kerak."""
        middleware = AntiFloodMiddleware(rate_limit=1.0, redis_client=None)
        handler = AsyncMock(return_value="ok")
        event = MagicMock()  # spec yo'q — from_user attributi yo'q

        result = await middleware(handler, event, {})

        assert result == "ok"

    async def test_cache_cleanup_triggered(self):
        """10000 dan oshganda cache tozalanishi kerak."""
        middleware = AntiFloodMiddleware(rate_limit=0.01, redis_client=None)
        handler = AsyncMock(return_value="ok")

        # Cache ni 10001 ta yozuv bilan to'ldiramiz
        old_time = time.time() - 120  # 2 daqiqa oldin
        for i in range(10001):
            middleware.cache[i] = old_time

        # Yangi xabar yuborish — cleanup ni trigger qilishi kerak
        event = self._make_message_event(user_id=99998)
        await middleware(handler, event, {})

        # Eski yozuvlar o'chirilgan bo'lishi kerak (60 soniyadan eski)
        assert len(middleware.cache) < 10001
