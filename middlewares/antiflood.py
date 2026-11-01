from __future__ import annotations

import logging
import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

# Lua script Redis'da atomik rate-limit tekshiruvi uchun.
# GET + SET operatsiyasini race condition'siz bajaradi.
_RATE_LIMIT_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local ttl_ms = tonumber(ARGV[3])
local last = redis.call('GET', key)
if last then
    local last_num = tonumber(last)
    if last_num and (now - last_num) < limit then
        return 0
    end
end
redis.call('SET', key, tostring(now), 'PX', ttl_ms)
return 1
"""


class AntiFloodMiddleware(BaseMiddleware):
    """
    Anti-flood middleware: har bir foydalanuvchiga rate_limit soniyada
    bir marta xabar yuborishga ruxsat beradi.

    Redis mavjud bo'lsa — Lua script orqali atomik tekshiruv (race condition yo'q).
    Redis yo'q bo'lsa — in-memory dict (bir process uchun).
    """

    def __init__(self, rate_limit: float = 1.5, redis_client: Any = None) -> None:
        """
        :param rate_limit: Har bir foydalanuvchi uchun minimal interval (soniyalarda).
        :param redis_client: Redis asyncio klienti yoki None.
        """
        super().__init__()
        self.rate_limit = rate_limit
        self.redis = redis_client
        self.cache: Dict[int, float] = {}
        self._lua_sha: str | None = None

    async def _ensure_lua_script(self) -> None:
        """
        Lua skriptni Redis'ga yuklaydi (SCRIPT LOAD) va SHA'sini saqlaydi.
        Keyingi chaqiruvlarda EVALSHA ishlatiladi (tezroq).
        """
        if self._lua_sha is None and self.redis is not None:
            try:
                self._lua_sha = await self.redis.script_load(_RATE_LIMIT_LUA)
            except Exception as e:
                logging.warning(f"AntiFlood: Could not load Lua script into Redis: {e}")
                self._lua_sha = None

    async def _check_redis_rate_limit(self, user_id: int, current_time: float) -> bool:
        """
        Redis orqali rate limit tekshiruvi (atomik Lua script).

        :param user_id: Foydalanuvchi Telegram IDsi.
        :param current_time: Hozirgi vaqt (time.time()).
        :return: True — ruxsat, False — flood.
        """
        if self.redis is None:
            return True

        key = f"antiflood:{user_id}"
        now_str = str(current_time)
        limit_str = str(self.rate_limit)
        ttl_ms = int(self.rate_limit * 1000 * 2)  # TTL = rate_limit * 2 ms

        try:
            if self._lua_sha:
                # Tez yo'l: EVALSHA
                try:
                    result = await self.redis.evalsha(
                        self._lua_sha, 1, key, now_str, limit_str, str(ttl_ms)
                    )
                    return bool(result)
                except Exception as sha_err:
                    # SHA eskirgan yoki yo'q — qayta yuklash
                    logging.debug(f"AntiFlood: EVALSHA failed, falling back to EVAL: {sha_err}")
                    self._lua_sha = None

            # Zaxira yo'l: EVAL (to'g'ridan-to'g'ri skript)
            result = await self.redis.eval(
                _RATE_LIMIT_LUA, 1, key, now_str, limit_str, str(ttl_ms)
            )
            return bool(result)

        except Exception as e:
            # Redis xato bersa — fail-open (foydalanuvchini o'tkazib yuborish)
            logging.warning(f"AntiFlood: Redis error for user {user_id}, failing open: {e}")
            return True

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Middleware asosiy logikasi."""
        user_id: int | None = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id is None:
            return await handler(event, data)

        current_time = time.time()

        if self.redis:
            await self._ensure_lua_script()
            allowed = await self._check_redis_rate_limit(user_id, current_time)
            if not allowed:
                await self._notify_user(event)
                return None
        else:
            last_time = self.cache.get(user_id, 0.0)
            if current_time - last_time < self.rate_limit:
                await self._notify_user(event)
                return None
            self.cache[user_id] = current_time

            # Memory cleanup: kesh katta bo'lib ketsa, eski yozuvlarni tozalash
            if len(self.cache) > 10000:
                self.cache = {
                    k: v for k, v in self.cache.items() if current_time - v < 60
                }

        return await handler(event, data)

    @staticmethod
    async def _notify_user(event: TelegramObject) -> None:
        """
        Foydalanuvchiga flood haqida xabar beradi.
        Xatoliklar jim o'tkazilmaydi — debug darajasida loglash.
        """
        try:
            if isinstance(event, CallbackQuery):
                await event.answer("⚠️ Juda ko'p bosdingiz! Bir oz kuting...", show_alert=True)
            elif isinstance(event, Message):
                await event.answer("⚠️ Juda ko'p yozdingiz! Bir oz kuting...")
        except Exception as e:
            logging.debug(f"AntiFlood: Could not notify user about rate limit: {e}")
