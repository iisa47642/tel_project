import os

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

from filters.isSuperAdmin import is_super_admin

#######################     ReplyKeyBoards          ##########################################


main_super_admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Модерация фотографий"),KeyboardButton(text="Рассылка"),KeyboardButton(text="Статистика")],
        [KeyboardButton(text="Очистка баттла"),KeyboardButton(text="Управление администраторами")],
        [KeyboardButton(text="Настройка баттла",),KeyboardButton(text="Список участников")]
    ],
    resize_keyboard=True
)

main_admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Модерация фотографий"),KeyboardButton(text="Рассылка"),KeyboardButton(text="Статистика")],
        [KeyboardButton(text="Очистка баттла"),KeyboardButton(text="Список участников")],
        [KeyboardButton(text="Настройка баттла",)]
    ],
    resize_keyboard=True
)

admin_channel_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Добавить канал")],
        [KeyboardButton(text="Удалить канал")],
        [KeyboardButton(text="Назад в меню")]
    ],
    resize_keyboard=True
)


# photo_moderation_admin_kb = ReplyKeyboardMarkup(
#     keyboard=[
#         [KeyboardButton(text="Принять"), KeyboardButton(text="Отклонить")],
#         [KeyboardButton(text="Забанить")],
#         [KeyboardButton(text="Назад")]
#     ],
#     resize_keyboard=True
# )

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
        [KeyboardButton(text="Минимальное количество голосов"), KeyboardButton(text="Интервал между раундами")],
        [KeyboardButton(text="Текущие настройки"),KeyboardButton(text="Время начала баттла")],
        [KeyboardButton(text="Автоматическая победа"),KeyboardButton(text="Назад")]
    ],
    resize_keyboard=True
)

back_admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Назад")]
    ],
    resize_keyboard=True
)


#######################     InlineKeyboards          ##########################################


photo_moderation_admin_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Принять",callback_data="Принять"), InlineKeyboardButton(text="Отклонить",callback_data="Отклонить")],
        [InlineKeyboardButton(text="Забанить",callback_data="Забанить")],
    ],
    resize_keyboard=True
)
kick_user_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Кикнуть", callback_data="kick")]
])


confirm_kick_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="✅ Да", callback_data="confirm_kick"),
        InlineKeyboardButton(text="❌ Нет", callback_data="cancel_kick")
    ]
])

def get_main_admin_kb(user_id):
    return main_super_admin_kb if is_super_admin(user_id) else main_admin_kb