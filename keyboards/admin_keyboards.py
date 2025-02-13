import os

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

from filters.isSuperAdmin import is_super_admin

#######################     ReplyKeyBoards          ##########################################


main_super_admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📷 Модерация"),KeyboardButton(text="✉️ Рассылка"),KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="💣 Очистка баттла"),KeyboardButton(text="👮‍♂ Админы")],
        [KeyboardButton(text="⚙ Настройка баттла"),KeyboardButton(text="👥 Список участников")],
        [KeyboardButton(text="📧 Уведомления")]
    ],
    resize_keyboard=True
)

main_admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📷 Модерация"),KeyboardButton(text="✉️ Рассылка"),KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="💣 Очистка баттла"),KeyboardButton(text="👥 Список участников")],
        [KeyboardButton(text="⚙ Настройка баттла"),KeyboardButton(text="📧 Уведомления")]
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
        [KeyboardButton(text="Участникам, ожидающих баттл")],
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
        [KeyboardButton(text="Продолжительность раунда"),KeyboardButton(text="Приз")],
        [KeyboardButton(text="Минимальное количество голосов"), KeyboardButton(text="Интервал между раундами")],
        [KeyboardButton(text="Текущие настройки"),KeyboardButton(text="Время начала баттла")],
        [KeyboardButton(text="Автоматическая победа"),KeyboardButton(text="Добавить информацию к посту")],
        [KeyboardButton(text="Фотографии админа"),KeyboardButton(text="Выложить донабор")],
        [KeyboardButton(text="Назад")]
    ],
    resize_keyboard=True
)

back_admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Назад")]
    ],
    resize_keyboard=True
)


# Клавиатура управления информацией
battle_info_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Изменить сообщение"), KeyboardButton(text="Удалить сообщение")],
        [KeyboardButton(text="Посмотреть сообщение"), KeyboardButton(text="Назад в общие настройки")]
    ],
    resize_keyboard=True
)




admin_photo_keyboard= ReplyKeyboardMarkup(
     keyboard=[
    [KeyboardButton(text="Добавить фотографии")],
    [KeyboardButton(text="Удалить первую фотографию")],
    [KeyboardButton(text="Просмотреть первую фотографию")],
    [KeyboardButton(text="Назад")]
    ],
    resize_keyboard=True
)

#######################     InlineKeyboards          ##########################################


photo_moderation_admin_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Принять ✅",callback_data="Принять"), InlineKeyboardButton(text="Отклонить ❌",callback_data="Отклонить")],
        [InlineKeyboardButton(text="Забанить ☠",callback_data="Забанить")],
    ],
    resize_keyboard=True
)
kick_user_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Кикнуть 💀", callback_data="kick")]
])


confirm_kick_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="✅ Да", callback_data="confirm_kick"),
        InlineKeyboardButton(text="❌ Нет", callback_data="cancel_kick")
    ]
])

def get_main_admin_kb(user_id):
    return main_super_admin_kb if is_super_admin(user_id) else main_admin_kb


def get_admin_keyboard_notif():
    buttons = [
        [KeyboardButton(text="Добавить уведомление"), KeyboardButton(text="Список уведомлений")],
        [KeyboardButton(text="Удалить уведомление"), KeyboardButton(text="Назад")]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    return keyboard

def get_notifications_keyboard():
    buttons = [
        [KeyboardButton(text="Удалить уведомление"), KeyboardButton(text="Назад")]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    return keyboard