from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from config import config


async def setup_bot_commands(bot: Bot) -> None:
    # Oddiy foydalanuvchilar uchun buyruqlar
    user_commands = [
        BotCommand(command="start", description="♻️ Botni qayta ishga tushirish"),
        BotCommand(command="bot", description="🤖 Shunday bot buyurtma qilish"),
    ]
    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    # Adminlar uchun buyruqlar
    admin_commands = [
        BotCommand(command="start", description="♻️ Botni qayta ishga tushirish"),
        BotCommand(command="admin", description="👨‍💻 Admin paneli"),
        BotCommand(command="bot", description="🤖 Shunday bot buyurtma qilish"),
    ]
    for admin_id in config.admin_ids:
        try:
            await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception as e:
            logging.warning("Admin ID %s uchun buyruqlar o'rnatishda xato: %s", admin_id, e)