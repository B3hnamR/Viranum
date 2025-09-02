# Numiran Telegram Bot – Roadmap و طرح فنی

نسخه: 0.1 (Phase Planning)

هدف: ساخت یک ربات تلگرامی حرفه‌ای، API-Based، مقیاس‌پذیر و چندزبانه (FA/EN/RU) برای خرید و مدیریت شماره‌های مجازی (موقت و دائمی) از Numberland با زیرساخت Docker.

منابع:
- Numberland API Summary: api.md
- مستندات اصلی: Info.md


## 1) معماری سامانه
- Bot (Aiogram 3.x, Python 3.11): مدیریت دیالوگ‌ها، کیبوردها، i18n، منطق سفارش.
- Service Layer: کلاینت Numberland (HTTP), مدیریت خطا/Throttle/Retry.
- Data Layer (PostgreSQL): کاربران، سفارش‌ها، تراکنش‌های کیف پول، تنظیمات قیمت‌گذاری، لاگ وضعیت‌ها.
- Cache/Queue (Redis): ذخیره موقت وضعیت‌ها، Rate limiting، صف پایش وضعیت شماره.
- Payments: Top-up کیف پول (MVP: دستی/کد شارژ داخلی؛ فاز بعد: درگاه پرداخت).
- Observability: Logging ساختاریافته، Metrics/Healthchecks، (اختیاری: Sentry).
- Containerization: Docker + docker-compose برای bot, db, redis, (اختیاری pgadmin).

Deployment اولیه: Long polling. فاز بعد: Webhook پشت Reverse Proxy در صورت نیاز.


## 2) ساختار پوشه‌ها (Plan)
پس از تایید این Roadmap، اسکلت پروژه به این ساختار ساخته خواهد شد:

```
Numiran/
├─ api.md                        # خلاصه API Numberland (موجود)
├─ ROADMAP.md                    # این فایل
├─ docker-compose.yml            # Orchestration (bot, db, redis)
├─ .env.example                  # نمونه تنظیمات محیطی
├─ Makefile                      # دستورات متداول توسعه/دیپلوی
├─ README.md                     # راهنمای اجرا و توسعه
├─ infra/
│  ├─ Dockerfile                 # تصویر bot
│  ├─ alembic.ini                # تنظیمات Alembic
│  └─ migrations/                # فایل‌های مهاجرت دیتابیس
├─ src/
│  ├─ app/
│  │  ├─ main.py                 # Entry. start bot
│  │  ├─ config.py               # پیکربندی و validation (.env)
│  │  ├─ db.py                   # sessionmaker, engine
│  │  ├─ i18n.py                 # تنظیم i18n (fa/en/ru)
│  │  ├─ middlewares/            # logging, i18n, rate-limit
│  │  ├─ keyboards/              # reply/inline keyboards
│  │  ├─ handlers/               # ماژول‌های هندلر هر فلو
│  │  │  ├─ start.py
│  │  │  ├─ language.py
│  │  │  ├─ catalog.py           # انتخاب سرویس/کشور/اپراتور
│  │  │  ├─ order_temp.py        # شماره عادی (getnum/checkstatus/...)
│  │  │  ├─ order_perm.py        # شماره دائمی (spnumbers...)
│  │  │  ├─ wallet.py            # کیف پول، شارژ، تاریخچه
│  │  │  ├─ admin.py             # ابزارهای مدیریتی
│  │  │  └─ support.py           # راهنما/FAQ/تیکت
│  │  ├─ services/
│  │  │  ├─ numberland_client.py # فراخوان‌های API + خطاها
│  │  │  ├─ pricing.py           # قوانین قیمت‌گذاری/سود
│  │  │  └─ billing.py           # شارژ کیف پول/تراکنش‌ها
│  │  ├─ repositories/
│  │  │  ├─ users.py
│  │  │  ├─ orders.py
│  │  │  ├─ wallet.py
│  │  │  └─ settings.py
│  │  ├─ models/                 # SQLAlchemy models
│  │  ├─ schemas/                # Pydantic DTOs
│  │  └─ utils/
│  │     ├─ enums.py             # Result codes/state mapping
│  │     ├─ cache.py
│  │     └─ logger.py
│  └─ locales/
│     ├─ fa/LC_MESSAGES/bot.po   # پیام‌ها/کیبوردها فارسی
│     ├─ en/LC_MESSAGES/bot.po   # انگلیسی
│     └─ ru/LC_MESSAGES/bot.po   # روسی
└─ tests/
   ├─ unit/
   └─ integration/
```


## 3) متغیرهای محیطی (env)
- BOT_TOKEN=
- ADMIN_IDS= "12345,67890"
- NUMBERLAND_API_KEY=
- DB_DSN= "postgresql+psycopg://user:pass@db:5432/numiran"
- REDIS_DSN= "redis://redis:6379/0"
- BOT_MODE= "polling" | "webhook"
- BASE_MARKUP_PERCENT= e.g. 20
- MARKUP_ROUND_TO= e.g. 100 (ریال/تومان)
- LOCALE_DEFAULT= fa


## 4) جریان کار کاربر (UX Flows) و دکمه‌ها
همه مراحل با دکمه‌های ربات هدایت می‌شوند. ساختار کیبوردها از ابتدا تا انتها:

- منوی اصلی:
  - خرید شماره عادی
  - خرید شماره دائمی
  - کیف پول (موجودی، شارژ، تاریخچه)
  - راهنما و پشتیبانی
  - تنظیمات زبان

- خرید شماره عادی (Temporary):
  1) انتخاب سرویس (Inline Pagination از getservice)
  2) انتخ��ب کشور (Inline Pagination از getcountry)
  3) انتخاب اپراتور (1..4, any, min) + نمایش قیمت/موجودی از getinfo
  4) تایید خرید (نمایش Amount، TIME و قابلیت repeat)
  5) نمایش شماره خریداری‌شده + شروع پایش وضعیت (checkstatus)
  6) دکمه‌ها: «لغو» (cancelnumber)، «کد مجدد» (repeat)، «بستن» (closenumber)
  7) اعلان دریافت کد (RESULT=2) و نمایش CODE

- خرید شماره دائمی (Special):
  - مشاهده لیست (spnumberslist/spnumberstree) با فیلتر نوع (not/half/fully round)
  - نمایش قیمت و تایید خرید (در صورت پشتیبانی)
  - نمایش اطلاعات شماره خریداری‌شده

- کیف پول:
  - نمایش موجودی
  - شارژ کیف پول (MVP: کد شارژ داخلی/اداری – فاز بعد درگاه پرداخت)
  - تاریخچه تراکنش‌ها

- تنظیمات زبان:
  - فارسی / English / Русский

- راهنما و پشتیبانی:
  - FAQ، قوانین استفاده، محدودیت‌ها (50 RPS)، سیاست بازگشت وجه
  - لینک پشتیبانی/تیکت


## 5) قابلیت‌ها (Backlog Features)
- کاربر:
  - ورود/ثبت‌نام خودکار بر پایه Telegram ID
  - انتخاب زبان (fa/en/ru) و ذخیره ترجیح کاربر
  - مرور کاتالوگ سرویس/کشور/اپراتور با Pagination
  - مشاهده قیمت و موجودی به‌روز (getinfo)
  - خرید شماره عادی (getnum) و مدیریت چرخه حیات (checkstatus / cancel / repeat / close)
  - اعلان لحظه‌ای دریافت کد
  - خرید شماره دائمی (spnumbers...)
  - کیف پول: موجودی، شارژ، تاریخچه و بازگشت وجه‌های خودکار
  - اطلاع‌رسانی درباره انقضای TIME

- مدیریت/ادمین:
  - گزارش فروش/تراکنش‌ها
  - broadcast پیام
  - قوانین قیمت‌گذاری پویا (global, per service/country/operator)
  - مسدودسازی کاربر متخلف

- سیستمی:
  - Rate limit و Queue برای رعایت 50 RPS
  - Cache داده‌های ثابت (countries/services) + refresh دوره‌ای
  - Logging ساختاریافته و Trace ID
  - تست‌های واحد و یکپارچه با Mock Numberland


## 6) مدل داده (خلاصه)
- users(id, tg_id, language, created_at, last_seen)
- wallets(user_id, balance)
- wallet_transactions(id, user_id, type: credit/debit, amount, ref, meta, created_at)
- orders(id, user_id, kind: temp|perm, numberland_id, service_id, country_id, operator, number, areacode, amount, repeat, time_span, state, created_at, updated_at)
- order_status_logs(order_id, result_code, code, description, created_at)
- pricing_rules(id, scope: global/service/country/operator, margin_percent, min_margin, round_to, active)
- settings(key, value)


## 7) قیمت‌گذاری و سود
- Base price = amount از Numberland
- Markup Rule Chain (به ترتیب خاص):
  - Rule خاص (service+country+operator) اگر بود
  - Rule سطح سرویس/کشور
  - Rule سراسری (DEFAULT)
- محاسبه: price = round_to(base * (1 + margin%), round_to)
- حداقل سود: اگر price - base < min_margin، price += (min_margin - diff)
- نمایش قیمت نهایی به کاربر پیش از خرید. کسر از کیف پول کاربر در تایید خرید.
- Refund: در سناریوهای لغو/مسدودی در وضعیت مجاز و عدم دریافت کد، شارژ به کیف پول برمی‌گردد.


## 8) چندزبانه (FA/EN/RU)
- i18n با gettext/aiogram-i18n. فایل‌های bot.po برای fa/en/ru.
- تشخیص اولیه از language_code تلگرام + امکان تغییر دستی در تنظیمات.
- همه متن‌ها/کیبوردها با کلید i18n. هیچ متن هاردکد نشده.


## 9) Docker و استق��ار
- docker-compose.yml شامل:
  - bot: Python 3.11-slim, user non-root, healthcheck
  - db: postgres:15 + volume
  - redis: latest + healthcheck
  - (اختیاری) pgadmin
- شبکه داخلی compose. Env از .env
- لاگ‌ها stdout (json)
- توسعه: hot-reload (watchfiles) در حالت dev


## 10) تست و کیفیت
- Unit tests: services (numberland_client, pricing), repositories، handlers (با Bot test context)
- Integration: پایش وضعیت با Mock Server
- Lint/Format: ruff + black
- CI (Phase بعد): GitHub Actions


## 11) ریسک‌ها و کنترل‌ها
- محدودیت نرخ 50 RPS: پیاده‌سازی throttle مرکزی + batching + backoff
- نوسان موجودی/قیمت: نمایش لحظه‌ای از getinfo و اعتبارسنجی قبل از خرید
- پایداری API خارجی: retry با jitter، timeout و circuit-breaker ساده
- امنیت: نگهداری apikey و توکن‌ها در env، ماسک در لاگ


## 12) مراحل اجرایی (Roadmap)
- Phase 0 – آماده‌سازی
  - [x] تنظیم خلاصه API (api.md)
  - [x] تدوین Roadmap (این فایل)
  - [ ] تایید طرح و نیازمندی‌ها

- Phase 1 – اسکلت پروژه و Docker
  - [ ] ایجاد ساختار پوشه‌ها و فایل‌های پایه (src/، infra/، tests/، README، Makefile، .env.example)
  - [ ] Dockerfile و docker-compose.yml (bot/db/redis)
  - [ ] پیکربندی i18n (fa/en/ru) و کیبوردهای اولیه (منوی اصلی)

- Phase 2 – لایه سرویس‌ها و مدل داده
  - [ ] SQLAlchemy models + migrations (users, wallets, orders, ...)
  - [ ] numberland_client با خطاها، retry، throttle
  - [ ] repositories و قیمت‌گذاری (pricing.py)

- Phase 3 – فلوهای کاربری (Temporary Numbers)
  - [ ] کاتالوگ سرویس/کشور/اپراتور (getservice/getcountry/getinfo)
  - [ ] خرید (getnum) + پیگیری وضعیت (checkstatus) + عملیات (cancel/repeat/close)
  - [ ] اعلان کد و مدیریت انقضا (TIME)

- Phase 4 – کیف پول و تراکنش‌ها
  - [ ] موجودی، شارژ (MVP: کد شارژ داخلی)، تاریخچه
  - [ ] بازگشت وجه خودکار در سنار��وهای مجاز

- Phase 5 – شماره دائمی و مدیریت
  - [ ] spnumberslist/tree و خرید/نمایش
  - [ ] پنل ادمین ساده داخل ربات + گزارش‌ها

- Phase 6 – کیفیت، لاگ و انتشار
  - [ ] تست‌های واحد و ی��پارچه، بهینه‌سازی
  - [ ] مانیتورینگ و Healthcheck
  - [ ] مستندسازی نهایی و انتشار


## 13) تحویل‌ها
- سورس‌کد کامل با ساختار حرفه‌ای
- پکیج Docker قابل اجرا (compose up)
- مستندات اجرا و پیکربندی (README)
- پوشش تست حداقلی روی سرویس‌های کلیدی


---
یادداشت: پس از تایید این Roadmap، در فاز بعد اسکلت پوشه‌ها و فایل‌های اصلی (Docker/Compose، src و i18n و ...) ایجاد و Commited خواهد شد تا توسعه تدریجی فازهای بعدی انجام شود.

_____________________________________________________

گزارش اولیه (قبل از شروع اجرا)

خلاصه طرح فنی

زبان/فریم‌ورک: Python 3.11، Aiogram 3.x (async)، SQLAlchemy + Alembic
زیرساخت: Docker و docker-compose (bot + PostgreSQL + Redis)
معماری: Bot (هندلرها و کیبوردها) + Service Layer (کلاینت Numberland) + Data Layer (Postgres) + Cache/Queue (Redis) + Observability (لاگ ساختاریافته، healthcheck)
الگوی توسعه: API-Based کامل با مدیریت خطا/Throttle/Retry و i18n سه‌زبانه (FA/EN/RU)
خلاصه و دسته‌بندی API: در فایل api.md آماده شده است
Roadmap و طرح فنی: فایل ROADMAP.md ایجاد شد و شامل معماری، ساختار پوشه‌ها، Docker plan، جریان‌ها، قیمت‌گذاری، چندزبانه و مراحل اجرایی است
ساختار پوشه‌ها (طراحی)

ریشه پروژه:
api.md: خلاصه Numberland API
ROADMAP.md: طرح فنی و مراحل
docker-compose.yml: ارکستریشن سرویس‌ها (bot، db، redis)
.env.example: نمونه تنظیمات محیطی
Makefile: دستورات توسعه/استقرار
README.md: راهنمای اجرا
infra/:
Dockerfile، alembic.ini، migrations/
src/app/:
main.py (entrypoint)، config.py، db.py، i18n.py
middlewares/، keyboards/، handlers/ (start، language، catalog، order_temp، order_perm، wallet، admin، support)
services/ (numberland_client.py، pricing.py، billing.py)
repositories/ (users.py، orders.py، wallet.py، settings.py)
models/، schemas/، utils/ (enums.py، cache.py، logger.py)
src/locales/: fa/en/ru
tests/: unit/ و integration/
Docker و استقرار

docker-compose با سرویس‌های:
bot: تصویر Python 3.11 slim، non-root، healthcheck
db: postgres:15 + volume
redis: latest + healthcheck
توسعه: hot-reload در dev، لاگ‌ها به stdout (JSON)، env از .env
جریان کار کاربر و دکمه‌ها

از ابتدا تا انتها همه مراحل با دکمه‌های ربات هدایت می‌شود:
منوی اصلی:
خرید شماره عادی
خرید شماره دائمی
کیف پول (موجودی، شارژ، تاریخچه)
راهنما و پشتیبانی
تنظیمات زبان
خرید شماره عادی (Temporary):
انتخاب سرویس (InlinePagination از getservice)
انتخاب کشور (InlinePagination از getcountry)
انتخاب اپراتور (1..4، any، min) + نمایش قیمت/موجودی با getinfo
تایید خرید (نمایش Amount، TIME، قابلیت repeat)
نمایش شماره خریداری‌شده + شروع پایش وضعیت (checkstatus)
دکمه‌ها: لغو (cancelnumber)، کد مجدد (repeat)، بستن (closenumber)
اعلان «کد دریافت شد» با نمایش CODE (RESULT=2)
خرید شماره دائمی (Special):
فیلتر نوع شماره (not/half/fully round) از spnumberslist/spnumberstree
نمایش قیمت، تایید خرید، نشان‌دادن اطلاعات شماره خریداری‌شده
کیف پول:
نمایش موجودی
شارژ کیف پول (MVP: کد شارژ داخلی/دستی؛ فاز بعد: درگاه پرداخت)
تاریخچه تراکنش‌ها
تنظیم زبان:
فارسی / English / Русский
راهنما و پشتیبانی:
FAQ، قوانین، محدودیت 50 RPS، سیاست بازگشت وجه، لینک پشتیبانی
قابلیت‌ها (Backlog تحلیلی)

کاربری:
ثبت‌نام خودکار با Telegram ID و انتخاب/تغییر زبان
مرور کاتالوگ سرویس/کشور/اپراتور با Pagination
مشاهده لحظه‌ای قیمت/موجودی (getinfo) و تایید خرید
خرید و مدیریت چرخه حیات شماره عادی (getnum/checkstatus/cancel/repeat/close)
اعلان فوری دریافت کد
خرید و مشاهده شماره‌های دائمی
کیف پول: موجودی، شارژ، تاریخچه، بازگشت وجه خودکار
اعلان یادآوری نزدیک‌شدن به پایان TIME
مدیریتی:
گزارش فروش/تراکنش‌ها
Broadcast
قوانین قیمت‌گذاری پویا (global، per service/country/operator)
مسدودسازی کاربر متخلف
سیستمی:
Token bucket/Throttle مرکزی برای رعایت 50 RPS
Cache داده‌های ثابت و refresh دوره‌ای
Logging ساختاریافته و Trace ID
تست‌های واحد/یکپارچه با Mock Numberland
Circuit-breaker ساده، Timeout و Retry با jitter
سیستم خرید کاربر (پیشنهاد نهایی)

شماره عادی:
کاربر از منوی اصلی وارد خرید می‌شود و قدم‌به‌قدم سرویس، کشور و اپراتور را انتخاب می‌کند
ربات قیمت نهایی را (با سود شما) از روی amount + قوانین قیمت‌گذاری محاسبه و نشان می‌دهد
با تایید خرید و کافی بودن موجودی کیف پول، مبلغ از کیف پول کاربر کسر و خرید انجام می‌شود (getnum)
ربات شماره را نمایش داده و پایش وضعیت با checkstatus را آغاز می‌کند تا کد برسد یا زمان تمام شود
کاربر هر لحظه می‌تواند «لغو»، «کد مجدد» یا «بستن» را از طریق دکمه‌ها انجام دهد
در سناریوهای مجاز، بازگشت وجه به کیف پول اعمال می‌شود
شماره دائمی:
کاربر نوع رُند بودن را فیلتر می‌کند، لیست را می‌بیند، تایید خرید، و اطلاعات شماره خریداری شده به او نمایش داده می‌شود
کیف پول

بله، کیف پول داخلی در نظر گرفته شده:
فاز MVP: افزایش موجودی با کد/روش داخلی و ثبت تراکنش‌ها
فاز بعدی: اتصال به درگاه پرداخت
همه خریدها از کیف پول کاربر کسر می‌شوند و بازگشت وجه‌ها به کیف پول واریز می‌شوند
قیمت‌گذاری و سود

قیمت پایه = amount دریافتی از Numberland
Rule Chain:
Rule خاص (service+country+operator) در صورت وجود
Rule سطح سرویس/کشور
Rule سراسری (DEFAULT)
محاسبه نهایی:
price = round_to(base * (1 + margin%), round_to)
حداقل سود: اگر (price - base) < min_margin, افزایش تا حداقل سود
قیمت نهایی قبل از خرید به کاربر نمایش داده می‌شود
چندزبانه (FA/EN/RU)

پیاده‌سازی i18n با gettext/aiogram-i18n
فایل‌های ترجمه po برای fa/en/ru
انتخاب اولیه زبان از language_code تلگرام + دکمه تغییر در تنظیمات
هیچ متن هاردکد؛ همه پیام‌ها و کیبوردها کلیددار
مدیریت API Numberland

همه فراخوان‌ها GET و پاسخ JSON
محدودیت 50 درخواست در ثانیه رعایت می‌شود (throttle مرکزی + queue + backoff)
mapping کامل خطاها (RESULT < 0) به پیام‌های قابل‌فهم و رفتار مناسب
cache کاتالوگ کشور/سرویس با refresh دوره‌ای
مستندات ایجادشده

api.md: خلاصه کامل Numberland API
ROADMAP.md: معماری، ساختار پوشه‌ها، Docker، جریان‌ها، کیف پول، قیمت‌گذاری، چندزبانه و مراحل اجرایی
گام بعدی

پس از این گزارش، مرحله بعد ایجاد اسکلت پروژه و فایل‌های Docker/Compose، .env.example، و پایه i18n و منوی اصلی است.