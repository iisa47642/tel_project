# tasks/task_handlers.py
from datetime import datetime, time, timedelta
import logging
import os
from random import randint
from aiogram import Bot
from typing import Optional
import asyncio
from math import log
import pytz

from routers.channel_router import make_some_magic, send_battle_pairs, end_round, announce_winner, delete_previous_messages, get_new_participants
from database.db import clear_users_in_batl, create_user_in_batl, delete_users_add_voices, delete_users_in_buffer, get_participants, get_users_in_buffer, remove_losers, save_message_ids, delete_users_in_batl, select_admin_photo, select_all_admins, select_battle_settings, delete_users_points, swap_user_position, swap_user_position_first, update_admin_battle_points, update_admin_photo_in_battle, update_points,users_plays_buttle_update,users_buttle_win_update

from config.config import load_config
from routers.channel_router import send_battle_pairs, end_round, announce_winner, delete_previous_messages
from database.db import get_participants, remove_losers, save_message_ids, delete_users_in_batl,get_all_users
from routers.globals_var import reset_vote_states
from locks import battle_lock

class TaskManager:
    def __init__(self):
        self._bot: Optional[Bot] = None
        self.channel_id: int = self.get_channel_id()
        self.round_duration: int = None #15
        self.break_duration: int = None #30
        self.min_votes_for_single: int = None  # Минимум голосов для одиночного участника
        self.notification_task = None
        self.battle_task = None
        self.battle_active = False
        self.first_round_active = False
        self.current_round_start = None
        self.next_battle_start = None
        self.timezone = pytz.timezone('Europe/Moscow')
        self.DEFAULT_BATTLE_TIME = None
        self.prize = None

    async def initialize(self):
    # """Асинхронная инициализация настроек"""
        BATTLE_SETTINGS = await select_battle_settings()
        hours = BATTLE_SETTINGS[4] // 3600
        minutes = (BATTLE_SETTINGS[4] % 3600) // 60
        self.DEFAULT_BATTLE_TIME = time(hour=int(hours), minute=int(minutes))
        self.round_duration = BATTLE_SETTINGS[0]//60
        self.break_duration = BATTLE_SETTINGS[3]//60
        self.min_votes_for_single = BATTLE_SETTINGS[2]
        self.prize = BATTLE_SETTINGS[1]
    @property
    def bot(self) -> Bot:
        return self._bot

    @bot.setter
    def bot(self, bot: Bot):
        self._bot = bot


    async def get_current_mode(self) -> int:
        """
        Определение текущего режима работы бота
        Returns:
            1 - нет активного баттла
            2 - период донабора (с начала первого раунда до 30 минут до его конца)
            3 - активный баттл
        """
        TIMEZONE = pytz.timezone('Europe/Moscow')
        now = datetime.now(TIMEZONE)

        # Если баттл активен
        if self.battle_active:
            # if self.first_round_active and self.current_round_start:
                # Период донабора: от начала раунда до 30 минут до его конца
                # round_end = self.current_round_start + timedelta(minutes=self.round_duration)
                # donabor_end = round_end - timedelta(seconds=30)
                # donabor_end = round_end - timedelta(minutes=30)
                # if now < donabor_end:
                #     return 2
            return 2

        # Если баттл не активен - режим 1
        return 1

    async def get_config(self):
        dirname = os.path.dirname(__file__)
        filename = os.path.abspath(os.path.join(dirname, '..', 'config/config.env'))
        config = load_config(filename)
        return config
    
    async def notification_before_battle(self):
        last_notification_battle_time = None  # Для отслеживания последнего уведомления

        while True:
            try:
                TIMEZONE = pytz.timezone('Europe/Moscow')
                now = datetime.now(TIMEZONE)

                battle_time = await self.get_next_battle_time()

                # Убедимся, что battle_time имеет информацию о временной зоне
                if battle_time.tzinfo is None:
                    battle_time = TIMEZONE.localize(battle_time)

                # Вычисляем разницу во времени
                time_diff = battle_time - now
                minutes_until_battle = int(time_diff.total_seconds() / 60)
                hours_until_battle = minutes_until_battle // 60
                remaining_minutes = minutes_until_battle % 60

                notification_time = battle_time - timedelta(hours=1)
                
                # Добавим логирование для отладки
                logging.info(f"Current time: {now}")
                logging.info(f"Battle time: {battle_time}")
                logging.info(f"Time until battle: {hours_until_battle}h {remaining_minutes}m")
                
                wait_seconds = (notification_time - now).total_seconds()
                logging.info(f"Wait seconds: {wait_seconds}")

                # Проверяем, нужно ли отправлять уведомление
                should_notify = (
                    # Стандартное уведомление за час или уведомление о перепланировании
                    minutes_until_battle > 0 and 
                    minutes_until_battle <= 60 and 
                    last_notification_battle_time != battle_time
                )

                if wait_seconds > 0 and not should_notify:
                    # Ждём 10 секунд и проверяем время снова
                    sleep_interval = min(wait_seconds, 10)  # Проверяем каждые 10 секунд
                    logging.info(f"Sleeping for {sleep_interval} seconds")
                    await asyncio.sleep(sleep_interval)
                    continue  # После ожидания начинаем проверку заново

                if self.notification_task and self.notification_task.cancelled():
                    break

                if should_notify:
                    # Формируем текст уведомления
                    if hours_until_battle > 0:
                        time_text = f"{hours_until_battle} ч {remaining_minutes} мин"
                    else:
                        time_text = f"{remaining_minutes} мин"

                    config = await self.get_config()
                    bot_link = config.tg_bot.bot_link
                    
                    channel_message = (
                        f"🔥 Принимаю последние фото, кидать сюда: <a href='{bot_link}'>cсылка</a>\n\n"
                        f"Баттл начнется через {time_text} (в {battle_time.strftime('%H:%M')})!"
                    )

                    user_message = (
                        f"⚠️ Внимание! Баттл начнется через {time_text} "
                        f"(в {battle_time.strftime('%H:%M')})!"
                    )

                    notif_mes = await self.bot.send_message(
                        self.channel_id,
                        channel_message,
                        parse_mode='HTML'
                    )
                    await save_message_ids([notif_mes.message_id])
                    users = await get_all_users()
                    users_id = [i[0] for i in users]
                    for id_u in users_id:
                        try:
                            await self.bot.send_message(id_u, user_message)
                        except Exception as e:
                            logging.error(f'Не удалось отправить сообщение пользователю {id_u}: {str(e)}')
                    
                    logging.info("Notification sent successfully")
                    last_notification_battle_time = battle_time  # Обновляем время последнего уведомления

                # Ждем немного перед следующей итерацией
                await asyncio.sleep(10)

            except asyncio.CancelledError:
                logging.info("Notification task was cancelled")
                break
            except Exception as e:
                logging.error(f"Error in notification task: {e}", exc_info=True)
                await asyncio.sleep(60)


    async def start_notification_task(self):
        try:
            if self.notification_task is None or self.notification_task.done():
                self.notification_task = asyncio.create_task(self.notification_before_battle())
                logging.info("Notification task started")
            else:
                logging.info("Notification task is already running")
                
        except Exception as e:
            logging.error(f"Error starting notification task: {e}", exc_info=True)

    async def stop_notification_task(self):
        try:
            if self.notification_task and not self.notification_task.done():
                self.notification_task.cancel()
                try:
                    await self.notification_task
                except asyncio.CancelledError:
                    pass
                self.notification_task = None
                logging.info("Notification task stopped")
            else:
                logging.info("Notification task is not running")
        except Exception as e:
            logging.error(f"Error stopping notification task: {e}", exc_info=True)

    def get_channel_id(self):
        dirname = os.path.dirname(__file__)
        filename = os.path.abspath(os.path.join(dirname, '..', 'config/config.env'))
        config = load_config(filename)
        return config.tg_bot.channel_id

    def get_super_admin_ids(self):
        dirname = os.path.dirname(__file__)
        filename = os.path.abspath(os.path.join(dirname, '..', 'config/config.env'))
        config = load_config(filename)
        return config.tg_bot.super_admin_ids


    async def start_battle(self):
        await reset_vote_states()
        await self.initialize()
        users = await get_all_users()
        users_id = [i[0] for i in users]
        config = await self.get_config()
        channel_link = config.tg_bot.channel_link
        for id_u in users_id:
            try:
                await self.bot.send_message(
                    id_u,
                    f"⚠️ Внимание! Баттл начался! <a href='{channel_link}'>Канал</a>",
                    parse_mode='HTML'
                )
            except Exception as e:
                logging.error(f'Не удалось отправить сообщение пользователю {id_u}: {str(e)}')
                continue
        self.battle_active = True
        self.first_round_active = True
        round_number = 1
        TIMEZONE = pytz.timezone('Europe/Moscow')
        # время начала баттла
        self.current_round_start = datetime.now(TIMEZONE)

        while self.battle_active:
            # Проверяем отмену в начале каждой итерации
            if not self.battle_active:
                break
            await swap_user_position()
            now = datetime.now(TIMEZONE)
            participants = await get_participants()
            # Если баттл был принудительно завершен администратором
            # if not self.battle_active:
            #     break
            
            if round_number == 1:
                await users_plays_buttle_update()
            
            if len(participants) == 1:
                await self.end_battle([participants[0]])
                break
            elif len(participants) == 2 and participants[0]['points'] == participants[1]['points']:
                await self.end_battle([participants[0], participants[1]])
                break
            if not self.battle_active:
                break
            if not self.battle_active:
                break
            await delete_previous_messages(self.bot, self.channel_id)
            await delete_users_points()
            await update_admin_battle_points()
            # settings = await select_battle_settings()
            
            # if not self.battle_active:
            #     break
            if 2 < len(participants)<=4:
                round_txt = f"Начинается полуфинал!"
                # start_message = await self.bot.send_message(
                # self.channel_id,
                # round_txt
            # )
            elif len(participants)==2:
                round_txt = f"Начинается финал!"
                # start_message = await self.bot.send_message(
                # self.channel_id,
                # round_txt
            # )
            else:
                round_txt = f"Начинается раунд {round_number}!"
                # start_message = await self.bot.send_message(
                # self.channel_id,
                # round_txt
            # )
            # if not self.battle_active:  # Проверка после отправки сообщения о раунде
            #     await delete_previous_messages(self.bot, self.channel_id)
            #     break
            if not self.battle_active:
                break
            # await save_message_ids([start_message.message_id])
            current_start = datetime.now(TIMEZONE)
            async with battle_lock:
                message_ids = await send_battle_pairs(self.bot, self.channel_id, participants,self.prize, round_txt,self.round_duration, self.min_votes_for_single, current_start)
            await save_message_ids(message_ids)
            if not self.battle_active:
                break
            # Определяем продолжительность раунда
            # if now.hour < 10 and now.hour >= 0:
            if now.hour < 10 and now.hour >= 1:  # Если раунд начался после полуночи
                today = now.date()
                round_end_time = self.timezone.localize(datetime.combine(today, time(hour=10)))
                wait_time = (round_end_time - now).total_seconds()
            else:
                wait_time = self.round_duration * 60  # Переводим минуты в секунды

            # Основное ожидание заверешния раунда с динамическим добавлением участников
            start_time = datetime.now(TIMEZONE)
            if not self.battle_active:
                break
            end_time = start_time + timedelta(seconds=wait_time)

            while datetime.now(TIMEZONE) < end_time:
                try:
                    if not self.battle_active:
                        return
                    # Проверяем участников каждые 10 секунд
                    await asyncio.sleep(10)

                    new_participants = await get_new_participants(participants)
                    if new_participants:
                        logging.info(f"Adding {len(new_participants)} new participants to the battle")
                        participants.extend(new_participants)
                        async with battle_lock:
                            new_message_ids = await send_battle_pairs(self.bot, self.channel_id, new_participants,self.prize, round_txt,self.round_duration,self.min_votes_for_single, current_start)
                        await save_message_ids(new_message_ids)
                except Exception as e:
                    logging.error(f"Error while checking new participants: {e}")

            end_values = await end_round(self.bot, self.channel_id, self.min_votes_for_single)
            # end_message_ids = end_values[0]
            # await save_message_ids(end_message_ids)
            losers = end_values[0]

            await remove_losers(losers)
            round_number += 1
            self.min_votes_for_single += 5
            self.first_round_active = False

            await asyncio.sleep(self.break_duration * 60)

    async def end_battle(self, winners: list):
        # Удаляем все предыдущие сообщения
        await delete_previous_messages(self.bot, self.channel_id)
        for winner in winners:
            await users_buttle_win_update(winner['user_id'])
        # Объявляем победителя
        final_message_ids = await announce_winner(self.bot, self.channel_id, winners)
        await save_message_ids(final_message_ids)
        await delete_users_add_voices()
        await clear_users_in_batl()
        await swap_user_position_first()
        photo_admin_id = await select_admin_photo()
        if photo_admin_id:
            await update_admin_photo_in_battle(photo_admin_id)

        BATTLE_SETTINGS = await select_battle_settings()
        self.min_votes_for_single = BATTLE_SETTINGS[2]

        TIMEZONE = pytz.timezone('Europe/Moscow')
        now = datetime.now(TIMEZONE)
        battle_duration = now - self.current_round_start

        if battle_duration > timedelta(days=1):
            self.next_battle_start = TIMEZONE.localize(now + timedelta(hours=2))

        else:
            next_day = now.date() + timedelta(days=1)
            self.next_battle_start = TIMEZONE.localize(
                datetime.combine(next_day, self.DEFAULT_BATTLE_TIME)
            )

            # if now.hour >= 0 and now.hour < 10:
            #     self.next_battle_start = TIMEZONE.localize(
            #         datetime.combine(next_day, time(hour=10, minute=0))
            #     )
            if now.time() <= self.DEFAULT_BATTLE_TIME:
                current_day = now.date()  # берем текущую дату
                self.next_battle_start = TIMEZONE.localize(
                    datetime.combine(current_day, self.DEFAULT_BATTLE_TIME)
                )
        config = await self.get_config()
        bot_link = config.tg_bot.bot_link
        if self.next_battle_start.date() == now.date():
            message_text = f"👑 Следующий баттл (сегодня в {self.next_battle_start.strftime('%H:%M')})! Фото сюда: <a href='{bot_link}'>cсылка</a>"
        else:
            message_text = f"👑 Следующий баттл (завтра в {self.next_battle_start.strftime('%H:%M')})! Фото сюда: <a href='{bot_link}'>cсылка</a>"

        end_ms = await self.bot.send_message(
            self.channel_id,
            message_text,
            parse_mode='HTML'
        )
        await save_message_ids([end_ms.message_id])
        try:
            users_buffer = await get_users_in_buffer()
            for user in users_buffer:
                await create_user_in_batl(user['user_id'],user['photo_id'], 'user')
                await delete_users_in_buffer()
        except Exception as e:
            print('Не удалось перенести участника из буфера в баттл ' + str(e))
        self.battle_active = False
        self.first_round_active = False


    async def get_battle_status(self) -> str:
        """Метод для получения текущего статуса баттла"""
        TIMEZONE = pytz.timezone('Europe/Moscow')
        now = datetime.now(TIMEZONE)

        status = []
        status.append(f"Текущее время: {now.strftime('%H:%M')}")
        status.append(f"Баттл активен: {self.battle_active}")
        status.append(f"Первый раунд активен: {self.first_round_active}")

        if self.next_battle_start:
            status.append(f"Следующий баттл запланирован на: {self.next_battle_start.strftime('%H:%M')}")

        if self.battle_active:
            if self.first_round_active:
                now = datetime.now(TIMEZONE)
                time_passed = (now - self.current_round_start).total_seconds()
                time_remaining = (self.round_duration * 60) - time_passed
                round_end = now + timedelta(seconds=time_remaining)
                status.append(f"Текущий раунд закончится в: {round_end.strftime('%H:%M')}")


        return "\n".join(status)

    async def get_next_battle_time(self) -> datetime:
        """Метод для получения времени следующего баттла"""
        try:
            if not self.DEFAULT_BATTLE_TIME:
                logging.warning("DEFAULT_BATTLE_TIME not set, initializing...")
                await self.initialize()
            # Получаем текущие настройки из БД
            
            current_settings = await select_battle_settings()
            current_hours = current_settings[4] // 3600
            current_minutes = (current_settings[4] % 3600) // 60
            current_battle_time = time(hour=int(current_hours), minute=int(current_minutes))
            
            if not self.next_battle_start or current_battle_time != self.DEFAULT_BATTLE_TIME:
                now = datetime.now(self.timezone)
                print(f"now in get {now}")
                
                # Обновляем DEFAULT_BATTLE_TIME на новое значение
                self.DEFAULT_BATTLE_TIME = current_battle_time
                # Создаем время следующего баттла
                battle_time = datetime.combine(
                    now.date(),
                    self.DEFAULT_BATTLE_TIME
                )
                # Добавляем информацию о временной зоне
                battle_time = self.timezone.localize(battle_time)
                # Если время уже прошло, переносим на следующий день
                if now >= battle_time:
                    battle_time += timedelta(days=1)
                # Проверяем ночное время
                # if battle_time.hour >= 0 and battle_time.hour < 10:
                #     next_day = battle_time.date()
                #     # if battle_time.hour >= 3:
                #         # 22 быть должно
                #     next_day += timedelta(days=1)
                #     battle_time = self.timezone.localize(
                #         datetime.combine(next_day, time(hour=10, minute=0))
                #     )
                # if battle_time.hour >= 0 and battle_time.hour < 10:
                #     current_day = battle_time.date()  # берем текущую дату
                #     battle_time = self.timezone.localize(
                #         datetime.combine(current_day, time(hour=10, minute=0))
                #     )


                self.next_battle_start = battle_time
                logging.info(f"Next battle time set to: {battle_time}")

            return self.next_battle_start
        except Exception as e:
            logging.error(f"Error in get_next_battle_time: {e}", exc_info=True)
            raise




    
    
    
    
    
    
    
