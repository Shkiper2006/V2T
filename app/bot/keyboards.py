from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Тарифы"), KeyboardButton(text="Подключить Google")],
            [KeyboardButton(text="История"), KeyboardButton(text="Подписка")],
        ],
        resize_keyboard=True,
    )


def tariff_select_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Free", callback_data="plan:free")
    kb.button(text="Basic", callback_data="plan:basic")
    kb.button(text="Pro", callback_data="plan:pro")
    kb.button(text="Business", callback_data="plan:business")
    kb.adjust(2)
    return kb.as_markup()


def payment_select_keyboard(tariff_code: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Оплатить", callback_data=f"pay:{tariff_code}")
    return kb.as_markup()
