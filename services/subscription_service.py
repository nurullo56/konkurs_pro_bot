from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List
from aiogram import Bot
from aiogram.enums import ChatMemberStatus

from database import Database

ALLOWED_STATUSES = {
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.CREATOR,
}


def _normalize(chat_id: str) -> int | str:
    return int(chat_id) if chat_id.lstrip("-").isdigit() else chat_id


async def _check_single_channel(
    bot: Bot, channel: Dict[str, Any], user_id: int, db: Database | None = None
) -> Dict[str, Any] | None:
    chat_id_raw = channel["chat_id"]
    is_subbed = False
    try:
        member = await bot.get_chat_member(_normalize(chat_id_raw), user_id)
        if member.status in ALLOWED_STATUSES:
            is_subbed = True
    except Exception as e:
        logging.warning(f"Could not check membership for channel {chat_id_raw}, user {user_id}: {e}")

    if not is_subbed and db is not None:
        try:
            has_req = await db.join_requests.has_request(user_id, str(chat_id_raw))
            if has_req:
                is_subbed = True
        except Exception as e:
            logging.error(f"Error checking join_requests for channel {chat_id_raw}: {e}")

    return None if is_subbed else channel


async def get_unsubscribed(
    bot: Bot, channels: List[Dict[str, Any]], user_id: int, db: Database | None = None
) -> List[Dict[str, Any]]:
    if not channels:
        return []

    tasks = [_check_single_channel(bot, ch, user_id, db) for ch in channels]
    results = await asyncio.gather(*tasks)
    return [ch for ch in results if ch is not None]
