import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import Message
from handlers.user.menu import my_points, participate

@pytest.mark.asyncio
async def test_my_points():
    message = MagicMock()
    message.from_user = MagicMock(id=123)
    message.answer = AsyncMock()
    db = MagicMock()
    db.users = AsyncMock()
    db.users.get_by_id.return_value = {"points": 10, "registered": 1}
    db.users.get_all_registered_ids.return_value = [123]
    db.users.get_winners_ids.return_value = [123]
    db.users.get_user_stats.return_value = {"points": 10, "registered": 1, "rank": 1}
    await my_points(message, db, "test_bot")
    message.answer.assert_called_once()
    assert "Ballaringiz: 10" in message.answer.call_args[0][0]

@pytest.mark.asyncio
async def test_participate():
    message = MagicMock()
    message.from_user = MagicMock(id=123)
    message.answer = AsyncMock()
    db = MagicMock()
    db.users = AsyncMock()
    db.users.get_by_id.return_value = {"registered": 1}
    bot = AsyncMock()
    state = AsyncMock()
    await participate(message, bot, db, state, "test_bot")
    message.answer.assert_called_once()


@pytest.mark.asyncio
async def test_show_main_menu_regular_user():
    """Oddiy (admin bo'lmagan) foydalanuvchi uchun _show_main_menu xatosiz ishlashi kerak."""
    from handlers.user.registration import _show_main_menu
    message = MagicMock()
    message.from_user = MagicMock(id=111222333, full_name="Regular User")
    message.answer = AsyncMock()
    db = MagicMock()
    db.admins = AsyncMock()
    db.admins.is_admin.return_value = False

    await _show_main_menu(message, db=db, full_name="Regular User")
    message.answer.assert_called_once()
    assert "Assalomu alaykum" in message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_start_already_registered_regular_user():
    """Ro'yxatdan o'tgan oddiy foydalanuvchi /start bosganda _show_main_menu chaqirilishi kerak."""
    from handlers.user.registration import start
    message = MagicMock()
    message.from_user = MagicMock(id=444555666, full_name="Test User")
    loading_msg = AsyncMock()
    loading_msg.delete = AsyncMock()
    message.answer = AsyncMock(return_value=loading_msg)
    
    db = MagicMock()
    db.users = AsyncMock()
    db.users.get_by_id.return_value = {"full_name": "Test User", "registered": 1}
    db.admins = AsyncMock()
    db.admins.is_admin.return_value = False

    command = MagicMock()
    command.args = None
    bot = AsyncMock()
    state = AsyncMock()

    await start(message, command, bot, db, state, "test_bot")
    loading_msg.delete.assert_called_once()
    # message.answer kamida 2 marta chaqirilgan (loading_msg + main_menu)
    assert message.answer.call_count >= 2


def test_main_menu_kb():
    from keyboards.user import BTN_ADMIN, main_menu_kb

    kb_user = main_menu_kb(is_admin=False)
    user_buttons = [btn.text for row in kb_user.keyboard for btn in row]
    assert BTN_ADMIN not in user_buttons

    kb_admin = main_menu_kb(is_admin=True)
    admin_buttons = [btn.text for row in kb_admin.keyboard for btn in row]
    assert BTN_ADMIN in admin_buttons


def test_admins_menu_kb():
    from keyboards.admin import (
        BTN_ADMIN_ADD_ADMIN,
        BTN_ADMIN_BACK,
        BTN_ADMIN_LIST_ADMINS,
        BTN_ADMIN_MANAGEMENT,
        BTN_ADMIN_REMOVE_ADMIN,
        admin_menu_kb,
        admins_menu_kb,
    )

    kb = admins_menu_kb()
    buttons = [btn.text for row in kb.keyboard for btn in row]
    assert BTN_ADMIN_ADD_ADMIN in buttons
    assert BTN_ADMIN_REMOVE_ADMIN in buttons
    assert BTN_ADMIN_LIST_ADMINS in buttons
    assert BTN_ADMIN_BACK in buttons

    admin_kb = admin_menu_kb()
    admin_buttons = [btn.text for row in admin_kb.keyboard for btn in row]
    assert BTN_ADMIN_MANAGEMENT in admin_buttons


