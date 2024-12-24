# keyboards/form_kb.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Клавиатура для выбора пола
gender_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Мужской"),
            KeyboardButton(text="Женский")
        ],
        [KeyboardButton(text="Отмена")]
    ],
    resize_keyboard=True
)

# Клавиатура для подтверждения
confirm_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Подтвердить"),
            KeyboardButton(text="Отменить")
        ]
    ],
    resize_keyboard=True
)