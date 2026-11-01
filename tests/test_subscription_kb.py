"""test_subscription_kb.py — channels_kb() testlari."""
from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup

from keyboards.user.subscription_kb import channels_kb, _resolve_channel_url


class TestResolveChannelUrl:
    def test_invite_link_priority(self):
        assert _resolve_channel_url("@test_ch", "https://t.me/+abc") == "https://t.me/+abc"

    def test_username_without_invite_link(self):
        assert _resolve_channel_url("@my_channel", None) == "https://t.me/my_channel"

    def test_numeric_chat_id_fallback(self):
        result = _resolve_channel_url("-1001234567890", None)
        assert result.startswith("https://t.me/")


class TestChannelsKb:
    def test_returns_inline_keyboard(self):
        kb = channels_kb([{"chat_id": "@ch1", "title": "Kanal 1", "invite_link": None}])
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_empty_only_check_button(self):
        kb = channels_kb([])
        assert len(kb.inline_keyboard) == 1
        assert kb.inline_keyboard[0][0].text == "✅ A'zo bo'ldim"

    def test_one_channel_two_buttons(self):
        kb = channels_kb([{"chat_id": "@ch1", "title": "Kanal 1", "invite_link": None}])
        assert len(kb.inline_keyboard) == 2
        assert kb.inline_keyboard[0][0].text == "Kanal 1"
        assert kb.inline_keyboard[1][0].text == "✅ A'zo bo'ldim"

    def test_title_none_uses_chat_id(self):
        kb = channels_kb([{"chat_id": "@ch1", "title": None, "invite_link": None}])
        assert kb.inline_keyboard[0][0].text == "@ch1"

    def test_check_sub_callback_data(self):
        kb = channels_kb([{"chat_id": "@ch1", "title": "Kanal 1", "invite_link": None}])
        assert kb.inline_keyboard[-1][0].callback_data == "check_sub"
