# 🧠 Loyiha Xotirasi: konkurs_bot_pro

> [!NOTE]
> Ushbu fayl AGY (Antigravity) uchun loyihaning qisqacha kontekst xaritasidir. 
> AGY har safar butun fayllarni qayta titkilamasdan, shu xaritalash orqali loyihani darhol tushunadi.

## 📌 Umumiy Ma'lumot
- **Loyiha nomi**: `konkurs_bot_pro`
- **Loyiha turi**: Python
- **Ildiz yo'li**: `C:\Users\Acer\Downloads\konkurs_bot_pro`

## 📦 Bog'liqliklar va Buyruqlar
- **Python paketlar**: aiogram>=3.18.0,<4.0.0, asyncpg, aiosqlite, redis, python-dotenv, matplotlib, openpyxl, fastapi>=0.115.0, uvicorn>=0.34.0

## 📁 Loyiha Tuzilmasi (Daraxt)
- 📁 **config/**
  - 📄 `__init__.py`
  - 📄 `settings.py`
- 📁 **database/**
  - 📁 **repositories/**
    - 📄 `__init__.py`
    - 📄 `admin_repo.py`
    - 📄 `base_repo.py`
    - 📄 `channel_repo.py`
    - 📄 `join_request_repo.py`
    - 📄 `settings_repo.py`
    - 📄 `user_repo.py`
  - 📄 `__init__.py`
  - 📄 `db.py`
- 📁 **handlers/**
  - 📁 **admin/**
    - 📄 `__init__.py`
    - 📄 `main_panel.py`
    - 📄 `manage_admins.py`
    - 📄 `manage_channels.py`
    - 📄 `manage_emoji.py`
    - 📄 `manage_prizes.py`
    - 📄 `manage_rules.py`
    - 📄 `router.py`
    - 📄 `send_broadcast.py`
    - 📄 `view_statistics.py`
  - 📁 **user/**
    - 📄 `__init__.py`
    - 📄 `menu.py`
    - 📄 `registration.py`
    - 📄 `router.py`
  - 📄 `__init__.py`
- 📁 **instances/**
  - 📁 **Mentorlik_Aziza_1/**
    - 📄 `bot.log`
    - 📄 `bot.pid`
    - 📄 `contest.db`
    - 📄 `contest.db-shm`
    - 📄 `contest.db-wal`
  - 📁 **Mentorlik_Nurulloh_2/**
    - 📄 `bot.log`
    - 📄 `bot.pid`
    - 📄 `contest.db`
    - 📄 `contest.db-shm`
    - 📄 `contest.db-wal`
  - 📄 `_init_.py`
- 📁 **keyboards/**
  - 📁 **admin/**
    - 📄 `__init__.py`
    - 📄 `admin_inline_kb.py`
    - 📄 `admin_reply_kb.py`
  - 📁 **user/**
    - 📄 `__init__.py`
    - 📄 `subscription_kb.py`
    - 📄 `user_kb.py`
  - 📄 `__init__.py`
- 📁 **middlewares/**
  - 📄 `__init__.py`
  - 📄 `antiflood.py`
- 📁 **nginx/**
  - 📄 `default.conf`
  - 📄 `generate_nginx.py`
- 📁 **scripts/**
  - 📄 `backup_db.py`
  - 📄 `deploy.py`
  - 📄 `super_broadcast.py`
- 📁 **services/**
  - 📄 `__init__.py`
  - 📄 `chart_service.py`
  - 📄 `emoji_service.py`
  - 📄 `export_service.py`
  - 📄 `leaderboard_service.py`
  - 📄 `referral_service.py`
  - 📄 `subscription_service.py`
- 📁 **states/**
  - 📄 `__init__.py`
  - 📄 `admin.py`
  - 📄 `registration.py`
- 📁 **tests/**
  - 📄 `__init__.py`
  - 📄 `conftest.py`
  - 📄 `test_config.py`
  - 📄 `test_database.py`
  - 📄 `test_deploy.py`
  - 📄 `test_emoji_service.py`
  - 📄 `test_export_chart.py`
  - 📄 `test_handlers_user.py`
  - 📄 `test_repositories.py`
  - 📄 `test_services.py`
  - 📄 `test_subscription.py`
  - 📄 `test_subscription_kb.py`
- 📁 **utils/**
  - 📄 `__init__.py`
  - 📄 `commands.py`
- 📄 `bot.py`
- 📄 `project_stats.py`
- 📄 `pytest.ini`
- 📄 `README.md`
- 📄 `requirements-dev.txt`
- 📄 `requirements.txt`

## ⚙️ Asosiy Modullar va Vazifalari
<!-- Har bir asosiy fayl yoki modulning vazifasi haqida qisqacha izoh -->
- `(Loyihadagi asosiy fayllar haqida qisqa izohlar shu yerga yoziladi)`

## 🎯 Joriy Holat va Qoidalar
- Kod yozishda to'g'ri UTF-8 va Unicode emojilardan (📦, 🤖, 🎯, 💾, 🛑, ✅) foydalaning.
- Mojibake yoki buzuq harflar yozish qat'iyan taqiqlanadi.
