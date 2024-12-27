from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
import pytz
from typing import Optional
from .task_handlers import TaskManager

class SchedulerManager:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.timezone = pytz.timezone('Europe/Moscow')
        self.task_manager = TaskManager()

    def setup(self, bot: Bot):
        """Настройка планировщика и добавление задач"""
        self.task_manager.bot = bot
        self.scheduler.timezone = self.timezone

        # Задачи режима 1
        self.scheduler.add_job(
            self.task_manager.mode_1_task,
            trigger='cron',
            hour='*',
            minute='*',
            second='*/5',
            name='Mode 1 Task'
        )

        # Задачи режима 2
        self.scheduler.add_job(
            self.task_manager.mode_2_task,
            trigger='cron',
            hour='14-15',
            minute='*/30',
            name='Mode 2 Task'
        )

        # Задачи режима 3
        self.scheduler.add_job(
            self.task_manager.mode_3_task,
            trigger='cron',
            hour='16-17',
            minute=15,
            name='Mode 3 Task'
        )

        # Общие задачи
        self.scheduler.add_job(
            self.task_manager.general_task,
            trigger='cron',
            hour='*/2',  # Каждые 2 часа
            minute=0,
            name='General Task'
        )

    def start(self):
        """Запуск планировщика"""
        try:
            self.scheduler.start()
            print("Scheduler started successfully")
        except Exception as e:
            print(f"Error starting scheduler: {e}")

    def shutdown(self):
        """Остановка планировщика"""
        try:
            self.scheduler.shutdown()
            print("Scheduler shut down successfully")
        except Exception as e:
            print(f"Error shutting down scheduler: {e}")

def reschedule_task(self, task_id: str, new_trigger: dict):
        try:
            self.scheduler.reschedule_job(task_id, trigger='cron', **new_trigger)
            print(f"Task {task_id} rescheduled successfully to: {new_trigger}")
        except Exception as e:
            print(f"Error rescheduling task {task_id}: {e}")


# пример использования
# scheduler_manager.reschedule_task(
#         task_id='mode_1_task',
#         new_trigger={'hour': '*', 'minute': '*', 'second': '*/10'}
#     )