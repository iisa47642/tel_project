import asyncio
import logging
from aiogram import Bot, Router, F
from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from database.db import create_user, create_user_in_batl, get_participants, select_admin_photo, update_points, get_round_results, get_message_ids, clear_message_ids, \
    get_user, edit_user, select_user_from_battle, select_max_number_of_users_voices, select_admin_autowin_const, \
    insert_admin_autowin_const, edit_admin_autowin_const, select_battle_settings

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
                continue

            # Если второй участник исключён, первый выигрывает
            if participant2['is_kick'] == 1:
                loser_ids.append(participant2['user_id'])
                message += (
                    f"Участник №{participant2['user_id']} исключен за нарушение правил. "
                    f"Победителем становится участник №{participant1['user_id']}\n"
                )
                continue

            # Если оба не исключены, побеждает тот, кто набрал больше голосов
            winner, loser = sorted(pair, key=lambda x: x['votes'], reverse=True)
            message += (
                f"Участник №{winner['user_id']} побеждает участника №{loser['user_id']} "
                f"со счетом {winner['votes']}:{loser['votes']}\n"
            )
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




async def announce_winner(bot: Bot, channel_id: int, winner):
    """
    Объявляет победителя баттла.
    """
    winner_message = await bot.send_message(channel_id, f"Поздравляем участника №{winner['user_id']}! Победитель баттла!")
    return [winner_message.message_id]

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

async def check_subscription(user_id: int) -> bool:
    """Проверяет, подписан ли пользователь на указанный канал."""
    try:
        member = await _bot.get_chat_member(chat_id=-1002430244531, user_id=user_id)
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
        chat_id=-1002430244531,
):
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
    delta=5
    number_of_admins_votes = await select_user_from_battle(admin_id)
    number_of_admins_votes=number_of_admins_votes[3]
    max_number_of_users_voices = await select_max_number_of_users_voices(admin_id)
    max_number_of_users_voices=max_number_of_users_voices[0]
    if number_of_admins_votes < max_number_of_users_voices + delta:
        return True
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
        member=await _bot.get_chat_member(user_id=uID,chat_id=-1002430244531)

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

        if user_clicks.get(uID) is not None and user_clicks.get(uID).get(mID) is not None and user_clicks[uID][mID] == 1 and member.status not in ["creator", "administrator"]:
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

        settings=await select_battle_settings()
        is_autowin=settings[5]
        if is_autowin:
            admin_id= await select_admin_autowin_const("admin_id")
            admin_id=admin_id[0]
            if await need_intervention(admin_id):
                message_id=await select_admin_autowin_const("message_id")
                message_id=message_id[0]
                admin_position=await select_admin_autowin_const("admin_position")
                admin_position=admin_position[0]
                user_id = await select_admin_autowin_const("user_id")
                user_id = user_id[0]
                await update_admin_kb(message_id,admin_id,admin_position,user_id)

    else:
        await callback.answer("Для использования бота подпишитесь на канал")

async def make_some_magic():
    settings = await select_battle_settings()
    is_autowin = settings[5]
    if is_autowin:
        photo_id=await select_admin_photo()
        photo_id=photo_id[0]
        try:
            await create_user(0,'user')
        except Exception:
            pass
        await create_user_in_batl(0,photo_id, 'user')