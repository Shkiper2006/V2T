from __future__ import annotations

from collections.abc import Mapping

DEFAULT_LOCALE = "ru"

TRANSLATIONS: dict[str, dict[str, str]] = {
    "ru": {
        "welcome": "Добро пожаловать! Ниже быстрый старт 👇",
        "start_step_google_connected": "✅ Google подключен.",
        "start_step_google_missing": "⚠️ Google не подключен. Нажмите «Подключить Google».",
        "start_step_tariff": "2) Текущий тариф: {tariff}.",
        "start_step_quota": "3) Остаток лимита в этом месяце: {remaining}/{quota} сообщений.",
        "start_step_end": "Выберите действие в меню или используйте команды /tariffs и /subscribe.",
        "menu_tariffs": "Тарифы",
        "menu_connect_google": "Подключить Google",
        "menu_history": "История",
        "menu_subscription": "Подписка",
        "tariffs_title": "Выберите тариф:",
        "subscribe_title": "Выберите тариф для подписки:",
        "tariff_line": "{title}: {price}₽/мес · {quota} сообщений · до {max_audio}s",
        "payment_title": "Выберите способ оплаты:",
        "payment_link": "Оплатить {tariff}: {url}\nПровайдер: {provider}",
        "connect_google_message": "Подключите Google по персональной ссылке:\n{url}",
        "history_empty": "История заметок пока пуста.",
        "history_header": "🗂 Последние {count} заметок:",
        "help": "Доступные команды:\n/start\n/subscribe\n/tariffs\n/connect_google\n/history\n/help",
        "unsupported_callback": "Неизвестное действие. Попробуйте снова.",
    }
}


def get_locale(language_code: str | None) -> str:
    if not language_code:
        return DEFAULT_LOCALE

    normalized = language_code.lower().split("-")[0]
    if normalized in TRANSLATIONS:
        return normalized

    return DEFAULT_LOCALE


def t(key: str, locale: str | None = None, **kwargs: str | int) -> str:
    selected_locale = locale or DEFAULT_LOCALE
    locale_payload: Mapping[str, str] = TRANSLATIONS.get(selected_locale, TRANSLATIONS[DEFAULT_LOCALE])
    template = locale_payload.get(key) or TRANSLATIONS[DEFAULT_LOCALE].get(key, key)
    return template.format(**kwargs)
