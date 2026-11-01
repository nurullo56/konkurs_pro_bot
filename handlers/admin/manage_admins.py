from __future__ import annotations

from aiogram import Bot, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import config
from database import Database
from handlers.admin.router import router
from keyboards.admin import (
    BTN_ADMIN_ADD_ADMIN,
    BTN_ADMIN_BACK,
    BTN_ADMIN_LIST_ADMINS,
    BTN_ADMIN_MANAGEMENT,
    BTN_ADMIN_REMOVE_ADMIN,
    admins_menu_kb,
)
from states import AdminState


async def _get_admins_list_text(db: Database) -> str:
    """Barcha (.env va baza) adminlari ro'yxatini matn ko'rinishida shakllantiradi."""
    lines: list[str] = []

    # 1. Asosiy (.env) adminlar
    lines.append("👑 <b>Asosiy (.env) adminlar:</b>")
    for admin_id in config.admin_ids:
        user = await db.users.get_by_id(admin_id)
        name = user["full_name"] if user else "Superadmin"
        username_part = f" (@{user['username']})" if user and user.get("username") else ""
        lines.append(f"• <b>{name}</b>{username_part} — <code>{admin_id}</code>")

    # 2. Qo'shilgan adminlar
    db_admins = await db.admins.get_all()
    dynamic_admins = [a for a in db_admins if a["user_id"] not in config.admin_ids]

    lines.append("\n👥 <b>Qo'shilgan adminlar:</b>")
    if dynamic_admins:
        for a in dynamic_admins:
            name = a["full_name"] or "Admin"
            username_part = f" (@{a['username']})" if a.get("username") else ""
            lines.append(f"• <b>{name}</b>{username_part} — <code>{a['user_id']}</code>")
    else:
        lines.append("<i>Hozircha qo'shimcha adminlar yo'q.</i>")

    return (
        "👨‍💼 <b>Adminlar boshqaruvi bo'limi</b>\n\n"
        + "\n".join(lines)
        + "\n\n<i>Kerakli amalni tanlang:</i>"
    )


@router.message(Command("admins"))
@router.message(F.text == BTN_ADMIN_MANAGEMENT)
async def show_admins_menu(message: Message, db: Database, state: FSMContext) -> None:
    """Admin boshqaruvi bo'limi va menyusini ko'rsatadi."""
    await state.clear()
    text = await _get_admins_list_text(db)
    await message.answer(text, reply_markup=admins_menu_kb())


@router.message(F.text == BTN_ADMIN_LIST_ADMINS)
async def list_admins(message: Message, db: Database, state: FSMContext) -> None:
    """Adminlar ro'yxatini yangilab ko'rsatadi."""
    await state.clear()
    text = await _get_admins_list_text(db)
    await message.answer(text, reply_markup=admins_menu_kb())


@router.message(Command("add_admin"))
@router.message(F.text == BTN_ADMIN_ADD_ADMIN)
async def add_admin_start(message: Message, state: FSMContext) -> None:
    """Yangi admin qo'shish jarayonini boshlaydi."""
    await state.set_state(AdminState.waiting_admin_add)
    await message.answer(
        "➕ <b>Yangi adminning Telegram ID sini yuboring:</b>\n\n"
        "<i>Eslatma: ID faqat raqamlardan iborat bo'lishi kerak.</i>\n"
        "Masalan: <code>123456789</code>",
        reply_markup=admins_menu_kb(),
    )


@router.message(AdminState.waiting_admin_add)
async def process_add_admin(message: Message, bot: Bot, db: Database, state: FSMContext) -> None:
    """Yangi admin ID sini tekshirib, bazaga qo'shadi."""
    if not message.text:
        await message.answer("Iltimos, matn shaklida yuboring.", reply_markup=admins_menu_kb())
        return

    if message.text == BTN_ADMIN_BACK:
        await state.clear()
        await show_admins_menu(message, db, state)
        return

    raw_text = message.text.strip()
    if not raw_text.isdigit():
        await message.answer(
            "❌ Noto'g'ri ID! Telegram ID faqat raqamlardan iborat bo'lishi kerak.\n"
            "Qaytadan yuboring yoki '⬅️ Orqaga' tugmasini bosing:",
            reply_markup=admins_menu_kb(),
        )
        return

    target_id = int(raw_text)

    # Allaqachon adminmi?
    if target_id in config.admin_ids or await db.admins.is_admin(target_id):
        await state.clear()
        await message.answer(
            f"ℹ️ Foydalanuvchi (ID: <code>{target_id}</code>) allaqachon adminlar ro'yxatida mavjud.",
            reply_markup=admins_menu_kb(),
        )
        return

    # Foydalanuvchi ma'lumotlarini olishga urinish
    username: str | None = None
    full_name: str | None = None

    user_row = await db.users.get_by_id(target_id)
    if user_row:
        username = user_row.get("username")
        full_name = user_row.get("full_name")

    if not full_name:
        try:
            chat = await bot.get_chat(target_id)
            full_name = chat.full_name or chat.title
            username = chat.username
        except Exception:
            full_name = f"Admin {target_id}"

    await db.admins.add(target_id, username, full_name)
    await state.clear()

    username_str = f" (@{username})" if username else ""
    await message.answer(
        f"✅ <b>Admin muvaffaqiyatli qo'shildi!</b>\n\n"
        f"👤 Nomi: <b>{full_name}</b>{username_str}\n"
        f"🆔 ID: <code>{target_id}</code>",
        reply_markup=admins_menu_kb(),
    )


@router.message(Command("remove_admin"))
@router.message(F.text == BTN_ADMIN_REMOVE_ADMIN)
async def remove_admin_start(message: Message, state: FSMContext) -> None:
    """Adminni o'chirish jarayonini boshlaydi."""
    await state.set_state(AdminState.waiting_admin_remove)
    await message.answer(
        "➖ <b>O'chirmoqchi bo'lgan adminning Telegram ID sini yuboring:</b>\n\n"
        "Masalan: <code>123456789</code>",
        reply_markup=admins_menu_kb(),
    )


@router.message(AdminState.waiting_admin_remove)
async def process_remove_admin(message: Message, db: Database, state: FSMContext) -> None:
    """Adminni ro'yxatdan o'chiradi."""
    if not message.text:
        await message.answer("Iltimos, ID raqamini yuboring.", reply_markup=admins_menu_kb())
        return

    if message.text == BTN_ADMIN_BACK:
        await state.clear()
        await show_admins_menu(message, db, state)
        return

    raw_text = message.text.strip()
    if not raw_text.isdigit():
        await message.answer(
            "❌ Noto'g'ri ID! Telegram ID faqat raqamlardan iborat bo'lishi kerak.\n"
            "Qaytadan yuboring yoki '⬅️ Orqaga' tugmasini bosing:",
            reply_markup=admins_menu_kb(),
        )
        return

    target_id = int(raw_text)

    # Asosiy adminni o'chirishdan himoya
    if target_id in config.admin_ids:
        await state.clear()
        await message.answer(
            "⚠️ <b>Bu foydalanuvchi asosiy (.env) admin!</b>\n"
            "Tizim xavfsizligi uchun asosiy adminni bot orqali o'chirib bo'lmaydi.",
            reply_markup=admins_menu_kb(),
        )
        return

    removed = await db.admins.remove(target_id)
    await state.clear()
    if removed:
        await message.answer(
            f"✅ Admin (ID: <code>{target_id}</code>) muvaffaqiyatli o'chirildi.",
            reply_markup=admins_menu_kb(),
        )
    else:
        await message.answer(
            f"❌ ID: <code>{target_id}</code> bo'lgan admin qo'shilganlar ro'yxatida topilmadi.",
            reply_markup=admins_menu_kb(),
        )
