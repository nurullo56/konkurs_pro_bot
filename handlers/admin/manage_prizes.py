from __future__ import annotations

from aiogram import F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import config
from database import Database
from handlers.admin.router import router
from keyboards.admin import BTN_ADMIN_EDIT_PRIZES
from states import AdminState


def default_prizes_text() -> str:
    return (
        f"🏆 <b>{config.contest_name}</b>\n"
        f"💰 Sovrin: {config.prize_text}\n"
        f"🥇 G'oliblar: TOP {config.top_n}"
    )


@router.message(Command("edit_prizes"))
@router.message(F.text == BTN_ADMIN_EDIT_PRIZES)
async def edit_prizes_start(message: Message, state: FSMContext, db: Database) -> None:
    current_photo = await db.settings.get("prizes_photo", "")
    current_text = await db.settings.get("prizes_text", default_prizes_text())

    await state.set_state(AdminState.waiting_prizes_media)

    prompt = (
        "🎁 <b>Yangi sovg'alar ma'lumotini yuboring:</b>\n\n"
        "Siz oddiy <b>Matn</b> yoki <b>Rasm + Matn (caption)</b> yuborishingiz mumkin.\n"
        "Matnda HTML formatidan foydalanishingiz mumkin."
    )

    if current_photo:
        await message.answer_photo(
            photo=current_photo,
            caption=f"Hozirgi sovg'alar ko'rinishi:\n\n{current_text}\n\n{prompt}",
        )
    else:
        await message.answer(f"Hozirgi sovg'alar ko'rinishi:\n\n{current_text}\n\n{prompt}")


@router.message(AdminState.waiting_prizes_media)
async def process_edit_prizes(message: Message, db: Database, state: FSMContext) -> None:
    text_content = message.caption or message.text or ""

    if message.photo:
        photo_id = message.photo[-1].file_id
        await db.settings.set("prizes_photo", photo_id)
        await db.settings.set("prizes_text", text_content)
    elif text_content:
        await db.settings.set("prizes_photo", "")
        await db.settings.set("prizes_text", text_content)
    else:
        await message.answer("Iltimos, rasm yoki matn shaklida yuboring.")
        return

    await state.clear()
    await message.answer("✅ Sovg'alar ma'lumotlari muvaffaqiyatli yangilandi!")
