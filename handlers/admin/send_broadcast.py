from __future__ import annotations

import asyncio
import logging
import time

from aiogram import F
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import config
from database import Database
from handlers.admin.router import router
from keyboards.admin import BTN_ADMIN_BROADCAST, broadcast_type_kb
from services import get_emoji
from states import AdminState


# ✅ FIX #5: Broadcast uchun xavfsizlik konstantalari
MAX_RETRIES_PER_USER = 3           # Har bir user uchun maksimal urinish
MAX_RETRY_AFTER_SECONDS = 60       # Agar retry_after > bu qiymat → skip
MAX_BROADCAST_DURATION = 7200      # 2 soat — butun broadcast uchun timeout
PROGRESS_UPDATE_EVERY = 10         # Har 10 ta user'da progress yangilanadi
THROTTLE_DELAY = 0.04              # Har bir xabar orasidagi pauza (~25 msg/sec)


@router.message(Command("broadcast"))
@router.message(F.text == BTN_ADMIN_BROADCAST)
async def broadcast_start(message: Message, db: Database, state: FSMContext) -> None:
    """Xabar tarqatish bo'limini ochadi va maqsadli auditoriyani tanlashni so'raydi."""
    await state.clear()
    await state.set_state(AdminState.waiting_broadcast_target)
    e_bc = await get_emoji(db, "broadcast")
    await message.answer(
        f"{e_bc} <b>Xabar tarqatish bo'limi</b>\n\n"
        "Xabar yubormoqchi bo'lgan maqsadli auditoriyani tanlang:",
        reply_markup=broadcast_type_kb(),
    )


@router.callback_query(F.data.startswith("bc_target:"))
async def process_broadcast_target(call: CallbackQuery, state: FSMContext) -> None:
    """Broadcast maqsadini tanlash callback'ini qayta ishlaydi."""
    target = call.data.split(":")[1]
    if target == "cancel":
        await state.clear()
        await call.message.edit_text("❌ Xabar tarqatish bekor qilindi.")
        await call.answer()
        return

    await state.update_data(broadcast_target=target)

    if target == "single":
        await state.set_state(AdminState.waiting_single_user_id)
        await call.message.edit_text(
            "👤 <b>Xabar yubormoqchi bo'lgan foydalanuvchining Telegram ID sini kiriting:</b>"
        )
    else:
        await state.set_state(AdminState.waiting_broadcast_message)
        target_name = "barcha foydalanuvchilarga" if target == "all" else f"top {config.top_n} g'oliblarga"
        await call.message.edit_text(
            f"📢 <b>{target_name.capitalize()} yubormoqchi bo'lgan xabaringizni yuboring:</b>\n"
            f"(Matn, rasm, video, audio va h.k.)"
        )
    await call.answer()


@router.message(AdminState.waiting_single_user_id)
async def process_single_user_id(message: Message, state: FSMContext) -> None:
    """Muayyan foydalanuvchi ID sini qayta ishlaydi."""
    text = (message.text or "").strip()
    if not text.lstrip("-").isdigit():
        await message.answer("❌ Telegram ID raqamlardan iborat bo'lishi kerak. Qayta kiriting:")
        return

    await state.update_data(target_user_id=int(text))
    await state.set_state(AdminState.waiting_broadcast_message)
    await message.answer(f"👤 User ID <code>{text}</code> uchun yubormoqchi bo'lgan xabaringizni yuboring:")


# ✅ FIX #5: Bitta userga xabar yuborish (retry bilan)
async def _send_one(
    target_message: Message,
    uid: int,
) -> tuple[str, int | None]:
    """
    Bitta foydalanuvchiga xabar yuborishga harakat qiladi (retry bilan).

    :return: (status, retry_after_or_none):
             - 'sent'    — muvaffaqiyatli yuborildi
             - 'blocked' — bot bloklangan (ban qilish kerak)
             - 'failed'  — doimiy xato
             - 'timeout' — retry_after juda katta (keyingi safar uriniladi)
    """
    for attempt in range(1, MAX_RETRIES_PER_USER + 1):
        try:
            await target_message.copy_to(uid)
            return ("sent", None)
        except TelegramRetryAfter as e:
            if e.retry_after > MAX_RETRY_AFTER_SECONDS:
                logging.warning(
                    f"Broadcast: User {uid} uchun retry_after={e.retry_after}s "
                    f"juda katta (>{MAX_RETRY_AFTER_SECONDS}s). Skip qilinadi."
                )
                return ("timeout", e.retry_after)
            if attempt == MAX_RETRIES_PER_USER:
                logging.warning(
                    f"Broadcast: User {uid} uchun {MAX_RETRIES_PER_USER} marta "
                    f"FloodWait. Skip qilinadi."
                )
                return ("timeout", e.retry_after)
            logging.info(
                f"Broadcast: FloodWait {e.retry_after}s "
                f"(urinish {attempt}/{MAX_RETRIES_PER_USER}, user={uid})"
            )
            await asyncio.sleep(e.retry_after + 1)
        except TelegramForbiddenError:
            logging.info(f"Broadcast: User {uid} botni bloklagan. Ban qilinadi.")
            return ("blocked", None)
        except TelegramBadRequest as e:
            logging.info(f"Broadcast: User {uid} uchun BadRequest: {e}")
            return ("failed", None)
        except Exception:
            logging.exception(f"Broadcast: User {uid} uchun kutilmagan xato")
            return ("failed", None)
    return ("failed", None)


async def _execute_broadcast(
    target_message: Message,
    status_message: Message,
    db: Database,
    target: str,
    target_user_id: int | None = None,
) -> None:
    """
    Xabar tarqatishni bajaradi (xavfsiz retry + global timeout bilan).
    """
    if target == "all":
        user_ids = await db.users.get_all_registered_ids()
    elif target == "winners":
        user_ids = await db.users.get_winners_ids(config.top_n)
    elif target == "single" and target_user_id:
        user_ids = [target_user_id]
    else:
        user_ids = []

    if not user_ids:
        await status_message.edit_text("❌ Xabar yuborish uchun foydalanuvchilar topilmadi.")
        return

    total = len(user_ids)
    sent = failed = blocked = skipped = 0
    start_time = time.monotonic()
    last_status_update = 0.0
    MIN_STATUS_UPDATE_INTERVAL = 2.5  # Kamida 2.5s oralig'ida tahrirlash (Telegram 429 flood'dan himoya)

    for idx, uid in enumerate(user_ids, 1):
        # Global timeout
        elapsed = time.monotonic() - start_time
        if elapsed > MAX_BROADCAST_DURATION:
            logging.warning(
                f"Broadcast: Global timeout ({MAX_BROADCAST_DURATION}s) "
                f"yetdi. {idx - 1}/{total} user'ga yuborildi."
            )
            await status_message.answer(
                f"⚠️ <b>Broadcast vaqt tugashi sababli to'xtatildi</b>\n\n"
                f"📊 {idx - 1}/{total} user'ga yuborildi.\n"
                f"Keyingi safar qolgan {total - idx + 1} user'ga urinib ko'ring."
            )
            break

        status, retry_after = await _send_one(target_message, uid)

        if status == "sent":
            sent += 1
        elif status == "blocked":
            blocked += 1
            try:
                await db.users.set_banned(uid, True)
            except Exception as ban_err:
                logging.warning(f"Could not mark user {uid} as banned: {ban_err}")
        elif status == "timeout":
            skipped += 1
        else:
            failed += 1

        now = time.monotonic()
        if (now - last_status_update >= MIN_STATUS_UPDATE_INTERVAL and idx % PROGRESS_UPDATE_EVERY == 0) or idx == total:
            last_status_update = now
            elapsed_str = f"{int(elapsed)}s"
            try:
                await status_message.edit_text(
                    f"📢 <b>Xabar yuborilmoqda...</b> ({idx}/{total})\n\n"
                    f"✅ Yuborildi: {sent}\n"
                    f"🚫 Bloklangan: {blocked}\n"
                    f"⏭ Skip: {skipped}\n"
                    f"❌ Xato: {failed}\n"
                    f"⏱ Vaqt: {elapsed_str}"
                )
            except Exception as e:
                logging.debug(f"Could not update status message: {e}")

        await asyncio.sleep(THROTTLE_DELAY)

    total_elapsed = time.monotonic() - start_time
    minutes = int(total_elapsed // 60)
    seconds = int(total_elapsed % 60)

    await status_message.answer(
        f"🎉 <b>Xabar tarqatish yakunlandi!</b>\n\n"
        f"📊 Jami target: {total}\n"
        f"✅ Yuborildi: {sent}\n"
        f"🚫 Bloklangan (ban qilindi): {blocked}\n"
        f"⏭ Skip (keyingi safar): {skipped}\n"
        f"❌ Xato: {failed}\n\n"
        f"⏱ Umumiy vaqt: {minutes}m {seconds}s"
    )


@router.message(AdminState.waiting_broadcast_message)
async def process_broadcast_message(message: Message, db: Database, state: FSMContext) -> None:
    """
    Broadcast xabarini qabul qiladi va yuborishni boshlaydi.

    FIX: media_group_id bo'lsa ogohlantirish ko'rsatiladi (album to'liq qo'llab-quvvatlanmaydi).
    """
    # FIX: Album (media group) yuborilsa — ogohlantirish
    if message.media_group_id:
        await message.answer(
            "⚠️ <b>Album yubordingiz!</b>\n\n"
            "Hozircha album to'liq qo'llab-quvvatlanmaydi. "
            "Iltimos, bitta rasm/video/matn yuboring."
        )
        return

    data = await state.get_data()
    target = data.get("broadcast_target", "all")
    target_user_id = data.get("target_user_id")

    await state.clear()
    progress_msg = await message.answer("📢 Xabar tarqatish boshlanmoqda...")
    await _execute_broadcast(message, progress_msg, db, target, target_user_id)
