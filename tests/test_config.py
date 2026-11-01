from __future__ import annotations

"""
test_config.py — Config validation testlari.

Config.__post_init__ metodi qiymatlarni tekshiradi.
Bu testlar noto'g'ri qiymatlar berilganda xato ko'tarilishini tekshiradi.
"""

import os
from dataclasses import replace

import pytest


# ─── Fixtures & Helpers ───────────────────────────────────────────────────────

def _make_config(**overrides):
    """
    To'g'ri Config obyektini yaratadi va keyin overrides bilan o'zgartiradi.
    Bu Config.load() ni chaqirmasdan, to'g'ridan-to'g'ri Config(**kwargs) yaratadi.
    """
    from config import Config

    base_kwargs = dict(
        bot_token="1234567890:TEST_TOKEN",
        admin_ids=frozenset([123456789]),
        contest_name="Test Konkurs",
        prize_text="1 000 000 so'm",
        top_n=10,
        start_points=5,
        referral_points=1,
        db_type="sqlite",
        postgres_dsn="",
        db_path=":memory:",
        redis_url=None,
        rate_limit=1.5,
        use_webhook=False,
        webhook_url="",
        webhook_path="/webhook",
        webapp_host="0.0.0.0",
        webapp_port=8001,
        webhook_secret="",
    )
    base_kwargs.update(overrides)
    return Config(**base_kwargs)


# ─── Test Cases ───────────────────────────────────────────────────────────────


class TestConfigValidation:
    """Config.__post_init__ validation testlari."""

    def test_valid_config_sqlite(self):
        """To'g'ri SQLite config hech qanday xato ko'tarmasligi kerak."""
        cfg = _make_config()
        assert cfg.db_type == "sqlite"
        assert cfg.rate_limit == 1.5

    def test_valid_config_postgresql(self):
        """To'g'ri PostgreSQL config hech qanday xato ko'tarmasligi kerak."""
        cfg = _make_config(db_type="postgresql", postgres_dsn="postgresql://user:pass@host/db")
        assert cfg.is_postgres if hasattr(cfg, "is_postgres") else True

    def test_invalid_db_type_raises(self):
        """Noto'g'ri DB_TYPE ValueError ko'tarishi kerak."""
        with pytest.raises(ValueError, match="DB_TYPE"):
            _make_config(db_type="mongodb")

    def test_negative_top_n_raises(self):
        """Manfiy TOP_N ValueError ko'tarishi kerak."""
        with pytest.raises(ValueError, match="TOP_N"):
            _make_config(top_n=-5)

    def test_zero_top_n_raises(self):
        """Nol TOP_N ValueError ko'tarishi kerak."""
        with pytest.raises(ValueError, match="TOP_N"):
            _make_config(top_n=0)

    def test_negative_start_points_raises(self):
        """Manfiy START_POINTS ValueError ko'tarishi kerak."""
        with pytest.raises(ValueError, match="START_POINTS"):
            _make_config(start_points=-1)

    def test_negative_referral_points_raises(self):
        """Manfiy REFERRAL_POINTS ValueError ko'tarishi kerak."""
        with pytest.raises(ValueError, match="REFERRAL_POINTS"):
            _make_config(referral_points=-3)

    def test_zero_rate_limit_raises(self):
        """Nol RATE_LIMIT ValueError ko'tarishi kerak."""
        with pytest.raises(ValueError, match="RATE_LIMIT"):
            _make_config(rate_limit=0.0)

    def test_negative_rate_limit_raises(self):
        """Manfiy RATE_LIMIT ValueError ko'tarishi kerak."""
        with pytest.raises(ValueError, match="RATE_LIMIT"):
            _make_config(rate_limit=-1.0)

    def test_webhook_without_url_raises(self):
        """USE_WEBHOOK=true va WEBHOOK_URL bo'sh bo'lsa ValueError ko'tarishi kerak."""
        with pytest.raises(ValueError, match="WEBHOOK_URL"):
            _make_config(
                use_webhook=True,
                webhook_url="",
                webhook_secret="some-secret",
            )

    def test_webhook_without_secret_raises(self):
        """USE_WEBHOOK=true va WEBHOOK_SECRET bo'sh bo'lsa ValueError ko'tarishi kerak."""
        with pytest.raises(ValueError, match="WEBHOOK_SECRET"):
            _make_config(
                use_webhook=True,
                webhook_url="https://example.com",
                webhook_secret="",
            )

    def test_webhook_with_all_settings_valid(self):
        """USE_WEBHOOK=true va barcha sozlamalar to'g'ri bo'lsa xato bo'lmasligi kerak."""
        cfg = _make_config(
            use_webhook=True,
            webhook_url="https://example.com",
            webhook_secret="random-secret-123",
        )
        assert cfg.use_webhook is True
        assert cfg.webhook_url == "https://example.com"
        assert cfg.webhook_secret == "random-secret-123"

    def test_postgres_db_type_aliases(self):
        """'postgres' va 'pg' ham to'g'ri qiymat sifatida qabul qilinishi kerak."""
        for alias in ("postgres", "pg"):
            cfg = _make_config(db_type=alias)
            assert cfg.db_type == alias

    def test_admin_ids_frozenset(self):
        """admin_ids frozenset bo'lishi kerak."""
        cfg = _make_config(admin_ids=frozenset([111, 222]))
        assert isinstance(cfg.admin_ids, frozenset)
        assert 111 in cfg.admin_ids

    def test_empty_admin_ids_raises(self):
        """Bo'sh ADMIN_IDS ValueError ko'tarishi kerak (fail-fast)."""
        with pytest.raises(ValueError, match="ADMIN_IDS"):
            _make_config(admin_ids=frozenset())

    def test_admin_ids_with_one_id_valid(self):
        cfg = _make_config(admin_ids=frozenset([123456789]))
        assert len(cfg.admin_ids) == 1

    def test_redis_url_none(self):
        """redis_url None bo'lsa to'g'ri ishlashi kerak."""
        cfg = _make_config(redis_url=None)
        assert cfg.redis_url is None

    def test_redis_url_string(self):
        """redis_url string bo'lsa to'g'ri saqlaniши kerak."""
        cfg = _make_config(redis_url="redis://localhost:6379/0")
        assert cfg.redis_url == "redis://localhost:6379/0"


class TestConfigLoad:
    """Config.load() muhit o'zgaruvchilaridan to'g'ri yuklashini tekshiradi."""

    def test_load_with_env_vars(self, monkeypatch):
        """Muhit o'zgaruvchilari o'rnatilganida Config.load() to'g'ri ishlashi kerak."""
        monkeypatch.setenv("BOT_TOKEN", "9876543210:TESTTOKEN")
        monkeypatch.setenv("ADMIN_IDS", "111,222,333")
        monkeypatch.setenv("DB_TYPE", "sqlite")
        monkeypatch.setenv("DB_PATH", ":memory:")
        monkeypatch.setenv("REDIS_URL", "")
        monkeypatch.setenv("RATE_LIMIT", "2.0")
        monkeypatch.setenv("TOP_N", "5")
        monkeypatch.setenv("START_POINTS", "10")
        monkeypatch.setenv("REFERRAL_POINTS", "2")
        monkeypatch.setenv("USE_WEBHOOK", "false")
        monkeypatch.setenv("WEBHOOK_URL", "")
        monkeypatch.setenv("WEBHOOK_SECRET", "")
        monkeypatch.setenv("WEBAPP_HOST", "0.0.0.0")
        monkeypatch.setenv("WEBAPP_PORT", "8001")
        monkeypatch.setenv("WEBHOOK_PATH", "/webhook")
        monkeypatch.setenv("CONTEST_NAME", "Test Contest")
        monkeypatch.setenv("PRIZE_TEXT", "500 000 so'm")

        from config import Config
        cfg = Config.load()

        assert cfg.bot_token == "9876543210:TESTTOKEN"
        assert 111 in cfg.admin_ids
        assert 222 in cfg.admin_ids
        assert 333 in cfg.admin_ids
        assert cfg.rate_limit == 2.0
        assert cfg.top_n == 5
        assert cfg.redis_url is None  # Bo'sh string → None

    def test_load_invalid_admin_ids_raises(self, monkeypatch):
        """Noto'g'ri ADMIN_IDS ValueError ko'tarishi kerak."""
        monkeypatch.setenv("ADMIN_IDS", "abc,def")

        from config import Config
        with pytest.raises(ValueError, match="ADMIN_IDS"):
            Config.load()

    def test_load_invalid_rate_limit_raises(self, monkeypatch):
        """Noto'g'ri RATE_LIMIT ValueError ko'tarishi kerak."""
        monkeypatch.setenv("RATE_LIMIT", "not_a_number")
        monkeypatch.setenv("BOT_TOKEN", "123:test")
        monkeypatch.setenv("ADMIN_IDS", "123")

        from config import Config
        with pytest.raises(ValueError, match="RATE_LIMIT"):
            Config.load()
