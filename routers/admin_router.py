import logging
import os
import re
import string
from typing import List
from datetime import datetime
from aiogram import Router, Bot, F
from aiogram.filters import Command, StateFilter, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from config.config import load_config

from filters.isAdmin import is_admin
from keyboards.admin_keyboards import *
from database.db import *
from routers.channel_router import delete_previous_messages, make_some_magic, get_channel_id
from states.admin_states import ClearBattleStates, DateInput, FSMFillForm, FSMNotification
from tasks import scheduler_manager
from utils.task_manager import TaskManagerInstance
from keyboards.user_keyboards import main_user_kb
admin_router = Router()
admin_router.message.filter(is_admin)



_bot: Bot = None

def setup_router(dp, bot: Bot):
    global _bot
    _bot = bot


async def get_config():
        dirname = os.path.dirname(__file__)
        filename = os.path.abspath(os.path.join(dirname, '..', 'config/config.env'))
        config = load_config(filename)
        return config

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
            caption=(
                    f"🛰ID: {user_id}\n"
                    f"👽 User: @{await get_username_by_id(user_id)}\n\n"
                    f"🎮 Сыграно фотобатлов: {plays_buttle}\n"
                    f"🥇 Выиграно фотобатлов: {buttle_win}\n"
                    f"⚔ Выиграно дуэлей: {dual_win}\n\n"
                    f"🔑 Дополнительные голоса: {additional_voices}\n"
                    f"💸 Приглашенных рефералов: {referals}"
                )
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

@admin_router.message(lambda message: message.text == "📷 Модерация")
async def photo_moderation(message: Message):
    application = (await select_all_applications())
    if application:
        values = await gen_mode_aplic(application)
        photo = values[0]
        caption = values[1]
        reply_markup = values[2]
        await message.answer_photo(photo=photo,caption=caption, reply_markup=reply_markup)
    else:
        await message.answer(text = 'Заявок нет 😶‍🌫')


@admin_router.callback_query(lambda query: query.data == "Принять")
async def apply(call: CallbackQuery):
    task_manager = TaskManagerInstance.get_instance()
    current_mode = await task_manager.get_current_mode()
    await call.answer(text="ok", reply_markup=mailing_admin_kb)
    application = (await select_all_applications())
    all_application = application
    delMessage = 0 if len(application) > 1 else 1
    if len(application) != 0:
        application = application[0]
        user_id = application[0]
        try:
            config = await get_config()
            channel_link = config.tg_bot.channel_link
            await _bot.send_message(user_id, text=(f"✅ Поздравляем! Ваша фотография одобрена к участию в фотобатле! Я сообщу о начале.\n\nКанал проведения: <a href='{channel_link}'>cсылка</a>"),parse_mode='HTML')
        except Exception as e:
                print(f"Ошибка при отправке личного сообщения: {e}")
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
            await edit_user(user_id, 'ref_owner', 0)
            try:
                await _bot.send_message(ref_owner_id, text=(
                    f"🎊 Поздравляем! Реферал подал заявку и вы получили три голоса на этот баттл.\n\n" +
                    f"🪄 В любом из раундов баттла вы можете нажать на кнопку голосования 3 раза, чтобы использовать дополнительные голоса. (Голоса сгорают в конце каждого баттла, успей их использовать)."
                    ))
            except Exception as e:
                print(f"Ошибка при отправке личного сообщения: {e}")
        if delMessage:
            await _bot.send_message(call.from_user.id, "Заявки закончились 😶‍🌫")
            await call.message.delete()
        if current_mode == 1:
            await create_user_in_batl(user_id,photo_id, 'user')
        else:
            await create_user_in_buffer(user_id,photo_id, 'user')
        await delete_application(user_id)
        # /////
        if len(all_application)>1:
            values = await gen_mode_aplic(all_application[1:])
            photo = values[0]
            caption = values[1]
            reply_markup = values[2]
            await call.message.edit_media(media=InputMediaPhoto(media=photo, caption=caption), reply_markup=reply_markup)
    else:
        await _bot.send_message(call.from_user.id, "Заявки закончились 😶‍🌫")
    


@admin_router.callback_query(lambda query: query.data == "Отклонить")
async def decline(call: CallbackQuery):
    await   call.answer(text="ok", reply_markup=mailing_admin_kb)
    application = (await select_all_applications())
    all_application = application
    delMessage = 0 if len(application) > 1 else 1
    if len(application) != 0:
        application = application[0]
        user_id = application[0]
        try:
            config = await get_config()
            rule_link = config.tg_bot.rule_link
            await _bot.send_message(user_id, text=f"❌ Ваша фотография отклонена. Изучите <a href='{rule_link}'>правила</a> и попробуйте снова.", parse_mode="HTML")
        except Exception as e:
                print(f"Ошибка при отправке личного сообщения: {e}")
        if delMessage:
            await _bot.send_message(call.from_user.id, "Заявки закончились 😶‍🌫")
            await call.message.delete()
        await delete_application(user_id)
        if len(all_application)>1:
            values = await gen_mode_aplic(all_application[1:])
            photo = values[0]
            caption = values[1]
            reply_markup = values[2]
            await call.message.edit_media(media=InputMediaPhoto(media=photo, caption=caption), reply_markup=reply_markup)
    else:
        await _bot.send_message(call.from_user.id, "Заявки закончились 😶‍🌫")


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
            await _bot.send_message(call.from_user.id, "Заявки закончились 😶‍🌫")
            await call.message.delete()
        await edit_user(user_id,'is_ban',1)
        await delete_application(user_id)
        if len(all_application)>1:
            values = await gen_mode_aplic(all_application[1:])
            photo = values[0]
            caption = values[1]
            reply_markup = values[2]
            await call.message.edit_media(media=InputMediaPhoto(media=photo, caption=caption), reply_markup=reply_markup)
    else:
        await _bot.send_message(call.from_user.id, "Заявки закончились 😶‍🌫")


####################################                    Статистика                      #################################


@admin_router.message(lambda message: message.text == "📊 Статистика")
async def statistics(message: Message):
    quantity_users = len(await get_all_users())
    quantity_aplic = len(await select_all_applications())
    quantity_battle = len(await select_all_battle())
    quantity_buffer = len(await get_users_in_buffer())
    
    
    task_manager = TaskManagerInstance.get_instance()
    current_mode = await task_manager.get_current_mode()
    if current_mode == 2:
        await message.answer(text=
                            f"📊Количество зарегистрированных пользователей: {quantity_users}\n\n"+
                            f"⏳Количество необработанных заявок: {quantity_aplic}\n\n"+
                            f"⏳Количество ожидающих: {quantity_buffer}\n\n"+
                            f"🎮Количество активных участников баттла: {quantity_battle}"
                            , reply_markup=get_main_admin_kb(message.from_user.id))
    else:
        await message.answer(text=
                            f"📊Количество зарегистрированных пользователей: {quantity_users}\n\n"+
                            f"⏳Количество необработанных заявок: {quantity_aplic}\n\n"+
                            f"⏳Количество ожидающих: {quantity_battle}"
                            , reply_markup=get_main_admin_kb(message.from_user.id))


####################################                    Очистка баттла                      #################################



@admin_router.message(lambda message: message.text == "💣 Очистка баттла")
async def clear_battle_confirmation(message: Message, state: FSMContext):
    # Создаем клавиатуру для подтверждения
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="✅ Да, очистить"),
                KeyboardButton(text="❌ Нет, отменить")
            ]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "⚠️ Вы уверены, что хотите очистить баттл?\n"
        "Это действие нельзя будет отменить.",
        reply_markup=keyboard
    )
    # Устанавливаем состояние ожидания подтверждения
    await state.set_state(ClearBattleStates.waiting_for_confirmation)




@admin_router.message(ClearBattleStates.waiting_for_confirmation)
async def clear_battle(message: Message, state: FSMContext):
    main_keyboard = get_main_admin_kb(message.from_user.id)
    if message.text == "✅ Да, очистить":
        # Очищаем состояние
        await state.clear()
        channel_id = get_channel_id()
        try:
            if not scheduler_manager.task_manager.battle_active:
                users_on_battle = await select_participants_no_id_null()
                if users_on_battle:
                    for user in users_on_battle:
                        await create_application(user['user_id'],user['photo_id'])
                    await clear_users_in_batl()        
                    await _bot.send_message(message.from_user.id,"Список участников баттла очищен", )
                else:
                    await _bot.send_message(message.from_user.id,"Список участников баттла уже пуст")
                await _bot.send_message(message.from_user.id,"В данный момент нет активного баттла.", reply_markup=main_keyboard)
                return
            
            
            # Останавливаем текущий баттл
            if scheduler_manager.remove_current_battle():
                # Очистка произойдет автоматически в обработчике CancelledError
                await delete_previous_messages(message.bot, channel_id)
                
                users_on_battle = await select_participants_no_id_null()
                if users_on_battle:
                    for user in users_on_battle:
                        await create_application(user['user_id'],user['photo_id'])
                    await clear_users_in_batl()
                # Обновляем сообщение с подтверждением
                await _bot.send_message(message.from_user.id, text="Баттл успешно остановлен.", reply_markup=main_keyboard)
                
                # Отправляем уведомление в канал
                war_message = await _bot.send_message(
                    channel_id,
                    "⚠️ Баттл был остановлен администратором."
                )
                await save_message_ids([war_message.message_id])


            else:
                await _bot.send_message(message.from_user.id,text="Не удалось остановить баттл.", reply_markup=main_keyboard)
            

        except Exception as e:
            error_message = f"Ошибка при остановке баттла: {e}"
            logging.error(error_message)
            await _bot.send_message(message.from_user.id, error_message)
            
    elif message.text == "❌ Нет, отменить":
        await message.answer(
            "Действие отменено.",
            reply_markup=main_keyboard
        )
        await state.clear()
    
    else:
        await message.answer(
            "Пожалуйста, используйте кнопки для ответа.",
            reply_markup=main_keyboard
        )
        await state.clear()



####################################                    Рассылка                      #################################


@admin_router.message(lambda message: message.text == "✉️ Рассылка")
async def mailing(message: Message):
    await message.answer(text="✉️ Рассылка",reply_markup=mailing_admin_kb)

@admin_router.message(lambda message: message.text == "Всем пользователям" ,StateFilter(default_state))
async def mailing_everybody(message: Message, state: FSMContext):
    await message.answer(text="🌍 Введите сообщение для рассылки.",reply_markup=back_admin_kb)
    await state.set_state(FSMFillForm.fill_message_for_all)

# Хэндлер для рассылки всем пользователям (с поддержкой пересланных сообщений)
@admin_router.message(F.text | F.forward_from_chat, StateFilter(FSMFillForm.fill_message_for_all))
async def enter_mailing_everybody(message: Message, state: FSMContext, bot: Bot):
    """
    Обработчик для рассылки пересланных сообщений из канала всем пользователям.
    """
    # Проверяем, что сообщение переслано из канала
    if message.forward_from_chat and message.forward_from_message_id:
        from_chat_id = message.forward_from_chat.id  # ID канала
        message_id = message.forward_from_message_id # Оригинальный ID сообщения в канале
    elif message.text:
        content = message.text
    else:
        await message.answer("Ошибка: сообщение не содержит данных для пересылки.")
        return

    # Получаем список пользователей
    users = await get_all_users()  # Функция должна возвращать список [(user_id,), ...]
    users_id = [user[0] for user in users]

    # Рассылка сообщения
    for user_id in users_id:
        try:
            if message.forward_from_chat:
                # Пересылаем сообщение из канала
                await bot.forward_message(chat_id=user_id, from_chat_id=from_chat_id, message_id=message_id)
            else:
                # Отправляем обычное текстовое сообщение
                await bot.send_message(chat_id=user_id, text=content, parse_mode="HTML")
        except Exception as e:
            print(f"Ошибка отправки пользователю {user_id}: {e}")

    # Ответ админу
    await message.answer("Сообщение отправлено всем пользователям!", reply_markup=mailing_admin_kb)
    await state.clear()

    
    
    
@admin_router.message(lambda message: message.text == "Участникам, чьи фото находятся на модерации",StateFilter(default_state))
async def mailing_on_moderation(message: Message, state: FSMContext):
    await message.answer(text="Введите сообщение для рассылки",reply_markup=back_admin_kb)
    await state.set_state(FSMFillForm.fill_message_for_moder)



# Хэндлер для рассылки участникам, чьи фото на модерации (с поддержкой пересланных сообщений)
@admin_router.message(F.text | F.forward_from_chat, StateFilter(FSMFillForm.fill_message_for_moder))
async def enter_mailing_on_moderation(message: Message, state: FSMContext, bot: Bot):
    """
    Обработчик для рассылки участникам, чьи фото на модерации.
    Поддерживает текстовые сообщения и пересланные сообщения из каналов.
    """
    # Проверяем, пересланное это сообщение или обычный текст
    if message.forward_from_chat and message.forward_from_message_id:
        from_chat_id = message.forward_from_chat.id  # ID канала
        message_id = message.forward_from_message_id  # Оригинальный ID сообщения в канале
    elif message.text:
        content = message.text  # Обычный текст сообщения
    else:
        await message.answer("Ошибка: неподдерживаемый тип сообщения.")
        return

    # Получаем список пользователей
    users = await select_all_applications()  # Функция должна возвращать список [(user_id,), ...]
    users_id = [user[0] for user in users]

    # Рассылка сообщения
    for user_id in users_id:
        try:
            if message.forward_from_chat:
                # Пересылаем сообщение из канала
                await bot.forward_message(chat_id=user_id, from_chat_id=from_chat_id, message_id=message_id)
            else:
                # Отправляем обычное текстовое сообщение
                await bot.send_message(chat_id=user_id, text=content, parse_mode="HTML")
        except Exception as e:
            print(f"Ошибка отправки пользователю {user_id}: {e}")

    # Ответ админу
    await message.answer("Сообщение отправлено участникам, чьи фото находятся на модерации", reply_markup=mailing_admin_kb)
    await state.clear()





@admin_router.message(lambda message: message.text == "Участникам, ожидающих баттл",StateFilter(default_state))
async def mailing_active_participants(message: Message, state: FSMContext):
    await message.answer(text="Введите сообщение для рассылки",reply_markup=back_admin_kb)
    await state.set_state(FSMFillForm.fill_message_for_user_on_except)
    
# Хэндлер для рассылки участникам текущего баттла (с поддержкой пересланных сообщений)
@admin_router.message(F.text | F.forward_from_chat, StateFilter(FSMFillForm.fill_message_for_user_on_except))
async def enter_mailing_on_battle(message: Message, state: FSMContext, bot: Bot):
    """
    Обработчик для рассылки участникам текущего баттла.
    Поддерживает текстовые сообщения и пересланные сообщения из каналов.
    """
    # Проверяем, пересланное это сообщение или обычный текст
    task_manager = TaskManagerInstance.get_instance()
    current_mode = await task_manager.get_current_mode()
    if message.forward_from_chat and message.forward_from_message_id:
        from_chat_id = message.forward_from_chat.id  # ID канала
        message_id = message.forward_from_message_id  # Оригинальный ID сообщения в канале
    elif message.text:
        content = message.text  # Обычный текст сообщения
    else:
        await message.answer("Ошибка: неподдерживаемый тип сообщения.")
        return

    # Получаем список пользователей
    if current_mode == 1:
        users = await select_all_battle()  # Функция должна возвращать список [(user_id,), ...]
        users_id = [user[0] for user in users]
    else:
        users = await get_users_in_buffer()
        users_id = [user['user_id'] for user in users] 
        

    # Рассылка сообщения
    for user_id in users_id:
        try:
            if message.forward_from_chat:
                # Пересылаем сообщение из канала
                await bot.forward_message(chat_id=user_id, from_chat_id=from_chat_id, message_id=message_id)
            else:
                # Отправляем обычное текстовое сообщение
                await bot.send_message(chat_id=user_id, text=content, parse_mode="HTML")
        except Exception as e:
            print(f"Ошибка отправки пользователю {user_id}: {e}")

    # Ответ админу
    await message.answer("Сообщение отправлено всем участникам, ожидающих баттл", reply_markup=mailing_admin_kb)
    await state.clear()







@admin_router.message(lambda message: message.text == "Активным участникам текущего баттла",StateFilter(default_state))
async def mailing_active_participants(message: Message, state: FSMContext):
    task_manager = TaskManagerInstance.get_instance()
    current_mode = await task_manager.get_current_mode()
    if current_mode != 2:
        await message.answer("В данный момент баттл не идёт",reply_markup=back_admin_kb)
    else:
        await message.answer(text="Введите сообщение для рассылки",reply_markup=back_admin_kb)
        await state.set_state(FSMFillForm.fill_message_for_user_on_battle)
    
# Хэндлер для рассылки участникам текущего баттла (с поддержкой пересланных сообщений)
@admin_router.message(F.text | F.forward_from_chat, StateFilter(FSMFillForm.fill_message_for_user_on_battle))
async def enter_mailing_on_battle(message: Message, state: FSMContext, bot: Bot):
    """
    Обработчик для рассылки участникам текущего баттла.
    Поддерживает текстовые сообщения и пересланные сообщения из каналов.
    """
    # Проверяем, пересланное это сообщение или обычный текст
    task_manager = TaskManagerInstance.get_instance()
    current_mode = await task_manager.get_current_mode()
    if current_mode != 2:
        await message.answer("В данный момент баттл не идёт")
        return
    if message.forward_from_chat and message.forward_from_message_id:
        from_chat_id = message.forward_from_chat.id  # ID канала
        message_id = message.forward_from_message_id  # Оригинальный ID сообщения в канале
    elif message.text:
        content = message.text  # Обычный текст сообщения
    else:
        await message.answer("Ошибка: неподдерживаемый тип сообщения.")
        return

    # Получаем список пользователей
    users = await select_all_battle()  # Функция должна возвращать список [(user_id,), ...]
    users_id = [user[0] for user in users]

    # Рассылка сообщения
    for user_id in users_id:
        try:
            if message.forward_from_chat:
                # Пересылаем сообщение из канала
                await bot.forward_message(chat_id=user_id, from_chat_id=from_chat_id, message_id=message_id)
            else:
                # Отправляем обычное текстовое сообщение
                await bot.send_message(chat_id=user_id, text=content, parse_mode="HTML")
        except Exception as e:
            print(f"Ошибка отправки пользователю {user_id}: {e}")

    # Ответ админу
    await message.answer("Сообщение отправлено всем активным участникам текущего баттла", reply_markup=mailing_admin_kb)
    await state.clear()

    
@admin_router.message(StateFilter(FSMFillForm.fill_message_for_all))
@admin_router.message(StateFilter(FSMFillForm.fill_message_for_moder))
@admin_router.message(StateFilter(FSMFillForm.fill_message_for_user_on_battle))
async def enter_correct_data(message: Message):
    await message.answer('Пожалуйста, на этом шаге отправьте '
             'текстовое сообщение\n\nЕсли вы хотите прервать '
             'заполнение - нажмите "Назад"',reply_markup=mailing_admin_kb)

##############################              Управление администраторами         ########################################


@admin_router.message(lambda message: message.text == "👮‍♂ Админы",StateFilter(default_state))
async def amdin_moderation(message: Message):
    if not is_super_admin(message.from_user.id): return
    await message.answer(text="👮‍♂ Админы",reply_markup=managing_admins_kb)

@admin_router.message(lambda message: message.text == "Назначить",StateFilter(default_state))
async def enter_new_admin(message: Message, state: FSMContext):
    if not is_super_admin(message.from_user.id): return
    await message.answer(text="Введите id пользователя",reply_markup=back_admin_kb)
    await state.set_state(FSMFillForm.fill_id_of_new_admin)

@admin_router.message(StateFilter(FSMFillForm.fill_id_of_new_admin), F.text.regexp(r"^\d+$"))
async def get_new_admin(message: Message, state: FSMContext):
    if await edit_user_role(int(message.text), "admin"):
        await message.answer(text="😎 Данные получены",reply_markup=managing_admins_kb)
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
        await message.answer(text="😎 Данные получены",reply_markup=managing_admins_kb)
        await state.clear()
    else:
        await message.answer(text="Упс, похоже этот пользователь не подписан на бота.", reply_markup=back_admin_kb)

@admin_router.message(StateFilter(FSMFillForm.fill_id_of_old_admin))
async def get_id_of_old_admin_invalid(message: Message):
    await message.answer(text="Вы ввели неверные данные. Пожалуйста, попробуйте снова.",reply_markup=back_admin_kb)


##############################          Настройка баттла                ####################################

@admin_router.message(lambda message: message.text == "⚙ Настройка баттла",StateFilter(default_state))
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
    await message.answer(text="😎 Данные получены",reply_markup=tune_battle_admin_kb)
    await state.clear()

@admin_router.message(StateFilter(FSMFillForm.fill_duration_of_battle))
async def get_duration_of_round_invalid(message: Message):
    await message.answer(text="Вы ввели неверные данные. Пожалуйста, попробуйте снова.",reply_markup=back_admin_kb)


@admin_router.message(lambda message: message.text == "Приз",StateFilter(default_state))
async def enter_amount_of_prize(message: Message, state: FSMContext):
    await message.answer(text="Выберите приз",reply_markup=back_admin_kb)
    await state.set_state(FSMFillForm.fill_amount_of_prize)

@admin_router.message(StateFilter(FSMFillForm.fill_amount_of_prize))
async def get_amount_of_prize(message: Message, state: FSMContext):
    value = str(message.text)
    parametr = 'prize_amount'
    await edit_battle_settings(parametr, value)
    await message.answer(text="😎 Данные получены",reply_markup=tune_battle_admin_kb)
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
    await message.answer(text="😎 Данные получены",reply_markup=tune_battle_admin_kb)
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
    await message.answer(text="😎 Данные получены",reply_markup=tune_battle_admin_kb)
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
    await message.answer(text="😎 Данные получены",reply_markup=tune_battle_admin_kb)
    await state.clear()

@admin_router.message(StateFilter(FSMFillForm.fill_start_time_of_battle))
async def get_start_time_of_battle_invalid(message: Message):
    await message.answer(text="Вы ввели неверные данные. Пожалуйста, попробуйте снова.",reply_markup=back_admin_kb)

@admin_router.message(lambda message: message.text == "Автоматическая победа",StateFilter(default_state))
async def enter_autowin(message: Message, state: FSMContext):
    await message.answer(text="🥷 Включить автовыигрыш, напиши y - если да, n - если нет!",reply_markup=back_admin_kb)
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
    await message.answer(text="😎 Данные получены",reply_markup=tune_battle_admin_kb)
    await state.clear()

@admin_router.message(StateFilter(FSMFillForm.fill_autowin_state))
async def get_autowin_invalid(message: Message):
    await message.answer(text="Вы ввели неверные данные. Пожалуйста, попробуйте снова.",reply_markup=back_admin_kb)



#@admin_router.message()

# --------------

@admin_router.message(F.text == "👥 Список участников")
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
                username = "Неизвестно"
            command = f'/prof{user_id}'
            user_info = f'ID: {user_id}, ник: @{username}, анкета: {command}\n'
            
            # Если добавление информации о новом пользователе превысит лимит
            if len(text) + len(user_info) > 4000:
                # Отправляем текущую часть сообщения
                await message.answer(text=text)
                # Начинаем новую часть сообщения
                text = user_info
            else:
                # Добавляем информацию о пользователе к текущей части сообщения
                text += user_info
        
        # Отправляем последнюю часть сообщения, если она не пустая
        if text:
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
                    f"🛰ID: {user_id}\n"
                    f"👽 User: @{await get_username_by_id(user_id)}\n\n"
                    f"🎮 Сыграно фотобатлов: {plays_buttle}\n"
                    f"🥇 Выиграно фотобатлов: {buttle_win}\n"
                    f"⚔ Выиграно дуэлей: {dual_win}\n\n"
                    f"🔑 Дополнительные голоса: {additional_voices}\n"
                    f"💸 Приглашенных рефералов: {referals}"
                )
            except Exception as e:
                print("Не удалось получить ник пользователя. Ошибка:", e)
                caption = (
                    f"🛰ID: {user_id}\n\n"
                    f"🎮 Сыграно фотобатлов: {plays_buttle}\n"
                    f"🥇 Выиграно фотобатлов: {buttle_win}\n"
                    f"⚔ Выиграно дуэлей: {dual_win}\n\n"
                    f"🔑 Дополнительные голоса: {additional_voices}\n"
                    f"💸 Приглашенных рефералов: {referals}"
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
    await message.answer("🙃 Введите НАЗВАНИЕ канала:")
    await state.set_state(FSMFillForm.add_channel_name)
    
@admin_router.message(FSMFillForm.add_channel_name)
async def process_channel_name(message: Message, state: FSMContext):
    # Проверяем корректность ввода (название не должно быть пустым)
    if not message.text or len(message.text) < 3:
        await message.answer("Название канала должно содержать хотя бы 3 символа. Попробуйте снова.")
        return

    # Сохраняем название канала во временное состояние
    await state.update_data(channel_name=message.text)
    await message.answer("🔗 Теперь введите ссылку на канал:")
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




@admin_router.message(F.text == "Добавить информацию к посту")
async def add_info_command(message: Message):
    await message.answer("Выберите действие:", reply_markup=battle_info_kb)

@admin_router.message(F.text == "Изменить сообщение")
async def change_info_command(message: Message, state: FSMContext):
    await message.answer("Введите новый текст сообщения:", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Назад в общие настройки")]],
        resize_keyboard=True
    ))
    await state.set_state(FSMFillForm.waiting_for_text)

@admin_router.message(FSMFillForm.waiting_for_text)
async def process_battle_info(message: Message, state: FSMContext):
    # if message.text == "Назад в общие настройки":
    #     await state.clear()
    #     await message.answer("Возврат к настройкам баттла", reply_markup=tune_battle_admin_kb)
    #     return
    
    if not message.text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение")
        return
    
    await update_info_message(message.text)
    
    await message.answer("Информация успешно обновлена!", reply_markup=tune_battle_admin_kb)
    await state.clear()
    
@admin_router.message(F.text == "Назад в общие настройки")
async def process_battle_info_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Возврат к настройкам баттла", reply_markup=tune_battle_admin_kb)
    return

@admin_router.message(F.text == "Удалить сообщение")
async def delete_info_command(message: Message):
    await delete_info_message()
    await message.answer("Информация удалена!", reply_markup=tune_battle_admin_kb)

@admin_router.message(F.text == "Посмотреть сообщение")
async def view_info_command(message: Message):
    result = await select_info_message()
    
    if result and result[0]:
        await message.answer(f"Текущее сообщение:\n\n{result[0]}")
    else:
        await message.answer("Информационное сообщение не задано")





@admin_router.message(F.text == "Назад к настройкам фото")
async def back_to_settings_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Возврат к настройкам фото", reply_markup=admin_photo_keyboard)


@admin_router.message(F.text == "Фотографии админа")
async def admin_photos_menu(message: Message):
    await message.answer("Выберите действие:", reply_markup=admin_photo_keyboard)


@admin_router.message(F.text == "Добавить фотографии")
async def add_photos_start(message: Message, state: FSMContext):
    await message.answer(
        "Отправьте до 30 вертикальных фотографий разом. Чтобы выйти, нажмите 'Назад' или отправьте /cancel.",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Назад к настройкам фото")]], resize_keyboard=True)
    )
    await state.set_state(FSMFillForm.waiting_for_photos)



@admin_router.message(F.text == "Добавить фотографии")
async def add_photos_start(message: Message, state: FSMContext):
    await message.answer(
        "Отправьте до 30 вертикальных фотографий разом. Чтобы выйти, нажмите 'Назад' или отправьте /cancel.",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Назад к настройкам фото")]], resize_keyboard=True)
    )
    await state.set_state(FSMFillForm.waiting_for_photos)


@admin_router.message(FSMFillForm.waiting_for_photos, F.photo)
async def process_photos(message: Message, state: FSMContext, **kwargs):
    album = kwargs.get('album')  # Получаем альбом из kwargs
    
    if album:  # Если это альбом
        if len(album) > 30:
            await message.answer("Вы можете отправить не более 30 фотографий за раз")
            return

        valid_photos = []
        skipped = 0

        for msg in album:
            photo = msg.photo[-1]
            if photo.width < photo.height:
                valid_photos.append(photo.file_id)
            else:
                skipped += 1

        if valid_photos:
            await save_admin_photo_two(valid_photos)  # Теперь valid_photos передается корректно
            response = f"Успешно добавлено {len(valid_photos)} фотографий"
            if skipped > 0:
                response += f"\nПропущено {skipped} неподходящих фотографий"
            await message.answer(response)
        else:
            await message.answer("Не удалось добавить ни одной фотографии. Убедитесь, что все фотографии вертикальные.")

    else:  # Если одиночное фото
        photo = message.photo[-1]
        if photo.width < photo.height:
            await save_admin_photo(photo.file_id)
            await message.answer("Фотография успешно добавлена!")
        else:
            await message.answer("Фотография должна быть вертикальной")



            
            
@admin_router.message(FSMFillForm.waiting_for_photos)
async def error_multiple_photos(message: Message, state: FSMContext):
    await message.answer(
        text='Пожалуйста, на этом шаге отправьте '
             'ваше фото\n\nЕсли вы хотите прервать '
             'заполнение анкеты - отправьте команду /cancel или нажмите на кнопку "Назад к настройкам фото"'    )


@admin_router.message(F.text == "Удалить первую фотографию")
async def delete_first_photo_handler(message: Message):
    photo_id = await select_admin_photo()
    if photo_id:
        await message.answer(f"Фотография с ID {photo_id} была удалена.")
    else:
        await message.answer("Нет фотографий для удаления.")
        
        
@admin_router.message(F.text == "Просмотреть первую фотографию")
async def view_first_photo_handler(message: Message):
    photo_id = await get_first_photo()
    if photo_id:
        await message.answer_photo(photo_id, caption="Самая первая добавленная фотография.")
    else:
        await message.answer("Нет фотографий для просмотра.")




@admin_router.message(F.text == "Выложить донабор")
async def add_participants_from_buffer_to_battle(message: Message):
    users_buffer = await get_users_in_buffer()
    if users_buffer:
        for user in users_buffer:
            await create_user_in_batl(user['user_id'],user['photo_id'], 'user')
        await message.answer("Все участники успешно добавлены в баттл")
        await delete_users_in_buffer()
    else:
        await message.answer("Не было найдено участников для добавления в баттл")
        
        
        
@admin_router.message(lambda message: message.text == "📧 Уведомления")
async def mailing(message: Message):
    await message.answer(text="📧 Уведомления",reply_markup=get_admin_keyboard_notif())


async def generate_unique_code():
    """Генерация уникального 1-значного кода"""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=1))
        if not await check_notification_code_exists(code):
            return code

@admin_router.message(F.text == "Добавить уведомление")
async def add_notification_start(message: Message, state: FSMContext):
    try:
        await message.answer(
            "Введите текст уведомления, которое будет отправляться пользователям:"
        )
        await state.set_state(FSMNotification.waiting_for_message)
    except Exception as e:
        logging.error(f"Error in add_notification_start: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")

@admin_router.message(StateFilter(FSMNotification.waiting_for_message))
async def process_notification_message(message: Message, state: FSMContext):
    try:
        text = message.text
        entities = message.entities  # Получаем разметку
        await state.update_data(message=text, entities=entities)
        await message.answer(
            "Введите время для ежедневного уведомления в формате ЧЧ:ММ (например, 14:30):"
        )
        await state.set_state(FSMNotification.waiting_for_time)
    except Exception as e:
        logging.error(f"Error in process_notification_message: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")
        await state.clear()

@admin_router.message(StateFilter(FSMNotification.waiting_for_time))
async def process_notification_time(message: Message, state: FSMContext):
    try:
        # Проверяем корректность формата времени
        time_str = message.text
        time_obj = datetime.strptime(time_str, "%H:%M").time()

        data = await state.get_data()
        notification_message = data['message']
        entities = data.get('entities', None)

        await state.update_data(time=time_str)
        
        # # Дополнительный вывод в лог
        # logging.info(f"Adding notification: {code} - {notification_message} - {time_str}")
        
        # # Сохраняем уведомление в БД
        # await add_notification(code, notification_message, time_str, entities)
        
        # # Дополнительный вывод в лог
        # logging.info(f"Scheduling notification: {code} - {notification_message} - {time_obj}")
        
        # await scheduler_manager.add_notification_job(code, notification_message, time_obj, entities)
        # await message.answer(
        #     f"✅ Уведомление успешно добавлено!\n\n"
        #     f"📝 Код: {code}\n"
        #     f"⏰ Время: {message.text}\n"
        #     f"📜 Текст: {notification_message}\n\n"
        #     f"Уведомление будет отправляться ежедневно в указанное время.",
        #     reply_markup=get_admin_keyboard_notif()
        # )
        # Спрашиваем, куда отправлять уведомление
        buttons = [
            [KeyboardButton(text="🗣 В канал")],
            [KeyboardButton(text="💬 В ЛС пользователям")]
        ]
        keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
        await message.answer("Выберите, куда будет отправляться уведомление:", reply_markup=keyboard)
        await state.set_state(FSMNotification.waiting_for_target)
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат времени. Пожалуйста, используйте формат ЧЧ:ММ"
        )
    except Exception as e:
        logging.error(f"Error in process_notification_time: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")
        await state.clear()


@admin_router.message(StateFilter(FSMNotification.waiting_for_target))
async def process_notification_target(message: Message, state: FSMContext):
    data = await state.get_data()
    notification_message = data['message']
    entities = data.get('entities', None)
    time_str = data['time']

    if message.text == "💬 В ЛС пользователям":
        target = "private"
    elif message.text == "🗣 В канал":
        target = "channel"
        await state.update_data(target=target)
    else:
        await message.answer("⚠ Неверный выбор. Выберите вариант из предложенных.")
        return

    code = await generate_unique_code()
    await add_notification(code, notification_message, time_str, entities, target)
    await scheduler_manager.add_notification_job(code, notification_message, time_str, entities, target)

    await message.answer(f"✅ Уведомление добавлено! Оно будет отправляться в {target}.",reply_markup=get_admin_keyboard_notif())
    await state.clear()


# @admin_router.message(StateFilter(FSMNotification.waiting_for_channel))
# async def process_notification_channel(message: Message, state: FSMContext):
#     data = await state.get_data()
#     notification_message = data['message']
#     entities = data.get('entities', None)
#     time_str = data['time']
#     target = data['target']
#     channel_id = message.text.strip()

#     code = await generate_unique_code()
#     await add_notification(code, notification_message, time_str, entities, target, channel_id)
#     await scheduler_manager.add_notification_job(code, notification_message, time_str, entities, target, channel_id)

#     await message.answer(f"✅ Уведомление добавлено! Оно будет отправляться в канал {channel_id}.")
#     await state.clear()




@admin_router.message(F.text == "Список уведомлений")
async def view_notifications(message: Message):
    try:
        notifications = await get_all_notifications()
        if not notifications:
            await message.answer(
                "📝 Список уведомлений пуст",
                reply_markup=get_admin_keyboard_notif()
            )
            return

        text = "📋 Список активных уведомлений:\n\n"
        for notif in notifications:
            text += f"🔹 Код: {notif[1]}\n"
            text += f"⏰ Время: {notif[3]}\n"
            text += f"📜 Текст: {notif[2]}\n"
            text += "─────────────────\n"

        await message.answer(
            text,
            reply_markup=get_notifications_keyboard()
        )
    except Exception as e:
        logging.error(f"Error in view_notifications: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")

@admin_router.message(F.text == "Удалить уведомление")
async def delete_notification_start(message: Message, state: FSMContext):
    try:
        await message.answer(
            "Введите код уведомления, которое хотите удалить:"
        )
        await state.set_state(FSMNotification.waiting_for_code)
    except Exception as e:
        logging.error(f"Error in delete_notification_start: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")


@admin_router.message(StateFilter(FSMNotification.waiting_for_code))
async def delete_notifications(message: Message, state: FSMContext):
    try:
        code = message.text
        notification = await get_notification_by_code(code)
        if notification:
            await delete_notification(code)
            await scheduler_manager.remove_notification_job(code)
            await message.answer(f"Уведомление с кодом {code} успешно удалено.")
        else:
            await message.answer(f"Уведомление с кодом {code} не найдено.")
        await state.clear()
    except Exception as e:
        logging.error(f"Error deleting notification: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")
        await state.clear()


@admin_router.message(Command("au"))
async def auction_menu(message: Message):
    await message.answer("Выберите действие:", reply_markup=get_auction_kb())

@admin_router.message(F.text == "Просмотреть сообщения")
async def view_messages(message: Message, state: FSMContext):
    dates = await get_distinct_dates()
    if not dates:
        await message.answer("Нет сохраненных сообщений.")
        return

    dates_text = "Доступные даты:\n" + "\n".join([date[0] for date in dates])
    await message.answer(
        f"{dates_text}\n\nВведите дату в формате MM-DD:"
    )
    await state.set_state(DateInput.waiting_for_date)
    await state.update_data(action="view")

@admin_router.message(F.text == "Удалить сообщения")
async def delete_messages(message: Message, state: FSMContext):
    dates = await get_distinct_dates()
    if not dates:
        await message.answer("Нет сохраненных сообщений.")
        return

    dates_text = "Доступные даты:\n" + "\n".join([date[0] for date in dates])
    await message.answer(
        f"{dates_text}\n\nВведите дату для удаления сообщений (MM-DD):"
    )
    await state.set_state(DateInput.waiting_for_date)
    await state.update_data(action="delete")

@admin_router.message(DateInput.waiting_for_date)
async def process_date_input(message: Message, state: FSMContext):
    try:
        input_date = f"2025-{message.text}"
        datetime.strptime(input_date, '%Y-%m-%d')

        state_data = await state.get_data()
        action = state_data.get("action")

        if action == "view":
            messages = await get_messages_by_date(input_date)
            if not messages:
                await message.answer("Сообщений за эту дату не найдено.")
            else:
                result_text = f"Сообщения за {message.text}:\n\n"
                for msg_text, msg_time in messages:
                    result_text += f"[{msg_time}]\n{msg_text}\n\n"
                
                if len(result_text) <= 4096:
                    await message.answer(result_text)
                else:
                    parts = [result_text[i:i+4096] for i in range(0, len(result_text), 4096)]
                    for part in parts:
                        await message.answer(part)

        elif action == "delete":
            await delete_messages_by_date(input_date)
            await message.answer(f"Сообщения за {message.text} удалены.")

        await state.clear()
        await message.answer("Выберите действие:", reply_markup=get_main_admin_kb(message.from_user.id))

    except ValueError:
        await message.answer("Неверный формат даты. Пожалуйста, используйте формат MM-DD")

@admin_router.message(F.text == "Назад")
async def back_to_main(message: Message):
    await message.answer("Главное меню", reply_markup=get_main_admin_kb(message.from_user.id))
