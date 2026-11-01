from __future__ import annotations

import asyncio
import logging
import os as _os
import sys as _sys

# LOG_FILE env orqali log faylga yo'naltirish — import'lardan oldin qilinadi,
# shunda barcha xatoliklar (shu jumladan import xatoliklari) ham log ga tushadi.
_log_file_path = _os.getenv("LOG_FILE")
_log_handlers: list[logging.Handler] = []
if _log_file_path:
    _log_handlers.append(logging.FileHandler(_log_file_path, encoding="utf-8"))
# pythonw.exe da stdout yo'q, shuning uchun StreamHandler xato bermasin
try:
    _log_handlers.append(logging.StreamHandler(_sys.stdout))
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=_log_handlers if _log_handlers else None,
    force=True,
)

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

try:
    from aiogram.fsm.storage.redis import RedisStorage
    import redis.asyncio as aioredis
except ImportError:
    RedisStorage = None
    aioredis = None

from config import config
from database import Database
from handlers import admin, user
from middlewares import AntiFloodMiddleware
from utils import setup_bot_commands


def _validate_config() -> None:
    """
    Konfiguratsiyani tekshiradi va kritik xatolar haqida ogohlantirishlar beradi.
    BOT_TOKEN yo'q bo'lsa, ValueError ko'taradi.

    Eslatma: ADMIN_IDS tekshiruvi endi Config.__post_init__ da amalga oshiriladi
    (fail-fast). Bu yerda faqat BOT_TOKEN format tekshiriladi.
    """
    if not config.bot_token or config.bot_token in ("YOUR_BOT_TOKEN_HERE", ""):
        raise ValueError(
            "❌ BOT_TOKEN is not set in .env file!\n"
            "Iltimos, .env faylida BOT_TOKEN ni to'g'ri kiriting."
        )


async def main() -> None:
    """Bot asosiy entry point."""
    # Logging global darajada (bot.py boshida) allaqachon o'rnatilgan.

    # 0. Config tekshiruvi
    _validate_config()

    # 1. Initialize Database (PostgreSQL / SQLite)
    db = Database(
        db_type=config.db_type,
        dsn=config.postgres_dsn,
        path=config.db_path,
    )
    await db.connect()

    # 2. Setup FSM Storage & Redis Client
    redis_client = None
    storage = MemoryStorage()

    if config.redis_url and aioredis and RedisStorage:
        try:
            redis_client = aioredis.from_url(config.redis_url)
            await redis_client.ping()
            storage = RedisStorage(redis=redis_client)
            logging.info(f"Connected to Redis at {config.redis_url}")
        except Exception as e:
            logging.warning(f"Redis connection failed ({e}), using MemoryStorage.")
            redis_client = None
            storage = MemoryStorage()

    bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=storage)
    dp["db"] = db
    dp["redis"] = redis_client

    # 3. Setup Anti-Flood Middleware
    antiflood = AntiFloodMiddleware(rate_limit=config.rate_limit, redis_client=redis_client)
    dp.message.outer_middleware(antiflood)
    dp.callback_query.outer_middleware(antiflood)

    # 4. Include Routers
    dp.include_router(admin.router)
    dp.include_router(user.router)

    # Startup function to register webhook
    async def on_startup(bot: Bot) -> None:
        await setup_bot_commands(bot)
        me = await bot.get_me()
        dp["bot_username"] = me.username
        logging.info(f"Bot started: @{me.username}")

        if config.use_webhook:
            url = f"{config.webhook_url}{config.webhook_path}"
            await bot.set_webhook(
                url=url,
                secret_token=config.webhook_secret,
                drop_pending_updates=True
            )
            logging.info(f"Webhook set to {url}")
        else:
            await bot.delete_webhook(drop_pending_updates=True)

    dp.startup.register(on_startup)

    try:
        if config.use_webhook:
            from fastapi import FastAPI, Request, HTTPException
            import uvicorn
            from aiogram.types import Update
            from contextlib import asynccontextmanager

            logging.info(f"Starting FastAPI Webhook server on {config.webapp_host}:{config.webapp_port}...")

            workflow_data = {"dispatcher": dp, "bot": bot, **dp.workflow_data}

            @asynccontextmanager
            async def lifespan(app: FastAPI):
                await dp.emit_startup(**workflow_data)
                yield
                await dp.emit_shutdown(**workflow_data)

            app = FastAPI(lifespan=lifespan)

            @app.post(config.webhook_path)
            async def bot_webhook(request: Request):
                if config.webhook_secret:
                    token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
                    if token != config.webhook_secret:
                        raise HTTPException(status_code=401, detail="Unauthorized")
                
                try:
                    update_dict = await request.json()
                    update = Update(**update_dict)
                    await dp.feed_update(bot=bot, update=update)
                except Exception as e:
                    logging.error(f"Error handling update: {e}")
                
                return {"ok": True}

            config_uv = uvicorn.Config(app, host=config.webapp_host, port=config.webapp_port, log_level="info")
            server = uvicorn.Server(config_uv)
            await server.serve()
        else:
            logging.info("Starting Telegram Bot polling...")
            await dp.start_polling(bot)
    finally:
        await db.close()
        if redis_client:
            await redis_client.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
