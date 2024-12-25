from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message

from filters.isAdmin import is_admin

admin_router = Router()
admin_router.message.filter(is_admin)

_bot: Bot = None

def setup_router(dp, bot: Bot):
    global _bot
    _bot = bot

@admin_router.message(Command("admin"))
async def cmd_admin(message: Message):
    await message.answer("Привет, админ! Ты в админской панели.")
# --------------
