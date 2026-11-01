from __future__ import annotations

from aiogram import F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from handlers.admin.router import router
from keyboards.admin import BTN_ADMIN_EXIT, admin_menu_kb
from keyboards.user import BTN_ADMIN, main_menu_kb


@router.message(Command("admin"))
@router.message(F.text == BTN_ADMIN)
async def admin_panel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "👨‍💻 <b>Admin paneliga xush kelibsiz!</b>\n"
        "Quyidagi menyudan kerakli bo'limni tanlang:",
        reply_markup=admin_menu_kb(),
    )


@router.message(F.text == BTN_ADMIN_EXIT)
async def exit_admin(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Asosiy menyuga qaytdingiz.", reply_markup=main_menu_kb(is_admin=True))
