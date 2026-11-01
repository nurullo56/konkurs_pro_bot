from __future__ import annotations

from aiogram import F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import config
from database import Database
from handlers.admin.router import router
from keyboards.admin import BTN_ADMIN_EDIT_RULES
from states import AdminState


def default_rules_text() -> str:
    return (
        "📋 <b>Konkurs shartlari</b>\n\n"
        "1. Barcha majburiy kanallarga a'zo bo'ling\n"
        "2. Ro'yxatdan o'ting va referral havolangizni oling\n"
        f"3. Do'stlaringizni taklif qiling — har biri uchun {config.referral_points} ball\n"
        f"4. Eng ko'p ball to'plagan TOP {config.top_n} kishi g'olib bo'ladi\n"
        f"5. Sovrin: {config.prize_text}"
    )


@router.message(Command("edit_rules"))
@router.message(F.text == BTN_ADMIN_EDIT_RULES)
async def edit_rules_start(message: Message, state: FSMContext, db: Database) -> None:
    current_rules = await db.settings.get("rules_text", default_rules_text())
    await state.set_state(AdminState.waiting_rules_text)
    await message.answer(
        f"📝 <b>Hozirgi shartlar matni:</b>\n\n{current_rules}\n\n"
        "✏️ <b>Yangi shartlar matnini yuboring:</b>\n"
        "(Matnda HTML formatidan foydalanishingiz mumkin)"
    )


@router.message(AdminState.waiting_rules_text)
async def process_edit_rules(message: Message, db: Database, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Iltimos, matn shaklida yuboring.")
        return

    await db.settings.set("rules_text", message.text)
    await state.clear()
    await message.answer("✅ Konkurs shartlari matni muvaffaqiyatli yangilandi!")
