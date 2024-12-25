from aiogram import Router, Bot
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message, MessageOriginChannel

from states.user_states import FSMFillForm
from filters.isAdmin import is_admin

_bot: Bot = None  # Placeholder for the bot instance

def setup_router(dp, bot: Bot):
    global _bot
    _bot = bot

user_router = Router()
user_router.message.filter(lambda message: not is_admin(message))



# -----------
# хэндлеры для канала
@user_router.channel_post()
async def send_message(message: MessageOriginChannel):
    await _bot.send_message(chat_id=message.chat.id, text = 'Привет!')
# -----------

#-----------
# Команды для пользователей
@user_router.message(CommandStart() ,StateFilter(default_state))
async def cmd_start(message: Message):
    await message.answer("Привет! Отправь мне /battle для участия в баттле")


@user_router.message(Command("battle"), StateFilter(default_state))
async def cmd_help(message: Message, state: FSMContext):
    await message.answer("Отправь мне свое фото для баттла.")
    await state.set_state(FSMFillForm.fill_photo)


@user_router.message()
async def echo(message: Message):
    await message.answer(f"Вы сказали: {message.text}")



