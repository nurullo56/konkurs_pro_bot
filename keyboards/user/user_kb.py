from __future__ import annotations

from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

BTN_PARTICIPATE = "Konkursda qatnashish 🔴"
BTN_PRIZES = "🎁 Sovg'alar"
BTN_POINTS = "👤 Ballarim"
BTN_LEADERBOARD = "📊 Reyting"
BTN_RULES = "💡 Shartlar"
BTN_ADMIN = "👨‍💻 Admin panel"


def contact_request_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="📱 Raqamni yuborish", request_contact=True)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def main_menu_kb(is_admin: bool = False) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=BTN_PARTICIPATE)
    builder.button(text=BTN_PRIZES)
    builder.button(text=BTN_POINTS)
    builder.button(text=BTN_LEADERBOARD)
    builder.button(text=BTN_RULES)
    if is_admin:
        builder.button(text=BTN_ADMIN)
        builder.adjust(1, 2, 2, 1)
    else:
        builder.adjust(1, 2, 2)
    return builder.as_markup(resize_keyboard=True)
