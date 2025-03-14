import asyncio
from collections import defaultdict
import json
import logging
import os
from random import randint
import asyncio
import random
from datetime import datetime, time, timedelta
import logging
from aiogram import F, Bot, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.exceptions import TelegramBadRequest
from aiogram import Bot, Router, F
from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
import pytz
from aiogram.types import Message, MessageOriginChannel, PhotoSize
from config.config import load_config
from database.db import active_battle, create_user, create_user_in_batl, delete_users_single, edit_user, get_current_votes, get_participants, get_user, save_message, select_admin_photo, select_info_message, set_single_user, update_admin_battle_points, update_points, \
    get_round_results, get_message_ids, clear_message_ids,\
    select_battle_settings, select_all_admins,users_dual_win_update
from routers.globals_var import (
    vote_states, user_clicks, pair_locks, vote_states_locks,
    user_last_click, click_counters, click_reset_times
)
import routers.globals_var

from filters.isAdmin import is_admin
from locks import battle_lock

keyboard_update_lock = asyncio.Lock()


_bot: Bot = None  # Placeholder for the bot instance

def setup_router(dp, bot: Bot):
    global _bot
    _bot = bot



channel_router = Router()


async def init_vote_state(message_id: int, admin_id: int, admin_position: str, opponent_id: int, current_start):
    """
    Инициализирует состояние голосования для сообщения с админом
    """
    ROUND_DURATION = routers.globals_var.ROUND_DURATION

    if current_start.hour < 10 and current_start.hour >= 0:  # Если время начала между 00:00 и 10:00
        today = current_start.date()
        end_time = pytz.timezone('Europe/Moscow').localize(datetime.combine(today, time(hour=10)))
        round_duration = (end_time - current_start).total_seconds()
    else:
        round_duration = ROUND_DURATION
    print(round_duration)
    vote_states[message_id] = {
        'admin_id': admin_id,
        'admin_position': admin_position,
        'opponent_id': opponent_id,
        'current_votes': 0,
        'start_time': datetime.now(),
        'last_update_time': datetime.now(),
        'round_duration': round_duration,
        'vote_history': [],
        'is_single': admin_position == "middle"
    }

async def send_battle_pairs(bot: Bot, channel_id: int, participants, prize, round_txt, round_duration, min_votes, current_start):
    """
    Отправляет пары участников в канал для голосования.
    """
    message_ids = []
    
    for i in range(0, len(participants), 2):
        if i + 1 < len(participants):
            pair_message_ids = await send_pair(bot, channel_id, participants[i], participants[i+1], prize, round_txt,round_duration, current_start)
        else:
            pair_message_ids = await send_single(bot, channel_id, participants[i], prize, round_txt,round_duration, min_votes, current_start)
        message_ids.extend(pair_message_ids)
    
    return message_ids

async def send_pair(bot: Bot, channel_id: int, participant1, participant2, prize, round_txt, round_duration, current_start):
    """
    Отправляет пару участников в канал.
    """
    await asyncio.sleep(12)
    media = [
        InputMediaPhoto(media=participant1['photo_id'], caption=f""),
        InputMediaPhoto(media=participant2['photo_id'], caption=f"")
    ]
    media_message = await bot.send_media_group(channel_id, media)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Левый: 0",
                              callback_data=f"vote:{participant1['user_id']}:left"),
        InlineKeyboardButton(text=f"Правый: 0",
                              callback_data=f"vote:{participant2['user_id']}:right")]
    ])
    if 'раунд' in round_txt:
        num = 1
        for i in round_txt:
            if i.isdigit():
                num = int(i)
        round_txt = f'{num} раунд'
    elif 'полуфинал' in round_txt:
        round_txt = 'Полуфинал'
    elif 'финал' in round_txt:
        round_txt = 'Финал'
        
        
        
    # round_end = current_start + timedelta(minutes=round_duration)
    now = datetime.now(current_start.tzinfo)

    if now.hour < 10 and now.hour >= 0:  # Если время между 23:00 и 10:00
        today = now.date()
        round_end_time = pytz.timezone('Europe/Moscow').localize(datetime.combine(today, time(hour=10)))
        wait_time = (round_end_time - now).total_seconds()
        total_minutes = int(wait_time / 60)
    else:
        # Используем текущее время как основу для расчета
        minutes_passed = (now - current_start).total_seconds() / 60
        total_minutes = round_duration - int(minutes_passed)

    end_hour = (total_minutes // 60) % 24
    end_min = total_minutes % 60

    
    # end_hour = round_duration//60
    # end_min = round_duration % 60
    if end_hour == 0:
        end_text = f'{end_min} мин'
    elif end_min == 0:
        if end_hour == 1:
            end_text = f'{end_hour} час'
        elif 2 <= end_hour <= 4:
            end_text = f'{end_hour} часа'
        elif end_hour >= 5:
            end_text = f'{end_hour} часов'
    elif end_hour != 0 and end_min != 0:
        if end_hour == 1:
            end_text = f'{end_hour} час ' + f'{end_min} мин'
        elif 2 <= end_hour <= 4:
            end_text = f'{end_hour} часа ' + f'{end_min} мин'
        elif end_hour >= 5:
            end_text = f'{end_hour} часов ' + f'{end_min} мин'
        
    addit_msg = await select_info_message()
    if addit_msg and addit_msg[0]:
        addit_msg = addit_msg[0]
    else:
        addit_msg = ''
    vote_message = await bot.send_message(channel_id,
                                          f'<b>👑 {round_txt} 👑</b>\n\n'+
                                          f'⏱️Итоги через {end_text}⏱️\n\n'+
                                          f"<a href='t.me/c/{str(channel_id)[4:]}/{media_message[0].message_id}'>⛓️Ссылка на голосование⛓️</a>\n\n"+
                                          f'💵Приз: {prize} 💵\n\n'
                                          f'{addit_msg}',
                                          reply_markup=keyboard,
                                          parse_mode="HTML")
        # Формируем ссылку на пост с голосованием
    vote_link = f"https://t.me/c/{str(channel_id)[4:]}/{vote_message.message_id}"
    
    # Отправляем ссылки участникам
    notification_text = (
        f"🎯 <b>Началось новое голосование с вашим участием!</b>\n\n"
        f"🔗 <a href='{vote_link}'>Ссылка на пост с голосованием</a>\n\n"
        f"⏱️ Продолжительность: {end_text}"
    )
    
    try:
        await bot.send_message(participant1['user_id'], 
                             notification_text, 
                             parse_mode="HTML")
    except Exception as e:
        logging.error(f"Failed to send notification to participant1 {participant1['user_id']}: {e}")
    
    try:
        await bot.send_message(participant2['user_id'], 
                             notification_text, 
                             parse_mode="HTML")
    except Exception as e:
        logging.error(f"Failed to send notification to participant2 {participant2['user_id']}: {e}")
    
    ADMIN_ID=0
    if participant1['user_id'] == ADMIN_ID:
        await init_vote_state(
            message_id=vote_message.message_id,
            admin_id=participant1['user_id'],
            admin_position="left",
            opponent_id=participant2['user_id'],
            current_start=current_start
        )
    # Инициализация для админа справа
    elif participant2['user_id'] == ADMIN_ID:
        await init_vote_state(
            message_id=vote_message.message_id,
            admin_id=participant2['user_id'],
            admin_position="right",
            opponent_id=participant1['user_id'],
            current_start=current_start
        )
    else:
        await init_vote_state(
            message_id=vote_message.message_id,
            admin_id=participant1['user_id'],
            admin_position="left",
            opponent_id=participant2['user_id'],
            current_start=current_start
        )
    return [msg.message_id for msg in media_message] + [vote_message.message_id]

async def send_single(bot: Bot, channel_id: int, participant, prize ,round_txt , round_duration, min_votes, current_start):
    """
    Отправляет одиночного участника в канал.
    """
    # f"Участник №{participant['user_id']}"
    await asyncio.sleep(12)
    photo_message = await bot.send_photo(channel_id, participant['photo_id'], caption="")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=
                              #f"Голос за участника №{participant['user_id']} \n"+
                              f"Голосов сейчас: 0"
                              , callback_data=f"vote:{participant['user_id']}:middle")]
    ])
    if 'раунд' in round_txt:
        num = 1
        for i in round_txt:
            if i.isdigit():
                num = int(i)
        round_txt = f'{num} раунд'
    elif 'полуфинал' in round_txt:
        round_txt = 'Полуфинал'
    elif 'финал' in round_txt:
        round_txt = 'Финал'
        
    now = datetime.now(current_start.tzinfo)

    if now.hour < 10 and now.hour >= 1:
        today = now.date()
        round_end_time = pytz.timezone('Europe/Moscow').localize(datetime.combine(today, time(hour=10)))
        wait_time = (round_end_time - now).total_seconds()
        total_minutes = int(wait_time / 60)
    else:
        # Используем текущее время как основу для расчета
        minutes_passed = (now - current_start).total_seconds() / 60
        total_minutes = round_duration - int(minutes_passed)

    end_hour = (total_minutes // 60) % 24
    end_min = total_minutes % 60
    
    if end_hour == 0:
        end_text = f'{end_min} мин'
    elif end_min == 0:
        if end_hour == 1:
            end_text = f'{end_hour} час'
        elif 2 <= end_hour <= 4:
            end_text = f'{end_hour} часа'
        elif end_hour >= 5:
            end_text = f'{end_hour} часов'
    elif end_hour != 0 and end_min != 0:
        if end_hour == 1:
            end_text = f'{end_hour} час ' + f'{end_min} мин'
        elif 2 <= end_hour <= 4:
            end_text = f'{end_hour} часа ' + f'{end_min} мин'
        elif end_hour >= 5:
            end_text = f'{end_hour} часов ' + f'{end_min} мин'
    addit_msg = await select_info_message()
    if addit_msg and addit_msg[0]:
        addit_msg = addit_msg[0]
    else:
        addit_msg = ''
    vote_message = await bot.send_message(channel_id,
                                          f'<b>👑 {round_txt} 👑</b>\n\n'
                                          f'⏱️Итоги через {end_text}⏱️\n\n'
                                          f"<a href='t.me/c/{str(channel_id)[4:]}/{photo_message.message_id}'>⛓️Ссылка на голосование⛓️</a>\n\n"+
                                          f'☀️ Не хватило соперника, поэтому необходимо набрать {min_votes} голосов!\n\n'
                                          f'💵Приз: {prize} 💵\n\n'
                                          f'{addit_msg}',
                                          reply_markup=keyboard,
                                          parse_mode="HTML")
    
    vote_link = f"https://t.me/c/{str(channel_id)[4:]}/{vote_message.message_id}"
    
    # Отправляем ссылки участникам
    notification_text = (
        f"🎯 <b>Началось новое голосование с вашим участием!</b>\n\n"
        f"🔗 <a href='{vote_link}'>Ссылка на пост с голосованием</a>\n\n"
        f"⏱️ Продолжительность: {end_text}"
    )
    
    try:
        await bot.send_message(participant['user_id'], 
                             notification_text, 
                             parse_mode="HTML")
    except Exception as e:
        logging.error(f"Failed to send notification to participant1 {participant['user_id']}: {e}")
        
    await init_vote_state(
        message_id=vote_message.message_id,
        admin_id=participant['user_id'],
        admin_position="middle",
        opponent_id=0,
        current_start=current_start# для одиночного фото opponent_id не важен
    )
    return [photo_message.message_id, vote_message.message_id]

async def end_round(bot: Bot, channel_id: int, min_votes_for_single: int):
    """
    Завершает текущий раунд и объявляет результаты.
    """
    results = await get_round_results(min_votes_for_single)
    # message = "Результаты раунда:\n\n"
    loser_ids = []
    # print(results)
    for pair in results:
        # Если пара состоит из двух участников
        if len(pair) == 2:
            participant1, participant2 = pair

            # Если оба исключены, оба проигрывают
            if participant1['is_kick'] == 1 and participant2['is_kick'] == 1:
                loser_ids.extend([participant1['user_id'], participant2['user_id']])
                # message += (
                #     f"Участник №{participant1['user_id']} и участник №{participant2['user_id']} "
                #     f"исключены за нарушение правил\n"
                # )
                continue

            # Если первый участник исключён, второй выигрывает
            if participant1['is_kick'] == 1:
                loser_ids.append(participant1['user_id'])
                # message += (
                #     f"Участник №{participant1['user_id']} исключен за нарушение правил. "
                #     f"Победителем становится участник №{participant2['user_id']}\n"
                # )
                await users_dual_win_update(participant2['user_id'])
                continue

            # Если второй участник исключён, первый выигрывает
            if participant2['is_kick'] == 1:
                loser_ids.append(participant2['user_id'])
                # message += (
                #     f"Участник №{participant2['user_id']} исключен за нарушение правил. "
                #     f"Победителем становится участник №{participant1['user_id']}\n"
                # )
                await users_dual_win_update(participant1['user_id'])
                continue
            
            if participant1['votes'] == participant2['votes']:
                # message += (
                #     f"Участник №{participant1['user_id']} сыграл в ничью с участником №{participant2['user_id']} "
                #     f"со счетом {participant1['votes']}:{participant2['votes']}\n"
                # )
                for partic in pair:
                    try:
                        await users_dual_win_update(partic['user_id'])
                        await bot.send_message(
                        partic['user_id'],
                        f"🎉 Поздравляем, вы успешно прошли в следующий раунд! Продолжайте в том же духе и выиграете!"
                    )
                    except Exception as e:
                        print(f"Ошибка при отправке личного сообщения: {e}")
                continue
            
            
            # Если оба не исключены, побеждает тот, кто набрал больше голосов
            winner, loser = sorted(pair, key=lambda x: x['votes'], reverse=True)
            # message += (
            #     f"Участник №{winner['user_id']} побеждает участника №{loser['user_id']} "
            #     f"со счетом {winner['votes']}:{loser['votes']}\n"
            # )
            await users_dual_win_update(winner['user_id'])
            loser_ids.append(loser['user_id'])
            # Отправляем личные сообщения победителю и проигравшему
            try:
                await bot.send_message(
                    winner['user_id'],
                    f"🎉 Поздравляем, вы успешно прошли в следующий раунд! Продолжайте в том же духе и выиграете!"
                )
                await asyncio.sleep(0.2)
                await bot.send_message(
                    loser['user_id'],
                    f"😢 К сожалению, вы потерпели поражение в фотобатле, так как ваш соперник набрал больше реакций\n " +
                    f"🍀 Однако, вы можете принять участие в следующем фотобатле, отправив мне /battle и победить!"
                )
            except Exception as e:
                print(f"Ошибка при отправке личного сообщения: {e}")

        # Если один участник без пары
        elif len(pair) == 1:
            participant = pair[0]

            # Если участник исключён, он проигрывает
            if participant['is_kick'] == 1:
                loser_ids.append(participant['user_id'])
                # message += f"Участник №{participant['user_id']} исключен за нарушение правил\n"
                continue

            # Если участник набрал достаточно голосов, он проходит дальше
            if participant['votes'] >= min_votes_for_single:
                # message += (
                #     f"Участник №{participant['user_id']} проходит дальше с {participant['votes']} голосами\n"
                # )
                try:
                    await users_dual_win_update(participant['user_id'])
                    await bot.send_message(
                        participant['user_id'],
                        f"🎉 Поздравляем, вы успешно прошли в следующий раунд! Продолжайте в том же духе и выиграете!"
                    )
                except Exception as e:
                    print(f"Ошибка при отправке личного сообщения: {e}")
            else:
                # Если участник не набрал достаточно голосов, он проигрывает
                loser_ids.append(participant['user_id'])
                # message += (
                #     f"Участник №{participant['user_id']} выбывает с {participant['votes']} голосами\n"
                # )
                try:
                    await bot.send_message(
                        participant['user_id'],
                        f'😢 К сожалению, вы потерпели поражение в фотобатле, вы выбываете из конкурса, набрав {participant['votes']} голосов из {min_votes_for_single}.\n🍀 Однако, вы можете принять участие в следующем фотобатле, отправив мне /battle и победить!'
                    )
                except Exception as e:
                    print(f"Ошибка при отправке личного сообщения: {e}")

    # Отправляем общий результат в канал
    # result_message = await bot.send_message(channel_id, message)
    await delete_users_single()
    return [loser_ids]


async def get_super_admin_ids():
        dirname = os.path.dirname(__file__)
        filename = os.path.abspath(os.path.join(dirname, '..', 'config/config.env'))
        config = load_config(filename)
        return config.tg_bot.super_admin_ids

async def get_config():
        dirname = os.path.dirname(__file__)
        filename = os.path.abspath(os.path.join(dirname, '..', 'config/config.env'))
        config = load_config(filename)
        return config


async def announce_winner(bot: Bot, channel_id: int, winners):
    """
    Объявляет победителя баттла.
    """
    # Отправляем личное сообщение победителю
    ADMIN_ID = await select_all_admins()
    admin_ids = []
    if ADMIN_ID:
        admin_ids = [i[0] for i in ADMIN_ID]
    admin_ids += await get_super_admin_ids()
    config = await get_config()
    user_link = config.tg_bot.user_link
    for winner in winners:
        try:
            secret_code = randint(1000,9999)
            # if len(winners)==1:
            await bot.send_message(winner['user_id'], f"❤️‍🔥 Вы победили в баттле! Ваш секретный код - {secret_code}. Напишите его в поддержку вместе с номером карты и ждите приз!")
            # if len(winners)==2:
            #     await bot.send_message(winner['user_id'], f"Поздравляем! Вы сыграли в ничью в баттле с другим участником! Ваш секретный код {secret_code}. Обратитесь в поддержку за получением приза")
        except Exception as e:
            logging.error(f"Failed to send congratulation message to winner (ID: {winner['user_id']}): {e}")
            # Отправляем сообщение администратору о проблеме
            try:
                error_message = (
                    f"⚠️ Не удалось отправить поздравление победителю:\n"
                    f"ID: {winner['user_id']}\n"
                    f"Ошибка: {str(e)}"
                )
                
                for admin_id in admin_ids:
                    await bot.send_message(admin_id, error_message)
            except Exception as admin_error:
                logging.error(f"Failed to notify admin about winner message error: {admin_error}")
    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, f'Секретный код победителя: {secret_code}')
        except Exception as admin_error:
            logging.error(f"Failed to notify admin with ID = {admin_id} about winner message error: {admin_error}")
    if len(winners)==1:
        winner = winners[0]
        media = [
        InputMediaPhoto(media=winner['photo_id'], caption=f"🥇Поздравляем победителя!🥇\n\n🏆 Можешь забрать свой приз, написав нам <a href='{user_link}'>сюда</a>🏆\n\n🧸 Проигравшим не отчаиваться, ведь новый день - новые возможности 🧸\n\n💛 Следующий батл начнется завтра в то же время, отправляй заявку! 💛", parse_mode="HTML")
    ]
        
    if len(winners)==2:
        winner1 = winners[0]
        winner2 = winners[1]
        media = [
        InputMediaPhoto(media=winner1['photo_id'], caption=f"🥇Поздравляем победителей!🥇\n\n🏆 Можете забрать свой приз, написав нам <a href='{user_link}'>сюда</a>\n\n 🏆🧸 Проигравшим не отчаиваться, ведь новый день - новые возможности 🧸\n\n💛 Следующий батл начнется завтра в то же время, отправляй заявку! 💛", parse_mode="HTML"),
        
        InputMediaPhoto(media=winner2['photo_id'], caption=f"")
    ]
    winner_message = await bot.send_media_group(channel_id, media)
    return [msg.message_id for msg in winner_message]

async def delete_previous_messages(bot: Bot, channel_id: int):
    """
    Удаляет предыдущие сообщения в канале.
    """
    count = 0
    message_ids = await get_message_ids()
    for msg_id in message_ids:
        try:
            await bot.delete_message(channel_id, msg_id)
        except Exception as e:
            print(f"Не удалось удалить сообщение {msg_id}: {e}")
        count+=1
        if count % 2 == 0:
            await asyncio.sleep(0.5)
    await clear_message_ids()



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
        all_participants = await get_participants() # Получаем всех участников из базы
        current_ids = {p['user_id'] for p in current_participants}  # ID текущих участников

        # Фильтруем новых участников
        new_participants = [p for p in all_participants if p['user_id'] not in current_ids]
        single_flag = 0
        if len(new_participants) % 2 == 1:
            single_flag = 1
        if single_flag:
            sin_user = new_participants[-1]
            await set_single_user(sin_user['user_id'])

        if new_participants:
            logging.info(f"Найдены новые участники: {[p['user_id'] for p in new_participants]}")

        return new_participants


async def check_is_admin(callback: CallbackQuery, bot, channel_id, user_id) -> bool:
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
    try:
        member = await bot.get_chat_member(channel_id, user_id)
        if member.status in ['creator', 'administrator']:
            return True
    except Exception as e:
        logging.error(f"Error checking admin status: {e}")
    else:
        return False


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
    admin = await get_user(0)
    if is_autowin and not admin:
        # Получает ID фото администратора
        photo_id=await select_admin_photo()
        # photo_id=photo_id[1]

        # Создает пользователя с ID 0, если он еще не создан
        try:
            await create_user(0,'user')
        except Exception as e:
            print('Не удалось создать подставного игрока: ' + e)

        # Добавляет пользователя с ID 0 в баттл с полученным ID фото
        try:
            await create_user_in_batl(0,photo_id, 'user')
        except Exception as e:
            print('Не удалось добавить подставного игрока в баттл: ' + e)
        await update_admin_battle_points()





# -------------------------------------------------------



# async def calculate_vote_increment(state: dict, opponent_votes: int = 0) -> int:
#     """
#     Рассчитывает следующее увеличение голосов с учетом прогресса и типа голосования
#     """
#     elapsed_time = (datetime.now() - state['start_time']).total_seconds()
#     progress = elapsed_time / state['round_duration']
#     is_end_phase = progress > routers.globals_var.END_PHASE_THRESHOLD
#     current_votes = state['current_votes']

#     if state['is_single']:
#         if current_votes < routers.globals_var.MIN_REQUIRED_VOTES:
#             remaining_time = state['round_duration'] - elapsed_time
#             needed_votes = routers.globals_var.MIN_REQUIRED_VOTES - current_votes
            
#             if remaining_time <= 0:
#                 return routers.globals_var.MAX_VOTE_INCREMENT
            
#             votes_per_second_needed = needed_votes / remaining_time
#             if votes_per_second_needed > 0.1:
#                 return random.randint(2, routers.globals_var.MAX_VOTE_INCREMENT)
#             return random.randint(routers.globals_var.MIN_VOTE_INCREMENT, 2)
#     else:
#         if is_end_phase:
#             return random.randint(routers.globals_var.MIN_VOTE_INCREMENT, 2)
#         elif opponent_votes > current_votes:
#             return random.randint(2, routers.globals_var.MAX_VOTE_INCREMENT)
#         return random.randint(routers.globals_var.MIN_VOTE_INCREMENT, 2)
    
async def safe_get_vote_state(message_id: int):
    """
    Безопасное получение состояния голосования
    """
    async with vote_states_locks[message_id]:
        return vote_states.get(message_id)
    
    
async def safe_update_vote_state(message_id: int, state: dict):
    """Безопасное обновление состояния голосования"""
    async with vote_states_locks[message_id]:
        vote_states[message_id] = state




async def update_vote_display(bot: Bot, channel_id: int, message_id: int, state: dict, opponent_votes: int):
    """
    Обновляет отображение голосов на кнопках
    """
    # pair_key = f"{channel_id}:{message_id}"
    # async with pair_locks[pair_key]:
    try:
        adm_votes = await get_current_votes(0) + 1 - 100000
        
        if state['admin_position'] == 'left':
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"Левый: {adm_votes}",
                    callback_data=f"vote:{state['admin_id']}:left"
                ),
                InlineKeyboardButton(
                    text=f"Правый: {opponent_votes}",
                    callback_data=f"vote:{state['opponent_id']}:right"
                )]
            ])
        else:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"Левый: {opponent_votes}",
                    callback_data=f"vote:{state['opponent_id']}:left"
                ),
                InlineKeyboardButton(
                    text=f"Правый: {adm_votes}",
                    callback_data=f"vote:{state['admin_id']}:right"
                )]
            ])
        
        await bot.edit_message_reply_markup(
            chat_id=channel_id,
            message_id=message_id,
            reply_markup=keyboard
        )
        await update_points(0)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            logging.error(f"Telegram error: {e}")
        raise
    except Exception as e:
        logging.error(f"Error updating vote display: {e}")
        raise

        
def get_current_phase(progress):
    """
    Определяет текущую фазу на основе прогресса
    progress: float от 0 до 1, представляющий процент пройденного времени
    """
    if progress < routers.globals_var.PHASE_1_END:
        return 1
    elif progress < routers.globals_var.PHASE_2_END:
        return 2
    elif progress < routers.globals_var.PHASE_3_END:
        return 3
    elif progress < routers.globals_var.PHASE_4_END:
        return 4
    elif progress < routers.globals_var.PHASE_5_END:
        return 5
    elif progress < routers.globals_var.PHASE_6_END:
        return 6
    else:
        return 7




async def check_and_update_behavior(current_time, phase_params, current_behavior):
    """Обновляет параметры отставания/опережения в рамках текущей фазы"""
    if current_behavior and current_behavior['until_time'] >= current_time:
        return current_behavior

    behavior_type = phase_params['behavior']
    
    if behavior_type == routers.globals_var.BEHAVIOR_NORMAL:
        new_behavior = {
            'type': behavior_type,
            'until_time': current_time + timedelta(seconds=routers.globals_var.BEHAVIOR_UPDATE_INTERVAL),
            'gap': 0  # или phase_params.get('allowed_difference', 0)
        }
    else:
        params = phase_params['behavior_params']
        duration = random.uniform(params['min_duration'], params['max_duration'])
        gap = random.randint(params['min_difference'], params['max_difference'])
        new_behavior = {
            'type': behavior_type,
            'until_time': current_time + timedelta(seconds=duration),
            'gap': gap
        }
    
    logging.info(f"Updated behavior: {new_behavior}")
    return new_behavior



def should_update_votes(admin_votes, opponent_votes, phase_params, behavior):
    """Определяет необходимость обновления голосов"""
    if phase_params['behavior'] == routers.globals_var.BEHAVIOR_NORMAL:
        vote_difference = abs(admin_votes - opponent_votes)
        should_update = (opponent_votes > admin_votes) or \
               (vote_difference > phase_params['allowed_difference'])
        logging.info(f"Should update votes (normal): {should_update}. Admin: {admin_votes}, Opponent: {opponent_votes}")
        return should_update

    if not behavior:
        return False

    if behavior['type'] == routers.globals_var.BEHAVIOR_LAG:
        should_update = opponent_votes > admin_votes + behavior['gap']
    elif behavior['type'] == routers.globals_var.BEHAVIOR_LEAD:
        # Обычная логика для LEAD поведения
        should_update = admin_votes <= opponent_votes + behavior['gap']
    else:
        should_update = False

    logging.info(f"Should update votes ({behavior['type']}): {should_update}. Admin: {admin_votes}, Opponent: {opponent_votes}, Gap: {behavior['gap']}")
    return should_update



async def try_update_votes(bot, channel_id, message_id, current_state, opponent_votes, new_admin_votes, current_delay):
    """Пытается обновить голоса с учетом возможных ошибок"""
    # pair_key = f"{channel_id}:{message_id}"
    attempts = 0
    while attempts < 4:  # Максимум 3 попытки
        # async with pair_locks[pair_key]:
        try:
            current_state['current_votes'] = new_admin_votes
            await safe_update_vote_state(message_id, current_state)
            # async with keyboard_update_lock:
            # async with pair_locks[pair_key]:
            await update_vote_display(bot, channel_id, message_id, current_state, opponent_votes)
            return True
            
        except TelegramBadRequest as e:
            if "Flood control exceeded" in str(e):
                current_delay *= routers.globals_var.DELAY_INCREASE_FACTOR
                await asyncio.sleep(min(current_delay, routers.globals_var.MAX_UPDATE_DELAY))
            elif "message is not modified" not in str(e):
                logging.error(f"Error updating keyboard: {e}")
                return False
        except Exception as e:
            logging.error(f"Unexpected error while updating: {str(e)}")
            current_delay *= routers.globals_var.DELAY_INCREASE_FACTOR
            await asyncio.sleep(min(current_delay, routers.globals_var.MAX_UPDATE_DELAY))
        
        attempts += 1
        
    logging.warning(f"Failed to update votes after {attempts} attempts")
    return False



async def admin_vote_monitor(bot: Bot, channel_id: int, message_id: int):
    """Основная функция мониторинга голосования"""
    # pair_key = f"{channel_id}:{message_id}"
    current_behavior = None
    last_update_time = datetime.now()
    last_behavior_check = datetime.now()
    current_delay = routers.globals_var.INITIAL_UPDATE_DELAY
    
    logging.info(f"Starting admin vote monitor for message {message_id} in channel {channel_id}")
    while True:
        try:
            current_time = datetime.now()
            if (current_time - last_update_time).total_seconds() < routers.globals_var.MIN_UPDATE_INTERVAL:
                await asyncio.sleep(routers.globals_var.MIN_UPDATE_INTERVAL)
                continue
            # эта блокировка должна работать как и в хэндлере, но когда админ монитор занимает блокировку на весь раунд то в паре с админом не обновляются голоса, поэтому админ монитор должен держать блокировку только при обновлении
            # async with pair_locks[pair_key]:
            current_state = await safe_get_vote_state(message_id)
            if not current_state or current_state['admin_id'] != 0:
                return

            elapsed_time = (current_time - current_state['start_time']).total_seconds()
            round_duration = current_state['round_duration']
            progress = elapsed_time / round_duration
            
            if progress >= routers.globals_var.FINAL_PHASE or not (await active_battle()):
                logging.info(f"Final phase reached for message {message_id}. Ending monitor.")
                break

            current_phase = get_current_phase(progress)
            phase_params = routers.globals_var.PHASE_PARAMETERS[current_phase]
            opponent_votes = await get_current_votes(current_state['opponent_id'])
            admin_votes = await get_current_votes(0)-100000
            # admin_votes = current_state['current_votes']
            
            logging.info(f"Current state - Phase: {current_phase}, Admin votes: {admin_votes}, Opponent votes: {opponent_votes}")
            
            # Обновление параметров поведения
            if (current_time - last_behavior_check).total_seconds() >= routers.globals_var.BEHAVIOR_UPDATE_INTERVAL:
                current_behavior = await check_and_update_behavior(
                    current_time, phase_params, current_behavior
                )
                last_behavior_check = current_time

            if should_update_votes(admin_votes, opponent_votes, phase_params, current_behavior):
                logging.info(f"Attempting to update votes for message {message_id}")
                success = await try_update_votes(
                    bot, channel_id, message_id, current_state,
                    opponent_votes, admin_votes, current_delay
                )
                
                if success:
                    last_update_time = current_time
                    await asyncio.sleep(random.uniform(*phase_params['step_delays']))
            
            await asyncio.sleep(random.uniform(*phase_params['update_delays']))

        except Exception as e:
            logging.error(f"Error in admin monitor for message {message_id}: {e}", exc_info=True)
            await asyncio.sleep(routers.globals_var.ERROR_RETRY_DELAY)







async def can_process_click(user_id: int, message_id: int) -> bool:
    """
    Проверяет, можно ли обработать клик пользователя
    """
    current_time = datetime.now()
    user_key = f"{user_id}:{message_id}"
    button_key = f"button:{message_id}"
    
    # Сброс счетчика кликов для кнопки, если прошел интервал сброса
    if (current_time - click_reset_times[button_key]).total_seconds() >= routers.globals_var.RESET_INTERVAL:
        click_counters[button_key] = 0
        click_reset_times[button_key] = current_time
    
    # Проверка общего количества кликов на кнопку
    if click_counters[button_key] >= routers.globals_var.MAX_CLICKS_PER_INTERVAL:
        return False
        
    # Проверка времени с последнего клика для конкретного пользователя
    time_since_last_click = (current_time - user_last_click[user_key]).total_seconds()
    if time_since_last_click < routers.globals_var.CLICK_COOLDOWN:
        return False
        
    # Увеличение счетчика кликов для кнопки
    click_counters[button_key] += 1
    # Обновление времени последнего клика для пользователя
    user_last_click[user_key] = current_time
    return True





@channel_router.callback_query(F.data.startswith("vote:"))
async def process_vote(callback: CallbackQuery):
    """
    Обработчик голосования с мгновенной обработкой клика
    """
    try:
        if battle_lock.locked():
            await callback.answer("Пожалуйста, подождите пока выложатся все участники прежде чем голосовать!", show_alert=True)
            return
        channel_id = callback.message.chat.id
        message_id = callback.message.message_id
        user_id = callback.from_user.id
        pair_key = f"{channel_id}:{message_id}"

        is_admin = await check_is_admin(callback, _bot, channel_id, user_id)
        
        if not await can_process_click(user_id, message_id):
            print('can_process_click')
            return callback.answer("Пожалуйста, попробуйте проголосовать через минуту, телеграмм не позволяет слишком быстро менять количество голосов.",show_alert=True)
        if not is_admin:
            if not await check_subscription(user_id):
                await callback.answer('Для голосования необходимо подписаться на канал!',show_alert=True)
                return
            if message_id in user_clicks and user_id in user_clicks[message_id]:
                await callback.answer('Вы уже голосовали!', show_alert=True)
                return

        _, vote_user_id, position = callback.data.split(":")
        vote_user_id = int(vote_user_id)
        # if not pair_locks[pair_key].locked():
        # async with pair_locks[pair_key]: 
            # Защищаем критическую секцию
        current_state = await safe_get_vote_state(message_id)
        if not current_state:
            return
        # Получаем текущие значения голосов
        current_markup = callback.message.reply_markup
        current_buttons = current_markup.inline_keyboard[0]
        
        # Быстрое обновление для клика пользователя
        if position == "middle":
            current_votes = int(current_buttons[0].text.split(": ")[1])
            new_votes = current_votes + 1
            
            new_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"Голосов сейчас: {new_votes}",
                    callback_data=f"vote:{vote_user_id}:middle"
                )]
            ])
            
            current_state['current_votes'] = new_votes
            await safe_update_vote_state(message_id, current_state)
            await callback.message.edit_reply_markup(reply_markup=new_keyboard)
            
        else:
            left_votes = int(current_buttons[0].text.split(": ")[1])
            right_votes = int(current_buttons[1].text.split(": ")[1])
            if current_state['admin_id'] != 0:
                print('in current_state["admin_id"] != 0')
                if position == "left":
                    left_votes += 1
                    # if vote_user_id == current_state['admin_id']:
                    current_state['current_votes'] = left_votes
                    new_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text=f"Левый: {left_votes}",
                            callback_data=f"vote:{vote_user_id}:left"
                        ),
                        InlineKeyboardButton(
                            text=f"Правый: {right_votes}",
                            callback_data=f"vote:{current_state['opponent_id']}:right"
                        )]
                    ])
                else:
                    right_votes += 1
                    new_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text=f"Левый: {left_votes}",
                            callback_data=f"vote:{current_state['admin_id']}:left"
                        ),
                        InlineKeyboardButton(
                            text=f"Правый: {right_votes}",
                            callback_data=f"vote:{vote_user_id}:right"
                        )]
                    ])
            else:
                adm_pos = current_state["admin_position"]
                if position == "left":
                    left_votes += 1
                    current_state['current_votes'] = left_votes
                    if adm_pos == "left":
                        new_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(
                                text=f"Левый: {left_votes}",
                                callback_data=f"vote:{vote_user_id}:left"
                            ),
                            InlineKeyboardButton(
                                text=f"Правый: {right_votes}",
                                callback_data=f"vote:{current_state['opponent_id']}:right"
                            )]
                        ])
                    else:
                        new_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(
                                text=f"Левый: {left_votes}",
                                callback_data=f"vote:{vote_user_id}:left"
                            ),
                            InlineKeyboardButton(
                                text=f"Правый: {right_votes}",
                                callback_data=f"vote:{current_state['admin_id']}:right"
                            )]
                        ])
                else:
                    right_votes += 1
                    if adm_pos == "right":
                        new_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(
                                text=f"Левый: {left_votes}",
                                callback_data=f"vote:{current_state['opponent_id']}:left"
                            ),
                            InlineKeyboardButton(
                                text=f"Правый: {right_votes}",
                                callback_data=f"vote:{vote_user_id}:right"
                            )]
                        ])
                    else:
                        new_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(
                                text=f"Левый: {left_votes}",
                                callback_data=f"vote:{current_state['admin_id']}:left"
                            ),
                            InlineKeyboardButton(
                                text=f"Правый: {right_votes}",
                                callback_data=f"vote:{vote_user_id}:right"
                            )]
                        ])
            await safe_update_vote_state(message_id, current_state)
            await callback.message.edit_reply_markup(reply_markup=new_keyboard)

            # Отмечаем голос пользователя и обновляем базу данных
            if not is_admin:
                if message_id not in user_clicks:
                    user_clicks[message_id] = set()
                us = await get_user(user_id)
                if us and us[5]!=0:
                    add_voic = us[5]
                    new_add_voic=add_voic-1
                    await edit_user(us[0],'additional_voices',new_add_voic)
                else:
                    user_clicks[message_id].add(user_id)
            try:
                await callback.answer('Ваш голос учтен! ✅\n\n(При отписке от канала - голос пропадает)', show_alert=True)
            except Exception as cb_error:
                logging.error(f"Error sending callback answer: {cb_error}")
            asyncio.create_task(update_points(vote_user_id))

            # Запускаем монитор админа в отдельном таске, если нужно
            if (current_state['admin_id'] == 0):
                admin_votes = adm_votes = await get_current_votes(0) - 100000
                opponent_votes = (right_votes if current_state['admin_position'] == 'left' 
                                else left_votes)
                logging.info(f"Admin: {admin_votes} , Opponent: {opponent_votes}")
                if opponent_votes >= admin_votes:
                    # monitor_task = asyncio.create_task(
                    #     admin_vote_monitor(callback.bot, channel_id, message_id)
                    # )
                    
                    # Проверяем, не запущен ли уже монитор для этого сообщения
                    if not hasattr(callback.bot, 'monitor_tasks'):
                        callback.bot.monitor_tasks = set()
                    
                    # Проверяем, нет ли уже активного таска для этого сообщения
                    existing_task = next((task for task in callback.bot.monitor_tasks 
                                        if task.get_name() == f"admin_monitor_{channel_id}_{message_id}"), None)
                    
                    if existing_task is None or existing_task.done():
                        monitor_task = asyncio.create_task(
                            admin_vote_monitor(callback.bot, channel_id, message_id),
                            name=f"admin_monitor_{channel_id}_{message_id}"
                        )
                        
                        callback.bot.monitor_tasks.add(monitor_task)
                        monitor_task.add_done_callback(
                            lambda t: callback.bot.monitor_tasks.remove(t) 
                            if t in callback.bot.monitor_tasks else None
                        )

    except Exception as e:
        logging.error(f"Error processing vote: {e}")
        
        

KEYWORDS = ['auction', 'sale', 'bid']

moscow_tz = pytz.timezone('Europe/Moscow')

@channel_router.channel_post()
async def handle_channel_post(message: Message):
    if any(keyword.lower() in message.text.lower() for keyword in KEYWORDS):
        moscow_time = datetime.now(moscow_tz)
        current_date = moscow_time.strftime('%Y-%m-%d')
        current_time = moscow_time.strftime('%H:%M:%S')
        
        await save_message(message.text, current_date, current_time)

