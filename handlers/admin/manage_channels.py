from __future__ import annotations

from aiogram import Bot, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database import Database
from handlers.admin.router import router
from keyboards.admin import (
    BTN_ADMIN_ADD_CHANNEL,
    BTN_ADMIN_BACK,
    BTN_ADMIN_CHANNEL_MGMT,
    BTN_ADMIN_CHANNELS,
    BTN_ADMIN_REMOVE_CHANNEL,
    admin_menu_kb,
    channels_menu_kb,
)
from states import AdminState


def _normalize_chat_id(raw_id: str) -> int | str:
    cleaned = raw_id.strip()
    if cleaned.lstrip("-").isdigit():
        return int(cleaned)
    return cleaned


async def _parse_and_add_channel(text: str, message: Message, bot: Bot, db: Database) -> bool:
    parts = [p.strip() for p in text.split("|")]
    head = parts[0].split(maxsplit=1)

    if head[0].startswith("/add_channel"):
        if len(head) < 2:
            return False
        raw_chat_id = head[1].strip()
    else:
        raw_chat_id = head[0].strip()

    if not raw_chat_id:
        return False

    title = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
    invite_link = parts[2].strip() if len(parts) > 2 and parts[2].strip() else None

    target_chat_id = _normalize_chat_id(raw_chat_id)

    # 1. Kanal ma'lumotlarini va nomini avtomatik olish
    try:
        chat = await bot.get_chat(target_chat_id)
        target_chat_id_str = str(chat.id)
        if not title:
            title = chat.title or str(raw_chat_id)
    except Exception:
        target_chat_id_str = str(target_chat_id)
        if not title:
            title = str(raw_chat_id)

    # 2. Taklif (Join Request) havolasini avtomatik yaratish
    if not invite_link:
        try:
            # So'rov admin tasdiqlaydigan (Join Request) havola yaratish
            link_obj = await bot.create_chat_invite_link(
                chat_id=target_chat_id_str,
                creates_join_request=True,
                name="Konkurs Bot",
            )
            invite_link = link_obj.invite_link
        except Exception:
            try:
                # Oddiy taklif havolasi yaratish
                link_obj = await bot.create_chat_invite_link(
                    chat_id=target_chat_id_str, name="Konkurs Bot"
                )
                invite_link = link_obj.invite_link
            except Exception:
                if str(raw_chat_id).startswith("@"):
                    invite_link = f"https://t.me/{str(raw_chat_id).lstrip('@')}"

    await db.channels.add(target_chat_id_str, title, invite_link)
    await message.answer(
        f"✅ <b>Kanal muvaffaqiyatli qo'shildi!</b>\n\n"
        f"📌 Nomi: <b>{title}</b>\n"
        f"🆔 Chat ID: <code>{raw_chat_id}</code>\n"
        f"🔗 Havola: {invite_link or 'Mavjud emas'}",
        reply_markup=channels_menu_kb(),
    )
    return True


@router.message(Command("channels_menu"))
@router.message(F.text == BTN_ADMIN_CHANNEL_MGMT)
async def channel_management_menu(message: Message, db: Database, state: FSMContext) -> None:
    await state.clear()
    channels = await db.channels.get_all()
    if channels:
        lines = [f"• {c['title']} (<code>{c['chat_id']}</code>)" for c in channels]
        text = (
            "📢 <b>Kanal boshqaruvi bo'limi</b>\n\n"
            "📋 <b>Ulangan majburiy kanallar:</b>\n"
            + "\n".join(lines)
            + "\n\n<i>Kerakli amalni tanlang:</i>"
        )
    else:
        text = (
            "📢 <b>Kanal boshqaruvi bo'limi</b>\n\n"
            "📋 <i>Hozircha majburiy kanallar ulanmagan.</i>\n\n"
            "<i>Kerakli amalni tanlang:</i>"
        )
    await message.answer(text, reply_markup=channels_menu_kb())


@router.message(F.text == BTN_ADMIN_BACK)
async def back_to_admin_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "👨‍💻 <b>Admin paneliga qaytdingiz.</b>\n"
        "Quyidagi menyudan kerakli bo'limni tanlang:",
        reply_markup=admin_menu_kb(),
    )


@router.message(Command("add_channel"))
@router.message(F.text == BTN_ADMIN_ADD_CHANNEL)
async def add_channel_start(message: Message, state: FSMContext, bot: Bot, db: Database) -> None:
    if message.text and message.text != BTN_ADMIN_ADD_CHANNEL:
        if await _parse_and_add_channel(message.text, message, bot, db):
            return

    await state.set_state(AdminState.waiting_channel_info)
    await message.answer(
        "➕ <b>Qo'shmoqchi bo'lgan kanalingiz username yoki ID sini yuboring:</b>\n\n"
        "<i>Eslatma: Bot avval o'sha kanalda admin bo'lishi kerak! Bot kanal nomini va So'rovli (Join Request) taklif havolasini avtomatik yaratib oladi.</i>\n\n"
        "Masalan:\n"
        "<code>@kanal_username</code>\n"
        "yoki\n"
        "<code>-1001234567890</code>\n"
        "yoki (ixtiyoriy nom berish bilan):\n"
        "<code>@kanal_username | Mening Kanalim</code>",
        reply_markup=channels_menu_kb(),
    )


@router.message(AdminState.waiting_channel_info)
async def process_add_channel(message: Message, bot: Bot, db: Database, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Iltimos, matn shaklida yuboring.")
        return

    if message.text == BTN_ADMIN_BACK:
        await state.clear()
        await channel_management_menu(message, db, state)
        return

    success = await _parse_and_add_channel(message.text, message, bot, db)
    if success:
        await state.clear()
    else:
        await message.answer(
            "❌ Noto'g'ri format yoki bot kanalda admin emas. Qaytadan yuboring:\n"
            "<code>@kanal_username</code>",
            reply_markup=channels_menu_kb(),
        )


@router.message(Command("remove_channel"))
@router.message(F.text == BTN_ADMIN_REMOVE_CHANNEL)
async def remove_channel_start(message: Message, state: FSMContext, db: Database) -> None:
    args = (message.text or "").split(maxsplit=1)
    if len(args) == 2 and args[0].startswith("/remove_channel"):
        removed = await db.channels.remove(args[1].strip())
        await message.answer(
            "✅ O'chirildi." if removed else "❌ Bunday kanal topilmadi.",
            reply_markup=channels_menu_kb(),
        )
        return

    await state.set_state(AdminState.waiting_channel_remove)
    await message.answer(
        "➖ O'chirmoqchi bo'lgan kanal ID si yoki username'ini yuboring:\n"
        "(Masalan: <code>@username</code> yoki <code>-1001234567890</code>)",
        reply_markup=channels_menu_kb(),
    )


@router.message(AdminState.waiting_channel_remove)
async def process_remove_channel(message: Message, db: Database, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Iltimos, username yoki ID yuboring.")
        return

    if message.text == BTN_ADMIN_BACK:
        await state.clear()
        await channel_management_menu(message, db, state)
        return

    removed = await db.channels.remove(message.text.strip())
    await state.clear()
    await message.answer(
        "✅ O'chirildi." if removed else "❌ Bunday kanal topilmadi.",
        reply_markup=channels_menu_kb(),
    )


@router.message(Command("channels"))
@router.message(F.text == BTN_ADMIN_CHANNELS)
@router.message(F.text == "📋 Kanallar")
async def list_channels(message: Message, db: Database, state: FSMContext) -> None:
    await state.clear()
    channels = await db.channels.get_all()
    if not channels:
        await message.answer("📋 Majburiy kanallar ro'yxati bo'sh.", reply_markup=channels_menu_kb())
        return

    lines = [f"• {c['title']} (<code>{c['chat_id']}</code>)" for c in channels]
    await message.answer("📋 <b>Majburiy kanallar:</b>\n\n" + "\n".join(lines), reply_markup=channels_menu_kb())