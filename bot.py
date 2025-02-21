# bot.py
from aiogram import Bot, Dispatcher
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.fsm.storage.memory import MemoryStorage
from middlewares.middlewares import AlbumsMiddleware, ModeMiddleware, ThrottlingMiddleware, UserCheckMiddleware
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
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from typing import List
from tasks.task_handlers import TaskManager
from utils.task_manager import TaskManagerInstance


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


USER_COMMANDS: List[BotCommand] = [
    BotCommand(command="start", description="Меню"),
    BotCommand(command="battle", description="Регистрация на баттл")
    # Добавьте другие команды для пользователей
]

ADMIN_COMMANDS: List[BotCommand] = [
    BotCommand(command="start", description="Меню"),
    BotCommand(command="battle", description="Регистрация на баттл"),
    BotCommand(command="admin", description="Админ-панель")
    # Добавьте другие админские команды
]

async def setup_bot_commands(bot: Bot):
    """
    Установка команд бота для разных типов пользователей
    """
    # Устанавливаем базовые команды для всех пользователей
    try:
        await bot.set_my_commands(
            USER_COMMANDS,
            scope=BotCommandScopeDefault()
        )

        SUPER_ADMIN_IDS = config.tg_bot.super_admin_ids
        ADMIN_IDS = await select_all_admins()
        ADMIN_IDS = [i[0] for i in ADMIN_IDS]
        ADMIN_IDS += SUPER_ADMIN_IDS
        for admin_id in ADMIN_IDS:
            try:
                await bot.set_my_commands(
                    ADMIN_COMMANDS,
                    scope=BotCommandScopeChat(chat_id=admin_id)
                )
            except Exception as e:
                logging.error(f"Failed to set admin commands for {admin_id}: {e}")
    except Exception as e:
        logging.error(f"Error setting up bot commands: {e}")
@dp.message(Command(commands='cancel'), StateFilter(default_state))
async def process_cancel_command(message: Message):
    await message.answer(
        text='Отменять нечего. Вы ничего не заполняете\n\n'
    )


@dp.message(Command(commands='cancel'), ~StateFilter(default_state))
async def process_cancel_command_state(message: Message, state: FSMContext):
    await message.answer(
        text='Вы больше не заполняете форму\n\n'
    )

    await state.clear()

async def update_bot_commands(bot: Bot):
    await setup_bot_commands(bot)


# ---------------



async def main():
    updates = await bot.get_updates(offset=-1)
    if updates:
        last_update_id = updates[-1].update_id
        await bot.get_updates(offset=last_update_id + 1)
    await create_tables()
    await channel_router.make_some_magic()
    SUPER_ADMIN_IDS = config.tg_bot.super_admin_ids
    ADMIN_IDS = await select_all_admins()
    ADMIN_IDS = [i[0] for i in ADMIN_IDS]
    ADMIN_IDS += SUPER_ADMIN_IDS
    message_throttling = ThrottlingMiddleware(limit=1.0, admin_ids=ADMIN_IDS)  # 2 секунды для сообщений
    callback_throttling = ThrottlingMiddleware(limit=1.0, admin_ids=ADMIN_IDS)
    
    dp.message.middleware(message_throttling)
    dp.callback_query.middleware(callback_throttling)
    dp.message.middleware(AlbumsMiddleware(2))

    global task_manager
    task_manager = TaskManager()
    await task_manager.initialize()  # Инициализируем настройки
    TaskManagerInstance.set_instance(task_manager)
    # Настраиваем middleware с task_manager
    setup_middleware(dp, bot, task_manager)
    dp.update.outer_middleware(ModeMiddleware())
    user_router.user_router.message.middleware(UserCheckMiddleware())

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),  # Логи будут записываться в файл bot.log
        logging.StreamHandler()  # Логи также будут выводиться в консоль
    ])
    #await create_tables()
    # Запускаем бота
    scheduler_manager.task_manager = task_manager
    await scheduler_manager.setup(bot)  # Настраиваем планировщик
    await setup_bot_commands(bot)
    try:
        await dp.start_polling(bot, offset=-1, allowed_updates=[])  # 1
    finally:
        try:
            # Очищаем общие команды
            await bot.delete_my_commands(scope=BotCommandScopeDefault())
            
            # Очищаем команды для всех известных админов
            for admin_id in ADMIN_IDS:
                try:
                    await bot.delete_my_commands(
                        scope=BotCommandScopeChat(chat_id=admin_id)
                    )
                except Exception as e:
                    logging.error(f"Failed to delete commands for admin {admin_id}: {e}")
                    
        except Exception as e:
            logging.error(f"Error clearing bot commands: {e}")
        await bot.session.close()    # 2
        scheduler_manager.shutdown()  # 3


if __name__ == "__main__":
    asyncio.run(main())