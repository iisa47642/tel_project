import asyncio
import logging
import os
from random import randint

from aiogram import Bot, Router, F
from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto

from config.config import load_config
from database.db import create_user, create_user_in_batl, get_participants, select_admin_photo, update_points, \
    get_round_results, get_message_ids, clear_message_ids, \
    get_user, edit_user, select_user_from_battle, select_max_number_of_users_voices, select_admin_autowin_const, \
    insert_admin_autowin_const, edit_admin_autowin_const, select_battle_settings, select_all_admins,users_dual_win_update

from filters.isAdmin import is_admin

_bot: Bot = None  # Placeholder for the bot instance

def setup_router(dp, bot: Bot):
    global _bot
    _bot = bot
    
channel_router = Router()
user_clicks = {0:{}}

async def send_battle_pairs(bot: Bot, channel_id: int, participants):
    """
    Отправляет пары участников в канал для голосования.
    """
    message_ids = []
    
    for i in range(0, len(participants), 2):
        if i + 1 < len(participants):
            pair_message_ids = await send_pair(bot, channel_id, participants[i], participants[i+1])
        else:
            pair_message_ids = await send_single(bot, channel_id, participants[i])
        message_ids.extend(pair_message_ids)
    
    return message_ids

async def send_pair(bot: Bot, channel_id: int, participant1, participant2):
    """
    Отправляет пару участников в канал.
    """
    media = [
        InputMediaPhoto(media=participant1['photo_id'], caption=f""),
        InputMediaPhoto(media=participant2['photo_id'], caption=f"")
    ]
    media_message = await bot.send_media_group(channel_id, media)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Левый: 0",
                              callback_data=f"vote:{participant1['user_id']}:left"),
        InlineKeyboardButton(text=f"Право: 0",
                              callback_data=f"vote:{participant2['user_id']}:right")]
    ])
    vote_message = await bot.send_message(channel_id, "Голосуйте за понравившегося участника!", reply_markup=keyboard)
    ADMIN_ID=0
    if (participant1['user_id'] == ADMIN_ID):
        await edit_admin_autowin_const("message_id", vote_message.message_id)
        await edit_admin_autowin_const("admin_id", participant1['user_id'])
        await edit_admin_autowin_const("admin_position", 'left')
        await edit_admin_autowin_const("user_id", participant2['user_id'])
    elif (participant2['user_id'] == ADMIN_ID):
        await edit_admin_autowin_const("message_id", vote_message.message_id)
        await edit_admin_autowin_const("admin_id", participant2['user_id'])
        await edit_admin_autowin_const("admin_position", "right")
        await edit_admin_autowin_const("user_id", participant1['user_id'])
    
    return [msg.message_id for msg in media_message] + [vote_message.message_id]

async def send_single(bot: Bot, channel_id: int, participant):
    """
    Отправляет одиночного участника в канал.
    """
    # f"Участник №{participant['user_id']}"
    photo_message = await bot.send_photo(channel_id, participant['photo_id'], caption="")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=
                              #f"Голос за участника №{participant['user_id']} \n"+
                              f"Голосов сейчас: 0"
                              , callback_data=f"vote:{participant['user_id']}:middle")]
    ])
    vote_message = await bot.send_message(channel_id, "Голосуйте за участника!", reply_markup=keyboard)

    ADMIN_ID = 0
    if (participant['user_id'] == ADMIN_ID):
        await insert_admin_autowin_const("message_id", vote_message.message_id)
        await insert_admin_autowin_const("admin_id", participant['user_id'])
        await insert_admin_autowin_const("admin_position", "middle")
        await insert_admin_autowin_const("user_id", participant['user_id'])
    
    return [photo_message.message_id, vote_message.message_id]

async def end_round(bot: Bot, channel_id: int, min_votes_for_single: int):
    """
    Завершает текущий раунд и объявляет результаты.
    """
    results = await get_round_results(min_votes_for_single)
    message = "Результаты раунда:\n\n"
    loser_ids = []
    # print(results)
    for pair in results:
        # Если пара состоит из двух участников
        if len(pair) == 2:
            participant1, participant2 = pair

            # Если оба исключены, оба проигрывают
            if participant1['is_kick'] == 1 and participant2['is_kick'] == 1:
                loser_ids.extend([participant1['user_id'], participant2['user_id']])
                message += (
                    f"Участник №{participant1['user_id']} и участник №{participant2['user_id']} "
                    f"исключены за нарушение правил\n"
                )
                continue

            # Если первый участник исключён, второй выигрывает
            if participant1['is_kick'] == 1:
                loser_ids.append(participant1['user_id'])
                message += (
                    f"Участник №{participant1['user_id']} исключен за нарушение правил. "
                    f"Победителем становится участник №{participant2['user_id']}\n"
                )
                await users_dual_win_update(participant2['user_id'])
                continue

            # Если второй участник исключён, первый выигрывает
            if participant2['is_kick'] == 1:
                loser_ids.append(participant2['user_id'])
                message += (
                    f"Участник №{participant2['user_id']} исключен за нарушение правил. "
                    f"Победителем становится участник №{participant1['user_id']}\n"
                )
                await users_dual_win_update(participant1['user_id'])
                continue
            
            if participant1['votes'] == participant2['votes']:
                message += (
                    f"Участник №{participant1['user_id']} сыграл в ничью с участником №{participant2['user_id']} "
                    f"со счетом {participant1['votes']}:{participant2['votes']}\n"
                )
                for partic in pair:
                    try:
                        await bot.send_message(
                        partic['user_id'],
                        f"Поздравляем! Вы сыграли в ничью "
                        f"со счетом {participant1['votes']}:{participant2['votes']}. Вы проходите в следующий раунд!"
                    )
                    except Exception as e:
                        print(f"Ошибка при отправке личного сообщения: {e}")
                continue
            
            
            # Если оба не исключены, побеждает тот, кто набрал больше голосов
            winner, loser = sorted(pair, key=lambda x: x['votes'], reverse=True)
            message += (
                f"Участник №{winner['user_id']} побеждает участника №{loser['user_id']} "
                f"со счетом {winner['votes']}:{loser['votes']}\n"
            )
            await users_dual_win_update(winner['user_id'])
            loser_ids.append(loser['user_id'])
            # Отправляем личные сообщения победителю и проигравшему
            try:
                await bot.send_message(
                    winner['user_id'],
                    f"Поздравляем! Вы победили участника №{loser['user_id']} "
                    f"со счетом {winner['votes']}:{loser['votes']}. Вы проходите в следующий раунд!"
                )
                await bot.send_message(
                    loser['user_id'],
                    f"К сожалению, вы проиграли участнику №{winner['user_id']} "
                    f"со счетом {loser['votes']}:{winner['votes']}. Спасибо за участие!"
                )
            except Exception as e:
                print(f"Ошибка при отправке личного сообщения: {e}")

        # Если один участник без пары
        elif len(pair) == 1:
            participant = pair[0]

            # Если участник исключён, он проигрывает
            if participant['is_kick'] == 1:
                loser_ids.append(participant['user_id'])
                message += f"Участник №{participant['user_id']} исключен за нарушение правил\n"
                continue

            # Если участник набрал достаточно голосов, он проходит дальше
            if participant['votes'] >= min_votes_for_single:
                message += (
                    f"Участник №{participant['user_id']} проходит дальше с {participant['votes']} голосами\n"
                )
                try:
                    await bot.send_message(
                        participant['user_id'],
                        f"Поздравляем! Вы набрали {participant['votes']} голосов и проходите в следующий раунд!"
                    )
                except Exception as e:
                    print(f"Ошибка при отправке личного сообщения: {e}")
            else:
                # Если участник не набрал достаточно голосов, он проигрывает
                loser_ids.append(participant['user_id'])
                message += (
                    f"Участник №{participant['user_id']} выбывает с {participant['votes']} голосами\n"
                )
                try:
                    await bot.send_message(
                        participant['user_id'],
                        f"К сожалению, вы выбываете из конкурса, набрав {participant['votes']} голосов. Спасибо за участие!"
                    )
                except Exception as e:
                    print(f"Ошибка при отправке личного сообщения: {e}")

    # Отправляем общий результат в канал
    result_message = await bot.send_message(channel_id, message)
    
    return [[result_message.message_id], loser_ids]


async def get_super_admin_ids():
        dirname = os.path.dirname(__file__)
        filename = os.path.abspath(os.path.join(dirname, '..', 'config/config.env'))
        config = load_config(filename)
        return config.tg_bot.super_admin_ids


async def announce_winner(bot: Bot, channel_id: int, winners):
    """
    Объявляет победителя баттла.
    """
    # Отправляем личное сообщение победителю
    for winner in winners:
        try:
            secret_code = randint(1000,9999)
            if len(winners)==1:
                await bot.send_message(winner['user_id'], f"Поздравляем! Вы победили в баттле! Ваш секретный код {secret_code}. Обратитесь в поддержку за получением приза")
            if len(winners)==2:
                await bot.send_message(winner['user_id'], f"Поздравляем! Вы сыграли в ничью в баттле с другим участником! Ваш секретный код {secret_code}. Обратитесь в поддержку за получением приза")
        except Exception as e:
            logging.error(f"Failed to send congratulation message to winner (ID: {winner['user_id']}): {e}")
            # Отправляем сообщение администратору о проблеме
            try:
                error_message = (
                    f"⚠️ Не удалось отправить поздравление победителю:\n"
                    f"ID: {winner['user_id']}\n"
                    f"Ошибка: {str(e)}"
                )
                
                ADMIN_ID = await select_all_admins()
                admin_ids = []
                if ADMIN_ID:
                    admin_ids = [i[0] for i in ADMIN_ID]
                admin_ids += await get_super_admin_ids()
                for admin_id in admin_ids:
                    await bot.send_message(admin_id, error_message)
            except Exception as admin_error:
                logging.error(f"Failed to notify admin about winner message error: {admin_error}")
    if len(winners)==1:
        winner = winners[0]
        media = [
        InputMediaPhoto(media=winner['photo_id'], caption=f"Поздравляем участника №{winner['user_id']}! Победитель баттла!")
    ]
        
    if len(winners)==2:
        winner1 = winners[0]
        winner2 = winners[1]
        media = [
        InputMediaPhoto(media=winner1['photo_id'], caption=f"Поздравляем участников №{winner1['user_id']} и №{winner2['user_id']}! Сыгравших баттл в ничью!"),
        InputMediaPhoto(media=winner2['photo_id'], caption=f"")
    ]
    winner_message = await bot.send_media_group(channel_id, media)
    return [msg.message_id for msg in winner_message]

async def delete_previous_messages(bot: Bot, channel_id: int):
    """
    Удаляет предыдущие сообщения в канале.
    """
    message_ids = await get_message_ids()
    for msg_id in message_ids:
        try:
            await bot.delete_message(channel_id, msg_id)
        except Exception as e:
            print(f"Не удалось удалить сообщение {msg_id}: {e}")
    await clear_message_ids()

async def make_keyboard(callback: CallbackQuery):
    #votes:id:pos
    splitted_callback_data = callback.data.split(":")
    if splitted_callback_data[2] == "left":
        right_callback_data=callback.message.reply_markup.inline_keyboard[0][1].callback_data
        splitted_right_text = callback.message.reply_markup.inline_keyboard[0][0].text.split(":")
        right_text= callback.message.reply_markup.inline_keyboard[0][1].text
        old_text = splitted_right_text[0]
        current_value = int(splitted_right_text[1]) + 1
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=old_text+f": {current_value}", callback_data=callback.data),
                    InlineKeyboardButton(text=right_text, callback_data=right_callback_data)
                ]
            ])
        return keyboard
    elif splitted_callback_data[2] == "right":
        left_callback_data = callback.message.reply_markup.inline_keyboard[0][0].callback_data
        splitted_right_text = callback.message.reply_markup.inline_keyboard[0][1].text.split(":")
        left_text = callback.message.reply_markup.inline_keyboard[0][0].text
        old_text = splitted_right_text[0]
        current_value = int(splitted_right_text[1]) + 1
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=left_text, callback_data=left_callback_data),
                    InlineKeyboardButton(text=old_text + f": {current_value}", callback_data=callback.data),

                ]
            ])
        return keyboard
    elif splitted_callback_data[2] == "middle":
        splitted_text=callback.message.reply_markup.inline_keyboard[0][0].text.split(":")
        old_text = splitted_text[0]
        current_value = int(splitted_text[1])+1


        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=
                                   old_text+f": {current_value}"
                                  , callback_data=callback.data)]
        ])
        return keyboard

def get_channel_id():
    dirname = os.path.dirname(__file__)
    filename = os.path.abspath(os.path.join(dirname, '..', 'config/config.env'))
    config = load_config(filename)
    return config.tg_bot.channel_id


async def check_subscription(user_id: int) -> bool:
    """Проверяет, подписан ли пользователь на указанный канал."""
    try:
        member = await _bot.get_chat_member(chat_id=get_channel_id(), user_id=user_id)
        # Возможные статусы: 'creator', 'administrator', 'member', 'restricted', 'left', 'kicked'
        return member.status in ("creator", "administrator", "member")
    except Exception as e:
        print(f"Ошибка при проверке подписки: {e}")
        return False


async def get_new_participants(current_participants):
        """
        Проверяет базу данных на наличие новых участников, которых ещё нет в текущем списке.
        """
        all_participants = await get_participants()  # Получаем всех участников из базы
        current_ids = {p['user_id'] for p in current_participants}  # ID текущих участников

        # Фильтруем новых участников
        new_participants = [p for p in all_participants if p['user_id'] not in current_ids]

        if new_participants:
            logging.info(f"Найдены новые участники: {[p['user_id'] for p in new_participants]}")

        return new_participants


async def update_admin_kb(
        message_id,
        admin_id,
        admin_position="middle",
        user_id=None,
        chat_id=get_channel_id(),
):
    """
        Обновляет клавиатуру администратора.

        Эта функция редактирует клавиатуру сообщения в зависимости от позиции администратора.
        Если позиция администратора "middle", создается новая клавиатура для одиночного голосования.
        В противном случае создается новая клавиатура для двойного голосования.

        :param message_id: ID сообщения, которое нужно отредактировать
        :param admin_id: ID администратора
        :param admin_position: Позиция администратора в голосовании ("middle" по умолчанию)
        :param user_id: ID пользователя (необязательный параметр, используется для двойного голосования)
        :param chat_id: ID чата (по умолчанию используется ID канала)
    """
    try:
        if admin_position=="middle":
            await _bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=await make_new_single_keyboard_and_update_db(admin_position, admin_id)
            )
        else:
            await _bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=await make_new_double_keyboard_and_update_db(admin_position, admin_id, user_id)
            )
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)

async def make_new_double_keyboard_and_update_db(admin_position,admin_id,user_id):
    """
        Создает новую клавиатуру для двойного голосования и обновляет базу данных.

        Эта функция получает количество голосов администратора и пользователя, обновляет очки администратора
        и создает новую клавиатуру для двойного голосования с обновленным количеством голосов.

        :param admin_position: Позиция администратора в голосовании ("left" или "right")
        :param admin_id: ID администратора
        :param user_id: ID пользователя
        :return: Объект InlineKeyboardMarkup с обновленной клавиатурой
    """
    number_of_admins_votes = await select_user_from_battle(admin_id)
    number_of_admins_votes = number_of_admins_votes[3]
    number_of_users_votes = await select_user_from_battle(user_id)
    number_of_users_votes = number_of_users_votes[3]
    await update_points(admin_id)

    if admin_position == "left":
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"Левый: {number_of_admins_votes+1}",callback_data=f"vote:{admin_id}:left"),
                 InlineKeyboardButton(text=f"Право: {number_of_users_votes}",callback_data=f"vote:{user_id}:right"),]
            ],
            resize_keyboard=True
        )
        return keyboard
    elif admin_position == "right":
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"Левый: {number_of_users_votes}",callback_data=f"vote:{user_id}:left"),
                 InlineKeyboardButton(text=f"Право: {number_of_admins_votes+1}", callback_data=f"vote:{admin_id}:right"), ]
            ],
            resize_keyboard=True
        )
        return keyboard

async def make_new_single_keyboard_and_update_db(admin_position,admin_id):
    """
        Создает новую клавиатуру для одиночного голосования и обновляет базу данных.

        Эта функция получает количество голосов администратора, обновляет его очки и создает новую клавиатуру
        для одиночного голосования с обновленным количеством голосов.

        :param admin_position: Позиция администратора в голосовании (должна быть "middle")
        :param admin_id: ID администратора
        :return: Объект InlineKeyboardMarkup с обновленной клавиатурой
    """

    number_of_admins_votes = await select_user_from_battle(admin_id)
    number_of_admins_votes=number_of_admins_votes[3]
    await update_points(admin_id)
    if admin_position == "middle":
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"Голосов сейчас: {number_of_admins_votes+1}", callback_data=f"vote:{admin_id}:middle"),]
            ]
        )
        return keyboard

async def need_intervention(admin_id):
    """
        Проверяет, требуется ли вмешательство администратора.

        Эта функция сравнивает количество голосов администратора с максимальным количеством голосов пользователей,
        добавляя дельту. Если количество голосов администратора меньше, чем максимальное количество голосов пользователей плюс дельта,
        функция возвращает True, иначе False.

        :param admin_id: ID администратора
        :return: True, если требуется вмешательство, иначе False
    """
    delta=5
    number_of_admins_votes = await select_user_from_battle(admin_id)
    number_of_admins_votes=number_of_admins_votes[3]
    max_number_of_users_voices = await select_max_number_of_users_voices(admin_id)
    max_number_of_users_voices=max_number_of_users_voices[0]
    if number_of_admins_votes < max_number_of_users_voices + delta:
        return True
    return False



# 842589261,1270990667

async def is_admin(callback: CallbackQuery) -> bool:
    dirname = os.path.dirname(__file__)
    filename = os.path.abspath(os.path.join(dirname, '..', 'config/config.env'))
    config = load_config(filename)
    SUPER_ADMIN_IDS = config.tg_bot.super_admin_ids
    if callback.from_user.id in SUPER_ADMIN_IDS:
        return True
    ADMIN_ID = await select_all_admins()
    if ADMIN_ID:
        ADMIN_ID = [i[0] for i in ADMIN_ID]
        return callback.from_user.id in ADMIN_ID
    else:
        return False


@channel_router.callback_query(F.data.startswith("vote:"))
async def process_vote(callback: CallbackQuery):

    """
    Обрабатывает голосование пользователей.
    """

    #TODO check if subscribed before getting by uID
    uID = callback.from_user.id

    if await check_subscription(uID):
        keyboard = await make_keyboard(callback)
        mID = callback.message.message_id
        member=await _bot.get_chat_member(user_id=uID,chat_id=get_channel_id())

        number_of_additional_votes=0
        user=0
        user = await get_user(uID)
        if user == False :
            number_of_additional_votes=0
        else:
            number_of_additional_votes=user[5]

        # allowed_number_of_votes=number_of_additional_votes+1

        # {uID:{mID:clicks}}

        if uID not in user_clicks:
            user_clicks[uID]={}
            if mID not in user_clicks[uID]:
                user_clicks[uID][mID]=0
        elif mID not in user_clicks[uID]:
            user_clicks[uID][mID] = 0

        is_admin_of_bot=await is_admin(callback)

        if user_clicks.get(uID) is not None and user_clicks.get(uID).get(mID) is not None and user_clicks[uID][mID] >= 1 and member.status not in ["creator", "administrator"] and not is_admin_of_bot:
            if number_of_additional_votes > 0:
                user_id = int(callback.data.split(':')[1]) # the one who is voted
                await update_points(user_id)
                number_of_additional_votes-=1
                await edit_user(uID,'additional_voices',number_of_additional_votes)
                try:
                    await callback.message.edit_reply_markup(reply_markup=keyboard)
                except TelegramRetryAfter as e:
                    await asyncio.sleep(e.retry_after)
                try:
                    await callback.answer("Ваш голос учтен!")
                except TelegramBadRequest as e:
                    pass
            else:
                await callback.answer("Вы уже проголосовали")
        else:
            user_clicks[uID][mID] += 1
            try:
                await callback.message.edit_reply_markup(reply_markup=keyboard)
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
            user_id = int(callback.data.split(':')[1])
            await update_points(user_id)
            try:
                await callback.answer("Ваш голос учтен!")
            except TelegramBadRequest as e:
                pass

        # Получает настройки баттла
        settings=await select_battle_settings()
        # Проверяет, включен ли автоматический выигрыш
        is_autowin=settings[5]

        if is_autowin:
            # Получает ID администратора для автоматического выигрыша
            admin_id= await select_admin_autowin_const("admin_id")
            admin_id=admin_id[0]

            # Проверяет, требуется ли вмешательство администратора
            if await need_intervention(admin_id):
                # Получает ID сообщения для автоматического выигрыша
                message_id=await select_admin_autowin_const("message_id")
                message_id=message_id[0]

                # Получает позицию администратора в голосовании
                admin_position=await select_admin_autowin_const("admin_position")
                admin_position=admin_position[0]

                # Получает ID пользователя для автоматического выигрыша
                user_id = await select_admin_autowin_const("user_id")
                user_id = user_id[0]

                # Обновляет клавиатуру администратора
                await update_admin_kb(message_id,admin_id,admin_position,user_id)
    else:
        await callback.answer("Для использования бота подпишитесь на канал")

async def make_some_magic():
    """
        Проверяет, включен ли автоматический выигрыш, и выполняет необходимые действия.

        Эта функция проверяет настройки баттла, чтобы узнать, включена ли функция автоматического выигрыша.
        Если она включена, функция получает ID фото администратора, создает пользователя с ID 0 (если он еще не создан),
        и добавляет этого пользователя в баттл с полученным ID фото.
    """
    # Проверяет, включен ли автоматический выигрыш
    settings = await select_battle_settings()
    is_autowin = settings[5]

    if is_autowin:
        # Получает ID фото администратора
        photo_id=await select_admin_photo()
        photo_id=photo_id[1]

        # Создает пользователя с ID 0, если он еще не создан
        try:
            await create_user(0,'user')
        except Exception:
            pass

        # Добавляет пользователя с ID 0 в баттл с полученным ID фото
        await create_user_in_batl(0,photo_id, 'user')