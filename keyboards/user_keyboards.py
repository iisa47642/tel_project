import os
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from config.config import load_config



def get_config():
        dirname = os.path.dirname(__file__)
        filename = os.path.abspath(os.path.join(dirname, '..', 'config/config.env'))
        config = load_config(filename)
        return config
        # return config.tg_bot.channel_link

    
#######################     ReplyKeyBoards          ##########################################

main_user_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔥Принять участие")],
        [KeyboardButton(text="🎗️Профиль"),KeyboardButton(text="✨Наши каналы и спонсоры")],
        [KeyboardButton(text="🍪Получить голоса"),KeyboardButton(text="⚡️Поддержка")]
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
        [InlineKeyboardButton(text="Правила",url=get_config().tg_bot.rule_link),InlineKeyboardButton(text="Канал",url=get_config().tg_bot.channel_link)],
        [InlineKeyboardButton(text="Связь с администратором",url=get_config().tg_bot.user_link)]
    ],
    resize_keyboard=True
)