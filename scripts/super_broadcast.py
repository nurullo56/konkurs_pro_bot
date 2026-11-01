import argparse
import asyncio
import logging
import os
import time

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError, TelegramBadRequest

# Bot configuration and database
from config import Config
from database.db import Database


# ✅ FIX #5: Xavfsizlik konstantalari
MAX_RETRIES_PER_USER = 3
MAX_RETRY_AFTER_SECONDS = 60
MAX_BROADCAST_DURATION = 7200
PROGRESS_UPDATE_EVERY = 10
THROTTLE_DELAY = 0.04


async def _send_one_super(bot: Bot, uid: int, text: str) -> tuple[str, int | None]:
    """Terminal broadcast uchun bitta userga xabar yuborish (retry bilan)."""
    for attempt in range(1, MAX_RETRIES_PER_USER + 1):
        try:
            await bot.send_message(chat_id=uid, text=text, parse_mode="HTML")
            return ("sent", None)
        except TelegramRetryAfter as e:
            if e.retry_after > MAX_RETRY_AFTER_SECONDS:
                logging.warning(f"User {uid}: retry_after={e.retry_after}s juda katta. Skip.")
                return ("timeout", e.retry_after)
            if attempt == MAX_RETRIES_PER_USER:
                logging.warning(f"User {uid}: {MAX_RETRIES_PER_USER} marta FloodWait. Skip.")
                return ("timeout", e.retry_after)
            logging.info(f"FloodWait {e.retry_after}s (urinish {attempt}/{MAX_RETRIES_PER_USER}, user={uid})")
            await asyncio.sleep(e.retry_after + 1)
        except TelegramForbiddenError:
            logging.info(f"User {uid} botni bloklagan. Ban qilinadi.")
            return ("blocked", None)
        except TelegramBadRequest as e:
            logging.error(f"User {uid}: BadRequest: {e}")
            return ("failed", None)
        except Exception as e:
            logging.error(f"User {uid}: kutilmagan xato: {e}")
            return ("failed", None)
    return ("failed", None)


async def broadcast(bot: Bot, db: Database, text: str, target: str, target_user_id: int = None):
    logging.info("Ma'lumotlar bazasiga ulanilmoqda...")
    await db.connect()

    try:
        if target == "all":
            user_ids = await db.users.get_all_registered_ids()
        elif target == "winners":
            # get_winners_ids top_n kabi limit qabul qilishi mumkin, bu yerda 10 deymiz
            user_ids = await db.users.get_winners_ids(10)
        elif target == "single" and target_user_id:
            user_ids = [target_user_id]
        else:
            user_ids = []

        if not user_ids:
            logging.warning("Xabar yuborish uchun foydalanuvchilar topilmadi!")
            return

        total = len(user_ids)
        logging.info(f"Jami {total} ta foydalanuvchiga xabar yuborish boshlandi...")

        sent = failed = blocked = skipped = 0
        start_time = time.monotonic()

        for idx, uid in enumerate(user_ids, 1):
            elapsed = time.monotonic() - start_time
            if elapsed > MAX_BROADCAST_DURATION:
                logging.warning(
                    f"Global timeout ({MAX_BROADCAST_DURATION}s). "
                    f"{idx - 1}/{total} user'ga yuborildi."
                )
                break

            status, retry_after = await _send_one_super(bot, uid, text)

            if status == "sent":
                sent += 1
            elif status == "blocked":
                blocked += 1
                try:
                    await db.users.set_banned(uid, True)
                except Exception as ban_err:
                    logging.warning(f"Could not ban user {uid}: {ban_err}")
            elif status == "timeout":
                skipped += 1
            else:
                failed += 1

            if idx % PROGRESS_UPDATE_EVERY == 0 or idx == total:
                logging.info(
                    f"Progress: {idx}/{total} "
                    f"(✅ {sent}, 🚫 {blocked}, ⏭ {skipped}, ❌ {failed})"
                )

            await asyncio.sleep(THROTTLE_DELAY)

        total_elapsed = time.monotonic() - start_time
        logging.info(
            f"Tarqatish yakunlandi! Jami: {total}, "
            f"✅ {sent}, 🚫 {blocked}, ⏭ {skipped}, ❌ {failed}, "
            f"⏱ {int(total_elapsed)}s"
        )

    finally:
        await db.close()
        await bot.session.close()


def main():
    parser = argparse.ArgumentParser(description="Terminal orqali bot foydalanuvchilariga xabar tarqatish (Super Admin)")
    parser.add_argument("--text", type=str, required=True, help="Yuboriladigan xabar matni (HTML formatida yozish mumkin)")
    parser.add_argument("--env", type=str, default=".env", help="Qaysi botning .env faylini ishlatish kerakligi")
    parser.add_argument("--target", type=str, choices=["all", "winners", "single"], default="all", help="Kimlarga yuborish (all, winners, single)")
    parser.add_argument("--user_id", type=int, help="Agar target='single' bo'lsa, foydalanuvchi Telegram ID si")

    args = parser.parse_args()

    # ENV faylni o'zgartirish (agar ko'rsatilgan bo'lsa)
    if args.env != ".env":
        os.environ["ENV_FILE"] = args.env

    # Config.load() shunda biz bergan .env faylni o'qiydi
    config = Config.load()

    bot = Bot(token=config.bot_token)
    db = Database(
        db_type=config.db_type,
        dsn=config.postgres_dsn,
        path=config.db_path,
    )

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    asyncio.run(broadcast(
        bot=bot,
        db=db,
        text=args.text,
        target=args.target,
        target_user_id=args.user_id
    ))


if __name__ == "__main__":
    main()
