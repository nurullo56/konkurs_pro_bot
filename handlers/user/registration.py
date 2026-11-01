from __future__ import annotations

import logging

from aiogram import Bot, F
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ChatJoinRequest, Message

from config import config
from database import Database
from handlers.user.router import router
from keyboards.user import channels_kb, contact_request_kb, main_menu_kb
from services import referral_service as referral
from services import subscription_service as subscription
from states import Registration


# ✅ FIX #6: Xabar muallifining ID sini xavfsiz olish
def _get_user_id(message: Message) -> int | None:
    """
    Xabar muallifining Telegram ID sini qaytaradi.
    Guruh/kanalda ham to'g'ri ishlaydi (chat.id emas, from_user.id).
    Kanal post bo'lsa — None qaytaradi.
    """
    return message.from_user.id if message.from_user else None


def _referral_link(bot_username: str, user_id: int) -> str:
    """Foydalanuvchi uchun referral havolasini yaratadi."""
    return f"https://t.me/{bot_username}?start={user_id}"


@router.chat_join_request()
async def on_chat_join_request(event: ChatJoinRequest, db: Database) -> None:
    """Kanal join request'ini qayd qiladi (ham chat_id, ham @username bilan)."""
    chat_id_str = str(event.chat.id)
    await db.join_requests.add(event.from_user.id, chat_id_str)
    if event.chat.username:
        await db.join_requests.add(event.from_user.id, f"@{event.chat.username}")


async def prompt_subscription(
    message: Message, bot: Bot, db: Database, loading_msg: Message | None = None
) -> bool:
    """
    Foydalanuvchi barcha kanallarga obuna bo'lganligini tekshiradi.
    Agar yo'q bo'lsa, obuna tugmalarini ko'rsatadi va False qaytaradi.
    Agar kanallar yo'q yoki hammaga obuna bo'lsa, True qaytaradi.
    """
    user_id = _get_user_id(message)
    if user_id is None:
        return False  # kanal post → obuna tekshirish kerak emas

    channels = await db.channels.get_all()
    if not channels:
        if loading_msg:
            try:
                await loading_msg.delete()
            except Exception as e:
                logging.debug(f"Failed to delete loading_msg: {e}")
        return True

    if not loading_msg:
        loading_msg = await message.answer("⏳ Yuklanmoqda...")

    # ✅ FIX #6: message.chat.id → user_id
    missing = await subscription.get_unsubscribed(bot, channels, user_id, db)

    try:
        await loading_msg.delete()
    except Exception as e:
        logging.debug(f"Failed to delete loading_msg: {e}")

    if not missing:
        return True

    await message.answer(
        "🚀 Loyihada ishtirok etish uchun quyidagi kanallarga a'zo bo'ling. "
        "Keyin \"✅ A'zo bo'ldim\" tugmasini bosing",
        reply_markup=channels_kb(missing),
    )
    return False


async def prompt_phone(message: Message, state: FSMContext) -> None:
    """Foydalanuvchidan telefon raqamini so'raydi."""
    await state.set_state(Registration.waiting_phone)
    await message.answer(
        "📱 \"Raqamni yuborish\" tugmasini bosgan holda raqamingizni yuboring!",
        reply_markup=contact_request_kb(),
    )


async def begin_registration(
    message: Message,
    bot: Bot,
    db: Database,
    state: FSMContext,
    referrer_id: int | None,
    loading_msg: Message | None = None,
) -> None:
    """
    Ro'yxatdan o'tish jarayonini boshlaydi:
    referrer_id ni saqlaydi, obunani tekshiradi, keyin telefon raqamini so'raydi.
    """
    await state.update_data(referrer_id=referrer_id)
    if not await prompt_subscription(message, bot, db, loading_msg=loading_msg):
        return
    await prompt_phone(message, state)


import html

async def _show_main_menu(message: Message, full_name: str | None = None) -> None:
    """Asosiy menyuni ko'rsatadi."""
    name = full_name or (message.from_user.full_name if message.from_user else "")
    name = html.escape(name)
    user_id = _get_user_id(message)
    if user_id and name:
        name_str = f' <a href="tg://user?id={user_id}">{name}</a>'
    elif name:
        name_str = f" {name}"
    else:
        name_str = ""
    is_admin = bool(
        message.from_user
        and (
            message.from_user.id in config.admin_ids
            or (hasattr(db, "admins") and await db.admins.is_admin(message.from_user.id))
        )
    )
    await message.answer(
        f"Assalomu alaykum{name_str} 👋\nQuyidagi menyudan kerakli bo'limni tanlang 👇",
        reply_markup=main_menu_kb(is_admin=is_admin),
    )


@router.message(CommandStart())
async def start(
    message: Message, command: CommandObject, bot: Bot, db: Database, state: FSMContext,
    bot_username: str,
) -> None:
    """
    /start komandasi handleri.
    Allaqachon ro'yxatdan o'tgan foydalanuvchilarni menyuga yo'naltiradi,
    yangilarni ro'yxatdan o'tish jarayoniga kiritadi.
    """
    user_id = _get_user_id(message)
    if user_id is None:
        return  # kanal post yoki anonim admin

    loading_msg = await message.answer("⏳ Yuklanmoqda...")
    # ✅ FIX #6: message.chat.id → user_id
    user = await db.users.get_by_id(user_id)
    if user and user["registered"]:
        name = user["full_name"] or (message.from_user.full_name if message.from_user else "")
        try:
            await loading_msg.delete()
        except Exception as e:
            logging.debug(f"Failed to delete loading_msg: {e}")
        await _show_main_menu(message, full_name=name)
        return

    referrer_id = int(command.args) if command.args and command.args.isdigit() else None
    await begin_registration(message, bot, db, state, referrer_id, loading_msg=loading_msg)


@router.callback_query(F.data == "check_sub")
async def check_sub(callback: CallbackQuery, bot: Bot, db: Database, state: FSMContext) -> None:
    """Foydalanuvchi obunani tekshirish tugmasini bosganida chaqiriladi."""
    await callback.answer("⏳ Yuklanmoqda...", show_alert=False)
    channels = await db.channels.get_all()
    missing = await subscription.get_unsubscribed(bot, channels, callback.from_user.id, db)
    if missing:
        await callback.answer("❌ Barcha kanallarga a'zo bo'lmadingiz.", show_alert=True)
        return

    await callback.message.delete()
    await prompt_phone(callback.message, state)
    await callback.answer()


@router.message(Registration.waiting_phone, F.contact)
async def receive_contact(
    message: Message, bot: Bot, db: Database, state: FSMContext, bot_username: str
) -> None:
    """
    Foydalanuvchi kontakt yuborganida chaqiriladi.
    FIX: contact.user_id None bo'lishi mumkin — None va o'zga ID tekshiriladi.
    """
    # FIX: contact.user_id None bo'lishi mumkin
    if not message.contact.user_id or message.contact.user_id != message.from_user.id:
        await message.answer("❗️ Iltimos, o'zingizning raqamingizni yuboring.")
        return

    data = await state.get_data()
    result = await referral.complete_registration(
        db.users,
        user_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username,
        phone=message.contact.phone_number,
        referrer_id=data.get("referrer_id"),
        start_points=config.start_points,
        referral_points=config.referral_points,
    )
    await state.clear()

    if not result.is_new:
        is_admin = bool(
            message.from_user
            and (
                message.from_user.id in config.admin_ids
                or (hasattr(db, "admins") and await db.admins.is_admin(message.from_user.id))
            )
        )
        await message.answer("Siz allaqachon ro'yxatdan o'tgansiz.", reply_markup=main_menu_kb(is_admin=is_admin))
        return

    # Referrer (taklif qilgan shaxs) ga xabarnoma yuborish
    if result.referrer_id:
        try:
            # DB dan eng yangi qiymatni o'qish (tranzaksiyadan keyin)
            referrer = await db.users.get_by_id(result.referrer_id)
            ref_name = referrer["full_name"] if referrer else ""
            ref_name = html.escape(ref_name)
            ref_points = referrer["points"] if referrer else 0
            ref_name_str = f" {ref_name}" if ref_name else ""
            escaped_full_name = html.escape(message.from_user.full_name)

            notification = (
                f"🎉 <b>Tabriklaymiz{ref_name_str}!</b>\n\n"
                f"👤 Do'stingiz <b>{escaped_full_name}</b> taklifingiz bo'yicha ro'yxatdan o'tdi!\n"
                f"⭐️ Sizga <b>+{config.referral_points} ball</b> berildi.\n"
                f"📊 Jami ballaringiz: <b>{ref_points} ball</b>"
            )
            await bot.send_message(result.referrer_id, notification)
        except Exception as e:
            logging.warning(f"Could not send referral notification to user {result.referrer_id}: {e}")

    link = _referral_link(bot_username, message.from_user.id)
    is_admin = bool(
        message.from_user
        and (
            message.from_user.id in config.admin_ids
            or (hasattr(db, "admins") and await db.admins.is_admin(message.from_user.id))
        )
    )
    await message.answer(
        f"🎉 Tabriklaymiz! Siz loyihamizga to'liq ro'yxatdan o'tdingiz va "
        f"boshlang'ich {config.start_points} ballga ega bo'ldingiz!\n\n"
        f"🔗 Referral havolangiz:\n{link}",
        reply_markup=main_menu_kb(is_admin=is_admin),
    )


@router.message(Registration.waiting_phone)
async def waiting_phone_fallback(message: Message) -> None:
    """Kontakt o'rniga boshqa narsa yuborilganida eslatma beradi."""
    await message.answer(
        "📱 Iltimos, \"Raqamni yuborish\" tugmasini bosing.",
        reply_markup=contact_request_kb(),
    )
