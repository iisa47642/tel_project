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

from config.config import load_config
from database.db import create_user, create_user_in_batl, delete_users_single, edit_user, get_current_votes, get_participants, get_user, select_admin_photo, select_info_message, set_single_user, update_admin_battle_points, update_points, \
    get_round_results, get_message_ids, clear_message_ids,\
    select_battle_settings, select_all_admins,users_dual_win_update
from routers.globals_var import (
    vote_states, user_clicks, pair_locks, vote_states_locks,
    user_last_click, click_counters, click_reset_times
)
import routers.globals_var
from filters.isAdmin import is_admin

_bot: Bot = None  # Placeholder for the bot instance

def setup_router(dp, bot: Bot):
    global _bot
    _bot = bot
    
    
LAG_UPDATE_INTERVAL = 180
INITIAL_UPDATE_DELAY = 1  # Начальная задержка при ошибке
MAX_UPDATE_DELAY = 5      # Максимальная задержка при повторных ошибках
DELAY_INCREASE_FACTOR = 1.5  # Множитель увеличения задержки

END_PHASE_THRESHOLD = 0.85  # Последние 15% времени считаются концом раунда
MIN_REQUIRED_VOTES = 5  # Минимальное количество голосов для прохождения
MIN_VOTE_INCREMENT = 1   # Минимальный прирост голосов
MAX_VOTE_INCREMENT = 2   # Максимальный прирост голосов
# Константы для задержек в разных фазах (в секундах)
INITIAL_PHASE_DELAYS = (60.0, 80.0)  # Большие задержки в начальной фазе
MIDDLE_PHASE_DELAYS = (40.0, 50.0)   # Средние задержки в средней фазе
FINAL_PHASE_DELAYS = (5.0, 15.0)    # Минимальные задержки в финальной фазе

# Константы для задержек при пошаговом обновлении счета
INITIAL_PHASE_STEP_DELAYS = (30, 40)
MIDDLE_PHASE_STEP_DELAYS = (20, 25)
FINAL_PHASE_STEP_DELAYS = (5.0, 15.0)


ALLOW_LAG_CHANCE = 0.4  # Вероятность разрешить отставание
MIN_LAG_DURATION = 50  # Минимальная продолжительность отставания в секундах
MAX_LAG_DURATION = 200  # Максимальная продолжительность отставания в секундах
MAX_LAG_DIFFERENCE = 8  # Максимальная разница в голосах при отставании
MIN_LAG_DIFFERENCE = 1
GUARANTEED_WIN_PHASE = 0.85  # Начало фазы гарантированной победы (85% времени раунда)
MIN_WINNING_MARGIN = 5  # Минимальный отрыв для победы

MIN_UPDATE_INTERVAL = 2.0  # Минимальный интервал между обновлениями в секундах
FLOOD_CONTROL_RESET = 10# Время сброса флуд-контроля в секундах

CLICK_COOLDOWN = 1.0  # Уменьшаем задержку между кликами до 300мс
MAX_CLICKS_PER_INTERVAL = 5  # Увеличиваем количество разрешенных кликов
RESET_INTERVAL = 5.0  # Интервал сброса счетчика кликов

INITIAL_PHASE_VOTE_DIFF = 7  # В начальной фазе допускаем разницу в 3 голоса
MIDDLE_PHASE_VOTE_DIFF = 5   # В средней фазе - в 2 голоса
FINAL_PHASE_VOTE_DIFF = 1
MAX_FINAL_PHASE_DIFF = 15
MAX_LAG_DIFFERENCE = 8  # Максимальная разница при временном отставании


channel_router = Router()


async def init_vote_state(message_id: int, admin_id: int, admin_position: str, opponent_id: int, current_start):
    """
    Инициализирует состояние голосования для сообщения с админом
    """
    ROUND_DURATION = routers.globals_var.ROUND_DURATION

    if current_start.hour < 10 and current_start.hour >= 3:  # Если время начала между 00:00 и 10:00
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
    await asyncio.sleep(8)
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

    if now.hour < 10 and now.hour >= 3:  # Если время между 23:00 и 10:00
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
                                          f'👑{round_txt}👑\n\n'+
                                          f'⏱️Итоги через {end_text}⏱️\n\n'+
                                          f"<a href='t.me/c/{str(channel_id)[4:]}/{media_message[0].message_id}'>⛓️Ссылка на голосование⛓️</a>\n\n"+
                                          f'💵Приз: {prize} ₽💵\n\n'
                                          f'{addit_msg}',
                                          reply_markup=keyboard,
                                          parse_mode="HTML")
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
    await asyncio.sleep(8)
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

    if now.hour < 10 and now.hour >= 3:
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
                                          f'👑{round_txt}👑\n\n'
                                          f'⏱️Итоги через {end_text}⏱️\n\n'
                                          f"<a href='t.me/c/{str(channel_id)[4:]}/{photo_message.message_id}'>⛓️Ссылка на голосование⛓️</a>\n\n"+
                                          f'☀️ Не хватило соперника, поэтому необходимо набрать {min_votes} реакций!\n\n'
                                          f'💵Приз: {prize} ₽💵\n\n'
                                          f'{addit_msg}',
                                          reply_markup=keyboard,
                                          parse_mode="HTML")
    

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
        await bot.send_message(admin_id, f'Секретный код победителя: {secret_code}')
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
    message_ids = await get_message_ids()
    for msg_id in message_ids:
        try:
            await bot.delete_message(channel_id, msg_id)
        except Exception as e:
            print(f"Не удалось удалить сообщение {msg_id}: {e}")
        await asyncio.sleep(8)
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

    if is_autowin:
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



async def calculate_vote_increment(state: dict, opponent_votes: int = 0) -> int:
    """
    Рассчитывает следующее увеличение голосов с учетом прогресса и типа голосования
    """
    elapsed_time = (datetime.now() - state['start_time']).total_seconds()
    progress = elapsed_time / state['round_duration']
    is_end_phase = progress > END_PHASE_THRESHOLD
    current_votes = state['current_votes']

    if state['is_single']:
        if current_votes < MIN_REQUIRED_VOTES:
            remaining_time = state['round_duration'] - elapsed_time
            needed_votes = MIN_REQUIRED_VOTES - current_votes
            
            if remaining_time <= 0:
                return MAX_VOTE_INCREMENT
            
            votes_per_second_needed = needed_votes / remaining_time
            if votes_per_second_needed > 0.1:
                return random.randint(2, MAX_VOTE_INCREMENT)
            return random.randint(MIN_VOTE_INCREMENT, 2)
    else:
        if is_end_phase:
            return random.randint(MIN_VOTE_INCREMENT, 2)
        elif opponent_votes > current_votes:
            return random.randint(2, MAX_VOTE_INCREMENT)
        return random.randint(MIN_VOTE_INCREMENT, 2)
    
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
    try:
        if state['is_single']:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"Голосов сейчас: {state['current_votes']}",
                    callback_data=f"vote:{state['admin_id']}:middle"
                )]
            ])
        else:
            if state['admin_position'] == 'left':
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=f"Левый: {state['current_votes']}",
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
                        text=f"Правый: {state['current_votes']}",
                        callback_data=f"vote:{state['admin_id']}:right"
                    )]
                ])

        await bot.edit_message_reply_markup(
            chat_id=channel_id,
            message_id=message_id,
            reply_markup=keyboard
        )
        
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            logging.error(f"Telegram error: {e}")
    except Exception as e:
        logging.error(f"Error updating vote display: {e}")

        
def get_phase_delays(progress: float) -> tuple:
    """
    Возвращает задержки в зависимости от фазы раунда
    """
    if progress < 0.3:
        return INITIAL_PHASE_DELAYS, INITIAL_PHASE_STEP_DELAYS
    elif progress < 0.7:
        return MIDDLE_PHASE_DELAYS, MIDDLE_PHASE_STEP_DELAYS
    else:
        return FINAL_PHASE_DELAYS, FINAL_PHASE_STEP_DELAYS


async def gradual_vote_update(bot: Bot, channel_id: int, message_id: int, 
                            state: dict, opponent_votes: int, 
                            target_votes: int, step_delay_range: tuple):
    """
    Постепенно обновляет количество голосов
    """
    current = state['current_votes']
    target = target_votes
    
    while current < target:
        delay = random.uniform(*step_delay_range)
        delay = max(delay, MIN_UPDATE_INTERVAL)
        await asyncio.sleep(delay)
        
        current += 1
        if current > target:
            break
            
        state['current_votes'] = current
        
        try:
            await update_vote_display(bot, channel_id, message_id, state, opponent_votes)
        except Exception as e:
            if "Flood control exceeded" in str(e):
                await asyncio.sleep(FLOOD_CONTROL_RESET)
            elif "message is not modified" not in str(e):
                logging.error(f"Error in gradual update: {e}")

async def check_and_update_lag(current_time, progress, allow_lag_until, allowed_gap, round_duration, elapsed_time):
    """Периодически обновляет параметры отставания"""
    if progress >= GUARANTEED_WIN_PHASE or elapsed_time >= round_duration:
        return allow_lag_until, allowed_gap

    # Проверяем, нужно ли обновить отставание
    #if (allow_lag_until is None or current_time >= allow_lag_until) and allowed_gap is None:  # ИЗНАЧАЛЬНОЕ УСЛОВИЕ (ПРОБЛЕМНОЕ)
    if allow_lag_until is None or current_time >= allow_lag_until:  # ИСПРАВЛЕННОЕ УСЛОВИЕ
        if random.random() < ALLOW_LAG_CHANCE:
            # Временное отставание
            lag_duration = random.uniform(MIN_LAG_DURATION, MAX_LAG_DURATION)
            max_allowed_lag_time = round_duration * GUARANTEED_WIN_PHASE - elapsed_time
            lag_duration = min(lag_duration, max_allowed_lag_time)
            if lag_duration > 0:
                allow_lag_until = current_time + timedelta(seconds=lag_duration)
                print(f'Новое временное отставание на {lag_duration} сек')
                allowed_gap = None  # Сбрасываем голосовое отставание
        else:
            # Голосовое отставание
            allowed_gap = random.randint(MIN_LAG_DIFFERENCE, MAX_LAG_DIFFERENCE)
            print(f'Новое голосовое отставание: {allowed_gap}')
            allow_lag_until = None  # Сбрасываем временное отставание

    return allow_lag_until, allowed_gap

async def admin_vote_monitor(bot: Bot, channel_id: int, message_id: int):
    pair_key = f"{channel_id}:{message_id}"
    allow_lag_until = None
    last_update_time = datetime.now()
    allowed_gap = None
    current_delay = INITIAL_UPDATE_DELAY
    print('run_admin_monitor')
    
    while True:
        try:
            current_time = datetime.now()
            if (current_time - last_update_time).total_seconds() < MIN_UPDATE_INTERVAL:
                await asyncio.sleep(MIN_UPDATE_INTERVAL)
                continue

            async with pair_locks[pair_key]:
                current_state = await safe_get_vote_state(message_id)
                if not current_state or current_state['admin_id'] != 0:
                    return

                elapsed_time = (current_time - current_state['start_time']).total_seconds()
                progress = elapsed_time / current_state['round_duration']
                
                if elapsed_time >= current_state['round_duration']:
                    break

                update_delays, step_delays = get_phase_delays(progress)
                opponent_votes = await get_current_votes(current_state['opponent_id'])
                admin_votes = current_state['current_votes']
                vote_difference = abs(admin_votes - opponent_votes)
                
                if progress < 0.3:  # Начальная фаза
                    allowed_difference = INITIAL_PHASE_VOTE_DIFF
                    current_step_delays = INITIAL_PHASE_STEP_DELAYS
                elif progress < 0.7:  # Средняя фаза
                    allowed_difference = MIDDLE_PHASE_VOTE_DIFF
                    current_step_delays = MIDDLE_PHASE_STEP_DELAYS
                else:  # Финальная фаза
                    allowed_difference = FINAL_PHASE_VOTE_DIFF
                    current_step_delays = FINAL_PHASE_STEP_DELAYS

                # Обновление параметров отставания
                if not hasattr(admin_vote_monitor, 'last_lag_update') or \
                   (current_time - getattr(admin_vote_monitor, 'last_lag_update')).total_seconds() >= LAG_UPDATE_INTERVAL:
                    allow_lag_until, allowed_gap = await check_and_update_lag(
                        current_time, progress, allow_lag_until, allowed_gap,
                        current_state['round_duration'], elapsed_time
                    )
                    admin_vote_monitor.last_lag_update = current_time

                # Определяем необходимость и размер обновления
                needs_update = False
                if progress >= GUARANTEED_WIN_PHASE:
                    random_gap = random.randint(MIN_WINNING_MARGIN, MAX_FINAL_PHASE_DIFF)
                    if opponent_votes >= admin_votes or (admin_votes - opponent_votes) < random_gap:
                        needs_update = True
                else:
                    if allow_lag_until and current_time < allow_lag_until:
                        needs_update = opponent_votes > admin_votes + MAX_LAG_DIFFERENCE
                    elif allowed_gap is not None:
                        needs_update = opponent_votes > admin_votes + allowed_gap
                    else:
                        needs_update = (opponent_votes > admin_votes) or (vote_difference > allowed_difference)
                
                print(f"Состояние: admin={admin_votes}, opponent={opponent_votes}, разница={vote_difference}, needs_update={needs_update}")
                if needs_update:
                    # Используем calculate_vote_increment для определения размера обновления
                    new_admin_votes = admin_votes + 1
                    
                    success = False
                    attempts = 0
                    while not success and attempts < 3:
                        try:
                            current_state['current_votes'] = new_admin_votes
                            await safe_update_vote_state(message_id, current_state)
                            
                            await update_vote_display(bot, channel_id, message_id, current_state, opponent_votes)
                            
                            success = True
                            current_delay = INITIAL_UPDATE_DELAY
                            last_update_time = datetime.now()
                            print(f"Успешное обновление голосов: {new_admin_votes} ")
                            
                        except TelegramBadRequest as e:
                            attempts += 1
                            if "Flood control exceeded" in str(e):
                                current_delay = min(current_delay * DELAY_INCREASE_FACTOR, MAX_UPDATE_DELAY)
                                print(f"Flood control hit, waiting {current_delay} seconds...")
                                await asyncio.sleep(current_delay)
                            elif "message is not modified" not in str(e):
                                logging.error(f"Error updating keyboard: {e}")
                                break
                        except Exception as e:
                            print(f"Unexpected error while updating: {str(e)}")
                            current_delay = min(current_delay * DELAY_INCREASE_FACTOR, MAX_UPDATE_DELAY)
                            await asyncio.sleep(current_delay)
                            attempts += 1

                    if success:
                        await asyncio.sleep(random.uniform(*current_step_delays))

                # Задержка между итерациями
                await asyncio.sleep(random.uniform(*update_delays))

        except Exception as e:
            logging.error(f"Error in admin monitor: {e}")
            await asyncio.sleep(2)








async def can_process_click(user_id: int, message_id: int) -> bool:
    """
    Проверяет, можно ли обработать клик пользователя
    """
    current_time = datetime.now()
    key = f"{user_id}:{message_id}"
    
    if (current_time - click_reset_times[key]).total_seconds() >= RESET_INTERVAL:
        click_counters[key] = 0
        click_reset_times[key] = current_time
    
    if click_counters[key] >= MAX_CLICKS_PER_INTERVAL:
        return False
        
    time_since_last_click = (current_time - user_last_click[key]).total_seconds()
    if time_since_last_click < CLICK_COOLDOWN:
        return False
        
    click_counters[key] += 1
    user_last_click[key] = current_time
    return True



@channel_router.callback_query(F.data.startswith("vote:"))
async def process_vote(callback: CallbackQuery):
    """
    Обработчик голосования с мгновенной обработкой клика
    """
    try:
        
        channel_id = callback.message.chat.id
        message_id = callback.message.message_id
        user_id = callback.from_user.id
        pair_key = f"{channel_id}:{message_id}"

        is_admin = await check_is_admin(callback, _bot, channel_id, user_id)
        
        if not is_admin:
            if not await can_process_click(user_id, message_id):
                return
            if not await check_subscription(user_id):
                await callback.answer('Для голосования необходимо подписаться на канал!',show_alert=True)
                return
            if message_id in user_clicks and user_id in user_clicks[message_id]:
                await callback.answer('Вы уже голосовали!', show_alert=True)
                return

        _, vote_user_id, position = callback.data.split(":")
        vote_user_id = int(vote_user_id)

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
            
            if position == "left":
                left_votes += 1
                if vote_user_id == current_state['admin_id']:
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
                if vote_user_id == current_state['admin_id']:
                    current_state['current_votes'] = right_votes
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
        if (not current_state['is_single'] and 
            current_state['admin_id'] == 0 and 
            vote_user_id != current_state['admin_id']):
            
            admin_votes = current_state['current_votes']
            opponent_votes = (right_votes if current_state['admin_position'] == 'left' 
                            else left_votes)

            if opponent_votes > admin_votes:
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

