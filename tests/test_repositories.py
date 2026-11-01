"""
test_user_repo.py — UserRepository testlari.

Testlar qamrovi:
  - Foydalanuvchi ro'yxatdan o'tishi
  - Takroriy ro'yxatdan o'tish oldini olish
  - O'ziga referral qila olmaslik
  - Ro'yxatdan o'tmagan referrer e'tiborga olinmasligi
  - Ball hisoblash (start + referral)
  - Leaderboard tartibi
  - Ban/unban
  - get_user_stats (kombinatsiyalangan so'rov)
"""
from __future__ import annotations

import pytest
from database.repositories import UserRepository
from tests.conftest import SAMPLE_REFERRER, SAMPLE_USER


# ─── Registration ─────────────────────────────────────────────────────────────

class TestRegistration:
    async def test_new_user_registers_successfully(self, user_repo: UserRepository):
        """Yangi foydalanuvchi muvaffaqiyatli ro'yxatdan o'tishi kerak."""
        is_new, referrer = await user_repo.register_and_credit_referrer(
            user_id=SAMPLE_USER["user_id"],
            full_name=SAMPLE_USER["full_name"],
            username=SAMPLE_USER["username"],
            phone=SAMPLE_USER["phone"],
            referrer_id=None,
            start_points=5,
            referral_points=1,
        )
        assert is_new is True
        assert referrer is None

        # DB dan tekshiruv
        user = await user_repo.get_by_id(SAMPLE_USER["user_id"])
        assert user is not None
        assert user["registered"] == 1
        assert user["points"] == 5
        assert user["full_name"] == SAMPLE_USER["full_name"]
        assert user["phone"] == SAMPLE_USER["phone"]

    async def test_duplicate_registration_returns_false(self, user_repo: UserRepository):
        """Ikkinchi marta ro'yxatdan o'tish False qaytarishi kerak."""
        kwargs = dict(
            user_id=SAMPLE_USER["user_id"],
            full_name=SAMPLE_USER["full_name"],
            username=SAMPLE_USER["username"],
            phone=SAMPLE_USER["phone"],
            referrer_id=None,
            start_points=5,
            referral_points=1,
        )
        await user_repo.register_and_credit_referrer(**kwargs)
        is_new, referrer = await user_repo.register_and_credit_referrer(**kwargs)

        assert is_new is False
        assert referrer is None

    async def test_points_not_doubled_on_duplicate(self, user_repo: UserRepository):
        """Ikkinchi marta ro'yxatdan o'tganda ballar ikki barobar bo'lmasligi kerak."""
        kwargs = dict(
            user_id=SAMPLE_USER["user_id"],
            full_name=SAMPLE_USER["full_name"],
            username=None,
            phone=SAMPLE_USER["phone"],
            referrer_id=None,
            start_points=5,
            referral_points=1,
        )
        await user_repo.register_and_credit_referrer(**kwargs)
        await user_repo.register_and_credit_referrer(**kwargs)

        user = await user_repo.get_by_id(SAMPLE_USER["user_id"])
        assert user["points"] == 5  # 5, 10 emas!


# ─── Referral Logic ───────────────────────────────────────────────────────────

class TestReferralLogic:
    async def _register_referrer(self, user_repo: UserRepository) -> None:
        """Referrer ni avval ro'yxatdan o'tkazish yordamchi metod."""
        await user_repo.register_and_credit_referrer(
            user_id=SAMPLE_REFERRER["user_id"],
            full_name=SAMPLE_REFERRER["full_name"],
            username=SAMPLE_REFERRER["username"],
            phone=SAMPLE_REFERRER["phone"],
            referrer_id=None,
            start_points=5,
            referral_points=1,
        )

    async def test_valid_referral_credits_referrer(self, user_repo: UserRepository):
        """To'g'ri referral bilan referrer ball olishi kerak."""
        await self._register_referrer(user_repo)

        is_new, valid_referrer = await user_repo.register_and_credit_referrer(
            user_id=SAMPLE_USER["user_id"],
            full_name=SAMPLE_USER["full_name"],
            username=SAMPLE_USER["username"],
            phone=SAMPLE_USER["phone"],
            referrer_id=SAMPLE_REFERRER["user_id"],
            start_points=5,
            referral_points=1,
        )

        assert is_new is True
        assert valid_referrer == SAMPLE_REFERRER["user_id"]

        # Referrerning ballari oshdi: 5 (boshlang'ich) + 1 (referral) = 6
        referrer = await user_repo.get_by_id(SAMPLE_REFERRER["user_id"])
        assert referrer["points"] == 6

    async def test_self_referral_is_rejected(self, user_repo: UserRepository):
        """Foydalanuvchi o'ziga referral qila olmasligi kerak."""
        user_id = SAMPLE_USER["user_id"]
        is_new, valid_referrer = await user_repo.register_and_credit_referrer(
            user_id=user_id,
            full_name=SAMPLE_USER["full_name"],
            username=SAMPLE_USER["username"],
            phone=SAMPLE_USER["phone"],
            referrer_id=user_id,  # o'zini ko'rsatyapti!
            start_points=5,
            referral_points=1,
        )

        assert is_new is True
        assert valid_referrer is None  # o'z-o'ziga referral rad etilgan

        user = await user_repo.get_by_id(user_id)
        assert user["points"] == 5  # faqat start_points, referral_points yo'q

    async def test_unregistered_referrer_is_ignored(self, user_repo: UserRepository):
        """Ro'yxatdan o'tmagan referrer e'tiborga olinmasligi kerak."""
        # SAMPLE_REFERRER ro'yxatdan o'tkazilmagan!
        is_new, valid_referrer = await user_repo.register_and_credit_referrer(
            user_id=SAMPLE_USER["user_id"],
            full_name=SAMPLE_USER["full_name"],
            username=SAMPLE_USER["username"],
            phone=SAMPLE_USER["phone"],
            referrer_id=SAMPLE_REFERRER["user_id"],  # DB da yo'q
            start_points=5,
            referral_points=1,
        )

        assert is_new is True
        assert valid_referrer is None  # ro'yxatdan o'tmagan referrer rad etilgan

    async def test_referral_count(self, user_repo: UserRepository):
        """Referral soni to'g'ri hisoblanishi kerak."""
        await self._register_referrer(user_repo)

        # 3 ta user referrer orqali ro'yxatdan o'tadi
        for i in range(3):
            await user_repo.register_and_credit_referrer(
                user_id=300000 + i,
                full_name=f"Test User {i}",
                username=None,
                phone=f"+99890000000{i}",
                referrer_id=SAMPLE_REFERRER["user_id"],
                start_points=5,
                referral_points=1,
            )

        count = await user_repo.get_referral_count(SAMPLE_REFERRER["user_id"])
        assert count == 3


# ─── Points & Leaderboard ─────────────────────────────────────────────────────

class TestLeaderboard:
    async def _register_users(self, user_repo: UserRepository) -> None:
        """Leaderboard testlari uchun bir nechta user yaratadi."""
        users = [
            (111, "Aziz", 50),
            (222, "Bobur", 30),
            (333, "Jasur", 80),
            (444, "Doniyor", 10),
        ]
        for uid, name, pts in users:
            await user_repo.register_and_credit_referrer(
                user_id=uid,
                full_name=name,
                username=None,
                phone=f"+9989000{uid}",
                referrer_id=None,
                start_points=pts,
                referral_points=1,
            )

    async def test_leaderboard_sorted_by_points_desc(self, user_repo: UserRepository):
        """Leaderboard ballar bo'yicha kamayib tartiblangan bo'lishi kerak."""
        await self._register_users(user_repo)

        rows = await user_repo.get_leaderboard(limit=10)
        points = [r["points"] for r in rows]
        assert points == sorted(points, reverse=True)

    async def test_leaderboard_respects_limit(self, user_repo: UserRepository):
        """Leaderboard limit parametrini hurmat qilishi kerak."""
        await self._register_users(user_repo)

        rows = await user_repo.get_leaderboard(limit=2)
        assert len(rows) == 2
        assert rows[0]["full_name"] == "Jasur"   # 80 ball
        assert rows[1]["full_name"] == "Aziz"    # 50 ball

    async def test_total_count(self, user_repo: UserRepository):
        """Jami ishtirokchilar soni to'g'ri qaytarilishi kerak."""
        await self._register_users(user_repo)
        count = await user_repo.get_total_count()
        assert count == 4

    async def test_get_user_stats_rank(self, user_repo: UserRepository):
        """get_user_stats eng yuqori ballga ega userga 1-o'rin berishi kerak."""
        await self._register_users(user_repo)

        # Jasur 80 ball bilan birinchi bo'lishi kerak
        stats = await user_repo.get_user_stats(333)
        assert stats is not None
        assert stats["rank"] == 1
        assert stats["points"] == 80

    async def test_get_user_stats_lower_rank(self, user_repo: UserRepository):
        """Eng kam ballga ega user oxirgi o'rinda bo'lishi kerak."""
        await self._register_users(user_repo)

        # Doniyor 10 ball bilan 4-o'rinda
        stats = await user_repo.get_user_stats(444)
        assert stats["rank"] == 4


# ─── Ban / Unban ──────────────────────────────────────────────────────────────

class TestBanSystem:
    async def test_banned_user_excluded_from_leaderboard(self, user_repo: UserRepository):
        """Ban qilingan foydalanuvchi leaderboardda ko'rsatilmasligi kerak."""
        # 2 ta user ro'yxatdan o'tadi
        for uid, name, pts in [(111, "Aziz", 100), (222, "Bobur", 50)]:
            await user_repo.register_and_credit_referrer(
                user_id=uid, full_name=name, username=None,
                phone=f"+9989{uid}", referrer_id=None,
                start_points=pts, referral_points=1,
            )

        # Azizni ban qilish
        await user_repo.set_banned(111, True)

        rows = await user_repo.get_leaderboard(limit=10)
        user_ids = [r["user_id"] for r in rows]
        assert 111 not in user_ids  # ban qilingan ko'rsatilmasin
        assert 222 in user_ids

    async def test_unban_restores_user_to_leaderboard(self, user_repo: UserRepository):
        """Unban qilingan foydalanuvchi yana leaderboardga qaytishi kerak."""
        await user_repo.register_and_credit_referrer(
            user_id=111, full_name="Aziz", username=None,
            phone="+998901234567", referrer_id=None,
            start_points=100, referral_points=1,
        )

        await user_repo.set_banned(111, True)
        await user_repo.set_banned(111, False)

        rows = await user_repo.get_leaderboard(limit=10)
        user_ids = [r["user_id"] for r in rows]
        assert 111 in user_ids

    async def test_banned_referral_not_counted(self, user_repo: UserRepository):
        """Ban qilingan taklif qilganlar referral_count da hisoblanmasligi kerak."""
        # Referrer ro'yxatdan o'tadi
        await user_repo.register_and_credit_referrer(
            user_id=SAMPLE_REFERRER["user_id"],
            full_name=SAMPLE_REFERRER["full_name"],
            username=None, phone=SAMPLE_REFERRER["phone"],
            referrer_id=None, start_points=5, referral_points=1,
        )
        # Referral orqali kiritilgan user ro'yxatdan o'tadi
        await user_repo.register_and_credit_referrer(
            user_id=SAMPLE_USER["user_id"],
            full_name=SAMPLE_USER["full_name"],
            username=None, phone=SAMPLE_USER["phone"],
            referrer_id=SAMPLE_REFERRER["user_id"],
            start_points=5, referral_points=1,
        )

        count_before = await user_repo.get_referral_count(SAMPLE_REFERRER["user_id"])
        assert count_before == 1

        # Referral qilingan user ban qilinadi
        await user_repo.set_banned(SAMPLE_USER["user_id"], True)

        count_after = await user_repo.get_referral_count(SAMPLE_REFERRER["user_id"])
        assert count_after == 0  # ban qilingan hisoblanmaydi


# ─── Settings Repository ──────────────────────────────────────────────────────

class TestSettingsRepo:
    async def test_set_and_get(self, settings_repo):
        """Sozlama yozib o'qish to'g'ri ishlashi kerak."""
        await settings_repo.set("test_key", "test_value")
        result = await settings_repo.get("test_key")
        assert result == "test_value"

    async def test_default_value_when_missing(self, settings_repo):
        """Mavjud bo'lmagan kalit uchun default qaytarilishi kerak."""
        result = await settings_repo.get("non_existent_key", default="DEFAULT")
        assert result == "DEFAULT"

    async def test_overwrite_existing_setting(self, settings_repo):
        """Mavjud sozlamani qayta yozish to'g'ri ishlashi kerak."""
        await settings_repo.set("key", "old_value")
        await settings_repo.set("key", "new_value")
        result = await settings_repo.get("key")
        assert result == "new_value"


# ─── Channel Repository ───────────────────────────────────────────────────────

class TestChannelRepo:
    async def test_add_and_list_channel(self, channel_repo):
        """Kanal qo'shish va ro'yxatini olish to'g'ri ishlashi kerak."""
        await channel_repo.add("@test_channel", "Test Kanal", "https://t.me/test")
        channels = await channel_repo.get_all()
        assert len(channels) == 1
        assert channels[0]["chat_id"] == "@test_channel"
        assert channels[0]["title"] == "Test Kanal"

    async def test_remove_existing_channel(self, channel_repo):
        """Mavjud kanalni o'chirish True qaytarishi kerak."""
        await channel_repo.add("-1001234567890", "Kanal 1", None)
        removed = await channel_repo.remove("-1001234567890")
        assert removed is True

        channels = await channel_repo.get_all()
        assert len(channels) == 0

    async def test_remove_nonexistent_channel(self, channel_repo):
        """Mavjud bo'lmagan kanalni o'chirish False qaytarishi kerak."""
        removed = await channel_repo.remove("@yoq_kanal")
        assert removed is False

    async def test_upsert_channel_updates_existing(self, channel_repo):
        """Mavjud kanal uchun add() ma'lumotlarni yangilashi kerak."""
        await channel_repo.add("@chan", "Eski nom", None)
        await channel_repo.add("@chan", "Yangi nom", "https://t.me/invite/abc")
        channels = await channel_repo.get_all()
        assert len(channels) == 1
        assert channels[0]["title"] == "Yangi nom"
        assert channels[0]["invite_link"] == "https://t.me/invite/abc"


# ─── Admin Repository ────────────────────────────────────────────────────────

class TestAdminRepo:
    async def test_add_and_is_admin(self, db):
        """Admin qo'shish va tekshirish to'g'ri ishlashi kerak."""
        await db.admins.add(111222333, "new_admin", "Test Admin")
        assert await db.admins.is_admin(111222333) is True
        assert await db.admins.is_admin(999000111) is False

        admins = await db.admins.get_all()
        assert len(admins) == 1
        assert admins[0]["user_id"] == 111222333
        assert admins[0]["username"] == "new_admin"

    async def test_remove_admin(self, db):
        """Adminni o'chirish to'g'ri ishlashi kerak."""
        await db.admins.add(111222333, "new_admin", "Test Admin")
        removed = await db.admins.remove(111222333)
        assert removed is True
        assert await db.admins.is_admin(111222333) is False

        removed_again = await db.admins.remove(111222333)
        assert removed_again is False
