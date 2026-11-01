from __future__ import annotations

from typing import Any, Dict

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.emoji_service import EMOJI_KEYS


def broadcast_type_kb() -> InlineKeyboardMarkup:
    """Xabar tarqatish maqsadini tanlash klaviaturasi."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Barchaga xabar yuborish", callback_data="bc_target:all")
    builder.button(text="🏆 G'oliblarga xabar yuborish (Top N)", callback_data="bc_target:winners")
    builder.button(text="👤 Muayyan foydalanuvchiga yuborish", callback_data="bc_target:single")
    builder.button(text="❌ Bekor qilish", callback_data="bc_target:cancel")
    builder.adjust(1)
    return builder.as_markup()


async def premium_emoji_settings_kb(db: Any) -> InlineKeyboardMarkup:
    """
    Premium emoji sozlamalari uchun inline klaviatura.

    :param db: Database obyekti (settings.get ni chaqirish uchun).
    :return: Har bir emoji uchun tugmalar bilan InlineKeyboardMarkup.
    """
    builder = InlineKeyboardBuilder()

    for key, (default_char, label) in EMOJI_KEYS.items():
        custom_id = await db.settings.get(f"emoji_{key}", "")
        status = "✨ [Premium ✅]" if custom_id else "⚪️ [Oddiy]"
        builder.button(
            text=f"{default_char} {label} {status}",
            callback_data=f"set_emoji:{key}",
        )

    builder.button(text="❌ Bekor qilish / Yopish", callback_data="set_emoji:cancel")
    builder.adjust(1)
    return builder.as_markup()
