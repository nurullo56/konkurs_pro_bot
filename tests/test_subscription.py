"""
test_subscription.py — Kanal obunasini tekshirish (services/subscription.py) testlari.

Testlar qamrovi:
  - Obuna bo'lgan user to'g'ri aniqlanishi
  - Obuna bo'lmagan user to'g'ri aniqlanishi
  - Bot kanalga kirish imkoni bo'lmaganda xato ushlanishi
  - Join request orqali obuna (private kanal)
  - Bir nechta kanalda parallel tekshiruv
"""
from __future__ import annotations

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.enums import ChatMemberStatus

from database import Database
from services.subscription_service import get_unsubscribed


def _channel(chat_id: str, title: str = "Test Kanal") -> Dict[str, Any]:
    return {"chat_id": chat_id, "title": title, "invite_link": None}


def _mock_member(status: ChatMemberStatus) -> MagicMock:
    member = MagicMock()
    member.status = status
    return member


class TestSubscriptionCheck:

    async def test_subscribed_user_not_in_missing(self, mock_bot: AsyncMock):
        """Obuna bo'lgan foydalanuvchi 'missing' ro'yxatida bo'lmasligi kerak."""
        mock_bot.get_chat_member.return_value = _mock_member(ChatMemberStatus.MEMBER)
        channels = [_channel("@test_ch")]

        missing = await get_unsubscribed(mock_bot, channels, user_id=12345)

        assert missing == []

    async def test_unsubscribed_user_in_missing(self, mock_bot: AsyncMock):
        """Obuna bo'lmagan foydalanuvchi 'missing' ro'yxatida bo'lishi kerak."""
        mock_bot.get_chat_member.return_value = _mock_member(ChatMemberStatus.LEFT)
        channels = [_channel("@test_ch")]

        missing = await get_unsubscribed(mock_bot, channels, user_id=12345)

        assert len(missing) == 1
        assert missing[0]["chat_id"] == "@test_ch"

    async def test_admin_considered_subscribed(self, mock_bot: AsyncMock):
        """Admin ham obuna hisoblashi kerak."""
        mock_bot.get_chat_member.return_value = _mock_member(ChatMemberStatus.ADMINISTRATOR)
        channels = [_channel("@test_ch")]

        missing = await get_unsubscribed(mock_bot, channels, user_id=12345)

        assert missing == []

    async def test_creator_considered_subscribed(self, mock_bot: AsyncMock):
        """Kanal egasi ham obuna hisoblashi kerak."""
        mock_bot.get_chat_member.return_value = _mock_member(ChatMemberStatus.CREATOR)
        channels = [_channel("@test_ch")]

        missing = await get_unsubscribed(mock_bot, channels, user_id=12345)

        assert missing == []

    async def test_empty_channels_list(self, mock_bot: AsyncMock):
        """Kanal ro'yxati bo'sh bo'lsa, bo'sh natija qaytishi kerak."""
        missing = await get_unsubscribed(mock_bot, channels=[], user_id=12345)

        assert missing == []
        mock_bot.get_chat_member.assert_not_called()

    async def test_api_error_treated_as_not_subscribed(self, mock_bot: AsyncMock):
        """API xatosi bo'lganda foydalanuvchi obuna emas deb hisoblanishi kerak."""
        mock_bot.get_chat_member.side_effect = Exception("Forbidden: bot not in channel")
        channels = [_channel("@private_ch")]

        missing = await get_unsubscribed(mock_bot, channels, user_id=12345)

        assert len(missing) == 1  # xato = obuna emas

    async def test_join_request_counts_as_subscribed(self, mock_bot: AsyncMock, db: Database):
        """
        Join request bo'lgan foydalanuvchi
        (private kanal uchun) obuna hisoblashi kerak.
        """
        # Bot check_member da KICKED qaytaradi (ya'ni obuna emas)
        mock_bot.get_chat_member.return_value = _mock_member(ChatMemberStatus.KICKED)

        # Lekin join request bor
        await db.join_requests.add(user_id=12345, chat_id="@private_ch")
        channels = [_channel("@private_ch")]

        missing = await get_unsubscribed(mock_bot, channels, user_id=12345, db=db)

        assert missing == []  # join request tufayli obuna hisoblanadi

    async def test_multiple_channels_partial_subscription(self, mock_bot: AsyncMock):
        """
        Bir nechta kanaldan faqat bir qismiga obuna bo'lsa,
        faqat o'sha kanallar 'missing' da bo'lishi kerak.
        """
        def side_effect(chat_id, user_id):
            if chat_id == "@ch1":
                return _mock_member(ChatMemberStatus.MEMBER)
            elif chat_id == "@ch2":
                return _mock_member(ChatMemberStatus.LEFT)
            return _mock_member(ChatMemberStatus.LEFT)

        mock_bot.get_chat_member.side_effect = side_effect

        channels = [_channel("@ch1"), _channel("@ch2"), _channel("@ch3")]
        missing = await get_unsubscribed(mock_bot, channels, user_id=12345)

        missing_ids = [ch["chat_id"] for ch in missing]
        assert "@ch1" not in missing_ids  # obuna bor
        assert "@ch2" in missing_ids       # obuna yo'q
        assert "@ch3" in missing_ids       # obuna yo'q

    async def test_integer_chat_id_normalized(self, mock_bot: AsyncMock):
        """Raqamli chat_id to'g'ri int ga konvertatsiya qilinishi kerak."""
        mock_bot.get_chat_member.return_value = _mock_member(ChatMemberStatus.MEMBER)
        channels = [_channel("-1001234567890")]

        await get_unsubscribed(mock_bot, channels, user_id=12345)

        # get_chat_member int bilan chaqirilishi kerak, string emas
        call_args = mock_bot.get_chat_member.call_args[0]
        assert call_args[0] == -1001234567890  # int!
