# Numberland API – راهنمای خلاصه و ساختارمند

این فایل خلاصه‌ای ساختارمند از مستندات Info.md (سایت numberland.ir) برای استفاده در توسعه ربات تلگرامی پایتونی است. همه پاسخ‌ها JSON هستند و از طریق فراخوانی GET به آدرس v2.php با پارامترهای query انجام می‌شوند.


## اطلاعات پایه
- Base URL: https://api.numberland.ir/v2.php
- Auth: پارامتر apikey در Query String (از بخش تنظیمات حساب کاربری دریافت می‌شود)
- Content-Type: JSON (همه پاسخ‌ها)
- Rate limit: حداکثر 50 درخواست در ثانیه برای هر IP. در صورت عبور از حد، درخواست رد یا IP به‌طور موقت مسدود می‌شود.
- واحد پول: Toman
- قواعد خطا: اگر RESULT منفی باشد یعنی خطا. نمونه خطاهای عمومی:
  - -901: apikey not found (کلید API اشتباه است)
  - -902: method invalid (دستور اشتباه است)
  - -990: number id invalid (آیدی شماره اشتباه است)
  - -900: سایر ایرادات فنی (با پشتیبانی و مستندات تماس بگیرید)


## الگوی کلی فراخوانی
همه متدها از طریق پارامتر method فراخوانی می‌شوند و سایر پارامترها در Query اضافه می‌شوند:
- v2.php?apikey=YOUR_API_KEY&method=METHOD_NAME[&other=params]

همه متدها GET هستند.


## گردش کار پیشنهادی برای «شماره عادی» (Temporary)
1) بررسی موجودی حساب: method=balance
2) دریافت موجودی/قیمت شماره‌ها برای انتخاب: method=getinfo (با فیلترهای service/country/operator)
3) خرید شماره: method=getnum (با service/country/operator)
4) پایش وضعیت و دریافت کد: method=checkstatus&id=ID
5) عملیات روی وضعیت شماره در صورت نیاز:
   - لغو: method=cancelnumber&id=ID (در وضعیت 1)
   - اعلام مسدودی: method=bannumber&id=ID (در وضعیت 1)
   - درخواست کد مجدد: method=repeat&id=ID (اگر شماره قابلیت repeat داشته و در وضعیت 2 است)
   - بستن/اتمام: method=closenumber&id=ID (در وضعیت 2 یا 5)

نکته: زمان اعتبار شماره بین 10 تا 20 دقیقه است. در این بازه می‌توانید چندین پیامک دریافت کنید. اگر کدی دریافت نشود و لغو/اتمام رخ دهد، مبلغ عودت داده می‌شود (طبق شرایط ذکرشده).


## گردش کار پیشنهادی برای «شماره دائمی» (Special/Permanent)
- لیست شماره‌های دائمی: method=spnumberslist یا method=spnumberstree
- خرید/جزییات یک شماره دائمی خاص: method=getspnumber&id=NUMBER_ID
- لیست شماره‌های دائمی خریداری‌شده: method=myspnumbers


## اندپوینت‌ها و پارامترها

### 1) Balance – موجودی حساب
- URL نمونه:
  - v2.php?apikey=API&method=balance
- پاسخ نمونه:
  {
    "RESULT":"1",
    "BALANCE":"192100",
    "CURRENCY":"Toman"
  }


### 2) Get Info – موجودی/قیمت شماره‌ها (شماره عادی)
- URL نمونه:
  - v2.php?apikey=API&method=getinfo[&operator=OP][&country=CC][&service=SV]
- پارامترهای اختیاری فیلتر/مرتب‌سازی:
  - operator: کد اپراتور 1..4 یا any یا min
    - any: انتخاب خودکار اپراتور با موجودی، از ارزان به گران
    - min: انتخاب ارزان‌ترین اپراتور، اما در صورت عدم ��وجودی، گزینه گران‌تر انتخاب نمی‌شود
  - country: کد کشور (از getcountry)
  - service: کد سرویس (از getservice)
- پاسخ نمونه (هر آیتم):
  {
    "service":"1",
    "country":"8",
    "operator":"1",
    "count":"1087",
    "amount":"1700",
    "repeat":"1",
    "time":"00:20:00",
    "active":1,
    "description":"بدون ریپورت"
  }
- فیلدها:
  - service: کد سرویس
  - country: کد کشور
  - operator: کد اپراتور
  - count: تعداد موجودی
  - amount: قیمت (تومان)
  - repeat: 1 یعنی قابل دریافت کد مجدد
  - time: بازه زمانی مجاز دریافت کدها
  - active: 1 فعال، 0 غیرفعال
  - description: توضیحات (مثلاً «بدون ریپورت» برای تلگرام)


### 3) Get Number – خرید شماره عادی
- URL نمونه:
  - v2.php?apikey=API&method=getnum&country=CC&operator=OP&service=SV
- پارامترها:
  - apikey: کلید API
  - service: کد سرویس
  - country: کد کشور
  - operator: 1..4 یا any یا min
- پاسخ موفق نمونه:
  {
    "RESULT":"1",
    "ID":"74001",
    "NUMBER":"79313226657",
    "AREACODE":"7",
    "AMOUNT":"2200",
    "REPEAT":"1",
    "TIME":"00:20:00"
  }
- خطاهای اختصاصی این بخش (RESULT منفی):
  - -202: parameters not found (پارامتر خالی/اشتباه)
  - -204: this number is not active (شماره فعال نیست)
  - -205: no balance (شارژ کافی نیست)
  - -210: service is not active (سرویس فعال نیست)
  - -211: operator is not active (اپراتور فعال نیست)
  - -212: country is not active (کشور فعال نیست)


### 4) Check Status – بررسی وضعیت شماره عادی
- URL نمونه:
  - v2.php?apikey=API&method=checkstatus&id=ID
- پاسخ نمونه:
  {
    "RESULT":1,
    "CODE":"0",
    "DESCRIPTION":"wait code"
  }
- معانی RESULT (مثبت):
  - 1: wait code (در انتظار کد)
  - 2: code received (کد دریافت شده؛ مقدار در فیلد CODE برمی‌گردد)
  - 3: number canceled (شماره کنسل)
  - 4: number banned (شماره مسدود)
  - 5: wait code again (در انتظار کد مجدد)
  - 6: completed (تکمیل درخواست)
- خطای اختصاصی:
  - -304: number id not found (آیدی یافت نشد)


### 5) Control Methods – عملیات روی وضعیت شماره عادی
- الگو:
  - v2.php?apikey=API&method=METHOD_NAME&id=ID
- METHOD_NAME و محدودیت‌ها:
  - cancelnumber: لغو (فقط در وضعیت 1). در صورت موفقیت، هزینه بازگشت.
  - bannumber: اعلام مسدودی (فقط در وضعیت 1). در صورت موفقیت، هزینه بازگشت.
  - repeat: درخواست کد مجدد (اگر شماره repeat دارد و در وضعیت 2 است). پس از موفقیت، وضعیت به 5 می‌رود.
  - closenumber: اتمام/بستن (اگر در وضعیت 2 یا 5 است). پس از موفقیت، وضعیت 6.
- پاسخ: همان ساختار checkstatus برای مشاهده وضعیت نهایی برمی‌گردد.


### 6) Permanent Numbers – شماره‌های دائمی

6-1) لیست ساده
- URL: v2.php?apikey=API&method=spnumberslist
- پاسخ نمونه:
  {
    "RESULT":1,
    "DESCRIPTION":[
      {"ID":"13244","NUMBER":"+1 (706) 610000 7","PRICE":"730000","TYPE":"2","COMMENT":"fully round"},
      {"ID":"13328","NUMBER":"+1 (775) 302-9356","PRICE":"240000","TYPE":"0","COMMENT":"not round"}
    ]
  }
- TYPE: 0 not round، 1 half round، 2 fully round

6-2) لیست درختی
- URL: v2.php?apikey=API&method=spnumberstree
- پاسخ نمونه (تقسیم بر اساس TYPE):
  {
    "RESULT":1,
    "TYPES":[
      {"TYPE":0,"DESCRIPTION":"not round","NUMBERS":[{"ID":"13328","NUMBER":"+1 (775) 302-9356","PRICE":"240000"}]},
      {"TYPE":2,"DESCRIPTION":"fully round","NUMBERS":[{"ID":"13244","NUMBER":"+1 (706) 610000 7","PRICE":"730000"}]}
    ]
  }

6-3) جزییات شماره دائمی خریداری‌شده
- URL: v2.php?apikey=API&method=getspnumber&id=NUMBER_ID
- پاسخ نمونه:
  {
    "result":"1",
    "numbers":[
      {
        "ID":"3170",
        "NUMBER":"+1 (551) 800 26 35",
        "PRICE":"180000",
        "USERNAME":"...",
        "PASSWORD":"...",
        "RECOVERY":"...",
        "DATE":"1400/7/27",
        "TIME":"14:15:06"
      }
    ]
  }

6-4) لیست شماره‌های دائمی خریداری‌شده
- URL: v2.php?apikey=API&method=myspnumbers
- پاسخ: مشابه getspnumber اما چند آیتمی


### 7) Catalog – کاتالوگ کشور/سرویس/اپراتور

7-1) کشورهای قابل پشتیبانی
- URL: v2.php?apikey=API&method=getcountry
- خروجی هر آیتم:
  - id، name، name_en، areacode، emoji، image، active
- نکته: برخی کشورها ممکن است غیرفعال باشند (active=0)

7-2) سرویس‌ها
- URL: v2.php?apikey=API&method=getservice
- خروجی هر آیتم:
  - id، name، name_en، description، image، active
- توجه: لیست طولانی است و شامل سرویس‌های متداول (Telegram, WhatsApp, Instagram, Gmail, ...)، سرویس‌های پرداخت/کریپتو، و سرویس‌های AI (ChatGPT, Claude, Gemini, Copilot, Grok, Perplexity, ...)

7-3) اپراتورها
- operator=1..4: مطابق شماره‌گذاری در UI پنل
- operator=min: ارزان‌ترین اپراتور انتخاب می‌شود؛ اگر موجودی نداشت، گزینه گران‌تر انتخاب نمی‌شود
- operator=any: از ارزان به گران، اپراتوری که موجود باشد انتخاب می‌شود


## نکات پیاده‌سازی ربات تلگرام (Python)

- کتابخانه‌ها:
  - پیشنهاد Async: aiogram یا python-telegram-bot (v20+) با asyncio
- ساختار جریان کار برای «شماره عادی»:
  - انتخاب سرویس > انتخاب کشور > نمایش ارزان‌ترین/موجودترین اپراتور (با getinfo) > خرید (getnum) > نمایش شماره به کاربر > پایش وضعیت (checkstatus) تا دریافت کد > ارائه کد > امکان درخواست کد مجدد (repeat) یا بستن (closenumber) یا لغو (cancelnumber)
- Polling وضعیت:
  - بازه پیشنهادی 3 تا 5 ثانیه با backoff ملای��، توقف در دریافت کد (RESULT=2) یا اتمام (6) یا لغو/مسدود (3/4) یا اتمام زمان
  - محدودیت 50 rps رعایت شود (صف درخواست، batching، throttle per user)
- مدیریت خطا:
  - RESULT<0 را مپ کنید به پیام‌های قابل فهم کاربر و رفتار مناسب (Retry/Refund/Stop)
  - در -205 (no balance) پیام مدیریتی بدهید
  - در -202 پارامترها را بازبینی کنید
- ذخیره‌سازی:
  - سفارش‌ها: id، number، areacode، amount، repeat، expire_time/time، وضعیت جاری، user_id، service/country/operator، timestamps
  - لاگ وضعیت‌ها و پیامک‌های دریافت‌شده
- امنیت:
  - apikey را در متغیر محیطی/Secret Manager نگه دارید؛ در لاگ‌ها ماسک کنید
  - timeouts و retry با jitter برای پایداری شبکه
- تجربه کاربری:
  - نمایش قیمت پیش از خرید، اطلاع از بازه TIME و قابلیت repeat
  - امکان لغو خودکار قبل از انقضا اگر کد نیامد (و بازپرداخت)
  - یادآوری محدودیت زمانی و وضعیت زنده سفارش


## الگوهای URL آماده استفاده
- Balance: v2.php?apikey=API&method=balance
- Get Info: v2.php?apikey=API&method=getinfo&service=SV&country=CC&operator=any|min|1|2|3|4
- Get Number: v2.php?apikey=API&method=getnum&service=SV&country=CC&operator=any|min|1|2|3|4
- Check Status: v2.php?apikey=API&method=checkstatus&id=ID
- Cancel Number: v2.php?apikey=API&method=cancelnumber&id=ID
- Ban Number: v2.php?apikey=API&method=bannumber&id=ID
- Repeat Code: v2.php?apikey=API&method=repeat&id=ID
- Close Number: v2.php?apikey=API&method=closenumber&id=ID
- Countries: v2.php?apikey=API&method=getcountry
- Services: v2.php?apikey=API&method=getservice
- SP Numbers List: v2.php?apikey=API&method=spnumberslist
- SP Numbers Tree: v2.php?apikey=API&method=spnumberstree
- Get SP Number Detail: v2.php?apikey=API&method=getspnumber&id=NUMBER_ID
- My SP Numbers: v2.php?apikey=API&method=myspnumbers


## ملاحظات مهم عملیاتی
- زمان اعتبار شماره عادی: 10 تا 20 دقیقه؛ هر تعداد پیامک در این بازه
- شناسه سفارش (ID) را حتماً ذخیره کنید؛ مبنای تمام عملیات بعدی است
- Refund: در لغو/مسدودی در وضعیت مجاز و نبودن کد؛ مبلغ به حساب پنل برمی‌گردد
- قیمت‌ها در API با تخفیفات حساب شما اعمال می‌شوند
- برای ارزان‌ترین شماره از operator=min استفاده کنید؛ برای «انتخاب دارای موجودی از ارزان به گران» از any استفاده کنید


## نظر و توصیه‌ها برای توسعه
- مستندات شفاف و endpointها ساده‌اند، اما:
  - خطاها در چند بخش توزیع شده‌اند؛ بهتر است در کد، یک ErrorMap واحد بسازید که همه RESULT<0 را مدیریت کند.
  - وضعیت‌ها (1..6) را به enum/State تبدیل کنید تا منطق ربات ساده‌تر شود.
  - برای جلوگیری از block، یک لایه throttle مرکزی بسازید (token bucket) و polling را adaptive کنید.
  - سفارش‌ها را با TTL بر اساس TIME مانیتور کنید و قبل از انقضا به کاربر هشدار دهید.
  - از operator=any برای بهبود نرخ موفقیت دریافت شماره استفاده کنید؛ اگر سیاست قیمت‌گذاری سفارشی دارید، قیمت نهایی را قبل از خرید به کاربر نشان دهید.
  - داده‌های کاتالوگ (کشورها/سرویس‌ها) را cache کنید و به‌صورت دوره‌ای refresh کنید.


---
آخرین به‌روزرسانی این خلاصه: بر اساس Info.md موجود در مخزن. در صورت تغییرات جدید در پنل Numberland، این فایل را نیز به‌روز کنید.
