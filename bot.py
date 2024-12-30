# bot.py
from aiogram import Bot, Dispatcher, F
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.fsm.storage.memory import MemoryStorage
from middlewares.middlewares import ModeMiddleware, ThrottlingMiddleware, UserCheckMiddleware
from aiogram.types import Message
from config.config import load_config
from routers import admin_router, channel_router
from routers import user_router
from states.user_states import FSMFillForm
from database.db import *
from tasks import scheduler_manager
from middlewares.middlewares import setup_router as setup_middleware
import asyncio
import logging
import os

from tasks.task_handlers import TaskManager


dirname = os.path.dirname(__file__)
filename = os.path.join(dirname, 'config/config.env')
config = load_config(filename)

async def on_shutdown(dp):
    scheduler_manager.shutdown()

# Инициализация бота и диспетчера с хранилищем состояний
bot = Bot(token=config.tg_bot.token)
# Используем MemoryStorage для хранения состояний
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

admin_router.setup_router(dp, bot)
user_router.setup_router(dp, bot)
channel_router.setup_router(dp,bot)

# Подключаем роутер формы
dp.include_router(
    admin_router.admin_router
)

dp.include_router(
    user_router.user_router
)
dp.include_router(
    channel_router.channel_router
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
    dp.message.middleware(ThrottlingMiddleware())
    task_manager = TaskManager()
    await task_manager.initialize()  # Инициализируем настройки
    
    # Настраиваем middleware с task_manager
    setup_middleware(dp, bot, task_manager)
    dp.update.outer_middleware(ModeMiddleware())
    user_router.user_router.message.middleware(UserCheckMiddleware())

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    await create_tables()
    # Запускаем бота
    scheduler_manager.task_manager = task_manager
    await scheduler_manager.setup(bot)  # Настраиваем планировщик
    
    try:
        await dp.start_polling(bot)  # 1
    finally:
        await bot.session.close()    # 2
        scheduler_manager.shutdown()  # 3


if __name__ == "__main__":
    asyncio.run(main())