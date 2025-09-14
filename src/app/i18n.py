from typing import Dict

# Minimal i18n stub with in-memory dicts for MVP. Later replace with gettext .po files.

_STRINGS: Dict[str, Dict[str, str]] = {
    "fa": {
        "greet": "به ربات ویرانام خوش آمدید. از منوی زیر انتخاب کنید:",
        "choose_language": "زبان را انتخاب کنید:",
        "language_set": "زبان تنظیم شد.",
        "wallet.info": "کیف پول: به زودی امکانات شارژ و تاریخچه اضافه می‌شود.",
        "support.info": "پشتیبانی: راهنما و ارتباط بزودی.",
        "buy_temp.stub": "خرید شماره عادی: به زودی لیست سرویس/کشور/اپراتور افزوده می‌شود.",
        "buy_perm.stub": "خرید شماره دائمی: به زودی لیست رُند/نیمه‌رُند افزوده می‌شود.",
        "menu.buy_temp": "خرید شماره عادی",
        "menu.buy_perm": "خرید شماره دائمی",
        "menu.wallet": "کیف پول",
        "menu.support": "راهنما و پشتیبانی",
        "menu.language": "تنظیمات زبان",
        "menu.orders": "سفارش‌های من",
        "menu.active": "سفارش‌های فعال",
    },
    "en": {
        "greet": "Welcome to Viranum bot. Choose an option:",
        "choose_language": "Choose your language:",
        "language_set": "Language has been set.",
        "wallet.info": "Wallet: Top-up and history coming soon.",
        "support.info": "Support: Help and contact coming soon.",
        "buy_temp.stub": "Temporary number purchase: service/country/operator list coming soon.",
        "buy_perm.stub": "Permanent numbers: round/half-round list coming soon.",
        "menu.buy_temp": "Buy Temporary Number",
        "menu.buy_perm": "Buy Permanent Number",
        "menu.wallet": "Wallet",
        "menu.support": "Support",
        "menu.language": "Language Settings",
        "menu.providers": "Providers",
        "menu.orders": "My purchases",
        "menu.active": "Active orders",
    },
    "ru": {
        "greet": "Добро пожаловать в бота Viranum. Выберите действие:",
        "choose_language": "Выберите язык:",
        "language_set": "Язык установлен.",
        "wallet.info": "Кошелёк: пополнение и история скоро.",
        "support.info": "Поддержка: помощь и контакты скоро.",
        "buy_temp.stub": "Покупка временно��о номера: список сервис/страна/оператор скоро.",
        "buy_perm.stub": "Постоянные номера: список красивых/полукрасивых скоро.",
        "menu.buy_temp": "Купить временный номер",
        "menu.buy_perm": "Купить постоянный номер",
        "menu.wallet": "Кошелёк",
        "menu.support": "Поддержка",
        "menu.language": "Язык",
        "menu.orders": "Мои покупки",
        "menu.active": "Активные покупки",
    },
}


def tr(key: str, lang: str) -> str:
    lang = lang if lang in _STRINGS else "fa"
    return _STRINGS.get(lang, {}).get(key, _STRINGS["fa"].get(key, key))


def set_locale_middleware(dp):
    # Placeholder for real middleware when moving to gettext
    return dp
