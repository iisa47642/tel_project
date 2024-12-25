# bot.py
from aiogram import Bot, Dispatcher, F
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, PhotoSize
from config.config import load_config
import asyncio
import logging
import os
from routers import admin_router
from routers import user_router
from states.user_states import FSMFillForm
from database.db import *
from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable
import sqlite3
async def on_startup():
    await create_tables()


dirname = os.path.dirname(__file__)
filename = os.path.join(dirname, 'config/config.env')
config = load_config(filename)



# Инициализация бота и диспетчера с хранилищем состояний
bot = Bot(token=config.tg_bot.token)
# Используем MemoryStorage для хранения состояний
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

admin_router.setup_router(dp, bot)
user_router.setup_router(dp, bot)

# Подключаем роутер формы
dp.include_router(
    admin_router.admin_router
)

dp.include_router(
    user_router.user_router
)

class UserCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        existing_user = cursor.fetchone()

        if not existing_user and event.text != '/start':
            await event.answer("Пожалуйста, используйте команду /start, чтобы начать работу с ботом.")
            return

        return await handler(event, data)



@dp.message(Command(commands='cancel'), StateFilter(default_state))
async def process_cancel_command(message: Message):
    await message.answer(
        text='Отменять нечего. Вы регистрации на баттл\n\n'
             'Чтобы перейти к заполнению анкеты - '
             'отправьте команду /battle'
    )


@dp.message(Command(commands='cancel'), ~StateFilter(default_state))
async def process_cancel_command_state(message: Message, state: FSMContext):
    await message.answer(
        text='Вы вышли из регистрации на баттл\n\n'
             'Чтобы снова перейти к заполнению анкеты - '
             'отправьте команду /battle'
    )

    await state.clear()


@dp.message(StateFilter(FSMFillForm.fill_photo),
            F.photo[-1].as_('largest_photo'))
async def process_photo_sent(message: Message,
                             state: FSMContext,
                             largest_photo: PhotoSize):
    await state.update_data(
        photo_unique_id=largest_photo.file_unique_id,
        photo_id=largest_photo.file_id
    )
    # !!!! запрос в бд на добавление в батл !!!!
    await message.answer(
        text='Спасибо!\n\nОжидайте сообщения о начале раунда'
    )
    await create_user_in_batl()

    await state.clear()


@dp.message(StateFilter(FSMFillForm.fill_photo))
async def warning_not_photo(message: Message):
    await message.answer(
        text='Пожалуйста, на этом шаге отправьте '
             'ваше фото\n\nЕсли вы хотите прервать '
             'заполнение анкеты - отправьте команду /cancel'
    )


# ---------------


async def main():
    user_router.user_router.message.middleware(UserCheckMiddleware())
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    await on_startup()
    # Запускаем бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())