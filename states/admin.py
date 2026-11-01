from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class AdminState(StatesGroup):
    waiting_channel_info = State()
    waiting_channel_remove = State()
    waiting_broadcast_target = State()
    waiting_broadcast_message = State()
    waiting_single_user_id = State()
    waiting_single_user_message = State()
    waiting_rules_text = State()
    waiting_prizes_media = State()
    waiting_custom_emoji_input = State()
    waiting_admin_add = State()
    waiting_admin_remove = State()