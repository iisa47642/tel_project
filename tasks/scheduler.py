import asyncio
import json
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
import pytz
from typing import Optional
from datetime import datetime, time, timedelta

import telethon
from config.config import load_config
from database.db import clear_users_in_batl, get_all_notifications, get_all_users
from routers.channel_router import delete_previous_messages
from tasks.task_handlers import TaskManager
import logging
from aiogram.types import MessageEntity
from user_bot import user_bot
from telethon.tl.types import *

class SchedulerManager:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.timezone = pytz.timezone('Europe/Moscow')
        self.task_manager = TaskManager()
        self.sent_notifications = set()

    async def setup(self, bot: Bot):
        """Настройка планировщика и добавление задач"""
        try:
            self.task_manager.bot = bot
            self.scheduler.timezone = self.timezone

            # Добавляем задачу для проверки и обновления расписания
            self.scheduler.add_job(
                self.check_and_schedule_battle,
                'interval',
                minutes=1,
                seconds=0,
                name='Schedule_checker',
                misfire_grace_time=300
            )
            
            # Добавляем задачу для проверки и обновления расписания
            self.scheduler.add_job(
                self.check_and_schedule_notifications,
                'interval',
                minutes=2,
                seconds=0,
                name='Notification_checker',
                misfire_grace_time=300
            )
            
            self.scheduler.add_job(
                self.check_scheduler_status,
                'interval',
                minutes=1,
                name='Scheduler_status_checker'
            )
            
            self.scheduler.add_job(
                self.clear_sent_notifications,
                'cron',
                hour=0,
                minute=36,
                name="Notification destuctor")

            


            
            # Запускаем планировщик
            if not self.scheduler.running:
                self.scheduler.start()
                logging.info("Scheduler started successfully")
        except Exception as e:
            logging.error(f"Error in scheduler setup: {str(e)}")
            raise
    
    async def get_config(self):
        dirname = os.path.dirname(__file__)
        filename = os.path.abspath(os.path.join(dirname, '..', 'config/config.env'))
        config = load_config(filename)
        return config
    
    async def start_battle_wrapper(self):
        """Обертка для запуска баттла с сохранением Task"""
        try:
            self.current_battle_task = asyncio.current_task()
            await self.task_manager.start_battle()
        except asyncio.CancelledError:
            logging.info("Battle task was cancelled")
            await self.cleanup_battle()
        except Exception as e:
            logging.error("Error in battle task " + str(e))
            await self.cleanup_battle()
            
            
    def remove_current_battle(self):
        """Останавливает текущий баттл, сохраняя следующее запланированное выполнение"""
        try:
            # Проверяем реальное состояние баттла
            if not self.task_manager.battle_active:
                logging.warning("Battle is not active according to task_manager")
                return False

            battle_job = self.scheduler.get_job('battle_job')
            checker_job = self.scheduler.get_job('Schedule_checker')
            
            # Останавливаем баттл независимо от наличия задачи в планировщике
            self.task_manager.battle_active = False
            
            # Временно приостанавливаем проверку расписания
            if checker_job:
                self.scheduler.pause_job('Schedule_checker')
            
            # Если задача существует в планировщике, удаляем её
            if battle_job:
                self.scheduler.remove_job('battle_job')
                logging.info("Battle job removed from scheduler")
            else:
                logging.warning("Battle job not found in scheduler, but battle was active")
            
            # Возобновляем проверку расписания
            if checker_job:
                self.scheduler.resume_job('Schedule_checker')
                
            logging.info("Current battle stopped, next battle will be scheduled by checker")
            return True
                
        except Exception as e:
            logging.error(f"Error in remove_current_battle: {e}")
            return False

    
    async def cleanup_battle(self):
        """Очистка после остановки баттла"""
        try:
            await delete_previous_messages(self.task_manager.bot, self.task_manager.channel_id)
            await clear_users_in_batl()
            self.task_manager.battle_active = False
            self.task_manager.first_round_active = False
            self.current_battle_task = None
            logging.info("Battle cleanup completed")
        except Exception as e:
            logging.error(f"Error in cleanup_battle: {e}")
    
    def stop(self):
        """Остановка планировщика"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                logging.info("Scheduler stopped")
        except Exception as e:
            logging.error(f"Error stopping scheduler: {e}")

    async def check_and_schedule_battle(self):
        """Проверка и планирование следующего баттла"""
        try:
            # Запускаем задачу уведомлений сразу при старте
            await self.task_manager.start_notification_task()
            logging.info("Checking battle schedule...")
            if self.task_manager.battle_active:
                logging.info("Battle is currently active, skipping scheduling")
                return

            next_battle_time = await self.task_manager.get_next_battle_time()
            # print(next_battle_time)
            if not next_battle_time:
                logging.warning("No next battle time available")
                return

            # Всегда работаем с временной зоной
            if next_battle_time.tzinfo is None:
                next_battle_time = self.timezone.localize(next_battle_time)
            logging.info(f"Next battle time determined: {next_battle_time}")

            existing_job = self.scheduler.get_job('battle_job')
            if existing_job:
                current_time = existing_job.next_run_time
                # Приводим оба времени к UTC для сравнения
                if current_time.astimezone(pytz.UTC) != next_battle_time.astimezone(pytz.UTC):
                    self.scheduler.reschedule_job(
                        'battle_job',
                        trigger='date',
                        run_date=next_battle_time,
                    )
                    logging.info(f"Battle rescheduled to: {next_battle_time}")
            else:
                self.scheduler.add_job(
                    self.start_battle_wrapper,
                    trigger='date',
                    run_date=next_battle_time,
                    id='battle_job',
                    name='Battle_task'
                )
                logging.info(f"New battle scheduled for: {next_battle_time}")
        except Exception as e:
            logging.error(f"Error in check_and_schedule_battle: {e}", exc_info=True)

    async def add_notification_job(self, code: str, message: str, time: time, entities=None, target="private"):
        """Добавление задачи уведомления"""
        try:  
        
            # Преобразуем строку времени в объект `datetime.time`
            time_obj = datetime.strptime(time, "%H:%M").time()
            users = await get_all_users()
            user_ids = [user[0] for user in users]
            
            # Дополнительный вывод в лог
            logging.info(f"Adding notification job: {code} at {time}")
            
            self.scheduler.add_job(
                self.send_notification,
                'cron',
                hour=time_obj.hour,  # Теперь берем `hour` из time_obj
                minute=time_obj.minute,  # Теперь берем `minute` из time_obj
                id=f'notification_{code}',
                args=[code, user_ids, message, entities, target],
                replace_existing=True
            )
        except Exception as e:
            logging.error(f"Error adding notification job: {code} at {time}", exc_info=True)



    async def send_notification(self, notification_id, user_ids, message, entities=None, target="private"):
        try:
            config = await self.get_config()
            CHANNEL_ID = config.tg_bot.channel_id
            
            if not isinstance(message, str):
                logging.error(f"Invalid message type for notification {notification_id}: {type(message)}")
                return

            telethon_entities = None
            aiogram_entities = None
            
            if entities:
                try:
                    print("Entities received:", entities)
                    if isinstance(entities, list) and all(isinstance(e, dict) for e in entities):
                        print("Processing list of dicts")
                        aiogram_entities = [MessageEntity(
                            type=entity['type'],
                            offset=entity['offset'],
                            length=entity['length'],
                            url=entity.get('url'),
                            user=entity.get('user'),
                            language=entity.get('language'),
                            custom_emoji_id=entity.get('custom_emoji_id')
                        ) for entity in entities]
                        telethon_entities = []
                        for entity in entities:
                            if entity['type'] == 'custom_emoji':
                                telethon_entities.append(MessageEntityCustomEmoji(
                                    offset=entity['offset'],
                                    length=entity['length'],
                                    document_id=int(entity['custom_emoji_id'])
                                ))
                            elif entity['type'] == 'bold':
                                telethon_entities.append(MessageEntityBold(
                                    offset=entity['offset'],
                                    length=entity['length']
                                ))
                            elif entity['type'] == 'italic':
                                telethon_entities.append(MessageEntityItalic(
                                    offset=entity['offset'],
                                    length=entity['length']
                                ))
                            elif entity['type'] == 'text_link':
                                telethon_entities.append(MessageEntityTextUrl(
                                    offset=entity['offset'],
                                    length=entity['length'],
                                    url=entity['url']
                                ))
                    elif isinstance(entities, list) and all(isinstance(e, MessageEntity) for e in entities):
                        print("Processing list of MessageEntity")
                        aiogram_entities = entities
                        telethon_entities = []
                        for entity in entities:
                            if entity.type == 'custom_emoji':
                                telethon_entities.append(MessageEntityCustomEmoji(
                                    offset=entity.offset,
                                    length=entity.length,
                                    document_id=int(entity.custom_emoji_id)
                                ))
                            elif entity.type == 'bold':
                                telethon_entities.append(MessageEntityBold(
                                    offset=entity.offset,
                                    length=entity.length
                                ))
                            elif entity.type == 'italic':
                                telethon_entities.append(MessageEntityItalic(
                                    offset=entity.offset,
                                    length=entity.length
                                ))
                            elif entity.type == 'text_link':
                                telethon_entities.append(MessageEntityTextUrl(
                                    offset=entity.offset,
                                    length=entity.length,
                                    url=entity.url
                                ))


                    elif isinstance(entities, str):
                        print("Processing JSON string")
                        entities_dicts = json.loads(entities)
                        aiogram_entities = [MessageEntity(
                            type=entity['type'],
                            offset=entity['offset'],
                            length=entity['length'],
                            url=entity.get('url'),
                            user=entity.get('user'),
                            language=entity.get('language'),
                            custom_emoji_id=entity.get('custom_emoji_id')
                        ) for entity in entities_dicts]
                        # Преобразование для Telethon (все поддерживаемые типы)
                        telethon_entities = []
                        for entity in entities_dicts:
                            if entity['type'] == 'custom_emoji':
                                telethon_entities.append(MessageEntityCustomEmoji(
                                    offset=entity['offset'],
                                    length=entity['length'],
                                    document_id=int(entity['custom_emoji_id'])
                                ))
                            elif entity['type'] == 'bold':
                                telethon_entities.append(MessageEntityBold(
                                    offset=entity['offset'],
                                    length=entity['length']
                                ))
                            elif entity['type'] == 'italic':
                                telethon_entities.append(MessageEntityItalic(
                                    offset=entity['offset'],
                                    length=entity['length']
                                ))
                            elif entity['type'] == 'text_link':
                                telethon_entities.append(MessageEntityTextUrl(
                                    offset=entity['offset'],
                                    length=entity['length'],
                                    url=entity['url']
                                ))
                    else:
                        print("Unknown entities format")
                    print(entities)
                except Exception as e:
                    logging.error(f"Error processing entities for notification {notification_id}: {e}")
                    # Можно добавить  raise, чтобы ошибка не игнорировалась, а всплывала выше
                    # raise

            if target == "private":
                for user_id in user_ids:
                    try:
                        await self.task_manager.bot.send_message(
                            chat_id=user_id,
                            text=message,
                            entities=aiogram_entities,
                            # parse_mode='HTML'  # Раскомментируйте, если нужен HTML, но это не обязательно
                        )
                        logging.info(f"Notification sent to user {user_id}: {notification_id} - {message}")
                    except Exception as e:
                        logging.error(f"Error sending notification {notification_id} to user {user_id}: {e}")

            elif target == "channel":
                try:
                    # Отправка через UserBot (Telethon)
                    await user_bot.send_channel_message(
                        channel_id=CHANNEL_ID,
                        message=message,
                        entities=telethon_entities
                    )
                    logging.info(f"Notification sent to channel via UserBot: {notification_id} - {message}")
                except Exception as e:
                    logging.error(f"Error sending notification {notification_id} to channel via UserBot: {e}")
                    logging.info("Attempting to send message via regular bot...")

                    try:
                        # Отправка через обычный бот (aiogram)
                        await self.task_manager.bot.send_message(
                            chat_id=CHANNEL_ID,
                            text=message,
                            entities=aiogram_entities,
                            # parse_mode='HTML'  # Раскомментируйте, если нужен HTML, но это не обязательно
                        )
                        logging.info(f"Notification sent to channel via regular bot: {notification_id} - {message}")
                    except Exception as e:
                        logging.error(f"Error sending notification {notification_id} to channel via regular bot: {e}")

        except Exception as e:
            logging.error(f"Error sending notification {notification_id}: {e}")




    
    async def check_and_schedule_notifications(self):
        try:
            notifications = await get_all_notifications()
            current_time = datetime.now(self.timezone)

            for notification in notifications:
                notification_id, code, message, time_str, entities, target = notification
                
                # Преобразуем строку времени в объект time
                time_obj = datetime.strptime(time_str, "%H:%M").time()
                
                # Создаем datetime объект для времени уведомления в текущем дне
                notification_time = self.timezone.localize(datetime.combine(current_time.date(), time_obj))
                
                # Создаем временное окно в 2 минуты после запланированного времени
                time_window_end = notification_time + timedelta(seconds=40)
                job_id = f'notification_{code}'
                if job_id in self.sent_notifications:
                    if current_time > notification_time:
                        logging.info(f"Notification {code} already sent today")
                    continue
                if current_time <= time_window_end:
                    # Если текущее время находится в пределах временного окна (включая запланированное время),
                    # планируем отправку уведомления
                    if current_time >= notification_time:
                        # Если уже прошло запланированное время, отправляем немедленно
                        run_date = current_time
                    else:
                        # Иначе планируем на запланированное время
                        run_date = notification_time
                    self.sent_notifications.add(job_id)
                    users = await get_all_users()  # Функция должна возвращать список [(user_id,), ...]
                    user_ids = [user[0] for user in users]
                    self.scheduler.add_job(
                        self.send_notification,
                        'date',
                        run_date=run_date,
                        args=(notification_id, user_ids, message, entities, target),
                        id=job_id,
                        replace_existing=True,
                    )
                    logging.info(f"Scheduled notification: {code} - {message}")
                else:
                    logging.info(f"Skipped notification {code} scheduled for {notification_time} (current time: {current_time})")
        except Exception as e:
            logging.error(f"Error in check_and_schedule_notifications: {e}", exc_info=True)



    async def remove_notification_job(self, code: str):
        try:
            self.scheduler.remove_job(f'notification_{code}')
            logging.info(f"Removed notification job: {code}")
        except Exception as e:
            logging.error(f"Error removing notification job: {code}", exc_info=True)

    
    async def check_scheduler_status(self):
        logging.info(f"Scheduler status: running={self.scheduler.running}")
        for job in self.scheduler.get_jobs():
            logging.info(f"Job: {job.id}, next run time: {job.next_run_time}")



    async def clear_sent_notifications(self):
        self.sent_notifications.clear()
        logging.info("Cleared sent notifications for the new day")








# для дальнейшего изменения времени баттла через
    async def reschedule_battle(self, new_time: datetime):
        """Изменение времени следующего баттла"""
        try:
            if self.task_manager.battle_active:
                logging.warning("Cannot reschedule while battle is active")
                return False

            # Добавляем информацию о временной зоне
            new_time = self.timezone.localize(new_time)

            job = self.scheduler.get_job('battle_job')
            if job:
                self.scheduler.reschedule_job(
                    'battle_job',
                    trigger='date',
                    run_date=new_time,
                    misfire_grace_time=300
                )
                logging.info(f"Battle rescheduled to: {new_time}")
            else:
                self.scheduler.add_job(
                    self.task_manager.start_battle,
                    trigger='date',
                    run_date=new_time,
                    id='battle_job',
                    name='Battle_task',
                    misfire_grace_time=300
                )
                logging.info(f"New battle scheduled for: {new_time}")
            return True
        except Exception as e:
            logging.error(f"Error rescheduling battle: {e}")
            return False





    # def get_next_battle_time(self) -> Optional[datetime]:
    #     """Получение времени следующего запланированного баттла"""
    #     job = self.scheduler.get_job('battle_job')
    #     return job.next_run_time if job else None

    # def remove_battle_job(self):
    #     """Удаляет задачу 'battle_job' из планировщика"""
    #     try:
    #         job = self.scheduler.get_job('battle_job')
    #         if job:
    #             self.scheduler.remove_job('battle_job')
    #             logging.info("Battle_job successfully removed from scheduler.")
    #         else:
    #             logging.warning("Battle_job not found in scheduler.")
    #     except Exception as e:
    #         logging.error(f"Error removing battle_job: {e}")


# для дебагга
    def get_scheduler_status(self) -> str:
        """Получение статуса планировщика"""
        try:
            status = []
            status.append(f"Scheduler running: {self.scheduler.running}")
            status.append(f"Current time (Moscow): {datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M:%S')}")

            for job in self.scheduler.get_jobs():
                status.append(f"Job: {job.name}")
                status.append(f"Next run: {job.next_run_time}")
                status.append(f"ID: {job.id}")
                status.append(f"Pending: {job.pending}")
                status.append("---")

            return "\n".join(status)
        except Exception as e:
            logging.error(f"Error getting scheduler status: {e}")
            return f"Error getting status: {str(e)}"

# Создание экземпляра SchedulerManager
scheduler_manager = SchedulerManager()