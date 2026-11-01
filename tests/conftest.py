from __future__ import annotations

import logging
import os
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

# ⚠️ MUHIM: config import qilinishidan OLDIN test muhiti o'rnatiladi.
# Bu haqiqiy .env faylidan qiymatlar yuklanmasligi uchun zarur.
os.environ["BOT_TOKEN"] = "1234567890:TEST_TOKEN_FOR_PYTEST_ONLY"
os.environ["ADMIN_IDS"] = "999999999"
os.environ["DB_TYPE"] = "sqlite"
os.environ["DB_PATH"] = ":memory:"
os.environ["REDIS_URL"] = ""
os.environ["USE_WEBHOOK"] = "false"
os.environ["WEBHOOK_URL"] = ""
os.environ["WEBHOOK_SECRET"] = ""
os.environ["RATE_LIMIT"] = "1.5"
os.environ["TOP_N"] = "10"
os.environ["START_POINTS"] = "5"
os.environ["REFERRAL_POINTS"] = "1"

from config import config  # noqa: E402  (env o'rnatilgandan keyin)
from database import Database  # noqa: E402
from database.repositories import (  # noqa: E402
    ChannelRepository,
    SettingsRepository,
    UserRepository,
)


# ─── Database Fixture ────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db() -> Database:
    """Har test uchun yangi, bo'sh in-memory SQLite DB yaratadi."""
    database = Database(db_type="sqlite", path=":memory:")
    await database.connect()
    yield database
    await database.close()


# ─── Repository Fixtures ─────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def user_repo(db: Database) -> UserRepository:
    """UserRepository fixture."""
    return db.users


@pytest_asyncio.fixture
async def channel_repo(db: Database) -> ChannelRepository:
    """ChannelRepository fixture."""
    return db.channels


@pytest_asyncio.fixture
async def settings_repo(db: Database) -> SettingsRepository:
    """SettingsRepository fixture."""
    return db.settings


# ─── Mock Bot Fixture ─────────────────────────────────────────────────────────

@pytest.fixture
def mock_bot() -> AsyncMock:
    """Telegram Bot ni mock qiladi — hech qanday real API call bo'lmaydi."""
    bot = AsyncMock()
    bot.get_me.return_value = MagicMock(username="test_konkurs_bot")
    bot.send_message.return_value = MagicMock(message_id=1)
    bot.get_chat_member.return_value = MagicMock(status="member")
    return bot


# ─── Config Fixture ───────────────────────────────────────────────────────────

@pytest.fixture
def test_config():
    """
    Test uchun Config nusxasi (dataclasses.replace bilan).
    Har bir test uchun alohida konfiguratsiya kerak bo'lsa ishlatiladi.
    """
    from dataclasses import replace
    return replace(
        config,
        bot_token="1234567890:TEST_TOKEN_FOR_PYTEST_ONLY",
        admin_ids=frozenset([999999999]),
        db_type="sqlite",
        db_path=":memory:",
        redis_url=None,
        use_webhook=False,
        webhook_url="",
        webhook_secret="",
        rate_limit=1.5,
    )


# ─── Sample Data ──────────────────────────────────────────────────────────────

SAMPLE_USER = {
    "user_id": 100001,
    "full_name": "Ali Valiyev",
    "username": "ali_val",
    "phone": "+998901234567",
}

SAMPLE_REFERRER = {
    "user_id": 200002,
    "full_name": "Vali Aliyev",
    "username": "vali_ali",
    "phone": "+998907654321",
}
