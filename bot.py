# bot.py
from aiogram import Bot, Dispatcher, F
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.fsm.storage.memory import MemoryStorage
from middlewares.middlewares import UserCheckMiddleware
from aiogram.types import Message
from config.config import load_config
from routers import admin_router
from routers import user_router
from states.user_states import FSMFillForm
from database.db import *

import asyncio
import logging
import os


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




# ---------------


async def main():
    user_router.user_router.message.middleware(UserCheckMiddleware())
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    await create_tables()
    # Запускаем бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())