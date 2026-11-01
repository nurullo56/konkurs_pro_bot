from __future__ import annotations

import logging

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import Database
from handlers.admin.router import router
from keyboards.admin import BTN_ADMIN_PREMIUM_EMOJI, premium_emoji_settings_kb
from services import EMOJI_KEYS, extract_custom_emoji_from_message
from states import AdminState


@router.message(F.text == BTN_ADMIN_PREMIUM_EMOJI)
async def open_emoji_settings(message: Message, db: Database, state: FSMContext) -> None:
    """Premium emoji sozlamalari panelini ochadi."""
    await state.clear()
    kb = await premium_emoji_settings_kb(db)
    await message.answer(
        "👑 <b>Telegram Premium Emojilar Boshqaruvi</b>\n\n"
        "Botdagi standart smayliklar o'rniga o'zingizning Telegram Premium moslashtirilgan (Custom) emojilaringizni o'rnatishingiz mumkin.\n\n"
        "O'zgartirmoqchi bo'lgan emoijini quyidagi ro'yxatdan tanlang:",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("set_emoji:"))
async def process_emoji_select(call: CallbackQuery, db: Database, state: FSMContext) -> None:
    """Emoji tanlash callback'ini qayta ishlaydi."""
    key = call.data.split(":")[1]
    if key == "cancel":
        await state.clear()
        await call.message.edit_text("❌ Emoji sozlamalari yopildi.")
        await call.answer()
        return

    if key not in EMOJI_KEYS:
        await call.answer("❌ Noto'g'ri emoji turi.", show_alert=True)
        return

    default_char, label = EMOJI_KEYS[key]
    await state.update_data(target_emoji_key=key)
    await state.set_state(AdminState.waiting_custom_emoji_input)

    await call.message.edit_text(
        f"👑 <b>{label} ({default_char}) uchun Premium Emoji o'rnatish</b>\n\n"
        f"Iltimos, Telegram Premium hisobingizdan ushbu bo'lim uchun ishlatmoqchi bo'lgan <b>Custom Emoji</b>'ni shu yerga yuboring "
        f"(matn yoki rasm caption'ida).\n\n"
        f"<i>Masalan: Shu chatga premium emojini xabar qilib yuboring. Bot uni avtomatik ushlab oladi va saqlaydi!</i>"
    )
    await call.answer()


@router.message(AdminState.waiting_custom_emoji_input)
async def process_custom_emoji_input(message: Message, db: Database, state: FSMContext) -> None:
    """
    Admin yuborgan xabardan custom emoji ID ni ajratadi va saqlaydi.

    FIX: message.caption ham qo'llab-quvvatlanadi (rasmli xabarlar uchun).
    """
    data = await state.get_data()
    key = data.get("target_emoji_key")
    if not key or key not in EMOJI_KEYS:
        await state.clear()
        await message.answer("❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.")
        return

    default_char, label = EMOJI_KEYS[key]

    # Matn yoki caption'dan custom emoji entity'ni ajratish
    # FIX: caption ham tekshiriladi
    emoji_info = extract_custom_emoji_from_message(message)

    if emoji_info:
        char, custom_id = emoji_info
        await db.settings.set(f"emoji_{key}", custom_id)
        await state.clear()
        await message.answer(
            f"🎉 <b>Premium Emoji muvaffaqiyatli o'rnatildi!</b>\n\n"
            f"📌 Bo'lim: <b>{label}</b>\n"
            f"🆔 Custom Emoji ID: <code>{custom_id}</code>\n"
            f"✨ Ko'rinishi: <tg-emoji emoji-id=\"{custom_id}\">{char}</tg-emoji>\n\n"
            f"Endi bot xabarlarida ushbu Premium emoji avtomatik ko'rsatiladi!"
        )
    else:
        # FIX: matn yoki caption'dan raqam (raw custom_emoji_id) tekshirish
        text = (message.text or message.caption or "").strip()
        if text.isdigit():
            await db.settings.set(f"emoji_{key}", text)
            await state.clear()
            await message.answer(
                f"🎉 <b>Custom Emoji ID muvaffaqiyatli saqlandi!</b>\n\n"
                f"📌 Bo'lim: <b>{label}</b>\n"
                f"🆔 Custom Emoji ID: <code>{text}</code>"
            )
        else:
            await message.answer(
                "⚠️ <b>Telegram Premium Custom Emoji topilmadi!</b>\n\n"
                "Iltimos, Telegram Premium obunangiz bo'lsa, emoji menyusidan moslashtirilgan "
                "Premium emoji tanlab yuboring (matn yoki rasm caption'ida) yoki ID sini yuboring."
            )
            logging.debug(
                f"manage_emoji: No custom emoji found in message from user {message.from_user.id if message.from_user else 'unknown'}"
            )