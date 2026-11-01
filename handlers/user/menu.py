from __future__ import annotations

from aiogram import Bot, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import config
from database import Database
from handlers.admin.manage_prizes import default_prizes_text
from handlers.admin.manage_rules import default_rules_text
from handlers.user.registration import _referral_link, begin_registration
from handlers.user.router import router
from keyboards.user import (
    BTN_LEADERBOARD,
    BTN_PARTICIPATE,
    BTN_POINTS,
    BTN_PRIZES,
    BTN_RULES,
)
from services.leaderboard_service import format_leaderboard, format_user_stats


# ✅ FIX #6: Xabar muallifining ID sini xavfsiz olish
def _get_user_id(message: Message) -> int | None:
    """
    Xabar muallifining Telegram ID sini qaytaradi.
    Guruh/kanalda ham to'g'ri ishlaydi (chat.id emas, from_user.id).
    """
    return message.from_user.id if message.from_user else None


@router.message(F.text == BTN_PARTICIPATE)
async def participate(message: Message, bot: Bot, db: Database, state: FSMContext, bot_username: str) -> None:
    """Ishtirok etish tugmasini bosganda chaqiriladi."""
    user_id = _get_user_id(message)
    if user_id is None:
        return

    # ✅ FIX #6: message.chat.id → user_id
    user = await db.users.get_by_id(user_id)
    if user and user["registered"]:
        link = _referral_link(bot_username, user_id)
        await message.answer(
            f"✅ Siz allaqachon ishtirokchisiz!\n🏆 Sovrin: {config.prize_text}\n\n"
            f"🔗 Referral havolangiz:\n{link}"
        )
        return
    await begin_registration(message, bot, db, state, None)


@router.message(F.text == BTN_PRIZES)
async def prizes(message: Message, db: Database) -> None:
    """Sovrinlar ma'lumotlarini ko'rsatadi."""
    photo_id = await db.settings.get("prizes_photo", "")
    prizes_text = await db.settings.get("prizes_text", default_prizes_text())
    if photo_id:
        await message.answer_photo(photo=photo_id, caption=prizes_text)
    else:
        await message.answer(prizes_text)


@router.message(F.text == BTN_POINTS)
async def my_points(message: Message, db: Database, bot_username: str) -> None:
    """Foydalanuvchi ballarini va referral havolasini ko'rsatadi."""
    user_id = _get_user_id(message)
    if user_id is None:
        return

    # ✅ FIX #6: message.chat.id → user_id (ikki joyda)
    text = await format_user_stats(db.users, user_id)
    link = _referral_link(bot_username, user_id)
    await message.answer(f"{text}\n\n🔗 Referral havolangiz:\n{link}")


@router.message(F.text == BTN_LEADERBOARD)
async def show_leaderboard(message: Message, db: Database) -> None:
    """Peshqadamlar jadvalini ko'rsatadi."""
    text = await format_leaderboard(db.users, config.top_n)
    await message.answer(f"🏆 <b>Top {config.top_n}</b>\n\n{text}")


@router.message(F.text == BTN_RULES)
async def rules(message: Message, db: Database) -> None:
    """Konkurs qoidalarini ko'rsatadi."""
    rules_text = await db.settings.get("rules_text", default_rules_text())
    await message.answer(rules_text)


@router.message(Command("bot"))
async def about_bot_developer(message: Message) -> None:
    """Sizga ham shunday bot kerakmi? /bot buyrug'i handleri."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    text = (
        "🤖 <b>Sizga ham shunday sifatli va kuchli Telegram bot kerakmi?</b>\n\n"
        "Biz sizning biznesingiz, kanalingiz yoki shaxsiy loyihangiz uchun istalgan "
        "murakkablikdagi botlarni professional darajada tayyorlab beramiz!\n\n"
        "✨ <b>Bizning imkoniyatlarimiz:</b>\n"
        "• 🎯 Konkurs va referral (taklif) tizimlari\n"
        "• 🛒 Internet-do'kon va katalog botlari\n"
        "• 💳 To'lov tizimlari (Click, Payme, Uzum va h.k.) integratsiyasi\n"
        "• 📊 Statistika, CRM va avtomatlashtirish tizimlari\n"
        "• ⚡️ Yuqori tezlik, 24/7 uzluksiz ishlash va xavfsizlik\n\n"
        "💡 <i>G'oyangizni qisqa muddatda va professional darajada hayotga tatbiq etamiz!</i>\n\n"
        "👨‍💻 <b>Bog'lanish:</b> @Nurulloh_codes"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Bog'lanish (@Nurulloh_codes)",
                    url="https://t.me/Nurulloh_codes",
                )
            ]
        ]
    )
    await message.answer(text, reply_markup=kb)