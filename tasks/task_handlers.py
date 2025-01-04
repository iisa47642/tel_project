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
from database.db import get_participants, remove_losers, save_message_ids, delete_users_in_batl, select_all_admins, select_battle_settings, delete_users_points, update_admin_battle_points, update_points,users_plays_buttle_update,users_buttle_win_update

from config.config import load_config
from routers.channel_router import send_battle_pairs, end_round, announce_winner, delete_previous_messages
from database.db import get_participants, remove_losers, save_message_ids, delete_users_in_batl

class TaskManager:
    def __init__(self):
        self._bot: Optional[Bot] = None
        self.channel_id: int = self.get_channel_id()
        self.round_duration: int = None #15
        self.break_duration: int = None #30
        self.min_votes_for_single: int = None  # Минимум голосов для одиночного участника
        self.notification_task = None
        self.battle_task = None
        self.mode_2_duration = timedelta(hours=1, minutes=30)  # Длительность режима 2
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
            if self.first_round_active and self.current_round_start:
                # Период донабора: от начала раунда до 30 минут до его конца
                round_end = self.current_round_start + timedelta(minutes=self.round_duration)
                donabor_end = round_end - timedelta(seconds=30)
                # donabor_end = round_end - timedelta(minutes=30)
                if now < donabor_end:
                    return 2
            return 3

        # Если баттл не активен - режим 1
        return 1

    async def notification_before_battle(self):
        while True:
            try:
                TIMEZONE = pytz.timezone('Europe/Moscow')
                now = datetime.now(TIMEZONE)

                if self.next_battle_start:
                    battle_time = self.next_battle_start
                else:
                    BATTLE_SETTINGS = await select_battle_settings()
                    BATTLE_START_SECONDS = BATTLE_SETTINGS[4]
                    hours = BATTLE_START_SECONDS // 3600
                    minutes = (BATTLE_START_SECONDS % 3600) // 60
                    battle_time = datetime.combine(
                        now.date(),
                        time(hour=int(hours), minute=int(minutes))
                    )
                    if now.time() >= time(hour=int(hours), minute=int(minutes)):
                        battle_time += timedelta(days=1)

                notification_time = battle_time - timedelta(hours=1)
                wait_seconds = (notification_time - now).total_seconds()

                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds)
                    await self.bot.send_message(
                        self.channel_id,
                        f"Внимание! Баттл начнется через 1 час (в {battle_time.strftime('%H:%M')})!"
                    )

                await asyncio.sleep(10)

            except Exception as e:
                logging.error(f"Error in notification task: {e}")
                await asyncio.sleep(60)

    async def start_notification_task(self):
        if self.notification_task is None or self.notification_task.done():
            self.notification_task = asyncio.create_task(self.notification_before_battle())
            logging.info("Notification task started")
        else:
            logging.info("Notification task is already running")

    async def stop_notification_task(self):
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
        self.battle_active = True
        self.first_round_active = True
        round_number = 1
        TIMEZONE = pytz.timezone('Europe/Moscow')
        # время начала баттла
        self.current_round_start = datetime.now(TIMEZONE)

        while self.battle_active:
            now = datetime.now(TIMEZONE)

            participants = await get_participants()
            if round_number == 1:
                await users_plays_buttle_update()
            # number_of_rounds = int(log(len(participants),2))
            # if len(participants) == 0:
            #     self._bot.send_message(
            #         self.channel_id,
            #     f"Баттл был принудительно завершен администратором")
            #     break
            
            if len(participants) == 1:
                await self.end_battle([participants[0]])
                break
            elif len(participants) == 2 and participants[0]['points'] == participants[1]['points']:
                await self.end_battle([participants[0], participants[1]])
                break

            await delete_previous_messages(self.bot, self.channel_id)
            await delete_users_points()
            await update_admin_battle_points()
            settings = await select_battle_settings()
            if 2 < len(participants)<=4:
                start_message = await self.bot.send_message(
                self.channel_id,
                f"Начинается полуфинал!"
            )
            elif len(participants)==2:
                start_message = await self.bot.send_message(
                self.channel_id,
                f"Начинается финал!"
            )
            else:
                start_message = await self.bot.send_message(
                self.channel_id,
                f"Начинается раунд {round_number}!"
            )
            await save_message_ids([start_message.message_id])
            
            message_ids = await send_battle_pairs(self.bot, self.channel_id, participants)
            await save_message_ids(message_ids)

            # Определяем продолжительность раунда
            # if now.hour < 10 and now.hour >= 0:
            if now.hour < 10 and now.hour >= 9:  # Если раунд начался после полуночи
                tomorrow = now.date() + timedelta(days=1)
                round_end_time = self.timezone.localize(datetime.combine(tomorrow, time(hour=10)))
                wait_time = (round_end_time - now).total_seconds()
            else:
                wait_time = self.round_duration * 60  # Переводим минуты в секунды

            # Основное ожидание заверешния раунда с динамическим добавлением участников
            start_time = datetime.now(TIMEZONE)
            end_time = start_time + timedelta(seconds=wait_time)

            while datetime.now(TIMEZONE) < end_time:
                try:
                    # Проверяем участников каждые 10 секунд
                    await asyncio.sleep(10)

                    new_participants = await get_new_participants(participants)
                    if new_participants:
                        logging.info(f"Adding {len(new_participants)} new participants to the battle")
                        participants.extend(new_participants)
                        new_message_ids = await send_battle_pairs(self.bot, self.channel_id, new_participants)
                        await save_message_ids(new_message_ids)
                except Exception as e:
                    logging.error(f"Error while checking new participants: {e}")

            end_values = await end_round(self.bot, self.channel_id, self.min_votes_for_single)
            end_message_ids = end_values[0]
            await save_message_ids(end_message_ids)
            losers = end_values[1]

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
        await delete_users_in_batl()
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

            if now.hour >= 9 and now.hour < 10:
                self.next_battle_start = TIMEZONE.localize(
                    datetime.combine(next_day, time(hour=10, minute=0))
                )
        await self.bot.send_message(
            self.channel_id,
            f"Следующий баттл начнется в {self.next_battle_start.strftime('%d/%m, %H:%M')}"
            )

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

            if not self.next_battle_start:
                now = datetime.now(self.timezone)
                print(f"now in get {now}")
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
                if battle_time.hour >= 9 and battle_time.hour < 10:
                    next_day = battle_time.date()
                    # if battle_time.hour >= 3:
                        # 22 быть должно
                    next_day += timedelta(days=1)
                    battle_time = self.timezone.localize(
                        datetime.combine(next_day, time(hour=10, minute=0))
                    )

                self.next_battle_start = battle_time
                logging.info(f"Next battle time set to: {battle_time}")

            return self.next_battle_start
        except Exception as e:
            logging.error(f"Error in get_next_battle_time: {e}", exc_info=True)
            raise

# опциональная функция мб иожно и вынести из класса
    # async def validate_battle_time(self, time: datetime) -> bool:
    #         """Проверка допустимости времени для баттла"""
    #         if time.hour >= 22 or time.hour < 10:
    #             return False
    #         return True





    # async def update_battle_settings(self, settings: dict):
    #         """Обновление настроек баттла"""
    #         try:
    #             self.round_duration = settings.get('round_duration', self.round_duration)
    #             self.break_duration = settings.get('break_duration', self.break_duration)
    #             self.min_votes_for_single = settings.get('min_votes', self.min_votes_for_single)
    #             logging.info(f"Battle settings updated: {settings}")
    #         except Exception as e:
    #             logging.error(f"Error updating battle settings: {e}")
    #             raise



    # async def check_and_update_battle_schedule(self):
    #     """Метод для проверки и обновления расписания баттлов"""
    #     TIMEZONE = pytz.timezone('Europe/Moscow')
    #     now = datetime.now(TIMEZONE)

    #     if self.next_battle_start:
    #         # Если следующий баттл запланирован на ночное время
    #         if self.next_battle_start.hour >= 22 or self.next_battle_start.hour < 10:
    #             next_day = now.date() + timedelta(days=1)
    #             self.next_battle_start = datetime.combine(next_day, time(hour=10))
    #             await self.bot.send_message(
    #                 self.channel_id,
    #                 f"Время следующего баттла перенесено на {self.next_battle_start.strftime('%H:%M')}"
    #             )

    # async def force_next_battle(self, new_time: datetime):
    #     """Метод для принудительного назначения времени следующего баттла"""
    #     if 22 <= new_time.hour or new_time.hour < 10:
    #         raise ValueError("Нельзя назначить баттл на ночное время (22:00-10:00)")

    #     self.next_battle_start = new_time
    #     await self.bot.send_message(
    #         self.channel_id,
    #         f"Время следующего баттла установлено на {new_time.strftime('%H:%M')}"
    #     )


# async def stop_battle(self):
    #     """Метод для принудительной остановки баттла"""
    #     self.battle_active = False
    #     self.first_round_active = False
    #     await self.bot.send_message(
    #         self.channel_id,
    #         "Баттл был принудительно остановлен администратором."
    #     )

    #     TIMEZONE = pytz.timezone('Europe/Moscow')
    #     now = datetime.now(TIMEZONE)

    #     # Если текущее время между 22:00 и 10:00, следующий баттл в 10:00
    #     if now.hour >= 22 or now.hour < 10:
    #         next_day = now.date() + timedelta(days=1)
    #         self.next_battle_start = datetime.combine(next_day, time(hour=10))
    #     else:
    #         # Иначе через 2 часа
    #         self.next_battle_start = now + timedelta(hours=2)

    #     await self.bot.send_message(
    #         self.channel_id,
    #         f"Следующий баттл начнется в {self.next_battle_start.strftime('%H:%M')}"
    #     )
    
    
    
    
    
    
    
    
