from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

env_file_path = Path(os.getenv("ENV_FILE", ".env"))
if env_file_path.exists():
    # override=False: subprocess orqali to'g'ridan-to'g'ri uzatilgan
    # env o'zgaruvchilar (deploy.py parse_env_file orqali) ustunlik qiladi.
    load_dotenv(env_file_path, override=False)
else:
    logging.warning(f"ENV file not found: {env_file_path}")


@dataclass(frozen=True, slots=True)
class Config:
    """Bot konfiguratsiyasi — muhit o'zgaruvchilaridan yuklanadi."""

    bot_token: str
    admin_ids: frozenset[int]
    contest_name: str
    prize_text: str
    top_n: int
    start_points: int
    referral_points: int
    db_type: str
    postgres_dsn: str
    db_path: str
    redis_url: Optional[str]
    rate_limit: float
    use_webhook: bool
    webhook_url: str
    webhook_path: str
    webapp_host: str
    webapp_port: int
    webhook_secret: str

    def __post_init__(self) -> None:
        """Konfiguratsiya qiymatlarini tekshirish."""
        valid_db_types = {"sqlite", "postgresql", "postgres", "pg"}
        if self.db_type not in valid_db_types:
            raise ValueError(
                f"DB_TYPE '{self.db_type}' noto'g'ri. "
                f"Quyidagilardan birini tanlang: {valid_db_types}"
            )

        # ✅ FIX #1: ADMIN_IDS majburiy — bo'sh bo'lsa bot ishga tushmasin
        if not self.admin_ids:
            raise ValueError(
                "❌ ADMIN_IDS bo'sh! Kamida bitta admin ID kiritilishi shart.\n"
                "Sabab: ADMIN_IDS bo'sh bo'lsa, admin panel butunlay ishlamaydi "
                "va botni boshqarib bo'lmaydi.\n"
                "Misol: ADMIN_IDS=123456789,987654321 (.env faylida)"
            )

        if self.top_n <= 0:
            raise ValueError(f"TOP_N musbat bo'lishi kerak, lekin {self.top_n} berildi.")

        if self.start_points < 0:
            raise ValueError(
                f"START_POINTS manfiy bo'lishi mumkin emas, lekin {self.start_points} berildi."
            )

        if self.referral_points < 0:
            raise ValueError(
                f"REFERRAL_POINTS manfiy bo'lishi mumkin emas, lekin {self.referral_points} berildi."
            )

        if self.rate_limit <= 0:
            raise ValueError(
                f"RATE_LIMIT musbat bo'lishi kerak, lekin {self.rate_limit} berildi."
            )

        if self.use_webhook:
            if not self.webhook_url:
                raise ValueError(
                    "USE_WEBHOOK=true bo'lsa, WEBHOOK_URL bo'sh bo'lishi mumkin emas."
                )
            if not self.webhook_secret:
                raise ValueError(
                    "USE_WEBHOOK=true bo'lsa, WEBHOOK_SECRET bo'sh bo'lishi mumkin emas. "
                    "Xavfsizlik uchun tasodifiy satr kiriting."
                )

    @classmethod
    def load(cls) -> "Config":
        """
        Muhit o'zgaruvchilaridan Config obyektini yaratadi.
        Type conversion xatolarini ushlaydi va aniq xato xabari ko'rsatadi.
        """
        # ADMIN_IDS
        try:
            raw_admins = os.getenv("ADMIN_IDS", "")
            admin_ids: frozenset[int] = frozenset(
                int(x.strip()) for x in raw_admins.split(",") if x.strip()
            )
        except ValueError as e:
            raise ValueError(
                f"ADMIN_IDS noto'g'ri format: '{raw_admins}'. "
                f"Vergul bilan ajratilgan sonlar bo'lishi kerak. Xato: {e}"
            ) from e

        # TOP_N
        try:
            top_n = int(os.getenv("TOP_N", "10"))
        except ValueError as e:
            raise ValueError(f"TOP_N butun son bo'lishi kerak. Xato: {e}") from e

        # START_POINTS
        try:
            start_points = int(os.getenv("START_POINTS", "5"))
        except ValueError as e:
            raise ValueError(f"START_POINTS butun son bo'lishi kerak. Xato: {e}") from e

        # REFERRAL_POINTS
        try:
            referral_points = int(os.getenv("REFERRAL_POINTS", "1"))
        except ValueError as e:
            raise ValueError(f"REFERRAL_POINTS butun son bo'lishi kerak. Xato: {e}") from e

        # RATE_LIMIT
        try:
            rate_limit = float(os.getenv("RATE_LIMIT", "1.5"))
        except ValueError as e:
            raise ValueError(f"RATE_LIMIT o'nli son bo'lishi kerak. Xato: {e}") from e

        # WEBAPP_PORT
        try:
            webapp_port = int(os.getenv("WEBAPP_PORT", "8001"))
        except ValueError as e:
            raise ValueError(f"WEBAPP_PORT butun son bo'lishi kerak. Xato: {e}") from e

        # REDIS_URL — bo'sh bo'lsa None
        redis_url_raw = os.getenv("REDIS_URL", "").strip()
        redis_url: Optional[str] = redis_url_raw if redis_url_raw else None

        # USE_WEBHOOK
        use_webhook = os.getenv("USE_WEBHOOK", "false").lower().strip() == "true"

        return cls(
            bot_token=os.environ.get("BOT_TOKEN", ""),
            admin_ids=admin_ids,
            contest_name=os.getenv("CONTEST_NAME", "Pro Konkurs"),
            prize_text=os.getenv("PRIZE_TEXT", "2 000 000 so'm"),
            top_n=top_n,
            start_points=start_points,
            referral_points=referral_points,
            db_type=os.getenv("DB_TYPE", "sqlite").lower().strip(),
            postgres_dsn=os.getenv("POSTGRES_DSN", ""),
            db_path=os.getenv("DB_PATH", "contest.db"),
            redis_url=redis_url,
            rate_limit=rate_limit,
            use_webhook=use_webhook,
            webhook_url=os.getenv("WEBHOOK_URL", ""),
            webhook_path=os.getenv("WEBHOOK_PATH", "/webhook"),
            webapp_host=os.getenv("WEBAPP_HOST", "0.0.0.0"),
            webapp_port=webapp_port,
            webhook_secret=os.getenv("WEBHOOK_SECRET", ""),
        )


config = Config.load() 