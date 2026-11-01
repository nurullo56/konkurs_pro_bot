from __future__ import annotations

from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

BTN_ADMIN_STATS = "📊 Statistika & Analitika"
BTN_ADMIN_CHARTS = "📈 Statistika Grafigi"
BTN_ADMIN_EXCEL = "📥 Excel (Foydalanuvchilar)"
BTN_ADMIN_WINNERS = "🏆 G'oliblar ro'yxati"
BTN_ADMIN_BROADCAST = "📢 Xabar tarqatish"
BTN_ADMIN_CHANNEL_MGMT = "📢 Kanal boshqaruvi"
BTN_ADMIN_MANAGEMENT = "👨‍💼 Admin boshqaruvi"
BTN_ADMIN_CHANNELS = "📋 Kanallar ro'yxati"
BTN_ADMIN_ADD_CHANNEL = "➕ Kanal qo'shish"
BTN_ADMIN_REMOVE_CHANNEL = "➖ Kanalni o'chirish"
BTN_ADMIN_ADD_ADMIN = "➕ Admin qo'shish"
BTN_ADMIN_REMOVE_ADMIN = "➖ Adminni o'chirish"
BTN_ADMIN_LIST_ADMINS = "📋 Adminlar ro'yxati"
BTN_ADMIN_BACK = "⬅️ Orqaga"
BTN_ADMIN_PREMIUM_EMOJI = "👑 Premium Emojilar"
BTN_ADMIN_EDIT_RULES = "📝 Shartlarni tahrirlash"
BTN_ADMIN_EDIT_PRIZES = "🎁 Sovg'alarni tahrirlash"
BTN_ADMIN_EXIT = "⬅️ Asosiy menyuga qaytish"


def admin_menu_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=BTN_ADMIN_STATS)
    builder.button(text=BTN_ADMIN_CHARTS)
    builder.button(text=BTN_ADMIN_EXCEL)
    builder.button(text=BTN_ADMIN_WINNERS)
    builder.button(text=BTN_ADMIN_BROADCAST)
    builder.button(text=BTN_ADMIN_CHANNEL_MGMT)
    builder.button(text=BTN_ADMIN_MANAGEMENT)
    builder.button(text=BTN_ADMIN_PREMIUM_EMOJI)
    builder.button(text=BTN_ADMIN_EDIT_RULES)
    builder.button(text=BTN_ADMIN_EDIT_PRIZES)
    builder.button(text=BTN_ADMIN_EXIT)
    builder.adjust(2, 2, 2, 2, 2, 1)
    return builder.as_markup(resize_keyboard=True)


def channels_menu_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=BTN_ADMIN_ADD_CHANNEL)
    builder.button(text=BTN_ADMIN_REMOVE_CHANNEL)
    builder.button(text=BTN_ADMIN_CHANNELS)
    builder.button(text=BTN_ADMIN_BACK)
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True)


def admins_menu_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=BTN_ADMIN_ADD_ADMIN)
    builder.button(text=BTN_ADMIN_REMOVE_ADMIN)
    builder.button(text=BTN_ADMIN_LIST_ADMINS)
    builder.button(text=BTN_ADMIN_BACK)
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True)
