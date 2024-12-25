from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, PhotoSize,MessageOriginChannel)
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config.config import load_config
import asyncio
# import logging
import os

dirname = os.path.dirname(__file__)
filename = os.path.join(dirname, 'config/config.env')
config = load_config(filename)

# Инициализируем хранилище (создаем экземпляр класса MemoryStorage)
storage = MemoryStorage()

# Создаем объекты бота и диспетчера
bot = Bot(token=config.tg_bot.token)
dp = Dispatcher(storage=storage)

ADMIN_ID = []

dp = Dispatcher()

# Создаем роутеры
user_router = Router()
admin_router = Router()

class FSMFillForm(StatesGroup):
    fill_photo = State()

# Фильтр для определения администратора
def is_admin(message: Message) -> bool:
    return message.from_user.id in ADMIN_ID

# Добавляем фильтры к роутерам
user_router.message.filter(lambda message: not is_admin(message))
admin_router.message.filter(is_admin)


# хэндлер для канала
@user_router.channel_post()
async def send_message(message: MessageOriginChannel):
    await bot.send_message(chat_id=message.chat.id, text = 'Привет!')


# Команды для пользователей
@user_router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Привет! Отправь мне /battl для участия в баттле")


@dp.message(Command(commands='cancel'))
async def process_cancel_command(message: Message):
    await message.answer(
        text='Отменять нечего. Вы регистрации на баттл\n\n'
             'Чтобы перейти к заполнению анкеты - '
             'отправьте команду /battl'
    )


@dp.message(Command(commands='cancel'), ~StateFilter(default_state))
async def process_cancel_command_state(message: Message, state: FSMContext):
    await message.answer(
        text='Вы вышли из регистрации на баттл\n\n'
             'Чтобы снова перейти к заполнению анкеты - '
             'отправьте команду /battl'
    )
    
    await state.clear()
    
    
@user_router.message(Command("battle"))
async def cmd_help(message: Message):
    await message.answer("Отправь мне свое фото для баттла.")
    
    
    
@user_router.message(Command("battle"))
async def cmd_help(message: Message, state: FSMContext):
    await message.answer("Отправь мне свое фото для баттла.")
    await state.set_state(FSMFillForm.fill_photo)
    
    
    
@dp.message(StateFilter(FSMFillForm.fill_photo),
            F.photo[-1].as_('largest_photo'))
async def process_photo_sent(message: Message,
                             state: FSMContext,
                             largest_photo: PhotoSize):

    await state.update_data(
        photo_unique_id=largest_photo.file_unique_id,
        photo_id=largest_photo.file_id
    )
    #!!!! запрос в бд !!!!
    await message.answer(
        text='Спасибо!\n\nОжидайте сообщения о начале раунда'
    )
    
    
@dp.message(StateFilter(FSMFillForm.fill_photo))
async def warning_not_photo(message: Message):
    await message.answer(
        text='Пожалуйста, на этом шаге отправьте '
             'ваше фото\n\nЕсли вы хотите прервать '
             'заполнение анкеты - отправьте команду /cancel'
    )


# Команды для администратора
@admin_router.message(Command("admin"))
async def cmd_admin(message: Message):
    await message.answer("Привет, админ! Ты в админской панели.")

# Обработка всех остальных сообщений
@user_router.message()
async def echo(message: Message):
    await message.answer(f"Вы сказали: {message.text}")

@admin_router.message()
async def admin_echo(message: Message):
    await message.answer(f"Админ сказал: {message.text}")

# Регистрируем роутеры в диспетчере
dp.include_router(admin_router)
dp.include_router(user_router)

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())