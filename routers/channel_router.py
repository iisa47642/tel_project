from aiogram import Bot, Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from database.db import get_participants, update_points, get_round_results, get_message_ids, clear_message_ids

_bot: Bot = None  # Placeholder for the bot instance

def setup_router(dp, bot: Bot):
    global _bot
    _bot = bot
    
channel_router = Router()

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
    media = [
        InputMediaPhoto(media=participant1['photo_id'], caption=f"Участник №{participant1['user_id']} и " + f"Участник №{participant2['user_id']}"),
        InputMediaPhoto(media=participant2['photo_id'], caption=f"Участник №{participant2['user_id']}")
    ]
    media_message = await bot.send_media_group(channel_id, media)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Голос за участника №{participant1['user_id']}", callback_data=f"vote:{participant1['user_id']}")],
        [InlineKeyboardButton(text=f"Голос за участника №{participant2['user_id']}", callback_data=f"vote:{participant2['user_id']}")]
    ])
    vote_message = await bot.send_message(channel_id, "Голосуйте за понравившегося участника!", reply_markup=keyboard)
    
    return [msg.message_id for msg in media_message] + [vote_message.message_id]

async def send_single(bot: Bot, channel_id: int, participant):
    """
    Отправляет одиночного участника в канал.
    """
    photo_message = await bot.send_photo(channel_id, participant['photo_id'], caption=f"Участник №{participant['user_id']}")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Голос за участника №{participant['user_id']}", callback_data=f"vote:{participant['user_id']}")]
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

@channel_router.callback_query(F.data.startswith("vote:"))
async def process_vote(callback: CallbackQuery):
    """
    Обрабатывает голосование пользователей.
    """
    user_id = int(callback.data.split(':')[1])
    await update_points(user_id)
    await callback.answer("Ваш голос учтен!")

# def setup_channel_router(dp: Dispatcher):
#     dp.include_router(channel_router)