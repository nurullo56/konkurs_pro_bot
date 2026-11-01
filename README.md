# 🏆 Konkurs Bot Pro

> **Referral + ball tizimiga asoslangan Telegram konkurs boti.**  
> Bitta kodbaza — ko'p instansiya, PostgreSQL/SQLite dual qo'llab-quvvatlash, Redis FSM va anti-flood.

![CI](https://github.com/YOUR_USERNAME/konkurs_bot_pro/actions/workflows/ci.yml/badge.svg)
![Coverage](https://img.shields.io/badge/coverage-77%25-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![aiogram](https://img.shields.io/badge/aiogram-3.x-blue)

---

## 📋 Mundarija

- [Xususiyatlar](#-xususiyatlar)
- [Arxitektura](#-arxitektura)
- [O'rnatish](#-ornatish)
- [Sozlash (.env)](#-sozlash-env)
- [Ishga tushirish](#-ishga-tushirish)
- [Ko'p instansiya (SaaS)](#-kop-instansiya-saas)
- [Admin buyruqlari](#-admin-buyruqlari)
- [Ro'yxatdan o'tish oqimi](#-royxatdan-otish-oqimi)
- [Ball va reyting mantiqi](#-ball-va-reyting-mantiqi)
- [Test va qamrov](#-test-va-qamrov)
- [CI/CD](#-cicd)

---

## ✨ Xususiyatlar
 
| Xususiyat | Tavsif |
|---|---|
| 🔗 **Referral tizimi** | Har bir taklif uchun referer ball oladi |
| 📢 **Broadcast** | Hammaga / faqat g'oliblarga / bitta userga xabar |
| 📊 **Statistika** | Jami, bugungi, ban qilinganlar soni + TOP N |
| 📈 **Grafik** | Oxirgi 14 kunlik o'sish dinamikasi (matplotlib) |
| 📥 **Excel export** | Barcha foydalanuvchilar .xlsx formatda |
| 👑 **Premium Emoji** | Telegram Premium custom emoji boshqaruvi |
| 🔄 **Dual DB** | PostgreSQL (production) / SQLite (development) |
| ⚡ **Redis FSM** | Tez va izolyatsiyalangan holatlar (fallback: MemoryStorage) |
| 🛡️ **Anti-flood** | Redis yoki in-memory rate limiting |
| 🚀 **Multi-instance** | PM2 yoki manual PID orqali bir serverda ko'p bot |

---

## 🏗️ Arxitektura

```
konkurs_bot_pro/
│
├── bot.py                   # Kirish nuqtasi — bot, dp, middleware, router
├── config.py                # Sozlamalar (.env dan yuklanadi)
├── deploy.py                # Ko'p instansiya boshqaruvchi script
│
├── database/
│   ├── db.py                # Database wrapper (SQLite + PostgreSQL)
│   └── repositories/
│       ├── base.py          # BaseRepository (SQL placeholder konvertatsiya)
│       ├── user.py          # Foydalanuvchi CRUD, leaderboard, statistika
│       ├── channel.py       # Majburiy kanallar
│       ├── settings.py      # Kalit-qiymat sozlamalar
│       └── join_request.py  # Private kanal join requestlari
│
├── handlers/
│   ├── admin/               # Admin paneli handlerlari
│   │   ├── router.py        # Admin filter (faqat admin_ids)
│   │   ├── broadcast.py     # Xabar tarqatish
│   │   ├── channels.py      # Kanal boshqaruvi
│   │   ├── statistics.py    # Statistika, grafik, Excel
│   │   ├── prizes.py        # Sovg'alar tahrirlash
│   │   ├── rules.py         # Shartlar tahrirlash
│   │   └── emoji.py         # Premium emoji boshqaruvi
│   └── user/
│       ├── registration.py  # /start, kanal tekshiruv, telefon
│       └── menu.py          # Asosiy menyu handlerlari
│
├── keyboards/               # Reply va Inline klaviaturalar
├── middlewares/
│   └── antiflood.py         # Rate limiting middleware
├── services/
│   ├── referral.py          # Ro'yxatdan o'tish + ball berish logikasi
│   ├── subscription.py      # Kanal obunasini tekshirish
│   ├── leaderboard.py       # Matn formatlash
│   ├── chart.py             # matplotlib grafik
│   ├── export.py            # Excel/CSV eksport
│   └── emoji.py             # Premium emoji yordamchi funksiyalar
├── states/                  # FSM holatlari
│
└── tests/                   # Pytest test to'plami (77% qamrov)
    ├── conftest.py
    ├── test_repositories.py
    ├── test_services.py
    ├── test_subscription.py
    └── test_export_chart.py
```

---

## ⚙️ O'rnatish

### Talablar

- Python **3.11+**
- (Ixtiyoriy) PostgreSQL 14+
- (Ixtiyoriy) Redis 6+

### Bosqichlar

```bash
# 1. Repo klonlash
git clone https://github.com/YOUR_USERNAME/konkurs_bot_pro.git
cd konkurs_bot_pro

# 2. Virtual muhit
python -m venv venv

# Windows:
venv\Scripts\activate

# Linux/macOS:
source venv/bin/activate

# 3. Kutubxonalar
pip install -r requirements.txt

# 4. (Test uchun) Dev kutubxonalar
pip install -r requirements-dev.txt
```

---

## 🔧 Sozlash (.env)

`.env.example` faylini `.env` sifatida nusxalang va to'ldiring:

```bash
cp .env.example .env
```

| O'zgaruvchi | Majburiy | Misol | Tavsif |
|---|---|---|---|
| `BOT_TOKEN` | ✅ | `123456:ABC-DEF...` | BotFather tokenı |
| `ADMIN_IDS` | ✅ | `123456789,987654321` | Admin Telegram IDlar (vergul bilan) |
| `CONTEST_NAME` | — | `Pro Konkurs` | Konkurs nomi |
| `PRIZE_TEXT` | — | `2 000 000 so'm` | Sovrin matni |
| `TOP_N` | — | `10` | G'oliblar soni |
| `START_POINTS` | — | `5` | Ro'yxatdagi boshlang'ich ball |
| `REFERRAL_POINTS` | — | `1` | Har bir taklif uchun ball |
| `DB_TYPE` | — | `sqlite` / `postgresql` | Ma'lumotlar bazasi turi |
| `POSTGRES_DSN` | — | `postgresql://user:pass@localhost/db` | PostgreSQL ulanish string |
| `DB_PATH` | — | `contest.db` | SQLite fayl joylashuvi |
| `REDIS_URL` | — | `redis://localhost:6379/0` | Redis (yo'q bo'lsa MemoryStorage) |
| `RATE_LIMIT` | — | `1.5` | Anti-flood (soniyada) |

---

## 🚀 Ishga tushirish

### Oddiy rejim

```bash
python bot.py
```

### PM2 bilan (production)

```bash
pm2 start bot.py --name konkurs_bot --interpreter python3
pm2 save
pm2 startup
```

---

## 🖥️ Ko'p instansiya (SaaS)

Bir serverda bir nechta bot (har biri o'z tokeni va DB si bilan):

```bash
# Yangi mijoz boti qo'shish (interaktiv)
python deploy.py add

# Ro'yxat
python deploy.py list

# Boshqarish
python deploy.py start  client_1
python deploy.py stop   client_1
python deploy.py restart client_1
python deploy.py remove client_1
```

Har bir instansiya `instances/<name>/` papkasida o'z `.env` va `contest.db` fayliga ega.

---

## 👨‍💼 Admin buyruqlari

### Kanal boshqaruvi

```
/add_channel @username
/add_channel -1001234567890
/add_channel @username | Kanal nomi | https://t.me/+invite
/remove_channel @username
/channels
```

> **Eslatma:** Bot barcha qo'shilgan kanallarda **admin** bo'lishi shart.  
> Private kanallar uchun bot avtomatik **Join Request** havolasi yaratadi.

### Statistika va eksport

```
/stats    — Jami ishtirokchilar, bugungi, ban qilinganlar + TOP N
/chart    — 14 kunlik o'sish grafigi (PNG)
/excel    — Barcha foydalanuvchilar (Excel .xlsx)
/winners  — TOP N g'oliblar (ism, username, telefon, ball)
```

### Broadcast

```
/broadcast  — Xabar tarqatish menyusi
             → Hammaga
             → Faqat g'oliblarga (TOP N)
             → Bitta foydalanuvchiga (ID orqali)
```

> **Eslatma:** Bot bloklagan foydalanuvchilar avtomatik `is_banned=1` belgilanadi va keyingi broadcastlarga kiritilmaydi.

### Kontent boshqaruvi

```
/edit_prizes  — Sovg'alar sahifasini tahrirlash (matn yoki rasm+matn)
/edit_rules   — Konkurs shartlarini tahrirlash
```

### Premium Emoji

Admin panelidan botdagi standart emojilar o'rniga Telegram Premium custom emoji o'rnatish mumkin.

---

## 📝 Ro'yxatdan o'tish oqimi

```
/start  (ixtiyoriy: ?start=<referrer_id>)
    │
    ├─► Allaqachon ro'yxatdan o'tganmi? → Asosiy menyu
    │
    ├─► Majburiy kanallarga a'zolikni tekshirish
    │       Bo'sh ro'yxat → o'tkazib yuborish
    │       A'zo emas → havolalar + "A'zo bo'ldim" tugmasi
    │
    └─► Telefon raqam so'rash (reply tugma orqali)
            │
            └─► Atomik ro'yxatdan o'tish:
                  ✅ Foydalanuvchiga START_POINTS ball
                  ✅ Referer bo'lsa → unga REFERRAL_POINTS ball
                  ✅ Referer foydalanuvchiga xabarnoma
                  ✅ Referral havola ko'rsatiladi
```

---

## ⭐ Ball va reyting mantiqi

- Ro'yxatdan o'tishda: **`START_POINTS`** ball (default: 5)
- Har bir muvaffaqiyatli taklif uchun: **`REFERRAL_POINTS`** ball (default: 1)
- Reyting `RANK() OVER (ORDER BY points DESC)` — SQLite 3.25+ va PostgreSQL
- G'oliblar — TOP `TOP_N` (ban qilinganlar hisobga olinmaydi)
- **O'z-o'ziga referral** va **ro'yxatdan o'tmagan referer** — avtomatik rad etiladi

---

## 🧪 Test va qamrov

```bash
# Barcha testlarni ishga tushirish (coverage bilan)
python -m pytest tests/ -v

# Faqat test (covsiz, tez)
python -m pytest tests/ -v --no-cov

# Bitta fayl
python -m pytest tests/test_repositories.py -v

# HTML hisobot
# → htmlcov/index.html ni brauzerda oching
```

### Test qamrovi (77%)

| Modul | Qamrov |
|---|---|
| `services/referral.py` | 100% 🏆 |
| `services/leaderboard.py` | 100% 🏆 |
| `services/chart.py` | 100% 🏆 |
| `services/subscription.py` | 94% ⭐ |
| `services/export.py` | 76% ✅ |
| `middlewares/antiflood.py` | 74% ✅ |
| `database/repositories/*` | 78–89% ✅ |

### Test to'plami (58 ta test)

| Fayl | Testlar | Nima tekshiriladi |
|---|---|---|
| `test_repositories.py` | 22 | Ro'yxat, referral, ban, leaderboard, kanal, sozlama |
| `test_services.py` | 17 | Referral service, leaderboard matn, anti-flood |
| `test_subscription.py` | 9 | Obuna tekshiruv, join request, multi-kanal |
| `test_export_chart.py` | 12 | PNG grafik, Excel/CSV eksport |

---

## 🔄 CI/CD

GitHub Actions orqali har `push` va `pull_request` da avtomatik:

1. ✅ Sintaksis tekshiruvi (`ast.parse`)
2. ✅ Python 3.11 va 3.12 da testlar
3. ✅ Coverage 70%+ tekshiruvi
4. ✅ Coverage hisoboti artifact sifatida saqlanadi

Workflow fayli: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

---

## 📄 Litsenziya

MIT © 2024