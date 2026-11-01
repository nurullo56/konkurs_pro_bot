from __future__ import annotations

from typing import TypedDict

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ✅ FIX #7: To'g'ri type hint
class ChannelData(TypedDict, total=False):
    """
    Kanallar repository'sidan keladigan ma'lumot strukturasi.

    total=False — barcha maydonlar ixtiyoriy (chunki DB dan kelishi mumkin).
    Runtime'da bu oddiy dict, lekin type checker uchun aniq struktura.
    """
    id: int
    chat_id: str
    title: str | None
    invite_link: str | None
    added_at: str


def _resolve_channel_url(chat_id: str, invite_link: str | None) -> str:
    """
    Kanal uchun URL ni aniqlaydi.

    Ustuvorlik:
      1. invite_link (agar mavjud bo'lsa)
      2. @username asosida t.me/username
      3. Raqamli chat_id — fallback
    """
    if invite_link:
        return invite_link

    if chat_id.startswith("@"):
        return f"https://t.me/{chat_id.lstrip('@')}"

    if chat_id.lstrip("-").isdigit():
        # Raqamli chat_id — invite_link bo'lishi SHART edi, lekin fallback
        return f"https://t.me/{chat_id.lstrip('-')}"

    return f"https://t.me/{chat_id}"


def channels_kb(channels: list[ChannelData]) -> InlineKeyboardMarkup:
    """
    Majburiy kanallar uchun inline klaviatura yaratadi.

    :param channels: Kanal ma'lumotlari ro'yxati (dict yoki dict-like).
    :return: InlineKeyboardMarkup.
    """
    builder = InlineKeyboardBuilder()

    for channel in channels:
        chat_id = channel["chat_id"]
        title = channel.get("title") or chat_id
        url = _resolve_channel_url(chat_id, channel.get("invite_link"))
        builder.button(text=title, url=url)

    builder.button(text="✅ A'zo bo'ldim", callback_data="check_sub")
    builder.adjust(1)
    return builder.as_markup()
