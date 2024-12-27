from aiogram import Router, Bot, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message, CallbackQuery

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


#####################################               Общее                          ##########################################


@admin_router.message(Command("admin"),StateFilter(default_state))
async def cmd_admin(message: Message):
    await message.answer("Привет, админ! Ты в админской панели.", reply_markup=main_admin_kb)


@admin_router.message(lambda message: message.text == "Назад")
async def photo_moderation(message: Message, state: FSMContext):
    await message.answer(text="Назад",reply_markup=main_admin_kb)
    await state.clear()

#########################                       Модерация фотографий                ##########################################

@admin_router.message(lambda message: message.text == "Модерация фотографий")
async def photo_moderation(message: Message):
    user = await get_user(message.from_user.id)

    buttle_win = user[1]
    dual_win = user[2]
    plays_buttle = user[3]
    referals = user[4]
    additional_voices = user[5]

    #select photo by user_id
    application = (await select_all_applications())
    if application:
        application = application[0]
        
        photo_id = application[1]


        await message.answer_photo(
            photo=photo_id,
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
        
    else:
        await message.answer(text = 'Заявок нет')


@admin_router.callback_query(lambda query: query.data == "Принять")
async def apply(call: CallbackQuery):
    await call.answer(text="ok", reply_markup=mailing_admin_kb)
    application = (await select_all_applications())
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
    else:
        await _bot.send_message(call.from_user.id, "Заявки закончились")
    


@admin_router.callback_query(lambda query: query.data == "Отклонить")
async def decline(call: CallbackQuery):
    await   call.answer(text="ok", reply_markup=mailing_admin_kb)
    application = (await select_all_applications())
    delMessage = 0 if len(application) > 1 else 1
    if len(application) != 0:
        application = application[0]
        user_id = application[0]
        if delMessage:
            await _bot.send_message(call.from_user.id, "Заявки закончились")
            await call.message.delete()
        await delete_application(user_id)
    else:
        await _bot.send_message(call.from_user.id, "Заявки закончились")


@admin_router.callback_query(lambda query: query.data == "Забанить")
async def ban(call: CallbackQuery):
    await call.answer(text="ok", reply_markup=mailing_admin_kb)
    application = (await select_all_applications())
    delMessage = 0 if len(application) > 1 else 1
    if len(application) != 0:
        application = application[0]
        user_id = application[0]
        if delMessage:
            await _bot.send_message(call.from_user.id, "Заявки закончились")
            await call.message.delete()
        await edit_user(user_id,'is_ban',1)
        await delete_application(user_id)
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
                         , reply_markup=main_admin_kb)


####################################                    Очистка баттла                      #################################


@admin_router.message(lambda message: message.text == "Очистка баттла")
async def clear_battle(message: Message):
    await message.answer(text="Все пользователи удалены из батла",reply_markup=main_admin_kb)
    await delete_applications()
    await delete_users_in_batl()
    
    


####################################                    Рассылка                      #################################


@admin_router.message(lambda message: message.text == "Рассылка")
async def mailing(message: Message):
    await message.answer(text="Рассылка",reply_markup=mailing_admin_kb)

@admin_router.message(lambda message: message.text == "Всем пользователям" ,StateFilter(default_state))
async def mailing_everybody(message: Message, state: FSMContext):
    await message.answer(text="Введите сообщение для рассылки",reply_markup=mailing_admin_kb)
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
    await message.answer(text="Введите сообщение для рассылки",reply_markup=mailing_admin_kb)
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
    await message.answer(text="Введите сообщение для рассылки",reply_markup=mailing_admin_kb)
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
    await message.answer(text="Управление администраторами",reply_markup=managing_admins_kb)

@admin_router.message(lambda message: message.text == "Назначить",StateFilter(default_state))
async def enter_duration_of_round(message: Message, state: FSMContext):
    await message.answer(text="Введите id пользователя",reply_markup=managing_admins_kb)
    await state.set_state(FSMFillForm.fill_id_of_new_admin)

@admin_router.message(StateFilter(FSMFillForm.fill_id_of_new_admin))
async def get_duration_of_round(message: Message, state: FSMContext):
    await message.answer(text="Данные получены",reply_markup=managing_admins_kb)
    await state.clear()

@admin_router.message(lambda message: message.text == "Cнять права",StateFilter(default_state))
async def enter_duration_of_round(message: Message, state: FSMContext):
    await message.answer(text="Введите id администратора",reply_markup=managing_admins_kb)
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

@admin_router.message(lambda message: message.text == "Текущие настройки баттла",StateFilter(default_state))
async def current_battle_settings(message: Message):
    settings = await select_battle_settings()
    print(settings)
    round_duration = settings[0]
    prize_amount = settings[1]
    min_vote_total = settings[2]
    round_interval = settings[3]
    await message.answer(text=
                        f"Текущие настройки баттла: \n" 
                        f"Продолжительность раунда: {round_duration}\n"+
                        f"Сумма приза: {prize_amount}\n"+
                        f"Минимальное количество голосов: {min_vote_total}\n"+
                        f"Интервал между раундами: {round_interval}",
                         reply_markup=tune_battle_admin_kb)


@admin_router.message(lambda message: message.text == "Продолжительность раунда",StateFilter(default_state))
async def enter_duration_of_round(message: Message, state: FSMContext):
    await message.answer(text="Введите продолжительность раунда в формате hour:min",reply_markup=tune_battle_admin_kb)
    await state.set_state(FSMFillForm.fill_duration_of_battle)


@admin_router.message(StateFilter(FSMFillForm.fill_duration_of_battle),F.text.regexp(r"^\d+$"))
async def get_duration_of_round(message: Message, state: FSMContext):
    txt = message.text
    hours = int(txt[:2])
    minutes = int(txt[2:])
    seconds = hours * 3600 + minutes * 60
    parametr = 'round_duration'
    await edit_battle_settings(parametr, seconds)
    await message.answer(text="Данные получены",reply_markup=tune_battle_admin_kb)
    await state.clear()

@admin_router.message(StateFilter(FSMFillForm.fill_duration_of_battle))
async def get_duration_of_round_invalid(message: Message):
    await message.answer(text="Вы ввели неверные данные. Пожалуйста, попробуйте снова.",reply_markup=tune_battle_admin_kb)


@admin_router.message(lambda message: message.text == "Сумма приза",StateFilter(default_state))
async def enter_amount_of_prize(message: Message, state: FSMContext):
    await message.answer(text="Введите сумму приза",reply_markup=tune_battle_admin_kb)
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
    await message.answer(text="Вы ввели неверные данные. Пожалуйста, попробуйте снова.",reply_markup=tune_battle_admin_kb)



@admin_router.message(lambda message: message.text == "Минимальное количество голосов",StateFilter(default_state))
async def enter_minimal_number_of_votes(message: Message, state: FSMContext):
    await message.answer(text="Введите минимальное количество голосов",reply_markup=tune_battle_admin_kb)
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
    await message.answer(text="Вы ввели неверные данные. Пожалуйста, попробуйте снова.",reply_markup=tune_battle_admin_kb)


@admin_router.message(lambda message: message.text == "Интервал между раундами",StateFilter(default_state))
async def enter_interval_between_rounds(message: Message, state: FSMContext):
    await message.answer(text="Введите интервал между раундами",reply_markup=tune_battle_admin_kb)
    await state.set_state(FSMFillForm.fill_interval_between_battles)

@admin_router.message(StateFilter(FSMFillForm.fill_interval_between_battles),F.text.regexp(r"^\d+$"))
async def get_interval_between_rounds(message: Message, state: FSMContext):
    txt = message.text
    hours = int(txt[:2])
    minutes = int(txt[2:])
    seconds = hours * 3600 + minutes * 60
    parametr = 'round_interval'
    await edit_battle_settings(parametr, seconds)
    await message.answer(text="Данные получены",reply_markup=tune_battle_admin_kb)
    await state.clear()

@admin_router.message(StateFilter(FSMFillForm.fill_interval_between_battles))
async def get_interval_between_rounds_invalid(message: Message):
    await message.answer(text="Вы ввели неверные данные. Пожалуйста, попробуйте снова.",reply_markup=tune_battle_admin_kb)


#@admin_router.message()

# --------------


# --------------
