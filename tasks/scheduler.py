from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
import pytz
from typing import Optional
from tasks.task_handlers import TaskManager

class SchedulerManager:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.timezone = pytz.timezone('Europe/Moscow')
        self.task_manager = TaskManager()

    def setup(self, bot: Bot):
        """Настройка планировщика и добавление задач"""
        self.task_manager.bot = bot
        self.scheduler.timezone = self.timezone

        # Задача для запуска баттла
        self.scheduler.add_job(
            self.task_manager.start_battle,
            trigger='cron',
            hour=10, 
            minute=54,
            name='Start Battle'
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
        """Изменение расписания задачи"""
        try:
            self.scheduler.reschedule_job(task_id, trigger='cron', **new_trigger)
            print(f"Task {task_id} rescheduled successfully to: {new_trigger}")
        except Exception as e:
            print(f"Error rescheduling task {task_id}: {e}")

# Создание экземпляра SchedulerManager
scheduler_manager = SchedulerManager()

# пример использования
# scheduler_manager.reschedule_task(
#         task_id='mode_1_task',
#         new_trigger={'hour': '*', 'minute': '*', 'second': '*/10'}
#     )