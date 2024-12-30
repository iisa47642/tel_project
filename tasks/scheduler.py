from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
import pytz
from typing import Optional
from datetime import datetime, time, timedelta
from tasks.task_handlers import TaskManager
import logging

class SchedulerManager:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.timezone = pytz.timezone('Europe/Moscow')
        self.task_manager = TaskManager()

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

            # Запускаем задачу уведомлений
            self.scheduler.add_job(
                self.task_manager.start_notification_task,
                'cron',
                hour=0,
                minute=0,
                name='Notification_task',
                misfire_grace_time=3600
            )
            # Запускаем планировщик
            if not self.scheduler.running:
                self.scheduler.start()
                logging.info("Scheduler started successfully")
        except Exception as e:
            logging.error(f"Error in scheduler setup: {e}")
            raise

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
                        misfire_grace_time=300
                    )
                    logging.info(f"Battle rescheduled to: {next_battle_time}")
            else:
                self.scheduler.add_job(
                    self.task_manager.start_battle,
                    trigger='date',
                    run_date=next_battle_time,
                    id='battle_job',
                    name='Battle_task',
                    misfire_grace_time=300
                )
                logging.info(f"New battle scheduled for: {next_battle_time}")
        except Exception as e:
            logging.error(f"Error in check_and_schedule_battle: {e}", exc_info=True)

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