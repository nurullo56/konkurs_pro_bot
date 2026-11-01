from __future__ import annotations

from aiogram import Router
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from config import config
from database import Database


class AdminFilter(BaseFilter):
    """
    Foydalanuvchi admin ekanligini tekshiruvchi filtr:
    1) config.admin_ids (.env) da bormi?
    2) Ma'lumotlar bazasidagi (db.admins) ro'yxatda bormi?
    """

    async def __call__(self, event: Message | CallbackQuery, db: Database | None = None) -> bool:
        if not event.from_user:
            return False
        user_id = event.from_user.id
        if user_id in config.admin_ids:
            return True
        if db is not None and hasattr(db, "admins"):
            return await db.admins.is_admin(user_id)
        return False


router = Router(name="admin")
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())
