from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


#######################     ReplyKeyBoards          ##########################################


main_admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Модерация фотографий"),KeyboardButton(text="Рассылка"),KeyboardButton(text="Статистика")],
        [KeyboardButton(text="Очистка баттла"),KeyboardButton(text="Управление администраторами")],
        [KeyboardButton(text="Настройка баттла",)]
    ],
    resize_keyboard=True
)

photo_moderation_admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Принять"), KeyboardButton(text="Отклонить")],
        [KeyboardButton(text="Забанить")],
        [KeyboardButton(text="Назад")]
    ],
    resize_keyboard=True
)

mailing_admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Всем пользователям")],
        [KeyboardButton(text="Участникам, чьи фото находятся на модерации")],
        [KeyboardButton(text="Активным участникам текущего баттла")],
        [KeyboardButton(text="Назад")]
    ],
    resize_keyboard=True
)

managing_admins_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Назначить")],
        [KeyboardButton(text="Cнять права")],
        [KeyboardButton(text="Назад")]
    ],
    resize_keyboard=True
)

tune_battle_admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Продолжительность раунда"),KeyboardButton(text="Сумма приза")],
        [KeyboardButton(text="Минимальное количество голосов")],
        [KeyboardButton(text="Интервал между раундами")],
        [KeyboardButton(text="Назад")]
    ],
    resize_keyboard=True
)


#######################     InlineKeyboards          ##########################################
