from aiogram import Bot, Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from database.db import get_participants, update_points, get_round_results, get_message_ids, clear_message_ids

_bot: Bot = None  # Placeholder for the bot instance

def setup_router(dp, bot: Bot):
    global _bot
    _bot = bot
    
channel_router = Router()
user_clicks = {}

async def send_battle_pairs(bot: Bot, channel_id: int):
    """
    Отправляет пары участников в канал для голосования.
    """
    participants = await get_participants()
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
    # эта параша работает нормально, но выглядит неправильно, надо править
    media = [
        InputMediaPhoto(media=participant1['photo_id'], caption=f"Участник №{participant1['user_id']} и " + f"Участник №{participant2['user_id']}"),
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
    
    return [msg.message_id for msg in media_message] + [vote_message.message_id]

async def send_single(bot: Bot, channel_id: int, participant):
    """
    Отправляет одиночного участника в канал.
    """
    photo_message = await bot.send_photo(channel_id, participant['photo_id'], caption=f"Участник №{participant['user_id']}")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=
                              f"Голос за участника №{participant['user_id']} \n"+
                              f"Голосов сейчас: 0"
                              , callback_data=f"vote:{participant['user_id']}:middle")]
    ])
    vote_message = await bot.send_message(channel_id, "Голосуйте за участника!", reply_markup=keyboard)
    
    return [photo_message.message_id, vote_message.message_id]

async def end_round(bot: Bot, channel_id: int, min_votes_for_single: int):
    """
    Завершает текущий раунд и объявляет результаты.
    """
    results = await get_round_results(min_votes_for_single)
    message = "Результаты раунда:\n\n"
    loser_ids = []
    for pair in results:
        if len(pair) == 2:
            winner = max(pair, key=lambda x: x['votes'])
            loser = min(pair, key=lambda x: x['votes'])
            loser_ids.append(loser['user_id'])
            message += f"Участник №{winner['user_id']} побеждает участника №{loser['user_id']} со счетом {winner['votes']}:{loser['votes']}\n"
        else:
            participant = pair[0]
            if participant['votes'] >= min_votes_for_single:
                message += f"Участник №{participant['user_id']} проходит дальше с {participant['votes']} голосами\n"
            else:
                loser_ids.append(participant['user_id'])
                message += f"Участник №{participant['user_id']} выбывает с {participant['votes']} голосами\n"
    
    result_message = await bot.send_message(channel_id, message)
    return [[result_message.message_id],loser_ids]

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
        member = await _bot.get_chat_member(chat_id=-1002298527034, user_id=user_id)
        # Возможные статусы: 'creator', 'administrator', 'member', 'restricted', 'left', 'kicked'
        return member.status in ("creator", "administrator", "member")
    except Exception as e:
        print(f"Ошибка при проверке подписки: {e}")
        return False


@channel_router.callback_query(F.data.startswith("vote:"))
async def process_vote(callback: CallbackQuery):
    keyboard = await make_keyboard(callback)
    """
    Обрабатывает голосование пользователей.
    """

    uID = callback.from_user.id
    member=await _bot.get_chat_member(user_id=uID,chat_id=-1002298527034)

    if uID not in user_clicks:
        user_clicks[uID] = 0

    if await check_subscription(uID):
        if user_clicks.get(uID) is not None and user_clicks[uID] == 1 and member.status not in ["creator", "administrator"]:
            await callback.answer("Вы уже проголосовали")
        else:
            user_clicks[uID] += 1
            await callback.message.edit_reply_markup(reply_markup=keyboard)
            user_id = int(callback.data.split(':')[1])
            await update_points(user_id)
            await callback.answer("Ваш голос учтен!")
    else:
        await callback.answer("Для использования бота подпишитесь на канал")