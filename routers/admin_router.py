from aiogram import Router, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message

import keyboards
from filters.isAdmin import is_admin
from keyboards.admin_keyboards import *
from database.db import *
from states.admin_states import FSMFillForm

admin_router = Router()
admin_router.message.filter(is_admin)

_bot: Bot = None

def setup_router(dp, bot: Bot):
    global _bot
    _bot = bot

@admin_router.message(Command("admin"),StateFilter(default_state))
async def cmd_admin(message: Message):
    await message.answer("Привет, админ! Ты в админской панели.", reply_markup=main_admin_kb)


@admin_router.message(lambda message: message.text == "Назад")
async def photo_moderation(message: Message):
    await message.answer(text="Назад",reply_markup=main_admin_kb)

@admin_router.message(lambda message: message.text == "Модерация фотографий")
async def photo_moderation(message: Message):
    user = await get_user(message.from_user.id)

    buttle_win = user[1]
    dual_win = user[2]
    plays_buttle = user[3]
    referals = user[4]
    additional_voices = user[5]

    #select photo by user_id
    photo_link="https://static.vecteezy.com/vite/assets/photo-masthead-375-BoK_p8LG.webp"


    await message.answer_photo(
        photo=photo_link,
        caption=
        f"ID: {message.from_user.id}\n" +
        f"Ник: @{message.from_user.username}\n" +
        f"Выйгранных фотобатлов: {buttle_win} \n" +
        f"Общее число фотобатлов: {plays_buttle} \n" +
        f"Выйгранных дуэлей: {dual_win}\n\n" +
        f"Дополнительные голоса: {additional_voices}\n"
        f"Приглашенных рефералов: {referals}",
        reply_markup=photo_moderation_admin_kb
    )


@admin_router.callback_query(lambda query: query.data == "Принять")
async def apply(message: Message):
    await message.answer(text="ok", reply_markup=mailing_admin_kb)

@admin_router.callback_query(lambda query: query.data == "Отклонить")
async def decline(message: Message):
    await message.answer(text="ok", reply_markup=mailing_admin_kb)

@admin_router.callback_query(lambda query: query.data == "Забанить")
async def ban(message: Message):
    await message.answer(text="ok", reply_markup=mailing_admin_kb)


@admin_router.message(lambda message: message.text == "Статистика")
async def statistics(message: Message):
    await message.answer(text=
                         f"Количество зарегистрированных пользователей: \n"+
                         f"Количество отправленных фотографий: \n"+
                         f"Количество активных участников баттла: \n"
                         , reply_markup=main_admin_kb)


@admin_router.message(lambda message: message.text == "Рассылка")
async def mailing(message: Message):
    await message.answer(text="Рассылка",reply_markup=mailing_admin_kb)


##############################              Управление администраторами         ########################################


@admin_router.message(lambda message: message.text == "Управление администраторами",StateFilter(default_state))
async def photo_moderation(message: Message):
    await message.answer(text="Управление администраторами",reply_markup=managing_admins_kb)

@admin_router.message(lambda message: message.text == "Назначить",StateFilter(default_state))
async def enter_duration_of_round(message: Message, state: FSMContext):
    await message.answer(text="Введите id пользователя",reply_markup=tune_battle_admin_kb)
    await state.set_state(FSMFillForm.fill_id_of_new_admin)

#TODO add validation
@admin_router.message(StateFilter(FSMFillForm.fill_id_of_new_admin))
async def get_duration_of_round(message: Message, state: FSMContext):
    await message.answer(text="Данные получены",reply_markup=tune_battle_admin_kb)
    await state.set_state(default_state)

@admin_router.message(lambda message: message.text == "Cнять права",StateFilter(default_state))
async def enter_duration_of_round(message: Message, state: FSMContext):
    await message.answer(text="Введите id администратора",reply_markup=tune_battle_admin_kb)
    await state.set_state(FSMFillForm.fill_id_of_old_admin)

#TODO add validation
@admin_router.message(StateFilter(FSMFillForm.fill_id_of_old_admin))
async def get_duration_of_round(message: Message, state: FSMContext):
    await message.answer(text="Данные получены",reply_markup=tune_battle_admin_kb)
    await state.set_state(default_state)


##############################          Настройка баттла                ####################################

@admin_router.message(lambda message: message.text == "Настройка баттла",StateFilter(default_state))
async def battle_moderation(message: Message):
    await message.answer(text="Настройка баттла",reply_markup=tune_battle_admin_kb)


@admin_router.message(lambda message: message.text == "Продолжительность раунда",StateFilter(default_state))
async def enter_duration_of_round(message: Message, state: FSMContext):
    await message.answer(text="Введите продолжительность раунда",reply_markup=tune_battle_admin_kb)
    await state.set_state(FSMFillForm.fill_duration_of_battle)

#TODO add validation
@admin_router.message(StateFilter(FSMFillForm.fill_duration_of_battle))
async def get_duration_of_round(message: Message, state: FSMContext):
    await message.answer(text="Данные получены",reply_markup=tune_battle_admin_kb)
    await state.set_state(default_state)



@admin_router.message(lambda message: message.text == "Сумма приза",StateFilter(default_state))
async def enter_duration_of_round(message: Message, state: FSMContext):
    await message.answer(text="Введите сумму приза",reply_markup=tune_battle_admin_kb)
    await state.set_state(FSMFillForm.fill_amount_of_prize)

#TODO add validation
@admin_router.message(StateFilter(FSMFillForm.fill_amount_of_prize))
async def get_duration_of_round(message: Message, state: FSMContext):
    await message.answer(text="Данные получены",reply_markup=tune_battle_admin_kb)
    await state.set_state(default_state)


@admin_router.message(lambda message: message.text == "Минимальное количество голосов",StateFilter(default_state))
async def enter_duration_of_round(message: Message, state: FSMContext):
    await message.answer(text="Введите минимальное количество голосов",reply_markup=tune_battle_admin_kb)
    await state.set_state(FSMFillForm.fill_minimal_number_of_votes)

#TODO add validation
@admin_router.message(StateFilter(FSMFillForm.fill_minimal_number_of_votes))
async def get_duration_of_round(message: Message, state: FSMContext):
    await message.answer(text="Данные получены",reply_markup=tune_battle_admin_kb)
    await state.set_state(default_state)


@admin_router.message(lambda message: message.text == "Интервал между раундами",StateFilter(default_state))
async def enter_duration_of_round(message: Message, state: FSMContext):
    await message.answer(text="Введите интервал между раундами",reply_markup=tune_battle_admin_kb)
    await state.set_state(FSMFillForm.fill_interval_between_battles)

#TODO add validation
@admin_router.message(StateFilter(FSMFillForm.fill_interval_between_battles))
async def get_duration_of_round(message: Message, state: FSMContext):
    await message.answer(text="Данные получены",reply_markup=tune_battle_admin_kb)
    await state.set_state(default_state)

#@admin_router.message()

# --------------


# --------------
