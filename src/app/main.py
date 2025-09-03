import asyncio
import logging
import json
import time
from typing import Any, Dict, List, Optional, Tuple

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest

from .config import settings
from .i18n import tr, set_locale_middleware
from .utils.logger import setup_logging
from .services.numberland_client import NumberlandClient, NumberlandAPIError
from .services.pricing import calculate_price
from .utils.enums import NumberStatus


# ---------------------- Helpers ----------------------

def get_lang_from_user(obj) -> str:
    lang = getattr(getattr(obj, "from_user", None), "language_code", None) or settings.LOCALE_DEFAULT
    return lang if lang in {"fa", "en", "ru"} else settings.LOCALE_DEFAULT


def t(lang: str, fa: str, en: str, ru: str) -> str:
    return {"fa": fa, "en": en, "ru": ru}.get(lang, fa)


def parse_time_to_seconds(time_str: str) -> int:
    # format: HH:MM:SS e.g. 00:20:00
    try:
        h, m, s = map(int, time_str.split(":"))
        return h * 3600 + m * 60 + s
    except Exception:
        return 1200  # default 20 minutes


def localize_api_error(lang: str, code: Optional[int], description: str) -> str:
    # Map well-known codes/descriptions to localized messages
    code = int(code) if code is not None else None
    desc_key = description.strip().lower() if description else ""

    # Known mappings
    if code == -206 or desc_key == "price not set":
        return t(lang, "قیمت برای خرید تنظیم نشده است.", "Price is not set for purchase.", "Цена для покупки не установлена.")
    if code == -205 or desc_key == "no balance":
        return t(lang, "موجودی پنل کافی نیست.", "Insufficient panel balance.", "Недостаточно средств на панели.")
    if code == -202 or desc_key == "parameters not found":
        return t(lang, "پارامترها نامعتبر هستند.", "Invalid parameters.", "Неверные параметры.")

    # Fallback
    return description or t(lang, "خطای نامشخص.", "Unknown error.", "Неизвестная ошибка.")


# ---------------------- Keyboards ----------------------

async def safe_edit_text(message: Message, text: str, reply_markup=None):
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return
        raise

def main_kb(lang: str):
    b = InlineKeyboardBuilder()
    b.button(text=tr("menu.buy_temp", lang), callback_data="buy_temp")
    b.button(text=tr("menu.buy_perm", lang), callback_data="buy_perm")
    b.button(text=tr("menu.wallet", lang), callback_data="wallet")
    b.button(text=tr("menu.active", lang), callback_data="active_orders")
    b.button(text=tr("menu.orders", lang), callback_data="orders")
    b.button(text=tr("menu.support", lang), callback_data="support")
    b.button(text=tr("menu.language", lang), callback_data="language")
    b.adjust(2, 2, 3)
    return b.as_markup()


def language_kb():
    b = InlineKeyboardBuilder()
    b.button(text="فارسی", callback_data="lang:fa")
    b.button(text="English", callback_data="lang:en")
    b.button(text="Русский", callback_data="lang:ru")
    b.adjust(3)
    return b.as_markup()


def services_kb(services: List[Dict[str, Any]], page: int, per_page: int, lang: str):
    b = InlineKeyboardBuilder()
    start = page * per_page
    end = start + per_page
    page_items = services[start:end]

    for sv in page_items:
        if str(sv.get("active", 1)) != "1":
            continue
        name_fa = sv.get("name") or ""
        name_en = sv.get("name_en") or name_fa
        name = name_fa if lang == "fa" else name_en
        b.button(text=name, callback_data=f"sv:s:{sv['id']}:{page}")

    nav_row = []
    if page > 0:
        nav_row.append((t(lang, "⬅️ قبلی", "⬅️ Prev", "⬅️ Назад"), f"sv:p:{page-1}"))
    if end < len(services):
        nav_row.append((t(lang, "بعدی ➡️", "Next ➡️", "Далее ➡️"), f"sv:p:{page+1}"))

    for text, data in nav_row:
        b.button(text=text, callback_data=data)

    b.button(text=t(lang, "بازگشت", "Back", "Назад"), callback_data="home")
    b.adjust(2)
    return b.as_markup()


def countries_kb(countries: List[Dict[str, Any]], page: int, per_page: int, lang: str):
    b = InlineKeyboardBuilder()
    start = page * per_page
    end = start + per_page
    page_items = countries[start:end]

    for ct in page_items:
        if str(ct.get("active", 1)) != "1":
            continue
        name_fa = ct.get("name") or ""
        name_en = ct.get("name_en") or name_fa
        name = name_fa if lang == "fa" else name_en
        emoji = ct.get("emoji") or ""
        b.button(text=f"{emoji} {name}", callback_data=f"ct:s:{ct['id']}:{page}")

    nav_row = []
    if page > 0:
        nav_row.append((t(lang, "⬅️ قبلی", "⬅️ Prev", "⬅️ Назад"), f"ct:p:{page-1}"))
    if end < len(countries):
        nav_row.append((t(lang, "بعدی ➡️", "Next ➡️", "Далее ➡️"), f"ct:p:{page+1}"))

    for text, data in nav_row:
        b.button(text=text, callback_data=data)

    b.button(text=t(lang, "بازگشت", "Back", "Назад"), callback_data="buy_temp")
    b.adjust(2)
    return b.as_markup()


def operators_kb(lang: str):
    b = InlineKeyboardBuilder()
    ops = [
        ("1", "1"),
        ("2", "2"),
        ("3", "3"),
        ("4", "4"),
        (t(lang, "ارزان‌ترین (min)", "Cheapest (min)", "Самый дешёвый (min)"), "min"),
        (t(lang, "هرکدام (any)", "Any (any)", "Любой (any)"), "any"),
    ]
    for label, code in ops:
        b.button(text=label, callback_data=f"op:{code}")
    b.button(text=t(lang, "بازگشت", "Back", "Назад"), callback_data="buy_temp")
    b.adjust(3, 3, 1)
    return b.as_markup()


def confirm_kb(lang: str):
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "تایید خرید ✅", "Confirm Purchase ✅", "Подтвердить покупку ✅"), callback_data="cf:buy")
    b.button(text=t(lang, "بازگشت", "Back", "Назад"), callback_data="buy_temp")
    b.adjust(1, 1)
    return b.as_markup()


def status_kb(lang: str, number_id: str):
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "لغو", "Cancel", "Отмена"), callback_data=f"st:cancel:{number_id}")
    b.button(text=t(lang, "کد مجدد", "Repeat", "Повтор"), callback_data=f"st:repeat:{number_id}")
    b.button(text=t(lang, "بستن", "Close", "Закрыть"), callback_data=f"st:close:{number_id}")
    b.button(text=t(lang, "به‌روزرسانی", "Refresh", "Обновить"), callback_data=f"st:refresh:{number_id}")
    b.adjust(3, 1)
    return b.as_markup()


# ---------------------- FSM ----------------------

class BuyTemp(StatesGroup):
    choosing_service = State()
    choosing_country = State()
    choosing_operator = State()
    confirm_purchase = State()
    active_order = State()


POLL_TASKS: Dict[str, asyncio.Task] = {}


class WalletTopUp(StatesGroup):
    waiting_amount = State()


def admin_ids() -> List[int]:
    ids: List[int] = []
    for part in (settings.ADMIN_IDS or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.append(int(part))
        except ValueError:
            continue
    return ids


async def get_redis():
    try:
        from redis.asyncio import from_url
        return from_url(settings.REDIS_DSN)
    except Exception:
        return None


async def set_user_lang(user_id: int, lang: str) -> None:
    r = await get_redis()
    if not r:
        return
    if lang not in {"fa", "en", "ru"}:
        lang = settings.LOCALE_DEFAULT
    await r.set(f"user:lang:{user_id}", lang)


async def get_lang(obj) -> str:
    r = await get_redis()
    uid = getattr(getattr(obj, "from_user", None), "id", None)
    tg_lang = getattr(getattr(obj, "from_user", None), "language_code", None)
    if r and uid:
        try:
            v = await r.get(f"user:lang:{uid}")
            if v:
                val = v.decode() if isinstance(v, (bytes, bytearray)) else str(v)
                if val in {"fa", "en", "ru"}:
                    return val
        except Exception:
            pass
    base = tg_lang or settings.LOCALE_DEFAULT
    return base if base in {"fa", "en", "ru"} else settings.LOCALE_DEFAULT


async def wallet_get_balance(user_id: int) -> int:
    r = await get_redis()
    if not r:
        return 0
    val = await r.get(f"wallet:bal:{user_id}")
    return int(val) if val else 0


async def wallet_add_tx(user_id: int, tx: Dict[str, Any]):
    r = await get_redis()
    if not r:
        return
    await r.lpush(f"wallet:tx:{user_id}", json.dumps(tx, ensure_ascii=False))
    await r.ltrim(f"wallet:tx:{user_id}", 0, 49)  # keep last 50


async def wallet_credit(user_id: int, amount: int, meta: str = ""):
    r = await get_redis()
    if not r:
        return
    pipe = r.pipeline()
    pipe.incrby(f"wallet:bal:{user_id}", amount)
    await pipe.execute()
    await wallet_add_tx(user_id, {"type": "credit", "amount": amount, "ts": int(time.time()), "meta": meta})


async def wallet_debit(user_id: int, amount: int, meta: str = "") -> bool:
    r = await get_redis()
    if not r:
        return False
    key = f"wallet:bal:{user_id}"
    # optimistic: get balance then decr if enough
    bal = await wallet_get_balance(user_id)
    if bal < amount:
        return False
    pipe = r.pipeline()
    pipe.decrby(key, amount)
    await pipe.execute()
    await wallet_add_tx(user_id, {"type": "debit", "amount": amount, "ts": int(time.time()), "meta": meta})
    return True


async def wallet_history(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    r = await get_redis()
    if not r:
        return []
    items = await r.lrange(f"wallet:tx:{user_id}", 0, limit - 1)
    out: List[Dict[str, Any]] = []
    for it in items:
        try:
            out.append(json.loads(it))
        except Exception:
            continue
    return out


# ---------------------- Handlers ----------------------

async def on_startup(bot: Bot):
    logging.getLogger(__name__).info("Bot started")


async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    lang = await get_lang(message)
    await message.answer(tr("greet", lang), reply_markup=main_kb(lang))


async def home_handler(call: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = await get_lang(call)
    await call.answer()
    await call.message.edit_text(tr("greet", lang), reply_markup=main_kb(lang))


async def language_handler(call: CallbackQuery):
    lang = await get_lang(call)
    await call.message.edit_text(tr("choose_language", lang), reply_markup=language_kb())


async def set_language_handler(call: CallbackQuery):
    _, lang = call.data.split(":", 1)
    await set_user_lang(call.from_user.id, lang)
    await call.message.edit_text(tr("language_set", lang), reply_markup=main_kb(lang))


async def wallet_kb(lang: str):
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "افزایش موجودی", "Increase balance", "Пополнить баланс"), callback_data="w:topup")
    b.button(text=t(lang, "تاریخچه", "History", "История"), callback_data="w:history")
    b.button(text=t(lang, "بازگشت", "Back", "Назад"), callback_data="home")
    b.adjust(2, 1)
    return b.as_markup()


async def wallet_handler(call: CallbackQuery, state: FSMContext):
    lang = await get_lang(call)
    await call.answer()
    uid = call.from_user.id
    bal = await wallet_get_balance(uid)
    text = t(lang, "موجودی کیف پول شما: ", "Your wallet balance: ", "Баланс кошелька: ") + f"{bal} تومان"
    await call.message.edit_text(text, reply_markup=await wallet_kb(lang))


async def balance_cmd(message: Message):
    lang = await get_lang(message)
    try:
        async with NumberlandClient() as cl:
            bal = await cl.balance()
        balance = bal.get("BALANCE") or bal.get("balance")
        currency = bal.get("CURRENCY") or bal.get("currency") or "Toman"
        await message.answer(t(lang, "موجودی شما: ", "Your balance: ", "Ваш баланс: ") + f"{balance} {currency}")
    except Exception:
        await message.answer(t(lang, "خطا در دریافت موجودی.", "Failed to fetch balance.", "Не удалось получить баланс."))


async def support_handler(call: CallbackQuery):
    lang = await get_lang(call)
    await call.answer()
    await call.message.edit_text(tr("support.info", lang), reply_markup=main_kb(lang))


# --------- Wallet Top-up (manual with admin approval) ---------

async def wallet_topup_start_handler(call: CallbackQuery, state: FSMContext):
    lang = await get_lang(call)
    await call.answer()
    await state.set_state(WalletTopUp.waiting_amount)
    await call.message.edit_text(t(lang, "مبلغ شارژ را به تومان ارسال کنید:", "Send top-up amount (Toman):", "Отправьте сумму пополнения (Томан):"))


async def topup_amount_input_handler(message: Message, state: FSMContext, bot: Bot):
    lang = await get_lang(message)
    text = (message.text or "").strip()
    try:
        amount = int(text)
    except ValueError:
        await message.answer(t(lang, "مبلغ نامعتبر است. یک عدد ارسال کنید.", "Invalid amount. Send a number.", "Неверная сумма. Отправьте число."))
        return

    if amount <= 0:
        await message.answer(t(lang, "مبلغ باید بزرگتر از صفر باشد.", "Amount must be greater than zero.", "Сумма должна быть больше нуля."))
        return

    uid = message.from_user.id
    req_id = f"{int(time.time()*1000)}:{uid}"

    r = await get_redis()
    if r:
        payload = {"user_id": uid, "amount": amount, "status": "pending"}
        await r.set(f"wallet:topup:{req_id}", json.dumps(payload, ensure_ascii=False), ex=86400)

    # notify admins
    admins = admin_ids()
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "تایید ✅", "Approve ✅", "Одобрить ✅"), callback_data=f"w:approve:{req_id}")
    kb.button(text=t(lang, "رد ❌", "Reject ❌", "Отклонить ❌"), callback_data=f"w:reject:{req_id}")
    kb.adjust(2)

    note = (
        t(lang, "درخواست شارژ جدید", "New top-up request", "Новый запрос на пополнение")
        + f"\nID: {req_id}\nUser: {uid}\nAmount: {amount}"
    )

    for admin_id in admins:
        try:
            await bot.send_message(admin_id, note, reply_markup=kb.as_markup())
        except Exception:
            continue

    await state.clear()
    await message.answer(t(lang, "درخواست شما ثبت شد و در انتظار تایید است.", "Your request was submitted and awaits approval.", "Ваш запрос отправлен и ожидает одобрения."))


async def wallet_history_handler(call: CallbackQuery):
    lang = await get_lang(call)
    await call.answer()
    uid = call.from_user.id
    items = await wallet_history(uid, 10)
    if not items:
        await call.message.edit_text(t(lang, "تاریخچه‌ای موجود نیست.", "No history.", "История отсутствует."), reply_markup=await wallet_kb(lang))
        return

    lines = []
    for it in items:
        typ = it.get("type")
        amount = it.get("amount")
        if typ == "credit":
            lines.append(t(lang, "+ شارژ ", "+ Credit ", "+ Пополнение ") + f"{amount}")
        elif typ == "debit":
            lines.append(t(lang, "- برداشت ", "- Debit ", "- Списание ") + f"{amount}")
        else:
            lines.append(json.dumps(it, ensure_ascii=False))
    text = "\n".join(lines)
    await call.message.edit_text(text, reply_markup=await wallet_kb(lang))


async def wallet_topup_approve_handler(call: CallbackQuery, bot: Bot):
    lang = await get_lang(call)
    await call.answer()
    if call.from_user.id not in admin_ids():
        await call.message.answer(t(lang, "دسترسی ندارید.", "No permission.", "Нет доступа."))
        return
    _, _, req_id = call.data.split(":", 2)
    r = await get_redis()
    if not r:
        await call.message.answer(t(lang, "خطا در Redis.", "Redis error.", "Ошибка Redis."))
        return
    data = await r.get(f"wallet:topup:{req_id}")
    if not data:
        await call.message.answer(t(lang, "درخواست یافت نشد یا منقضی شده.", "Request not found or expired.", "Запрос не найден или истёк."))
        return
    payload = json.loads(data)
    if payload.get("status") != "pending":
        await call.message.answer(t(lang, "این درخواست قبلاً پردازش شده است.", "Request already processed.", "Запрос уже обработан."))
        return

    uid = int(payload["user_id"])  # type: ignore
    amount = int(payload["amount"])  # type: ignore

    await wallet_credit(uid, amount, meta=f"topup:{req_id}")
    payload["status"] = "approved"
    await r.set(f"wallet:topup:{req_id}", json.dumps(payload, ensure_ascii=False), ex=3600)

    try:
        await bot.send_message(uid, t(lang, "شارژ شما با موفقیت انجام شد.", "Your top-up was approved.", "Ваше пополнение одобрено."))
    except Exception:
        pass

    await call.message.edit_text(t(lang, "درخواست تایید شد.", "Request approved.", "Запрос одобрен."))


async def wallet_topup_reject_handler(call: CallbackQuery, bot: Bot):
    lang = await get_lang(call)
    await call.answer()
    if call.from_user.id not in admin_ids():
        await call.message.answer(t(lang, "دسترسی ندارید.", "No permission.", "Нет доступа."))
        return
    _, _, req_id = call.data.split(":", 2)
    r = await get_redis()
    if not r:
        await call.message.answer(t(lang, "خطا در Redis.", "Redis error.", "Ошибка Redis."))
        return
    data = await r.get(f"wallet:topup:{req_id}")
    if not data:
        await call.message.answer(t(lang, "درخواست یافت نشد یا منقضی شده.", "Request not found or expired.", "Запрос не найден или истёк."))
        return
    payload = json.loads(data)
    if payload.get("status") != "pending":
        await call.message.answer(t(lang, "این درخواست قبلاً پردازش شده است.", "Request already processed.", "Запрос уже обработан."))
        return

    payload["status"] = "rejected"
    await r.set(f"wallet:topup:{req_id}", json.dumps(payload, ensure_ascii=False), ex=3600)

    uid = int(payload["user_id"])  # type: ignore
    try:
        await bot.send_message(uid, t(lang, "درخواست شارژ شما رد شد.", "Your top-up request was rejected.", "Ваш запрос на пополнение отклонён."))
    except Exception:
        pass

    await call.message.edit_text(t(lang, "درخواست رد شد.", "Request rejected.", "Запрос отклонён."))


# --------- Temporary Number Flow ---------

async def buy_temp_handler(call: CallbackQuery, state: FSMContext):
    lang = await get_lang(call)
    await call.answer()
    # Fetch services
    async with NumberlandClient() as cl:
        services = await cl.get_services()
        if not isinstance(services, list):
            services = []
    await state.set_state(BuyTemp.choosing_service)
    await state.update_data(services=services, sv_page=0, lang=lang)
    await call.message.edit_text(
        t(lang, "یک سرویس را انتخاب کنید:", "Choose a service:", "Выберите сервис:"),
        reply_markup=services_kb(services, 0, 8, lang),
    )


async def services_page_handler(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    services = data.get("services", [])
    lang = data.get("lang", settings.LOCALE_DEFAULT)
    page = int(call.data.split(":")[2])
    await state.update_data(sv_page=page)
    await call.message.edit_reply_markup(reply_markup=services_kb(services, page, 8, lang))


async def service_select_handler(call: CallbackQuery, state: FSMContext):
    await call.answer()
    _, _, sid, page = call.data.split(":")
    page = int(page)
    data = await state.get_data()
    lang = data.get("lang", settings.LOCALE_DEFAULT)

    await state.update_data(service_id=sid)

    # Fetch countries
    async with NumberlandClient() as cl:
        countries = await cl.get_countries()
        if not isinstance(countries, list):
            countries = []
    await state.set_state(BuyTemp.choosing_country)
    await state.update_data(countries=countries, ct_page=0)

    await call.message.edit_text(
        t(lang, "کشور را انتخاب کنید:", "Choose a country:", "Выберите страну:"),
        reply_markup=countries_kb(countries, 0, 8, lang),
    )


async def countries_page_handler(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    countries = data.get("countries", [])
    lang = data.get("lang", settings.LOCALE_DEFAULT)
    page = int(call.data.split(":")[2])
    await state.update_data(ct_page=page)
    await call.message.edit_reply_markup(reply_markup=countries_kb(countries, page, 8, lang))


async def country_select_handler(call: CallbackQuery, state: FSMContext):
    await call.answer()
    _, _, cid, page = call.data.split(":")
    data = await state.get_data()
    lang = data.get("lang", settings.LOCALE_DEFAULT)

    await state.update_data(country_id=cid)
    await state.set_state(BuyTemp.choosing_operator)

    await call.message.edit_text(
        t(lang, "اپراتور را انتخاب کنید:", "Choose an operator:", "Выберите оператора:"),
        reply_markup=operators_kb(lang),
    )


async def operator_select_handler(call: CallbackQuery, state: FSMContext):
    await call.answer()
    _, op = call.data.split(":")
    data = await state.get_data()
    lang = data.get("lang", settings.LOCALE_DEFAULT)
    sid = data.get("service_id")
    cid = data.get("country_id")

    # Query getinfo for quote
    async with NumberlandClient() as cl:
        info = await cl.get_info(service=sid, country=cid, operator=op)

    # Normalize info
    item: Optional[Dict[str, Any]] = None
    if isinstance(info, dict) and info.get("amount"):
        item = info
    elif isinstance(info, list) and info:
        item = info[0]

    if not item:
        await call.message.edit_text(
            t(lang, "شماره‌ای یافت نشد.", "No numbers available.", "Нет доступных номеров."),
            reply_markup=main_kb(lang),
        )
        await state.clear()
        return

    amount = int(item.get("amount", 0))
    count = int(item.get("count", 0))
    repeat = str(item.get("repeat", "0"))
    time_str = item.get("time", "00:20:00")

    final_price = calculate_price(amount)

    await state.update_data(operator=op, quote={
        "amount": amount,
        "final_price": final_price,
        "count": count,
        "repeat": repeat,
        "time": time_str,
    })

    msg = (
        t(lang, "اطلاعات شماره:", "Number info:", "Информация о номере:")
        + f"\n\n"
        + t(lang, "- موجودی: ", "- Available: ", "- Доступно: ") + f"{count}\n"
        + t(lang, "- قیمت پایه: ", "- Base amount: ", "- Базовая цена: ") + f"{amount} تومان\n"
        + t(lang, "- قیمت نهایی: ", "- Final price: ", "- Итоговая цена: ") + f"{final_price} تومان\n"
        + t(lang, "- قابلیت کد مجدد: ", "- Repeat capable: ", "- Повтор возможен: ") + (t(lang, "بله", "Yes", "Да") if repeat == "1" else t(lang, "خیر", "No", "Нет")) + "\n"
        + t(lang, "- بازه زمانی: ", "- Time window: ", "- Временное окно: ") + f"{time_str}"
    )

    await state.set_state(BuyTemp.confirm_purchase)
    await call.message.edit_text(msg, reply_markup=confirm_kb(lang))


async def confirm_buy_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    await call.answer()
    data = await state.get_data()
    lang = await get_lang(call)
    sid = data.get("service_id")
    cid = data.get("country_id")
    op = data.get("operator")

    # For MVP we skip wallet check; directly attempt purchase
    async with NumberlandClient() as cl:
        try:
            quote = data.get("quote", {})
            base_amount = int(quote.get("amount", 0)) if quote else 0
            params = {"service": str(sid), "country": str(cid), "operator": str(op)}
            if base_amount > 0:
                params["price"] = str(base_amount)
            res = await cl._get("getnum", params)
        except NumberlandAPIError as e:
            localized = localize_api_error(lang, getattr(e, "code", None), getattr(e, "description", ""))
            await call.message.edit_text(
                t(lang, "خطا در خرید: ", "Purchase error: ", "Ошибка покупки: ") + localized,
                reply_markup=main_kb(lang),
            )
            await state.clear()
            return

    rid = str(res.get("ID"))
    number = str(res.get("NUMBER"))
    areacode = str(res.get("AREACODE", ""))
    amt = str(res.get("AMOUNT", ""))
    repeat = str(res.get("REPEAT", "0"))
    time_str = str(res.get("TIME", "00:20:00"))

    # Format phone number
    if number.startswith("+"):
        full_number = number
    else:
        prefix = "+" + areacode if areacode else "+"
        full_number = f"{prefix}{number}"

    order_msg = (
        t(lang, "شماره خریداری شد:", "Number purchased:", "Номер куплен:")
        + f"\n\n"
        + t(lang, "- آیدی: ", "- ID: ", "- ID: ") + rid + "\n"
        + t(lang, "- شماره: ", "- Number: ", "- Номер: ") + full_number + "\n"
        + t(lang, "- قیمت: ", "- Price: ", "- Цена: ") + f"{amt} تومان\n"
        + t(lang, "- بازه زمانی: ", "- Time: ", "- Время: ") + time_str + "\n"
        + t(lang, "- کد مجدد: ", "- Repeat: ", "- Повтор: ") + (t(lang, "بله", "Yes", "Да") if repeat == "1" else t(lang, "خیر", "No", "Нет"))
    )

    await state.update_data(order_id=rid)
    await state.set_state(BuyTemp.active_order)

    # persist order to Redis history and active set
    uid = call.from_user.id
    now_ts = int(time.time())
    ttl_sec = parse_time_to_seconds(time_str)
    expire_ts = now_ts + ttl_sec
    r = await get_redis()
    if r:
        entry = {
            "id": rid,
            "number": full_number,
            "amount": amt,
            "time": time_str,
            "repeat": repeat,
            "ts": now_ts,
            "expire_ts": expire_ts,
            "status": "active",
        }
        await r.lpush(f"orders:{uid}", json.dumps(entry, ensure_ascii=False))
        await r.ltrim(f"orders:{uid}", 0, 49)
        await r.hset(f"active:{uid}", mapping={rid: json.dumps(entry, ensure_ascii=False)})
        await r.expire(f"active:{uid}", ttl_sec + 3600)

    await call.message.edit_text(order_msg, reply_markup=status_kb(lang, rid))

    # Start polling task
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    async def poll_status(order_id: str, lang: str):
        async with NumberlandClient() as pcl:
            max_seconds = parse_time_to_seconds(time_str)
            elapsed = 0
            interval = 4
            while elapsed <= max_seconds:
                try:
                    st = await pcl.check_status(id=order_id)
                except Exception as e:
                    await asyncio.sleep(interval)
                    elapsed += interval
                    continue

                result = int(st.get("RESULT", 0))
                code = st.get("CODE", "") or ""
                desc = st.get("DESCRIPTION", "") or ""

                if result == NumberStatus.CODE_RECEIVED:
                    txt = (
                        t(lang, "کد دریافت شد:", "Code received:", "Код получен:")
                        + f"\n\n<code>{code}</code>\n\n"
                        + t(lang, "وضعیت: ", "Status: ", "Статус: ") + desc
                    )
                    try:
                        await bot.send_message(chat_id, txt, parse_mode=ParseMode.HTML)
                    except Exception:
                        pass
                    return
                elif result in (NumberStatus.CANCELED, NumberStatus.BANNED, NumberStatus.COMPLETED):
                    txt = (
                        t(lang, "وضعیت نهایی: ", "Final status: ", "Итоговый статус: ")
                        + f"{desc}"
                    )
                    try:
                        await bot.send_message(chat_id, txt)
                    except Exception:
                        pass
                    return

                await asyncio.sleep(interval)
                elapsed += interval

    # cancel previous task if exists
    prev = POLL_TASKS.get(rid)
    if prev and not prev.done():
        prev.cancel()
    POLL_TASKS[rid] = asyncio.create_task(poll_status(rid, lang))


# --------- Status control ---------

async def _update_active_order(uid: int, order_id: str, status: str, extra: Optional[Dict[str, Any]] = None):
    r = await get_redis()
    if not r:
        return
    raw = await r.hget(f"active:{uid}", order_id)
    if not raw:
        return
    try:
        obj = json.loads(raw)
    except Exception:
        obj = {}
    obj["status"] = status
    if extra:
        obj.update(extra)
    await r.hset(f"active:{uid}", order_id, json.dumps(obj, ensure_ascii=False))
    # keep existing TTL


async def status_action_handler(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    lang = await get_lang(call)

    _, action, rid = call.data.split(":", 2)

    async with NumberlandClient() as cl:
        try:
            if action == "cancel":
                res = await cl.cancel_number(id=rid)
            elif action == "repeat":
                res = await cl.repeat(id=rid)
            elif action == "close":
                res = await cl.close_number(id=rid)
            elif action == "refresh":
                res = await cl.check_status(id=rid)
            else:
                return
        except NumberlandAPIError as e:
            await call.message.answer(t(lang, "خطا: ", "Error: ", "Ошибка: ") + str(e))
            return

    result = int(res.get("RESULT", 0))
    code = res.get("CODE", "") or ""
    desc = res.get("DESCRIPTION", "") or ""

    # Localize common descriptions
    desc_map = {
        "wait code": t(lang, "در انتظار دریافت کد", "wait code", "ожидайте код"),
        "number canceled": t(lang, "شماره کنسل شده", "number canceled", "номер отменён"),
        "number banned": t(lang, "شماره مسدود شده", "number banned", "номер заблокирован"),
        "wait code again": t(lang, "در انتظار دریافت کد مجدد", "wait code again", "ожидание повторного кода"),
        "completed": t(lang, "تکمیل درخواست", "completed", "завершено"),
        "code received": t(lang, "کد دریافت شد", "code received", "код получен"),
    }
    desc_lower = desc.lower()
    localized_desc = desc_map.get(desc_lower, desc)

    uid = call.from_user.id
    if result == NumberStatus.CODE_RECEIVED:
        await _update_active_order(uid, rid, "code", {"code": code})
        txt = t(lang, "کد دریافت شد:", "Code received:", "Код получен:") + f"\n\n<code>{code}</code>"
        await call.message.answer(txt, parse_mode=ParseMode.HTML)
    elif result in (NumberStatus.CANCELED, NumberStatus.BANNED):
        await _update_active_order(uid, rid, "canceled")
        await call.message.answer(t(lang, "وضعیت نهایی: ", "Final status: ", "Итоговый статус: ") + localized_desc)
    elif result == NumberStatus.COMPLETED:
        await _update_active_order(uid, rid, "completed")
        await call.message.answer(t(lang, "وضعیت نهایی: ", "Final status: ", "Итоговый статус: ") + localized_desc)
    else:
        await call.message.answer(t(lang, "وضعیت: ", "Status: ", "Статус: ") + localized_desc)


# --------- My Orders ---------

async def my_orders_handler(call: CallbackQuery):
    lang = await get_lang(call)
    await call.answer()
    uid = call.from_user.id
    r = await get_redis()
    items: List[Dict[str, Any]] = []
    if r:
        raw = await r.lrange(f"orders:{uid}", 0, 9)
        for it in raw or []:
            try:
                items.append(json.loads(it))
            except Exception:
                continue

    if not items:
        await call.message.edit_text(t(lang, "سفارشی یافت نشد.", "No purchases yet.", "Покупки отсутствуют."), reply_markup=main_kb(lang))
        return

    lines = []
    for e in items:
        line = (
            t(lang, "آیدی:", "ID:", "ID:") + f" {e.get('id')} | "
            + t(lang, "شماره:", "Number:", "Номер:") + f" {e.get('number')} | "
            + t(lang, "قیمت:", "Price:", "Цена:") + f" {e.get('amount')}"
        )
        lines.append(line)
    msg = "\n".join(lines)
    await safe_edit_text(call.message, msg, reply_markup=main_kb(lang))


async def active_orders_handler(call: CallbackQuery):
    lang = await get_lang(call)
    await call.answer()
    uid = call.from_user.id
    r = await get_redis()
    if not r:
        await call.message.edit_text(t(lang, "خطا در خواندن داده‌ها.", "Data read error.", "Ошиб��а чтения данных."), reply_markup=main_kb(lang))
        return
    data = await r.hgetall(f"active:{uid}")
    if not data:
        await call.message.edit_text(t(lang, "سفارش فعالی یافت نشد.", "No active orders.", "Активных покупок нет."), reply_markup=main_kb(lang))
        return
    lines = []
    now_ts = int(time.time())
    for key, val in data.items():
        try:
            obj = json.loads(val)
        except Exception:
            continue
        remain = max(0, obj.get("expire_ts", now_ts) - now_ts)
        mins = remain // 60
        secs = remain % 60
        status = obj.get("status", "active")
        line = (
            t(lang, "آیدی:", "ID:", "ID:") + f" {obj.get('id')} | "
            + t(lang, "شماره:", "Number:", "Номер:") + f" {obj.get('number')} | "
            + t(lang, "وضعیت:", "Status:", "Статус:") + f" {status} | "
            + t(lang, "مانده:", "Remaining:", "Осталось:") + f" {mins:02d}:{secs:02d}"
        )
        if status == "code" and obj.get("code"):
            line += t(lang, " | کد:", " | Code:", " | Код:") + f" {obj.get('code')}"
        lines.append(line)
    msg = "\n".join(lines)
    await safe_edit_text(call.message, msg, reply_markup=main_kb(lang))


# --------- Permanent numbers (stub) ---------

async def buy_perm_handler(call: CallbackQuery):
    lang = await get_lang(call)
    await call.answer()
    await call.message.edit_text(tr("buy_perm.stub", lang), reply_markup=main_kb(lang))


# ---------------------- App bootstrap ----------------------

async def app():
    setup_logging()

    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    storage = None
    try:
        from redis.asyncio import from_url

        storage = RedisStorage(from_url(settings.REDIS_DSN))
    except Exception:
        from aiogram.fsm.storage.memory import MemoryStorage

        storage = MemoryStorage()

    dp = Dispatcher(storage=storage)

    # middlewares (placeholder)
    set_locale_middleware(dp)

    # handlers
    dp.message.register(start_handler, F.text == "/start")
    dp.message.register(balance_cmd, F.text == "/balance")
    dp.message.register(topup_amount_input_handler, WalletTopUp.waiting_amount)

    dp.callback_query.register(home_handler, F.data == "home")

    dp.callback_query.register(language_handler, F.data == "language")
    dp.callback_query.register(set_language_handler, F.data.startswith("lang:"))

    dp.callback_query.register(wallet_handler, F.data == "wallet")
    dp.callback_query.register(wallet_topup_start_handler, F.data == "w:topup")
    dp.callback_query.register(wallet_history_handler, F.data == "w:history")
    dp.callback_query.register(wallet_topup_approve_handler, F.data.startswith("w:approve:"))
    dp.callback_query.register(wallet_topup_reject_handler, F.data.startswith("w:reject:"))

    dp.callback_query.register(support_handler, F.data == "support")
    dp.callback_query.register(my_orders_handler, F.data == "orders")
    dp.callback_query.register(active_orders_handler, F.data == "active_orders")

    # Temp number flow
    dp.callback_query.register(buy_temp_handler, F.data == "buy_temp")
    dp.callback_query.register(services_page_handler, F.data.startswith("sv:p:"))
    dp.callback_query.register(service_select_handler, F.data.startswith("sv:s:"))
    dp.callback_query.register(countries_page_handler, F.data.startswith("ct:p:"))
    dp.callback_query.register(country_select_handler, F.data.startswith("ct:s:"))
    dp.callback_query.register(operator_select_handler, F.data.startswith("op:"))
    dp.callback_query.register(confirm_buy_handler, F.data == "cf:buy")

    # Status control
    dp.callback_query.register(status_action_handler, F.data.startswith("st:"))

    # Permanent numbers (stub)
    dp.callback_query.register(buy_perm_handler, F.data == "buy_perm")

    await on_startup(bot)

    mode = settings.BOT_MODE.lower()
    if mode == "polling":
        await dp.start_polling(bot)
    else:
        await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(app())
