from __future__ import annotations

from aiogram import F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import config
from database import Database
from handlers.admin.router import router
from keyboards.admin import (
    BTN_ADMIN_CHARTS,
    BTN_ADMIN_EXCEL,
    BTN_ADMIN_STATS,
    BTN_ADMIN_WINNERS,
)
from services.chart_service import generate_registration_chart
from services.emoji_service import get_emoji
from services.export_service import export_users_to_excel
from services.leaderboard_service import format_leaderboard


@router.message(Command("stats"))
@router.message(F.text == BTN_ADMIN_STATS)
async def admin_stats(message: Message, db: Database, state: FSMContext) -> None:
    """Batafsil statistika va tahlilni ko'rsatadi."""
    await state.clear()
    total = await db.users.get_total_count()
    today = await db.users.get_today_count()
    banned = await db.users.get_banned_count()
    top_text = await format_leaderboard(db.users, config.top_n)

    e_stats = await get_emoji(db, "stats")
    e_users = await get_emoji(db, "users")
    e_trophy = await get_emoji(db, "trophy")

    text = (
        f"{e_stats} <b>Batafsil Statistika & Analitika</b>\n\n"
        f"{e_users} Jami ishtirokchilar: <b>{total}</b> ta\n"
        f"📅 Bugun qo'shilganlar: <b>{today}</b> ta\n"
        f"🚫 Bloklanganlar: <b>{banned}</b> ta\n\n"
        f"{e_trophy} <b>Top {config.top_n} Peshqadamlar:</b>\n{top_text}"
    )
    await message.answer(text)


@router.message(Command("chart"))
@router.message(F.text == BTN_ADMIN_CHARTS)
async def admin_chart(message: Message, db: Database, state: FSMContext) -> None:
    """Kunlik ro'yxatdan o'tish dinamikasi grafigini yaratadi va yuboradi."""
    await state.clear()
    e_stats = await get_emoji(db, "stats")
    wait_msg = await message.answer(f"{e_stats} Grafik tayyorlanmoqda, iltimos kuting...")
    try:
        growth_data = await db.users.get_daily_registration_growth()
        chart_file = generate_registration_chart(growth_data)
        await message.answer_photo(
            photo=chart_file,
            caption=f"{e_stats} <b>A'zolar o'sish dinamikasi (Oxirgi 14 kun)</b>"
        )
        await wait_msg.delete()
    except Exception as e:
        await wait_msg.edit_text(f"❌ Grafikni yaratishda xatolik: {e}")


@router.message(Command("excel"))
@router.message(F.text == BTN_ADMIN_EXCEL)
async def admin_excel(message: Message, db: Database, state: FSMContext) -> None:
    """Foydalanuvchilar bazasini Excel formatida eksport qiladi."""
    await state.clear()
    wait_msg = await message.answer("📥 Foydalanuvchilar bazasi Excel formatga o'tkazilmoqda...")
    try:
        users = await db.users.get_all_users_data()
        excel_file = export_users_to_excel(users)
        await message.answer_document(
            document=excel_file,
            caption=f"📁 <b>Foydalanuvchilar bazasi ({len(users)} ta a'zo)</b>"
        )
        await wait_msg.delete()
    except Exception as e:
        await wait_msg.edit_text(f"❌ Excel eksportda xatolik: {e}")


@router.message(Command("winners"))
@router.message(F.text == BTN_ADMIN_WINNERS)
async def announce_winners(message: Message, db: Database, state: FSMContext) -> None:
    """G'oliblar ro'yxatini ko'rsatadi."""
    await state.clear()
    winners = await db.users.get_winners(config.top_n)
    if not winners:
        await message.answer("Hozircha g'oliblar mavjud emas.")
        return

    e_trophy = await get_emoji(db, "trophy")
    e_gift = await get_emoji(db, "gift")

    text_lines = []
    for idx, w in enumerate(winners, 1):
        username = f" (@{w['username']})" if w.get('username') else ""
        phone = f" - 📞 {w['phone']}" if w.get('phone') else ""
        text_lines.append(f"{idx}. <b>{w['full_name']}</b>{username}{phone} — <b>{w['points']}</b> ball")

    winners_str = "\n".join(text_lines)
    await message.answer(
        f"{e_trophy} <b>G'oliblar ro'yxati — {config.contest_name}</b>\n"
        f"{e_gift} Sovrin: <b>{config.prize_text}</b>\n\n"
        f"{winners_str}"
    )