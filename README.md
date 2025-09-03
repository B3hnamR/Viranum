# Viranum – Telegram Bot (Numberland API)

ربات تلگرامی چندزبانه، داکرایز و API-Based برای دریافت و مدیریت شماره‌های مجازی از Numberland.

- Multi-lang: فارسی، English، Русский
- API: یکپارچه با Numberland v2.php (GET + JSON)
- معماری ماژولار: لایه Bot، لایه Service (کلاینت Numberland)، Cache (Redis)، DB (Postgres – فاز بعد)
- کیف پول داخلی (MVP): مبتنی بر Redis با شارژ دستی و تایید ادمین
- Docker-first: اجرا و استقرار ساده با docker compose


## امکانات کلیدی
- خرید شماره عادی (Temporary):
  - انتخاب سرویس → کشور → اپراتور (1..4، any، min)
  - نمایش قیمت پایه از API و محاسبه قیمت نهایی (markup, rounding, min-profit)
  - خرید (getnum)، نمایش شماره، پایش وضعیت (checkstatus)
  - دکمه‌ها: لغو، کد مجدد، بستن، Refresh
- شماره دائمی (Special):
  - ساختار آماده؛ فاز بعدی: spnumberslist/tree و خرید
- کیف پول داخلی (Redis):
  - نمایش موجودی، تاریخچه تراکنش‌ها (Credit/Debit)
  - شارژ دستی: کاربر مبلغ می‌فرستد، ادمین Approve/Reject می‌کند
- اتصال سریع به Numberland:
  - /balance برای مشاهده موجودی پنل Numberland و تست اتصال
- ابزارهای استقرار:
  - setup.sh برای راه‌اندازی سرور خام
  - u.sh برای Pull + Build + Restart + Logs


## معماری و ساختار پوشه‌ها (خلاصه)
```
Viranum/
├─ docker-compose.yml
├─ infra/
│  ├─ Dockerfile
│  └─ requirements.txt
├─ src/
│  └─ app/
│     ├─ main.py                 # Entry: هندلرها، فلوها، کیبوردها
│     ├─ config.py               # تنظیمات .env
│     ├─ db.py                   # Async engine (فاز بعد Postgres)
│     ├─ i18n.py                 # استاب چندزبانه (FA/EN/RU)
│     ├─ services/
│     │  ├─ numberland_client.py # کلاینت API (retry/backoff/error-map)
│     │  └─ pricing.py           # موتور قیمت‌گذاری (markup/rounding/min-profit)
│     └─ utils/
│        ├─ logger.py            # Loguru
│        └─ enums.py             # وضعیت شماره‌ها
├─ api.md                        # خلاصه مستندات Numberland API
├─ ROADMAP.md                    # نقشه‌راه فنی
├─ changelog.md                  # تاریخچه تغییرات
├─ README.md                     # این فایل
├─ .env.example                  # نمونه تنظیمات
├─ setup.sh                      # راه‌اندازی خودکار سرور خام
└─ u.sh                          # Pull/Build/Restart/Logs
```


## پیش‌نیازها
- Git
- Docker + Docker Compose v2
- دسترسی به توکن ربات تلگرام و NUMBERLAND_API_KEY

روی Windows پیشنهاد می‌شود از WSL یا Git Bash برای اجرای اسکریپت‌ها استفاده کنید.


## راه‌اندازی سریع (Fresh Server)
به‌صورت خودکار با setup.sh:
```
sudo bash setup.sh "https://github.com/USERNAME/Viranum.git" main
# سپس طبق پرامپت‌ها BOT_TOKEN ،NUMBERLAND_API_KEY و ADMIN_IDS را وارد کنید
```
این اسکریپت:
- Git، Docker و Compose را نصب می‌کند
- ریپو را در /opt/viranum کلون/آپدیت می‌کند
- .env را می‌سازد و تنظیم می‌کند
- سرویس‌ها را build و up می‌کند و لاگ بات را نمایش می‌دهد


## راه‌اندازی محلی (Docker)
```
git clone https://github.com/USERNAME/Viranum.git
cd Viranum
cp .env.example .env
# فایل .env را ویرایش کنید (BOT_TOKEN, NUMBERLAND_API_KEY, ADMIN_IDS, ...)

docker compose build
docker compose up -d
docker compose logs -f bot
```

پس از اجرا، در تلگرام دستور /start را به ربات بفرستید.


## متغیرهای محیطی (env)
- BOT_TOKEN: توکن ربات تلگرام
- ADMIN_IDS: لیست آیدی تلگرام ادمین‌ها، جداشده با کاما (مثال: 123,456)
- NUMBERLAND_API_KEY: کلید API نامبرلند
- DB_DSN: پیش‌فرض اتصال Postgres (برای فاز بعد)
- REDIS_DSN: آدرس Redis (پیش‌فرض: redis://redis:6379/0)
- BASE_MARKUP_PERCENT: درصد سود پایه (مثال: 20)
- MARKUP_ROUND_TO: گرد کردن قیمت (مثال: 100)
- BOT_MODE: polling | webhook (در حال حاضر polling)
- LOCALE_DEFAULT: زبان پیش‌فرض (fa)


## استفاده از ربات
- /start: منوی اصلی
- /balance: مشاهده موجودی Numberland (تست اتصال API)
- خرید شماره عادی:
  1) انتخاب سرویس → 2) انتخاب کشور → 3) اپراتور (1..4، any، min)
  4) نمای�� قیمت پایه و قیمت نهایی → تایید خرید
  5) نمایش شماره و پایش وضعیت (دریافت کد/لغو/مسدود/اتمام)
  دکمه‌ها: لغو، کد مجدد، بستن، Refresh
- کیف پول:
  - نمایش موجودی کیف پول داخلی (Redis)
  - افزایش موجودی: ارسال مبلغ و انتظار تایید ادمین
  - تاریخچه تراکنش‌ها: نمایش 10 مورد آخر

یادآوری: در نسخه فعلی (MVP) خرید به کیف پول داخلی متصل نشده است؛ اتصال کسر موجودی و بازگشت وجه در فاز بعدی اضافه می‌شود.


## به‌روزرسانی و ری‌استارت سریع
از u.sh استفاده کنید:
```
bash u.sh [branch] [service]
# مثال:
bash u.sh main bot
```
این اسکریپت آخرین تغییرات را Pull کرده، build و up می‌کند و لاگ سرویس انتخابی را نمایش می‌دهد.


## عیب‌یابی
- docker compose version خطا داد؟ Compose v2 را نصب/فعال کنید (setup.sh این کار را انجام می‌دهد).
- دسترسی Docker: کاربر را به گروه docker اضافه کنید (setup.sh تلاش می‌کند این کار را انجام دهد؛ نیاز به relogin).
- لاگ‌��ا:
```
docker compose logs -f bot
```
- Redis در دسترس نیست؟ سرویس redis در compose باید healthy باشد.
- Numberland خطا برمی‌گرداند؟ مقدار RESULT منفی در پاسخ JSON را ببینید و مپ خطاها را در services/numberland_client.py بررسی کنید.


## توسعه و مشارکت
- ساختار کد ماژولار است. برای افزودن فلو جدید، هندلر/کیبورد و سرویس مرتبط را اضافه کنید.
- i18n فعلاً در حافظه است (i18n.py) و در فاز بعد به gettext (.po) منتقل می‌شود.
- برنامه‌های بعدی:
  - Postgres models + migrations (Alembic)
  - کش کاتالوگ سرویس/کشورها
  - اتصال خرید به کیف پول داخلی و بازگشت وجه خودکار
  - شماره دائمی (Special) و ابزارهای گزارش‌گیری ادمین
  - تست‌های واحد/یکپارچه و CI


## مستندات مرتبط
- api.md: خلاصه مستندات Numberland API
- ROADMAP.md: معماری، فازها و وظایف
- changelog.md: تاریخچه تغییرات نسخه‌ها

