import logging
import os
import re

from aiogram import Router, Bot, F
from aiogram.filters import Command, StateFilter, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from config.config import load_config
import keyboards
from filters.isAdmin import is_admin
from keyboards.admin_keyboards import *
from database.db import *
from routers.channel_router import delete_previous_messages, make_some_magic, get_channel_id
from states.admin_states import FSMFillForm
from tasks import scheduler_manager
from utils.task_manager import TaskManagerInstance
from keyboards.user_keyboards import main_user_kb
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
        print(photo)
        try:
            caption=f"ID: {user_id}\n" + f"Ник: @{await get_username_by_id(user_id)}\n" +f"Выйгранных фотобатлов: {buttle_win} \n" + f"Общее число фотобатлов: {plays_buttle} \n" + f"Выйгранных дуэлей: {dual_win}\n\n" + f"Дополнительные голоса: {additional_voices}\n" f"Приглашенных рефералов: {referals}"
        except Exception as e:
            print("Не удалось получить ник пользователя " + e)
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

@admin_router.message(lambda message: message.text == "Назад в меню")
async def photo_moderation(message: Message, state: FSMContext):
    await message.answer(text="Назад в меню",reply_markup=main_user_kb)
    await state.clear()
    
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
        ref_owner_id = (await get_user(user_id))
        if ref_owner_id:
            ref_owner_id=ref_owner_id[8]
            # print(await get_user(ref_owner_id))
            owner = await get_user(ref_owner_id)
            additional_voices_owner = owner[5]
            referals = owner[4]
            await edit_user(ref_owner_id, 'additional_voices', additional_voices_owner+3)
            await edit_user(ref_owner_id, 'referals',  referals+1)
            try:
                await _bot.send_message(ref_owner_id, text=(
                    f"Пользователь {user_id}, зарегистрированный по вашей ссылке получил одобрение на "+
                    f'баттл, вы получаете 3 дополнительных голоса, сейчас количество ваших голосов {additional_voices_owner+3}'
                    ))
            except Exception as e:
                print(f"Ошибка при отправке личного сообщения: {e}")
        if delMessage:
            await _bot.send_message(call.from_user.id, "Заявки закончились")
            await call.message.delete()
        await create_user_in_batl(user_id,photo_id, 'user')
        
        await delete_application(user_id)
        # /////
        if len(all_application)>1:
            values = await gen_mode_aplic(all_application[1:])
            photo = values[0]
            caption = values[1]
            reply_markup = values[2]
            await call.message.edit_media(media=InputMediaPhoto(media=photo, caption=caption), reply_markup=reply_markup)
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
        if len(all_application)>1:
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
        if len(all_application)>1:
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
    channel_id = get_channel_id()
    try:
        if not scheduler_manager.task_manager.battle_active:
            users_on_battle = await select_participants_no_id_null()
            if users_on_battle:
                for user in users_on_battle:
                    await create_application(user['user_id'],user['photo_id'])
                await clear_users_in_batl()        
                await _bot.send_message(message.from_user.id,"Список участников баттла очищен")
            else:
                await _bot.send_message(message.from_user.id,"Список участников баттла уже пуст")
            await _bot.send_message(message.from_user.id,"В данный момент нет активного баттла.")
            return
        
        
        # Останавливаем текущий баттл
        if scheduler_manager.remove_current_battle():
            # Очистка произойдет автоматически в обработчике CancelledError
            await delete_previous_messages(message.bot, channel_id)
            
            users_on_battle = await select_participants_no_id_null()
            if users_on_battle:
                for user in users_on_battle:
                    await create_application(user['user_id'],user['photo_id'])
            # Обновляем сообщение с подтверждением
            await _bot.send_message(message.from_user.id, text="Баттл успешно остановлен.")
            
            # Отправляем уведомление в канал
            war_message = await _bot.send_message(
                channel_id,
                "⚠️ Баттл был остановлен администратором."
            )
            await save_message_ids([war_message.message_id])


        else:
            await _bot.send_message(message.from_user.id,text="Не удалось остановить баттл.")
        

    except Exception as e:
        error_message = f"Ошибка при остановке баттла: {e}"
        logging.error(error_message)
        await _bot.send_message(message.from_user.id, error_message)




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
            try:
                await _bot.send_message(user_id,text=txt)
            except Exception as e:
                print(e)
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
            try:
                await _bot.send_message(user_id,text=txt)
            except Exception as e:
                print(e)
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
            try:
                await _bot.send_message(user_id,text=txt)
            except Exception as e:
                print(e)
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
async def amdin_moderation(message: Message):
    if not is_super_admin(message.from_user.id): return
    await message.answer(text="Управление администраторами",reply_markup=managing_admins_kb)

@admin_router.message(lambda message: message.text == "Назначить",StateFilter(default_state))
async def enter_new_admin(message: Message, state: FSMContext):
    if not is_super_admin(message.from_user.id): return
    await message.answer(text="Введите id пользователя",reply_markup=back_admin_kb)
    await state.set_state(FSMFillForm.fill_id_of_new_admin)

@admin_router.message(StateFilter(FSMFillForm.fill_id_of_new_admin), F.text.regexp(r"^\d+$"))
async def get_new_admin(message: Message, state: FSMContext):
    if await edit_user_role(int(message.text), "admin"):
        await message.answer(text="Данные получены",reply_markup=managing_admins_kb)
        await state.clear()
    else:
        await message.answer(text="Упс, похоже этот пользователь не подписан на бота.", reply_markup=back_admin_kb)

@admin_router.message(StateFilter(FSMFillForm.fill_id_of_new_admin))
async def get_id_of_new_admin_invalid(message: Message):
    await message.answer(text="Вы ввели неверные данные. Пожалуйста, попробуйте снова.",reply_markup=back_admin_kb)


@admin_router.message(lambda message: message.text == "Cнять права",StateFilter(default_state))
async def enter_id_of_old_admin(message: Message, state: FSMContext):
    if not is_super_admin(message.from_user.id): return
    await message.answer(text="Введите id администратора",reply_markup=back_admin_kb)
    await state.set_state(FSMFillForm.fill_id_of_old_admin)


@admin_router.message(StateFilter(FSMFillForm.fill_id_of_old_admin), F.text.regexp(r"^\d+$"))
async def get_id_of_old_admin(message: Message, state: FSMContext):
    if await edit_user_role(int(message.text), "user"):
        await message.answer(text="Данные получены",reply_markup=managing_admins_kb)
        await state.clear()
    else:
        await message.answer(text="Упс, похоже этот пользователь не подписан на бота.", reply_markup=back_admin_kb)

@admin_router.message(StateFilter(FSMFillForm.fill_id_of_old_admin))
async def get_id_of_old_admin_invalid(message: Message):
    await message.answer(text="Вы ввели неверные данные. Пожалуйста, попробуйте снова.",reply_markup=back_admin_kb)


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
    autowin = settings[5]
    if autowin == 0:
        autowin = 'Off'
    else:
        autowin = 'On'
    await message.answer(text=
                        f"Текущие настройки баттла: \n\n" 
                        f"Продолжительность раунда: {round_duration} мин\n"+
                        f"Сумма приза: {prize_amount}\n"+
                        f"Минимальное количество голосов: {min_vote_total}\n"+
                        f"Интервал между раундами: {round_interval} мин\n"+
                        f"Время начала баттла: {hours:02d}:{minutes:02d}\n"+
                        f"Автопобеда: {autowin} ",
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

@admin_router.message(lambda message: message.text == "Автоматическая победа",StateFilter(default_state))
async def enter_autowin(message: Message, state: FSMContext):
    await message.answer(text="Включить автовыигрыш, y/n?",reply_markup=back_admin_kb)
    await state.set_state(FSMFillForm.fill_autowin_state)

@admin_router.message(StateFilter(FSMFillForm.fill_autowin_state),F.text.regexp(r'^[yYnN]$'))
async def get_autowin(message: Message, state: FSMContext):
    req=message.text.lower()
    if req == 'y':
        await edit_battle_settings("is_autowin", 1)
        await make_some_magic()
    else:
        await edit_battle_settings("is_autowin", 0)
        await delete_user_in_batl(0)
    await message.answer(text="Данные получены",reply_markup=tune_battle_admin_kb)
    await state.clear()

@admin_router.message(StateFilter(FSMFillForm.fill_autowin_state))
async def get_autowin_invalid(message: Message):
    await message.answer(text="Вы ввели неверные данные. Пожалуйста, попробуйте снова.",reply_markup=back_admin_kb)



#@admin_router.message()

# --------------

@admin_router.message(F.text == "Список участников")
async def participiants_of_current_battle(message: Message):
    users_on_battle = await select_all_battle()
    if users_on_battle:
        text = ''
        for i in users_on_battle:
            user_id = i[0]
            try:
                username = await get_username_by_id(user_id)
            except Exception as e:
                print("Не удалось получить ник пользователя. Ошибка:", e)
            command = f'/prof{user_id}'
            text += f'ID: {user_id}, ник: @{username}, анкета: {command}\n'
        await message.answer(text=text)
    else:
        await message.answer(text='Список участников пуст')

# Команда /prof с параметром telegram_id
@admin_router.message(F.text.regexp(r'^/prof(\d+)$'))
async def handle_prof_command(message: Message):
    # Получаем ID из текста сообщения с помощью регулярного выражения
    match = re.match(r'^/prof(\d+)$', message.text)
    telegram_id = match.group(1)  # Получаем ID из регулярного выражения
    
    try:
        user_id = int(telegram_id)
        user_on_battle = await select_user_on_battle(user_id)
        if user_on_battle:
            user = await get_user(user_id)
            buttle_win = user[1]
            dual_win = user[2]
            plays_buttle = user[3]
            referals = user[4]
            additional_voices = user[5]

            photo_id = user_on_battle[1]
            photo = photo_id

            try:
                caption = (
                    f"ID: {user_id}\n"
                    f"Ник: @{await get_username_by_id(user_id)}\n"
                    f"Выйгранных фотобатлов: {buttle_win}\n"
                    f"Общее число фотобатлов: {plays_buttle}\n"
                    f"Выйгранных дуэлей: {dual_win}\n\n"
                    f"Дополнительные голоса: {additional_voices}\n"
                    f"Приглашенных рефералов: {referals}"
                )
            except Exception as e:
                print("Не удалось получить ник пользователя. Ошибка:", e)
                caption = (
                    f"ID: {user_id}\n"
                    f"Выйгранных фотобатлов: {buttle_win}\n"
                    f"Общее число фотобатлов: {plays_buttle}\n"
                    f"Выйгранных дуэлей: {dual_win}\n\n"
                    f"Дополнительные голоса: {additional_voices}\n"
                    f"Приглашенных рефералов: {referals}"
                )

            await message.answer_photo(photo=photo, caption=caption, reply_markup=kick_user_kb)
        else:
            await message.answer(text="Игрок с этим ID не зарегистрирован на баттле")
    except ValueError:
        await message.reply("Ошибка: Неверный формат ID")

@admin_router.callback_query(lambda c: c.data == "kick")
async def process_kick_button(callback: CallbackQuery):
    # Получаем ID пользователя из текста сообщения
    text = callback.message.caption
    user_id = int(text.split('\n')[0].split(': ')[1])
    
    await callback.message.edit_caption(
        caption=f"{callback.message.caption}\n\nВы уверены, что хотите кикнуть этого пользователя?",
        reply_markup=confirm_kick_kb
    )
    await callback.answer()

@admin_router.callback_query(lambda c: c.data == "confirm_kick")
async def process_confirm_kick(callback: CallbackQuery):
    # Получаем ID пользователя из текста сообщения
    text = callback.message.caption
    user_id = int(text.split('\n')[0].split(': ')[1])
    
    try:
        task_manager = TaskManagerInstance.get_instance()
        current_mode = await task_manager.get_current_mode()
        if current_mode != 1:
            await kick_user_battle(user_id)
            
            await callback.message.edit_caption(
                caption=f"{callback.message.caption}\n\nПользователь будет кикнут и удален из баттла в конце 1 раунда!",
                reply_markup=None
            )
        else:
            await delete_user_in_batl(user_id)

            await callback.message.edit_caption(
                caption=f"{callback.message.caption}\n\nПользователь был удален из баттла!",
                reply_markup=None
            )
            
    except Exception as e:
        await callback.answer(f"Ошибка при удалении пользователя: {str(e)}", show_alert=True)

@admin_router.callback_query(lambda c: c.data == "cancel_kick")
async def process_cancel_kick(callback: CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=kick_user_kb)
    await callback.answer("Действие отменено")


@admin_router.message(lambda message: message.text == "Добавить канал")
async def start_adding_channel(message: Message, state: FSMContext):
    await message.answer("Введите название канала:")
    await state.set_state(FSMFillForm.add_channel_name)
    
@admin_router.message(FSMFillForm.add_channel_name)
async def process_channel_name(message: Message, state: FSMContext):
    # Проверяем корректность ввода (название не должно быть пустым)
    if not message.text or len(message.text) < 3:
        await message.answer("Название канала должно содержать хотя бы 3 символа. Попробуйте снова.")
        return

    # Сохраняем название канала во временное состояние
    await state.update_data(channel_name=message.text)
    await message.answer("Теперь введите ссылку на канал:")
    await state.set_state(FSMFillForm.add_channel_link)


@admin_router.message(FSMFillForm.add_channel_link)
async def process_channel_link(message: Message, state: FSMContext):
    # Проверяем, что ссылка корректна
    if not re.match(r'^https?://', message.text):
        await message.answer("Ссылка должна начинаться с http:// или https://. Попробуйте снова.")
        return

    # Получаем данные из состояния
    data = await state.get_data()
    channel_name = data.get("channel_name")
    channel_link = message.text

    # Сохраняем канал в базу данных
    try:
        await add_channel_to_db(channel_name, channel_link)  # Функция для добавления в БД
        await message.answer(f"Канал <b>{channel_name}</b> успешно добавлен!", parse_mode="HTML")
    except Exception as e:
        await message.answer("Произошла ошибка при добавлении канала.")
        logging.error(f"Error adding channel: {e}")

    # Выходим из состояния
    await state.clear()

@admin_router.message(lambda message: message.text == "Удалить канал")
async def start_deleting_channel(message: Message, state: FSMContext):
    await message.answer("Введите название канала, который хотите удалить:")
    await state.set_state(FSMFillForm.delete_channel_name)


@admin_router.message(FSMFillForm.delete_channel_name)
async def process_channel_deletion(message: Message, state: FSMContext):
    channel_name = message.text

    try:
        # Удаляем канал из базы данных
        success = await delete_channel_from_db(channel_name)  # Функция для удаления из БД

        if success:
            await message.answer(f"Канал <b>{channel_name}</b> успешно удален!", parse_mode="HTML")
        else:
            await message.answer(f"Канал с названием <b>{channel_name}</b> не найден.", parse_mode="HTML")
    except Exception as e:
        await message.answer("Произошла ошибка при удалении канала.")
        logging.error(f"Error deleting channel: {e}")

    # Выходим из состояния
    await state.clear()
