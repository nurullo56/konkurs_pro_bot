from __future__ import annotations

import logging
from typing import Optional, Tuple

from aiogram.types import Message

from database import Database

logger = logging.getLogger(__name__)


# Default emoji mappings for quick reference
EMOJI_KEYS = {
    "trophy": ("🏆", "G'oliblar / Kubok"),
    "stats": ("📊", "Statistika / Analitika"),
    "gift": ("🎁", "Sovg'alar / Sovrin"),
    "broadcast": ("📢", "Xabar tarqatish"),
    "users": ("👥", "A'zolar / Ishtirokchilar"),
    "fire": ("🔥", "Konkurs aksiyasi"),
    "money": ("💰", "Pul / Balans"),
    "star": ("⭐️", "Reyting / Yulduz"),
}


def _utf16_slice(text: str, offset: int, length: int) -> str:
    """
    Telegram entity offset/length (UTF-16 code units) ni Python string
    slice (Unicode code points) ga konvertatsiya qiladi.

    Surrogate pair'lar (emoji, ba'zi CJK belgilari) bilan to'g'ri ishlaydi.

    :param text: Asl matn.
    :param offset: UTF-16 offset (Telegram entity dan).
    :param length: UTF-16 length (Telegram entity dan).
    :return: To'g'ri kesilgan substring.
    """
    try:
        encoded = text.encode("utf-16-le")
        start_byte = offset * 2
        end_byte = (offset + length) * 2
        sliced = encoded[start_byte:end_byte]
        return sliced.decode("utf-16-le", errors="replace")
    except (UnicodeDecodeError, UnicodeEncodeError) as e:
        logger.warning(
            f"UTF-16 slice failed (offset={offset}, length={length}): {e}. "
            f"Falling back to Python slice."
        )
        return text[offset : offset + length]


async def get_emoji(db: Database, key: str) -> str:
    """
    Returns custom Telegram Premium emoji tag <tg-emoji emoji-id="...">char</tg-emoji>
    if set in DB settings, otherwise returns default emoji char.

    :param db: Database obyekti.
    :param key: EMOJI_KEYS dagi kalit (masalan: 'trophy', 'stats').
    :return: HTML emoji string.
    """
    default_char = EMOJI_KEYS.get(key, ("✨", ""))[0]
    custom_id = await db.settings.get(f"emoji_{key}", "")
    if custom_id:
        return f'<tg-emoji emoji-id="{custom_id}">{default_char}</tg-emoji>'
    return default_char


def extract_custom_emoji_from_message(message: Message) -> Optional[Tuple[str, str]]:
    """
    Extracts (emoji_char, custom_emoji_id) from message entities if sent by Premium user.

    FIX: caption_entities ham tekshiriladi (rasmli xabarlar uchun).
    FIX #4: UTF-16 offset ni to'g'ri konvertatsiya qiladi (surrogate pair'lar uchun).

    :param message: aiogram Message obyekti.
    :return: (emoji_char, custom_emoji_id) tuple yoki None.
    """
    # 1. Text entities (oddiy matn xabarlari)
    if message.entities and message.text:
        for entity in message.entities:
            if entity.type == "custom_emoji" and entity.custom_emoji_id:
                char = _utf16_slice(message.text, entity.offset, entity.length)
                if char:
                    return char, entity.custom_emoji_id

    # 2. Caption entities (FIX: rasm/video caption'lari uchun)
    if message.caption_entities and message.caption:
        for entity in message.caption_entities:
            if entity.type == "custom_emoji" and entity.custom_emoji_id:
                char = _utf16_slice(message.caption, entity.offset, entity.length)
                if char:
                    return char, entity.custom_emoji_id

    return None
