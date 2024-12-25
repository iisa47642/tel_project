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


@admin_router.message(lambda message: message.text == "Назад")
async def photo_moderation(message: Message):
    await message.answer(text="Назад",reply_markup=main_admin_kb)

@admin_router.message(lambda message: message.text == "Модерация фотографий")
async def photo_moderation(message: Message):
    await message.answer(text="Модерация фотографий",reply_markup=photo_moderation_admin_kb)

@admin_router.message(lambda message: message.text == "Рассылка")
async def mailing(message: Message):
    await message.answer(text="Рассылка",reply_markup=mailing_admin_kb)

@admin_router.message(lambda message: message.text == "Управление администраторами")
async def photo_moderation(message: Message):
    await message.answer(text="Управление администраторами",reply_markup=managing_admins_kb)

@admin_router.message(lambda message: message.text == "Настройка баттла")
async def photo_moderation(message: Message):
    await message.answer(text="Настройка баттла",reply_markup=tune_battle_admin_kb)


# --------------


# --------------
