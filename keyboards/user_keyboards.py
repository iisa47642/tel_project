from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

#######################     ReplyKeyBoards          ##########################################

main_user_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Поддержка",url="https://www.google.com/")],
        [KeyboardButton(text="Принять участие")],
        [KeyboardButton(text="Получить голоса"),KeyboardButton(text="Профиль")]
    ],
    resize_keyboard=True
)


#######################     InlineKeyboards          ##########################################


vote_user_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Право",callback_data="Право"),InlineKeyboardButton(text="Лево",callback_data="Лево")],
    ],
    resize_keyboard=True
)

support_user_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Правила",url="https://telegra.ph/Pravila-fotobatla-11-25"),InlineKeyboardButton(text="Чат",url="https://www.google.com/")],
        [InlineKeyboardButton(text="Связь с модератором",url="https://t.me/NexTeaJr")]
    ],
    resize_keyboard=True
)