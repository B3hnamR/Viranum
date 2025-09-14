from aiogram.utils.keyboard import InlineKeyboardBuilder


def status_kb_provider(lang: str, provider_key: str, number_id: str, t=lambda l, fa, en, ru: en):
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "لغو", "Cancel", "Отмена"), callback_data=f"st:cancel:{provider_key}:{number_id}")
    b.button(text=t(lang, "تکرار", "Repeat", "Повтор"), callback_data=f"st:repeat:{provider_key}:{number_id}")
    b.button(text=t(lang, "بستن", "Close", "Закрыть"), callback_data=f"st:close:{provider_key}:{number_id}")
    b.button(text=t(lang, "بروزرسانی", "Refresh", "Обновить"), callback_data=f"st:refresh:{provider_key}:{number_id}")
    b.adjust(3, 1)
    return b.as_markup()

