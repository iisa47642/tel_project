import os
import re

from aiogram import Router, Bot, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message, CallbackQuery

from config.config import load_config
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

async def gen_mode_aplic(application):
    if application:
        user_id = application[0][0]
        user = await get_user(user_id)
        
        buttle_win = user[1]
        dual_win = user[2]
        plays_buttle = user[3]
        referals = user[4]
        additional_voices = user[5]

        #select photo by user_id
        
        photo_id = application[0][1]


        
        photo=photo_id,
        caption=f"ID: {user_id}\n" + f"Ник: @{await get_username_by_id(user_id)}\n" +f"Выйгранных фотобатлов: {buttle_win} \n" + f"Общее число фотобатлов: {plays_buttle} \n" + f"Выйгранных дуэлей: {dual_win}\n\n" + f"Дополнительные голоса: {additional_voices}\n" f"Приглашенных рефералов: {referals}"
        reply_markup=photo_moderation_admin_kb
        return (photo[0],caption,reply_markup)


async def get_username_by_id(user_id: int):
    """Получает никнейм пользователя по его ID."""
    try:
        chat = await _bot.get_chat(user_id)
        return chat.username
    except Exception as e:
        print(f"Ошибка при получении информации о пользователе: {e}")
        return None

#####################################               Общее                          ##########################################


@admin_router.message(Command("admin"),StateFilter(default_state))
async def cmd_admin(message: Message):
    await message.answer("Привет, админ! Ты в админской панели.", reply_markup=get_main_admin_kb(message.from_user.id))


@admin_router.message(lambda message: message.text == "Назад")
async def photo_moderation(message: Message, state: FSMContext):
    await message.answer(text="Назад",reply_markup=get_main_admin_kb(message.from_user.id))
    await state.clear()

#########################                       Модерация фотографий                ##########################################

@admin_router.message(lambda message: message.text == "Модерация фотографий")
async def photo_moderation(message: Message):
    application = (await select_all_applications())
    if application:
        values = await gen_mode_aplic(application)
        photo = values[0]
        caption = values[1]
        reply_markup = values[2]
        await message.answer_photo(photo=photo,caption=caption, reply_markup=reply_markup)
    else:
        await message.answer(text = 'Заявок нет')


@admin_router.callback_query(lambda query: query.data == "Принять")
async def apply(call: CallbackQuery):
    await call.answer(text="ok", reply_markup=mailing_admin_kb)
    application = (await select_all_applications())
    all_application = application
    delMessage = 0 if len(application) > 1 else 1
    if len(application) != 0:
        application = application[0]
        user_id = application[0]
        photo_id = application[1]
        if delMessage:
            await _bot.send_message(call.from_user.id, "Заявки закончились")
            await call.message.delete()
        await create_user_in_batl(user_id,photo_id, 'user')
        
        await delete_application(user_id)
        # /////
        values = await gen_mode_aplic(all_application[1:])
        photo = values[0]
        caption = values[1]
        reply_markup = values[2]
        await call.message.edit_caption(photo = photo,caption=caption, reply_markup=reply_markup)
    else:
        await _bot.send_message(call.from_user.id, "Заявки закончились")
    


@admin_router.callback_query(lambda query: query.data == "Отклонить")
async def decline(call: CallbackQuery):
    await   call.answer(text="ok", reply_markup=mailing_admin_kb)
    application = (await select_all_applications())
    all_application = application
    delMessage = 0 if len(application) > 1 else 1
    if len(application) != 0:
        application = application[0]
        user_id = application[0]
        if delMessage:
            await _bot.send_message(call.from_user.id, "Заявки закончились")
            await call.message.delete()
        await delete_application(user_id)
        values = await gen_mode_aplic(all_application[1:])
        photo = values[0]
        caption = values[1]
        reply_markup = values[2]
        await call.message.edit_caption(photo = photo,caption=caption, reply_markup=reply_markup)
    else:
        await _bot.send_message(call.from_user.id, "Заявки закончились")


@admin_router.callback_query(lambda query: query.data == "Забанить")
async def ban(call: CallbackQuery):
    await call.answer(text="ok", reply_markup=mailing_admin_kb)
    application = (await select_all_applications())
    all_application = application
    delMessage = 0 if len(application) > 1 else 1
    if len(application) != 0:
        application = application[0]
        user_id = application[0]
        if delMessage:
            await _bot.send_message(call.from_user.id, "Заявки закончились")
            await call.message.delete()
        await edit_user(user_id,'is_ban',1)
        await delete_application(user_id)
        values = await gen_mode_aplic(all_application[1:])
        photo = values[0]
        caption = values[1]
        reply_markup = values[2]
        await call.message.edit_caption(photo = photo,caption=caption, reply_markup=reply_markup)
    else:
        await _bot.send_message(call.from_user.id, "Заявки закончились")


####################################                    Статистика                      #################################


@admin_router.message(lambda message: message.text == "Статистика")
async def statistics(message: Message):
    quantity_users = len(await get_all_users())
    quantity_aplic = len(await select_all_applications())
    quantity_battle = len(await select_all_battle())
    
    
    await message.answer(text=
                         f"Количество зарегистрированных пользователей: {quantity_users}\n"+
                         f"Количество необработанных заявок: {quantity_aplic}\n"+
                         f"Количество активных участников баттла: {quantity_battle}\n"
                         , reply_markup=get_main_admin_kb(message.from_user.id))


####################################                    Очистка баттла                      #################################


@admin_router.message(lambda message: message.text == "Очистка баттла")
async def clear_battle(message: Message):
    await message.answer(text="Все пользователи удалены из батла",reply_markup=get_main_admin_kb(message.from_user.id))
    await delete_applications()
    await delete_users_in_batl()
    
    


####################################                    Рассылка                      #################################


@admin_router.message(lambda message: message.text == "Рассылка")
async def mailing(message: Message):
    await message.answer(text="Рассылка",reply_markup=mailing_admin_kb)

@admin_router.message(lambda message: message.text == "Всем пользователям" ,StateFilter(default_state))
async def mailing_everybody(message: Message, state: FSMContext):
    await message.answer(text="Введите сообщение для рассылки",reply_markup=back_admin_kb)
    await state.set_state(FSMFillForm.fill_message_for_all)

@admin_router.message(F.text,StateFilter(FSMFillForm.fill_message_for_all))
async def enter_mailing_everybody(message: Message, state: FSMContext):
    txt = message.text
    # возможно, исключить админов из списка
    users = await get_all_users()
    users_id = [user[0] for user in users]
    for user_id in users_id:
        await _bot.send_message(user_id,text=txt)
    await message.answer(text="Отправили всем пользователям",reply_markup=mailing_admin_kb)
    await state.clear()
    
@admin_router.message(lambda message: message.text == "Участникам, чьи фото находятся на модерации",StateFilter(default_state))
async def mailing_on_moderation(message: Message, state: FSMContext):
    await message.answer(text="Введите сообщение для рассылки",reply_markup=back_admin_kb)
    await state.set_state(FSMFillForm.fill_message_for_moder)

@admin_router.message(F.text,StateFilter(FSMFillForm.fill_message_for_moder))
async def enter_mailing_on_moderation(message: Message, state: FSMContext):
    txt = message.text
    # возможно, исключить админов из списка
    users = await select_all_applications()
    users_id = [user[0] for user in users]
    for user_id in users_id:
        await _bot.send_message(user_id,text=txt)
    await message.answer(text="Отправили всем участникам, чьи фото находятся на модерации",reply_markup=mailing_admin_kb)
    await state.clear()

@admin_router.message(lambda message: message.text == "Активным участникам текущего баттла",StateFilter(default_state))
async def mailing_active_participants(message: Message, state: FSMContext):
    await message.answer(text="Введите сообщение для рассылки",reply_markup=back_admin_kb)
    await state.set_state(FSMFillForm.fill_message_for_user_on_battle)
    
@admin_router.message(F.text,StateFilter(FSMFillForm.fill_message_for_user_on_battle))
async def enter_mailing_on_moderation(message: Message, state: FSMContext):
    txt = message.text
    # возможно, исключить админов из списка
    users = await select_all_battle()
    users_id = [user[0] for user in users]
    for user_id in users_id:
        await _bot.send_message(user_id,text=txt)
    await message.answer(text="Отправили всем активным участникам текущего баттла", reply_markup=mailing_admin_kb)
    await state.clear()
    
@admin_router.message(StateFilter(FSMFillForm.fill_message_for_all))
@admin_router.message(StateFilter(FSMFillForm.fill_message_for_moder))
@admin_router.message(StateFilter(FSMFillForm.fill_message_for_user_on_battle))
async def enter_correct_data(message: Message):
    await message.answer('Пожалуйста, на этом шаге отправьте '
             'текстовое сообщение\n\nЕсли вы хотите прервать '
             'заполнение - нажмите "Назад"',reply_markup=mailing_admin_kb)

##############################              Управление администраторами         ########################################


@admin_router.message(lambda message: message.text == "Управление администраторами",StateFilter(default_state))
async def photo_moderation(message: Message):
    if not is_super_admin(message.from_user.id): return
    await message.answer(text="Управление администраторами",reply_markup=managing_admins_kb)

@admin_router.message(lambda message: message.text == "Назначить",StateFilter(default_state))
async def enter_duration_of_round(message: Message, state: FSMContext):
    if not is_super_admin(message.from_user.id): return
    await message.answer(text="Введите id пользователя",reply_markup=back_admin_kb)
    await state.set_state(FSMFillForm.fill_id_of_new_admin)

@admin_router.message(StateFilter(FSMFillForm.fill_id_of_new_admin))
async def get_duration_of_round(message: Message, state: FSMContext):
    await message.answer(text="Данные получены",reply_markup=managing_admins_kb)
    await state.clear()

@admin_router.message(lambda message: message.text == "Cнять права",StateFilter(default_state))
async def enter_duration_of_round(message: Message, state: FSMContext):
    if not is_super_admin(message.from_user.id): return
    await message.answer(text="Введите id администратора",reply_markup=back_admin_kb)
    await state.set_state(FSMFillForm.fill_id_of_old_admin)

#TODO add validation
@admin_router.message(StateFilter(FSMFillForm.fill_id_of_old_admin))
async def get_duration_of_round(message: Message, state: FSMContext):
    await message.answer(text="Данные получены",reply_markup=managing_admins_kb)
    await state.clear()


##############################          Настройка баттла                ####################################

@admin_router.message(lambda message: message.text == "Настройка баттла",StateFilter(default_state))
async def battle_moderation(message: Message):
    await message.answer(text="Настройка баттла",reply_markup=tune_battle_admin_kb)

@admin_router.message(lambda message: message.text == "Текущие настройки",StateFilter(default_state))
async def current_battle_settings(message: Message):
    settings = await select_battle_settings()
    print(settings)
    round_duration = settings[0]//60
    prize_amount = settings[1]
    min_vote_total = settings[2]
    round_interval = settings[3]//60
    start_time = settings[4]
    hours = start_time // 3600
    minutes = (start_time % 3600) // 60
    await message.answer(text=
                        f"Текущие настройки баттла: \n\n" 
                        f"Продолжительность раунда: {round_duration} мин\n"+
                        f"Сумма приза: {prize_amount}\n"+
                        f"Минимальное количество голосов: {min_vote_total}\n"+
                        f"Интервал между раундами: {round_interval} мин\n"+
                        f"Время начала баттла: {hours:02d}:{minutes:02d} ",
                         reply_markup=tune_battle_admin_kb)


@admin_router.message(lambda message: message.text == "Продолжительность раунда",StateFilter(default_state))
async def enter_duration_of_round(message: Message, state: FSMContext):
    await message.answer(text="Введите продолжительность раунда в минутах",reply_markup=back_admin_kb)
    await state.set_state(FSMFillForm.fill_duration_of_battle)


@admin_router.message(StateFilter(FSMFillForm.fill_duration_of_battle),F.text.regexp(r"^\d+$"))
async def get_duration_of_round(message: Message, state: FSMContext):
    minutes = int(message.text)
    seconds = minutes * 60
    parametr = 'round_duration'
    await edit_battle_settings(parametr, seconds)
    await message.answer(text="Данные получены",reply_markup=tune_battle_admin_kb)
    await state.clear()

@admin_router.message(StateFilter(FSMFillForm.fill_duration_of_battle))
async def get_duration_of_round_invalid(message: Message):
    await message.answer(text="Вы ввели неверные данные. Пожалуйста, попробуйте снова.",reply_markup=back_admin_kb)


@admin_router.message(lambda message: message.text == "Сумма приза",StateFilter(default_state))
async def enter_amount_of_prize(message: Message, state: FSMContext):
    await message.answer(text="Введите сумму приза",reply_markup=back_admin_kb)
    await state.set_state(FSMFillForm.fill_amount_of_prize)

@admin_router.message(StateFilter(FSMFillForm.fill_amount_of_prize),F.text.regexp(r"^\d+$"))
async def get_amount_of_prize(message: Message, state: FSMContext):
    value = int(message.text)
    parametr = 'prize_amount'
    await edit_battle_settings(parametr, value)
    await message.answer(text="Данные получены",reply_markup=tune_battle_admin_kb)
    await state.clear()

@admin_router.message(StateFilter(FSMFillForm.fill_amount_of_prize))
async def get_amount_of_prize_invalid(message: Message):
    await message.answer(text="Вы ввели неверные данные. Пожалуйста, попробуйте снова.",reply_markup=back_admin_kb)



@admin_router.message(lambda message: message.text == "Минимальное количество голосов",StateFilter(default_state))
async def enter_minimal_number_of_votes(message: Message, state: FSMContext):
    await message.answer(text="Введите минимальное количество голосов",reply_markup=back_admin_kb)
    await state.set_state(FSMFillForm.fill_minimal_number_of_votes)

@admin_router.message(StateFilter(FSMFillForm.fill_minimal_number_of_votes),F.text.regexp(r"^\d+$"))
async def get_minimal_number_of_votes(message: Message, state: FSMContext):
    value = int(message.text)
    parametr = 'min_vote_total'
    await edit_battle_settings(parametr, value)
    await message.answer(text="Данные получены",reply_markup=tune_battle_admin_kb)
    await state.clear()

@admin_router.message(StateFilter(FSMFillForm.fill_minimal_number_of_votes))
async def get_minimal_number_of_votes_invalid(message: Message):
    await message.answer(text="Вы ввели неверные данные. Пожалуйста, попробуйте снова.",reply_markup=back_admin_kb)


@admin_router.message(lambda message: message.text == "Интервал между раундами",StateFilter(default_state))
async def enter_interval_between_rounds(message: Message, state: FSMContext):
    await message.answer(text="Введите интервал между раундами",reply_markup=back_admin_kb)
    await state.set_state(FSMFillForm.fill_interval_between_battles)

@admin_router.message(StateFilter(FSMFillForm.fill_interval_between_battles),F.text.regexp(r"^\d+$"))
async def get_interval_between_rounds(message: Message, state: FSMContext):
    minutes = int(message.text)
    seconds = minutes * 60
    parametr = 'round_interval'
    await edit_battle_settings(parametr, seconds)
    await message.answer(text="Данные получены",reply_markup=tune_battle_admin_kb)
    await state.clear()

@admin_router.message(StateFilter(FSMFillForm.fill_interval_between_battles))
async def get_interval_between_rounds_invalid(message: Message):
    await message.answer(text="Вы ввели неверные данные. Пожалуйста, попробуйте снова.",reply_markup=back_admin_kb)



@admin_router.message(lambda message: message.text == "Время начала баттла",StateFilter(default_state))
async def enter_start_time_of_battle(message: Message, state: FSMContext):
    await message.answer(text="Введите время начала баттла по МСК в формате hh:mm",reply_markup=back_admin_kb)
    await state.set_state(FSMFillForm.fill_start_time_of_battle)

@admin_router.message(StateFilter(FSMFillForm.fill_start_time_of_battle),F.text.regexp(r'^([01]?[0-9]|2[0-3]):([0-5][0-9])$'))
async def get_start_time_of_battle(message: Message, state: FSMContext):
    match = re.match(r'^([01]?[0-9]|2[0-3]):([0-5][0-9])$', message.text)
    hours, minutes = map(int, match.groups())
    seconds = hours * 60 * 60 + minutes * 60
    parametr = 'time_of_run'
    await edit_battle_settings(parametr, seconds)
    await message.answer(text="Данные получены",reply_markup=tune_battle_admin_kb)
    await state.clear()

@admin_router.message(StateFilter(FSMFillForm.fill_start_time_of_battle))
async def get_start_time_of_battle_invalid(message: Message):
    await message.answer(text="Вы ввели неверные данные. Пожалуйста, попробуйте снова.",reply_markup=back_admin_kb)


#@admin_router.message()

# --------------


# --------------
